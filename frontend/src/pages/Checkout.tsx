import { useState, useMemo, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import WebApp from '@twa-dev/sdk';
import { isAxiosError } from 'axios';
import {
	Wallet,
	X,
	MapPin,
	ExternalLink,
	ShieldCheck,
	CheckCircle2,
	Truck,
	Edit2,
	Mail,
	Phone,
	User,
} from 'lucide-react';

import { useCart } from '@/hooks/queries/useCart';
import { useCheckout } from '@/hooks/mutations/useCheckout';
import { useSettings } from '@/hooks/queries/useUserSettings';
import { useDeliveryData } from '@/hooks/queries/useUserDeliveryData';
import { useDeliveryEstimate } from '@/hooks/queries/useDelivery';
import { useConfig } from '@/store/ConfigContext';
import { CustomSelect, type SelectOption } from '@/components/ui/CustomSelect';
import { CheckoutSkeleton } from '@/components/skeletons/CheckoutSkeleton';

interface PaymentNetwork {
	id: string;
	name: string;
}

interface PaymentCurrency {
	display_name: string;
	icon_url: string;
	networks: PaymentNetwork[];
}

interface PaymentProvider {
	display_name: string;
	icon_url: string;
	buyer_fee_percent: number;
	currencies: Record<string, PaymentCurrency>;
}

interface PaymentsVisualConfig {
	default_payment_gateway?: string;
	providers: Record<string, PaymentProvider>;
}

const t = (dict: Record<string, unknown> | undefined, key: string, fallback: string): string => {
	return dict && typeof dict[key] === 'string' ? (dict[key] as string) : fallback;
};

export function Checkout() {
	const navigate = useNavigate();
	const location = useLocation();
	const { config } = useConfig();

	const appliedPromoCode = location.state?.promoCode;

	const checkoutConfig = (config?.translations as Record<string, unknown>)?.checkout_page as
		| Record<string, unknown>
		| undefined;
	const cartConfig = (config?.translations as Record<string, unknown>)?.cart_page as
		| Record<string, unknown>
		| undefined;
	const tDelivery = cartConfig?.delivery_scale as Record<string, unknown> | undefined;
	const paymentsVisual = config?.payments_visual as PaymentsVisualConfig | undefined;

	const { items, totals, isLoading: isCartLoading } = useCart(appliedPromoCode);
	const { createOrder, createTransaction, isCreatingOrder, isCreatingTransaction } = useCheckout();
	const { settings } = useSettings();
	const { deliveryList, isLoading: isDeliveryListLoading } = useDeliveryData();

	const currentAddress = useMemo(() => {
		if (!deliveryList || deliveryList.length === 0) return null;
		return deliveryList.find((d) => d.is_current) || deliveryList[0];
	}, [deliveryList]);

	const {
		estimate,
		requiresAddress,
		isLoading: isEstimateLoading,
	} = useDeliveryEstimate(
		currentAddress?.destination_code || null,
		currentAddress?.region_code || null,
	);

	const isInitialLoading = isCartLoading || isDeliveryListLoading || isEstimateLoading;

	const hasPhysicalItems = items.length > 0 && requiresAddress !== undefined;
	const shippingCost =
		!requiresAddress && estimate && !estimate.isFree ? parseFloat(estimate.cost || '0') : 0;
	const cartTotalValue = totals?.total || 0;
	const baseTotal = cartTotalValue + shippingCost;

	const [errorMsg, setErrorMsg] = useState('');
	const [showRedirectWarning, setShowRedirectWarning] = useState(false);
	const [paymentUrl, setPaymentUrl] = useState<string | null>(null);
	const [hasRedirected, setHasRedirected] = useState(false);

	const [isOrderPlaced, setIsOrderPlaced] = useState(false);
	const [createdOrderId, setCreatedOrderId] = useState<string | null>(null);

	const [selectedProvider, setSelectedProvider] = useState<string>('default');
	const [selectedCurrency, setSelectedCurrency] = useState<string>('default');
	const [selectedNetwork, setSelectedNetwork] = useState<string>('default');

	const defaultCurrencyLabel = settings?.preferred_payment_currency
		? `${t(checkoutConfig, 'default_option', 'Default')} (${settings.preferred_payment_currency.toUpperCase()})`
		: t(checkoutConfig, 'default_option', 'Default');

	const defaultNetworkLabel = settings?.preferred_network
		? `${t(checkoutConfig, 'default_option', 'Default')} (${settings.preferred_network.toUpperCase()})`
		: t(checkoutConfig, 'default_option', 'Default');

	const resolvedProvider = useMemo(() => {
		if (selectedProvider !== 'default') return selectedProvider;
		if (!paymentsVisual?.providers) return '';
		return paymentsVisual.default_payment_gateway || Object.keys(paymentsVisual.providers)[0] || '';
	}, [selectedProvider, paymentsVisual]);

	const currentProviderData = paymentsVisual?.providers?.[resolvedProvider];

	const providerOptions: SelectOption[] = useMemo(() => {
		if (!paymentsVisual?.providers) return [];
		return Object.entries(paymentsVisual.providers).map(([key, p]) => ({
			value: key,
			label: p.display_name,
			icon: p.icon_url,
		}));
	}, [paymentsVisual]);

	const currencyOptions: SelectOption[] = useMemo(() => {
		if (!currentProviderData?.currencies) return [];
		const opts: SelectOption[] = Object.entries(currentProviderData.currencies).map(([key, c]) => ({
			value: key,
			label: c.display_name,
			icon: c.icon_url,
		}));
		return [{ value: 'default', label: defaultCurrencyLabel }, ...opts];
	}, [currentProviderData, defaultCurrencyLabel]);

	const networkOptions: SelectOption[] = useMemo(() => {
		if (selectedCurrency === 'default') {
			return [{ value: 'default', label: defaultNetworkLabel }];
		}
		if (!currentProviderData?.currencies?.[selectedCurrency]) {
			return [];
		}
		return currentProviderData.currencies[selectedCurrency].networks.map((n) => ({
			value: n.id,
			label: n.name,
		}));
	}, [selectedCurrency, currentProviderData, defaultNetworkLabel]);

	const { providerFeePercent, providerFee, finalTotal } = useMemo(() => {
		const feePercent = currentProviderData?.buyer_fee_percent || 0;
		const fee = baseTotal * (feePercent / 100);
		return {
			providerFeePercent: feePercent,
			providerFee: fee,
			finalTotal: baseTotal + fee,
		};
	}, [currentProviderData, baseTotal]);

	const getTranslatedError = useCallback(
		(error: unknown) => {
			if (isAxiosError(error) && error.response?.data) {
				const code = error.response.data.code;
				if (code === 'LIMIT_EXCEEDED') {
					return t(
						checkoutConfig,
						'limit_exceeded',
						'You have reached the maximum number of pending orders.',
					);
				}
				if (code === 'OUT_OF_STOCK') {
					return t(checkoutConfig, 'out_of_stock', 'One or more products are out of stock.');
				}
			}
			return t(checkoutConfig, 'default_error', 'Failed to process order. Please try again.');
		},
		[checkoutConfig],
	);

	const handleGenerateInvoice = useCallback(async () => {
		setErrorMsg('');
		setIsOrderPlaced(true);

		let currentOrderId = createdOrderId;

		try {
			if (!currentOrderId) {
				const orderPayload = {
					...(appliedPromoCode ? { code: appliedPromoCode } : {}),
				};

				const orderRes = await createOrder(orderPayload);
				currentOrderId = orderRes.order_id;
				setCreatedOrderId(currentOrderId);
			}

			const txPayload = {
				order_id: currentOrderId,
				...(selectedProvider !== 'default' ? { provider_name: selectedProvider } : {}),
				...(selectedCurrency !== 'default' ? { currency: selectedCurrency } : {}),
				...(selectedNetwork !== 'default' ? { network: selectedNetwork } : {}),
			};

			const txRes = await createTransaction(txPayload);

			if (txRes.payload_url) {
				setPaymentUrl(txRes.payload_url);
				setShowRedirectWarning(true);
			} else {
				navigate('/orders');
			}
		} catch (error: unknown) {
			setErrorMsg(getTranslatedError(error));

			if (!currentOrderId) {
				setIsOrderPlaced(false);
			}
		}
	}, [
		createdOrderId,
		createOrder,
		appliedPromoCode,
		createTransaction,
		selectedProvider,
		selectedCurrency,
		selectedNetwork,
		navigate,
		getTranslatedError,
	]);

	const executeRedirect = useCallback(() => {
		if (!paymentUrl) return;
		setHasRedirected(true);
		setShowRedirectWarning(false);
		try {
			WebApp.openLink(paymentUrl);
		} catch {
			window.open(paymentUrl, '_blank');
		}
	}, [paymentUrl]);

	if (isInitialLoading) {
		return <CheckoutSkeleton />;
	}

	if (items.length === 0 && !hasRedirected && !isOrderPlaced && !createdOrderId) {
		navigate('/');
		return null;
	}

	if (hasRedirected) {
		return (
			<div className="flex flex-col items-center justify-center min-h-[70vh] p-4 text-center">
				<div className="w-16 h-16 bg-blue-50 dark:bg-blue-500/10 rounded-full flex items-center justify-center mb-6">
					<Wallet size={32} className="text-blue-600 dark:text-blue-500" />
				</div>
				<h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
					{t(checkoutConfig, 'payment_in_progress', 'Payment in Progress')}
				</h2>
				<p className="text-xs text-gray-500 dark:text-gray-400 mb-8 max-w-sm">
					{t(
						checkoutConfig,
						'payment_progress_desc',
						'We have opened the payment gateway for you. After completing the payment, check your order status.',
					)}
				</p>

				<div className="flex flex-col gap-3 w-full max-w-xs">
					<button
						onClick={() => navigate('/orders')}
						className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer"
					>
						{t(checkoutConfig, 'check_status', 'Check Order Status')}
					</button>

					<button
						onClick={executeRedirect}
						className="w-full py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-all text-xs cursor-pointer"
					>
						{t(checkoutConfig, 'reopen_payment', 'Re-open Payment Page')} <ExternalLink size={14} />
					</button>
				</div>
			</div>
		);
	}

	const isProcessing = isCreatingOrder || isCreatingTransaction;

	return (
		<div className="flex flex-col min-h-full pb-20 relative">
			<div className="p-3 sm:p-4 flex-1 max-w-3xl mx-auto w-full">
				<motion.div
					initial={{ opacity: 0, y: 10 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
					style={{ willChange: 'opacity, transform' }}
					className="space-y-4"
				>
					{hasPhysicalItems && (
						<div className="space-y-2">
							<h2 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5 ml-1">
								<MapPin size={14} />{' '}
								{t(checkoutConfig, 'shipping_address', 'Shipping & Contact Details')}
							</h2>
							<div
								className={`bg-white dark:bg-gray-900 p-3 sm:p-4 rounded-xl border transition-colors duration-300 shadow-sm ${requiresAddress ? 'border-red-500/50 dark:border-red-900/50' : 'border-gray-200 dark:border-gray-800'}`}
							>
								<div className="flex items-start gap-2.5">
									<div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 shrink-0">
										<Truck size={16} />
									</div>
									<div className="flex-1 min-w-0">
										<div className="flex justify-between items-start gap-2">
											<div className="min-w-0">
												<h3 className="font-bold text-xs text-gray-900 dark:text-white flex items-center gap-1.5 truncate">
													<User size={12} className="text-gray-400 dark:text-gray-500 shrink-0" />
													<span className="truncate">
														{currentAddress?.full_name || 'Name not set'}
													</span>
												</h3>
												<p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2.5 truncate">
													<span className="flex items-center gap-1 shrink-0">
														<Phone size={10} /> {currentAddress?.phone || '—'}
													</span>
													<span className="flex items-center gap-1 truncate">
														<Mail size={10} className="shrink-0" />{' '}
														<span className="truncate">{currentAddress?.email || '—'}</span>
													</span>
												</p>
											</div>
											<button
												onClick={() => navigate('/settings')}
												className="text-[10px] font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-500 transition-colors shrink-0 flex items-center gap-1 cursor-pointer mt-0.5"
											>
												{t(tDelivery, 'change_address', 'Change')} <Edit2 size={10} />
											</button>
										</div>

										<div className="mt-2.5 pt-2.5 border-t border-gray-200 dark:border-gray-800">
											<p className="text-[11px] sm:text-xs text-gray-700 dark:text-gray-300 leading-snug">
												{requiresAddress
													? t(tDelivery, 'inactive', 'Select Address')
													: currentAddress?.address_line}
											</p>
											{currentAddress && (
												<p className="text-[10px] sm:text-[11px] text-gray-500 mt-1">
													{currentAddress.destination_code}
													{currentAddress.region_code ? ', ' + currentAddress.region_code : ''}
												</p>
											)}
										</div>
									</div>
								</div>
							</div>

							{requiresAddress && (
								<div className="p-2.5 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl text-red-600 dark:text-red-500 text-xs text-center font-medium">
									{t(
										checkoutConfig,
										'required_address_error',
										'Please select or add a shipping address in settings to continue.',
									)}
								</div>
							)}
						</div>
					)}

					<div className="rounded-xl p-4 border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 space-y-2.5">
						<div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
							<span>{t(checkoutConfig, 'order_summary', 'Order Summary')}</span>
							<span>${cartTotalValue.toFixed(2)}</span>
						</div>
						{hasPhysicalItems && (
							<div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
								<span>{t(cartConfig, 'shipping', 'Shipping')}</span>
								<span>${shippingCost.toFixed(2)}</span>
							</div>
						)}
						<div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800 pb-2.5">
							<span>
								{t(checkoutConfig, 'fee', 'Provider Fee')} ({providerFeePercent}%)
							</span>
							<span>${providerFee.toFixed(2)}</span>
						</div>
						<div className="flex justify-between items-end pt-1">
							<span className="text-xs text-gray-700 dark:text-gray-300 font-semibold">
								{t(checkoutConfig, 'final_amount', 'Final Amount')}
							</span>
							<span className="text-xl font-bold text-gray-900 dark:text-white">
								${finalTotal.toFixed(2)}
							</span>
						</div>
					</div>

					<div className="space-y-3.5">
						<div>
							<h3 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider ml-1">
								{t(checkoutConfig, 'select_provider', 'Select Provider')}
							</h3>
							<CustomSelect
								value={resolvedProvider}
								onChange={(val) => {
									setSelectedProvider(val);
									setSelectedCurrency('default');
									setSelectedNetwork('default');
								}}
								options={providerOptions}
							/>
						</div>

						<div>
							<h3 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider ml-1">
								{t(checkoutConfig, 'select_crypto', 'Select Cryptocurrency')}
							</h3>
							<CustomSelect
								value={selectedCurrency}
								onChange={(val) => {
									setSelectedCurrency(val);
									if (val === 'default') {
										setSelectedNetwork('default');
									} else {
										const networks = currentProviderData?.currencies?.[val]?.networks;
										setSelectedNetwork(networks && networks.length > 0 ? networks[0].id : '');
									}
								}}
								options={currencyOptions}
							/>
						</div>

						<div>
							<h3 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wider ml-1 flex items-center justify-between">
								{t(checkoutConfig, 'select_network', 'Select Network')}
								<span className="text-[9px] text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-400/10 border border-orange-200/50 dark:border-transparent px-1.5 py-0.5 rounded uppercase">
									{t(checkoutConfig, 'important', 'Important')}
								</span>
							</h3>
							<CustomSelect
								value={selectedNetwork}
								onChange={setSelectedNetwork}
								options={networkOptions}
								disabled={selectedCurrency === 'default' && networkOptions.length <= 1}
							/>
						</div>
					</div>

					{errorMsg && (
						<div className="p-2.5 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl text-red-600 dark:text-red-500 text-xs text-center font-medium">
							{errorMsg}
						</div>
					)}

					<div className="pt-2">
						<div className="flex items-center justify-center gap-1.5 text-[11px] text-gray-500 mb-3 text-center">
							<Wallet size={12} /> {t(checkoutConfig, 'secure_payment', 'Secure Payment')}
						</div>
						{createdOrderId ? (
							<button
								onClick={() => navigate('/orders')}
								className="w-full py-3.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-xl text-sm font-semibold transition-colors shadow-lg cursor-pointer"
							>
								{t(checkoutConfig, 'go_to_orders', 'Go to Orders')}
							</button>
						) : (
							<button
								onClick={handleGenerateInvoice}
								disabled={isProcessing || (hasPhysicalItems && requiresAddress)}
								className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
							>
								{isProcessing ? (
									<div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
								) : (
									<>
										<Wallet size={16} />
										{t(checkoutConfig, 'generate_invoice', 'Generate Invoice')}
									</>
								)}
							</button>
						)}
					</div>
				</motion.div>
			</div>

			<AnimatePresence>
				{showRedirectWarning && (
					<>
						<motion.div
							initial={{ opacity: 0 }}
							animate={{ opacity: 1 }}
							exit={{ opacity: 0 }}
							onClick={() => setShowRedirectWarning(false)}
							className="fixed inset-0 bg-black/60 z-40"
						/>
						<motion.div
							initial={{ y: '100%' }}
							animate={{ y: 0 }}
							exit={{ y: '100%' }}
							transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
							style={{ willChange: 'transform' }}
							className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white dark:bg-gray-900 rounded-t-3xl border-t border-x border-gray-200 dark:border-gray-800 z-50 flex flex-col sm:shadow-2xl"
						>
							<div className="flex justify-between items-start p-4 border-b border-gray-200 dark:border-gray-800">
								<div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
									<ShieldCheck size={20} />
									<h2 className="text-lg font-bold text-gray-900 dark:text-white">
										{t(checkoutConfig, 'secure_payment', 'Secure Payment')}
									</h2>
								</div>
								<button
									onClick={() => setShowRedirectWarning(false)}
									className="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors bg-gray-100 dark:bg-gray-800 p-1.5 rounded-full cursor-pointer"
								>
									<X size={18} />
								</button>
							</div>

							<div className="p-5">
								<p className="text-gray-600 dark:text-gray-300 text-xs leading-relaxed mb-5">
									{t(
										checkoutConfig,
										'redirect_warning',
										'You are about to be redirected securely.',
									)?.replace('{provider}', currentProviderData?.display_name || 'Provider')}
								</p>

								<div className="space-y-2.5 mb-6">
									<div className="flex items-center gap-2.5 text-xs text-gray-600 dark:text-gray-400">
										<CheckCircle2 size={14} className="text-blue-600 dark:text-blue-500 shrink-0" />
										<span>{t(checkoutConfig, 'order_reserved', 'Your order is reserved.')}</span>
									</div>
									<div className="flex items-center gap-2.5 text-xs text-gray-600 dark:text-gray-400">
										<ExternalLink size={14} className="text-blue-600 dark:text-blue-500 shrink-0" />
										<span>
											{t(
												checkoutConfig,
												'close_browser_notice',
												'After payment, close the browser to return here.',
											)}
										</span>
									</div>
								</div>

								<div className="grid grid-cols-2 gap-2.5">
									<button
										onClick={() => setShowRedirectWarning(false)}
										className="py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-900 dark:text-white rounded-xl text-sm font-medium transition-colors cursor-pointer"
									>
										{t(checkoutConfig, 'cancel', 'Cancel')}
									</button>
									<button
										onClick={executeRedirect}
										className="py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer"
									>
										{t(checkoutConfig, 'continue', 'Continue')} <ExternalLink size={14} />
									</button>
								</div>
							</div>
						</motion.div>
					</>
				)}
			</AnimatePresence>
		</div>
	);
}

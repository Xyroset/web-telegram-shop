import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Minus, Plus, Trash2, ArrowRight, Tag, X, Truck, MapPin, Edit2 } from 'lucide-react';

import { useCart } from '@/hooks/queries/useCart';
import { useDeliveryEstimate } from '@/hooks/queries/useDelivery';
import { useDeliveryData } from '@/hooks/queries/useUserDeliveryData';
import { useConfig } from '@/store/ConfigContext';
import { ProductModal } from '@/components/ProductModal';
import { CartSkeleton } from '@/components/skeletons/CartSkeleton';
import type { Product } from '@/types/product';

const t = (dict: Record<string, unknown> | undefined, key: string, fallback: string): string => {
	return dict && typeof dict[key] === 'string' ? (dict[key] as string) : fallback;
};

type TranslationNode = string | Record<string, string>;
type ModalTranslations = Record<string, TranslationNode>;

interface QuantityControlProps {
	quantity: number;
	variantId: number;
	disabled: boolean;
	onUpdateExact: (variantId: number, newQuantity: number) => void;
	onRemove: (variantId: number) => void;
}

function QuantityControl({
	quantity,
	variantId,
	disabled,
	onUpdateExact,
	onRemove,
}: QuantityControlProps) {
	const [localVal, setLocalVal] = useState(String(quantity));
	const [prevQuantityProp, setPrevQuantityProp] = useState(quantity);

	if (quantity !== prevQuantityProp) {
		setPrevQuantityProp(quantity);
		setLocalVal(String(quantity));
	}

	const submitChange = () => {
		const parsed = parseInt(localVal, 10);
		if (isNaN(parsed) || parsed <= 0) {
			onRemove(variantId);
		} else if (parsed !== quantity) {
			onUpdateExact(variantId, parsed);
		} else {
			setLocalVal(String(quantity));
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === 'Enter') {
			e.currentTarget.blur();
		}
	};

	return (
		<div className="flex items-center gap-1 sm:gap-2 bg-gray-50 dark:bg-gray-950 p-1 rounded-lg border border-gray-100 dark:border-gray-800">
			<button
				onClick={() => {
					const parsed = parseInt(localVal, 10) || quantity;
					if (parsed - 1 <= 0) onRemove(variantId);
					else onUpdateExact(variantId, parsed - 1);
				}}
				disabled={disabled}
				className="w-6 h-6 sm:w-7 sm:h-7 rounded-md bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors duration-300 shadow-sm disabled:opacity-50"
			>
				<Minus size={12} className="sm:w-3.5 sm:h-3.5" />
			</button>
			<input
				type="number"
				value={localVal}
				onChange={(e) => setLocalVal(e.target.value)}
				onBlur={submitChange}
				onKeyDown={handleKeyDown}
				disabled={disabled}
				className="w-8 sm:w-10 text-center text-xs sm:text-sm font-medium bg-transparent border-none outline-none text-gray-900 dark:text-white appearance-none [&::-webkit-inner-spin-button]:appearance-none"
			/>
			<button
				onClick={() => {
					const parsed = parseInt(localVal, 10) || quantity;
					onUpdateExact(variantId, parsed + 1);
				}}
				disabled={disabled}
				className="w-6 h-6 sm:w-7 sm:h-7 rounded-md bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors duration-300 shadow-sm disabled:opacity-50"
			>
				<Plus size={12} className="sm:w-3.5 sm:h-3.5" />
			</button>
		</div>
	);
}

export function Cart() {
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();
	const { config } = useConfig();

	const cartConfig = (config?.translations as Record<string, unknown>)?.cart_page as
		| ModalTranslations
		| undefined;
	const productModal = (config?.translations as Record<string, unknown>)?.product_modal as
		| ModalTranslations
		| undefined;
	const tPromo = cartConfig?.promo_code as Record<string, unknown> | undefined;
	const tDelivery = cartConfig?.delivery_scale as Record<string, unknown> | undefined;

	const [promoInput, setPromoInput] = useState('');

	const [appliedPromo, setAppliedPromo] = useState<string | undefined>(() => {
		const stored = sessionStorage.getItem('applied_promo_checkout');
		if (stored && stored !== 'undefined' && stored !== 'null') {
			return stored;
		}
		return undefined;
	});

	useEffect(() => {
		sessionStorage.removeItem('applied_promo_checkout');
	}, []);

	const {
		items,
		totals,
		isLoading: isCartLoading,
		isError,
		updateQuantity,
		removeFromCart,
		isUpdating,
		refetchTotals,
	} = useCart(appliedPromo);

	const { deliveryList, isLoading: isDeliveryDataLoading } = useDeliveryData();

	const currentAddress = useMemo(() => {
		if (!deliveryList || deliveryList.length === 0) return null;
		return deliveryList.find((d) => d.is_current) || deliveryList[0];
	}, [deliveryList]);

	const userDestinationCode = currentAddress?.destination_code || null;
	const userRegionCode = currentAddress?.region_code || null;

	const {
		estimate,
		requiresAddress,
		isLoading: isEstimateLoading,
	} = useDeliveryEstimate(userDestinationCode, userRegionCode);

	const isGlobalLoading = isCartLoading || isDeliveryDataLoading;
	const modalVariantId = searchParams.get('variant');
	const subtotalValue = totals?.subtotal || 0;

	const sortedItems = useMemo(() => {
		return [...items].sort((a, b) => {
			const nameComparison = a.name.localeCompare(b.name);

			if (nameComparison !== 0) {
				return nameComparison;
			}
			return a.variantId - b.variantId;
		});
	}, [items]);

	const selectedProduct = useMemo(() => {
		if (!modalVariantId) return null;
		const matchedItem = items.find((item) => String(item.variantId) === modalVariantId);
		return matchedItem?.product ?? null;
	}, [items, modalVariantId]);

	useEffect(() => {
		if (!modalVariantId || selectedProduct) return;
		const nextParams = new URLSearchParams(searchParams);
		nextParams.delete('variant');
		setSearchParams(nextParams, { replace: true });
	}, [modalVariantId, searchParams, selectedProduct, setSearchParams]);

	const handleUpdateExactQuantity = useCallback(
		(variantId: number, newQuantity: number) => {
			if (newQuantity <= 0) {
				removeFromCart({ variantId });
			} else {
				updateQuantity({ variantId, quantity: newQuantity });
			}
		},
		[removeFromCart, updateQuantity],
	);

	const handleApplyPromo = useCallback(() => {
		const code = promoInput.trim().toUpperCase();
		if (!code) return;

		if (code === appliedPromo) {
			refetchTotals();
		} else {
			setAppliedPromo(code);
		}
	}, [promoInput, appliedPromo, refetchTotals]);

	const handleRemovePromo = useCallback(() => {
		setAppliedPromo(undefined);
		setPromoInput('');
	}, []);

	const handleOpenModal = useCallback(
		(variantId: number, product?: Product) => {
			if (!product) return;
			const nextParams = new URLSearchParams(searchParams);
			nextParams.set('variant', String(variantId));
			setSearchParams(nextParams, { replace: false });
		},
		[searchParams, setSearchParams],
	);

	const handleCloseModal = useCallback(() => {
		const nextParams = new URLSearchParams(searchParams);
		nextParams.delete('variant');
		setSearchParams(nextParams, { replace: true });
	}, [searchParams, setSearchParams]);

	const resolvePromoError = (errorStr: string | undefined): string => {
		console.log(errorStr);
		if (!errorStr) return '';

		const safeStr = errorStr.toLowerCase();

		if (safeStr.includes('already used'))
			return t(tPromo, 'already_used', 'This promo code has already been used.');
		if (safeStr.includes('expired')) return t(tPromo, 'expired', 'This promo code has expired.');
		if (safeStr.includes('inactive')) return t(tPromo, 'inactive', 'This promo code is inactive.');
		if (safeStr.includes('limit reached'))
			return t(tPromo, 'limit_reached', 'Promo code usage limit reached.');
		if (safeStr.includes('not yet valid'))
			return t(tPromo, 'not_yet_valid', 'Promo code is not yet valid.');

		if (
			safeStr.includes('minimum order amount is') ||
			safeStr.includes('min order amount not met')
		) {
			const match = safeStr.match(/minimum order amount is ([\d.]+)/);
			if (match) {
				const minAmount = parseFloat(match[1]);
				const diff = minAmount - subtotalValue;
				if (diff > 0) {
					const diffFormatted = diff.toFixed(2);
					return t(tPromo, 'min_amount_diff', 'Add ${amount} more to use this code').replace(
						'{amount}',
						diffFormatted,
					);
				}
			}
			return t(tPromo, 'min_amount', 'Minimum order amount not met.');
		}

		if (errorStr === 'server_error') return 'Server Error';
		return t(tPromo, 'error', 'Invalid promo code');
	};

	const promoError = appliedPromo && totals?.promoError ? resolvePromoError(totals.promoError) : '';

	const promoSuccess =
		appliedPromo && totals?.isPromoValid && !promoError
			? t(tPromo, 'success', 'Promo code applied successfully!')
			: '';

	if (isGlobalLoading) {
		return <CartSkeleton />;
	}

	if (isError) {
		return (
			<div className="flex justify-center items-center h-[70vh] text-center p-4">
				<p className="text-red-500 text-sm font-medium">
					Failed to load cart. Please try again later.
				</p>
			</div>
		);
	}

	if (sortedItems.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center h-[70vh] p-4 text-center">
				<div className="w-16 h-16 sm:w-20 sm:h-20 bg-gray-100 dark:bg-gray-900 rounded-full flex items-center justify-center mb-3 sm:mb-4 text-gray-500 dark:text-gray-700 transition-colors duration-300">
					<svg
						width="28"
						height="28"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						strokeWidth="2"
						strokeLinecap="round"
						strokeLinejoin="round"
						className="sm:w-8 sm:h-8"
					>
						<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" />
						<path d="M3 6h18" />
						<path d="M16 10a4 4 0 0 1-8 0" />
					</svg>
				</div>
				<h2 className="text-lg sm:text-xl font-bold mb-1.5 sm:mb-2 text-gray-900 dark:text-white transition-colors duration-300">
					{t(cartConfig, 'empty', 'Your cart is empty')}
				</h2>
				<p className="text-gray-500 dark:text-gray-400 mb-5 sm:mb-6 text-xs sm:text-sm transition-colors duration-300">
					{t(cartConfig, 'empty_subtext', "Looks like you haven't added anything yet.")}
				</p>
				<button
					onClick={() => navigate('/')}
					className="px-5 py-2.5 sm:px-6 sm:py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors cursor-pointer shadow-lg shadow-blue-600/20"
				>
					{t(cartConfig, 'start_shopping', 'Start Shopping')}
				</button>
			</div>
		);
	}

	const cartTotalValue = totals?.total || 0;

	let progressPercent = 0;
	let isFreeShipping = false;
	let shippingCost = 0;
	let deliveryMessage = t(tDelivery, 'inactive', 'Select a delivery address to see shipping costs');
	let deliverySubMessage = '';

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const zoneExtra = config?.zone_names_extra as Record<string, any> | undefined;
	const deliveryDays =
		userRegionCode && zoneExtra?.[userRegionCode]?.delivery_days
			? zoneExtra[userRegionCode].delivery_days
			: userDestinationCode && zoneExtra?.[userDestinationCode]?.delivery_days
				? zoneExtra[userDestinationCode].delivery_days
				: null;

	const estDeliveryText = deliveryDays
		? t(tDelivery, 'est_delivery', 'Estimated delivery: {days} days').replace(
				'{days}',
				String(deliveryDays),
			)
		: '';

	if (!requiresAddress && estimate && !isEstimateLoading) {
		const amountLeft = parseFloat(estimate.amountLeftForFree || '0');
		shippingCost = parseFloat(estimate.cost || '0');
		isFreeShipping = estimate.isFree;

		if (!estimate.isFreeAvailable) {
			deliveryMessage = t(cartConfig, 'shipping', 'Shipping');
			deliverySubMessage = t(
				tDelivery,
				'free_unavailable',
				'Free shipping is not available in your region',
			);
			progressPercent = 100;
		} else {
			const totalNeeded = subtotalValue + amountLeft;
			progressPercent = totalNeeded > 0 ? Math.min((subtotalValue / totalNeeded) * 100, 100) : 100;

			if (isFreeShipping) {
				progressPercent = 100;
				deliveryMessage = t(tDelivery, 'free_unlocked', 'Congratulations! You get Free Delivery!');
			} else {
				deliveryMessage = t(tDelivery, 'add_more', 'Add {amount} more for free delivery').replace(
					'{amount}',
					`$${amountLeft.toFixed(2)}`,
				);
				deliverySubMessage = t(
					tDelivery,
					'free_available',
					'Free shipping is available in your region',
				);
			}
		}
	} else if (isEstimateLoading) {
		deliveryMessage = t(tDelivery, 'calculating', 'Calculating delivery...');
	}

	const finalTotal = cartTotalValue + shippingCost;

	return (
		<>
			<div
				className={`flex flex-col min-h-full transition-opacity duration-300 ${isUpdating ? 'opacity-60 pointer-events-none' : ''}`}
			>
				<div className="flex-1 p-3 sm:p-4 space-y-3 sm:space-y-4 max-w-4xl mx-auto w-full">
					<motion.div
						initial={{ opacity: 0, y: -20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
						style={{ willChange: 'transform, opacity' }}
						className={`bg-white dark:bg-gray-900 p-3 sm:p-4 rounded-2xl border transition-colors duration-300 shadow-sm transform-gpu ${
							requiresAddress
								? 'border-gray-200 dark:border-gray-800'
								: isFreeShipping
									? 'border-green-200 dark:border-green-900/50'
									: 'border-blue-200 dark:border-blue-900/50'
						}`}
					>
						<div className="flex items-start gap-3 mb-2.5 sm:mb-3">
							<div
								className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center transition-colors duration-500 shrink-0 mt-0.5 ${
									requiresAddress
										? 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
										: isFreeShipping
											? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
											: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
								}`}
							>
								<Truck size={16} className="sm:w-5 sm:h-5" />
							</div>

							<div className="flex-1">
								<div className="flex justify-between items-start">
									<h3
										className={`font-bold text-xs sm:text-sm transition-colors duration-300 leading-tight ${
											requiresAddress
												? 'text-gray-600 dark:text-gray-300'
												: 'text-gray-900 dark:text-white'
										}`}
									>
										{deliveryMessage}
									</h3>
									{currentAddress && (
										<button
											onClick={() => navigate('/settings')}
											className="text-[10px] sm:text-xs font-bold uppercase tracking-wide text-blue-600 dark:text-blue-400 hover:text-blue-700 transition-colors ml-2 shrink-0 flex items-center gap-1 cursor-pointer"
										>
											{t(tDelivery, 'change_address', 'Change')} <Edit2 size={10} />
										</button>
									)}
								</div>

								{currentAddress && (
									<p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300 mt-1 flex items-center gap-1">
										<MapPin size={12} className="shrink-0" />
										<span className="truncate">
											{t(tDelivery, 'deliver_to', 'Deliver to')}: {currentAddress.address_line},{' '}
											{currentAddress.destination_code}
											{currentAddress.region_code ? ', ' + currentAddress.region_code : ''}
										</span>
									</p>
								)}

								{deliverySubMessage && (
									<p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 transition-colors duration-300 mt-1">
										{deliverySubMessage}
									</p>
								)}

								{estDeliveryText && (
									<p className="text-[10px] sm:text-xs font-medium text-blue-600/80 dark:text-blue-400/80 transition-colors duration-300 mt-1">
										{estDeliveryText}
									</p>
								)}
							</div>
						</div>

						{requiresAddress ? (
							<button
								onClick={() => navigate('/settings')}
								className="w-full mt-2 flex items-center justify-center gap-1.5 py-2 text-xs font-semibold bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-lg transition-colors cursor-pointer"
							>
								<MapPin size={14} /> {t(tDelivery, 'select_address', 'Select Address')}
							</button>
						) : (
							estimate?.isFreeAvailable && (
								<div className="h-1.5 sm:h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden transition-colors duration-300 mt-1">
									<motion.div
										initial={{ width: 0 }}
										animate={{ width: `${progressPercent}%` }}
										transition={{ duration: 1, ease: 'easeOut' }}
										className={`h-full rounded-full transition-colors duration-500 ${isFreeShipping ? 'bg-green-500' : 'bg-blue-600'}`}
									/>
								</div>
							)
						)}
					</motion.div>

					{sortedItems.map((item, idx) => {
						const stockStatus = item.product.displayVariant?.stockStatus;
						const lineItemTotal = item.price * item.quantity;

						return (
							<motion.div
								key={item.id}
								initial={{ opacity: 0, x: -20 }}
								animate={{ opacity: 1, x: 0 }}
								transition={{ type: 'tween', duration: 0.2, delay: idx * 0.03, ease: 'easeOut' }}
								style={{ willChange: 'transform, opacity' }}
								className="flex gap-3 sm:gap-4 bg-white dark:bg-gray-900 p-2.5 sm:p-3 rounded-2xl border border-gray-200 dark:border-gray-800 transition-colors duration-300 shadow-sm dark:shadow-none transform-gpu"
							>
								<button
									type="button"
									onClick={() => handleOpenModal(item.variantId, item.product)}
									className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 shrink-0 transition-colors duration-300 cursor-pointer"
								>
									<img
										src={
											item.image ||
											'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
										}
										alt={item.name}
										className="w-full h-full object-cover"
										loading="lazy"
										decoding="async"
									/>
								</button>

								<div className="flex flex-col flex-1 justify-between">
									<div className="flex justify-between items-start">
										<div className="pr-2 flex flex-col">
											<h3 className="font-semibold text-xs sm:text-sm text-gray-900 dark:text-gray-200 leading-tight transition-colors duration-300 line-clamp-2">
												{item.name}
											</h3>
											{item.variantTitle && (
												<p className="text-[10px] sm:text-xs text-gray-500 mt-0.5 transition-colors duration-300 truncate">
													{item.variantTitle}
												</p>
											)}
											{stockStatus === 'IN_STOCK' && (
												<span className="text-[9px] sm:text-[10px] text-emerald-600 dark:text-emerald-400 font-bold bg-emerald-50 dark:bg-emerald-500/10 px-1.5 py-0.5 rounded-md w-fit mt-1">
													{t(productModal, 'in_stock', 'In Stock')}
												</span>
											)}
											{stockStatus === 'LOW_STOCK' && (
												<span className="text-[9px] sm:text-[10px] text-amber-600 dark:text-amber-400 font-bold bg-amber-50 dark:bg-amber-500/10 px-1.5 py-0.5 rounded-md w-fit mt-1">
													{t(productModal, 'low_stock', 'Low Stock')}
												</span>
											)}
											{stockStatus === 'OUT_OF_STOCK' && (
												<span className="text-[9px] sm:text-[10px] text-rose-600 dark:text-rose-400 font-bold bg-rose-50 dark:bg-rose-500/10 px-1.5 py-0.5 rounded-md w-fit mt-1">
													{t(productModal, 'out_of_stock', 'Out of Stock')}
												</span>
											)}
										</div>
										<button
											onClick={() => removeFromCart({ variantId: item.variantId })}
											className="p-1 -mr-1 -mt-1 text-gray-400 hover:text-rose-500 dark:text-gray-500 dark:hover:text-rose-400 transition-colors cursor-pointer flex-shrink-0"
										>
											<Trash2 size={14} className="sm:w-4 sm:h-4" />
										</button>
									</div>

									<div className="flex items-center justify-between mt-1">
										<div className="flex items-baseline gap-1">
											<span className="font-bold text-sm sm:text-base text-blue-600 dark:text-blue-400 transition-colors duration-300">
												${item.price.toFixed(2)}
											</span>
											{item.quantity > 1 && (
												<span className="text-[10px] sm:text-xs font-medium text-gray-400 dark:text-gray-500">
													(${lineItemTotal.toFixed(2)})
												</span>
											)}
										</div>

										<QuantityControl
											quantity={item.quantity}
											variantId={item.variantId}
											disabled={isUpdating}
											onUpdateExact={handleUpdateExactQuantity}
											onRemove={() => removeFromCart({ variantId: item.variantId })}
										/>
									</div>
								</div>
							</motion.div>
						);
					})}

					<div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-3 sm:p-4 mt-2 transition-colors duration-300 shadow-sm dark:shadow-none">
						<div className="flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3 text-xs sm:text-sm font-semibold text-gray-900 dark:text-gray-200 transition-colors duration-300">
							<Tag size={14} className="text-blue-500 sm:w-4 sm:h-4" />
							{t(tPromo, 'header', 'Promo Code')}
						</div>

						{appliedPromo && totals?.isPromoValid ? (
							<div className="flex items-center justify-between bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 p-2 sm:p-3 rounded-xl transition-colors duration-300">
								<div>
									<span className="text-xs sm:text-sm font-bold text-blue-600 dark:text-blue-400 transition-colors duration-300">
										{appliedPromo}
									</span>
									<span className="text-[10px] sm:text-xs text-blue-500/80 ml-1.5 sm:ml-2">
										{t(tPromo, 'applied', 'Applied')}
									</span>
								</div>
								<button
									onClick={handleRemovePromo}
									className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-500 dark:text-blue-400 flex items-center justify-center hover:bg-blue-200 dark:hover:bg-blue-500/30 transition-colors cursor-pointer"
								>
									<X size={12} className="sm:w-3.5 sm:h-3.5" />
								</button>
							</div>
						) : (
							<div className="flex gap-1.5 sm:gap-2">
								<input
									type="text"
									placeholder={t(tPromo, 'placeholder', 'Enter promo code')}
									value={promoInput}
									onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
									className="flex-1 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-xl px-3 py-2 sm:px-4 sm:py-2.5 text-xs sm:text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-600 focus:outline-none focus:border-blue-500 transition-colors uppercase"
								/>
								<button
									onClick={handleApplyPromo}
									className="px-3 py-2 sm:px-4 sm:py-2.5 bg-gray-900 dark:bg-gray-800 hover:bg-gray-800 dark:hover:bg-gray-700 text-white rounded-xl text-xs sm:text-sm font-medium transition-colors cursor-pointer"
								>
									{t(tPromo, 'apply', 'Apply')}
								</button>
							</div>
						)}

						{promoError && (
							<p className="text-[10px] sm:text-xs text-rose-500 mt-1.5 sm:mt-2">{promoError}</p>
						)}
						{promoSuccess && (
							<p className="text-[10px] sm:text-xs text-emerald-500 mt-1.5 sm:mt-2">
								{promoSuccess}
							</p>
						)}
					</div>
				</div>

				<div className="bg-white dark:bg-gray-900 p-3 sm:p-4 border-t border-gray-200 dark:border-gray-800 sticky bottom-0 z-10 transition-colors duration-300">
					<div className="max-w-4xl mx-auto w-full">
						{appliedPromo && totals?.isPromoValid && (
							<>
								<div className="flex justify-between items-center mb-1.5 transition-colors duration-300">
									<span className="text-gray-500 dark:text-gray-400 text-xs sm:text-sm">
										{t(cartConfig, 'subtotal', 'Subtotal')}
									</span>
									<span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300">
										${subtotalValue.toFixed(2)}
									</span>
								</div>
								<div className="flex justify-between items-center mb-1.5 transition-colors duration-300">
									<span className="text-emerald-500 dark:text-emerald-400 text-xs sm:text-sm">
										{t(cartConfig, 'discount', 'Discount')}
									</span>
									<span className="text-xs sm:text-sm text-emerald-500 dark:text-emerald-400">
										-${(totals?.discountAmount || 0).toFixed(2)}
									</span>
								</div>
							</>
						)}

						<div className="flex justify-between items-center mb-3 sm:mb-4 transition-colors duration-300">
							<span className="text-gray-500 dark:text-gray-400 text-xs sm:text-sm">
								{t(cartConfig, 'shipping', 'Shipping')}
							</span>
							{requiresAddress ? (
								<span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300">
									{t(cartConfig, 'calculated_at_checkout', 'Calculated at checkout')}
								</span>
							) : isFreeShipping ? (
								<span className="text-xs sm:text-sm font-medium text-green-500 dark:text-green-400">
									{t(cartConfig, 'free', 'FREE')}
								</span>
							) : (
								<span className="text-xs sm:text-sm text-gray-700 dark:text-gray-300">
									${shippingCost.toFixed(2)}
								</span>
							)}
						</div>

						<div className="flex justify-between items-center mb-3 sm:mb-4 transition-colors duration-300">
							<span className="text-gray-900 dark:text-gray-400 text-xs sm:text-sm font-semibold">
								{t(cartConfig, 'total', 'Total Amount')}
							</span>
							<span className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
								${finalTotal.toFixed(2)}
							</span>
						</div>

						<button
							onClick={() => {
								if (appliedPromo && totals?.isPromoValid) {
									sessionStorage.setItem('applied_promo_checkout', appliedPromo);
								}
								navigate('/checkout', {
									state: { promoCode: totals?.isPromoValid ? appliedPromo : undefined },
								});
							}}
							className="w-full py-3 sm:py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-lg shadow-blue-600/20 dark:shadow-blue-900/20"
						>
							{t(cartConfig, 'checkout', 'Proceed to Checkout')}{' '}
							<ArrowRight size={16} className="sm:w-4 sm:h-4" />
						</button>
					</div>
				</div>
			</div>

			{selectedProduct && <ProductModal product={selectedProduct} onClose={handleCloseModal} />}
		</>
	);
}

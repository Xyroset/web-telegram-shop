import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import WebApp from '@twa-dev/sdk';
import {
	X,
	Package,
	Truck,
	CreditCard,
	ChevronDown,
	ChevronUp,
	ExternalLink,
	MapPin,
	Tag,
	Copy,
} from 'lucide-react';

import { useTransactions } from '@/hooks/queries/useTransactions';
import { useDeliveryData } from '@/hooks/queries/useDelivery';
import { useConfig } from '@/store/ConfigContext';
import { OrderModalSkeleton } from '@/components/skeletons/OrderModalSkeleton';
import type { OrderModel, OrderItemModel } from '@/types/order';

interface OrderModalProps {
	order: OrderModel;
	onClose: () => void;
}

const t = (dict: Record<string, unknown> | undefined, key: string, fallback: string): string => {
	return dict && typeof dict[key] === 'string' ? (dict[key] as string) : fallback;
};

const getTxStatusVisuals = (status: string) => {
	const normalized = String(status).toLowerCase();
	switch (normalized) {
		case 'paid':
			return {
				color: 'text-emerald-600 dark:text-emerald-400',
				bg: 'bg-emerald-50 dark:bg-emerald-400/10',
			};
		case 'pending':
		case 'partially_paid':
		case 'wrong_amount':
			return {
				color: 'text-yellow-600 dark:text-yellow-400',
				bg: 'bg-yellow-50 dark:bg-yellow-400/10',
			};
		case 'cancelled':
		case 'expired':
		case 'failed':
		case 'refunded':
			return { color: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-50 dark:bg-rose-400/10' };
		default:
			return { color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-50 dark:bg-gray-400/10' };
	}
};

export function OrderModal({ order, onClose }: OrderModalProps) {
	const navigate = useNavigate();
	const { config } = useConfig();

	const modalConfig = (config?.translations as Record<string, unknown>)?.order_modal as
		| Record<string, unknown>
		| undefined;
	const ordersConfig = (config?.translations as Record<string, unknown>)?.orders_page as  // eslint-disable-next-line @typescript-eslint/no-explicit-any
		| Record<string, any>
		| undefined;
	const txStatusesConfig = modalConfig?.tx_statuses as Record<string, unknown> | undefined;

	const { deliveryData, isLoading: isDeliveryLoading } = useDeliveryData(order.id);
	const { transactions, isLoading: isTxLoading } = useTransactions(order.id);

	const [isItemsOpen, setIsItemsOpen] = useState(true);
	const [isTxOpen, setIsTxOpen] = useState(false);

	const isInitialLoading = isDeliveryLoading && isTxLoading;

	const handleProductClick = (productId: string | number, variantId: string | number) => {
		onClose();
		navigate(`/?product=${productId}&variant=${variantId}`, {
			replace: true,
		});
	};

	const copyToClipboard = (text: string) => {
		navigator.clipboard.writeText(text);
	};

	const handlePayClick = () => {
		if (!order.payloadUrl) return;
		try {
			WebApp.openLink(order.payloadUrl);
		} catch {
			window.open(order.payloadUrl, '_blank', 'noopener,noreferrer');
		}
	};

	const translatedOrderStatus = t(ordersConfig?.statuses, order.status, order.status);
	const isPending = order.status.toLowerCase() === 'pending';

	if (isInitialLoading) {
		return <OrderModalSkeleton onClose={onClose} />;
	}

	return (
		<AnimatePresence>
			<motion.div
				initial={{ opacity: 0 }}
				animate={{ opacity: 1 }}
				exit={{ opacity: 0 }}
				className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 dark:bg-gray-950/80 p-0 sm:p-4"
				onClick={onClose}
			>
				<motion.div
					initial={{ y: '100%' }}
					animate={{ y: 0 }}
					exit={{ y: '100%' }}
					transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
					style={{ willChange: 'transform, opacity' }}
					onClick={(e) => e.stopPropagation()}
					className="w-full h-[100dvh] rounded-none sm:h-auto sm:max-h-[90vh] sm:max-w-xl bg-white dark:bg-gray-950 sm:rounded-3xl border border-gray-200 dark:border-gray-800 overflow-hidden flex flex-col relative sm:shadow-2xl mt-auto sm:mt-0"
				>
					<div className="absolute top-4 right-4 z-10">
						<button
							onClick={onClose}
							className="w-8 h-8 bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
						>
							<X size={16} />
						</button>
					</div>

					<div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5 [&::-webkit-scrollbar]:hidden">
						{/* Basic Order Info */}
						<div className="pt-6 sm:pt-0">
							<h2 className="text-lg font-bold text-gray-900 dark:text-white mb-3">
								{t(modalConfig, 'title', 'Order Details')}
							</h2>
							<div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-3">
								<div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-800/60 pb-2">
									<span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										{t(modalConfig, 'order_id', 'Order ID')}
									</span>
									<div className="flex items-center gap-2">
										<span className="text-xs font-mono text-gray-700 dark:text-gray-300">
											{order.id.slice(0, 18)}...
										</span>
										<button
											onClick={() => copyToClipboard(order.id)}
											className="text-gray-400 hover:text-gray-900 dark:text-gray-500 dark:hover:text-white transition-colors cursor-pointer"
										>
											<Copy size={12} />
										</button>
									</div>
								</div>
								<div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-800/60 pb-2">
									<span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										{t(modalConfig, 'date', 'Date')}
									</span>
									<span className="text-xs text-gray-700 dark:text-gray-300">{order.date}</span>
								</div>
								<div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-800/60 pb-2">
									<span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										{t(modalConfig, 'total', 'Total Amount')}
									</span>
									<span className="text-sm font-bold text-gray-900 dark:text-white">
										${order.total.toFixed(2)}
									</span>
								</div>
								<div className="flex justify-between items-center">
									<span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										{t(modalConfig, 'order_status', 'Status')}
									</span>
									<span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-700">
										{translatedOrderStatus}
									</span>
								</div>

								{/* Pay Now Button if Pending */}
								{isPending && order.payloadUrl && (
									<div className="pt-2 border-t border-gray-200 dark:border-gray-800/60">
										<button
											onClick={handlePayClick}
											className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-lg cursor-pointer"
										>
											{t(modalConfig, 'pay_now', 'Complete Payment')} <ExternalLink size={16} />
										</button>
									</div>
								)}
							</div>
						</div>

						{/* Promocode */}
						{order.promocode && (
							<div className="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 rounded-xl p-3 flex items-center justify-between gap-2">
								<div className="flex items-center gap-2">
									<Tag size={16} className="text-blue-600 dark:text-blue-400" />
									<span className="text-xs text-blue-600 dark:text-blue-400">
										{t(modalConfig, 'promocode', 'Applied Promo Code')}
									</span>
								</div>
								<span className="text-xs font-bold text-blue-700 dark:text-blue-400 bg-blue-100 dark:bg-blue-500/20 px-2 py-1 rounded-md">
									{/* @ts-expect-error - Fallback depending on DTO shape */}
									{order.promocode.code || order.promocode}
								</span>
							</div>
						)}

						{/* Delivery Info */}
						<div>
							<h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
								<Truck size={14} /> {t(modalConfig, 'delivery_info', 'Delivery Information')}
							</h3>
							<div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
								{deliveryData ? (
									<div className="space-y-3">
										{deliveryData.deliveryData?.address_line && (
											<div className="flex items-start gap-2">
												<MapPin
													size={14}
													className="text-gray-400 dark:text-gray-500 mt-0.5 shrink-0"
												/>
												<span className="text-xs text-gray-700 dark:text-gray-300 leading-snug">
													{deliveryData.deliveryData.address_line},{' '}
													{deliveryData.deliveryData.destination_code}
													{deliveryData.deliveryData.region_code
														? ', ' + deliveryData.deliveryData.region_code
														: ''}
												</span>
											</div>
										)}
										{deliveryData.trackingNumber && (
											<div className="flex justify-between items-center border-t border-gray-200 dark:border-gray-800/60 pt-2">
												<span className="text-xs text-gray-500">
													{t(modalConfig, 'tracking_number', 'Tracking Number')}
												</span>
												<span className="text-xs font-mono font-medium text-blue-600 dark:text-blue-400">
													{deliveryData.trackingNumber}
												</span>
											</div>
										)}
										{deliveryData.providerCode && (
											<div className="flex justify-between items-center border-t border-gray-200 dark:border-gray-800/60 pt-2">
												<span className="text-xs text-gray-500">
													{t(modalConfig, 'provider', 'Provider')}
												</span>
												<span className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase">
													{deliveryData.providerCode}
												</span>
											</div>
										)}
									</div>
								) : (
									<span className="text-xs text-gray-500">
										Digital order / No delivery required
									</span>
								)}
							</div>
						</div>

						{/* Order Items */}
						<div>
							<button
								onClick={() => setIsItemsOpen(!isItemsOpen)}
								className="w-full flex items-center justify-between text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 cursor-pointer"
							>
								<span className="flex items-center gap-1.5">
									<Package size={14} /> {t(modalConfig, 'items_title', 'Order Items')}
								</span>
								{isItemsOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
							</button>

							<AnimatePresence>
								{isItemsOpen && (
									<motion.div
										initial={{ height: 0, opacity: 0 }}
										animate={{ height: 'auto', opacity: 1 }}
										exit={{ height: 0, opacity: 0 }}
										className="space-y-2 overflow-hidden"
									>
										{order.items.map((item: OrderItemModel) => (
											<div
												key={item.id}
												className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-2.5 flex items-center gap-3"
											>
												<div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-gray-800 overflow-hidden shrink-0 border border-gray-200 dark:border-transparent">
													<img
														src={
															item.image ||
															'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
														}
														alt={item.variantTitle}
														className="w-full h-full object-cover"
													/>
												</div>
												<div className="flex-1 min-w-0">
													<h4 className="text-xs font-medium text-gray-900 dark:text-gray-200 truncate">
														{item.variantTitle}
													</h4>
													<div className="text-[10px] text-gray-500 mt-0.5">
														{item.quantity}x • ${item.fixedPrice.toFixed(2)}{' '}
														{t(modalConfig, 'price_per_unit', 'each')}
													</div>
												</div>
												<button
													onClick={() => handleProductClick(item.productId, item.variantId)}
													className="w-8 h-8 flex items-center justify-center bg-gray-200 dark:bg-gray-800 text-blue-600 dark:text-blue-400 hover:bg-gray-300 dark:hover:bg-gray-700 hover:text-blue-700 dark:hover:text-blue-300 rounded-lg transition-colors cursor-pointer shrink-0"
													title={t(modalConfig, 'leave_review', 'Leave a review / View product')}
												>
													<ExternalLink size={14} />
												</button>
											</div>
										))}
									</motion.div>
								)}
							</AnimatePresence>
						</div>

						{/* Transactions */}
						<div>
							<button
								onClick={() => setIsTxOpen(!isTxOpen)}
								className="w-full flex items-center justify-between text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 cursor-pointer"
							>
								<span className="flex items-center gap-1.5">
									<CreditCard size={14} /> {t(modalConfig, 'transactions_title', 'Transactions')}
								</span>
								{isTxOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
							</button>

							<AnimatePresence>
								{isTxOpen && (
									<motion.div
										initial={{ height: 0, opacity: 0 }}
										animate={{ height: 'auto', opacity: 1 }}
										exit={{ height: 0, opacity: 0 }}
										className="overflow-hidden"
									>
										{transactions.length > 0 ? (
											<div className="space-y-3">
												{transactions.map((tx) => {
													const txStyle = getTxStatusVisuals(tx.state);
													const translatedTxStatus = t(txStatusesConfig, tx.state, tx.state);

													return (
														<div
															key={tx.id}
															className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-3 space-y-2"
														>
															<div className="flex justify-between items-center border-b border-gray-200 dark:border-gray-800/60 pb-1.5">
																<span className="text-[10px] text-gray-500 font-mono">
																	{tx.id.split('-')[0]}...
																</span>
																<span
																	className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${txStyle.bg} ${txStyle.color}`}
																>
																	{translatedTxStatus}
																</span>
															</div>
															<div className="flex justify-between items-center">
																<span className="text-[10px] text-gray-500">
																	{t(modalConfig, 'tx_amount', 'Amount')}
																</span>
																<span className="text-xs font-medium text-gray-700 dark:text-gray-300">
																	{tx.amountCrypto} {tx.paymentCurrency.toUpperCase()}
																</span>
															</div>
															<div className="flex justify-between items-center">
																<span className="text-[10px] text-gray-500">
																	{t(modalConfig, 'tx_network', 'Network')}
																</span>
																<span className="text-[10px] bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 rounded">
																	{tx.network}
																</span>
															</div>
															{tx.txHash && (
																<div className="flex justify-between items-center border-t border-gray-200 dark:border-gray-800/60 pt-1.5 mt-1.5">
																	<span className="text-[10px] text-gray-500">
																		{t(modalConfig, 'tx_hash', 'Tx Hash')}
																	</span>
																	<span className="text-[10px] font-mono text-blue-600 dark:text-blue-400 truncate max-w-[120px]">
																		{tx.txHash}
																	</span>
																</div>
															)}
														</div>
													);
												})}
											</div>
										) : (
											<div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 text-center text-xs text-gray-500">
												{t(modalConfig, 'no_transactions', 'No transactions found.')}
											</div>
										)}
									</motion.div>
								)}
							</AnimatePresence>
						</div>
					</div>
				</motion.div>
			</motion.div>
		</AnimatePresence>
	);
}

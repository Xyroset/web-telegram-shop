import { useState, useMemo, useCallback, memo } from 'react';
import { motion } from 'framer-motion';
import {
	CheckCircle2,
	Clock,
	AlertCircle,
	Package,
	XCircle,
	ChevronLeft,
	ChevronRight,
	ChevronRight as ArrowRight,
} from 'lucide-react';

import { useSettings } from '@/hooks/queries/useUserSettings';
import { useOrders } from '@/hooks/queries/useOrders';
import { useConfig } from '@/store/ConfigContext';
import type { OrderModel } from '@/types/order';
import { OrderModal } from '@/components/OrderModal';
import { OrderResponseStateEnum } from '@/api/models/OrderResponseStateEnum';
import { OrdersSkeleton } from '@/components/skeletons/OrdersSkeleton';

const t = (dict: Record<string, unknown> | undefined, key: string, fallback: string): string => {
	return dict && typeof dict[key] === 'string' ? (dict[key] as string) : fallback;
};

const getStatusVisuals = (status: string) => {
	const normalized = String(status).toLowerCase();
	switch (normalized) {
		case 'paid':
			return {
				icon: <CheckCircle2 size={14} />,
				color: 'text-emerald-600 dark:text-emerald-400',
				bg: 'bg-emerald-500/10 dark:bg-emerald-400/10',
				border: 'border-emerald-500/20 dark:border-emerald-400/20',
			};
		case 'pending':
			return {
				icon: <Clock size={14} />,
				color: 'text-yellow-600 dark:text-yellow-400',
				bg: 'bg-yellow-500/10 dark:bg-yellow-400/10',
				border: 'border-yellow-500/20 dark:border-yellow-400/20',
			};
		case 'cancelled':
			return {
				icon: <XCircle size={14} />,
				color: 'text-gray-600 dark:text-gray-400',
				bg: 'bg-gray-500/10 dark:bg-gray-400/10',
				border: 'border-gray-500/20 dark:border-gray-400/20',
			};
		case 'expired':
			return {
				icon: <AlertCircle size={14} />,
				color: 'text-red-600 dark:text-red-400',
				bg: 'bg-red-500/10 dark:bg-red-400/10',
				border: 'border-red-500/20 dark:border-red-400/20',
			};
		case 'failed':
			return {
				icon: <XCircle size={14} />,
				color: 'text-rose-600 dark:text-rose-400',
				bg: 'bg-rose-500/10 dark:bg-rose-400/10',
				border: 'border-rose-500/20 dark:border-rose-400/20',
			};
		default:
			return {
				icon: <Clock size={14} />,
				color: 'text-gray-600 dark:text-gray-400',
				bg: 'bg-gray-500/10 dark:bg-gray-400/10',
				border: 'border-gray-500/20 dark:border-gray-400/20',
			};
	}
};

interface OrderCardProps {
	order: OrderModel;
	isPending: boolean;
	onCancel: (orderId: string) => void;
	onOpenDetails: (order: OrderModel) => void;
	ordersConfig: Record<string, unknown> | undefined;
	statusesConfig: Record<string, unknown> | undefined;
	buttonsConfig: Record<string, unknown> | undefined;
}

const OrderCard = memo(
	({
		order,
		isPending,
		onCancel,
		onOpenDetails,
		ordersConfig,
		statusesConfig,
		buttonsConfig,
	}: OrderCardProps) => {
		const visuals = getStatusVisuals(order.status);
		const translatedStatus = t(statusesConfig, order.status, order.status);
		const itemsCount = order.items.reduce((acc, item) => acc + (item.quantity || 1), 0);
		const itemsText =
			itemsCount === 1
				? t(ordersConfig, 'items_count_single', '1 item')
				: t(ordersConfig, 'items_count_plural', '{count} items').replace(
						'{count}',
						String(itemsCount),
					);

		return (
			<motion.div
				initial={{ opacity: 0, y: 10 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
				style={{ willChange: 'transform, opacity' }}
				className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-3.5 flex flex-col gap-3 shadow-sm transform-gpu"
			>
				<div className="flex justify-between items-start border-b border-gray-200 dark:border-gray-800/60 pb-2.5">
					<div>
						<div className="text-gray-900 dark:text-white text-sm font-bold mb-0.5">
							{t(ordersConfig, 'order_number', 'Order')} #{order.id.slice(0, 8)}
						</div>
						<div className="text-[11px] text-gray-500">{order.date}</div>
					</div>
					<div
						className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider border ${visuals.bg} ${visuals.color} ${visuals.border}`}
					>
						{visuals.icon}
						{translatedStatus}
					</div>
				</div>

				<div className="flex items-center justify-between py-1">
					<div className="flex -space-x-2 overflow-hidden">
						{order.items.slice(0, 3).map((item, i) => (
							<img
								key={item.id || i}
								src={
									item.image || 'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
								}
								alt={item.productName}
								decoding="async"
								loading="lazy"
								className="inline-block h-8 w-8 rounded-full ring-2 ring-white dark:ring-gray-900 object-cover bg-gray-100 dark:bg-gray-800"
							/>
						))}
						{order.items.length > 3 && (
							<div className="flex items-center justify-center h-8 w-8 rounded-full ring-2 ring-white dark:ring-gray-900 bg-gray-100 dark:bg-gray-800 text-[10px] font-medium text-gray-600 dark:text-gray-400">
								+{order.items.length - 3}
							</div>
						)}
					</div>
					<div className="text-right">
						<div className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">{itemsText}</div>
						<div className="font-bold text-sm text-gray-900 dark:text-white">
							${order.total.toFixed(2)}
						</div>
					</div>
				</div>

				<div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-800/60">
					{isPending && (
						<button
							onClick={() => onCancel(order.id)}
							className="flex-1 py-2 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-lg font-medium text-xs transition-colors cursor-pointer"
						>
							{t(buttonsConfig, 'cancel', 'Cancel')}
						</button>
					)}
					<button
						onClick={() => onOpenDetails(order)}
						className={`py-2 rounded-lg font-medium text-xs transition-colors flex items-center justify-center gap-1 cursor-pointer ${
							isPending
								? 'flex-[2] bg-blue-600 hover:bg-blue-700 text-white'
								: 'w-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200'
						}`}
					>
						{t(buttonsConfig, 'details', 'View Details')} <ArrowRight size={14} />
					</button>
				</div>
			</motion.div>
		);
	},
);

OrderCard.displayName = 'OrderCard';

export function Orders() {
	const { config } = useConfig();
	const { settings } = useSettings();

	const ordersConfig = (config?.translations as Record<string, unknown>)?.orders_page as
		| Record<string, unknown>
		| undefined;
	const statusesConfig = ordersConfig?.statuses as Record<string, unknown> | undefined;
	const buttonsConfig = ordersConfig?.buttons as Record<string, unknown> | undefined;
	const messagesConfig = ordersConfig?.messages as Record<string, unknown> | undefined;

	const [currentCursor, setCurrentCursor] = useState<string | undefined>(undefined);

	const {
		orders,
		nextCursor,
		previousCursor,
		isLoading,
		isError,
		cancelOrder,
		isCancelling,
		refetchOrders,
	} = useOrders(currentCursor, settings?.language_code);

	const [actionMessage, setActionMessage] = useState<{
		type: 'success' | 'error';
		text: string;
	} | null>(null);

	const [selectedOrder, setSelectedOrder] = useState<OrderModel | null>(null);

	const pendingOrders = useMemo(
		() => orders.filter((o) => o.status === OrderResponseStateEnum.PENDING),
		[orders],
	);
	const historyOrders = useMemo(
		() => orders.filter((o) => o.status !== OrderResponseStateEnum.PENDING),
		[orders],
	);

	const handleNextPage = useCallback(() => {
		if (nextCursor) {
			setCurrentCursor(nextCursor);
		}
	}, [nextCursor]);

	const handlePrevPage = useCallback(() => {
		setCurrentCursor(previousCursor ?? undefined);
	}, [previousCursor]);

	const handleCancelOrder = useCallback(
		async (orderId: string) => {
			setActionMessage(null);
			try {
				await cancelOrder({ orderId });
				await refetchOrders();
				setActionMessage({
					type: 'success',
					text: t(messagesConfig, 'cancel_success', 'Order cancelled successfully.'),
				});
			} catch {
				setActionMessage({
					type: 'error',
					text: t(messagesConfig, 'cancel_error', 'Failed to cancel order.'),
				});
			}
		},
		[cancelOrder, refetchOrders, messagesConfig],
	);

	const handleOpenDetails = useCallback((order: OrderModel) => {
		setSelectedOrder(order);
	}, []);

	const handleCloseDetails = useCallback(() => {
		setSelectedOrder(null);
	}, []);

	if (isLoading && !orders.length) {
		return <OrdersSkeleton />;
	}

	if (isError) {
		return (
			<div className="text-center text-red-500 p-10 text-sm font-medium">
				{t(messagesConfig, 'error', 'Failed to load orders.')}
			</div>
		);
	}

	const hasNoOrdersAtAll =
		pendingOrders.length === 0 && historyOrders.length === 0 && !currentCursor && !nextCursor;

	return (
		<div
			className={`p-3 sm:p-4 max-w-3xl mx-auto w-full pb-[100px] transition-opacity duration-300 ${
				isCancelling ? 'opacity-50 pointer-events-none' : ''
			}`}
		>
			{actionMessage && (
				<div
					className={`mb-4 rounded-xl border px-3 py-2.5 text-xs font-medium text-center shadow-sm ${
						actionMessage.type === 'success'
							? 'border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
							: 'border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400'
					}`}
				>
					{actionMessage.text}
				</div>
			)}

			{hasNoOrdersAtAll ? (
				<div className="text-center text-gray-500 py-20 flex flex-col items-center">
					<Package size={40} className="mb-3 opacity-20" />
					<h3 className="text-base font-bold text-gray-900 dark:text-white mb-1">
						{t(ordersConfig, 'empty_all', "You haven't placed any orders yet.")}
					</h3>
				</div>
			) : (
				<div className="space-y-6">
					{pendingOrders.length > 0 && (
						<div className="space-y-3">
							<h2 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5 ml-1">
								<Clock size={14} className="text-yellow-600 dark:text-yellow-500" />
								{t(ordersConfig, 'pending_section', 'Awaiting Payment')}
							</h2>
							<div className="flex flex-col gap-3">
								{pendingOrders.map((order) => (
									<OrderCard
										key={order.id}
										order={order}
										isPending={true}
										onCancel={handleCancelOrder}
										onOpenDetails={handleOpenDetails}
										ordersConfig={ordersConfig}
										statusesConfig={statusesConfig}
										buttonsConfig={buttonsConfig}
									/>
								))}
							</div>
						</div>
					)}

					{historyOrders.length > 0 && (
						<div className="space-y-3">
							<h2 className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5 ml-1">
								<Package size={14} />
								{t(ordersConfig, 'history_section', 'Order History')}
							</h2>
							<div className="flex flex-col gap-3">
								{historyOrders.map((order) => (
									<OrderCard
										key={order.id}
										order={order}
										isPending={false}
										onCancel={handleCancelOrder}
										onOpenDetails={handleOpenDetails}
										ordersConfig={ordersConfig}
										statusesConfig={statusesConfig}
										buttonsConfig={buttonsConfig}
									/>
								))}
							</div>
						</div>
					)}

					{(nextCursor || currentCursor) && (
						<div className="flex items-center justify-between pt-2">
							<button
								onClick={handlePrevPage}
								disabled={!currentCursor}
								className="flex items-center gap-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors cursor-pointer"
							>
								<ChevronLeft size={14} /> {t(buttonsConfig, 'previous', 'Previous')}
							</button>
							<button
								onClick={handleNextPage}
								disabled={!nextCursor}
								className="flex items-center gap-1 px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-xl text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors cursor-pointer"
							>
								{t(buttonsConfig, 'next', 'Next')} <ChevronRight size={14} />
							</button>
						</div>
					)}
				</div>
			)}

			{selectedOrder && <OrderModal order={selectedOrder} onClose={handleCloseDetails} />}
		</div>
	);
}

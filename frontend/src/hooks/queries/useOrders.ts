import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { OrderService } from '@/api/services/OrderService';
import type { OrderResponse } from '@/api/models/OrderResponse';
import { OrderResponseStateEnum } from '@/api/models/OrderResponseStateEnum';
import type { OrderModel, OrderItemModel, CancelOrderCommand } from '@/types/order';

interface RawOrderItemDTO {
	id?: number | string;
	variant?: {
		id?: number;
		title?: string;
		image?: string;
		product?: {
			id?: number | string;
			name?: string;
		};
	};
	quantity?: number;
	fixed_price?: string;
}

const mapOrderResponseToDomain = (order: OrderResponse, lang: string): OrderModel => {
	return {
		id: String(order.id),
		date: new Date(order.created_at).toLocaleString(lang, {
			year: 'numeric',
			month: 'short',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
		}),
		total: parseFloat(order.amount_usd || '0'),
		status: order.state ?? OrderResponseStateEnum.PENDING,
		paidAt: order.paid_at ?? null,
		payloadUrl: order.payload_url ?? null,
		promocode: order.promocode ?? null,
		items: ((order.items as RawOrderItemDTO[]) || []).map(
			(item): OrderItemModel => ({
				id: String(item.id),
				variantId: Number(item.variant?.id),
				variantTitle: item.variant?.title || 'Unknown Variant',
				productId: String(item.variant?.product?.id || ''),
				productName: item.variant?.product?.name || 'Unknown Product',
				image: item.variant?.image || 'https://via.placeholder.com/100',
				quantity: item.quantity || 1,
				fixedPrice: parseFloat(item.fixed_price || '0'),
			}),
		),
	};
};

const getCursorFromUrl = (url?: string | null): string | null => {
	if (!url) return null;
	return new URL(url).searchParams.get('c');
};

export const useOrders = (cursor?: string, lang: string = 'en') => {
	const queryClient = useQueryClient();

	const ordersQuery = useQuery({
		queryKey: ['orders', cursor],
		queryFn: async () => {
			const res = await OrderService.ordersList(cursor);
			return {
				results: res.results.map((order: OrderResponse) => mapOrderResponseToDomain(order, lang)),
				nextCursor: getCursorFromUrl(res.next),
				previousCursor: getCursorFromUrl(res.previous),
			};
		},
	});

	const cancelOrderMutation = useMutation({
		mutationFn: async (command: CancelOrderCommand) => {
			return await OrderService.ordersUpdate(command.orderId);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['orders'] });
		},
	});

	return {
		orders: ordersQuery.data?.results || [],
		nextCursor: ordersQuery.data?.nextCursor || null,
		previousCursor: ordersQuery.data?.previousCursor || null,
		isLoading: ordersQuery.isLoading,
		isError: ordersQuery.isError,
		cancelOrder: cancelOrderMutation.mutateAsync,
		isCancelling: cancelOrderMutation.isPending,
		refetchOrders: ordersQuery.refetch,
	};
};

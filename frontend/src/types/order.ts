import type { OrderResponseStateEnum } from '@/api/models/OrderResponseStateEnum';
import type { PromoCode } from '@/api/models/PromoCode';

export interface OrderItemModel {
	id: string;
	variantId: number;
	variantTitle: string;
	productId: string;
	productName: string;
	image: string;
	quantity: number;
	fixedPrice: number;
}

export interface OrderModel {
	id: string;
	date: string;
	total: number;
	status: OrderResponseStateEnum;
	paidAt: string | null;
	payloadUrl: string | null;
	promocode: PromoCode | null;
	items: OrderItemModel[];
}

export interface CancelOrderCommand {
	orderId: string;
}

import type { Product } from '@/types/product';

export interface CartItem {
	id: string;
	variantId: number;
	name: string;
	quantity: number;
	price: number;
	image: string;
	variantTitle?: string;
	product: Product;
}

export interface CartTotals {
	subtotal: number;
	total: number;
	discountAmount: number;
	promocodeType?: string;
	isPromoValid?: boolean;
	promoError?: string;
}

export interface UpdateCartItemCommand {
	variantId: number;
	quantity: number;
}

export interface RemoveCartItemCommand {
	variantId: number;
}

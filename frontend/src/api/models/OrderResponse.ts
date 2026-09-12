/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OrderItem } from './OrderItem';
import type { OrderResponseStateEnum } from './OrderResponseStateEnum';
import type { PromoCode } from './PromoCode';
export type OrderResponse = {
	readonly id: string;
	amount_usd: string;
	state?: OrderResponseStateEnum;
	paid_at?: string | null;
	readonly created_at: string;
	readonly promocode: PromoCode;
	payload_url?: string | null;
	readonly items: Array<OrderItem>;
};

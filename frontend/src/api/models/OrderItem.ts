/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShortVariantProduct } from './ShortVariantProduct';
export type OrderItem = {
	readonly id: string;
	readonly variant: ShortVariantProduct;
	quantity?: number;
	fixed_price: string;
};

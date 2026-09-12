/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShortProduct } from './ShortProduct';
export type ShortVariantProduct = {
	readonly id: number;
	title: string;
	image?: string | null;
	price: string;
	old_price?: string | null;
	readonly product: ShortProduct;
	readonly stock_status: string;
};

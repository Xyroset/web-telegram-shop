/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Tag } from './Tag';
export type ProductVariantDetail = {
	readonly id: number;
	badge?: string | null;
	price: string;
	old_price?: string | null;
	title: string;
	image?: string | null;
	readonly stock_status: string;
	readonly is_new: boolean;
	readonly is_promotion: boolean;
	readonly promotion_discount: number;
	readonly basket_quantity: number;
	specific_description?: string | null;
	readonly tags: Array<Tag>;
	weight_kg?: string;
	length_cm?: string;
	width_cm?: string;
	height_cm?: string;
	readonly volumetric_weight_kg: number;
	/**
	 * Universal field
	 */
	metadata?: any;
};

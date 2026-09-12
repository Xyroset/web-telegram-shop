/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DiscountTypeEnum } from './DiscountTypeEnum';
export type PromoCode = {
	readonly id: string;
	code: string;
	discount_type?: DiscountTypeEnum;
	discount_percent?: number | null;
	discount_amount?: string | null;
};

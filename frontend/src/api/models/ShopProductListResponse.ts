/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Category } from './Category';
import type { Photo } from './Photo';
export type ShopProductListResponse = {
	readonly id: number;
	name: string;
	readonly category: Category;
	base_description?: string | null;
	readonly is_favorite: boolean;
	main_image?: string | null;
	attributes?: any;
	readonly video_source: string | null;
	readonly display_variant: Record<string, any> | null;
	readonly photos: Array<Photo>;
	is_active?: boolean;
	readonly average_rating: number;
	readonly purchases_count: number;
};

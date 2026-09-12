/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Category } from '../models/Category';
import type { PaginatedShopProductListResponseList } from '../models/PaginatedShopProductListResponseList';
import type { ProductSuggestionResponse } from '../models/ProductSuggestionResponse';
import type { ProductVariantDetail } from '../models/ProductVariantDetail';
import type { Tag } from '../models/Tag';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CatalogService {
	/**
	 * Get all categories
	 * API View for fetching categories.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates to `ProductRepository`.
	 * @returns Category
	 * @throws ApiError
	 */
	public static catalogCategoriesList(): CancelablePromise<Array<Category>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/categories/',
		});
	}
	/**
	 * Get product catalog
	 * API View for fetching the product catalog.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates data fetching to `ProductRepository` and uses `FavoriteItemRepository` for serializer context.
	 * @param category
	 * @param inStock
	 * @param isFavorite
	 * @param isNew
	 * @param isPromotion
	 * @param limit Number of results to return per page.
	 * @param maxPrice
	 * @param minDiscount
	 * @param minPrice
	 * @param minRating
	 * @param offset The initial index from which to return the results.
	 * @param ordering Ordering
	 *
	 * * `date` - Date
	 * * `-date` - Date (descending)
	 * * `price` - Price
	 * * `-price` - Price (descending)
	 * * `name` - Sort alphabetically
	 * * `-name` - Sort alphabetically (descending)
	 * @param productType * `PHYSICAL` - Physical
	 * * `DIGITAL` - Digital
	 * @param search
	 * @param strictSearch If true, disables Trigram fuzzy matching and uses exact/partial substring search only.
	 * @param tag
	 * @returns PaginatedShopProductListResponseList
	 * @throws ApiError
	 */
	public static catalogProductsList(
		category?: string,
		inStock?: boolean,
		isFavorite?: boolean,
		isNew?: boolean,
		isPromotion?: boolean,
		limit?: number,
		maxPrice?: number,
		minDiscount?: string,
		minPrice?: number,
		minRating?: number,
		offset?: number,
		ordering?: Array<'-date' | '-name' | '-price' | 'date' | 'name' | 'price'>,
		productType?: 'DIGITAL' | 'PHYSICAL',
		search?: string,
		strictSearch?: boolean,
		tag?: string,
	): CancelablePromise<PaginatedShopProductListResponseList> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/products/',
			query: {
				category: category,
				in_stock: inStock,
				is_favorite: isFavorite,
				is_new: isNew,
				is_promotion: isPromotion,
				limit: limit,
				max_price: maxPrice,
				min_discount: minDiscount,
				min_price: minPrice,
				min_rating: minRating,
				offset: offset,
				ordering: ordering,
				product_type: productType,
				search: search,
				strict_search: strictSearch,
				tag: tag,
			},
		});
	}
	/**
	 * Get search autocomplete suggestions
	 * API View for fetching fast autocomplete search suggestions.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates to `ProductRepository`'s hybrid search logic.
	 * @param search Search term for autocomplete suggestions.
	 * @param limit Maximum number of suggestions to return (default: 5).
	 * @returns ProductSuggestionResponse
	 * @throws ApiError
	 */
	public static catalogProductsSuggestionsList(
		search: string,
		limit?: number,
	): CancelablePromise<Array<ProductSuggestionResponse>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/products/suggestions/',
			query: {
				limit: limit,
				search: search,
			},
		});
	}
	/**
	 * Get all variants for a specific product
	 * API View for fetching product variants.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates to `ProductRepository` to fetch variants and `BasketRepository` to enrich context.
	 * @param productId
	 * @returns ProductVariantDetail
	 * @throws ApiError
	 */
	public static catalogProductsVariantsList(
		productId: number,
	): CancelablePromise<Array<ProductVariantDetail>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/products/variants/{product_id}/',
			path: {
				product_id: productId,
			},
		});
	}
	/**
	 * Get all tags
	 * API View for fetching tags.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates to `ProductRepository`.
	 * @returns Tag
	 * @throws ApiError
	 */
	public static catalogTagsList(): CancelablePromise<Array<Tag>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/tags/',
		});
	}
}

/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class FavoriteService {
	/**
	 * Add a product in user favorites
	 * API View for managing user's favorite products.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **POST**: Delegates creation to `CreateFavoriteItemCase`.
	 * - **DELETE**: Delegates deletion to `DeleteFavoriteItemCase`.
	 * @param productId
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static catalogFavoritesCreate(productId: number): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/catalog/favorites/{product_id}/',
			path: {
				product_id: productId,
			},
		});
	}
	/**
	 * Delete a product in user favorites
	 * API View for managing user's favorite products.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **POST**: Delegates creation to `CreateFavoriteItemCase`.
	 * - **DELETE**: Delegates deletion to `DeleteFavoriteItemCase`.
	 * @param productId
	 * @returns void
	 * @throws ApiError
	 */
	public static catalogFavoritesDestroy(productId: number): CancelablePromise<void> {
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/v1/catalog/favorites/{product_id}/',
			path: {
				product_id: productId,
			},
		});
	}
}

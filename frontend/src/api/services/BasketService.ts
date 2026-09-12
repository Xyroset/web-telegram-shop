/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BasketCalculatePriceResponse } from '../models/BasketCalculatePriceResponse';
import type { BasketShopUpdateRequestRequest } from '../models/BasketShopUpdateRequestRequest';
import type { BasketUpdatePageResponse } from '../models/BasketUpdatePageResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class BasketService {
	/**
	 * Receive the user's entire basket
	 * Handles retrieval of the user's entire basket and creation/updating of basket items.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Uses `BasketRepository` to fetch the user's basket items for listing.
	 * - **POST**: Delegates item creation or quantity updates to `BasketCreateUpdateItemCase`.
	 * @returns BasketUpdatePageResponse
	 * @throws ApiError
	 */
	public static basketList(): CancelablePromise<Array<BasketUpdatePageResponse>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/basket/',
		});
	}
	/**
	 * Update/Create a basket item
	 * Handles retrieval of the user's entire basket and creation/updating of basket items.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Uses `BasketRepository` to fetch the user's basket items for listing.
	 * - **POST**: Delegates item creation or quantity updates to `BasketCreateUpdateItemCase`.
	 * @param requestBody
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static basketCreate(requestBody: BasketShopUpdateRequestRequest): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/basket/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Delete a basket item
	 * Handles deletion of a specific basket item.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **DELETE**: Delegates item deletion to `BasketDeleteItemCase` using variant_id.
	 * @param variantId
	 * @returns void
	 * @throws ApiError
	 */
	public static basketDestroy(variantId: number): CancelablePromise<void> {
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/v1/basket/{variant_id}/',
			path: {
				variant_id: variantId,
			},
		});
	}
	/**
	 * Receive total price of the user's entire shopping basket
	 * Handles calculating the total price of the user's basket.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Computes basket totals including promo code discounts using `BasketCalculateCase`.
	 * @param promocode Optional promotional code to apply a discount
	 * @returns BasketCalculatePriceResponse
	 * @throws ApiError
	 */
	public static basketCalculateRetrieve(
		promocode?: string,
	): CancelablePromise<BasketCalculatePriceResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/basket/calculate/',
			query: {
				promocode: promocode,
			},
		});
	}
}

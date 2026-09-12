/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeliveryDataResponse } from '../models/DeliveryDataResponse';
import type { DeliveryEstimateResponse } from '../models/DeliveryEstimateResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DeliveryService {
	/**
	 * Get delivery data on order id
	 * API View to retrieve delivery details for a specific order.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only access delivery data associated with their own order.
	 *
	 * Delegation:
	 * - GET: Fetches delivery details directly via `DeliveryRepository` using `order_id` and `user`.
	 * @param orderId
	 * @returns DeliveryDataResponse
	 * @throws ApiError
	 */
	public static deliveryRetrieve(orderId: string): CancelablePromise<DeliveryDataResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/delivery/{order_id}',
			path: {
				order_id: orderId,
			},
		});
	}
	/**
	 * Calculate Delivery Estimate
	 * API View to retrieve estimated delivery costs and gamification thresholds.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - GET: Validates query parameters using `DeliveryEstimateRequestSerializer`,
	 * delegates calculation to `CalculateDeliveryEstimateCase`,
	 * and serializes the result with `DeliveryEstimateResponseSerializer`.
	 * @param destinationCode
	 * @param regionCode
	 * @returns DeliveryEstimateResponse
	 * @throws ApiError
	 */
	public static deliveryEstimateRetrieve(
		destinationCode?: string,
		regionCode?: string,
	): CancelablePromise<DeliveryEstimateResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/delivery/estimate/',
			query: {
				destination_code: destinationCode,
				region_code: regionCode,
			},
		});
	}
}

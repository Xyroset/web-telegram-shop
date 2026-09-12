/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OrderCreateRequestRequest } from '../models/OrderCreateRequestRequest';
import type { OrderCreateResponse } from '../models/OrderCreateResponse';
import type { OrderResponse } from '../models/OrderResponse';
import type { PaginatedOrderResponseList } from '../models/PaginatedOrderResponseList';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class OrderService {
	/**
	 * Receive user's entire list orders
	 * Handles listing of user's orders and creation of new orders.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only access or modify their own orders (Ownership check).
	 *
	 * Delegation:
	 * - **GET**: Uses `OrderRepository` to fetch the user's order queryset for pagination.
	 * - **POST**: Delegates order creation, product reservation, and invoice generation to `CreateOrderCase`
	 * @param c The pagination cursor value.
	 * @returns PaginatedOrderResponseList
	 * @throws ApiError
	 */
	public static ordersList(c?: string): CancelablePromise<PaginatedOrderResponseList> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/orders/',
			query: {
				c: c,
			},
		});
	}
	/**
	 * Create a new user order from user basket
	 * Handles listing of user's orders and creation of new orders.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only access or modify their own orders (Ownership check).
	 *
	 * Delegation:
	 * - **GET**: Uses `OrderRepository` to fetch the user's order queryset for pagination.
	 * - **POST**: Delegates order creation, product reservation, and invoice generation to `CreateOrderCase`
	 * @param requestBody
	 * @returns OrderCreateResponse
	 * @throws ApiError
	 */
	public static ordersCreate(
		requestBody?: OrderCreateRequestRequest,
	): CancelablePromise<OrderCreateResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/orders/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Get an order
	 * Handles retrieval and cancellation of a specific order.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Fetches a single order directly via `OrderRepository`
	 * - **PATCH**: Delegates the cancellation process (and side effects) to `CancelOrderCase`.
	 * @param orderId
	 * @returns OrderResponse
	 * @throws ApiError
	 */
	public static ordersRetrieve(orderId: string): CancelablePromise<OrderResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/orders/{order_id}/',
			path: {
				order_id: orderId,
			},
		});
	}
	/**
	 * Cancel an order
	 * Handles retrieval and cancellation of a specific order.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Fetches a single order directly via `OrderRepository`
	 * - **PATCH**: Delegates the cancellation process (and side effects) to `CancelOrderCase`.
	 * @param orderId
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static ordersUpdate(orderId: string): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/orders/{order_id}/',
			path: {
				order_id: orderId,
			},
		});
	}
}

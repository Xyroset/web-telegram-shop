/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateInvoiceRequestRequest } from '../models/CreateInvoiceRequestRequest';
import type { PaginatedTransactionResponseList } from '../models/PaginatedTransactionResponseList';
import type { TransactionCreateResponse } from '../models/TransactionCreateResponse';
import type { TransactionResponse } from '../models/TransactionResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PaymentService {
	/**
	 * Create a new payment invoice
	 * Handles payment transaction creation and invoice generation with external gateways.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **POST**: Validates input data via `CreateInvoiceRequestSerializer`, resolves gateway,
	 * and delegates orchestrations to `CreateInvoiceCase`.
	 * @param requestBody
	 * @returns TransactionCreateResponse
	 * @throws ApiError
	 */
	public static paymentsCreate(
		requestBody: CreateInvoiceRequestRequest,
	): CancelablePromise<TransactionCreateResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/payments/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Get a transaction
	 * Handles retrieving details and cancellation of a single payment transaction.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only view or cancel transactions associated with their own orders.
	 *
	 * Delegation:
	 * - **GET**: Uses `PaymentTransactionRepository` to fetch single transaction by ID and user ownership.
	 * - **PUT**: Delegates transaction cancellation and task revocation to `CancelTransactionCase`.
	 * @param transactionId
	 * @returns TransactionResponse
	 * @throws ApiError
	 */
	public static paymentsRetrieve(transactionId: string): CancelablePromise<TransactionResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/payments/{transaction_id}/',
			path: {
				transaction_id: transactionId,
			},
		});
	}
	/**
	 * Cancel user transaction
	 * Handles retrieving details and cancellation of a single payment transaction.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only view or cancel transactions associated with their own orders.
	 *
	 * Delegation:
	 * - **GET**: Uses `PaymentTransactionRepository` to fetch single transaction by ID and user ownership.
	 * - **PUT**: Delegates transaction cancellation and task revocation to `CancelTransactionCase`.
	 * @param transactionId
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static paymentsUpdate(transactionId: string): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/payments/{transaction_id}/',
			path: {
				transaction_id: transactionId,
			},
		});
	}
	/**
	 * Receive user's entire list transactions
	 * Handles retrieval of paginated payment transactions for a specific user's order.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 * - User can only view transactions associated with their own orders.
	 *
	 * Delegation:
	 * - **GET**: Uses `PaymentTransactionRepository` to fetch filtered QuerySet for pagination.
	 * @param orderId
	 * @param c The pagination cursor value.
	 * @returns PaginatedTransactionResponseList
	 * @throws ApiError
	 */
	public static paymentsOrderList(
		orderId: string,
		c?: string,
	): CancelablePromise<PaginatedTransactionResponseList> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/payments/order/{order_id}/',
			path: {
				order_id: orderId,
			},
			query: {
				c: c,
			},
		});
	}
}

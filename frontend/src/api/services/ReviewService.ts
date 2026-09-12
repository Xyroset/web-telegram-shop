/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginatedReviewList } from '../models/PaginatedReviewList';
import type { ReviewCreateRequestRequest } from '../models/ReviewCreateRequestRequest';
import type { ReviewUpdateRequestRequest } from '../models/ReviewUpdateRequestRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ReviewService {
	/**
	 * Create a new review
	 * API View for creating a product review.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **POST**: Validates multipart data via serializer, delegates business rules to `CreateReviewCase`.
	 * @param formData
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static catalogReviewsCreate(formData: ReviewCreateRequestRequest): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/catalog/reviews/',
			formData: formData,
			mediaType: 'multipart/form-data',
		});
	}
	/**
	 * Update an old review
	 * API View for updating or deleting a product review.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **PUT**: Validates payload, delegates to `UpdateReviewCase`.
	 * - **DELETE**: Delegates to `DeleteReviewCase`.
	 * @param id
	 * @param requestBody
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static catalogReviewsUpdate(
		id: string,
		requestBody?: ReviewUpdateRequestRequest,
	): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/catalog/reviews/{id}/',
			path: {
				id: id,
			},
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Delete a review
	 * API View for updating or deleting a product review.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **PUT**: Validates payload, delegates to `UpdateReviewCase`.
	 * - **DELETE**: Delegates to `DeleteReviewCase`.
	 * @param id
	 * @returns void
	 * @throws ApiError
	 */
	public static catalogReviewsDestroy(id: string): CancelablePromise<void> {
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/v1/catalog/reviews/{id}/',
			path: {
				id: id,
			},
		});
	}
	/**
	 * Get reviews
	 * API View for fetching product reviews.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates query construction to `GetReviewsCase`.
	 * @param productId
	 * @param c The pagination cursor value.
	 * @returns PaginatedReviewList
	 * @throws ApiError
	 */
	public static catalogReviewsList(
		productId: number,
		c?: string,
	): CancelablePromise<PaginatedReviewList> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/catalog/reviews/{product_id}/',
			path: {
				product_id: productId,
			},
			query: {
				c: c,
			},
		});
	}
}

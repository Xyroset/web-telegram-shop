/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserDeliveryDataRequestRequest } from '../models/UserDeliveryDataRequestRequest';
import type { UserDeliveryDataResponse } from '../models/UserDeliveryDataResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UserDeliveryDataService {
	/**
	 * Get user's delivery data
	 * API View for managing user delivery records collection.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **GET**: Retrieves list of delivery addresses via `UserDeliveryDataRepository`.
	 * - **POST**: Validates input data and delegates creation to `CreateUserDeliveryDataCase`.
	 * @returns UserDeliveryDataResponse
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataList(): CancelablePromise<Array<UserDeliveryDataResponse>> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/users/me/delivery_data/',
		});
	}
	/**
	 * Create a new user delivery data
	 * API View for managing user delivery records collection.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **GET**: Retrieves list of delivery addresses via `UserDeliveryDataRepository`.
	 * - **POST**: Validates input data and delegates creation to `CreateUserDeliveryDataCase`.
	 * @param requestBody
	 * @returns any Delivery data created successfully.
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataCreate(
		requestBody?: UserDeliveryDataRequestRequest,
	): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/users/me/delivery_data/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Update one item user delivery data
	 * API View for updating and deleting a specific delivery data entry.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **PUT**: Validates input data and delegates update to `UpdateUserDeliveryDataCase`.
	 * - **DELETE**: Delegates deletion to `DeleteUserDeliveryDataCase`.
	 * @param id
	 * @param requestBody
	 * @returns any Delivery data updated successfully.
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataDetailsUpdate(
		id: number,
		requestBody?: UserDeliveryDataRequestRequest,
	): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/users/me/delivery_data/details/{id}/',
			path: {
				id: id,
			},
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Delete one item user delivery data
	 * API View for updating and deleting a specific delivery data entry.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **PUT**: Validates input data and delegates update to `UpdateUserDeliveryDataCase`.
	 * - **DELETE**: Delegates deletion to `DeleteUserDeliveryDataCase`.
	 * @param id
	 * @returns void
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataDetailsDestroy(id: number): CancelablePromise<void> {
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/v1/users/me/delivery_data/details/{id}/',
			path: {
				id: id,
			},
		});
	}
	/**
	 * Set is current one item user delivery data
	 * API View for toggling the active status of a user's delivery address.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **PATCH**: Delegates marking the record as current to `SetCurrentUserDeliveryDataCase`.
	 * - **DELETE**: Delegates unsetting the record as current to `UnSetCurrentUserDeliveryDataCase`.
	 * @param id
	 * @returns any Delivery data marked as current.
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataManagementPartialUpdate(id: number): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PATCH',
			url: '/api/v1/users/me/delivery_data/management/{id}/',
			path: {
				id: id,
			},
		});
	}
	/**
	 * Unset is current one item user delivery data
	 * API View for toggling the active status of a user's delivery address.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **PATCH**: Delegates marking the record as current to `SetCurrentUserDeliveryDataCase`.
	 * - **DELETE**: Delegates unsetting the record as current to `UnSetCurrentUserDeliveryDataCase`.
	 * @param id
	 * @returns void
	 * @throws ApiError
	 */
	public static usersMeDeliveryDataManagementDestroy(id: number): CancelablePromise<void> {
		return __request(OpenAPI, {
			method: 'DELETE',
			url: '/api/v1/users/me/delivery_data/management/{id}/',
			path: {
				id: id,
			},
		});
	}
}

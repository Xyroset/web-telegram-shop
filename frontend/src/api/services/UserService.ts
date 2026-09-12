/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GetUserDataResponse } from '../models/GetUserDataResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UserService {
	/**
	 * Get current user data
	 * API View for retrieving the current authenticated user's profile.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **GET**: Returns the serialized profile of `request.user`.
	 * @returns GetUserDataResponse
	 * @throws ApiError
	 */
	public static usersMeRetrieve(): CancelablePromise<GetUserDataResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/users/me/',
		});
	}
}

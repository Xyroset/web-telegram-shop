/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateTicketRequestRequest } from '../models/CreateTicketRequestRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SupportService {
	/**
	 * Create support ticket for admin
	 * Handles customer support ticket creation.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **POST**: Validates input payload and delegates ticket creation and admin notification to `CreateTicketCase`.
	 * @param requestBody
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static supportCreate(requestBody: CreateTicketRequestRequest): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/support/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
}

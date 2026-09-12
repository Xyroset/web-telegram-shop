/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GetWebAppInitConfigResponse } from '../models/GetWebAppInitConfigResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConfigService {
	/**
	 * Get init data for WebApp
	 * Provides initial configuration payload for the WebApp.
	 *
	 * Permissions:
	 * - Requires an authenticated user.
	 *
	 * Delegation:
	 * - **GET**: Delegates config generation to `GetWebAppInitConfigCase`.
	 * @returns GetWebAppInitConfigResponse
	 * @throws ApiError
	 */
	public static coreConfigInitRetrieve(): CancelablePromise<GetWebAppInitConfigResponse> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/core/config/init/',
		});
	}
}

/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserSettings } from '../models/UserSettings';
import type { UserSettingsRequest } from '../models/UserSettingsRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UserSettingsService {
	/**
	 * Get current user settings
	 * API View for retrieving and updating user application settings.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **GET**: Fetches settings via `UserSettingsDataRepository` and serializes them.
	 * - **PUT**: Validates payload via `UserSettingsSerializer` and delegates update to `UpdateUserSettingsCase`.
	 * @returns UserSettings
	 * @throws ApiError
	 */
	public static usersMeSettingsRetrieve(): CancelablePromise<UserSettings> {
		return __request(OpenAPI, {
			method: 'GET',
			url: '/api/v1/users/me/settings/',
		});
	}
	/**
	 * Update user settings
	 * API View for retrieving and updating user application settings.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **GET**: Fetches settings via `UserSettingsDataRepository` and serializes them.
	 * - **PUT**: Validates payload via `UserSettingsSerializer` and delegates update to `UpdateUserSettingsCase`.
	 * @param requestBody
	 * @returns any Settings updated successfully.
	 * @throws ApiError
	 */
	public static usersMeSettingsUpdate(requestBody?: UserSettingsRequest): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/users/me/settings/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Reset user settings to default state
	 * API View for resetting user settings to system defaults.
	 *
	 * Permissions:
	 * - Requires an authenticated user (IsAuthenticated).
	 *
	 * Delegation:
	 * - **PUT**: Loads defaults from `shop_config` and delegates updates to `UpdateUserSettingsCase`.
	 * @returns any Settings reset to defaults successfully.
	 * @throws ApiError
	 */
	public static usersMeSettingsResetToDefaultUpdate(): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'PUT',
			url: '/api/v1/users/me/settings/reset_to_default/',
		});
	}
}

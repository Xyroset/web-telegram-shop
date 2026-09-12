/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CookieTokenRefresh } from '../models/CookieTokenRefresh';
import type { DevAuthRequestRequest } from '../models/DevAuthRequestRequest';
import type { TelegramAuthRequestRequest } from '../models/TelegramAuthRequestRequest';
import type { TelegramAuthResponse } from '../models/TelegramAuthResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
	/**
	 * DEV ONLY: Login without Telegram auth
	 * Creates or logs in a user using only tg_id. Disabled in production.
	 * @param requestBody
	 * @returns TelegramAuthResponse
	 * @throws ApiError
	 */
	public static usersAuthDevCreate(
		requestBody?: DevAuthRequestRequest,
	): CancelablePromise<TelegramAuthResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/users/auth/dev/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * User authorization via Telegram
	 * API View for user authorization via Telegram.
	 *
	 * Permissions:
	 * - Allows any user (AllowAny). Payload authenticity is verified via Telegram HMAC.
	 *
	 * Delegation:
	 * - **POST**: Validates Telegram init data via `ValidateInitTelegramDataCase`
	 * and delegates authentication/creation to `TelegramAuthUseCase`.
	 * @param requestBody
	 * @returns TelegramAuthResponse
	 * @throws ApiError
	 */
	public static usersAuthTelegramCreate(
		requestBody: TelegramAuthRequestRequest,
	): CancelablePromise<TelegramAuthResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/users/auth/telegram/',
			body: requestBody,
			mediaType: 'application/json',
		});
	}
	/**
	 * Update access token via HttpOnly Cookie
	 * API View for refreshing JWT access tokens.
	 *
	 * Permissions:
	 * - Allows any user (AllowAny).
	 *
	 * Delegation:
	 * - **POST**: Validates the HttpOnly refresh cookie via `CookieTokenRefreshSerializer` and issues a new access token.
	 * @returns CookieTokenRefresh
	 * @throws ApiError
	 */
	public static usersTokenRefreshCreate(): CancelablePromise<CookieTokenRefresh> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/users/token/refresh/',
		});
	}
}

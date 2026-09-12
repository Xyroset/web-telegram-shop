/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TelegramService {
	/**
	 * Webhook for Telegram API communication
	 * Endpoint for receiving inbound updates from Telegram.
	 *
	 * Permissions:
	 * - Allows any client (AllowAny).
	 * Request authenticity is verified securely via the X-Telegram-Bot-Api-Secret-Token header.
	 *
	 * Delegation:
	 * - **POST**: Validates the webhook secret token and delegates the payload to `ProcessTelegramWebhookCase`.
	 * @returns any No response body
	 * @throws ApiError
	 */
	public static webhookTelegramCreate(): CancelablePromise<any> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/webhook/telegram/',
		});
	}
}

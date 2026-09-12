/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseResponse } from '../models/BaseResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WebhookService {
	/**
	 * Webhook for gateway CryptoBot
	 * Handles incoming payment status updates from the CryptoBot (Crypto Pay) webhook.
	 *
	 * Permissions:
	 * - Allows any user (AllowAny). Signature validation is handled internally by the gateway.
	 *
	 * Delegation:
	 * - **POST**: Delegates webhook signature verification, state mutation, and side-effects to `ProcessWebhookCase`.
	 * @returns BaseResponse
	 * @throws ApiError
	 */
	public static paymentsCryptobotCreate(): CancelablePromise<BaseResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/payments/cryptobot/',
		});
	}
	/**
	 * Webhook for gateway nowpayments
	 * Handles incoming payment status updates from the NOWPayments webhook.
	 *
	 * Permissions:
	 * - Allows any user (AllowAny). Signature validation is handled internally by the gateway.
	 *
	 * Delegation:
	 * - **POST**: Delegates webhook signature verification, state mutation, and side-effects to `ProcessWebhookCase`.
	 * @returns BaseResponse
	 * @throws ApiError
	 */
	public static paymentsNowpaymentsCreate(): CancelablePromise<BaseResponse> {
		return __request(OpenAPI, {
			method: 'POST',
			url: '/api/v1/payments/nowpayments/',
		});
	}
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

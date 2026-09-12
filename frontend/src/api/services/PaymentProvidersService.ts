/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseResponse } from '../models/BaseResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PaymentProvidersService {
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
}

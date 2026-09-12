/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * * `pending` - Waiting for payment
 * * `paid` - Successfully paid
 * * `wrong_amount` - Paid wrong amount
 * * `partially_paid` - Partially paid
 * * `expired` - Invoice expired
 * * `cancelled` - Cancelled
 * * `failed` - Failed
 * * `refunded` - Refunded
 */
export enum TransactionResponseStateEnum {
	PENDING = 'pending',
	PAID = 'paid',
	WRONG_AMOUNT = 'wrong_amount',
	PARTIALLY_PAID = 'partially_paid',
	EXPIRED = 'expired',
	CANCELLED = 'cancelled',
	FAILED = 'failed',
	REFUNDED = 'refunded',
}

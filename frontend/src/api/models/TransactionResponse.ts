/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TransactionResponseStateEnum } from './TransactionResponseStateEnum';
export type TransactionResponse = {
	readonly id: string;
	state?: TransactionResponseStateEnum;
	order: string;
	readonly created_at: string;
	invoice_id?: string | null;
	payment_currency: string;
	network: string;
	target_amount_usd?: string;
	amount_crypto?: string;
	current_amount_crypto?: string;
	receiver_address?: string | null;
	sender_address?: string | null;
	tx_hash?: string | null;
	raw_response?: any;
};

import type { TransactionResponseStateEnum } from '@/api/models/TransactionResponseStateEnum';

export interface TransactionModel {
	id: string;
	date: string;
	state: TransactionResponseStateEnum;
	orderId: string;
	invoiceId: string | null;
	paymentCurrency: string;
	network: string;
	targetAmountUsd: string;
	amountCrypto: string;
	currentAmountCrypto: string;
	txHash: string | null;
}

export interface CancelTransactionCommand {
	transactionId: string;
}

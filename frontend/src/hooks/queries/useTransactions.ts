import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PaymentService } from '@/api/services/PaymentService';
import type { TransactionResponse } from '@/api/models/TransactionResponse';
import { TransactionResponseStateEnum } from '@/api/models/TransactionResponseStateEnum';
import type { TransactionModel, CancelTransactionCommand } from '@/types/transaction';

const mapTransactionResponseToDomain = (
	tx: TransactionResponse,
	lang: string,
): TransactionModel => {
	return {
		id: String(tx.id),
		date: new Date(tx.created_at).toLocaleString(lang, {
			year: 'numeric',
			month: 'short',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
		}),
		state: tx.state ?? TransactionResponseStateEnum.PENDING,
		orderId: String(tx.order),
		invoiceId: tx.invoice_id ?? null,
		paymentCurrency: tx.payment_currency || 'Unknown',
		network: tx.network || 'Unknown',
		targetAmountUsd: tx.target_amount_usd || '0',
		amountCrypto: tx.amount_crypto || '0',
		currentAmountCrypto: tx.current_amount_crypto || '0',
		txHash: tx.tx_hash ?? null,
	};
};

const getCursorFromUrl = (url?: string | null): string | null => {
	if (!url) return null;
	return new URL(url).searchParams.get('c');
};

export const useTransactions = (orderId: string, cursor?: string, lang: string = 'en') => {
	const queryClient = useQueryClient();

	const transactionsQuery = useQuery({
		queryKey: ['transactions', cursor],
		queryFn: async () => {
			const res = await PaymentService.paymentsOrderList(orderId, cursor);
			return {
				results: res.results.map((tx: TransactionResponse) =>
					mapTransactionResponseToDomain(tx, lang),
				),
				nextCursor: getCursorFromUrl(res.next),
				previousCursor: getCursorFromUrl(res.previous),
			};
		},
		enabled: !!orderId,
	});

	const cancelTransactionMutation = useMutation({
		mutationFn: async (command: CancelTransactionCommand) => {
			return await PaymentService.paymentsUpdate(command.transactionId);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['transactions'] });
		},
	});

	return {
		transactions: transactionsQuery.data?.results || [],
		nextCursor: transactionsQuery.data?.nextCursor || null,
		previousCursor: transactionsQuery.data?.previousCursor || null,
		isLoading: transactionsQuery.isLoading,
		isError: transactionsQuery.isError,
		cancelTransaction: cancelTransactionMutation.mutateAsync,
		isCancelling: cancelTransactionMutation.isPending,
		refetchTransactions: transactionsQuery.refetch,
	};
};

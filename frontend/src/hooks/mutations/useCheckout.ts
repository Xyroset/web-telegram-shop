import { useMutation, useQueryClient } from '@tanstack/react-query';
import { OrderService } from '@/api/services/OrderService';
import { PaymentService } from '@/api/services/PaymentService';
import type { OrderCreateResponse } from '@/api/models/OrderCreateResponse';
import type { TransactionCreateResponse } from '@/api/models/TransactionCreateResponse';
import type { CreateOrderCommand, CreateTransactionCommand } from '@/types/checkout';

export const useCheckout = () => {
	const queryClient = useQueryClient();

	const createOrderMutation = useMutation<OrderCreateResponse, Error, CreateOrderCommand>({
		mutationFn: async (command: CreateOrderCommand) => {
			return await OrderService.ordersCreate(command);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['cart'] });
		},
	});

	const createTransactionMutation = useMutation<
		TransactionCreateResponse,
		Error,
		CreateTransactionCommand
	>({
		mutationFn: async (command: CreateTransactionCommand) => {
			return await PaymentService.paymentsCreate(command);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['orders'] });
			queryClient.invalidateQueries({ queryKey: ['transactions'] });
		},
	});

	return {
		createOrder: createOrderMutation.mutateAsync,
		isCreatingOrder: createOrderMutation.isPending,
		createTransaction: createTransactionMutation.mutateAsync,
		isCreatingTransaction: createTransactionMutation.isPending,
	};
};

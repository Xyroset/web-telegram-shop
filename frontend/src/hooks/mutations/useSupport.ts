import { useMutation } from '@tanstack/react-query';
import { SupportService } from '@/api/services/SupportService';
import type { CreateTicketRequestRequest } from '@/api/models/CreateTicketRequestRequest';

export const useSupport = () => {
	const createTicketMutation = useMutation<unknown, Error, CreateTicketRequestRequest>({
		mutationFn: async (data: CreateTicketRequestRequest) => {
			return await SupportService.supportCreate(data);
		},
	});

	return {
		createTicket: createTicketMutation.mutateAsync,
		isCreatingTicket: createTicketMutation.isPending,
		error: createTicketMutation.error,
	};
};

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserDeliveryDataService } from '@/api/services/UserDeliveryDataService';
import type { UserDeliveryDataRequestRequest } from '@/api/models/UserDeliveryDataRequestRequest';

export const useDeliveryData = () => {
	const queryClient = useQueryClient();

	const query = useQuery({
		queryKey: ['user', 'delivery_data'],
		queryFn: () => UserDeliveryDataService.usersMeDeliveryDataList(),
		staleTime: 1000 * 60 * 5,
	});

	const setMainAddressMutation = useMutation({
		mutationFn: (id: number) =>
			UserDeliveryDataService.usersMeDeliveryDataManagementPartialUpdate(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user', 'delivery_data'] });
		},
	});

	const createAddressMutation = useMutation({
		mutationFn: (data: UserDeliveryDataRequestRequest) =>
			UserDeliveryDataService.usersMeDeliveryDataCreate(data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user', 'delivery_data'] });
		},
	});

	const updateAddressMutation = useMutation({
		mutationFn: ({ id, data }: { id: number; data: UserDeliveryDataRequestRequest }) =>
			UserDeliveryDataService.usersMeDeliveryDataDetailsUpdate(id, data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user', 'delivery_data'] });
		},
	});

	const deleteAddressMutation = useMutation({
		mutationFn: (id: number) => UserDeliveryDataService.usersMeDeliveryDataDetailsDestroy(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user', 'delivery_data'] });
		},
	});

	return {
		deliveryList: query.data ?? [],
		isLoading: query.isLoading,
		setMainAddress: setMainAddressMutation.mutate,
		isSettingAddress: setMainAddressMutation.isPending,
		createAddress: createAddressMutation.mutateAsync,
		isCreatingAddress: createAddressMutation.isPending,
		updateAddress: updateAddressMutation.mutateAsync,
		isUpdatingAddress: updateAddressMutation.isPending,
		deleteAddress: deleteAddressMutation.mutate,
		isDeletingAddress: deleteAddressMutation.isPending,
	};
};

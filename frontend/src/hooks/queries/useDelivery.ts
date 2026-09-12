import { useQuery } from '@tanstack/react-query';
import { DeliveryService } from '@/api/services/DeliveryService';
import type { DeliveryEstimateModel, DeliveryDataModel } from '@/types/delivery';

export const useDeliveryEstimate = (
	destinationCode?: string | null,
	regionCode?: string | null,
) => {
	const query = useQuery({
		queryKey: ['deliveryEstimate', destinationCode, regionCode],
		queryFn: async (): Promise<DeliveryEstimateModel> => {
			const res = await DeliveryService.deliveryEstimateRetrieve(
				destinationCode || undefined,
				regionCode || undefined,
			);

			return {
				cost: res.cost,
				isFree: res.is_free,
				amountLeftForFree: res.amount_left_for_free,
				isFreeAvailable: res.is_free_available,
			};
		},
		staleTime: 1000 * 60 * 5,
		retry: false,
	});

	return {
		estimate: query.data,
		isLoading: query.isLoading,
		isError: query.isError,
		requiresAddress: query.isError || (!query.data && !query.isLoading),
	};
};

export const useDeliveryData = (orderId: string) => {
	const query = useQuery({
		queryKey: ['deliveryData', orderId],
		queryFn: async (): Promise<DeliveryDataModel> => {
			const res = await DeliveryService.deliveryRetrieve(orderId);

			return {
				id: res.id,
				...(res.state ? { state: res.state } : {}),
				orderId: res.order,
				providerCode: res.provider_code ?? null,
				trackingNumber: res.tracking_number ?? null,
				cost: res.cost,
				deliveryData: res.delivery_data,
			};
		},
		staleTime: 1000 * 60 * 5,
		enabled: !!orderId,
	});

	return {
		deliveryData: query.data,
		isLoading: query.isLoading,
		isError: query.isError,
	};
};

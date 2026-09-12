import type { DeliveryDataResponseStateEnum } from '@/api/models/DeliveryDataResponseStateEnum';

export interface DeliveryEstimateModel {
	cost: string;
	isFree: boolean;
	amountLeftForFree: string;
	isFreeAvailable: boolean;
}

export interface DeliveryData {
	full_name?: string;
	email?: string;
	phone?: string;
	zip_code?: string;
	address_line?: string;
	destination_code?: string;
	region_code?: string;
}

export interface DeliveryDataModel {
	id: number;
	state?: DeliveryDataResponseStateEnum;
	orderId: string;
	providerCode: string | null;
	trackingNumber: string | null;
	cost: string;
	deliveryData: DeliveryData;
}

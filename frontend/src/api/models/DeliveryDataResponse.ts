/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DeliveryDataResponseStateEnum } from './DeliveryDataResponseStateEnum';
export type DeliveryDataResponse = {
	readonly id: number;
	state?: DeliveryDataResponseStateEnum;
	order: string;
	provider_code?: string;
	tracking_number?: string | null;
	cost: string;
	delivery_data: any;
};

export interface UserModel {
	id: number;
	username: string;
	fullName: string;
	photo?: string | null;
	defaultLanguageCode?: string;
	customLanguageCode?: string;
	theme?: string;
	particlesStyle?: string;
	preferredPaymentCurrency?: string;
	preferredNetwork?: string;
	preferredDeliveryData?: Record<string, string>;
}

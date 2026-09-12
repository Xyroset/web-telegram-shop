export type VariantMetadata = Record<string, string>;

export interface ProductAttribute {
	label?: string;
	name?: string;
	value: string | number;
}

export interface ProductDisplayVariant {
	id: string;
	title: string;
	price: number;
	oldPrice?: number;
	badge?: string | null;
	image?: string;
	stockStatus: string;
	basketQuantity: number;
	isNew?: boolean;
	isPromotion?: boolean;
	promotionDiscount?: number;
}

export interface ProductVariantDetail extends ProductDisplayVariant {
	tags: string[];
	specificDescription?: string;
	metadata?: VariantMetadata;
	weightKg?: string;
	lengthCm?: string;
	widthCm?: string;
	heightCm?: string;
	volumetricWeightKg?: number;
}

export interface Product {
	id: string;
	name: string;
	category: string;
	description?: string;
	mainImage: string;
	videoSource?: string | null;
	images: string[];
	attributes?: ProductAttribute[];
	isFavorite: boolean;
	displayVariant?: ProductDisplayVariant;
	averageRating?: number;
	purchasesCount?: number;
}

export interface ProductFilters {
	search?: string;
	category?: string;
	tag?: string;
	ordering?: '-date' | '-name' | '-price' | 'date' | 'name' | 'price';
	minPrice?: string;
	maxPrice?: string;
	inStock?: boolean;
	isFavorite?: boolean;
	isNew?: boolean;
	isPromotion?: boolean;
	productType?: 'DIGITAL' | 'PHYSICAL';
	minRating?: string;
	minDiscount?: string;
	strictSearch?: boolean;
}

export interface ReviewPhoto {
	id: number;
	image: string;
}

export interface ReviewUser {
	tg_id: number;
	tg_username: string | null;
	photo: string | null;
}

export interface Review {
	id: string;
	user: ReviewUser;
	rating: number;
	text: string | null;
	is_author: boolean;
	photos: ReviewPhoto[];
	date: string;
	admin_reply_text?: string | null;
	admin_reply_created_at?: string | null;
}

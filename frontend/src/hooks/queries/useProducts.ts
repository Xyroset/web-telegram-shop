import { useInfiniteQuery } from '@tanstack/react-query';
import { CatalogService } from '@/api/services/CatalogService';
import type { ShopProductListResponse } from '@/api/models/ShopProductListResponse';
import type {
	Product,
	ProductDisplayVariant,
	ProductFilters,
	ProductAttribute,
} from '@/types/product';

const PAGE_LIMIT = 20;

const mapToDomainProduct = (item: ShopProductListResponse): Product => {
	const rawVariant = item.display_variant as Record<string, unknown> | null;
	let displayVariant: ProductDisplayVariant | undefined = undefined;

	if (rawVariant && rawVariant.id) {
		displayVariant = {
			id: String(rawVariant.id),
			title: String(rawVariant.title || ''),
			price: parseFloat(String(rawVariant.price || '0')),
			stockStatus: String(rawVariant.stock_status || 'OUT_OF_STOCK'),
			basketQuantity: Number(rawVariant.basket_quantity || 0),
		};

		if (rawVariant.old_price) displayVariant.oldPrice = parseFloat(String(rawVariant.old_price));
		if (rawVariant.badge) displayVariant.badge = String(rawVariant.badge);
		if (rawVariant.image) displayVariant.image = String(rawVariant.image);
		if (rawVariant.is_new !== undefined) displayVariant.isNew = Boolean(rawVariant.is_new);
		if (rawVariant.is_promotion !== undefined)
			displayVariant.isPromotion = Boolean(rawVariant.is_promotion);
		if (rawVariant.promotion_discount !== undefined)
			displayVariant.promotionDiscount = Number(rawVariant.promotion_discount);
	}

	const photos: string[] = Array.isArray(item.photos)
		? item.photos.map((p) => p.image).filter((img): img is string => Boolean(img))
		: [];

	const rawItemAttr = item as unknown as {
		attributes?: Record<string, unknown> | ProductAttribute[];
	};
	let attributesList: ProductAttribute[] = [];

	if (Array.isArray(rawItemAttr.attributes)) {
		attributesList = rawItemAttr.attributes as ProductAttribute[];
	} else if (rawItemAttr.attributes && typeof rawItemAttr.attributes === 'object') {
		attributesList = Object.entries(rawItemAttr.attributes).map(([key, value]) => ({
			label: key,
			value: String(value),
		}));
	}

	const product: Product = {
		id: String(item.id),
		name: item.name,
		category: item.category?.name ?? 'General',
		mainImage: item.main_image || '',
		images: photos,
		isFavorite: item.is_favorite ?? false,
		averageRating: Number(item.average_rating || 0),
		purchasesCount: Number(item.purchases_count || 0),
	};

	if (item.base_description) product.description = item.base_description;
	if (item.video_source) product.videoSource = item.video_source;
	if (attributesList.length > 0) product.attributes = attributesList;
	if (displayVariant) product.displayVariant = displayVariant;

	return product;
};

export const useProducts = (filters: ProductFilters = {}) => {
	return useInfiniteQuery({
		queryKey: ['products', filters],
		initialPageParam: 0,
		queryFn: async ({ pageParam = 0 }) => {
			const minPriceNum = filters.minPrice ? Number(filters.minPrice) : undefined;
			const maxPriceNum = filters.maxPrice ? Number(filters.maxPrice) : undefined;
			const minRatingNum = filters.minRating ? Number(filters.minRating) : undefined;

			const res = await CatalogService.catalogProductsList(
				filters.category,
				filters.inStock,
				filters.isFavorite,
				filters.isNew,
				filters.isPromotion,
				PAGE_LIMIT,
				maxPriceNum,
				filters.minDiscount,
				minPriceNum,
				minRatingNum,
				pageParam,
				filters.ordering ? [filters.ordering] : undefined,
				filters.productType,
				filters.search || undefined,
				filters.strictSearch,
				filters.tag,
			);

			return {
				products: res.results.map(mapToDomainProduct),
				nextOffset: res.next ? pageParam + PAGE_LIMIT : undefined,
			};
		},
		getNextPageParam: (lastPage) => lastPage.nextOffset,
	});
};

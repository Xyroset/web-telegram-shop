import { useQuery } from '@tanstack/react-query';
import { CatalogService } from '@/api/services/CatalogService';
import type { ProductVariantDetail, VariantMetadata } from '@/types/product';
import type { ProductVariantDetail as ApiProductVariantDetail } from '@/api/models/ProductVariantDetail';

const safeJsonParse = (raw: string): unknown => {
	try {
		return JSON.parse(raw);
	} catch {
		return undefined;
	}
};

const normalizeMetadata = (raw: unknown): VariantMetadata | undefined => {
	const parsed = typeof raw === 'string' ? safeJsonParse(raw) : raw;

	if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
		return undefined;
	}

	return Object.entries(parsed as Record<string, unknown>).reduce<VariantMetadata>(
		(acc, [key, value]) => {
			if (value === null || value === undefined) return acc;
			acc[key] = String(value);
			return acc;
		},
		{},
	);
};

export const useProductVariants = (productId: string | null) => {
	return useQuery({
		queryKey: ['productVariants', productId],
		queryFn: async () => {
			if (!productId) return [];

			const res = await CatalogService.catalogProductsVariantsList(Number(productId));

			return res.map((v: ApiProductVariantDetail): ProductVariantDetail => {
				const variant: ProductVariantDetail = {
					id: String(v.id),
					title: v.title,
					price: parseFloat(v.price || '0'),
					stockStatus: v.stock_status,
					basketQuantity: v.basket_quantity ?? 0,
					tags: (v.tags || []).map((t) => t.name),
				};

				if (v.old_price) variant.oldPrice = parseFloat(v.old_price);
				if (v.badge) variant.badge = v.badge;
				if (v.image) variant.image = v.image;
				if (v.specific_description) variant.specificDescription = v.specific_description;

				const metadata = normalizeMetadata(v.metadata);
				if (metadata) variant.metadata = metadata;

				if (v.weight_kg) variant.weightKg = v.weight_kg;
				if (v.length_cm) variant.lengthCm = v.length_cm;
				if (v.width_cm) variant.widthCm = v.width_cm;
				if (v.height_cm) variant.heightCm = v.height_cm;
				if (v.volumetric_weight_kg) variant.volumetricWeightKg = v.volumetric_weight_kg;

				return variant;
			});
		},
		enabled: !!productId,
		staleTime: 1000 * 60 * 5,
	});
};

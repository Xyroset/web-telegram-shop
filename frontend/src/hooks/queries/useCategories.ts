import { useQuery } from '@tanstack/react-query';
import { CatalogService } from '@/api/services/CatalogService';
import type { Category } from '@/api/models/Category';

export interface CategoryWithSlug extends Category {
	slug: string;
}

export const useCategories = () => {
	return useQuery({
		queryKey: ['categories'],
		queryFn: async () => {
			const res = await CatalogService.catalogCategoriesList();
			return res as CategoryWithSlug[];
		},
		staleTime: 1000 * 60 * 60,
	});
};

import { useQuery } from '@tanstack/react-query';
import { CatalogService } from '@/api/services/CatalogService';
import type { Tag } from '@/api/models/Tag';

export interface TagWithSlug extends Tag {
	slug: string;
}

export const useTags = () => {
	return useQuery({
		queryKey: ['tags'],
		queryFn: async () => {
			const res = await CatalogService.catalogTagsList();
			return res as TagWithSlug[];
		},
		staleTime: 1000 * 60 * 60,
	});
};

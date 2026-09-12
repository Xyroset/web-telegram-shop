import { useQuery } from '@tanstack/react-query';
import { CatalogService } from '@/api/services/CatalogService';

export const useSuggestions = (search: string) => {
	return useQuery({
		queryKey: ['suggestions', search],
		queryFn: () => CatalogService.catalogProductsSuggestionsList(search, 5),
		enabled: search.trim().length > 1,
		staleTime: 1000 * 60 * 5,
	});
};

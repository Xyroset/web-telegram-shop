import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FavoriteService } from '@/api/services/FavoriteService';

export const useFavorites = () => {
	const queryClient = useQueryClient();

	const addFavoriteMutation = useMutation({
		mutationFn: (productId: number) => FavoriteService.catalogFavoritesCreate(productId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['products'] });
		},
	});

	const removeFavoriteMutation = useMutation({
		mutationFn: (productId: number) => FavoriteService.catalogFavoritesDestroy(productId),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['products'] });
		},
	});

	return {
		addFavorite: addFavoriteMutation.mutateAsync,
		isAdding: addFavoriteMutation.isPending,
		removeFavorite: removeFavoriteMutation.mutateAsync,
		isRemoving: removeFavoriteMutation.isPending,
	};
};

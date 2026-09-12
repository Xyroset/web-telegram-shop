import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BasketService } from '@/api/services/BasketService';
import type { BasketUpdatePageResponse } from '@/api/models/BasketUpdatePageResponse';
import type {
	CartItem,
	CartTotals,
	UpdateCartItemCommand,
	RemoveCartItemCommand,
} from '@/types/cart';
import type { Product, ProductDisplayVariant } from '@/types/product';

interface RawBasketProductDTO {
	id?: number | string;
	name?: string;
	category?: { name?: string };
	main_image?: string;
}

const mapBasketItemToCartItem = (item: BasketUpdatePageResponse): CartItem => {
	const variant = item.variant;
	if (!variant) {
		throw new Error('Basket item is missing variant payload.');
	}

	const rawProduct = variant.product as RawBasketProductDTO | undefined;
	const fallbackImage = variant.image || 'https://via.placeholder.com/100';

	const mappedVariant: ProductDisplayVariant = {
		id: String(variant.id),
		title: variant.title,
		price: parseFloat(variant.price || '0'),
		...(variant.old_price ? { oldPrice: parseFloat(variant.old_price) } : {}),
		stockStatus: variant.stock_status,
		image: variant.image || fallbackImage,
		basketQuantity: item.quantity || 0,
	};

	const productSnapshot: Product = {
		id: String(rawProduct?.id ?? variant.id),
		name: rawProduct?.name || 'Unknown Product',
		category: rawProduct?.category?.name || 'General',
		mainImage: rawProduct?.main_image || fallbackImage,
		images: [],
		isFavorite: false,
		displayVariant: mappedVariant,
	};

	return {
		id: String(item.id),
		variantId: Number(mappedVariant.id),
		name: productSnapshot.name,
		quantity: item.quantity || 1,
		price: mappedVariant.price,
		image: productSnapshot.mainImage,
		variantTitle: mappedVariant.title,
		product: productSnapshot,
	};
};

export const useCart = (appliedPromoCode?: string) => {
	const queryClient = useQueryClient();

	const cartItemsQuery = useQuery({
		queryKey: ['cart', 'items'],
		queryFn: async (): Promise<CartItem[]> => {
			const res = await BasketService.basketList();
			return res.map(mapBasketItemToCartItem);
		},
	});

	const cartTotalsQuery = useQuery({
		queryKey: ['cart', 'totals', appliedPromoCode],
		queryFn: async (): Promise<CartTotals> => {
			try {
				const res = await BasketService.basketCalculateRetrieve(appliedPromoCode);
				return {
					subtotal: parseFloat(res.base_price || '0'),
					total: parseFloat(res.total_price || '0'),
					discountAmount: parseFloat(res.discount_value || '0'),
					promocodeType: res.promocode_type || '',
					isPromoValid: res.valid_promocode ?? false,
				};
			} catch (error: unknown) {
				const fallbackRes = await BasketService.basketCalculateRetrieve();

				let apiMessage: string | null = null;
				let isServerError = false;

				const err = error as Record<string, unknown>;
				const responseObj = err.response as Record<string, unknown> | undefined;
				const statusCode = err.status ?? responseObj?.status;

				if (typeof statusCode === 'number' && statusCode >= 500) {
					isServerError = true;
				}

				const responseData = responseObj?.data ?? err.body ?? err.data;

				if (responseData && typeof responseData === 'object') {
					const data = responseData as Record<string, unknown>;
					const rawMessage =
						data.message ||
						data.detail ||
						data.error ||
						data.non_field_errors ||
						data.promo_code ||
						Object.values(data)[0];

					if (Array.isArray(rawMessage) && rawMessage.length > 0) {
						apiMessage = String(rawMessage[0]);
					} else if (rawMessage) {
						apiMessage = String(rawMessage);
					}
				} else if (typeof responseData === 'string') {
					apiMessage = responseData;
				}

				return {
					subtotal: parseFloat(fallbackRes.base_price || '0'),
					total: parseFloat(fallbackRes.total_price || '0'),
					discountAmount: 0,
					promocodeType: fallbackRes.promocode_type || '',
					isPromoValid: false,
					promoError: apiMessage || (isServerError ? 'server_error' : 'invalid_code'),
				};
			}
		},
	});

	const updateQuantityMutation = useMutation({
		mutationFn: async (command: UpdateCartItemCommand) => {
			return await BasketService.basketCreate({
				variant_id: command.variantId,
				quantity: command.quantity,
			});
		},
		onMutate: async (command: UpdateCartItemCommand) => {
			await queryClient.cancelQueries({ queryKey: ['cart', 'items'] });
			const previousItems = queryClient.getQueryData<CartItem[]>(['cart', 'items']);

			if (previousItems) {
				queryClient.setQueryData<CartItem[]>(['cart', 'items'], (old) =>
					old?.map((item) =>
						item.variantId === command.variantId ? { ...item, quantity: command.quantity } : item,
					),
				);
			}

			return { previousItems };
		},
		onError: (_error, _command, context) => {
			if (context?.previousItems) {
				queryClient.setQueryData(['cart', 'items'], context.previousItems);
			}
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: ['cart'] });
			queryClient.invalidateQueries({ queryKey: ['deliveryEstimate'] });
		},
	});

	const removeFromCartMutation = useMutation({
		mutationFn: async (command: RemoveCartItemCommand) => {
			return await BasketService.basketDestroy(command.variantId);
		},
		onMutate: async (command: RemoveCartItemCommand) => {
			await queryClient.cancelQueries({ queryKey: ['cart', 'items'] });
			const previousItems = queryClient.getQueryData<CartItem[]>(['cart', 'items']);

			if (previousItems) {
				queryClient.setQueryData<CartItem[]>(['cart', 'items'], (old) =>
					old?.filter((item) => item.variantId !== command.variantId),
				);
			}

			return { previousItems };
		},
		onError: (_error, _command, context) => {
			if (context?.previousItems) {
				queryClient.setQueryData(['cart', 'items'], context.previousItems);
			}
		},
		onSettled: () => {
			queryClient.invalidateQueries({ queryKey: ['cart'] });
			queryClient.invalidateQueries({ queryKey: ['deliveryEstimate'] });
		},
	});

	return {
		items: cartItemsQuery.data || [],
		totals: cartTotalsQuery.data,
		isLoading: cartItemsQuery.isLoading || cartTotalsQuery.isLoading,
		isError: cartItemsQuery.isError || cartTotalsQuery.isError,
		updateQuantity: updateQuantityMutation.mutate,
		removeFromCart: removeFromCartMutation.mutate,
		isUpdating: updateQuantityMutation.isPending || removeFromCartMutation.isPending,
		refetchTotals: cartTotalsQuery.refetch,
	};
};

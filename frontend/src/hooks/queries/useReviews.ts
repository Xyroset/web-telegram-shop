import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ReviewService } from '@/api/services/ReviewService';
import type { ReviewCreateRequestRequest } from '@/api/models/ReviewCreateRequestRequest';
import type { ReviewUpdateRequestRequest } from '@/api/models/ReviewUpdateRequestRequest';
import type { Review as ApiReview } from '@/api/models/Review';
import type { Review } from '@/types/product';

export interface CreateReviewCommand {
	product_id: number;
	rating: number;
	text?: string;
	is_anonymous: boolean;
	photos?: File[];
}

const extractCursor = (urlUrl: string | null | undefined): string | undefined => {
	if (!urlUrl) return undefined;
	try {
		const url = new URL(urlUrl);
		return url.searchParams.get('c') || undefined;
	} catch {
		const match = urlUrl.match(/[?&]c=([^&]+)/);
		return match ? match[1] : undefined;
	}
};

export const useReviews = (productId: number | null, lang: string = 'en') => {
	const queryClient = useQueryClient();

	const query = useInfiniteQuery({
		queryKey: ['reviews', productId],
		initialPageParam: undefined as string | undefined,
		queryFn: async ({ pageParam }) => {
			if (!productId) return { reviews: [], nextCursor: undefined };

			const res = await ReviewService.catalogReviewsList(productId, pageParam);

			const reviews: Review[] = res.results.map((r: ApiReview) => ({
				id: String(r.id),
				user: {
					tg_id: r.user.tg_id,
					tg_username: r.user.tg_username ?? null,
					photo: r.user.photo ?? null,
				},
				is_author: r.is_author,
				rating: r.rating ?? 5,
				text: r.text ?? '',
				photos: r.photos || [],
				date: new Date(r.created_at).toLocaleString(lang || 'en', {
					year: 'numeric',
					month: 'short',
					day: '2-digit',
					hour: '2-digit',
					minute: '2-digit',
				}),
				admin_reply_text: r.admin_reply_text ?? null,
				admin_reply_created_at: r.admin_reply_created_at ?? null,
			}));

			return {
				reviews,
				nextCursor: extractCursor(res.next),
			};
		},
		enabled: !!productId,
		getNextPageParam: (lastPage) => lastPage.nextCursor,
	});

	const createReviewMutation = useMutation({
		mutationFn: (cmd: CreateReviewCommand) => {
			const payload: ReviewCreateRequestRequest = {
				product_id: cmd.product_id,
				rating: cmd.rating,
				is_anonymous: cmd.is_anonymous,
			};

			if (cmd.text && cmd.text.trim().length > 0) {
				payload.text = cmd.text.trim();
			}

			if (cmd.photos && cmd.photos.length > 0) {
				payload.photos = cmd.photos as Blob[];
			}

			return ReviewService.catalogReviewsCreate(payload);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
		},
	});

	const updateReviewMutation = useMutation({
		mutationFn: ({ id, data }: { id: string; data: ReviewUpdateRequestRequest }) => {
			const payload = { ...data };

			if (typeof payload.text === 'string' && payload.text.trim() === '') {
				delete payload.text;
			}

			return ReviewService.catalogReviewsUpdate(id, payload);
		},
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
		},
	});

	const deleteReviewMutation = useMutation({
		mutationFn: (id: string) => ReviewService.catalogReviewsDestroy(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['reviews', productId] });
		},
	});

	return {
		data: query.data,
		isLoading: query.isLoading,
		isFetchingNextPage: query.isFetchingNextPage,
		hasNextPage: query.hasNextPage,
		fetchNextPage: query.fetchNextPage,
		createReview: createReviewMutation.mutateAsync,
		isCreating: createReviewMutation.isPending,
		updateReview: updateReviewMutation.mutateAsync,
		isUpdating: updateReviewMutation.isPending,
		deleteReview: deleteReviewMutation.mutateAsync,
		isDeleting: deleteReviewMutation.isPending,
	};
};

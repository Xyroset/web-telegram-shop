import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
	X,
	ChevronRight,
	Heart,
	Star,
	Maximize2,
	Package,
	User as UserIcon,
	Edit2,
	Trash2,
	Check,
	Camera,
} from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { isAxiosError } from 'axios';
import WebApp from '@twa-dev/sdk';

import { useCart } from '@/hooks/queries/useCart';
import { useProductVariants } from '@/hooks/queries/useProductVariants';
import { useFavorites } from '@/hooks/mutations/useFavorites';
import { useReviews, type CreateReviewCommand } from '@/hooks/queries/useReviews';
import { useConfig } from '@/store/ConfigContext';
import { useSettings } from '@/hooks/queries/useUserSettings';
import { ProductModalSkeleton } from '@/components/skeletons/ProductModalSkeleton';
import type { Product, ProductVariantDetail, ProductAttribute, Review } from '@/types/product';

interface ProductModalProps {
	product: Product;
	onClose: () => void;
}

type MediaItem = {
	type: 'image' | 'video';
	url: string;
	isYouTube?: boolean;
};

type TranslationNode = string | Record<string, string>;
type ModalTranslations = Record<string, TranslationNode>;

interface LocalCartItem {
	variantId: number | string;
	quantity: number;
}

const isVariantDiscounted = (
	variant: ProductVariantDetail | { oldPrice?: number; price: number },
): boolean => {
	return typeof variant.oldPrice === 'number' && variant.oldPrice > variant.price;
};

const getYouTubeId = (url: string): string | null => {
	const regExp = /^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
	const match = url.match(regExp);
	return match && match[2].length === 11 ? match[2] : null;
};

const t = (dict: ModalTranslations | undefined, key: string, fallback: string): string => {
	const val = dict?.[key];
	return typeof val === 'string' ? val : fallback;
};

const tNested = (
	dict: ModalTranslations | undefined,
	parentKey: string,
	childKey: string,
	fallback: string,
): string => {
	const parent = dict?.[parentKey];
	if (parent && typeof parent === 'object' && typeof parent[childKey] === 'string') {
		return parent[childKey];
	}
	return fallback;
};

const resolveAvatarUrl = (path: string | null | undefined): string | null => {
	if (!path) return null;
	if (path.startsWith('http') || path.startsWith('/')) return path;
	return `/media/${path}`;
};

const GalleryImage = ({ url, alt }: { url: string; alt: string }) => {
	const [isLoaded, setIsLoaded] = useState(false);

	return (
		<div className="relative w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-900">
			{!isLoaded && (
				<div className="absolute inset-0 z-10 bg-gray-200 dark:bg-gray-800 animate-pulse" />
			)}
			<img
				src={url || 'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'}
				alt={alt}
				loading="lazy"
				decoding="async"
				onLoad={() => setIsLoaded(true)}
				className={`w-full h-full object-cover transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
			/>
		</div>
	);
};

export function ProductModal({ product, onClose }: ProductModalProps) {
	const navigate = useNavigate();
	const { config } = useConfig();
	const { settings } = useSettings();

	const translations = (config?.translations as Record<string, unknown>)?.product_modal as
		| ModalTranslations
		| undefined;

	const { items: cartItems, updateQuantity, isUpdating } = useCart();
	const { data: variants = [], isLoading: isLoadingVariants } = useProductVariants(product.id);
	const { addFavorite, removeFavorite } = useFavorites();

	const numericProductId = Number(product.id);

	const {
		data: reviewsData,
		createReview,
		isCreating: isCreatingReview,
		updateReview,
		isUpdating: isUpdatingReview,
		deleteReview,
		hasNextPage,
		fetchNextPage,
	} = useReviews(numericProductId || null, settings?.language_code);

	const [isFavorite, setIsFavorite] = useState<boolean>(product.isFavorite || false);
	const [activeMediaIndex, setActiveMediaIndex] = useState<number>(0);
	const [isZoomed, setIsZoomed] = useState<boolean>(false);
	const [zoomedReviewPhoto, setZoomedReviewPhoto] = useState<string | null>(null);
	const [selectedOptions, setSelectedOptions] = useState<Record<string, string> | null>(null);
	const [manualVariantId, setManualVariantId] = useState<string | null>(null);

	const [reviewText, setReviewText] = useState<string>('');
	const [reviewRating, setReviewRating] = useState<number>(5);
	const [isAnonymous, setIsAnonymous] = useState<boolean>(false);
	const [reviewPhotos, setReviewPhotos] = useState<File[]>([]);
	const [photoPreviews, setPhotoPreviews] = useState<string[]>([]);
	const [reviewError, setReviewError] = useState<string | null>(null);

	const [editingReviewId, setEditingReviewId] = useState<string | null>(null);
	const [editReviewText, setEditReviewText] = useState<string>('');
	const [editReviewRating, setEditReviewRating] = useState<number>(5);
	const [reviewToDelete, setReviewToDelete] = useState<string | null>(null);

	const reviews: Review[] = useMemo(
		() => reviewsData?.pages.flatMap((p) => p.reviews) || [],
		[reviewsData],
	);

	const averageRating = useMemo(() => {
		if (reviews.length === 0) return 0;
		return reviews.reduce((acc, r) => acc + (r.rating || 5), 0) / reviews.length;
	}, [reviews]);

	const handleToggleFavorite = async (e: React.MouseEvent) => {
		e.stopPropagation();
		if (!numericProductId) return;
		const newStatus = !isFavorite;
		setIsFavorite(newStatus);
		try {
			if (newStatus) await addFavorite(numericProductId);
			else await removeFavorite(numericProductId);
		} catch {
			setIsFavorite(!newStatus);
		}
	};

	const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
		if (e.target.files) {
			const files = Array.from(e.target.files);
			setReviewPhotos(files);
			const previews = files.map((file) => URL.createObjectURL(file));
			setPhotoPreviews(previews);
		}
	};

	const removePhoto = (index: number) => {
		setReviewPhotos((prev) => prev.filter((_, i) => i !== index));
		setPhotoPreviews((prev) => prev.filter((_, i) => i !== index));
	};

	const handleReviewSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setReviewError(null);
		if (!numericProductId) return;

		try {
			const cmd: CreateReviewCommand = {
				product_id: numericProductId,
				rating: reviewRating,
				text: reviewText,
				is_anonymous: isAnonymous,
			};

			if (reviewPhotos.length > 0) {
				cmd.photos = reviewPhotos;
			}

			await createReview(cmd);

			setReviewText('');
			setReviewRating(5);
			setIsAnonymous(false);
			setReviewPhotos([]);
			setPhotoPreviews([]);
		} catch (err: unknown) {
			const defaultErr = tNested(
				translations,
				'errors',
				'review_failed',
				'Cannot submit review. Make sure you purchased this item.',
			);

			if (
				isAxiosError(err) &&
				err.response?.data &&
				typeof err.response.data === 'object' &&
				'message' in err.response.data
			) {
				setReviewError(String((err.response.data as { message: unknown }).message));
			} else {
				setReviewError(defaultErr);
			}
		}
	};

	const handleEditSubmit = async (e: React.FormEvent, reviewId: string) => {
		e.preventDefault();
		try {
			await updateReview({
				id: reviewId,
				data: { text: editReviewText, rating: editReviewRating },
			});
			setEditingReviewId(null);
		} catch (err) {
			console.error('Failed to update review', err);
		}
	};

	const confirmDeleteReview = async (reviewId: string) => {
		try {
			await deleteReview(reviewId);
			setReviewError(null);
			setReviewText('');
			setEditingReviewId(null);
			setReviewToDelete(null);
		} catch (err) {
			console.error('Failed to delete review', err);
			setReviewToDelete(null);
		}
	};

	const handleUserLinkClick = (e: React.MouseEvent, username: string) => {
		e.preventDefault();
		const url = `https://t.me/${username}`;
		try {
			WebApp.openTelegramLink(url);
		} catch {
			window.open(url, '_blank', 'noopener,noreferrer');
		}
	};

	const hasMetadata = useMemo(
		() => variants.some((v) => v.metadata && Object.keys(v.metadata).length > 0),
		[variants],
	);

	const effectiveOptions = useMemo(() => {
		if (selectedOptions) return selectedOptions;
		if (hasMetadata && variants.length > 0 && variants[0].metadata) return variants[0].metadata;
		return {};
	}, [selectedOptions, hasMetadata, variants]);

	const effectiveManualVariantId = useMemo(() => {
		if (manualVariantId) return manualVariantId;
		if (!hasMetadata && variants.length > 0) return String(variants[0].id);
		return null;
	}, [manualVariantId, hasMetadata, variants]);

	const selectedVariantId = useMemo(() => {
		if (variants.length === 0) return null;
		if (hasMetadata) {
			const matched = variants.find((v) => {
				if (!v.metadata) return false;
				return Object.entries(effectiveOptions).every(([key, val]) => v.metadata![key] === val);
			});
			return matched ? String(matched.id) : null;
		}
		return effectiveManualVariantId;
	}, [variants, hasMetadata, effectiveOptions, effectiveManualVariantId]);

	const selectedVariant = useMemo(
		() => variants.find((v) => String(v.id) === selectedVariantId) || null,
		[variants, selectedVariantId],
	);

	const optionsMap = useMemo(() => {
		if (!hasMetadata || variants.length === 0) return null;
		const map: Record<string, Set<string>> = {};
		variants.forEach((v) => {
			if (v.metadata)
				Object.entries(v.metadata).forEach(([key, val]) => {
					if (!map[key]) map[key] = new Set<string>();
					map[key].add(String(val));
				});
		});
		return map;
	}, [variants, hasMetadata]);

	const mediaItems = useMemo<MediaItem[]>(() => {
		const items: MediaItem[] = [];
		const seenUrls = new Set<string>();

		const addImage = (url?: string) => {
			if (url && !seenUrls.has(url)) {
				items.push({ type: 'image', url });
				seenUrls.add(url);
			}
		};

		addImage(product.mainImage);
		if (product.videoSource && !seenUrls.has(product.videoSource)) {
			const isYouTube =
				product.videoSource.includes('youtube.com') || product.videoSource.includes('youtu.be');
			items.push({ type: 'video', url: product.videoSource, isYouTube });
			seenUrls.add(product.videoSource);
		}
		if (product.images?.length > 0) product.images.forEach(addImage);
		variants.forEach((v) => addImage(v.image));
		addImage(product.displayVariant?.image);

		return items;
	}, [product.mainImage, product.videoSource, product.images, variants, product.displayVariant]);

	const [prevSelectedVariantId, setPrevSelectedVariantId] = useState<string | null>(null);

	if (selectedVariantId !== prevSelectedVariantId) {
		setPrevSelectedVariantId(selectedVariantId);
		if (selectedVariant?.image) {
			const targetIndex = mediaItems.findIndex((m) => m.url === selectedVariant.image);
			if (targetIndex !== -1 && targetIndex !== activeMediaIndex) setActiveMediaIndex(targetIndex);
		} else if (activeMediaIndex !== 0) {
			setActiveMediaIndex(0);
		}
	}

	const displayPrice = selectedVariant?.price ?? product.displayVariant?.price ?? 0;
	const displayOldPrice = selectedVariant?.oldPrice ?? product.displayVariant?.oldPrice;
	const displayHasDiscount = selectedVariant
		? isVariantDiscounted(selectedVariant)
		: product.displayVariant
			? isVariantDiscounted(product.displayVariant)
			: false;
	const safeOldPrice = displayHasDiscount ? displayOldPrice : undefined;
	const displayTags = selectedVariant?.tags || [];
	const displayBadges = Array.from(
		new Set(
			[selectedVariant?.badge, product.displayVariant?.badge].filter((badge): badge is string =>
				Boolean(badge),
			),
		),
	);
	const displaySpecificDescription = selectedVariant?.specificDescription ?? null;
	const isOutOfStock = selectedVariant?.stockStatus === 'OUT_OF_STOCK';

	const formattedAttributes = useMemo(() => {
		const baseAttributes =
			(product as Product & { attributes?: ProductAttribute[] }).attributes ?? [];
		const mapped: { label: string; value: string | number }[] = baseAttributes.map((attr) => ({
			label: (attr.label || attr.name || '').trim() || 'Attribute',
			value: attr.value,
		}));
		if (selectedVariant) {
			if (selectedVariant.weightKg && Number(selectedVariant.weightKg) > 0)
				mapped.push({ label: 'Weight', value: `${selectedVariant.weightKg} kg` });
			if (selectedVariant.volumetricWeightKg && selectedVariant.volumetricWeightKg > 0)
				mapped.push({
					label: 'Volumetric Weight',
					value: `${selectedVariant.volumetricWeightKg.toFixed(2)} kg`,
				});
			if (
				selectedVariant.lengthCm &&
				selectedVariant.widthCm &&
				selectedVariant.heightCm &&
				Number(selectedVariant.lengthCm) > 0
			) {
				mapped.push({
					label: 'Dimensions (L×W×H)',
					value: `${selectedVariant.lengthCm} × ${selectedVariant.widthCm} × ${selectedVariant.heightCm} cm`,
				});
			}
		}
		return mapped.filter((attr) => String(attr.value).trim() !== '');
	}, [product, selectedVariant]);

	const canAddToCart =
		(!variants.length || selectedVariantId !== null) && !isOutOfStock && !isLoadingVariants;

	const currentCartItem = cartItems.find(
		(c: LocalCartItem) => String(c.variantId) === selectedVariantId,
	);

	const cartQuantity =
		currentCartItem?.quantity ||
		selectedVariant?.basketQuantity ||
		product.displayVariant?.basketQuantity ||
		0;

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-gray-950/80 p-0 sm:p-4"
		>
			<motion.div
				initial={{ y: '100%' }}
				animate={{ y: 0 }}
				exit={{ y: '100%' }}
				transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
				style={{ willChange: 'transform, opacity' }}
				className="w-full h-[100dvh] sm:h-auto sm:max-h-[90vh] sm:max-w-xl bg-white dark:bg-gray-950 rounded-t-3xl sm:rounded-3xl overflow-hidden flex flex-col relative sm:shadow-2xl mt-auto sm:mt-0"
			>
				{isLoadingVariants && variants.length === 0 ? (
					<ProductModalSkeleton onClose={onClose} />
				) : (
					<>
						{/* Header Action */}
						<div className="absolute top-4 right-4 z-[60] flex gap-2 pointer-events-auto">
							<button
								onClick={handleToggleFavorite}
								className="w-9 h-9 sm:w-10 sm:h-10 bg-white/95 dark:bg-gray-800/95 shadow-sm rounded-full flex items-center justify-center hover:bg-white dark:hover:bg-gray-700 transition-colors cursor-pointer"
							>
								<Heart
									size={18}
									className={
										isFavorite ? 'fill-rose-500 text-rose-500' : 'text-gray-800 dark:text-white'
									}
								/>
							</button>
							<button
								onClick={(e) => {
									e.stopPropagation();
									onClose();
								}}
								className="w-9 h-9 sm:w-10 sm:h-10 bg-white/95 dark:bg-gray-800/95 shadow-sm rounded-full flex items-center justify-center hover:bg-white dark:hover:bg-gray-700 transition-colors cursor-pointer"
							>
								<X size={18} className="text-gray-800 dark:text-white" />
							</button>
						</div>

						<div className="flex-1 overflow-y-auto pb-24 sm:pb-28 [&::-webkit-scrollbar]:hidden">
							{/* Media Gallery */}
							<div className="relative aspect-[4/3] sm:aspect-square w-full bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-center overflow-hidden group/gallery">
								<div
									className="w-full h-full flex transition-transform duration-300 ease-out"
									style={{ transform: `translateX(-${activeMediaIndex * 100}%)` }}
								>
									{mediaItems.map((media, idx) => (
										<div
											key={idx}
											className="w-full h-full flex-shrink-0 bg-black flex items-center justify-center"
										>
											{media.type === 'image' ? (
												<GalleryImage url={media.url} alt={`${product.name} ${idx + 1}`} />
											) : media.isYouTube ? (
												<iframe
													className="w-full h-full"
													src={`https://www.youtube.com/embed/${getYouTubeId(media.url)}`}
													title="YouTube video player"
													frameBorder="0"
													loading="lazy"
													allowFullScreen
												></iframe>
											) : (
												<video
													src={media.url}
													controls
													playsInline
													className="w-full h-full object-contain"
												/>
											)}
										</div>
									))}
								</div>

								{mediaItems.length > 1 && (
									<>
										<button
											onClick={(e) => {
												e.stopPropagation();
												setActiveMediaIndex((prev) =>
													prev > 0 ? prev - 1 : mediaItems.length - 1,
												);
											}}
											className="absolute left-0 top-0 bottom-0 w-1/4 z-20 flex items-center justify-start pl-4 group cursor-pointer"
										>
											<div className="w-8 h-8 rounded-full bg-white/90 dark:bg-black/50 text-gray-900 dark:text-white flex items-center justify-center opacity-80 active:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all shadow-sm hover:bg-white dark:hover:bg-black/70">
												<ChevronRight className="rotate-180" size={20} />
											</div>
										</button>
										<button
											onClick={(e) => {
												e.stopPropagation();
												setActiveMediaIndex((prev) =>
													prev < mediaItems.length - 1 ? prev + 1 : 0,
												);
											}}
											className="absolute right-0 top-0 bottom-0 w-1/4 z-20 flex items-center justify-end pr-4 group cursor-pointer"
										>
											<div className="w-8 h-8 rounded-full bg-white/90 dark:bg-black/50 text-gray-900 dark:text-white flex items-center justify-center opacity-80 active:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all shadow-sm hover:bg-white dark:hover:bg-black/70">
												<ChevronRight size={20} />
											</div>
										</button>
									</>
								)}

								<div className="absolute top-4 left-4 flex flex-col gap-2 z-10 pointer-events-none">
									{displayBadges.map((badge) => (
										<span
											key={badge}
											className="px-2 py-1 bg-amber-500/95 text-white rounded-md text-[9px] sm:text-[10px] font-bold uppercase tracking-wider w-max shadow-sm"
										>
											{badge}
										</span>
									))}
									{displayTags.map((tag) => (
										<span
											key={tag}
											className="px-2 py-1 bg-white/95 dark:bg-black/80 rounded-md text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-gray-900 dark:text-white w-max shadow-sm"
										>
											{tag}
										</span>
									))}
								</div>

								{mediaItems[activeMediaIndex]?.type === 'image' && (
									<button
										onClick={(e) => {
											e.stopPropagation();
											setIsZoomed(true);
										}}
										className="absolute bottom-4 right-4 z-20 bg-white/90 dark:bg-black/50 p-2 rounded-full text-gray-900 dark:text-white hover:bg-white dark:hover:bg-black/70 transition-all shadow-sm cursor-pointer"
									>
										<Maximize2 size={14} className="sm:w-4 sm:h-4" />
									</button>
								)}
							</div>

							<div className="p-4 sm:p-5 space-y-4 sm:space-y-6">
								<div>
									<div className="flex items-center justify-between mb-1.5 sm:mb-2">
										<span className="text-[10px] sm:text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400 font-bold block">
											{product.category}
										</span>
										{reviews.length > 0 && (
											<div className="flex items-center gap-1 text-yellow-500 dark:text-yellow-400 text-[10px] sm:text-xs font-bold">
												<Star
													size={12}
													className="fill-yellow-500 dark:fill-yellow-400 sm:w-3.5 sm:h-3.5"
												/>
												{averageRating.toFixed(1)} ({reviews.length})
											</div>
										)}
									</div>
									<h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2 leading-tight">
										{product.name}
									</h1>

									<div className="flex flex-col gap-2 mt-3 sm:mt-4">
										<div className="flex items-end gap-2 sm:gap-3">
											<span className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
												${displayPrice.toFixed(2)}
											</span>
											{safeOldPrice && (
												<span className="text-sm sm:text-lg text-gray-400 dark:text-gray-500 line-through mb-0.5 sm:mb-1">
													${safeOldPrice.toFixed(2)}
												</span>
											)}
										</div>

										<div className="flex flex-wrap items-center gap-2">
											{safeOldPrice && (
												<span className="text-[10px] sm:text-xs font-bold bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
													{t(translations, 'save', 'Save')} $
													{(safeOldPrice - displayPrice).toFixed(2)}
												</span>
											)}
											{selectedVariant && (
												<>
													{selectedVariant.stockStatus === 'IN_STOCK' && (
														<span className="flex items-center gap-1 text-[10px] sm:text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
															<Package size={12} /> {t(translations, 'in_stock', 'In Stock')}
														</span>
													)}
													{selectedVariant.stockStatus === 'LOW_STOCK' && (
														<span className="flex items-center gap-1 text-[10px] sm:text-xs font-bold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
															<Package size={12} /> {t(translations, 'low_stock', 'Low Stock')}
														</span>
													)}
													{selectedVariant.stockStatus === 'OUT_OF_STOCK' && (
														<span className="flex items-center gap-1 text-[10px] sm:text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-md">
															<X size={12} /> {t(translations, 'out_of_stock', 'Out of Stock')}
														</span>
													)}
												</>
											)}
										</div>
									</div>
								</div>

								{/* Variants Selection */}
								<div className="pt-4 border-t border-gray-200 dark:border-gray-800 min-h-[80px]">
									{variants.length > 0 ? (
										<div className="space-y-3 sm:space-y-4">
											{hasMetadata && optionsMap ? (
												Object.entries(optionsMap).map(([optionKey, optionValuesSet]) => (
													<div key={optionKey} className="space-y-2 sm:space-y-3">
														<span className="text-xs sm:text-sm font-bold text-gray-800 dark:text-gray-300 uppercase tracking-wider">
															{optionKey}
														</span>
														<div className="flex flex-wrap gap-2">
															{Array.from(optionValuesSet).map((value) => {
																const isSelected = effectiveOptions[optionKey] === value;
																return (
																	<button
																		key={value}
																		onClick={() =>
																			setSelectedOptions({
																				...effectiveOptions,
																				[optionKey]: value,
																			})
																		}
																		className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm font-semibold border cursor-pointer transition-colors ${isSelected ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-700 hover:border-gray-400'}`}
																	>
																		{value}
																	</button>
																);
															})}
														</div>
													</div>
												))
											) : (
												<div>
													<span className="text-xs sm:text-sm font-bold text-gray-800 dark:text-gray-300 block mb-2 sm:mb-3">
														{t(translations, 'select_variant', 'Select Variant')}
													</span>
													<div className="flex flex-wrap gap-2">
														{variants.map((variant) => (
															<button
																key={variant.id}
																onClick={() => setManualVariantId(String(variant.id))}
																className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm font-semibold border cursor-pointer transition-colors ${effectiveManualVariantId === String(variant.id) ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-200 border-gray-300 dark:border-gray-700 hover:border-gray-400'}`}
															>
																{variant.title}
															</button>
														))}
													</div>
												</div>
											)}
											{displaySpecificDescription && (
												<motion.div
													initial={{ opacity: 0, height: 0 }}
													animate={{ opacity: 1, height: 'auto' }}
													className="mt-2 sm:mt-3 p-2.5 sm:p-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-xl"
												>
													<p className="text-xs sm:text-sm text-blue-800 dark:text-blue-300 leading-relaxed">
														{displaySpecificDescription}
													</p>
												</motion.div>
											)}
										</div>
									) : null}
								</div>

								{/* Description & Specifications */}
								{product.description && (
									<div className="pt-4 border-t border-gray-200 dark:border-gray-800">
										<h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white mb-2 sm:mb-3">
											{t(translations, 'description', 'Description')}
										</h3>
										<p className="text-gray-800 dark:text-gray-200 text-xs sm:text-sm leading-relaxed">
											{product.description}
										</p>
									</div>
								)}

								{formattedAttributes.length > 0 && (
									<div className="pt-4 border-t border-gray-200 dark:border-gray-800">
										<h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white mb-2 sm:mb-3">
											{t(translations, 'specifications', 'Specifications')}
										</h3>
										<div className="bg-gray-50 dark:bg-gray-900 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800">
											{formattedAttributes.map((attr, idx) => (
												<div
													key={idx}
													className={`grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-1 sm:gap-2 p-2.5 sm:p-3 ${idx !== formattedAttributes.length - 1 ? 'border-b border-gray-200 dark:border-gray-800/50' : ''}`}
												>
													<span className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 font-medium">
														{attr.label}
													</span>
													<span className="text-xs sm:text-sm text-gray-900 dark:text-gray-100 font-semibold sm:text-right break-words">
														{attr.value}
													</span>
												</div>
											))}
										</div>
									</div>
								)}

								{/* Reviews Section */}
								<div className="pt-4 sm:pt-6 border-t border-gray-200 dark:border-gray-800">
									<h3 className="text-sm sm:text-base font-semibold text-gray-900 dark:text-white mb-3 sm:mb-4">
										{t(translations, 'reviews_title', 'Reviews')}{' '}
										{reviews.length > 0 && `(${reviews.length})`}
									</h3>

									<form
										onSubmit={handleReviewSubmit}
										className="mb-4 sm:mb-6 bg-gray-50 dark:bg-gray-900 p-3 sm:p-4 rounded-xl border border-gray-200 dark:border-gray-800"
									>
										<h4 className="text-xs sm:text-sm font-semibold mb-2 text-gray-900 dark:text-white">
											{t(translations, 'write_review', 'Write a Review')}
										</h4>
										{reviewError && (
											<p className="text-[10px] sm:text-xs text-rose-500 font-medium mb-2 sm:mb-3">
												{reviewError}
											</p>
										)}
										<div className="flex gap-1 mb-2 sm:mb-3">
											{[1, 2, 3, 4, 5].map((star) => (
												<button
													type="button"
													key={star}
													onClick={() => setReviewRating(star)}
													className="cursor-pointer p-0.5"
												>
													<Star
														size={16}
														className={`sm:w-5 sm:h-5 ${star <= reviewRating ? 'fill-yellow-500 text-yellow-500' : 'text-gray-300 dark:text-gray-700'}`}
													/>
												</button>
											))}
										</div>
										<textarea
											value={reviewText}
											onChange={(e) => setReviewText(e.target.value)}
											placeholder={t(
												translations,
												'review_placeholder',
												'Share your thoughts about this product...',
											)}
											className="w-full bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-xl p-2.5 sm:p-3 text-xs sm:text-sm focus:border-blue-500 outline-none mb-2 sm:mb-3 text-gray-900 dark:text-white resize-none"
											rows={3}
										/>

										<div className="flex flex-wrap gap-2 mb-3">
											{photoPreviews.map((preview, idx) => (
												<div
													key={idx}
													className="relative w-12 h-12 rounded-lg border border-gray-200 overflow-hidden"
												>
													<img
														src={
															preview ||
															'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
														}
														alt="preview"
														className="w-full h-full object-cover"
													/>
													<button
														type="button"
														onClick={() => removePhoto(idx)}
														className="absolute top-0 right-0 bg-black/60 p-0.5 text-white hover:bg-rose-500 transition-colors"
													>
														<X size={12} />
													</button>
												</div>
											))}
										</div>

										<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
											<div className="flex items-center gap-4">
												<label className="flex items-center gap-2 cursor-pointer group">
													<input
														type="checkbox"
														className="hidden"
														checked={isAnonymous}
														onChange={(e) => setIsAnonymous(e.target.checked)}
													/>
													<div
														className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${isAnonymous ? 'bg-blue-600 border-blue-600' : 'border-gray-400 dark:border-gray-600 group-hover:border-blue-500'}`}
													>
														{isAnonymous && <Check size={12} className="text-white" />}
													</div>
													<span className="text-xs font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
														{t(translations, 'submit_anonymously', 'Submit anonymously')}
													</span>
												</label>

												<label className="flex items-center gap-1.5 cursor-pointer text-gray-500 hover:text-blue-600 transition-colors">
													<Camera size={16} />
													<span className="text-xs font-medium">
														{t(translations, 'attach_photos', 'Add Photo')}
													</span>
													<input
														type="file"
														multiple
														accept="image/*"
														onChange={handlePhotoSelect}
														className="hidden"
													/>
												</label>
											</div>

											<button
												disabled={isCreatingReview}
												className="px-4 sm:px-5 py-2 sm:py-2.5 bg-blue-600 text-white rounded-xl text-xs sm:text-sm font-bold disabled:opacity-50 cursor-pointer hover:bg-blue-700 transition-colors w-full sm:w-auto"
											>
												{isCreatingReview
													? '...'
													: t(translations, 'submit_review', 'Submit Review')}
											</button>
										</div>
									</form>

									<div className="space-y-3 sm:space-y-4">
										{reviews.map((review) => {
											const rawUsername = review.user?.tg_username;
											const isAnonDisplay =
												!rawUsername || rawUsername.toLowerCase() === 'anonymous';
											const photoUrl = resolveAvatarUrl(review.user?.photo);
											const isEditing = editingReviewId === review.id;

											return (
												<div
													key={review.id}
													className="p-3 sm:p-4 border border-gray-200 dark:border-gray-800 rounded-xl bg-white dark:bg-gray-950"
												>
													<div className="flex justify-between items-start mb-2 sm:mb-3">
														<div className="flex items-center gap-2">
															<div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden shrink-0">
																{photoUrl && !isAnonDisplay ? (
																	<img
																		src={
																			photoUrl ||
																			'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
																		}
																		alt="avatar"
																		className="w-full h-full object-cover"
																	/>
																) : (
																	<UserIcon size={14} className="text-gray-400 sm:w-4 sm:h-4" />
																)}
															</div>
															<div className="flex flex-col leading-tight">
																{isAnonDisplay ? (
																	<span className="font-bold text-xs sm:text-sm text-gray-900 dark:text-white">
																		{t(translations, 'anonymous', 'Anonymous')}
																	</span>
																) : (
																	<button
																		onClick={(e) => handleUserLinkClick(e, rawUsername!)}
																		className="font-bold text-left text-xs sm:text-sm text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
																	>
																		@{rawUsername}
																	</button>
																)}
															</div>
														</div>

														<div className="flex items-center gap-2">
															{review.date && (
																<span className="text-[10px] sm:text-xs font-medium text-gray-500 dark:text-gray-400 ml-auto px-2">
																	{review.date}
																</span>
															)}
															{review.is_author && !isEditing && (
																<div className="flex items-center gap-1 sm:gap-2">
																	{reviewToDelete === review.id ? (
																		<div className="flex items-center gap-1 bg-rose-50 dark:bg-rose-500/10 p-0.5 rounded-lg border border-rose-100 dark:border-rose-500/30">
																			<button
																				onClick={() => confirmDeleteReview(review.id)}
																				className="p-1 sm:p-1.5 text-rose-600 dark:text-rose-400 hover:bg-rose-200 dark:hover:bg-rose-500/30 rounded-md transition-colors cursor-pointer"
																				aria-label="Confirm delete"
																			>
																				<Check size={14} className="sm:w-4 sm:h-4 stroke-[3]" />
																			</button>
																			<div className="w-px h-3.5 bg-rose-200 dark:bg-rose-500/30"></div>
																			<button
																				onClick={() => setReviewToDelete(null)}
																				className="p-1 sm:p-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors cursor-pointer"
																				aria-label="Cancel delete"
																			>
																				<X size={14} className="sm:w-4 sm:h-4 stroke-[3]" />
																			</button>
																		</div>
																	) : (
																		<>
																			<button
																				onClick={() => {
																					setEditingReviewId(review.id);
																					setEditReviewText(review.text || '');
																					setEditReviewRating(review.rating || 5);
																					setReviewToDelete(null);
																				}}
																				className="p-1.5 text-gray-400 hover:text-blue-500 transition-colors cursor-pointer"
																				title={t(translations, 'edit', 'Edit')}
																			>
																				<Edit2 size={14} className="sm:w-4 sm:h-4" />
																			</button>
																			<button
																				onClick={() => setReviewToDelete(review.id)}
																				className="p-1.5 text-gray-400 hover:text-rose-500 transition-colors cursor-pointer"
																				title={t(translations, 'delete', 'Delete')}
																			>
																				<Trash2 size={14} className="sm:w-4 sm:h-4" />
																			</button>
																		</>
																	)}
																</div>
															)}
														</div>
													</div>

													{isEditing ? (
														<form onSubmit={(e) => handleEditSubmit(e, review.id)} className="mt-2">
															<div className="flex gap-1 mb-2">
																{[1, 2, 3, 4, 5].map((star) => (
																	<button
																		type="button"
																		key={star}
																		onClick={() => setEditReviewRating(star)}
																		className="cursor-pointer p-0.5"
																	>
																		<Star
																			size={14}
																			className={`sm:w-4 sm:h-4 ${star <= editReviewRating ? 'fill-yellow-500 text-yellow-500' : 'text-gray-300 dark:text-gray-700'}`}
																		/>
																	</button>
																))}
															</div>
															<textarea
																value={editReviewText}
																onChange={(e) => setEditReviewText(e.target.value)}
																className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg p-2 text-xs sm:text-sm focus:border-blue-500 outline-none mb-2 text-gray-900 dark:text-white resize-none"
																rows={3}
																required
															/>
															<div className="flex justify-end gap-2">
																<button
																	type="button"
																	onClick={() => setEditingReviewId(null)}
																	className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg text-xs font-bold hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors cursor-pointer"
																>
																	{t(translations, 'cancel', 'Cancel')}
																</button>
																<button
																	type="submit"
																	disabled={isUpdatingReview}
																	className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold disabled:opacity-50 cursor-pointer hover:bg-blue-700 transition-colors"
																>
																	{isUpdatingReview
																		? '...'
																		: t(translations, 'save_changes', 'Save Changes')}
																</button>
															</div>
														</form>
													) : (
														<>
															<div className="flex items-center gap-1 text-yellow-500 text-[10px] sm:text-xs font-bold mb-1.5 sm:mb-2">
																<Star size={10} className="fill-yellow-500 sm:w-3 sm:h-3" />{' '}
																{review.rating}
															</div>
															<p className="text-xs sm:text-sm text-gray-900 dark:text-gray-100 font-medium leading-relaxed mb-2 sm:mb-3">
																{review.text}
															</p>

															{review.photos && review.photos.length > 0 && (
																<div className="flex flex-wrap gap-2 mb-2 sm:mb-3">
																	{review.photos.map((photo) => (
																		<button
																			key={photo.id}
																			onClick={(e) => {
																				e.stopPropagation();
																				setZoomedReviewPhoto(
																					photo.image ||
																						'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found',
																				);
																			}}
																			className="w-12 h-12 sm:w-16 sm:h-16 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-800 shrink-0 cursor-pointer hover:opacity-80 transition-opacity"
																		>
																			<img
																				src={
																					photo.image ||
																					'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
																				}
																				alt="Review attachment"
																				loading="lazy"
																				className="w-full h-full object-cover"
																			/>
																		</button>
																	))}
																</div>
															)}
														</>
													)}

													{review.admin_reply_text && !isEditing && (
														<div className="mt-2.5 sm:mt-3 bg-blue-50 dark:bg-blue-900/10 p-2.5 sm:p-3 rounded-lg border border-blue-100 dark:border-blue-900/30">
															<span className="text-[9px] sm:text-[10px] uppercase tracking-wider font-bold text-blue-600 dark:text-blue-400 block mb-1">
																{t(translations, 'admin_reply', 'Admin Reply')}
															</span>
															<p className="text-xs sm:text-sm font-medium text-blue-900 dark:text-blue-100">
																{review.admin_reply_text}
															</p>
														</div>
													)}
												</div>
											);
										})}
										{hasNextPage && (
											<button
												onClick={() => fetchNextPage()}
												className="w-full py-2.5 sm:py-3 text-xs sm:text-sm text-blue-600 dark:text-blue-400 font-bold bg-blue-50 dark:bg-blue-500/10 rounded-xl hover:bg-blue-100 dark:hover:bg-blue-500/20 transition-colors cursor-pointer"
											>
												{t(translations, 'load_more_reviews', 'Load More Reviews')}
											</button>
										)}
									</div>
								</div>
							</div>
						</div>

						{/* Bottom Action Bar */}
						<div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 z-20">
							<button
								onClick={() => {
									if (canAddToCart && selectedVariantId)
										updateQuantity({
											variantId: Number(selectedVariantId),
											quantity: cartQuantity + 1,
										});
								}}
								disabled={!canAddToCart || isUpdating}
								className={`w-full py-3 sm:py-4 rounded-xl sm:rounded-2xl font-bold flex items-center justify-center gap-1.5 sm:gap-2 transition-all shadow-lg text-sm sm:text-base ${canAddToCart && !isUpdating ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-blue-900/30 active:scale-[0.98] cursor-pointer' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-200 dark:border-gray-700'}`}
							>
								{isUpdating ? (
									<div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-gray-400/30 border-t-gray-500 rounded-full animate-spin" />
								) : canAddToCart ? (
									<>
										{t(translations, 'add_to_cart', 'Add to Cart')}{' '}
										<span className="font-normal opacity-80">· ${displayPrice.toFixed(2)}</span>
										{cartQuantity > 0 && (
											<span className="ml-1.5 sm:ml-2 px-1.5 sm:px-2 py-0.5 bg-white/20 rounded-full text-[10px] sm:text-xs animate-pulse">
												{cartQuantity} {t(translations, 'in_cart', 'in cart')}
											</span>
										)}
									</>
								) : isOutOfStock ? (
									t(translations, 'out_of_stock', 'Out of Stock')
								) : isLoadingVariants ? (
									t(translations, 'loading_variants', 'Loading variants...')
								) : (
									t(translations, 'unavailable', 'Unavailable Combination')
								)}
							</button>
							{cartQuantity > 0 && (
								<div className="mt-2 flex justify-end">
									<button
										onClick={() => {
											onClose();
											navigate('/cart');
										}}
										className="px-3 py-1.5 text-[10px] sm:text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 border border-blue-200 dark:border-blue-500/30 rounded-full transition-colors cursor-pointer"
									>
										{t(translations, 'go_to_cart', 'Go to Cart')}
									</button>
								</div>
							)}
						</div>
					</>
				)}
			</motion.div>

			<AnimatePresence>
				{(isZoomed || zoomedReviewPhoto) && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						className="fixed inset-0 z-[200] bg-white dark:bg-black flex flex-col items-center justify-center overscroll-none touch-none"
						onClick={(e) => e.stopPropagation()}
					>
						<button
							onClick={(e) => {
								e.stopPropagation();
								setIsZoomed(false);
								setZoomedReviewPhoto(null);
							}}
							className="absolute top-4 right-4 z-[210] w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center bg-gray-200/80 dark:bg-gray-800/80 backdrop-blur-md rounded-full text-gray-900 dark:text-white shadow-md hover:bg-gray-300 dark:hover:bg-gray-700 transition-colors cursor-pointer"
						>
							<X size={20} className="sm:w-6 sm:h-6" />
						</button>
						<div className="flex-1 w-full h-full flex items-center justify-center overflow-hidden">
							<TransformWrapper initialScale={1} minScale={1} maxScale={5} centerOnInit>
								<TransformComponent
									wrapperClass="!w-full !h-full"
									contentClass="!w-full !h-full flex items-center justify-center"
								>
									<img
										src={zoomedReviewPhoto || mediaItems[activeMediaIndex]?.url}
										alt="Zoomed"
										loading="lazy"
										decoding="async"
										className="max-w-full max-h-full object-contain pointer-events-auto select-none"
									/>
								</TransformComponent>
							</TransformWrapper>
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</motion.div>
	);
}

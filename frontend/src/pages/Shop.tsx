import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useLocation, useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
	Search,
	SlidersHorizontal,
	X,
	ArrowUpRight,
	ArrowDownRight,
	Tag,
	ShoppingBag,
	Check,
	Heart,
	Star,
} from 'lucide-react';

import { useProducts } from '@/hooks/queries/useProducts';
import { useCategories } from '@/hooks/queries/useCategories';
import { useTags } from '@/hooks/queries/useTags';
import { useSuggestions } from '@/hooks/queries/useSuggestions';
import { useFavorites } from '@/hooks/mutations/useFavorites';
import { useConfig } from '@/store/ConfigContext';
import { ShopSkeleton } from '@/components/skeletons/ShopSkeleton';
import type { Product, ProductFilters } from '@/types/product';
import { ProductModal } from '@/components/ProductModal';
import type { CategoryWithSlug } from '@/hooks/queries/useCategories';
import type { TagWithSlug } from '@/hooks/queries/useTags';

const DEFAULT_FILTERS: ProductFilters = {
	search: '',
	minPrice: '',
	maxPrice: '',
	inStock: false,
	isFavorite: false,
	isNew: false,
	isPromotion: false,
};

type OrderOption = NonNullable<ProductFilters['ordering']>;

const SORT_OPTIONS: { val: OrderOption; label: string; fallback: string }[] = [
	{ val: 'price', label: 'price_asc', fallback: 'Price: Low to High' },
	{ val: '-price', label: 'price_desc', fallback: 'Price: High to Low' },
	{ val: '-date', label: 'date_desc', fallback: 'Newest Arrivals' },
	{ val: 'date', label: 'date_asc', fallback: 'Oldest First' },
	{ val: 'name', label: 'name_asc', fallback: 'Name: A to Z' },
	{ val: '-name', label: 'name_desc', fallback: 'Name: Z to A' },
];

const PRODUCT_TYPES: { val: 'all' | 'DIGITAL' | 'PHYSICAL'; label: string; fallback: string }[] = [
	{ val: 'all', label: 'all', fallback: 'All' },
	{ val: 'PHYSICAL', label: 'physical', fallback: 'Physical' },
	{ val: 'DIGITAL', label: 'digital', fallback: 'Digital' },
];

interface FilterDict {
	header?: string;
	placeholder?: string;
	sort_by?: Record<string, string>;
	price_range?: Record<string, string>;
	categories?: Record<string, string>;
	tags?: Record<string, string>;
	toggles?: Record<string, string>;
	product_type?: Record<string, string>;
	buttons?: Record<string, string>;
}

interface ShopTranslations {
	header?: string;
	filters?: FilterDict;
	messages?: Record<string, string>;
	badges?: Record<string, string>;
	search?: Record<string, string>;
	active_filters?: Record<string, string>;
}

const t = (dict: Record<string, string> | undefined, key: string, fallback: string): string => {
	return dict && dict[key] ? dict[key] : fallback;
};

const FilterCheckbox = ({
	checked,
	onChange,
	label,
}: {
	checked: boolean;
	onChange: () => void;
	label: string;
}) => (
	<button
		onClick={onChange}
		className="flex items-center gap-3 w-full group cursor-pointer text-left py-1"
	>
		<div
			className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${checked ? 'bg-blue-600 border-blue-600' : 'border-gray-400 dark:border-gray-600 group-hover:border-blue-500'}`}
		>
			{checked && <Check size={14} className="text-white" />}
		</div>
		<span
			className={`text-sm font-medium transition-colors ${checked ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white'}`}
		>
			{label}
		</span>
	</button>
);

const toggleMultiSelect = (current: string | undefined, item: string): string | undefined => {
	const arr = current ? current.split(',') : [];
	if (arr.includes(item)) {
		const filtered = arr.filter((i) => i !== item);
		return filtered.length > 0 ? filtered.join(',') : undefined;
	}
	return [...arr, item].join(',');
};

interface FilterBottomSheetProps {
	onClose: () => void;
	currentFilters: ProductFilters;
	onApply: (filters: ProductFilters) => void;
	onClear: () => void;
	tFilters?: FilterDict | undefined;
	categoriesData: CategoryWithSlug[];
	tagsData: TagWithSlug[];
}

function FilterBottomSheet({
	onClose,
	currentFilters,
	onApply,
	onClear,
	tFilters,
	categoriesData,
	tagsData,
}: FilterBottomSheetProps) {
	const [tempFilters, setTempFilters] = useState<ProductFilters>(currentFilters);

	return (
		<>
			<motion.div
				initial={{ opacity: 0 }}
				animate={{ opacity: 1 }}
				exit={{ opacity: 0 }}
				onClick={onClose}
				className="fixed inset-0 bg-black/60 z-40"
			/>
			<motion.div
				initial={{ y: '100%' }}
				animate={{ y: 0 }}
				exit={{ y: '100%' }}
				transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
				style={{ willChange: 'transform' }}
				className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white dark:bg-gray-900 rounded-t-3xl border-t border-x border-gray-200 dark:border-gray-800 z-50 flex flex-col max-h-[90vh] sm:shadow-2xl"
			>
				<div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-800">
					<h2 className="text-xl font-bold text-gray-900 dark:text-white">
						{t(tFilters as unknown as Record<string, string>, 'header', 'Filters & Sort')}
					</h2>
					<button
						onClick={onClose}
						className="p-2 -mr-2 text-gray-500 hover:text-gray-900 dark:hover:text-white bg-gray-100 dark:bg-gray-800 rounded-full cursor-pointer transition-colors"
					>
						<X size={20} />
					</button>
				</div>

				<div className="p-5 overflow-y-auto space-y-8 flex-1 [&::-webkit-scrollbar]:hidden">
					{/* Toggles */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
							{t(tFilters?.toggles, 'header', 'FEATURES')}
						</h3>
						<div className="grid grid-cols-2 gap-x-4 gap-y-3">
							<FilterCheckbox
								label={t(tFilters?.toggles, 'in_stock', 'In Stock Only')}
								checked={tempFilters.inStock || false}
								onChange={() => setTempFilters((p) => ({ ...p, inStock: !p.inStock }))}
							/>
							<FilterCheckbox
								label={t(tFilters?.toggles, 'is_favorite', 'Favorites Only')}
								checked={tempFilters.isFavorite || false}
								onChange={() => setTempFilters((p) => ({ ...p, isFavorite: !p.isFavorite }))}
							/>
							<FilterCheckbox
								label={t(tFilters?.toggles, 'is_new', 'New Arrivals')}
								checked={tempFilters.isNew || false}
								onChange={() => setTempFilters((p) => ({ ...p, isNew: !p.isNew }))}
							/>
							<FilterCheckbox
								label={t(tFilters?.toggles, 'is_promotion', 'On Sale')}
								checked={tempFilters.isPromotion || false}
								onChange={() => setTempFilters((p) => ({ ...p, isPromotion: !p.isPromotion }))}
							/>
						</div>
					</div>

					{/* Product Type */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
							{t(tFilters?.product_type, 'header', 'PRODUCT TYPE')}
						</h3>
						<div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
							{PRODUCT_TYPES.map((type) => {
								const isActive =
									(type.val === 'all' && !tempFilters.productType) ||
									tempFilters.productType === type.val;
								return (
									<button
										key={type.val}
										onClick={() =>
											setTempFilters((p) => {
												const next = { ...p };
												if (type.val === 'all') delete next.productType;
												else next.productType = type.val as 'DIGITAL' | 'PHYSICAL';
												return next;
											})
										}
										className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${isActive ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'}`}
									>
										{t(tFilters?.product_type, type.label, type.fallback)}
									</button>
								);
							})}
						</div>
					</div>

					{/* Sorting */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
							{t(tFilters?.sort_by, 'header', 'SORT BY')}
						</h3>
						<div className="grid grid-cols-2 gap-3">
							{SORT_OPTIONS.map((sort) => (
								<button
									key={sort.val}
									onClick={() =>
										setTempFilters((p) => {
											const next = { ...p };
											next.ordering = sort.val;
											return next;
										})
									}
									className={`py-3 px-4 rounded-xl text-sm font-medium border transition-colors cursor-pointer ${tempFilters.ordering === sort.val ? 'bg-blue-50 dark:bg-blue-600/10 border-blue-500 text-blue-600 dark:text-blue-400' : 'bg-gray-50 dark:bg-gray-800 border-transparent text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'}`}
								>
									{t(tFilters?.sort_by, sort.label, sort.fallback)}
								</button>
							))}
						</div>
					</div>

					{/* Price Range */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
							{t(tFilters?.price_range, 'header', 'PRICE RANGE')}
						</h3>
						<div className="flex items-center gap-3">
							<div className="relative flex-1">
								<span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium">
									$
								</span>
								<input
									type="number"
									placeholder={t(tFilters?.price_range, 'min', 'Min')}
									value={tempFilters.minPrice || ''}
									onChange={(e) => setTempFilters((p) => ({ ...p, minPrice: e.target.value }))}
									className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pl-8 pr-4 py-3 text-gray-900 dark:text-white focus:border-blue-500 outline-none transition-colors"
								/>
							</div>
							<span className="text-gray-400 font-medium">-</span>
							<div className="relative flex-1">
								<span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium">
									$
								</span>
								<input
									type="number"
									placeholder={t(tFilters?.price_range, 'max', 'Max')}
									value={tempFilters.maxPrice || ''}
									onChange={(e) => setTempFilters((p) => ({ ...p, maxPrice: e.target.value }))}
									className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl pl-8 pr-4 py-3 text-gray-900 dark:text-white focus:border-blue-500 outline-none transition-colors"
								/>
							</div>
						</div>
					</div>

					{/* Categories Multi-select */}
					{categoriesData.length > 0 && (
						<div>
							<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
								{t(tFilters?.categories, 'header', 'CATEGORIES')}
							</h3>
							<div className="flex flex-wrap gap-2">
								{categoriesData.map((cat) => {
									const isActive = (tempFilters.category?.split(',') || []).includes(cat.slug);
									return (
										<button
											key={cat.slug}
											onClick={() =>
												setTempFilters((p) => {
													const next = { ...p };
													const newVal = toggleMultiSelect(p.category, cat.slug);
													if (newVal) next.category = newVal;
													else delete next.category;
													return next;
												})
											}
											className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors cursor-pointer ${isActive ? 'bg-blue-600 text-white border-blue-500' : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}`}
										>
											{cat.name}
										</button>
									);
								})}
							</div>
						</div>
					)}

					{/* Tags Multi-select */}
					{tagsData.length > 0 && (
						<div>
							<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
								{t(tFilters?.tags, 'header', 'TAGS')}
							</h3>
							<div className="flex flex-wrap gap-2">
								{tagsData.map((tag) => {
									const isActive = (tempFilters.tag?.split(',') || []).includes(tag.slug);
									return (
										<button
											key={tag.slug}
											onClick={() =>
												setTempFilters((p) => {
													const next = { ...p };
													const newVal = toggleMultiSelect(p.tag, tag.slug);
													if (newVal) next.tag = newVal;
													else delete next.tag;
													return next;
												})
											}
											className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors cursor-pointer ${isActive ? 'bg-purple-600 text-white border-purple-500' : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-transparent hover:bg-gray-100 dark:hover:bg-gray-700'}`}
										>
											<Tag size={12} className="inline mr-1 -mt-0.5" />
											{tag.name}
										</button>
									);
								})}
							</div>
						</div>
					)}
				</div>

				{/* Action Buttons */}
				<div className="p-5 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 grid grid-cols-2 gap-3">
					<button
						onClick={onClear}
						className="py-4 font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl border border-gray-200 dark:border-gray-700 transition-colors cursor-pointer"
					>
						{t(tFilters?.buttons, 'clear', 'Clear All')}
					</button>
					<button
						onClick={() => onApply(tempFilters)}
						className="py-4 font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors cursor-pointer shadow-lg shadow-blue-500/20"
					>
						{t(tFilters?.buttons, 'apply', 'Apply Filters')}
					</button>
				</div>
			</motion.div>
		</>
	);
}

export function Shop() {
	const { config } = useConfig();
	const location = useLocation();
	const navigate = useNavigate();
	const [searchParams, setSearchParams] = useSearchParams();

	const shopConfig = (config?.translations as Record<string, unknown>)?.shop_page as
		| ShopTranslations
		| undefined;

	const tFilters = shopConfig?.filters;
	const tMessages = shopConfig?.messages;
	const tSearch = shopConfig?.search;
	const tActive = shopConfig?.active_filters;

	const [filters, setFilters] = useState<ProductFilters>(DEFAULT_FILTERS);
	const [isFilterOpen, setIsFilterOpen] = useState(false);
	const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

	const [searchInput, setSearchInput] = useState('');
	const [debouncedSearch, setDebouncedSearch] = useState('');
	const [showSuggestions, setShowSuggestions] = useState(false);
	const searchContainerRef = useRef<HTMLDivElement>(null);

	const [localFavs, setLocalFavs] = useState<Record<string, boolean>>({});

	const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } =
		useProducts(filters);
	const { data: categoriesData = [] } = useCategories();
	const { data: tagsData = [] } = useTags();
	const { data: suggestionsData = [], isFetching: isFetchingSuggestions } =
		useSuggestions(debouncedSearch);
	const { addFavorite, removeFavorite } = useFavorites();

	const productsData = useMemo<Product[]>(
		() => data?.pages?.flatMap((page) => page.products) || [],
		[data],
	);

	useEffect(() => {
		const stateProduct = location.state?.openProduct as Product | undefined;
		const targetId = searchParams.get('product') || stateProduct?.id;

		if (targetId) {
			const fullProduct = productsData.find((p) => String(p.id) === String(targetId));

			if (fullProduct || stateProduct) {
				setTimeout(() => {
					setSelectedProduct(fullProduct || stateProduct!);
				}, 0);
			}
		}
	}, [location.state, searchParams, productsData]);

	const handleCloseProductModal = useCallback(() => {
		setSelectedProduct(null);

		const nextParams = new URLSearchParams(searchParams);
		if (nextParams.has('product') || nextParams.has('variant')) {
			nextParams.delete('product');
			nextParams.delete('variant');
			setSearchParams(nextParams, { replace: true, state: null });
		} else if (location.state) {
			navigate('.', { replace: true, state: null });
		}
	}, [searchParams, setSearchParams, location.state, navigate]);

	const activeFilterCount = useMemo(() => {
		let count = 0;
		if (filters.minPrice || filters.maxPrice) count++;
		if (filters.category) count += filters.category.split(',').length;
		if (filters.tag) count += filters.tag.split(',').length;
		if (filters.ordering) count++;
		if (filters.inStock) count++;
		if (filters.isFavorite) count++;
		if (filters.isNew) count++;
		if (filters.isPromotion) count++;
		if (filters.productType) count++;
		return count;
	}, [filters]);

	useEffect(() => {
		const timer = setTimeout(() => {
			setDebouncedSearch(searchInput);
			setFilters((prev) => (prev.search === searchInput ? prev : { ...prev, search: searchInput }));
		}, 300);
		return () => clearTimeout(timer);
	}, [searchInput]);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				searchContainerRef.current &&
				!searchContainerRef.current.contains(event.target as Node)
			) {
				setShowSuggestions(false);
			}
		};
		document.addEventListener('mousedown', handleClickOutside);
		return () => document.removeEventListener('mousedown', handleClickOutside);
	}, []);

	const clearFilters = () => {
		setSearchInput('');
		setDebouncedSearch('');
		setFilters({ ...DEFAULT_FILTERS });
	};

	const removeSpecificFilter = (type: keyof ProductFilters, valueToRemove?: string) => {
		setFilters((prev) => {
			const updated = { ...prev };

			if (type === 'minPrice' || type === 'maxPrice') {
				delete updated.minPrice;
				delete updated.maxPrice;
			} else if (type === 'category' && valueToRemove && typeof updated.category === 'string') {
				const newVal = toggleMultiSelect(updated.category, valueToRemove);
				if (newVal) updated.category = newVal;
				else delete updated.category;
			} else if (type === 'tag' && valueToRemove && typeof updated.tag === 'string') {
				const newVal = toggleMultiSelect(updated.tag, valueToRemove);
				if (newVal) updated.tag = newVal;
				else delete updated.tag;
			} else {
				delete updated[type];
			}

			return updated;
		});
	};

	const handleSelectSuggestion = (suggestionName: string) => {
		setSearchInput(suggestionName);
		setDebouncedSearch(suggestionName);
		setFilters((prev) => ({ ...prev, search: suggestionName }));
		setShowSuggestions(false);
	};

	const handleToggleFavorite = (e: React.MouseEvent, product: Product) => {
		e.stopPropagation();
		const numericId = Number(product.id);
		const currentStatus = localFavs[product.id] ?? product.isFavorite;
		const newStatus = !currentStatus;

		setLocalFavs((prev) => ({ ...prev, [product.id]: newStatus }));

		if (currentStatus) {
			removeFavorite(numericId).catch(() =>
				setLocalFavs((prev) => ({ ...prev, [product.id]: currentStatus })),
			);
		} else {
			addFavorite(numericId).catch(() =>
				setLocalFavs((prev) => ({ ...prev, [product.id]: currentStatus })),
			);
		}
	};

	if (isError) {
		return (
			<div className="flex justify-center items-center h-full py-20">
				<p className="text-red-500 font-medium">
					{t(tMessages, 'error', 'Failed to load products.')}
				</p>
			</div>
		);
	}

	return (
		<div className="flex flex-col min-h-full pb-[100px]">
			<div className="sticky top-0 z-30 bg-white dark:bg-gray-950 pt-4 pb-3 px-4 border-b border-gray-200 dark:border-gray-800">
				<div className="flex gap-2 max-w-7xl mx-auto w-full">
					<div className="relative flex-1" ref={searchContainerRef}>
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
						<input
							type="text"
							placeholder={t(
								tFilters as unknown as Record<string, string>,
								'placeholder',
								'Search products...',
							)}
							value={searchInput}
							onChange={(e) => {
								setSearchInput(e.target.value);
								setShowSuggestions(true);
							}}
							onFocus={() => setShowSuggestions(true)}
							className="w-full bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 text-gray-900 dark:text-white rounded-xl pl-10 pr-4 py-3 text-sm focus:outline-none focus:border-blue-500 placeholder:text-gray-500"
						/>
						{searchInput && (
							<button
								onClick={() => {
									setSearchInput('');
									setDebouncedSearch('');
								}}
								className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-900 dark:hover:text-white cursor-pointer"
							>
								<X size={16} />
							</button>
						)}

						<AnimatePresence>
							{showSuggestions && debouncedSearch.trim().length > 1 && (
								<motion.div
									initial={{ opacity: 0, y: -10 }}
									animate={{ opacity: 1, y: 0 }}
									exit={{ opacity: 0, y: -10 }}
									className="absolute top-full mt-2 left-0 w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-xl z-50 overflow-hidden"
								>
									{isFetchingSuggestions ? (
										<div className="p-4 text-center text-sm text-gray-500">
											{t(tMessages, 'loading', 'Loading...')}
										</div>
									) : suggestionsData.length === 0 ? (
										<div className="p-4 text-center text-sm text-gray-500">
											{t(tSearch, 'suggestions_empty', 'No matches found')}
										</div>
									) : (
										<div className="flex flex-col max-h-60 overflow-y-auto">
											{suggestionsData.map((suggestion: { id: number; name: string }) => (
												<button
													key={suggestion.id}
													onClick={() => handleSelectSuggestion(suggestion.name)}
													className="px-4 py-3 text-left text-sm text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-800/50 last:border-0 transition-colors truncate cursor-pointer"
												>
													{suggestion.name}
												</button>
											))}
										</div>
									)}
								</motion.div>
							)}
						</AnimatePresence>
					</div>
					<button
						onClick={() => setIsFilterOpen(true)}
						className="w-12 bg-blue-50 dark:bg-blue-600/10 text-blue-600 dark:text-blue-500 border border-blue-200 dark:border-blue-500/20 rounded-xl flex items-center justify-center hover:bg-blue-600 hover:text-white relative cursor-pointer transition-colors"
					>
						<SlidersHorizontal size={20} />
						{activeFilterCount > 0 && (
							<span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-gray-950">
								{activeFilterCount}
							</span>
						)}
					</button>
				</div>

				{/* Active Filters Horizontal Scroll */}
				{activeFilterCount > 0 && (
					<div className="max-w-7xl mx-auto w-full mt-3">
						<div className="flex overflow-x-auto gap-2 pb-1 [&::-webkit-scrollbar]:hidden">
							{filters.ordering && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 rounded-lg text-xs font-medium text-gray-200 whitespace-nowrap">
									{filters.ordering.includes('price') ? (
										filters.ordering.includes('-') ? (
											<ArrowDownRight size={14} className="text-red-400" />
										) : (
											<ArrowUpRight size={14} className="text-emerald-400" />
										)
									) : null}
									{t(tActive, 'sort_applied', 'Sort Applied')}
									<button
										onClick={() => removeSpecificFilter('ordering')}
										className="ml-1 text-gray-500 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
							{(filters.minPrice || filters.maxPrice) && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 rounded-lg text-xs font-medium text-gray-200 whitespace-nowrap">
									{t(tActive, 'price', 'Price')}: ${filters.minPrice || '0'} - $
									{filters.maxPrice || '∞'}
									<button
										onClick={() => removeSpecificFilter('minPrice')}
										className="ml-1 text-gray-500 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
							{filters.category &&
								filters.category.split(',').map((slug) => {
									const catName = categoriesData.find((c) => c.slug === slug)?.name || slug;
									return (
										<div
											key={`cat-${slug}`}
											className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-900/30 text-blue-400 rounded-lg text-xs font-medium whitespace-nowrap"
										>
											{catName}
											<button
												onClick={() => removeSpecificFilter('category', slug)}
												className="ml-1 text-blue-400 hover:text-white cursor-pointer"
											>
												<X size={12} />
											</button>
										</div>
									);
								})}
							{filters.tag &&
								filters.tag.split(',').map((slug) => {
									const tagName = tagsData.find((t) => t.slug === slug)?.name || slug;
									return (
										<div
											key={`tag-${slug}`}
											className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-900/30 text-purple-400 rounded-lg text-xs font-medium whitespace-nowrap"
										>
											<Tag size={12} /> {tagName}
											<button
												onClick={() => removeSpecificFilter('tag', slug)}
												className="ml-1 text-purple-400 hover:text-white cursor-pointer"
											>
												<X size={12} />
											</button>
										</div>
									);
								})}
							{filters.inStock && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-900/30 text-emerald-400 rounded-lg text-xs font-medium whitespace-nowrap">
									{t(tActive, 'in_stock', 'In Stock')}{' '}
									<button
										onClick={() => removeSpecificFilter('inStock')}
										className="ml-1 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
							{filters.isNew && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-900/30 text-amber-400 rounded-lg text-xs font-medium whitespace-nowrap">
									{t(tActive, 'new', 'New')}{' '}
									<button
										onClick={() => removeSpecificFilter('isNew')}
										className="ml-1 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
							{filters.isPromotion && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-900/30 text-rose-400 rounded-lg text-xs font-medium whitespace-nowrap">
									{t(tActive, 'promo', 'Promo')}{' '}
									<button
										onClick={() => removeSpecificFilter('isPromotion')}
										className="ml-1 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
							{filters.isFavorite && (
								<div className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-900/30 text-rose-400 rounded-lg text-xs font-medium whitespace-nowrap">
									{t(tActive, 'favorites', 'Favorites')}{' '}
									<button
										onClick={() => removeSpecificFilter('isFavorite')}
										className="ml-1 hover:text-white cursor-pointer"
									>
										<X size={12} />
									</button>
								</div>
							)}
						</div>
					</div>
				)}
			</div>

			<div className="p-4 flex-1 max-w-7xl mx-auto w-full z-10">
				{isLoading ? (
					<ShopSkeleton />
				) : productsData.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-20 text-center">
						<Search className="w-16 h-16 text-gray-800 mb-4" />
						<h3 className="text-xl font-bold text-gray-200 mb-2">
							{t(tMessages, 'empty', 'No products found')}
						</h3>
						<button
							onClick={clearFilters}
							className="mt-4 px-6 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl font-medium cursor-pointer transition-colors"
						>
							{t(tMessages, 'clear_empty', 'Clear all filters')}
						</button>
					</div>
				) : (
					<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 sm:gap-4">
						{productsData.map((product: Product, idx: number) => {
							const dv = product.displayVariant;
							const price = dv?.price ?? 0;
							const oldPrice = dv?.oldPrice;
							const hasDiscount = typeof oldPrice === 'number' && oldPrice > price;
							const basketQuantity = dv?.basketQuantity ?? 0;
							const isFav = localFavs[product.id] ?? product.isFavorite;

							return (
								<motion.div
									key={product.id}
									initial={{ opacity: 0, y: 10 }}
									animate={{ opacity: 1, y: 0 }}
									transition={{ type: 'tween', duration: 0.2, delay: (idx % 10) * 0.03 }}
									style={{ willChange: 'transform, opacity' }}
									onClick={() => setSelectedProduct(product)}
									className="flex flex-col bg-white dark:bg-gray-900 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800/50 cursor-pointer sm:hover:shadow-xl transition-shadow duration-300 transform-gpu"
								>
									<div className="relative aspect-square overflow-hidden bg-gray-100 dark:bg-gray-800">
										<img
											src={
												product.mainImage ||
												'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
											}
											alt={product.name}
											className="w-full h-full object-cover"
											loading="lazy"
											decoding="async"
										/>
										<div className="absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-white to-transparent dark:from-gray-900 pointer-events-none z-0"></div>

										<button
											onClick={(e) => handleToggleFavorite(e, product)}
											className="absolute top-1.5 right-1.5 z-10 p-1.5 bg-white/80 dark:bg-black/60 rounded-full text-gray-500 hover:bg-white dark:hover:bg-black transition-colors shadow-sm cursor-pointer"
										>
											<Heart
												size={14}
												className={
													isFav ? 'fill-rose-500 text-rose-500' : 'text-gray-800 dark:text-white'
												}
											/>
										</button>

										<div className="absolute top-2 left-0 flex flex-col items-start gap-1 z-10 pointer-events-none max-w-[85%]">
											{dv?.isNew && (
												<div className="bg-emerald-500/95 text-white pr-2 pl-1.5 py-0.5 rounded-r-md text-[8px] font-bold uppercase tracking-wider shadow-sm truncate w-full">
													{shopConfig?.badges?.new || 'New'}
												</div>
											)}
											{dv?.isPromotion && (
												<div
													className={`bg-rose-500/95 text-white pr-2 pl-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider shadow-sm truncate w-full ${dv?.isNew ? 'rounded-r-md mt-[1px]' : 'rounded-r-md'}`}
												>
													{shopConfig?.badges?.sale || 'Sale'}{' '}
													{dv.promotionDiscount && dv.promotionDiscount > 0
														? `-${dv.promotionDiscount}%`
														: ''}
												</div>
											)}
											{dv?.badge && !dv?.isNew && !dv?.isPromotion && (
												<div className="bg-gray-900/80 dark:bg-gray-100/20 text-white pr-2 pl-1.5 py-0.5 rounded-r-md text-[8px] font-bold uppercase tracking-wider shadow-sm truncate w-full mt-[1px]">
													{dv.badge}
												</div>
											)}
										</div>
										{basketQuantity > 0 && (
											<div className="absolute bottom-1.5 right-1.5 bg-green-500/90 text-white px-1.5 py-0.5 rounded-md text-[9px] font-bold z-10 flex items-center gap-1 shadow-sm">
												<ShoppingBag size={10} /> {basketQuantity}
											</div>
										)}
									</div>

									<div className="p-2 flex flex-col flex-1 z-10">
										<span className="text-[9px] uppercase tracking-wider text-gray-500 font-bold mb-0.5 truncate">
											{product.category}
										</span>
										<h3 className="text-xs font-semibold leading-snug mb-1 flex-1 dark:text-gray-200 line-clamp-2">
											{product.name}
										</h3>

										<div className="flex items-center gap-1.5 mb-1.5 text-[9px] text-gray-500 dark:text-gray-400 font-medium">
											<div className="flex items-center gap-0.5 text-yellow-500">
												<Star size={8} className="fill-yellow-500" />
												<span>{product.averageRating?.toFixed(1) || '0.0'}</span>
											</div>
											<span>•</span>
											<span>
												{product.purchasesCount || 0} {shopConfig?.badges?.sold || 'sold'}
											</span>
										</div>

										<div className="flex items-end justify-between mt-auto">
											<div className="flex flex-col leading-none">
												{hasDiscount && (
													<span className="text-[9px] text-gray-400 line-through mb-0.5">
														${oldPrice.toFixed(2)}
													</span>
												)}
												<span
													className={`font-bold text-sm ${hasDiscount ? 'text-rose-500' : 'dark:text-white'}`}
												>
													${price.toFixed(2)}
												</span>
											</div>
										</div>
									</div>
								</motion.div>
							);
						})}

						{hasNextPage && (
							<div className="flex justify-center mt-6 w-full col-span-full">
								<button
									onClick={() => fetchNextPage()}
									disabled={isFetchingNextPage}
									className="w-full sm:w-auto px-8 py-3.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl font-medium disabled:opacity-50 cursor-pointer transition-colors flex items-center justify-center"
								>
									{isFetchingNextPage ? (
										<div className="w-4 h-4 border-2 border-gray-400/30 border-t-gray-200 rounded-full animate-spin" />
									) : (
										t(tMessages, 'load_more', 'Show More Products')
									)}
								</button>
							</div>
						)}
					</div>
				)}
			</div>

			<AnimatePresence>
				{isFilterOpen && (
					<FilterBottomSheet
						onClose={() => setIsFilterOpen(false)}
						currentFilters={filters}
						tFilters={tFilters}
						categoriesData={categoriesData}
						tagsData={tagsData}
						onClear={() => {
							clearFilters();
							setIsFilterOpen(false);
						}}
						onApply={(newFilters) => {
							setFilters(newFilters);
							setIsFilterOpen(false);
						}}
					/>
				)}
			</AnimatePresence>

			<AnimatePresence>
				{selectedProduct && (
					<ProductModal
						key="product-modal"
						product={selectedProduct}
						onClose={handleCloseProductModal}
					/>
				)}
			</AnimatePresence>
		</div>
	);
}

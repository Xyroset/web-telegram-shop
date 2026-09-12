import { X } from 'lucide-react';

interface ProductModalSkeletonProps {
	onClose: () => void;
}

/**
 * Inner skeleton content for the Product Modal.
 */
export function ProductModalSkeleton({ onClose }: ProductModalSkeletonProps) {
	return (
		<>
			{/* Header Actions Placeholder */}
			<div className="absolute top-4 right-4 z-[60] flex gap-2 pointer-events-auto">
				<div className="w-9 h-9 sm:w-10 sm:h-10 bg-gray-200 dark:bg-gray-800 rounded-full animate-pulse" />
				<button
					onClick={onClose}
					className="w-9 h-9 sm:w-10 sm:h-10 bg-white/95 dark:bg-gray-800/95 shadow-sm rounded-full flex items-center justify-center hover:bg-white dark:hover:bg-gray-700 transition-colors cursor-pointer"
				>
					<X size={18} className="text-gray-800 dark:text-white" />
				</button>
			</div>

			<div className="flex-1 overflow-y-auto pb-24 sm:pb-28 [&::-webkit-scrollbar]:hidden">
				{/* Media Gallery Placeholder */}
				<div className="relative aspect-[4/3] sm:aspect-square w-full bg-gray-200 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 animate-pulse" />

				<div className="p-4 sm:p-5 space-y-4 sm:space-y-6">
					{/* Title & Category */}
					<div>
						<div className="w-20 h-3 bg-gray-200 dark:bg-gray-800 rounded mb-2 animate-pulse" />
						<div className="w-3/4 h-6 sm:h-8 bg-gray-200 dark:bg-gray-800 rounded mb-4 animate-pulse" />

						{/* Price */}
						<div className="w-1/3 h-8 sm:h-10 bg-gray-200 dark:bg-gray-800 rounded mb-2 animate-pulse" />
					</div>

					{/* Variants Placeholder */}
					<div className="pt-4 border-t border-gray-200 dark:border-gray-800">
						<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded mb-3 animate-pulse" />
						<div className="flex gap-2">
							<div className="w-16 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
							<div className="w-16 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
							<div className="w-16 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
						</div>
					</div>

					{/* Description Placeholder */}
					<div className="pt-4 border-t border-gray-200 dark:border-gray-800">
						<div className="w-32 h-4 bg-gray-200 dark:bg-gray-800 rounded mb-3 animate-pulse" />
						<div className="space-y-2">
							<div className="w-full h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-full h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-4/5 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>
					</div>
				</div>
			</div>

			{/* Bottom Action Bar Placeholder */}
			<div className="absolute bottom-0 left-0 right-0 p-3 sm:p-4 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 z-20">
				<div className="w-full h-12 sm:h-14 bg-gray-200 dark:bg-gray-800 rounded-xl sm:rounded-2xl animate-pulse" />
			</div>
		</>
	);
}

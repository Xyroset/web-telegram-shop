export function CartSkeleton() {
	return (
		<div className="flex flex-col min-h-full">
			<div className="flex-1 p-3 sm:p-4 space-y-3 sm:space-y-4 max-w-4xl mx-auto w-full">
				{/* Delivery Gamification Banner Skeleton */}
				<div className="bg-white dark:bg-gray-900 p-3 sm:p-4 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm">
					<div className="flex items-start gap-3 mb-2.5 sm:mb-3">
						<div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gray-200 dark:bg-gray-800 shrink-0 mt-0.5 animate-pulse" />
						<div className="flex-1 space-y-2 py-1">
							<div className="w-2/3 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-1/2 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-1/3 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>
					</div>
					<div className="w-full h-8 bg-gray-200 dark:bg-gray-800 rounded-lg mt-2 animate-pulse" />
				</div>

				{/* Cart Items Skeleton (Render 2 placeholder items) */}
				{[1, 2].map((idx) => (
					<div
						key={idx}
						className="flex gap-3 sm:gap-4 bg-white dark:bg-gray-900 p-2.5 sm:p-3 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm"
					>
						{/* Product Image */}
						<div className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl bg-gray-200 dark:bg-gray-800 shrink-0 animate-pulse" />

						<div className="flex flex-col flex-1 justify-between py-0.5">
							<div className="flex justify-between items-start">
								<div className="space-y-2 flex-1 pr-4">
									<div className="w-full h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									<div className="w-1/2 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								</div>
								<div className="w-4 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse shrink-0" />
							</div>

							<div className="flex items-center justify-between mt-2">
								{/* Price */}
								<div className="w-16 h-5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								{/* Quantity Controls */}
								<div className="w-20 h-7 sm:h-8 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse" />
							</div>
						</div>
					</div>
				))}

				{/* Promo Code Skeleton */}
				<div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 p-3 sm:p-4 mt-2 shadow-sm">
					<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded mb-3 animate-pulse" />
					<div className="flex gap-2">
						<div className="flex-1 h-9 sm:h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
						<div className="w-20 h-9 sm:h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
					</div>
				</div>
			</div>

			{/* Checkout Bottom Bar Skeleton */}
			<div className="bg-white dark:bg-gray-900 p-3 sm:p-4 border-t border-gray-200 dark:border-gray-800 sticky bottom-0 z-10">
				<div className="max-w-4xl mx-auto w-full space-y-3 sm:space-y-4">
					<div className="flex justify-between items-center">
						<div className="w-20 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-16 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="flex justify-between items-center">
						<div className="w-24 h-5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-20 h-6 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full h-12 sm:h-14 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse mt-2" />
				</div>
			</div>
		</div>
	);
}

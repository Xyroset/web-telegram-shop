export function CheckoutSkeleton() {
	return (
		<div className="flex flex-col min-h-full pb-20 relative">
			<div className="p-3 sm:p-4 flex-1 max-w-3xl mx-auto w-full space-y-4">
				{/* Shipping & Contact Details Skeleton */}
				<div className="space-y-2">
					<div className="flex items-center gap-1.5 ml-1">
						<div className="w-4 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-48 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="bg-white dark:bg-gray-900 p-3 sm:p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
						<div className="flex items-start gap-2.5">
							<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 shrink-0 animate-pulse" />
							<div className="flex-1 space-y-3 py-1">
								<div className="flex justify-between items-start">
									<div className="space-y-2 flex-1">
										<div className="w-1/2 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
										<div className="w-2/3 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									</div>
									<div className="w-12 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse mt-1" />
								</div>
								<div className="pt-2.5 border-t border-gray-200 dark:border-gray-800 space-y-2">
									<div className="w-3/4 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									<div className="w-1/3 h-2 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								</div>
							</div>
						</div>
					</div>
				</div>

				{/* Order Summary Math Skeleton */}
				<div className="rounded-xl p-4 border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 space-y-3">
					{[1, 2, 3].map((i) => (
						<div key={i} className="flex justify-between items-center">
							<div className="w-24 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-16 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>
					))}
					<div className="border-t border-gray-200 dark:border-gray-800 pt-3 mt-1 flex justify-between items-end">
						<div className="w-20 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-24 h-6 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
				</div>

				{/* Payment Configuration Selects Skeleton */}
				<div className="space-y-3.5">
					{[1, 2, 3].map((i) => (
						<div key={i} className="space-y-1.5">
							<div className="w-32 h-3 bg-gray-200 dark:bg-gray-800 rounded ml-1 animate-pulse" />
							<div className="w-full h-12 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
						</div>
					))}
				</div>

				{/* Bottom Action Button Skeleton */}
				<div className="pt-2 space-y-3">
					<div className="flex justify-center">
						<div className="w-32 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full py-3.5 h-[52px] bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>
			</div>
		</div>
	);
}

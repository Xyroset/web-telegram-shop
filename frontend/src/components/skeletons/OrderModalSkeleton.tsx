export function OrderModalSkeleton({ onClose }: { onClose?: () => void }) {
	return (
		<div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 dark:bg-gray-950/80 p-0 sm:p-4">
			<div className="w-full h-[100dvh] sm:h-auto sm:max-h-[90vh] sm:max-w-xl bg-white dark:bg-gray-950 sm:rounded-3xl border border-gray-200 dark:border-gray-800 overflow-hidden flex flex-col relative sm:shadow-2xl mt-auto sm:mt-0">
				{/* Header Action Skeleton */}
				<div className="absolute top-4 right-4 z-10">
					<div
						onClick={onClose}
						className="w-8 h-8 bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-full cursor-pointer animate-pulse"
					/>
				</div>

				<div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5 [&::-webkit-scrollbar]:hidden">
					{/* Basic Order Info Skeleton */}
					<div className="pt-6 sm:pt-0">
						<div className="w-32 h-6 bg-gray-200 dark:bg-gray-800 rounded mb-3 animate-pulse" />

						<div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-3">
							{[1, 2, 3, 4].map((i) => (
								<div
									key={i}
									className={`flex justify-between items-center ${i !== 4 ? 'border-b border-gray-200 dark:border-gray-800/60 pb-2' : ''}`}
								>
									<div className="w-16 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								</div>
							))}
						</div>
					</div>

					{/* Delivery Info Skeleton */}
					<div>
						<div className="w-40 h-3 bg-gray-200 dark:bg-gray-800 rounded mb-2 animate-pulse" />
						<div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 space-y-3">
							<div className="flex items-start gap-2">
								<div className="w-3.5 h-3.5 bg-gray-200 dark:bg-gray-800 rounded-full shrink-0 animate-pulse mt-0.5" />
								<div className="space-y-1.5 flex-1">
									<div className="w-full h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									<div className="w-2/3 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								</div>
							</div>
							<div className="flex justify-between items-center border-t border-gray-200 dark:border-gray-800/60 pt-2">
								<div className="w-24 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								<div className="w-32 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							</div>
						</div>
					</div>

					{/* Order Items Skeleton */}
					<div>
						<div className="w-full flex items-center justify-between mb-2">
							<div className="w-24 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-4 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>

						<div className="space-y-2">
							{[1, 2].map((i) => (
								<div
									key={i}
									className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-2.5 flex items-center gap-3"
								>
									<div className="w-12 h-12 rounded-lg bg-gray-200 dark:bg-gray-800 shrink-0 animate-pulse" />
									<div className="flex-1 space-y-1.5">
										<div className="w-3/4 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
										<div className="w-1/2 h-2.5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
									</div>
									<div className="w-8 h-8 rounded-lg bg-gray-200 dark:bg-gray-800 shrink-0 animate-pulse" />
								</div>
							))}
						</div>
					</div>

					{/* Transactions Skeleton */}
					<div>
						<div className="w-full flex items-center justify-between mb-2">
							<div className="w-28 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-4 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

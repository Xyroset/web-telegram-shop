export function OrdersSkeleton() {
	return (
		<div className="p-3 sm:p-4 max-w-3xl mx-auto w-full pb-[100px] space-y-6">
			{/* Pending Orders Section Skeleton */}
			<div className="space-y-3">
				<div className="flex items-center gap-1.5 ml-1">
					<div className="w-3.5 h-3.5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					<div className="w-32 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
				</div>

				<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-3.5 flex flex-col gap-3 shadow-sm">
					{/* Header */}
					<div className="flex justify-between items-start border-b border-gray-200 dark:border-gray-800/60 pb-2.5">
						<div className="space-y-1">
							<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							<div className="w-16 h-2.5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						</div>
						<div className="w-20 h-5 bg-gray-200 dark:bg-gray-800 rounded-md animate-pulse" />
					</div>

					{/* Body Summary */}
					<div className="flex items-center justify-between py-1">
						<div className="flex -space-x-2 overflow-hidden">
							{[1, 2, 3].map((item) => (
								<div
									key={item}
									className="inline-block h-8 w-8 rounded-full ring-2 ring-white dark:ring-gray-900 bg-gray-200 dark:bg-gray-800 animate-pulse"
								/>
							))}
						</div>
						<div className="text-right space-y-1">
							<div className="w-12 h-2.5 bg-gray-200 dark:bg-gray-800 rounded ml-auto animate-pulse" />
							<div className="w-16 h-4 bg-gray-200 dark:bg-gray-800 rounded ml-auto animate-pulse" />
						</div>
					</div>

					{/* Actions */}
					<div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-800/60">
						<div className="flex-1 h-8 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse" />
						<div className="flex-[2] h-8 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse" />
					</div>
				</div>
			</div>

			{/* History Orders Section Skeleton */}
			<div className="space-y-3">
				<div className="flex items-center gap-1.5 ml-1">
					<div className="w-3.5 h-3.5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					<div className="w-28 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
				</div>

				{[1, 2].map((idx) => (
					<div
						key={idx}
						className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-3.5 flex flex-col gap-3 shadow-sm"
					>
						{/* Header */}
						<div className="flex justify-between items-start border-b border-gray-200 dark:border-gray-800/60 pb-2.5">
							<div className="space-y-1">
								<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
								<div className="w-16 h-2.5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
							</div>
							<div className="w-20 h-5 bg-gray-200 dark:bg-gray-800 rounded-md animate-pulse" />
						</div>

						{/* Body Summary */}
						<div className="flex items-center justify-between py-1">
							<div className="flex -space-x-2 overflow-hidden">
								{[1, 2].map((item) => (
									<div
										key={item}
										className="inline-block h-8 w-8 rounded-full ring-2 ring-white dark:ring-gray-900 bg-gray-200 dark:bg-gray-800 animate-pulse"
									/>
								))}
							</div>
							<div className="text-right space-y-1">
								<div className="w-12 h-2.5 bg-gray-200 dark:bg-gray-800 rounded ml-auto animate-pulse" />
								<div className="w-16 h-4 bg-gray-200 dark:bg-gray-800 rounded ml-auto animate-pulse" />
							</div>
						</div>

						{/* Action */}
						<div className="pt-2 border-t border-gray-200 dark:border-gray-800/60">
							<div className="w-full h-8 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse" />
						</div>
					</div>
				))}
			</div>

			{/* Pagination Skeleton */}
			<div className="flex items-center justify-between pt-2">
				<div className="w-24 h-8 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				<div className="w-20 h-8 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
			</div>
		</div>
	);
}

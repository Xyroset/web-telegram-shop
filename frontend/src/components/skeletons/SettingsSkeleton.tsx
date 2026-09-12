export function SettingsSkeleton() {
	return (
		<div className="p-4 space-y-6 max-w-3xl mx-auto w-full pb-64">
			{/* User Profile Header Skeleton */}
			<div className="flex flex-col items-center justify-center py-4">
				<div className="w-20 h-20 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse mb-3" />
				<div className="w-36 h-6 bg-gray-200 dark:bg-gray-800 rounded animate-pulse mb-2" />
				<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
			</div>

			{/* Configuration Options Card Skeleton */}
			<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm">
				{/* Language row */}
				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse" />
						<div className="w-24 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full sm:w-48 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>

				{/* Crypto Currency row */}
				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse" />
						<div className="w-32 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full sm:w-48 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>

				{/* Network row */}
				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse" />
						<div className="w-20 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full sm:w-48 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>

				{/* Background Effect row */}
				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse" />
						<div className="w-36 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-full sm:w-48 h-10 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>

				{/* Reset Button */}
				<div className="p-4">
					<div className="w-full h-11 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
				</div>
			</div>

			{/* Delivery Addresses Section Skeleton */}
			<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-sm">
				<div className="flex items-center justify-between mb-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse" />
						<div className="w-40 h-5 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="w-9 h-9 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse" />
				</div>

				{/* Address Cards Placeholders */}
				<div className="space-y-3">
					<div className="p-4 rounded-xl border-2 border-gray-100 dark:border-gray-800 space-y-2">
						<div className="w-32 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-3/4 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-1/2 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
					<div className="p-4 rounded-xl border-2 border-gray-100 dark:border-gray-800 space-y-2">
						<div className="w-28 h-4 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-2/3 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
						<div className="w-1/3 h-3 bg-gray-200 dark:bg-gray-800 rounded animate-pulse" />
					</div>
				</div>
			</div>
		</div>
	);
}

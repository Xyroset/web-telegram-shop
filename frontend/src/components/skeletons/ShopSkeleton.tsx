import { motion } from 'framer-motion';

export function ShopSkeleton() {
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			transition={{ duration: 0.3 }}
			className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 sm:gap-4 w-full"
		>
			{[...Array(12)].map((_, i) => (
				<div
					key={i}
					className="flex flex-col bg-white dark:bg-gray-900 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800/50"
				>
					<div className="aspect-square bg-gray-200 dark:bg-gray-800 animate-pulse" />

					<div className="p-2 flex flex-col flex-1 z-10">
						<div className="w-1/3 h-2 rounded bg-gray-200 dark:bg-gray-800 animate-pulse mb-1" />
						<div className="w-full h-3 rounded bg-gray-200 dark:bg-gray-800 animate-pulse mb-1.5" />
						<div className="w-1/2 h-2 rounded bg-gray-200 dark:bg-gray-800 animate-pulse mb-1.5" />

						<div className="mt-auto flex justify-between items-end">
							<div className="w-1/3 h-4 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
						</div>
					</div>
				</div>
			))}
		</motion.div>
	);
}

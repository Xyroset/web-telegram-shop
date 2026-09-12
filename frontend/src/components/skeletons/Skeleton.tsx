import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '@/store/ThemeContext';
import { useConfig } from '@/store/ConfigContext';

interface SkeletonProps {
	isLoading: boolean;
}

export function Skeleton({ isLoading }: SkeletonProps) {
	const { isDark } = useTheme();
	const { config } = useConfig();

	const bgStyles = (config?.background as Record<string, string>) || {};
	const defaultDarkBg =
		'radial-gradient(circle at 0% 0%, rgba(30, 58, 138, 0.3) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(88, 28, 135, 0.3) 0%, transparent 50%), radial-gradient(circle at 100% 40%, rgba(6, 78, 59, 0.2) 0%, transparent 50%)';
	const defaultLightBg =
		'radial-gradient(circle at 0% 0%, rgba(147, 197, 253, 0.5) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(216, 180, 254, 0.5) 0%, transparent 50%), radial-gradient(circle at 100% 40%, rgba(167, 243, 208, 0.4) 0%, transparent 50%)';

	const currentBackground = isDark
		? bgStyles.background_dark || defaultDarkBg
		: bgStyles.background_light || defaultLightBg;

	return (
		<AnimatePresence>
			{isLoading && (
				<motion.div
					initial={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={{ type: 'tween', duration: 0.3, ease: 'easeOut' }}
					style={{ willChange: 'opacity', backgroundImage: currentBackground }}
					className="fixed inset-0 z-[9999] flex flex-col bg-gray-50 dark:bg-gray-950 overflow-hidden"
				>
					<div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
						<div className="flex items-center gap-3">
							<div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
							<div className="w-24 h-6 rounded-md bg-gray-200 dark:bg-gray-700 animate-pulse" />
						</div>
						<div className="flex items-center gap-2">
							<div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
							<div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
							<div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse" />
						</div>
					</div>

					<div className="bg-white dark:bg-gray-950 pt-4 pb-3 px-4 border-b border-gray-200 dark:border-gray-800">
						<div className="flex gap-2 max-w-7xl mx-auto w-full">
							<div className="flex-1 h-12 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
							<div className="w-12 h-12 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
						</div>
					</div>

					<div className="p-4 flex-1 max-w-7xl mx-auto w-full">
						<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 sm:gap-4">
							{[...Array(12)].map((_, i) => (
								<div
									key={i}
									className="flex flex-col bg-white dark:bg-gray-900 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800/50"
								>
									<div className="aspect-square bg-gray-200 dark:bg-gray-800 animate-pulse" />

									<div className="p-3 flex flex-col gap-2 flex-1">
										<div className="w-1/3 h-2 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />
										<div className="w-full h-3 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />
										<div className="w-2/3 h-3 rounded bg-gray-200 dark:bg-gray-800 animate-pulse" />

										<div className="mt-auto pt-2 flex flex-col gap-1">
											<div className="w-1/2 h-4 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
										</div>
									</div>
								</div>
							))}
						</div>
					</div>
				</motion.div>
			)}
		</AnimatePresence>
	);
}

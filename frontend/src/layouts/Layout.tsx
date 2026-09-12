import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
	ChevronLeft,
	ShoppingBag,
	Settings,
	Package,
	Sun,
	Moon,
	User as UserIcon,
	ArrowUp,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLayoutEffect, useRef, useState, Suspense } from 'react';

import { useTheme } from '@/store/ThemeContext';
import { useCart } from '@/hooks/queries/useCart';
import { useUser } from '@/hooks/queries/useUser';
import { useConfig } from '@/store/ConfigContext';

import { BackgroundEffect } from '@/components/BackgroundEffect';
import { SupportWidget } from '@/components/SupportWidget';
import { Skeleton } from '@/components/skeletons/Skeleton';

interface FooterLinks {
	privacy_policy?: string;
	terms_of_service?: string;
	refund_policy?: string;
}

interface FooterConfig {
	company_name?: string;
	copyright_year?: string | number;
	support_email?: string;
	support_phone?: string;
	links?: FooterLinks;
}

export function Layout() {
	const navigate = useNavigate();
	const location = useLocation();

	const { isDark, toggleTheme } = useTheme();
	const { config } = useConfig();
	const { items: cartItems } = useCart();
	const { data: user } = useUser();

	const itemCount = cartItems.reduce((total, item) => total + item.quantity, 0);
	const mainRef = useRef<HTMLElement>(null);
	const shopScrollPosition = useRef<number>(0);

	const [showScrollTop, setShowScrollTop] = useState(false);
	const SCROLL_THRESHOLD = 300;

	useLayoutEffect(() => {
		if (mainRef.current) {
			requestAnimationFrame(() => {
				if (!mainRef.current) return;
				const restorePos = location.pathname === '/' ? shopScrollPosition.current : 0;
				mainRef.current.scrollTop = restorePos;
				setShowScrollTop(restorePos > SCROLL_THRESHOLD);
			});
		}
	}, [location.pathname]);

	const handleScroll = (e: React.UIEvent<HTMLElement>) => {
		const scrollTop = e.currentTarget.scrollTop;

		if (location.pathname === '/') {
			shopScrollPosition.current = scrollTop;
		}

		const shouldShow = scrollTop > SCROLL_THRESHOLD;
		if (shouldShow !== showScrollTop) {
			setShowScrollTop(shouldShow);
		}
	};

	const scrollToTop = () => {
		mainRef.current?.scrollTo({
			top: 0,
			behavior: 'smooth',
		});
	};

	const isHome = location.pathname === '/';
	const hideHeader = location.pathname === '/success';

	const headers = (config?.translations as Record<string, Record<string, unknown>>) || {};

	const footerConfig = (config?.footer as FooterConfig) || {};
	const footerLinks = footerConfig.links || {};

	const getPageTitle = () => {
		if (location.pathname.startsWith('/pay')) return 'Pay';
		switch (location.pathname) {
			case '/':
				return String(headers?.shop_page?.header || 'MiniStore');
			case '/cart':
				return String(headers?.cart_page?.header || 'Your Cart');
			case '/checkout':
				return String(headers?.checkout_page?.header || 'Checkout');
			case '/orders':
				return String(headers?.orders_page?.header || 'My Orders');
			case '/settings':
				return String(headers?.settings_page?.header || 'Settings');
			default:
				return '';
		}
	};

	const bgStyles = (config?.background as Record<string, string>) || {};
	const defaultDarkBg =
		'radial-gradient(circle at 0% 0%, rgba(30, 58, 138, 0.3) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(88, 28, 135, 0.3) 0%, transparent 50%), radial-gradient(circle at 100% 40%, rgba(6, 78, 59, 0.2) 0%, transparent 50%)';
	const defaultLightBg =
		'radial-gradient(circle at 0% 0%, rgba(147, 197, 253, 0.5) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(216, 180, 254, 0.5) 0%, transparent 50%), radial-gradient(circle at 100% 40%, rgba(167, 243, 208, 0.4) 0%, transparent 50%)';

	const currentBackground = isDark
		? bgStyles.background_dark || defaultDarkBg
		: bgStyles.background_light || defaultLightBg;

	return (
		<div
			className="flex justify-center bg-gray-50 dark:bg-gray-950 min-h-screen text-gray-900 dark:text-white font-sans transition-colors duration-300 selection:bg-blue-500/30 relative"
			style={{ backgroundImage: currentBackground }}
		>
			<BackgroundEffect />

			<div className="w-full relative flex flex-col h-[100dvh] overflow-hidden transition-colors duration-300 z-10">
				{!hideHeader && (
					<header className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 sticky top-0 z-20 border-b border-gray-200 dark:border-gray-800 transition-colors duration-300">
						<div className="flex items-center gap-3">
							{!isHome ? (
								<button
									onClick={() => navigate(-1)}
									className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer p-1 -ml-1"
								>
									<ChevronLeft size={26} />
								</button>
							) : (
								<button
									onClick={() => navigate('/settings')}
									className="w-8 h-8 rounded-full overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-500 transition-colors cursor-pointer flex items-center justify-center bg-gray-100 dark:bg-gray-800"
								>
									{user?.photo ? (
										<img
											src={user.photo}
											alt={user.fullName || 'User'}
											className="w-full h-full object-cover"
											loading="lazy"
											decoding="async"
										/>
									) : (
										<UserIcon size={16} className="text-gray-400" />
									)}
								</button>
							)}
							<h1 className="font-semibold text-lg tracking-tight truncate">{getPageTitle()}</h1>
						</div>

						<div className="flex items-center gap-1 sm:gap-2 z-20">
							<button
								onClick={toggleTheme}
								className="relative w-9 h-9 flex items-center justify-center p-2 transition-colors cursor-pointer rounded-full text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
								aria-label="Toggle Theme"
							>
								<AnimatePresence mode="wait" initial={false}>
									{isDark ? (
										<motion.div
											key="moon"
											initial={{ y: -20, opacity: 0, rotate: -90 }}
											animate={{ y: 0, opacity: 1, rotate: 0 }}
											exit={{ y: 20, opacity: 0, rotate: 90 }}
											transition={{ duration: 0.2 }}
											style={{ willChange: 'transform, opacity' }}
											className="absolute"
										>
											<Moon size={20} />
										</motion.div>
									) : (
										<motion.div
											key="sun"
											initial={{ y: -20, opacity: 0, rotate: -90 }}
											animate={{ y: 0, opacity: 1, rotate: 0 }}
											exit={{ y: 20, opacity: 0, rotate: 90 }}
											transition={{ duration: 0.2 }}
											style={{ willChange: 'transform, opacity' }}
											className="absolute"
										>
											<Sun size={20} />
										</motion.div>
									)}
								</AnimatePresence>
							</button>

							<button
								onClick={() => navigate('/orders')}
								className={`p-2 transition-colors cursor-pointer rounded-full ${location.pathname === '/orders' ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'}`}
							>
								<Package size={22} />
							</button>

							<button
								onClick={() => navigate('/settings')}
								className={`p-2 transition-colors cursor-pointer rounded-full ${location.pathname === '/settings' ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'}`}
							>
								<Settings size={22} />
							</button>

							<button
								onClick={() => navigate('/cart')}
								className={`relative p-2 transition-colors cursor-pointer rounded-full ${location.pathname === '/cart' ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'}`}
							>
								<ShoppingBag size={22} />
								{itemCount > 0 && (
									<span className="absolute top-0.5 right-0.5 w-4 h-4 bg-blue-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-white dark:border-gray-900">
										{itemCount}
									</span>
								)}
							</button>
						</div>
					</header>
				)}

				<main
					ref={mainRef}
					onScroll={handleScroll}
					className="flex-1 overflow-y-auto flex flex-col transition-colors duration-300 [&::-webkit-scrollbar]:hidden relative scroll-smooth"
				>
					<div className="grow shrink-0 flex flex-col">
						<Suspense fallback={<Skeleton isLoading={true} />}>
							<Outlet />
						</Suspense>
					</div>

					{!hideHeader && Object.keys(footerConfig).length > 0 && (
						<footer className="mt-auto shrink-0 py-5 px-4 w-full flex flex-col items-center justify-center text-center text-[11px] sm:text-xs text-gray-500 dark:text-gray-500 border-t border-gray-200/50 dark:border-gray-800/50 relative z-10">
							<div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mb-2">
								{footerLinks.privacy_policy && (
									<a
										href={footerLinks.privacy_policy}
										target="_blank"
										rel="noreferrer"
										className="hover:text-gray-900 dark:hover:text-gray-300 transition-colors"
									>
										Privacy Policy
									</a>
								)}
								{footerLinks.terms_of_service && (
									<a
										href={footerLinks.terms_of_service}
										target="_blank"
										rel="noreferrer"
										className="hover:text-gray-900 dark:hover:text-gray-300 transition-colors"
									>
										Terms of Service
									</a>
								)}
								{footerLinks.refund_policy && (
									<a
										href={footerLinks.refund_policy}
										target="_blank"
										rel="noreferrer"
										className="hover:text-gray-900 dark:hover:text-gray-300 transition-colors"
									>
										Refund Policy
									</a>
								)}
							</div>

							<div className="flex items-center justify-center gap-4 mb-1.5">
								{footerConfig.support_email && (
									<a
										href={`mailto:${footerConfig.support_email}`}
										className="hover:text-gray-900 dark:hover:text-gray-300 transition-colors"
									>
										{footerConfig.support_email}
									</a>
								)}
								{footerConfig.support_phone && (
									<a
										href={`tel:${footerConfig.support_phone}`}
										className="hover:text-gray-900 dark:hover:text-gray-300 transition-colors"
									>
										{footerConfig.support_phone}
									</a>
								)}
							</div>

							<div>
								&copy; {footerConfig.copyright_year || new Date().getFullYear()}{' '}
								{footerConfig.company_name || 'MiniStore'}. All rights reserved.
							</div>
						</footer>
					)}
				</main>

				<AnimatePresence>
					{showScrollTop && (
						<motion.button
							initial={{ opacity: 0, scale: 0.8, y: 20 }}
							animate={{ opacity: 1, scale: 1, y: 0 }}
							exit={{ opacity: 0, scale: 0.8, y: 20 }}
							transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
							style={{ willChange: 'transform, opacity' }}
							onClick={scrollToTop}
							className="absolute bottom-24 right-5 w-12 h-12 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-full flex items-center justify-center shadow-lg shadow-gray-200/50 dark:shadow-black/40 z-30 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
							aria-label="Scroll to top"
						>
							<ArrowUp size={20} />
						</motion.button>
					)}
				</AnimatePresence>

				<SupportWidget />
			</div>
		</div>
	);
}

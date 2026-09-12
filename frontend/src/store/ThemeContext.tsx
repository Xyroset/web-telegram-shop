/* eslint-disable react-refresh/only-export-components */
import {
	createContext,
	useContext,
	useState,
	useEffect,
	useMemo,
	useCallback,
	ReactNode,
} from 'react';

import { OpenAPI } from '@/api/core/OpenAPI';
import { useSettings } from '@/hooks/queries/useUserSettings';

interface ThemeContextType {
	isDark: boolean;
	toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
	const getInitialTheme = (): boolean => {
		if (typeof window === 'undefined') return true;
		const savedTheme = localStorage.getItem('app-theme');
		return savedTheme !== 'light';
	};

	const [isDark, setIsDark] = useState<boolean>(getInitialTheme);
	const [lastServerTheme, setLastServerTheme] = useState<string | undefined>(undefined);

	const { settings, updateSettings } = useSettings();

	if (settings?.theme && settings.theme !== lastServerTheme) {
		setLastServerTheme(settings.theme);
		setIsDark(settings.theme === 'dark');
	}

	useEffect(() => {
		if (isDark) {
			document.documentElement.classList.add('dark');
			localStorage.setItem('app-theme', 'dark');
		} else {
			document.documentElement.classList.remove('dark');
			localStorage.setItem('app-theme', 'light');
		}
	}, [isDark]);

	const toggleTheme = useCallback(() => {
		setIsDark((prev) => {
			const nextIsDark = !prev;
			const nextThemeStr = nextIsDark ? 'dark' : 'light';

			if (OpenAPI.TOKEN) {
				updateSettings({ theme: nextThemeStr });
			}

			return nextIsDark;
		});
	}, [updateSettings]);

	const value = useMemo(
		() => ({
			isDark,
			toggleTheme,
		}),
		[isDark, toggleTheme],
	);

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
	const ctx = useContext(ThemeContext);
	if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
	return ctx;
}

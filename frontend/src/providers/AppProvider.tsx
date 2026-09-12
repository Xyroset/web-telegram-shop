import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/store/AuthContext';
import { ConfigProvider } from '@/store/ConfigContext';
import { ThemeProvider } from '@/store/ThemeContext';
import { AuthGuard } from '@/providers/AuthGuard';

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			refetchOnWindowFocus: false,
			retry: 1,
			staleTime: 5 * 60 * 1000,
		},
	},
});

interface AppProviderProps {
	children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
	return (
		<QueryClientProvider client={queryClient}>
			<AuthProvider>
				<ConfigProvider>
					<ThemeProvider>
						<AuthGuard>{children}</AuthGuard>
					</ThemeProvider>
				</ConfigProvider>
			</AuthProvider>
		</QueryClientProvider>
	);
}

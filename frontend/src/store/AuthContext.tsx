/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import WebApp from '@twa-dev/sdk';
import { useQueryClient } from '@tanstack/react-query';

import { AuthService } from '@/api/services/AuthService';
import { OpenAPI } from '@/api/core/OpenAPI';
import { fetchCurrentUser } from '@/hooks/queries/useUser';

OpenAPI.WITH_CREDENTIALS = true;

interface AuthContextType {
	isAuthenticated: boolean;
	isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
	isAuthenticated: false,
	isLoading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
	const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
	const [isLoading, setIsLoading] = useState<boolean>(true);

	const queryClient = useQueryClient();

	useEffect(() => {
		const rawInitData = WebApp.initData;
		const themeOption = WebApp.colorScheme || 'light';

		const syncTelegramData = async (): Promise<boolean> => {
			if (!rawInitData) return false;

			try {
				const response = await AuthService.usersAuthTelegramCreate({
					initData: rawInitData,
					theme: themeOption,
				});

				localStorage.setItem('access_token', response.access_token);
				OpenAPI.TOKEN = response.access_token;
				return true;
			} catch (error) {
				console.error('Auth sync error:', error);
				localStorage.removeItem('access_token');
				OpenAPI.TOKEN = undefined;
				return false;
			}
		};

		const tryRefreshToken = async (): Promise<boolean> => {
			try {
				const response = await AuthService.usersTokenRefreshCreate();
				localStorage.setItem('access_token', response.access_token);
				OpenAPI.TOKEN = response.access_token;
				return true;
			} catch (error) {
				console.warn('Token refresh failed:', error);
				return false;
			}
		};

		const initialize = async () => {
			const existingToken = localStorage.getItem('access_token');

			const authFlow = async (): Promise<boolean> => {
				if (existingToken) {
					OpenAPI.TOKEN = existingToken;
					try {
						await queryClient.fetchQuery({
							queryKey: ['user', 'me'],
							queryFn: fetchCurrentUser,
						});
						return true;
					} catch {
						console.warn('Access token invalid. Attempting to refresh...');
						const isRefreshed = await tryRefreshToken();

						if (isRefreshed) {
							try {
								await queryClient.fetchQuery({
									queryKey: ['user', 'me'],
									queryFn: fetchCurrentUser,
								});
								return true;
							} catch (error) {
								console.error('Failed to fetch user data after refresh:', error);
							}
						}

						console.warn('Refresh failed. Falling back to Telegram initData auth...');
						localStorage.removeItem('access_token');
						OpenAPI.TOKEN = undefined;
						return await syncTelegramData();
					}
				}
				return await syncTelegramData();
			};

			const success = await authFlow();

			setIsAuthenticated(success);
			setIsLoading(false);
		};

		initialize();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<AuthContext.Provider value={{ isAuthenticated, isLoading }}>{children}</AuthContext.Provider>
	);
}

export const useAuth = () => useContext(AuthContext);

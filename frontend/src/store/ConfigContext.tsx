/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, ReactNode, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ConfigService } from '@/api/services/ConfigService';
import { GetWebAppInitConfigResponse } from '@/api/models/GetWebAppInitConfigResponse';
import { useAuth } from '@/store/AuthContext';

interface ConfigContextType {
	config: GetWebAppInitConfigResponse | undefined;
	isConfigLoading: boolean;
	isConfigError: boolean;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
	const { isAuthenticated } = useAuth();

	const {
		data: config,
		isLoading: isConfigLoading,
		isError: isConfigError,
	} = useQuery({
		queryKey: ['app-init-config'],
		queryFn: () => ConfigService.coreConfigInitRetrieve(),
		enabled: isAuthenticated,
		staleTime: Infinity,
		retry: 2,
	});

	const value = useMemo(
		() => ({
			config,
			isConfigLoading,
			isConfigError,
		}),
		[config, isConfigLoading, isConfigError],
	);

	return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export const useConfig = (): ConfigContextType => {
	const context = useContext(ConfigContext);
	if (context === undefined) {
		throw new Error('useConfig must be used within a ConfigProvider');
	}
	return context;
};

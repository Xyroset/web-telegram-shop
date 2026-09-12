import { ReactNode } from 'react';
import { useAuth } from '@/store/AuthContext';
import { useConfig } from '@/store/ConfigContext';
import { Skeleton } from '@/components/skeletons/Skeleton';

interface AuthGuardProps {
	children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
	const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
	const { isConfigLoading, isConfigError } = useConfig();
	const isAppLoading = isAuthLoading || (isAuthenticated && isConfigLoading);

	if (isConfigError) {
		return <div>Critical Error: Failed to load application configuration.</div>;
	}

	return (
		<>
			<Skeleton isLoading={isAppLoading} />
			{!isAppLoading && children}
		</>
	);
}

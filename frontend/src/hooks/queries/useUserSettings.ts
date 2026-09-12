import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { UserSettingsService } from '@/api/services/UserSettingsService';

export const useSettings = () => {
	const queryClient = useQueryClient();

	const query = useQuery({
		queryKey: ['user', 'settings'],
		queryFn: () => UserSettingsService.usersMeSettingsRetrieve(),
		staleTime: 1000 * 60 * 5,
	});

	const updateMutation = useMutation({
		mutationFn: (data: Parameters<typeof UserSettingsService.usersMeSettingsUpdate>[0]) =>
			UserSettingsService.usersMeSettingsUpdate(data),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user'] });
		},
	});

	const resetMutation = useMutation({
		mutationFn: () => UserSettingsService.usersMeSettingsResetToDefaultUpdate(),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ['user'] });
		},
	});

	return {
		settings: query.data,
		isLoading: query.isLoading,
		isError: query.isError,
		updateSettings: updateMutation.mutate,
		isUpdating: updateMutation.isPending,
		resetSettings: resetMutation.mutate,
		isResetting: resetMutation.isPending,
	};
};

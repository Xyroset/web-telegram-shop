import { useQuery } from '@tanstack/react-query';
import { UserService } from '@/api/services/UserService';
import type { UserModel } from '@/types/user';

export const fetchCurrentUser = async (): Promise<UserModel> => {
	const res = await UserService.usersMeRetrieve();
	const fullName = [res.first_name, res.last_name].filter(Boolean).join(' ') || 'User';

	return {
		id: res.tg_id,
		username: res.tg_username || String(res.tg_id),
		fullName,
		photo: res.photo ?? null,
	};
};

export const useUser = () => {
	return useQuery({
		queryKey: ['user', 'me'],
		queryFn: fetchCurrentUser,
		staleTime: 1000 * 60 * 5,
	});
};

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
	Globe,
	Bitcoin,
	Activity,
	MapPin,
	Sparkles,
	User as UserIcon,
	RefreshCw,
	Plus,
	X,
	Trash2,
	CheckCircle2,
	Edit2,
} from 'lucide-react';

import { useUser } from '@/hooks/queries/useUser';
import { useSettings } from '@/hooks/queries/useUserSettings';
import { useDeliveryData } from '@/hooks/queries/useUserDeliveryData';
import { useConfig } from '@/store/ConfigContext';
import { CustomSelect, SelectOption } from '@/components/ui/CustomSelect';
import { SettingsSkeleton } from '@/components/skeletons/SettingsSkeleton';
import type { UserDeliveryDataRequestRequest } from '@/api/models/UserDeliveryDataRequestRequest';
import type { UserDeliveryDataResponse } from '@/api/models/UserDeliveryDataResponse';

interface NetworkDef {
	id: string;
	name: string;
}

interface CurrencyDef {
	display_name: string;
	icon_url: string;
	networks: NetworkDef[];
}

interface ZoneDef {
	default: string;
	[key: string]: string;
}

type TranslationDict = {
	[key: string]: string | TranslationDict;
};

interface AppConfig {
	translations?: {
		settings_page?: TranslationDict;
		zone_names?: Record<string, string | ZoneDef>;
	};
	payments_visual?: {
		providers?: { nowpayments?: { currencies?: Record<string, CurrencyDef> } };
	};
	available_languages?: Array<Record<string, unknown>>;
}

const EMPTY_FORM: UserDeliveryDataRequestRequest = {
	full_name: '',
	email: '',
	phone: '',
	zip_code: '',
	address_line: '',
	destination_code: '',
	region_code: '',
};

const t = (dict: TranslationDict | undefined, key: string, fallback: string): string => {
	if (!dict || typeof dict[key] !== 'string') {
		return fallback;
	}
	return dict[key] as string;
};

const parseLanguages = (rawLangs?: Array<Record<string, unknown>>): SelectOption[] => {
	if (!Array.isArray(rawLangs)) return [{ value: 'en', label: 'English' }];
	return rawLangs.map((langObj) => {
		const [code, name] = Object.entries(langObj)[0];
		return { value: code, label: String(name) };
	});
};

export function Settings() {
	const { config: rawConfig } = useConfig();
	const config = rawConfig as AppConfig | undefined;

	const { data: user, isLoading: isUserLoading, isError: isUserError } = useUser();
	const {
		settings,
		isLoading: isSettingsLoading,
		updateSettings,
		resetSettings,
		isResetting,
	} = useSettings();
	const {
		deliveryList,
		setMainAddress,
		createAddress,
		updateAddress,
		deleteAddress,
		isCreatingAddress,
		isUpdatingAddress,
	} = useDeliveryData();

	const [isAddressModalOpen, setIsAddressModalOpen] = useState(false);
	const [editingAddressId, setEditingAddressId] = useState<number | null>(null);
	const [addrForm, setAddrForm] = useState<UserDeliveryDataRequestRequest>(EMPTY_FORM);

	const [addressError, setAddressError] = useState<string | null>(null);

	const translations = useMemo(
		() => config?.translations?.settings_page || {},
		[config?.translations?.settings_page],
	);
	const zoneNames = useMemo(
		() => config?.translations?.zone_names || {},
		[config?.translations?.zone_names],
	);
	const cryptoCurrencies = useMemo(
		() => config?.payments_visual?.providers?.nowpayments?.currencies || {},
		[config?.payments_visual?.providers?.nowpayments?.currencies],
	);

	const tButtons = (translations.buttons as TranslationDict) || {};
	const tAddressForm = (translations.address_form as TranslationDict) || {};
	const tEmptyStates = (translations.empty_states as TranslationDict) || {};

	const langOptions = useMemo(
		() => parseLanguages(config?.available_languages),
		[config?.available_languages],
	);

	const cryptoOptions: SelectOption[] = useMemo(
		() =>
			Object.entries(cryptoCurrencies).map(([code, data]) => ({
				value: code,
				label: data.display_name,
				icon: data.icon_url,
			})),
		[cryptoCurrencies],
	);

	const selectedCrypto = settings?.preferred_payment_currency
		? cryptoCurrencies[settings.preferred_payment_currency]
		: null;

	const networkOptions: SelectOption[] = useMemo(
		() =>
			selectedCrypto
				? selectedCrypto.networks.map((net) => ({ value: net.id, label: net.name }))
				: [],
		[selectedCrypto],
	);

	const destinationOptions: SelectOption[] = useMemo(
		() =>
			Object.entries(zoneNames).map(([code, val]) => ({
				value: code,
				label: typeof val === 'string' ? val : val.default,
			})),
		[zoneNames],
	);

	const regionOptions: SelectOption[] = useMemo(() => {
		if (!addrForm.destination_code) return [];
		const zone = zoneNames[addrForm.destination_code];
		if (typeof zone === 'object' && zone !== null) {
			return Object.entries(zone)
				.filter(([k]) => k !== 'default')
				.map(([code, name]) => ({ value: code, label: String(name) }));
		}
		return [];
	}, [addrForm.destination_code, zoneNames]);

	const particleOptions: SelectOption[] = useMemo(
		() => [
			{ value: 'none', label: t(translations, 'particles_none', 'None') },
			{ value: 'lines', label: t(translations, 'particles_lines', 'Lines Only') },
			{ value: 'shapes', label: t(translations, 'particles_shapes', 'Shapes & Polygons') },
			{ value: 'both', label: t(translations, 'particles_both', 'Lines & Shapes') },
		],
		[translations],
	);

	const handleLanguageChange = (newLang: string) => {
		updateSettings({ language_code: newLang }, { onSuccess: () => window.location.reload() });
	};

	const handleCurrencyChange = (newCurrency: string) => {
		const networks = cryptoCurrencies[newCurrency]?.networks || [];
		const defaultNetwork = networks.length > 0 ? networks[0].id : '';
		updateSettings({ preferred_payment_currency: newCurrency, preferred_network: defaultNetwork });
	};

	const openCreateModal = () => {
		setEditingAddressId(null);
		setAddrForm(EMPTY_FORM);
		setAddressError(null);
		setIsAddressModalOpen(true);
	};

	const openEditModal = (addr: UserDeliveryDataResponse) => {
		if (!addr.id) return;

		setEditingAddressId(addr.id);
		setAddrForm({
			full_name: addr.full_name || '',
			email: addr.email || '',
			phone: addr.phone || '',
			zip_code: addr.zip_code || '',
			address_line: addr.address_line || '',
			destination_code: addr.destination_code || '',
			region_code: addr.region_code || '',
		});
		setAddressError(null);
		setIsAddressModalOpen(true);
	};

	const handleAddressSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setAddressError(null);

		const payload: UserDeliveryDataRequestRequest = {
			...addrForm,
			region_code: regionOptions.length === 0 ? '' : (addrForm.region_code ?? ''),
		};

		try {
			if (editingAddressId) {
				await updateAddress({ id: editingAddressId, data: payload });
			} else {
				await createAddress(payload);
			}
			setIsAddressModalOpen(false);
			setAddrForm(EMPTY_FORM);
			setEditingAddressId(null);
		} catch (error: unknown) {
			console.error('Failed to save address', error);

			const err = error as Record<string, unknown>;
			const responseObj = err.response as Record<string, unknown> | undefined;
			const responseData = responseObj?.data ?? err.body ?? err.data;

			let apiMessage = t(
				tAddressForm,
				'default_error',
				'Failed to save address. Please check your data.',
			);

			if (responseData && typeof responseData === 'object') {
				const data = responseData as Record<string, unknown>;
				const rawMessage =
					data.message ||
					data.detail ||
					data.error ||
					data.non_field_errors ||
					Object.values(data)[0];

				if (Array.isArray(rawMessage) && rawMessage.length > 0) {
					apiMessage = String(rawMessage[0]);
				} else if (rawMessage) {
					apiMessage = String(rawMessage);
				}
			} else if (typeof responseData === 'string') {
				apiMessage = responseData;
			}

			const lowerMsg = apiMessage.toLowerCase();
			if (lowerMsg.includes('email format')) {
				apiMessage = t(tAddressForm, 'invalid_email', 'Invalid email format.');
			} else if (lowerMsg.includes('phone format')) {
				apiMessage = t(tAddressForm, 'invalid_phone', 'Invalid phone format.');
			} else if (lowerMsg.includes('cannot be empty')) {
				apiMessage = t(tAddressForm, 'empty_field', 'One or more required fields cannot be empty.');
			} else {
				apiMessage = t(
					tAddressForm,
					'default_error',
					'Failed to save address. Please check your data.',
				);
			}

			setAddressError(apiMessage);
		}
	};

	if (isUserLoading || isSettingsLoading) return <SettingsSkeleton />;

	if (isUserError || !user)
		return (
			<div className="text-center text-red-500 p-10">
				{t(translations, 'errors', 'Failed to load settings')}
			</div>
		);

	const isSavingAddress = isCreatingAddress || isUpdatingAddress;

	return (
		<motion.div
			initial={{ opacity: 0, x: 20 }}
			animate={{ opacity: 1, x: 0 }}
			transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
			style={{ willChange: 'transform, opacity' }}
			className="p-4 space-y-6 max-w-3xl mx-auto w-full pb-64"
		>
			<div className="flex flex-col items-center justify-center py-4">
				<div className="w-20 h-20 rounded-full overflow-hidden border-2 border-gray-200 dark:border-gray-800 mb-3 bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
					{user.photo ? (
						<img
							src={user.photo}
							alt={user.fullName}
							className="w-full h-full object-cover"
							loading="lazy"
							decoding="async"
						/>
					) : (
						<UserIcon size={32} className="text-gray-400" />
					)}
				</div>
				<h2 className="text-xl font-bold text-gray-900 dark:text-white">{user.fullName}</h2>
				<span className="text-sm text-gray-500">@{user.username}</span>
			</div>

			<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm dark:shadow-none">
				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
							<Globe size={18} />
						</div>
						<span className="font-medium text-gray-900 dark:text-gray-200">
							{t(translations, 'language', 'Language')}
						</span>
					</div>
					<div className="w-full sm:w-48">
						<CustomSelect
							value={settings?.language_code || 'en'}
							onChange={handleLanguageChange}
							options={langOptions}
						/>
					</div>
				</div>

				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
							<Bitcoin size={18} />
						</div>
						<span className="font-medium text-gray-900 dark:text-gray-200">
							{t(translations, 'currency', 'Crypto Currency')}
						</span>
					</div>
					<div className="w-full sm:w-48">
						<CustomSelect
							value={settings?.preferred_payment_currency || ''}
							onChange={handleCurrencyChange}
							options={cryptoOptions}
							placeholder="Select Currency"
						/>
					</div>
				</div>

				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center">
							<Activity size={18} />
						</div>
						<span className="font-medium text-gray-900 dark:text-gray-200">
							{t(translations, 'network', 'Network')}
						</span>
					</div>
					<div className="w-full sm:w-48">
						<CustomSelect
							value={settings?.preferred_network || ''}
							onChange={(val) => updateSettings({ preferred_network: val })}
							options={networkOptions}
							disabled={networkOptions.length === 0}
							placeholder="Select Network"
						/>
					</div>
				</div>

				<div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800/50 gap-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
							<Sparkles size={18} />
						</div>
						<span className="font-medium text-gray-900 dark:text-gray-200">
							{t(translations, 'particles_mode', 'Background Effect')}
						</span>
					</div>
					<div className="w-full sm:w-48">
						<CustomSelect
							value={settings?.particles_style || 'both'}
							onChange={(val) => updateSettings({ particles_style: val })}
							options={particleOptions}
						/>
					</div>
				</div>

				<div className="p-4">
					<button
						onClick={() => resetSettings()}
						disabled={isResetting}
						className="flex items-center justify-center w-full gap-2 py-3 text-sm font-bold text-red-600 bg-red-50 dark:bg-red-500/10 rounded-xl hover:bg-red-100 transition-colors disabled:opacity-50 cursor-pointer"
					>
						<RefreshCw size={18} className={isResetting ? 'animate-spin' : ''} />
						{t(tButtons, 'reset', 'Reset to Default')}
					</button>
				</div>
			</div>

			<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-sm dark:shadow-none">
				<div className="flex items-center justify-between mb-4">
					<div className="flex items-center gap-3">
						<div className="w-8 h-8 rounded-full bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 flex items-center justify-center">
							<MapPin size={18} />
						</div>
						<h3 className="font-bold text-gray-900 dark:text-white">
							{t(translations, 'delivery_address', 'Delivery Addresses')}
						</h3>
					</div>
					<button
						onClick={openCreateModal}
						className="p-2 bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 transition-colors cursor-pointer"
					>
						<Plus size={18} />
					</button>
				</div>

				<div className="space-y-3">
					{deliveryList.length === 0 ? (
						<p className="text-center text-sm text-gray-500 py-4">
							{t(tEmptyStates, 'no_addresses', 'No saved addresses')}
						</p>
					) : (
						deliveryList.map((addr) => (
							<motion.div
								layout
								key={addr.id}
								className={`p-4 rounded-xl border-2 transition-colors transform-gpu ${addr.is_current ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-500/5' : 'border-gray-100 dark:border-gray-800'}`}
							>
								<div className="flex justify-between items-start">
									<div className="flex-1 pr-4">
										<p className="font-bold text-sm text-gray-900 dark:text-white">
											{addr.full_name}
										</p>
										<p className="text-sm text-gray-500 mt-1">
											{addr.address_line}, {addr.zip_code}
										</p>
										<p className="text-sm text-gray-500">
											{addr.destination_code} {addr.region_code ? `• ${addr.region_code}` : ''} •{' '}
											{addr.phone}
										</p>
										<p className="text-sm text-gray-500 truncate">{addr.email}</p>
									</div>
									<div className="flex gap-2">
										{!addr.is_current && addr.id && (
											<button
												onClick={() => setMainAddress(addr.id as number)}
												className="p-2 text-gray-400 hover:text-blue-500 transition-colors cursor-pointer"
												title={t(tButtons, 'set_active', 'Set Active')}
											>
												<CheckCircle2 size={18} />
											</button>
										)}
										{addr.is_current && (
											<div className="p-2 text-blue-500">
												<CheckCircle2 size={18} />
											</div>
										)}
										<button
											onClick={() => openEditModal(addr)}
											className="p-2 text-gray-400 hover:text-orange-500 transition-colors cursor-pointer"
											title={t(tButtons, 'edit', 'Edit')}
										>
											<Edit2 size={18} />
										</button>
										{addr.id && (
											<button
												onClick={() => deleteAddress(addr.id as number)}
												className="p-2 text-gray-400 hover:text-red-500 transition-colors cursor-pointer"
												title={t(tButtons, 'delete', 'Delete')}
											>
												<Trash2 size={18} />
											</button>
										)}
									</div>
								</div>
							</motion.div>
						))
					)}
				</div>
			</div>

			<AnimatePresence>
				{isAddressModalOpen && (
					<div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-0 sm:p-4">
						<motion.form
							initial={{ y: '100%' }}
							animate={{ y: 0 }}
							exit={{ y: '100%' }}
							transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
							style={{ willChange: 'transform' }}
							onSubmit={handleAddressSubmit}
							className="bg-white dark:bg-gray-900 w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-5 space-y-4 shadow-2xl max-h-[100vh] overflow-y-auto mt-auto sm:mt-0"
						>
							<div className="flex justify-between items-center mb-4">
								<h3 className="text-lg font-bold text-gray-900 dark:text-white">
									{editingAddressId
										? t(tAddressForm, 'edit_title', 'Edit Address')
										: t(tAddressForm, 'title', 'Add Address')}
								</h3>
								<button
									type="button"
									onClick={() => setIsAddressModalOpen(false)}
									className="text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
								>
									<X size={20} />
								</button>
							</div>

							{addressError && (
								<div className="p-3 mb-2 text-sm text-red-600 bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20 rounded-xl">
									{addressError}
								</div>
							)}
							<input
								required
								placeholder={t(tAddressForm, 'full_name', 'Full Name')}
								className="w-full p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white outline-none border border-transparent focus:border-blue-500 transition-colors"
								value={addrForm.full_name}
								onChange={(e) => setAddrForm({ ...addrForm, full_name: e.target.value })}
							/>
							<div className="flex flex-col sm:flex-row gap-3">
								<input
									required
									type="email"
									placeholder={t(tAddressForm, 'email', 'Email')}
									className="w-full p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white outline-none border border-transparent focus:border-blue-500 transition-colors"
									value={addrForm.email}
									onChange={(e) => setAddrForm({ ...addrForm, email: e.target.value })}
								/>
								<input
									required
									type="tel"
									placeholder={t(tAddressForm, 'phone', 'Phone')}
									className="w-full p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white outline-none border border-transparent focus:border-blue-500 transition-colors"
									value={addrForm.phone}
									onChange={(e) => setAddrForm({ ...addrForm, phone: e.target.value })}
								/>
							</div>
							<div className="relative z-20">
								<CustomSelect
									value={addrForm.destination_code || ''}
									onChange={(val) =>
										setAddrForm({ ...addrForm, destination_code: val, region_code: '' })
									}
									options={destinationOptions}
									placeholder={t(tAddressForm, 'destination', 'Select Country')}
								/>
							</div>
							<div className="relative z-10">
								<CustomSelect
									disabled={regionOptions.length === 0}
									value={addrForm.region_code || ''}
									onChange={(val) => setAddrForm({ ...addrForm, region_code: val })}
									options={regionOptions}
									placeholder={
										regionOptions.length > 0
											? t(tAddressForm, 'region', 'Select Region')
											: t(tAddressForm, 'no_region', 'No region required')
									}
								/>
							</div>
							<input
								required
								placeholder={t(tAddressForm, 'zip_code', 'ZIP Code')}
								className="w-full p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white outline-none border border-transparent focus:border-blue-500 transition-colors"
								value={addrForm.zip_code}
								onChange={(e) => setAddrForm({ ...addrForm, zip_code: e.target.value })}
							/>
							<input
								required
								placeholder={t(tAddressForm, 'address_line', 'Address Line')}
								className="w-full p-3 rounded-xl bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white outline-none border border-transparent focus:border-blue-500 transition-colors"
								value={addrForm.address_line}
								onChange={(e) => setAddrForm({ ...addrForm, address_line: e.target.value })}
							/>
							<button
								disabled={isSavingAddress}
								type="submit"
								className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold mt-4 disabled:opacity-70 transition-colors shadow-lg cursor-pointer"
							>
								{isSavingAddress
									? 'Saving...'
									: editingAddressId
										? t(tButtons, 'update', 'Update')
										: t(tButtons, 'save', 'Save')}
							</button>
						</motion.form>
					</div>
				)}
			</AnimatePresence>
		</motion.div>
	);
}

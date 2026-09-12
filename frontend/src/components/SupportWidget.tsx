import { useState } from 'react';
import {
	MessageCircle,
	X,
	Bug,
	Clock,
	HelpCircle,
	Mail,
	Send,
	CheckCircle2,
	User,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useConfig } from '@/store/ConfigContext';
import { useSupport } from '@/hooks/mutations/useSupport';

interface SupportTranslations {
	webapp?: Record<string, string>;
	categories?: Record<string, string>;
}

interface AppTranslations {
	support?: SupportTranslations;
}

interface AppConfig {
	translations?: AppTranslations;
}

const t = (dict: Record<string, string> | undefined, key: string, fallback: string): string => {
	return dict && typeof dict[key] === 'string' ? dict[key] : fallback;
};

export function SupportWidget() {
	const { config: rawConfig } = useConfig();
	const config = rawConfig as AppConfig | undefined;

	const webappConfig = config?.translations?.support?.webapp;
	const categoriesConfig = config?.translations?.support?.categories;

	const { createTicket, isCreatingTicket } = useSupport();

	const [isOpen, setIsOpen] = useState(false);
	const [step, setStep] = useState<'menu' | 'category' | 'message_form' | 'success'>('menu');
	const [selectedCategory, setSelectedCategory] = useState<string>('');
	const [message, setMessage] = useState('');
	const [errorMsg, setErrorMsg] = useState<string | null>(null);

	const categories = [
		{
			id: 'bug',
			icon: <Bug size={20} className="text-rose-500" />,
			label: t(categoriesConfig, 'bug', 'Bug Report'),
		},
		{
			id: 'order_issue',
			icon: <Clock size={20} className="text-yellow-500" />,
			label: t(categoriesConfig, 'order_issue', 'Order Issue'),
		},
		{
			id: 'general',
			icon: <HelpCircle size={20} className="text-blue-500" />,
			label: t(categoriesConfig, 'general', 'General Question'),
		},
	];

	const handleOpen = () => {
		setIsOpen(true);
		setStep('menu');
	};

	const handleClose = () => {
		setIsOpen(false);
		setTimeout(() => {
			setStep('menu');
			setSelectedCategory('');
			setMessage('');
			setErrorMsg(null);
		}, 300);
	};

	const handleCategorySelect = (id: string) => {
		setSelectedCategory(id);
		setStep('message_form');
	};

	const submitTicket = async (category: string, text: string) => {
		setErrorMsg(null);
		try {
			await createTicket({ category, message_text: text.trim() });
			setStep('success');
			setTimeout(() => {
				handleClose();
			}, 2500);
		} catch {
			setErrorMsg(t(webappConfig, 'error_desc', 'Failed to send request. Please try again.'));
		}
	};

	const handleSendMessage = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!message.trim() || !selectedCategory) return;
		await submitTicket(selectedCategory, message);
	};

	const handleQuickAdminContact = async () => {
		const quickMsg = t(
			webappConfig,
			'quick_admin_message',
			"Hello, I need an administrator's assistance.",
		);
		await submitTicket('general', quickMsg);
	};

	const getStepTitle = () => {
		switch (step) {
			case 'menu':
				return t(webappConfig, 'menu_title', 'How can we help?');
			case 'category':
				return t(webappConfig, 'category_title', 'Select Category');
			case 'message_form':
				return t(webappConfig, 'message_form_title', 'Send a Message');
			case 'success':
				return t(webappConfig, 'success_title', 'Message Sent!');
			default:
				return t(webappConfig, 'widget_title', 'Support');
		}
	};

	return (
		<>
			<motion.button
				initial={{ scale: 0 }}
				animate={{ scale: 1 }}
				whileHover={{ scale: 1.05 }}
				whileTap={{ scale: 0.95 }}
				onClick={handleOpen}
				className="fixed bottom-6 right-4 w-14 h-14 bg-blue-600 text-white rounded-full flex items-center justify-center shadow-lg shadow-blue-600/30 z-40 cursor-pointer"
			>
				<MessageCircle size={24} />
			</motion.button>

			<AnimatePresence>
				{isOpen && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						onClick={handleClose}
						className="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center"
					>
						<motion.div
							initial={{ y: '100%' }}
							animate={{ y: 0 }}
							exit={{ y: '100%' }}
							transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
							style={{ willChange: 'transform' }}
							onClick={(e) => e.stopPropagation()}
							className="w-full bg-white dark:bg-gray-900 rounded-t-3xl overflow-hidden flex flex-col max-h-[85vh] sm:max-h-[90vh] sm:rounded-3xl sm:max-w-md shadow-2xl transition-colors duration-300 transform-gpu"
						>
							<div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800 transition-colors duration-300 shrink-0">
								<h3 className="font-bold text-lg text-gray-900 dark:text-white transition-colors duration-300">
									{getStepTitle()}
								</h3>
								<button
									onClick={handleClose}
									className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 hover:text-gray-900 dark:hover:text-white flex items-center justify-center transition-colors cursor-pointer"
								>
									<X size={18} />
								</button>
							</div>

							<div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(85vh - 70px)' }}>
								{errorMsg && (
									<div className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-xl text-sm font-medium">
										{errorMsg}
									</div>
								)}

								<AnimatePresence mode="wait">
									{step === 'menu' && (
										<motion.div
											key="menu"
											initial={{ opacity: 0, x: -20 }}
											animate={{ opacity: 1, x: 0 }}
											exit={{ opacity: 0, x: -20 }}
											transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
											style={{ willChange: 'transform, opacity' }}
											className="space-y-3 pb-2 transform-gpu"
										>
											<button
												onClick={() => setStep('category')}
												className="w-full flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white transition-all text-left group cursor-pointer"
											>
												<div className="flex items-center gap-4">
													<div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
														<Mail size={20} />
													</div>
													<div>
														<span className="font-medium text-base block mb-0.5">
															{t(webappConfig, 'write_request', 'Write a Request')}
														</span>
														<span className="text-xs text-gray-500 dark:text-gray-400">
															{t(
																webappConfig,
																'write_request_desc',
																'Describe your issue in detail',
															)}
														</span>
													</div>
												</div>
											</button>

											<button
												onClick={handleQuickAdminContact}
												disabled={isCreatingTicket}
												className="w-full flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-900 dark:text-white transition-all text-left group cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
											>
												<div className="flex items-center gap-4">
													<div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-600 dark:text-gray-400">
														{isCreatingTicket ? (
															<span className="w-5 h-5 border-2 border-gray-400/30 border-t-gray-400 rounded-full animate-spin" />
														) : (
															<User size={20} />
														)}
													</div>
													<div>
														<span className="font-medium text-base block mb-0.5">
															{t(webappConfig, 'contact_admin', 'Contact Admin')}
														</span>
														<span className="text-xs text-gray-500 dark:text-gray-400">
															{t(
																webappConfig,
																'contact_admin_desc',
																'Request direct admin assistance',
															)}
														</span>
													</div>
												</div>
											</button>
										</motion.div>
									)}

									{step === 'category' && (
										<motion.div
											key="category"
											initial={{ opacity: 0, x: 20 }}
											animate={{ opacity: 1, x: 0 }}
											exit={{ opacity: 0, x: 20 }}
											transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
											style={{ willChange: 'transform, opacity' }}
											className="space-y-3 transform-gpu"
										>
											<button
												onClick={() => setStep('menu')}
												className="text-sm text-blue-500 hover:text-blue-600 mb-2 flex items-center font-medium cursor-pointer"
											>
												← {t(webappConfig, 'back', 'Back')}
											</button>

											{categories.map((cat) => (
												<button
													key={cat.id}
													onClick={() => handleCategorySelect(cat.id)}
													className="w-full flex items-center gap-4 p-4 rounded-xl border border-gray-200 dark:border-gray-800 hover:border-blue-500 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-gray-900 dark:text-white transition-all text-left cursor-pointer group"
												>
													<div className="w-10 h-10 rounded-full bg-gray-50 dark:bg-gray-800 flex items-center justify-center group-hover:scale-110 transition-transform">
														{cat.icon}
													</div>
													<span className="font-medium text-base">{cat.label}</span>
												</button>
											))}
										</motion.div>
									)}

									{step === 'message_form' && (
										<motion.div
											key="message_form"
											initial={{ opacity: 0, x: 20 }}
											animate={{ opacity: 1, x: 0 }}
											exit={{ opacity: 0, x: 20 }}
											transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
											style={{ willChange: 'transform, opacity' }}
											className="space-y-4 transform-gpu"
										>
											<button
												onClick={() => setStep('category')}
												className="text-sm text-blue-500 hover:text-blue-600 mb-2 flex items-center font-medium cursor-pointer"
											>
												← {t(webappConfig, 'back', 'Back')}
											</button>

											<form onSubmit={handleSendMessage} className="flex flex-col gap-4">
												<textarea
													autoFocus
													value={message}
													onChange={(e) => setMessage(e.target.value)}
													placeholder={t(webappConfig, 'placeholder', 'Type your message here...')}
													className="w-full h-32 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-colors duration-300"
												/>
												<button
													type="submit"
													disabled={!message.trim() || isCreatingTicket}
													className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-lg"
												>
													{isCreatingTicket ? (
														<span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
													) : (
														<>
															<Send size={18} />
															{t(webappConfig, 'send_btn', 'Send Message')}
														</>
													)}
												</button>
											</form>
										</motion.div>
									)}

									{step === 'success' && (
										<motion.div
											key="success"
											initial={{ opacity: 0, scale: 0.9 }}
											animate={{ opacity: 1, scale: 1 }}
											transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
											style={{ willChange: 'transform, opacity' }}
											className="flex flex-col items-center justify-center py-10 text-center space-y-4 transform-gpu"
										>
											<motion.div
												initial={{ scale: 0 }}
												animate={{ scale: 1 }}
												transition={{ type: 'spring', damping: 20, stiffness: 300, delay: 0.1 }}
												className="w-16 h-16 bg-green-100 dark:bg-green-900/30 text-green-500 rounded-full flex items-center justify-center"
											>
												<CheckCircle2 size={32} />
											</motion.div>
											<div>
												<h4 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
													{t(webappConfig, 'success_title', 'Message Sent!')}
												</h4>
												<p className="text-gray-500 dark:text-gray-400 text-sm">
													{t(
														webappConfig,
														'success_desc',
														'Thank you for reaching out. Our team will look into your request shortly.',
													)}
												</p>
											</div>
										</motion.div>
									)}
								</AnimatePresence>
							</div>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>
		</>
	);
}

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check } from 'lucide-react';

export interface SelectOption {
	value: string;
	label: string;
	icon?: string;
}

interface CustomSelectProps {
	value: string;
	onChange: (val: string) => void;
	options: SelectOption[];
	disabled?: boolean;
	placeholder?: string;
	className?: string;
}

export function CustomSelect({
	value,
	onChange,
	options,
	disabled,
	placeholder,
	className = '',
}: CustomSelectProps) {
	const [isOpen, setIsOpen] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);

	const selectedOption = options.find((opt) => opt.value === value);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
				setIsOpen(false);
			}
		};
		document.addEventListener('mousedown', handleClickOutside);
		return () => document.removeEventListener('mousedown', handleClickOutside);
	}, []);

	return (
		<div
			className={`relative ${className} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
			ref={containerRef}
		>
			<button
				type="button"
				onClick={() => !disabled && setIsOpen(!isOpen)}
				className="flex items-center justify-between w-full p-3 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl border border-transparent focus:border-blue-500 transition-colors focus:outline-none"
			>
				<div className="flex items-center gap-2 truncate">
					{selectedOption?.icon && (
						<img
							src={
								selectedOption.icon ||
								'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
							}
							alt="icon"
							className="w-5 h-5 rounded-full"
						/>
					)}
					<span className="truncate">{selectedOption ? selectedOption.label : placeholder}</span>
				</div>
				<ChevronDown
					size={16}
					className={`text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
				/>
			</button>

			<AnimatePresence>
				{isOpen && (
					<motion.div
						initial={{ opacity: 0, y: -10 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, y: -10 }}
						transition={{ duration: 0.15 }}
						className="absolute z-50 w-full mt-2 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl shadow-lg max-h-60 overflow-auto"
					>
						{options.length === 0 ? (
							<div className="p-3 text-sm text-gray-500 text-center">No options available</div>
						) : (
							options.map((opt) => (
								<button
									key={opt.value}
									type="button"
									onClick={() => {
										onChange(opt.value);
										setIsOpen(false);
									}}
									className="flex items-center justify-between w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
								>
									<div className="flex items-center gap-2">
										{opt.icon && (
											<img
												src={
													opt.icon ||
													'https://placehold.co/600x400/e0e0e0/333333?text=Image+Not+Found'
												}
												alt="icon"
												className="w-5 h-5 rounded-full"
											/>
										)}
										<span
											className={`text-sm ${value === opt.value ? 'font-bold dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}
										>
											{opt.label}
										</span>
									</div>
									{value === opt.value && <Check size={16} className="text-blue-500" />}
								</button>
							))
						)}
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
}

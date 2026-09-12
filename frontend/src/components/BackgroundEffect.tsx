import { useEffect, useRef, useMemo } from 'react';
import { useTheme } from '@/store/ThemeContext';
import { useConfig } from '@/store/ConfigContext';
import { useSettings } from '@/hooks/queries/useUserSettings';

interface ParticleConfig {
	render: { fillOpacity: number };
	base: {
		baseVelocity: number;
		minSize: number;
		maxSize: number;
		minAlpha: number;
		maxAlpha: number;
		friction: number;
		minSpeed: number;
		speedBoost: number;
	};
	mouse: {
		maxDistance: number;
		repelDistance: number;
		repelForce: number;
		pullForce: number;
		tangentialForce: number;
	};
	density: { target: number; minCount: number; maxCount: number };
	lines: { repelDistance: number; repelForce: number; connectDistance: number; width: number };
	theme: { darkColors: string[]; lightColors: string[]; darkLineRGB: string; lightLineRGB: string };
}

interface AppConfig {
	particles?: Partial<ParticleConfig>;
}

const DEFAULT_CONFIG: ParticleConfig = {
	render: { fillOpacity: 0.15 },
	base: {
		baseVelocity: 0.8,
		minSize: 1,
		maxSize: 3,
		minAlpha: 0.5,
		maxAlpha: 1.0,
		friction: 0.96,
		minSpeed: 0.3,
		speedBoost: 1.05,
	},
	mouse: {
		maxDistance: 150,
		repelDistance: 50,
		repelForce: 0.6,
		pullForce: 0.12,
		tangentialForce: 0.04,
	},
	density: { target: 4000, minCount: 50, maxCount: 800 },
	lines: { repelDistance: 70, repelForce: 0.1, connectDistance: 90, width: 1.5 },
	theme: {
		darkColors: ['rgba(96, 165, 250', 'rgba(167, 139, 250', 'rgba(56, 189, 248'],
		lightColors: ['rgba(37, 99, 235', 'rgba(79, 70, 229', 'rgba(14, 165, 233'],
		darkLineRGB: '167, 139, 250',
		lightLineRGB: '37, 99, 235',
	},
};

class Particle {
	x: number;
	y: number;
	vx: number;
	vy: number;
	size: number;
	color: string;

	constructor(x: number, y: number, isDark: boolean, config: ParticleConfig) {
		this.x = x;
		this.y = y;
		this.vx = (Math.random() - 0.5) * config.base.baseVelocity;
		this.vy = (Math.random() - 0.5) * config.base.baseVelocity;
		this.size = Math.random() * (config.base.maxSize - config.base.minSize) + config.base.minSize;

		const alpha =
			Math.random() * (config.base.maxAlpha - config.base.minAlpha) + config.base.minAlpha;
		const rawColors = isDark ? config.theme.darkColors : config.theme.lightColors;

		const colorSet =
			Array.isArray(rawColors) && rawColors.length > 0
				? rawColors
				: DEFAULT_CONFIG.theme.lightColors;
		this.color = `${colorSet[Math.floor(Math.random() * colorSet.length)]}, ${alpha})`;
	}

	update(
		mouseX: number | null,
		mouseY: number | null,
		canvasWidth: number,
		canvasHeight: number,
		config: ParticleConfig,
	) {
		this.x += this.vx;
		this.y += this.vy;

		if (this.x < 0) {
			this.x = 0;
			this.vx *= -1;
		}
		if (this.x > canvasWidth) {
			this.x = canvasWidth;
			this.vx *= -1;
		}
		if (this.y < 0) {
			this.y = 0;
			this.vy *= -1;
		}
		if (this.y > canvasHeight) {
			this.y = canvasHeight;
			this.vy *= -1;
		}

		if (mouseX !== null && mouseY !== null) {
			const dx = mouseX - this.x;
			const dy = mouseY - this.y;

			const distSq = dx * dx + dy * dy;
			const maxMouseDistSq = config.mouse.maxDistance * config.mouse.maxDistance;

			if (distSq < maxMouseDistSq) {
				const distance = Math.max(0.1, Math.sqrt(distSq));
				if (distance < config.mouse.repelDistance) {
					const repelForce = (config.mouse.repelDistance - distance) / config.mouse.repelDistance;
					this.vx -= (dx / distance) * repelForce * config.mouse.repelForce;
					this.vy -= (dy / distance) * repelForce * config.mouse.repelForce;
				} else {
					const pullForce = (config.mouse.maxDistance - distance) / config.mouse.maxDistance;
					this.vx +=
						(dx / distance) * pullForce * config.mouse.pullForce +
						(dy / distance) * pullForce * config.mouse.tangentialForce;
					this.vy +=
						(dy / distance) * pullForce * config.mouse.pullForce -
						(dx / distance) * pullForce * config.mouse.tangentialForce;
				}
			}
		}

		this.vx *= config.base.friction;
		this.vy *= config.base.friction;

		if (Math.sqrt(this.vx * this.vx + this.vy * this.vy) < config.base.minSpeed) {
			this.vx *= config.base.speedBoost;
			this.vy *= config.base.speedBoost;
		}

		if (Number.isNaN(this.x) || Number.isNaN(this.y)) {
			this.x = Math.random() * canvasWidth;
			this.y = Math.random() * canvasHeight;
			this.vx = (Math.random() - 0.5) * config.base.baseVelocity;
			this.vy = (Math.random() - 0.5) * config.base.baseVelocity;
		}
	}

	draw(ctx: CanvasRenderingContext2D) {
		ctx.beginPath();
		ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
		ctx.fillStyle = this.color;
		ctx.fill();
	}
}

export function BackgroundEffect() {
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const { isDark } = useTheme();
	const { config: rawGlobalConfig } = useConfig();
	const { settings } = useSettings();

	const currentMode = settings?.particles_style || 'both';

	const globalConfig = rawGlobalConfig as AppConfig | undefined;
	const rawParticles = globalConfig?.particles || {};
	const rawParticlesStr = JSON.stringify(rawParticles);

	const activeConfig = useMemo<ParticleConfig>(() => {
		const parsed = JSON.parse(rawParticlesStr) as Partial<ParticleConfig>;
		return {
			render: { ...DEFAULT_CONFIG.render, ...(parsed.render || {}) },
			base: { ...DEFAULT_CONFIG.base, ...(parsed.base || {}) },
			mouse: { ...DEFAULT_CONFIG.mouse, ...(parsed.mouse || {}) },
			density: { ...DEFAULT_CONFIG.density, ...(parsed.density || {}) },
			lines: { ...DEFAULT_CONFIG.lines, ...(parsed.lines || {}) },
			theme: { ...DEFAULT_CONFIG.theme, ...(parsed.theme || {}) },
		};
	}, [rawParticlesStr]);

	const mouseRef = useRef<{ x: number | null; y: number | null }>({ x: null, y: null });
	const particlesRef = useRef<Particle[]>([]);
	const animationRef = useRef<number>(0);

	useEffect(() => {
		if (currentMode === 'none') return;

		const canvas = canvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		const dpr = window.devicePixelRatio || 1;
		let width = window.innerWidth;
		let height = window.innerHeight;

		const setupCanvas = () => {
			width = window.innerWidth;
			height = window.innerHeight;
			if (width === 0 || height === 0) return;

			canvas.width = width * dpr;
			canvas.height = height * dpr;
			ctx.scale(dpr, dpr);
		};

		const initParticles = () => {
			if (width === 0 || height === 0) return;
			particlesRef.current = [];

			const targetDensity = Number(activeConfig.density.target) || 4000;
			const particleCount = Math.max(
				activeConfig.density.minCount,
				Math.min(activeConfig.density.maxCount, Math.floor((width * height) / targetDensity)),
			);

			for (let i = 0; i < particleCount; i++) {
				particlesRef.current.push(
					new Particle(Math.random() * width, Math.random() * height, isDark, activeConfig),
				);
			}
		};

		setupCanvas();
		initParticles();

		const handleResize = () => {
			setupCanvas();
			initParticles();
		};

		const handleMouseMove = (e: MouseEvent) => {
			mouseRef.current =
				e.clientX <= 0 ||
				e.clientY <= 0 ||
				e.clientX >= window.innerWidth ||
				e.clientY >= window.innerHeight
					? { x: null, y: null }
					: { x: e.clientX, y: e.clientY };
		};

		const handleMouseLeave = () => {
			mouseRef.current = { x: null, y: null };
		};

		const handleTouchMove = (e: TouchEvent) => {
			if (e.touches.length > 0)
				mouseRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
		};

		window.addEventListener('resize', handleResize, { passive: true });
		window.addEventListener('mousemove', handleMouseMove, { passive: true });
		document.addEventListener('mouseleave', handleMouseLeave, { passive: true });
		window.addEventListener('touchmove', handleTouchMove, { passive: true });

		const animate = () => {
			if (width > 0 && height > 0) {
				ctx.clearRect(0, 0, width, height);
			}

			const particles = particlesRef.current;
			const len = particles.length;

			const connectDist = activeConfig.lines.connectDistance;
			const connectDistSq = connectDist * connectDist;
			const repelDist = activeConfig.lines.repelDistance;
			const repelDistSq = repelDist * repelDist;

			const rawRGB = isDark ? activeConfig.theme.darkLineRGB : activeConfig.theme.lightLineRGB;
			const baseRGB = rawRGB || DEFAULT_CONFIG.theme.lightLineRGB;

			particles.forEach((p) => {
				p.update(mouseRef.current.x, mouseRef.current.y, width, height, activeConfig);
				p.draw(ctx);
			});

			for (let i = 0; i < len; i++) {
				for (let j = i + 1; j < len; j++) {
					const dx = particles[i].x - particles[j].x;
					const dy = particles[i].y - particles[j].y;
					const distSq = dx * dx + dy * dy;

					if (distSq < repelDistSq) {
						const distance = Math.max(0.1, Math.sqrt(distSq));
						const repelForce = ((repelDist - distance) / repelDist) * activeConfig.lines.repelForce;

						const forceX = (dx / distance) * repelForce;
						const forceY = (dy / distance) * repelForce;

						particles[i].vx += forceX;
						particles[i].vy += forceY;
						particles[j].vx -= forceX;
						particles[j].vy -= forceY;
					}

					if (distSq < connectDistSq) {
						const distance = Math.max(0.1, Math.sqrt(distSq));

						if (currentMode === 'lines' || currentMode === 'both') {
							ctx.beginPath();
							ctx.strokeStyle = `rgba(${baseRGB}, ${(1 - distance / connectDist) * 0.5})`;
							ctx.lineWidth = activeConfig.lines.width;
							ctx.moveTo(particles[i].x, particles[i].y);
							ctx.lineTo(particles[j].x, particles[j].y);
							ctx.stroke();
						}

						if (currentMode === 'shapes' || currentMode === 'both') {
							for (let k = j + 1; k < len; k++) {
								const dxIK = particles[i].x - particles[k].x;
								const dyIK = particles[i].y - particles[k].y;
								const distIKSq = dxIK * dxIK + dyIK * dyIK;

								if (distIKSq < connectDistSq) {
									const dxJK = particles[j].x - particles[k].x;
									const dyJK = particles[j].y - particles[k].y;
									const distJKSq = dxJK * dxJK + dyJK * dyJK;

									if (distJKSq < connectDistSq) {
										const distIK = Math.sqrt(distIKSq);
										const distJK = Math.sqrt(distJKSq);

										ctx.beginPath();
										ctx.fillStyle = `rgba(${baseRGB}, ${(1 - (distance + distJK + distIK) / 3 / connectDist) * activeConfig.render.fillOpacity})`;
										ctx.moveTo(particles[i].x, particles[i].y);
										ctx.lineTo(particles[j].x, particles[j].y);
										ctx.lineTo(particles[k].x, particles[k].y);
										ctx.fill();
									}
								}
							}
						}
					}
				}
			}
			animationRef.current = requestAnimationFrame(animate);
		};

		animate();

		return () => {
			window.removeEventListener('resize', handleResize);
			window.removeEventListener('mousemove', handleMouseMove);
			document.removeEventListener('mouseleave', handleMouseLeave);
			window.removeEventListener('touchmove', handleTouchMove);
			if (animationRef.current) cancelAnimationFrame(animationRef.current);
		};
	}, [isDark, activeConfig, currentMode]);

	if (currentMode === 'none') return null;

	return (
		<canvas
			ref={canvasRef}
			className="fixed top-0 left-0 w-full h-full pointer-events-none z-0"
			style={{ opacity: 1 }}
		/>
	);
}

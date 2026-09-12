import axios from 'axios';
import { OpenAPI } from '@/api/core/OpenAPI';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

OpenAPI.BASE = API_BASE_URL;
axios.defaults.baseURL = API_BASE_URL;

let isRefreshing = false;
let failedQueue: Array<{
	resolve: (token: string) => void;
	reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
	failedQueue.forEach((prom) => {
		if (error) {
			prom.reject(error);
		} else if (token) {
			prom.resolve(token);
		}
	});
	failedQueue = [];
};

axios.interceptors.request.use(
	(config) => {
		const token = localStorage.getItem('access_token');
		if (token && config.headers) {
			config.headers['Authorization'] = `Bearer ${token}`;
		}
		if (config.headers) {
			config.headers['ngrok-skip-browser-warning'] = 'true';
		}
		return config;
	},
	(error) => Promise.reject(error),
);

axios.interceptors.response.use(
	(response) => response,
	async (error) => {
		const originalRequest = error.config;

		if (
			error.response?.status === 401 &&
			!originalRequest._retry &&
			originalRequest.url &&
			!originalRequest.url.includes('/api/v1/users/token/refresh/')
		) {
			if (isRefreshing) {
				return new Promise(function (resolve, reject) {
					failedQueue.push({ resolve, reject });
				})
					.then((token) => {
						originalRequest.headers['Authorization'] = `Bearer ${token}`;
						return axios(originalRequest);
					})
					.catch((err) => {
						return Promise.reject(err);
					});
			}

			originalRequest._retry = true;
			isRefreshing = true;

			try {
				const response = await axios.post(
					'/api/v1/users/token/refresh/',
					{},
					{
						withCredentials: true,
					},
				);

				const { access_token } = response.data;

				localStorage.setItem('access_token', access_token);
				OpenAPI.TOKEN = access_token;

				if (originalRequest.headers) {
					originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
				}

				processQueue(null, access_token);

				return axios(originalRequest);
			} catch (refreshError) {
				processQueue(refreshError, null);

				localStorage.removeItem('access_token');
				OpenAPI.TOKEN = undefined;

				console.error('Session strictly expired', refreshError);
				window.location.reload();

				return Promise.reject(refreshError);
			} finally {
				isRefreshing = false;
			}
		}

		return Promise.reject(error);
	},
);

/* eslint-disable react-refresh/only-export-components */
import { lazy } from 'react';
import { createMemoryRouter } from 'react-router-dom';
import { AppProvider } from '@/providers/AppProvider';

import { Layout } from '@/layouts/Layout';

const Shop = lazy(() => import('@/pages/Shop').then((m) => ({ default: m.Shop })));
const Cart = lazy(() => import('@/pages/Cart').then((m) => ({ default: m.Cart })));
const Checkout = lazy(() => import('@/pages/Checkout').then((m) => ({ default: m.Checkout })));
const Orders = lazy(() => import('@/pages/Orders').then((m) => ({ default: m.Orders })));
const Settings = lazy(() => import('@/pages/Settings').then((m) => ({ default: m.Settings })));

function Root() {
	return (
		<AppProvider>
			<Layout />
		</AppProvider>
	);
}

export const router = createMemoryRouter([
	{
		path: '/',
		element: <Root />,
		children: [
			{ index: true, element: <Shop /> },
			{ path: 'cart', element: <Cart /> },
			{ path: 'checkout', element: <Checkout /> },
			{ path: 'orders', element: <Orders /> },
			{ path: 'settings', element: <Settings /> },
		],
	},
]);

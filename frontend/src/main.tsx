import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import WebApp from '@twa-dev/sdk';

import App from './App.tsx';
import './styles/index.css';

import './api/client';

interface ExtendedTelegramWebApp {
	disableVerticalSwipes?: () => void;
}

WebApp.expand();
WebApp.enableClosingConfirmation();

const tgWebApp = WebApp as unknown as ExtendedTelegramWebApp;

if (typeof tgWebApp.disableVerticalSwipes === 'function') {
	tgWebApp.disableVerticalSwipes();
}

WebApp.ready();

const rootElement = document.getElementById('root');
if (!rootElement) {
	throw new Error('Failed to find the root element.');
}

createRoot(rootElement).render(
	<StrictMode>
		<App />
	</StrictMode>,
);

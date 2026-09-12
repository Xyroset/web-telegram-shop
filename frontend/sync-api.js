/**
 * Script to synchronize the OpenAPI schema from the DRF backend
 * and generate a strictly typed API client.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const rootEnvPath = path.resolve(__dirname, '../.env');
dotenv.config({ path: rootEnvPath });

const host = process.env.VITE_API_URL;

if (!host) {
	console.error('Error: VITE_API_URL is not defined in the environment variables.');
	process.exit(1);
}

const schemaUrl = `${host}/api/v1/core/schema/?format=json`;
const schemaPath = path.resolve(__dirname, 'schema.json');
const outputDir = path.resolve(__dirname, 'src/api');

async function syncApi() {
	console.log(`Fetching OpenAPI schema from: ${schemaUrl}`);

	try {
		const response = await fetch(schemaUrl);

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
		}

		const schemaText = await response.text();
		fs.writeFileSync(schemaPath, schemaText);
		console.log('Schema downloaded successfully. Running codegen...');

		execSync(
			`npx openapi-typescript-codegen --input ${schemaPath} --output ${outputDir} --client axios`,
			{ stdio: 'inherit' },
		);

		console.log('API Client successfully generated and updated!');
	} catch (error) {
		console.error('Failed to sync API:', error.message);
		process.exit(1);
	}
}

syncApi();

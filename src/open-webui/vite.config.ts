import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { resolveBuildInfo } from './scripts/build-info.js';

import { viteStaticCopy } from 'vite-plugin-static-copy';
import { kbProxyPlugin } from './src/lib/plugins/kb-proxy.js';

const backendTarget = process.env.WEBUI_BACKEND_URL || 'http://localhost:8080';
const kbIdentityUrl = process.env.CORP_KB_IDENTITY_URL || 'http://localhost:8001';
const kbGoUrl = process.env.CORP_KB_GO_URL || 'http://localhost:8002';
const kbRetrievalUrl = process.env.CORP_KB_RETRIEVAL_URL || 'http://localhost:8003';
const kbIngestionUrl = process.env.CORP_KB_INGESTION_URL || 'http://localhost:8004';
const buildInfo = resolveBuildInfo();

const kbProxy = {
	changeOrigin: true,
	ws: false
};

export default defineConfig({
	resolve: {
		conditions: ['onnxruntime-web-use-extern-wasm']
	},
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'src/lib/encryption/vendor/THIRD_PARTY_LICENSES.txt',
					dest: 'licenses/encryption'
				},
				{
					src: ['node_modules/@novnc/novnc/docs/LICENSE*', 'node_modules/@novnc/novnc/AUTHORS'],
					dest: 'licenses/novnc'
				},
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
					dest: 'wasm'
				}
			]
		}),
		kbProxyPlugin()
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(buildInfo.hash),
		APP_BUILD_CHANNEL: JSON.stringify(buildInfo.channel)
	},
	build: {
		target: 'es2022',
		sourcemap: true
	},
	optimizeDeps: {
		esbuildOptions: { target: 'es2022' }
	},
	server: {
		proxy: {
			'/api/kb/v1/identity': { ...kbProxy, target: kbIdentityUrl },
			'/api/kb/v1/authz': { ...kbProxy, target: kbIdentityUrl },
			'/api/kb/v1/groups': { ...kbProxy, target: kbIdentityUrl },
			'/api/kb/v1/policies': { ...kbProxy, target: kbIdentityUrl },
			'/api/kb/v1/documents': { ...kbProxy, target: kbGoUrl },
			'/api/kb/v1/proposals': { ...kbProxy, target: kbGoUrl },
			'/api/kb/v1/decisions': { ...kbProxy, target: kbGoUrl },
			'/api/kb/v1/spaces': { ...kbProxy, target: kbGoUrl },
			'/api/kb/v1/index': { ...kbProxy, target: kbRetrievalUrl },
			'/api/kb/v1/search': { ...kbProxy, target: kbRetrievalUrl },
			'/api/kb/v1/sources': { ...kbProxy, target: kbIngestionUrl },
			'/api/kb/v1/dry-runs': { ...kbProxy, target: kbIngestionUrl },
			'/api/kb/v1/import-packages': { ...kbProxy, target: kbIngestionUrl },
			'/api': {
				target: backendTarget,
				changeOrigin: true,
				ws: true
			},
			'/ollama': {
				target: backendTarget,
				changeOrigin: true
			},
			'/openai': {
				target: backendTarget,
				changeOrigin: true
			},
			'/oauth': {
				target: backendTarget,
				changeOrigin: true
			},
			'/ws': {
				target: backendTarget,
				changeOrigin: true,
				ws: true
			}
		}
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});

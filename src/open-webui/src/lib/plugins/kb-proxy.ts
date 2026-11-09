/**
 * Vite dev-server proxy plugin for corp-ai-db backend seams.
 *
 * Open WebUI's own backend is served from WEBUI_BACKEND_URL (default
 * http://localhost:8080) via the catch-all `/api` proxy. The KB seam uses
 * dedicated backend services running on different ports during local
 * development. This plugin injects more specific proxy rules so requests
 * under `/api/kb/v1/*` are routed to the correct service.
 *
 * Environment variables:
 *   - CORP_KB_IDENTITY_URL          (default: http://localhost:8001)
 *   - CORP_KB_GO_URL                (default: http://localhost:8002)
 *   - CORP_KB_RETRIEVAL_URL         (default: http://localhost:8003)
 *   - CORP_KB_INGESTION_URL         (default: http://localhost:8004)
 */

import type { Plugin, ProxyOptions } from 'vite';

interface KBProxyEnv {
	readonly CORP_KB_IDENTITY_URL?: string;
	readonly CORP_KB_GO_URL?: string;
	readonly CORP_KB_RETRIEVAL_URL?: string;
	readonly CORP_KB_INGESTION_URL?: string;
}

const identityUrl = (process.env as unknown as KBProxyEnv).CORP_KB_IDENTITY_URL || 'http://localhost:8001';
const goUrl = (process.env as unknown as KBProxyEnv).CORP_KB_GO_URL || 'http://localhost:8002';
const retrievalUrl = (process.env as unknown as KBProxyEnv).CORP_KB_RETRIEVAL_URL || 'http://localhost:8003';
const ingestionUrl = (process.env as unknown as KBProxyEnv).CORP_KB_INGESTION_URL || 'http://localhost:8004';

const proxyDefaults: ProxyOptions = {
	changeOrigin: true,
	ws: false
};

export function kbProxyPlugin(): Plugin {
	return {
		name: 'corp-kb-proxy',
		config: () => ({
			server: {
				proxy: {
					'/api/kb/v1/identity': { ...proxyDefaults, target: identityUrl },
					'/api/kb/v1/authz': { ...proxyDefaults, target: identityUrl },
					'/api/kb/v1/groups': { ...proxyDefaults, target: identityUrl },
					'/api/kb/v1/policies': { ...proxyDefaults, target: identityUrl },
					'/api/kb/v1/documents': { ...proxyDefaults, target: goUrl },
					'/api/kb/v1/proposals': { ...proxyDefaults, target: goUrl },
					'/api/kb/v1/decisions': { ...proxyDefaults, target: goUrl },
					'/api/kb/v1/spaces': { ...proxyDefaults, target: goUrl },
					'/api/kb/v1/index': { ...proxyDefaults, target: retrievalUrl },
					'/api/kb/v1/search': { ...proxyDefaults, target: retrievalUrl },
					'/api/kb/v1/sources': { ...proxyDefaults, target: ingestionUrl },
					'/api/kb/v1/dry-runs': { ...proxyDefaults, target: ingestionUrl },
					'/api/kb/v1/import-packages': { ...proxyDefaults, target: ingestionUrl }
				}
			}
		})
	};
}

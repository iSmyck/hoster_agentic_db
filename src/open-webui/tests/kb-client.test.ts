import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
	KBClient,
	KBApiError,
	type ExternalRef,
	type KBTreeResponse,
	type KBDocumentReadResponse,
	type IdentityResponse,
	type AuthzContextResponse,
	type PathCheckResponse
} from '$lib/api/kb.js';

const GIT_URL = 'http://git-orchestrator.test/api/kb/v1';
const IDENTITY_URL = 'http://identity.test/api/kb/v1';
const SPACE_ID = 'space-42';
const SHA = 'c38885a1a737da4968f157092f304f3b5481d0bf';

function asFetch(mock: ReturnType<typeof vi.fn>): typeof fetch {
	return mock as unknown as typeof fetch;
}

function mockResponse(body: unknown, status = 200, headers?: Record<string, string>) {
	return {
		ok: status >= 200 && status < 300,
		status,
		headers: new Headers(headers ?? {}),
		json: async () => body
	} as Response;
}

describe('KBClient', () => {
	let fetchMock: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		fetchMock = vi.fn();
	});

	it('getKBTree posts the expected payload and returns entries', async () => {
		const tree: KBTreeResponse = {
			space_id: SPACE_ID,
			sha: SHA,
			entries: [
				{ path: 'README.md', type: 'blob', sha: 'aabbccdd11223344556677889900aabbccdd1122', mode: '100644' }
			]
		};
		fetchMock.mockResolvedValueOnce(mockResponse(tree));

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		const result = await client.getKBTree(SPACE_ID, SHA);

		expect(fetchMock).toHaveBeenCalledWith(
			`${GIT_URL}/documents/tree`,
			expect.objectContaining({
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ space_id: SPACE_ID, sha: SHA })
			})
		);
		expect(result).toEqual(tree);
	});

	it('readKBDocument posts path and sha', async () => {
		const doc: KBDocumentReadResponse = {
			space_id: SPACE_ID,
			path: 'README.md',
			sha: SHA,
			content: '# Hello KB'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(doc));

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		const result = await client.readKBDocument(SPACE_ID, 'README.md', SHA);

		expect(fetchMock).toHaveBeenCalledWith(
			`${GIT_URL}/documents/read`,
			expect.objectContaining({
				body: JSON.stringify({ space_id: SPACE_ID, path: 'README.md', sha: SHA })
			})
		);
		expect(result).toEqual(doc);
	});

	it('resolveIdentity posts external_ref', async () => {
		const ref: ExternalRef = { issuer: 'keycloak', sub: 'user-123' };
		const identity: IdentityResponse = {
			id: 'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4',
			external_refs: [ref as unknown as Record<string, unknown>],
			created_at: '2026-11-09T08:00:00Z'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(identity));

		const client = new KBClient({ identityUrl: IDENTITY_URL, fetchImpl: asFetch(fetchMock) });
		const result = await client.resolveIdentity(ref);

		expect(fetchMock).toHaveBeenCalledWith(
			`${IDENTITY_URL}/identity/resolve`,
			expect.objectContaining({
				body: JSON.stringify({ external_ref: ref })
			})
		);
		expect(result).toEqual(identity);
	});

	it('getAuthzContext posts actor information', async () => {
		const context: AuthzContextResponse = {
			schema_version: 'authz-context-v2',
			context_id: 'f5e4d3c2-b1a0-4fed-9cba-0123456789ab',
			issuer: 'corp-kb-identity',
			stable_id: 'user-123',
			actor_type: 'human',
			space_scopes: [],
			path_scopes: [],
			evaluated_at: '2026-11-09T08:00:00Z',
			expires_at: '2026-11-09T09:00:00Z',
			revocation_epoch: 1
		};
		fetchMock.mockResolvedValueOnce(mockResponse(context));

		const client = new KBClient({ identityUrl: IDENTITY_URL, fetchImpl: asFetch(fetchMock) });
		const result = await client.getAuthzContext(SPACE_ID, 'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4');

		expect(fetchMock).toHaveBeenCalledWith(
			`${IDENTITY_URL}/authz/context`,
			expect.objectContaining({
				body: JSON.stringify({
					space_id: SPACE_ID,
					actor_id: 'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4',
					actor_type: 'human'
				})
			})
		);
		expect(result).toEqual(context);
	});

	it('checkPath posts space, actor and path', async () => {
		const check: PathCheckResponse = {
			approved: true,
			space_id: SPACE_ID,
			actor_id: 'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4',
			path: 'README.md',
			matched_prefix: '',
			reason: 'owner'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(check));

		const client = new KBClient({ identityUrl: IDENTITY_URL, fetchImpl: asFetch(fetchMock) });
		const result = await client.checkPath(
			SPACE_ID,
			'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4',
			'README.md'
		);

		expect(fetchMock).toHaveBeenCalledWith(
			`${IDENTITY_URL}/authz/check`,
			expect.objectContaining({
				body: JSON.stringify({
					space_id: SPACE_ID,
					actor_id: 'e6b0ba76-4e62-402f-8d53-7e34e9b2c3d4',
					path: 'README.md'
				})
			})
		);
		expect(result).toEqual(check);
	});

	it('throws KBApiError with structured fields on 404', async () => {
		fetchMock.mockResolvedValueOnce(
			mockResponse(
				{ code: 'NOT_FOUND', message: 'No such document' },
				404,
				{ 'x-request-id': 'req-abc' }
			)
		);

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		let caught: unknown;
		try {
			await client.readKBDocument(SPACE_ID, 'missing.md', SHA);
		} catch (err) {
			caught = err;
		}

		expect(caught).toBeInstanceOf(KBApiError);
		const apiErr = caught as KBApiError;
		expect(apiErr.code).toBe('NOT_FOUND');
		expect(apiErr.message).toBe('No such document');
		expect(apiErr.requestId).toBe('req-abc');
		expect(apiErr.retryable).toBe(false);
		expect(apiErr.statusCode).toBe(404);
	});

	it('marks 5xx errors as retryable', async () => {
		fetchMock.mockResolvedValueOnce(mockResponse({ code: 'ADAPTER_ERROR', message: 'GitLab down' }, 502));

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		let caught: unknown;
		try {
			await client.getKBTree(SPACE_ID, SHA);
		} catch (err) {
			caught = err;
		}

		expect(caught).toBeInstanceOf(KBApiError);
		const apiErr = caught as KBApiError;
		expect(apiErr.code).toBe('ADAPTER_ERROR');
		expect(apiErr.retryable).toBe(true);
	});

	it('throws TIMEOUT error when fetch aborts', async () => {
		fetchMock.mockImplementation(
			async () =>
				new Promise((_, reject) => {
					const err = new Error('The operation was aborted');
					err.name = 'AbortError';
					reject(err);
				})
		);

		const client = new KBClient({
			gitOrchestratorUrl: GIT_URL,
			fetchImpl: asFetch(fetchMock),
			timeoutMs: 10
		});
		await expect(client.getKBTree(SPACE_ID, SHA)).rejects.toThrow(KBApiError);
		try {
			await client.getKBTree(SPACE_ID, SHA);
		} catch (err) {
			const apiErr = err as KBApiError;
			expect(apiErr.code).toBe('TIMEOUT');
			expect(apiErr.retryable).toBe(true);
		}
	});

	it('readKBDocumentView extracts attachments from Markdown', async () => {
		const doc: KBDocumentReadResponse = {
			space_id: SPACE_ID,
			path: 'guide.md',
			sha: SHA,
			content: '# Guide\n\nSee [diagram](./assets/diagram.png) and [same](./assets/diagram.png).'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(doc));

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		const view = await client.readKBDocumentView(SPACE_ID, 'guide.md', SHA);

		expect(view.title).toBe('guide.md');
		expect(view.attachments).toHaveLength(1);
		expect(view.attachments[0].name).toBe('diagram.png');
		expect(view.attachments[0].path).toBe('./assets/diagram.png');
	});

	it('readKBDocumentView skips non-local and non-attachment schemes', async () => {
		const doc: KBDocumentReadResponse = {
			space_id: SPACE_ID,
			path: 'guide.md',
			sha: SHA,
			content:
				'# Guide\n\n' +
				'External [site](https://example.com/x.png), ' +
				'email [contact](mailto:a@b.com), ' +
				'local [diagram](./assets/diagram.png).'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(doc));

		const client = new KBClient({ gitOrchestratorUrl: GIT_URL, fetchImpl: asFetch(fetchMock) });
		const view = await client.readKBDocumentView(SPACE_ID, 'guide.md', SHA);

		expect(view.attachments).toHaveLength(1);
		expect(view.attachments[0].path).toBe('./assets/diagram.png');
	});

	it('treats timeoutMs: 0 as no timeout', async () => {
		const doc: KBDocumentReadResponse = {
			space_id: SPACE_ID,
			path: 'guide.md',
			sha: SHA,
			content: '# Guide'
		};
		fetchMock.mockResolvedValueOnce(mockResponse(doc));

		const client = new KBClient({
			gitOrchestratorUrl: GIT_URL,
			fetchImpl: asFetch(fetchMock),
			timeoutMs: 0
		});
		const result = await client.readKBDocument(SPACE_ID, 'guide.md', SHA);

		expect(result).toEqual(doc);
		expect(fetchMock).toHaveBeenCalledWith(
			expect.any(String),
			expect.objectContaining({ signal: expect.any(AbortSignal) })
		);
	});
});

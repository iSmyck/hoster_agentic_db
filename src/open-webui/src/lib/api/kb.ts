/**
 * Typed KB API client for the corporate knowledge-base seams.
 *
 * Endpoints:
 *   - git-orchestrator: POST /api/kb/v1/documents/tree
 *                       POST /api/kb/v1/documents/read
 *   - identity:         POST /api/kb/v1/identity/resolve
 *                       POST /api/kb/v1/authz/context
 *                       POST /api/kb/v1/authz/check
 *
 * Environment variables:
 *   - CORP_KB_GIT_ORCHESTRATOR_URL  (default: /api/kb/v1, proxied by Vite)
 *   - CORP_KB_IDENTITY_URL          (default: /api/kb/v1, proxied by Vite)
 *   - CORP_KB_REQUEST_TIMEOUT_MS    (default: 30000)
 */



declare global {
	interface ImportMetaEnv {
		readonly CORP_KB_GIT_ORCHESTRATOR_URL?: string;
		readonly CORP_KB_IDENTITY_URL?: string;
		readonly CORP_KB_REQUEST_TIMEOUT_MS?: string;
	}

	interface ImportMeta {
		readonly env: ImportMetaEnv;
	}
}

export interface ExternalRef {
	issuer: string;
	sub: string;
}

export interface TreeEntry {
	path: string;
	type: string;
	sha: string;
	mode?: string | null;
}

export interface KBTreeResponse {
	space_id: string;
	sha: string;
	entries: TreeEntry[];
}

export interface KBDocumentReadResponse {
	space_id: string;
	path: string;
	sha: string;
	content: string;
}

export interface KBAttachment {
	name: string;
	path: string;
	sha: string;
}

export interface KBDocumentReadView {
	title: string;
	body: string;
	attachments: KBAttachment[];
	sha: string;
}

export interface IdentityResponse {
	id: string;
	external_refs: Array<Record<string, unknown>>;
	created_at: string;
}

export interface AuthzContextResponse {
	schema_version: string;
	context_id: string;
	issuer: string;
	stable_id: string;
	actor_type: string;
	space_scopes: Array<Record<string, unknown>>;
	path_scopes: Array<Record<string, unknown>>;
	evaluated_at: string;
	expires_at: string;
	revocation_epoch: number;
}

export interface PathCheckResponse {
	approved: boolean;
	space_id: string;
	actor_id: string;
	path: string;
	matched_prefix?: string | null;
	reason: string;
}

export interface ProposalRecord {
	id: string;
	space_id: string;
	proposal_sha: string;
	base_sha: string;
	target_sha?: string | null;
	status: string;
	idempotency_key: string;
	created_at: string;
}

export interface DecisionRecord {
	id: string;
	proposal_id: string;
	outcome: string;
	actor_id: string;
	idempotency_key: string;
	record_sha256: string;
	note_id?: number | null;
	tag_name: string;
	state: string;
	supersedes_decision_id?: string | null;
	created_at: string;
}

export interface ProposalSubmitRequest {
	space_id: string;
	proposal_sha: string;
	base_sha: string;
	target_sha?: string | null;
	target_branch?: string;
	idempotency_key: string;
	proposal_data: Record<string, unknown>;
}

export interface DecisionSubmitRequest {
	proposal_id: string;
	action: 'accepted' | 'rejected' | 'cancelled';
	actor_id: string;
	idempotency_key: string;
	decision_data: Record<string, unknown>;
}

export interface MergeResponse {
	proposal_id: string;
	status: string;
	merge_sha?: string | null;
	detail: string;
	fence_token?: number | null;
	recovery_required?: boolean | null;
}

export interface KBApiErrorDetail {
	code: string;
	message: string;
	request_id?: string;
	retryable?: boolean;
}

export class KBApiError extends Error {
	code: string;
	requestId: string;
	retryable: boolean;
	statusCode?: number;

	constructor(detail: KBApiErrorDetail, statusCode?: number) {
		super(detail.message);
		this.name = 'KBApiError';
		this.code = detail.code;
		this.requestId = detail.request_id ?? 'unknown';
		this.retryable = detail.retryable ?? isRetryableStatus(statusCode);
		this.statusCode = statusCode;
	}
}

function isRetryableStatus(status?: number): boolean {
	if (status === undefined) return true;
	return status >= 500 || status === 429 || status === 408;
}

function extractRequestId(response: Response | undefined): string {
	if (!response) return 'unknown';
	if ('headers' in response) {
		const headers = response.headers as Headers | Record<string, string>;
		if (headers instanceof Headers) {
			return headers.get('x-request-id') ?? headers.get('X-Request-ID') ?? 'unknown';
		}
		return (
			(headers['x-request-id'] as string | undefined) ??
			(headers['X-Request-ID'] as string | undefined) ??
			'unknown'
		);
	}
	return 'unknown';
}

function extractErrorDetail(
	body: unknown,
	requestId: string,
	statusCode?: number
): KBApiErrorDetail {
	if (body && typeof body === 'object') {
		const obj = body as Record<string, unknown>;
		const detail =
			obj.detail && typeof obj.detail === 'object'
				? (obj.detail as Record<string, unknown>)
				: obj;
		return {
			code: String(detail.code ?? 'API_ERROR'),
			message: String(detail.message ?? 'KB API request failed'),
			request_id: String(detail.request_id ?? requestId),
			retryable:
				typeof detail.retryable === 'boolean'
					? detail.retryable
					: isRetryableStatus(statusCode)
		};
	}
	return {
		code: 'API_ERROR',
		message: 'KB API request failed',
		request_id: requestId,
		retryable: isRetryableStatus(statusCode)
	};
}

export interface KBClientOptions {
	gitOrchestratorUrl?: string;
	identityUrl?: string;
	timeoutMs?: number;
	fetchImpl?: typeof fetch;
}

export class KBClient {
	private gitUrl: string;
	private identityUrl: string;
	private timeoutMs: number;
	private fetchImpl: typeof fetch;

	constructor(options: KBClientOptions = {}) {
		this.gitUrl = (options.gitOrchestratorUrl ?? import.meta.env?.CORP_KB_GIT_ORCHESTRATOR_URL) || '/api/kb/v1';
		this.identityUrl = (options.identityUrl ?? import.meta.env?.CORP_KB_IDENTITY_URL) || '/api/kb/v1';
		this.timeoutMs =
			options.timeoutMs === 0
				? 0
				: (options.timeoutMs ?? (Number(import.meta.env?.CORP_KB_REQUEST_TIMEOUT_MS) || 30000));
		this.fetchImpl = options.fetchImpl ?? fetch;
	}

	private async post<T>(baseUrl: string, path: string, body: unknown): Promise<T> {
		const url = `${baseUrl.replace(/\/$/, '')}${path}`;
		let response: Response;

		try {
			const controller = new AbortController();
			const timer =
				this.timeoutMs > 0 ? setTimeout(() => controller.abort(), this.timeoutMs) : null;
			response = await this.fetchImpl(url, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
				signal: controller.signal
			});
			if (timer) clearTimeout(timer);
		} catch (err) {
			const isTimeout = err instanceof Error && err.name === 'AbortError';
			throw new KBApiError({
				code: isTimeout ? 'TIMEOUT' : 'NETWORK_ERROR',
				message: isTimeout ? 'KB request timed out' : 'KB request failed',
				request_id: 'unknown',
				retryable: true
			});
		}

		const requestId = extractRequestId(response);

		if (!response.ok) {
			let body: unknown;
			try {
				body = await response.json();
			} catch {
				body = undefined;
			}
			throw new KBApiError(extractErrorDetail(body, requestId, response.status), response.status);
		}

		try {
			return (await response.json()) as T;
		} catch {
			throw new KBApiError(
				{
					code: 'INVALID_RESPONSE',
					message: 'KB response was not valid JSON',
					request_id: requestId,
					retryable: false
				},
				response.status
			);
		}
	}

	/**
	 * Fetch the document tree for a Space at an exact commit SHA.
	 */
	async getKBTree(spaceId: string, sha: string): Promise<KBTreeResponse> {
		return this.post<KBTreeResponse>(this.gitUrl, '/documents/tree', { space_id: spaceId, sha });
	}

	/**
	 * Read a single document at an exact commit SHA.
	 */
	async readKBDocument(
		spaceId: string,
		path: string,
		sha: string
	): Promise<KBDocumentReadResponse> {
		return this.post<KBDocumentReadResponse>(this.gitUrl, '/documents/read', {
			space_id: spaceId,
			path,
			sha
		});
	}

	/**
	 * Resolve an external identity reference to a stable internal identity.
	 */
	async resolveIdentity(ref: ExternalRef): Promise<IdentityResponse> {
		return this.post<IdentityResponse>(this.identityUrl, '/identity/resolve', {
			external_ref: ref
		});
	}

	/**
	 * Compute the authorization context for an actor in a Space.
	 */
	async getAuthzContext(
		spaceId: string,
		actorId: string,
		actorType: 'human' | 'agent' | 'connector' | 'internal_ci' = 'human'
	): Promise<AuthzContextResponse> {
		return this.post<AuthzContextResponse>(this.identityUrl, '/authz/context', {
			space_id: spaceId,
			actor_id: actorId,
			actor_type: actorType
		});
	}

	/**
	 * Check whether an actor is authorized to touch a path in a Space.
	 */
	async checkPath(spaceId: string, actorId: string, path: string): Promise<PathCheckResponse> {
		return this.post<PathCheckResponse>(this.identityUrl, '/authz/check', {
			space_id: spaceId,
			actor_id: actorId,
			path
		});
	}

	/**
	 * Convenience helper: read a document and return a view model with title,
	 * body, attachments and SHA. Attachments are inferred from Markdown image/link
	 * syntax and de-duplicated by path.
	 */
	async readKBDocumentView(
		spaceId: string,
		path: string,
		sha: string
	): Promise<KBDocumentReadView> {
		const raw = await this.readKBDocument(spaceId, path, sha);
		const title = raw.path.split('/').pop() ?? raw.path;
		const attachments = extractAttachments(raw.content);
		return { title, body: raw.content, attachments, sha: raw.sha };
	}

	/**
	 * Submit a new proposal to the Git Orchestrator.
	 */
	async submitProposal(request: ProposalSubmitRequest): Promise<ProposalRecord> {
		return this.post<ProposalRecord>(this.gitUrl, '/proposals', request);
	}

	/**
	 * Record a human decision for a proposal.
	 */
	async recordDecision(request: DecisionSubmitRequest): Promise<DecisionRecord> {
		return this.post<DecisionRecord>(this.gitUrl, '/decisions', request);
	}

	/**
	 * Execute an accepted proposal merge.
	 */
	async executeMerge(proposalId: string): Promise<MergeResponse> {
		return this.post<MergeResponse>(this.gitUrl, `/proposals/${proposalId}/merge`, {});
	}

	/**
	 * Reconcile a quarantined merge attempt using Git-derived evidence.
	 */
	async reconcileMerge(proposalId: string): Promise<MergeResponse> {
		return this.post<MergeResponse>(this.gitUrl, `/proposals/${proposalId}/reconcile`, {});
	}

	/**
	 * Recheck upstream group membership before a sensitive operation.
	 */
	async recheckGroups(spaceId: string, accessToken: string): Promise<{ space_id: string; epoch: number; groups: string[]; groups_ingested: number }> {
		return this.post(this.identityUrl, '/groups/recheck', { space_id: spaceId, access_token: accessToken });
	}
}

function isLocalAttachment(href: string): boolean {
	// Use the URL parser for absolute URLs so schemes like mailto:, tel:,
	// javascript:, data: etc. are skipped alongside external http/https links.
	// Relative paths and file: URLs are treated as local attachments.
	if (/^[a-z][a-z0-9+.-]*:/i.test(href)) {
		try {
			const url = new URL(href);
			return url.protocol === 'file:';
		} catch {
			return false;
		}
	}
	return true;
}

function extractAttachments(markdown: string): KBAttachment[] {
	const seen = new Set<string>();
	const attachments: KBAttachment[] = [];
	const linkPattern = /!?\[([^\]]*)\]\(([^)]+)\)/g;
	let match: RegExpExecArray | null;
	while ((match = linkPattern.exec(markdown)) !== null) {
		const href = match[2];
		if (!isLocalAttachment(href)) continue;
		if (seen.has(href)) continue;
		seen.add(href);
		attachments.push({
			name: href.split('/').pop() || href,
			path: href,
			sha: '' // SHA is resolved separately if the attachment tree is loaded.
		});
	}
	return attachments;
}



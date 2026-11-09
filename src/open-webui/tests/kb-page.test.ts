// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import KBPage from '$lib/routes/kb/+page.svelte';
import {
	KBClient,
	KBApiError,
	type TreeEntry,
	type KBDocumentReadView,
	type PathCheckResponse
} from '$lib/api/kb.js';

const SPACE_ID = 'space-42';
const SHA = 'c38885a1a737da4968f157092f304f3b5481d0bf';
const ACTOR_ID = 'actor-1';

const entries: TreeEntry[] = [
	{ path: 'README.md', type: 'blob', sha: 'aaa' },
	{ path: 'docs/guide.md', type: 'blob', sha: 'bbb' }
];

const documentView: KBDocumentReadView = {
	title: 'README.md',
	body: '# Hello',
	sha: SHA,
	attachments: []
};

vi.mock('$lib/api/kb.js', async (importOriginal) => {
	const actual = await importOriginal<typeof import('$lib/api/kb.js')>();
	return {
		...actual,
		KBClient: vi.fn()
	};
});

function createMockClient(overrides: Partial<InstanceType<typeof KBClient>> = {}) {
	return {
		getKBTree: vi.fn().mockResolvedValue({ space_id: SPACE_ID, sha: SHA, entries }),
		readKBDocumentView: vi.fn().mockResolvedValue(documentView),
		checkPath: vi.fn().mockResolvedValue({ approved: true, reason: 'owner' } as PathCheckResponse),
		...overrides
	};
}

describe('kb/+page.svelte', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('loads and displays the tree when spaceId and sha are provided', async () => {
		const mockClient = createMockClient();
		vi.mocked(KBClient).mockImplementation(() => mockClient as unknown as KBClient);

		render(KBPage, { props: { spaceId: SPACE_ID, sha: SHA } });

		await waitFor(() => {
			expect(screen.getByText('README.md')).toBeInTheDocument();
			expect(screen.getByText('docs/guide.md')).toBeInTheDocument();
		});
		expect(mockClient.getKBTree).toHaveBeenCalledWith(SPACE_ID, SHA);
	});

	it('shows a document when an entry is selected', async () => {
		const mockClient = createMockClient();
		vi.mocked(KBClient).mockImplementation(() => mockClient as unknown as KBClient);

		render(KBPage, { props: { spaceId: SPACE_ID, sha: SHA, actorId: ACTOR_ID } });

		await waitFor(() => expect(screen.getByText('README.md')).toBeInTheDocument());

		await fireEvent.click(screen.getByText('README.md'));

		await waitFor(() => {
			expect(screen.getByRole('heading', { name: 'README.md' })).toBeInTheDocument();
		});
		expect(mockClient.checkPath).toHaveBeenCalledWith(SPACE_ID, ACTOR_ID, 'README.md');
		expect(mockClient.readKBDocumentView).toHaveBeenCalledWith(SPACE_ID, 'README.md', SHA);
	});

	it('hides the document and shows an error when checkPath returns approved: false', async () => {
		const mockClient = createMockClient({
			checkPath: vi.fn().mockResolvedValue({
				approved: false,
				reason: 'restricted path'
			} as PathCheckResponse)
		});
		vi.mocked(KBClient).mockImplementation(() => mockClient as unknown as KBClient);

		render(KBPage, { props: { spaceId: SPACE_ID, sha: SHA, actorId: ACTOR_ID } });

		await waitFor(() => expect(screen.getByText('README.md')).toBeInTheDocument());

		await fireEvent.click(screen.getByText('README.md'));

		await waitFor(() => {
			expect(screen.getByRole('alert')).toHaveTextContent('Access denied: restricted path');
		});
		expect(screen.queryByRole('heading', { name: 'README.md' })).not.toBeInTheDocument();
		expect(mockClient.readKBDocumentView).not.toHaveBeenCalled();
	});

	it('reloads the tree when spaceId or sha props change', async () => {
		const mockClient = createMockClient();
		vi.mocked(KBClient).mockImplementation(() => mockClient as unknown as KBClient);

		const { rerender } = render(KBPage, { props: { spaceId: SPACE_ID, sha: SHA } });

		await waitFor(() => expect(mockClient.getKBTree).toHaveBeenCalledTimes(1));

		const newSpaceId = 'space-99';
		const newSha = 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeef';

		rerender({ spaceId: newSpaceId, sha: newSha });

		await waitFor(() => expect(mockClient.getKBTree).toHaveBeenCalledTimes(2));
		expect(mockClient.getKBTree).toHaveBeenLastCalledWith(newSpaceId, newSha);
	});

	it('displays a tree loading error when getKBTree fails', async () => {
		const mockClient = createMockClient({
			getKBTree: vi.fn().mockRejectedValue(new KBApiError({ code: 'NETWORK_ERROR', message: 'down' }))
		});
		vi.mocked(KBClient).mockImplementation(() => mockClient as unknown as KBClient);

		render(KBPage, { props: { spaceId: SPACE_ID, sha: SHA } });

		await waitFor(() => {
			expect(screen.getByRole('alert')).toHaveTextContent('NETWORK_ERROR: down');
		});
	});
});

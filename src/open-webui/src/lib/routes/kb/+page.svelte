<script lang="ts">
	import { KBClient, KBApiError, type TreeEntry, type KBDocumentReadView, type ProposalRecord, type DecisionRecord, type MergeResponse } from '$lib/api/kb.js';
	import KBTree from '$lib/components/KBTree.svelte';
	import KBDocumentRead from '$lib/components/KBDocumentRead.svelte';
	import KBEditor from '$lib/components/KBEditor.svelte';
	import KBReview from '$lib/components/KBReview.svelte';

	interface Props {
		spaceId?: string;
		sha?: string;
		actorId?: string;
	}

	let { spaceId = '', sha = '', actorId = '' }: Props = $props();

	let client = $state(new KBClient());
	let entries = $state<TreeEntry[]>([]);
	let selectedPath = $state<string>('');
	let document = $state<KBDocumentReadView | undefined>(undefined);
	let treeLoading = $state(false);
	let docLoading = $state(false);
	let treeError = $state('');
	let docError = $state('');

	let mode = $state<'read' | 'edit' | 'review'>('read');
	let editedContent = $state('');
	let proposal = $state<ProposalRecord | undefined>(undefined);
	let lastDecision = $state<DecisionRecord | undefined>(undefined);
	let lastMerge = $state<MergeResponse | undefined>(undefined);

	async function loadTree() {
		if (!spaceId || !sha) return;
		treeLoading = true;
		treeError = '';
		try {
			const response = await client.getKBTree(spaceId, sha);
			entries = response.entries;
		} catch (err) {
			treeError = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			treeLoading = false;
		}
	}

	async function handleSelect(entry: TreeEntry) {
		selectedPath = entry.path;
		document = undefined;
		mode = 'read';
		if (entry.type === 'tree' || entry.path.endsWith('/')) {
			return;
		}
		if (!spaceId || !sha) return;
		docLoading = true;
		docError = '';
		try {
			if (actorId) {
				const check = await client.checkPath(spaceId, actorId, entry.path);
				if (check.approved === false) {
					docError = `Access denied: ${check.reason}`;
					return;
				}
			}
			document = await client.readKBDocumentView(spaceId, entry.path, sha);
			editedContent = document.body;
		} catch (err) {
			docError = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			docLoading = false;
		}
	}

	function startEdit() {
		if (!document) return;
		editedContent = document.body;
		mode = 'edit';
	}

	async function submitProposal() {
		if (!spaceId || !sha || !selectedPath || !actorId) return;
		docLoading = true;
		docError = '';
		try {
			proposal = await client.submitProposal({
				space_id: spaceId,
				proposal_sha: sha,
				base_sha: sha,
				target_branch: 'main',
				idempotency_key: `ui-proposal-${selectedPath}-${Date.now()}`,
				proposal_data: {
					path: selectedPath,
					content: editedContent,
					author_stable_id: actorId,
					requester_stable_id: actorId
				}
			});
			mode = 'review';
		} catch (err) {
			docError = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			docLoading = false;
		}
	}

	function handleDecision(decision: DecisionRecord) {
		lastDecision = decision;
	}

	function handleMerge(result: MergeResponse) {
		lastMerge = result;
		if (result.status === 'merged') {
			mode = 'read';
			proposal = undefined;
			lastDecision = undefined;
			loadTree();
		}
	}

	$effect(() => {
		if (spaceId && sha) {
			loadTree();
		}
	});
</script>

<svelte:head>
	<title>Knowledge Base</title>
</svelte:head>

<div class="kb-page grid grid-cols-1 md:grid-cols-3 gap-4 h-screen p-4">
	<aside class="md:col-span-1 border rounded-lg p-3 bg-white shadow-sm">
		<KBTree
			{entries}
			{selectedPath}
			loading={treeLoading}
			error={treeError}
			onSelect={handleSelect}
		/>
	</aside>

	<main class="md:col-span-2 border rounded-lg p-4 bg-white shadow-sm flex flex-col gap-4">
		{#if mode === 'read'}
			<KBDocumentRead {document} loading={docLoading} error={docError} />
			{#if document}
				<div class="flex gap-2">
					<button
						class="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
						on:click={startEdit}
					>
						Edit
					</button>
				</div>
			{/if}
		{:else if mode === 'edit'}
			<KBEditor content={editedContent} onChange={(c) => (editedContent = c)} />
			<div class="flex gap-2">
				<button
					class="px-3 py-1.5 text-sm rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
					disabled={docLoading}
					on:click={submitProposal}
				>
					Submit Proposal
				</button>
				<button
					class="px-3 py-1.5 text-sm rounded bg-gray-500 text-white hover:bg-gray-600"
					on:click={() => (mode = 'read')}
				>
					Cancel
				</button>
			</div>
			{#if docError}
				<p class="text-sm text-red-600" role="alert">{docError}</p>
			{/if}
		{:else if mode === 'review'}
			<KBReview {proposal} {actorId} onDecision={handleDecision} onMerge={handleMerge} />
			{#if lastDecision}
				<p class="text-sm text-gray-600">
					Decision {lastDecision.outcome} recorded ({lastDecision.state}).
				</p>
			{/if}
			{#if lastMerge}
				<p class="text-sm text-gray-600">Merge: {lastMerge.status} — {lastMerge.detail}</p>
			{/if}
			<button
				class="px-3 py-1.5 text-sm rounded bg-gray-500 text-white hover:bg-gray-600 w-fit"
				on:click={() => (mode = 'read')}
			>
				Back to document
			</button>
		{/if}
	</main>
</div>

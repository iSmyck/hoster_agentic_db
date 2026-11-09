<script lang="ts">
	import { KBClient, KBApiError, type TreeEntry, type KBDocumentReadView } from '$lib/api/kb.js';
	import KBTree from '$lib/components/KBTree.svelte';
	import KBDocumentRead from '$lib/components/KBDocumentRead.svelte';

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
		} catch (err) {
			docError = err instanceof KBApiError ? `${err.code}: ${err.message}` : String(err);
		} finally {
			docLoading = false;
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

	<main class="md:col-span-2 border rounded-lg p-4 bg-white shadow-sm">
		<KBDocumentRead {document} loading={docLoading} error={docError} />
	</main>
</div>

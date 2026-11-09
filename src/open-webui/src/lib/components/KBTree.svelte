<script lang="ts">
	import type { TreeEntry } from '$lib/api/kb.js';

	interface Props {
		entries: TreeEntry[];
		selectedPath?: string;
		loading?: boolean;
		error?: string;
		onSelect?: (entry: TreeEntry) => void;
	}

	let { entries, selectedPath = '', loading = false, error = '', onSelect }: Props = $props();

	function handleClick(entry: TreeEntry) {
		onSelect?.(entry);
	}

	function isFolder(entry: TreeEntry): boolean {
		return entry.type === 'tree' || entry.path.endsWith('/');
	}
</script>

<div class="kb-tree flex flex-col h-full overflow-auto">
	<h2 class="text-lg font-semibold mb-2">Space documents</h2>

	{#if loading}
		<p class="text-sm text-gray-500">Loading tree…</p>
	{:else if error}
		<p class="text-sm text-red-600" role="alert">{error}</p>
	{:else if entries.length === 0}
		<p class="text-sm text-gray-500">No documents found.</p>
	{:else}
		<ul class="space-y-1">
			{#each entries as entry (entry.path)}
				<li>
					<button
						type="button"
						class="w-full text-left px-2 py-1 rounded hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
						class:bg-blue-50={selectedPath === entry.path}
						aria-current={selectedPath === entry.path ? 'true' : undefined}
						onclick={() => handleClick(entry)}
					>
						<span class="inline-block w-5 text-gray-400">
							{isFolder(entry) ? '📁' : '📄'}
						</span>
						<span class="text-sm">{entry.path}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

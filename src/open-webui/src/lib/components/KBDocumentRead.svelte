<script lang="ts">
	import type { KBDocumentReadView } from '$lib/api/kb.js';

	interface Props {
		document?: KBDocumentReadView;
		loading?: boolean;
		error?: string;
	}

	let { document, loading = false, error = '' }: Props = $props();
</script>

<div class="kb-document flex flex-col h-full overflow-auto">
	{#if loading}
		<p class="text-sm text-gray-500">Loading document…</p>
	{:else if error}
		<p class="text-sm text-red-600" role="alert">{error}</p>
	{:else if !document}
		<p class="text-sm text-gray-500">Select a document from the tree to read it.</p>
	{:else}
		<article class="prose max-w-none">
			<header class="mb-4 border-b pb-2">
				<h1 class="text-2xl font-bold">{document.title}</h1>
				<p class="text-xs text-gray-500 font-mono mt-1">
					SHA: {document.sha}
				</p>
			</header>

			<section class="whitespace-pre-wrap text-sm leading-relaxed">
				{document.body}
			</section>

			{#if document.attachments.length > 0}
				<footer class="mt-6 pt-4 border-t">
					<h3 class="text-sm font-semibold mb-2">Attachments</h3>
					<ul class="space-y-1">
						{#each document.attachments as attachment (attachment.path)}
							<li class="text-sm">
								<a
									href={attachment.path}
									class="text-blue-600 hover:underline"
									target="_blank"
									rel="noopener noreferrer"
								>
									{attachment.name}
								</a>
								{#if attachment.sha}
									<span class="text-xs text-gray-400 font-mono ml-2">
										{attachment.sha.slice(0, 8)}
									</span>
								{/if}
							</li>
						{/each}
					</ul>
				</footer>
			{/if}
		</article>
	{/if}
</div>

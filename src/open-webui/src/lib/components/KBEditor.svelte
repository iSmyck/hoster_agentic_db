<script lang="ts">
	interface Props {
		content?: string;
		onChange?: (content: string) => void;
	}

	let { content = '', onChange }: Props = $props();

	let raw = $state(content);
	let preview = $state(false);

	$effect(() => {
		raw = content;
	});

	function handleInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		raw = target.value;
		onChange?.(raw);
	}
</script>

<div class="kb-editor border rounded-lg bg-white shadow-sm flex flex-col h-full">
	<header class="border-b p-2 flex items-center justify-between">
		<span class="text-sm font-medium">Editor</span>
		<button
			class="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
			on:click={() => (preview = !preview)}
		>
			{preview ? 'Raw' : 'Preview'}
		</button>
	</header>

	{#if preview}
		<section class="p-4 prose max-w-none overflow-auto flex-1">
			<div class="whitespace-pre-wrap text-sm leading-relaxed">{raw}</div>
		</section>
	{:else}
		<textarea
			class="flex-1 p-4 font-mono text-sm resize-none focus:outline-none"
			value={raw}
			on:input={handleInput}
			placeholder="Write Markdown here…"
		></textarea>
	{/if}
</div>

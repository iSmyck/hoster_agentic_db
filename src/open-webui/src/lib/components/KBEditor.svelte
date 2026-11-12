<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { loadMarkdown, serializeMarkdown } from '$lib/kb/markdown-serializer.js';

	interface Props {
		content?: string;
		onChange?: (content: string) => void;
	}

	let { content = '', onChange }: Props = $props();

	let element: HTMLElement | undefined = $state();
	let editor = $state<Editor | undefined>();
	let preview = $state(false);
	let previewHtml = $state('');
	let isComposing = $state(false);
	let frontMatter = $state('');

	function renderMarkdown(body: string): string {
		const html = marked.parse(body, { async: false }) as string;
		return DOMPurify.sanitize(html);
	}

	function updatePreview() {
		if (!editor) return;
		const body = serializeMarkdown(editor.getJSON() as Record<string, unknown>, frontMatter);
		previewHtml = renderMarkdown(body);
	}

	function setEditorContent(source: string) {
		if (!editor) return;
		const parsed = loadMarkdown(source);
		frontMatter = parsed.frontMatter;
		editor.commands.setContent(parsed.doc, false);
	}

	onMount(() => {
		const parsed = loadMarkdown(content);
		frontMatter = parsed.frontMatter;

		editor = new Editor({
			element,
			extensions: [StarterKit],
			content: parsed.doc,
			injectCSS: false,
			onUpdate: ({ editor: ed }) => {
				if (isComposing) return;
				const md = serializeMarkdown(ed.getJSON() as Record<string, unknown>, frontMatter);
				onChange?.(md);
			},
			editorProps: {
				attributes: {
					role: 'textbox',
					'aria-label': 'Knowledge base editor',
					'aria-multiline': 'true',
					class: 'flex-1 p-4 font-mono text-sm focus:outline-none min-h-[200px]'
				},
				handleDOMEvents: {
					compositionstart: () => {
						isComposing = true;
						return false;
					},
					compositionend: () => {
						isComposing = false;
						if (editor) {
							const md = serializeMarkdown(
								editor.getJSON() as Record<string, unknown>,
								frontMatter
							);
							onChange?.(md);
						}
						return false;
					}
				}
			}
		});
	});

	onDestroy(() => {
		editor?.destroy();
	});

	$effect(() => {
		if (editor) {
			setEditorContent(content);
		}
	});

	function togglePreview() {
		preview = !preview;
		if (preview) updatePreview();
	}
</script>

<div class="kb-editor border rounded-lg bg-white shadow-sm flex flex-col h-full">
	<header class="border-b p-2 flex items-center justify-between">
		<span class="text-sm font-medium">Editor</span>
		<button
			type="button"
			class="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
			onclick={togglePreview}
		>
			{preview ? 'Raw' : 'Preview'}
		</button>
	</header>

	{#if preview}
		<section class="p-4 prose max-w-none overflow-auto flex-1" data-testid="kb-preview">
			<div class="text-sm leading-relaxed">{@html previewHtml}</div>
		</section>
	{:else}
		<div bind:this={element} class="flex-1 overflow-auto" data-testid="kb-editor"></div>
	{/if}
</div>

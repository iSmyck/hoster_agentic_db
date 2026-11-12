// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import KBEditor from '$lib/components/KBEditor.svelte';
import { loadMarkdown, serializeMarkdown } from '$lib/kb/markdown-serializer.js';

describe('markdown-serializer', () => {
	it('round-trips Markdown with front matter, lists, links and code', () => {
		const input = `---\ntitle: Test\n---\n# Heading\n\nParagraph with **bold**, *italic*, and \`code\`.\n\n* Item one\n* Item two\n\n1. First ordered\n2. Second ordered\n\n[Link text](https://example.com)\n\n\`\`\`python\ndef hello():\n    return "world"\n\`\`\`\n`;
		const { frontMatter, doc } = loadMarkdown(input);
		const output = serializeMarkdown(doc, frontMatter);
		expect(output).toBe(input);
	});

	it('round-trips Russian Markdown content', () => {
		const input = '# Привет мир\n\nЭто **жирный** и *курсивный* текст на русском.\n';
		const { frontMatter, doc } = loadMarkdown(input);
		const output = serializeMarkdown(doc, frontMatter);
		expect(output).toBe(input);
	});

	it('preserves front matter without a body', () => {
		const input = '---\ntitle: Empty\n---\n';
		const { frontMatter, doc } = loadMarkdown(input);
		const output = serializeMarkdown(doc, frontMatter);
		expect(output).toBe(input);
	});

	it('preserves body without front matter', () => {
		const input = 'Simple paragraph.\n';
		const { frontMatter, doc } = loadMarkdown(input);
		const output = serializeMarkdown(doc, frontMatter);
		expect(output).toBe(input);
	});
});

describe('KBEditor', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('renders with accessibility attributes', async () => {
		render(KBEditor, { props: { content: '# Hello' } });

		await waitFor(() => {
			const editor = screen.getByRole('textbox');
			expect(editor).toHaveAttribute('aria-label', 'Knowledge base editor');
			expect(editor).toHaveAttribute('aria-multiline', 'true');
		});
	});

	it('emits changes after IME composition end', async () => {
		const onChange = vi.fn();
		render(KBEditor, { props: { content: '', onChange } });

		const editor = await waitFor(() => screen.getByRole('textbox'));
		await fireEvent.compositionStart(editor);
		await fireEvent.compositionEnd(editor);

		await waitFor(() => {
			expect(onChange).toHaveBeenCalled();
		});
	});

	it('sanitizes preview HTML and removes script tags', async () => {
		render(KBEditor, { props: { content: '# Safe\n\n<script>alert(1)</script>' } });

		const button = await waitFor(() => screen.getByRole('button', { name: 'Preview' }));
		await fireEvent.click(button);

		await waitFor(() => {
			const preview = screen.getByTestId('kb-preview');
			expect(preview).toBeInTheDocument();
			expect(preview.querySelector('script')).not.toBeInTheDocument();
		});
	});

	it('fires composition events without crashing', async () => {
		const onChange = vi.fn();
		render(KBEditor, { props: { content: '', onChange } });

		const editor = await waitFor(() => screen.getByRole('textbox'));
		await fireEvent.compositionStart(editor);
		await fireEvent.compositionEnd(editor);

		expect(editor).toBeInTheDocument();
	});
});

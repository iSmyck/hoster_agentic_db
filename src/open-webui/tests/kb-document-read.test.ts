// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import KBDocumentRead from '$lib/components/KBDocumentRead.svelte';
import type { KBDocumentReadView } from '$lib/api/kb.js';

const document: KBDocumentReadView = {
	title: 'README.md',
	body: '# Hello KB',
	sha: 'c38885a1a737da4968f157092f304f3b5481d0bf',
	attachments: [
		{ name: 'diagram.png', path: './assets/diagram.png', sha: 'aabbccdd11223344' }
	]
};

describe('KBDocumentRead', () => {
	it('prompts to select a document when none is provided', () => {
		render(KBDocumentRead, { props: {} });
		expect(screen.getByText('Select a document from the tree to read it.')).toBeInTheDocument();
	});

	it('shows loading state', () => {
		render(KBDocumentRead, { props: { loading: true } });
		expect(screen.getByText('Loading document…')).toBeInTheDocument();
	});

	it('shows error state', () => {
		render(KBDocumentRead, { props: { error: 'Read failed' } });
		expect(screen.getByRole('alert')).toHaveTextContent('Read failed');
	});

	it('renders document title, body and sha', () => {
		render(KBDocumentRead, { props: { document } });

		expect(screen.getByRole('heading', { name: 'README.md' })).toBeInTheDocument();
		expect(screen.getByText('# Hello KB')).toBeInTheDocument();
		expect(screen.getByText(/SHA:/)).toBeInTheDocument();
	});

	it('renders attachment links', () => {
		render(KBDocumentRead, { props: { document } });

		const link = screen.getByRole('link', { name: 'diagram.png' }) as HTMLAnchorElement;
		expect(link).toBeInTheDocument();
		expect(link.href).toContain('assets/diagram.png');
	});

	it('does not render attachments section when empty', () => {
		render(KBDocumentRead, { props: { document: { ...document, attachments: [] } } });

		expect(screen.queryByText('Attachments')).not.toBeInTheDocument();
	});
});

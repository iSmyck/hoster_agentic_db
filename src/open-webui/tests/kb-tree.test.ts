// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import KBTree from '$lib/components/KBTree.svelte';
import type { TreeEntry } from '$lib/api/kb.js';

const entries: TreeEntry[] = [
	{ path: 'README.md', type: 'blob', sha: 'aaa' },
	{ path: 'docs/', type: 'tree', sha: 'bbb' },
	{ path: 'docs/guide.md', type: 'blob', sha: 'ccc' }
];

describe('KBTree', () => {
	it('renders all entries', () => {
		render(KBTree, { props: { entries } });

		expect(screen.getByText('README.md')).toBeInTheDocument();
		expect(screen.getByText('docs/')).toBeInTheDocument();
		expect(screen.getByText('docs/guide.md')).toBeInTheDocument();
	});

	it('shows loading state', () => {
		render(KBTree, { props: { entries: [], loading: true } });
		expect(screen.getByText('Loading tree…')).toBeInTheDocument();
	});

	it('shows error state', () => {
		render(KBTree, { props: { entries: [], error: 'Tree failed' } });
		expect(screen.getByRole('alert')).toHaveTextContent('Tree failed');
	});

	it('shows empty state', () => {
		render(KBTree, { props: { entries: [] } });
		expect(screen.getByText('No documents found.')).toBeInTheDocument();
	});

	it('calls onSelect with the clicked entry', async () => {
		const onSelect = vi.fn();
		render(KBTree, { props: { entries, onSelect } });

		await fireEvent.click(screen.getByText('docs/guide.md'));

		expect(onSelect).toHaveBeenCalledTimes(1);
		expect(onSelect).toHaveBeenCalledWith(entries[2]);
	});

	it('marks the selected entry', () => {
		render(KBTree, { props: { entries, selectedPath: 'docs/' } });
		const selected = screen.getByText('docs/').closest('button');
		expect(selected).toHaveAttribute('aria-current', 'true');
	});
});

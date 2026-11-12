/**
 * Lossless Markdown parser/serializer for the corporate KB editor.
 *
 * Built on TipTap's ProseMirror schema and prosemirror-markdown's
 * serialization utilities. Avoids the marked/turndown round-trip.
 * Front matter is split on load and re-attached on export so it is
 * never interpreted as document content.
 */

import { getSchema } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import MarkdownIt from 'markdown-it';
import { MarkdownParser, MarkdownSerializer } from 'prosemirror-markdown';
import { Node as ProseMirrorNode } from 'prosemirror-model';

const extensions = [StarterKit];
const schema = getSchema(extensions);

function backticksFor(node: ProseMirrorNode | undefined, side: number): string {
	let len = 0;
	if (node && node.isText) {
		const ticks = /`+/g;
		let m: RegExpExecArray | null;
		while ((m = ticks.exec(node.textContent))) len = Math.max(len, m[0].length);
	}
	let result = len > 0 && side > 0 ? ' `' : '`';
	for (let i = 0; i < len; i++) result += '`';
	if (len > 0 && side < 0) result += ' ';
	return result;
}

const markdownSerializer = new MarkdownSerializer(
	{
		blockquote(state, node) {
			state.wrapBlock('> ', null, node, () => state.renderContent(node));
		},
		codeBlock(state, node) {
			const backticks = node.textContent.match(/`{3,}/gm);
			const fence = backticks ? backticks.sort().slice(-1)[0] + '`' : '```';
			state.write(fence + (node.attrs.language || '') + '\n');
			state.text(node.textContent, false);
			state.write('\n');
			state.write(fence);
			state.closeBlock(node);
		},
		heading(state, node) {
			state.write(state.repeat('#', node.attrs.level) + ' ');
			state.renderInline(node, false);
			state.closeBlock(node);
		},
		horizontalRule(state, node) {
			state.write(node.attrs.markup || '---');
			state.closeBlock(node);
		},
		bulletList(state, node) {
			state.renderList(node, '  ', () => '* ');
		},
		orderedList(state, node) {
			const start = node.attrs.start || 1;
			const maxW = String(start + node.childCount - 1).length;
			const space = state.repeat(' ', maxW + 2);
			state.renderList(node, space, (i) => {
				const nStr = String(start + i);
				return state.repeat(' ', maxW - nStr.length) + nStr + '. ';
			});
		},
		listItem(state, node) {
			state.renderContent(node);
		},
		paragraph(state, node) {
			state.renderInline(node);
			state.closeBlock(node);
		},
		hardBreak(state, node, parent, index) {
			for (let i = index + 1; i < parent.childCount; i++) {
				if (parent.child(i).type !== node.type) {
					state.write('\\\n');
					return;
				}
			}
		},
		text(state, node) {
			state.text(node.text, true);
		}
	},
	{
		italic: { open: '*', close: '*', mixable: true, expelEnclosingWhitespace: true },
		bold: { open: '**', close: '**', mixable: true, expelEnclosingWhitespace: true },
		code: {
			open(_state, _mark, parent, index) {
				return backticksFor(parent.child(index), -1);
			},
			close(_state, _mark, parent, index) {
				return backticksFor(parent.child(index - 1), 1);
			},
			escape: false
		},
		link: {
			open: '[',
			close(state, mark) {
				return (
					'](' +
					mark.attrs.href.replace(/[\\(\\)"]/g, '\\$&') +
					(mark.attrs.title ? ` "${mark.attrs.title.replace(/"/g, '\\"')}"` : '') +
					')'
				);
			},
			mixable: true
		}
	},
	{ hardBreakNodeName: 'hardBreak', strict: false, tightLists: true }
);

const markdownParser = new MarkdownParser(
	schema,
	new MarkdownIt('commonmark', { html: false }),
	{
		blockquote: { block: 'blockquote' },
		paragraph: { block: 'paragraph' },
		list_item: { block: 'listItem' },
		bullet_list: { block: 'bulletList' },
		ordered_list: {
			block: 'orderedList',
			getAttrs: (tok) => ({ start: +(tok.attrGet('start') || 1) })
		},
		heading: { block: 'heading', getAttrs: (tok) => ({ level: +tok.tag.slice(1) }) },
		code_block: { block: 'codeBlock', noCloseToken: true },
		fence: {
			block: 'codeBlock',
			getAttrs: (tok) => ({ language: tok.info || '' }),
			noCloseToken: true
		},
		hr: { node: 'horizontalRule' },
		hardbreak: { node: 'hardBreak' },
		em: { mark: 'italic' },
		strong: { mark: 'bold' },
		link: {
			mark: 'link',
			getAttrs: (tok) => ({
				href: tok.attrGet('href'),
				title: tok.attrGet('title') || null
			})
		},
		code_inline: { mark: 'code', noCloseToken: true }
	}
);

export interface MarkdownLoadResult {
	frontMatter: string;
	doc: Record<string, unknown>;
}

/**
 * Split YAML front matter from the Markdown body.
 * Only `---\n...\n---` at the very start of the document is treated as front matter.
 */
export function splitFrontMatter(markdown: string): { frontMatter: string; body: string } {
	const normalized = markdown.replace(/\r\n/g, '\n');
	if (!normalized.startsWith('---\n')) {
		return { frontMatter: '', body: normalized };
	}
	const end = normalized.indexOf('\n---', 4);
	if (end === -1) {
		return { frontMatter: '', body: normalized };
	}
	const frontMatter = normalized.slice(0, end + 4);
	const body = normalized.slice(end + 4).replace(/^\n/, '');
	return { frontMatter, body };
}

/**
 * Parse Markdown into a TipTap JSON document and an optional front matter string.
 */
export function loadMarkdown(markdown: string): MarkdownLoadResult {
	const { frontMatter, body } = splitFrontMatter(markdown);
	const docNode = markdownParser.parse(body || '\n');
	return { frontMatter, doc: docNode.toJSON() as Record<string, unknown> };
}

/**
 * Serialize a TipTap JSON document and optional front matter back to Markdown.
 */
export function serializeMarkdown(doc: Record<string, unknown>, frontMatter: string): string {
	const docNode = ProseMirrorNode.fromJSON(schema, doc);
	const body = markdownSerializer.serialize(docNode).trimEnd();
	if (!frontMatter) return body + '\n';
	if (!body) return frontMatter + '\n';
	return frontMatter + '\n' + body + '\n';
}

#!/usr/bin/env node
/**
 * Merge overlay source files into the upstream Open WebUI checkout so that
 * upstream tooling (svelte-check, vite build) sees the KB seams.
 *
 * Rules:
 *   - src/lib/*      -> copied to upstream/src/lib/*
 *   - src/lib/routes -> copied to upstream/src/routes (SvelteKit route tree)
 *
 * The script is idempotent: it overwrites files from the overlay, removes
 * overlay-managed files that no longer exist, and keeps routes out of
 * upstream/src/lib/routes.
 */

import { cp, mkdir, readdir, rm, stat, unlink } from 'node:fs/promises';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const upstream = join(root, 'upstream');

async function exists(p) {
	try {
		await stat(p);
		return true;
	} catch {
		return false;
	}
}

async function* walk(dir) {
	const entries = await readdir(dir, { withFileTypes: true });
	for (const entry of entries) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) {
			yield* walk(path);
		} else {
			yield path;
		}
	}
}

async function copyDir(source, target) {
	await mkdir(target, { recursive: true });
	await cp(source, target, { recursive: true, force: true, preserveTimestamps: true });
}

/**
 * Remove files from `target` whose relative paths are not present in `source`.
 * Only walks files that exist under target; directories are left empty.
 */
async function cleanStaleFiles(source, target) {
	if (!(await exists(target))) return;
	const sourceFiles = new Set();
	for await (const file of walk(source)) {
		sourceFiles.add(relative(source, file));
	}
	for await (const file of walk(target)) {
		const rel = relative(target, file);
		if (!sourceFiles.has(rel)) {
			await unlink(file);
		}
	}
}

async function main() {
	try {
		await stat(upstream);
	} catch {
		console.error(
			`[merge-overlay] upstream/ directory not found. Run ./setup-openwebui.sh first.`,
		);
		process.exit(1);
	}

	const overlayLib = join(root, 'src', 'lib');
	const upstreamLib = join(upstream, 'src', 'lib');
	const overlayRoutes = join(overlayLib, 'routes');
	const upstreamRoutes = join(upstream, 'src', 'routes');
	const upstreamLibRoutes = join(upstreamLib, 'routes');

	// Clean stale overlay files before copying, then sync lib contents.
	await cleanStaleFiles(overlayLib, upstreamLib);
	await copyDir(overlayLib, upstreamLib);

	// SvelteKit expects routes under src/routes, not src/lib/routes.
	// Remove any duplicate routes left under upstream/src/lib/routes and sync
	// the canonical route tree separately.
	if (await exists(upstreamLibRoutes)) {
		await rm(upstreamLibRoutes, { recursive: true, force: true });
	}
	if (await exists(overlayRoutes)) {
		await cleanStaleFiles(overlayRoutes, upstreamRoutes);
		await copyDir(overlayRoutes, upstreamRoutes);
	}

	console.log(
		`[merge-overlay] Overlay merged into ${relative(root, upstream)}. KB routes mapped to upstream/src/routes.`,
	);
}

main().catch((err) => {
	console.error('[merge-overlay] Failed:', err.message);
	process.exit(1);
});

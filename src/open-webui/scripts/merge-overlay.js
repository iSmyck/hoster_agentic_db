#!/usr/bin/env node
/**
 * Merge overlay source files into the upstream Open WebUI checkout so that
 * upstream tooling (svelte-check, vite build) sees the KB seams.
 *
 * Rules:
 *   - src/lib/*      -> copied to upstream/src/lib/*
 *   - src/lib/routes -> copied to upstream/src/routes (SvelteKit route tree)
 *
 * The script is idempotent: it copies overlay files on top of upstream and
 * records a manifest so previously-copied overlay files can be removed when
 * they no longer exist in the overlay.
 */

import { cp, mkdir, readdir, readFile, rm, stat, unlink, writeFile } from 'node:fs/promises';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const upstream = join(root, 'upstream');
const manifestPath = join(root, '.overlay-manifest.json');

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

async function copyFile(source, target) {
	await mkdir(dirname(target), { recursive: true });
	await cp(source, target, { force: true, preserveTimestamps: true });
}

async function readManifest() {
	try {
		return JSON.parse(await readFile(manifestPath, 'utf-8'));
	} catch {
		return [];
	}
}

async function writeManifest(files) {
	await writeFile(manifestPath, JSON.stringify(Array.from(files), null, 2));
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

	const copied = new Set();

	// Copy overlay lib files individually so upstream-only files are preserved.
	for await (const file of walk(overlayLib)) {
		const rel = relative(overlayLib, file);
		// Routes are handled separately below.
		if (rel.startsWith('routes' + sep)) continue;
		const target = join(upstreamLib, rel);
		await copyFile(file, target);
		copied.add(relative(upstream, target));
	}

	// SvelteKit expects routes under src/routes, not src/lib/routes.
	if (await exists(overlayRoutes)) {
		for await (const file of walk(overlayRoutes)) {
			const rel = relative(overlayRoutes, file);
			const target = join(upstreamRoutes, rel);
			await copyFile(file, target);
			copied.add(relative(upstream, target));
		}
	}

	// Remove previously-copied overlay files that no longer exist.
	const previous = await readManifest();
	const current = new Set(copied);
	for (const rel of previous) {
		if (!current.has(rel)) {
			try {
				await unlink(join(upstream, rel));
			} catch {
				// ignore if already gone
			}
		}
	}

	await writeManifest(copied);

	// Copy overlay root-level configuration files (e.g. vite.config.ts) on top
	// of upstream. These are intentionally few and replace upstream defaults.
	const root_files_to_sync = ["vite.config.ts"];
	for (const name of root_files_to_sync) {
		const source = join(root, name);
		const target = join(upstream, name);
		if (await exists(source)) {
			await copyFile(source, target);
			copied.add(relative(upstream, target));
		}
	}

	console.log(
		`[merge-overlay] Overlay merged into ${relative(root, upstream)}. KB routes mapped to upstream/src/routes.`,
	);
}

main().catch((err) => {
	console.error('[merge-overlay] Failed:', err.message);
	process.exit(1);
});

import { describe, it, expect } from 'vitest';
import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const scriptPath = join(import.meta.dirname, '..', 'scripts', 'merge-overlay.js');

describe('merge-overlay script', () => {
	it('has exactly one shebang', () => {
		const content = readFileSync(scriptPath, 'utf-8');
		const matches = content.match(/^#!.*$/gm) ?? [];
		expect(matches).toHaveLength(1);
	});

	it('passes node --check syntax validation', () => {
		expect(() => execSync(`node --check "${scriptPath}"`, { stdio: 'ignore' })).not.toThrow();
	});
});

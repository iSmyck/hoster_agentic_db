import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
	plugins: [svelte({ compilerOptions: { dev: true } })],
	test: {
		globals: true,
		environment: 'node',
		include: ['tests/**/*.test.ts'],
		exclude: ['upstream/**', 'node_modules/**'],
		setupFiles: ['./tests/setup.ts']
	},
	resolve: {
		alias: {
			$lib: new URL('./src/lib', import.meta.url).pathname
		},
		conditions: ['browser']
	}
});

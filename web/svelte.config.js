import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const dev = process.env.NODE_ENV !== 'production';
// When publishing to GitHub Pages at https://<user>.github.io/<repo>/, set
// BASE_PATH=/probably-not-probabilities at build time. Empty otherwise.
const base = dev ? '' : process.env.BASE_PATH ?? '';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: true
    }),
    paths: { base },
    prerender: { entries: ['*'] }
  }
};

export default config;

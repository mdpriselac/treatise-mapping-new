import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://treatise-mapping-project-new.outsidethevillage.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
  // Keep every script in its own file so the Content-Security-Policy needs no inline scripts.
  vite: { build: { assetsInlineLimit: 0 } },
});

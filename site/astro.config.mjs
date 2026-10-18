import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://treatise-mapping-project-new.outsidethevillage.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
});

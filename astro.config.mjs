// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  // Cloudflare Pages 静态部署：构建输出到 dist/，域名确定后替换 site 占位
  output: 'static',
  site: 'https://hsr-lore.pages.dev',
  integrations: [react()],
});

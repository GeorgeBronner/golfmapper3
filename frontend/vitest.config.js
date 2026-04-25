import { mergeConfig } from 'vite';
import { defineConfig } from 'vitest/config';
import path from 'path';
import viteConfig from './vite.config.js';

export default mergeConfig(viteConfig, defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.js'],
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
}));

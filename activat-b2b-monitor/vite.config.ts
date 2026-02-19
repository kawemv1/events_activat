import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      },
      build: {
        // Оптимизация билда для Vercel
        outDir: 'dist',
        assetsDir: 'assets',
        sourcemap: false, // Отключаем sourcemaps для продакшена (можно включить при необходимости)
        minify: 'esbuild', // Используем esbuild для быстрой минификации
        chunkSizeWarningLimit: 1000, // Предупреждение при размере чанка > 1MB
        rollupOptions: {
          output: {
            // Оптимизация разделения кода на чанки
            manualChunks: {
              'react-vendor': ['react', 'react-dom'],
              'lucide-vendor': ['lucide-react'],
            },
          },
        },
        // Увеличиваем лимит для больших файлов (изображения)
        assetsInlineLimit: 4096, // Файлы меньше 4KB будут инлайниться
      },
      // Убеждаемся, что папка public копируется правильно
      publicDir: 'public',
    };
});

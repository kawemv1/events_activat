import { mkdir, writeFile } from 'fs/promises';
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const parsedImagesDir = join(__dirname, '..', 'public', 'parsed_images');
const gitkeepFile = join(parsedImagesDir, '.gitkeep');

try {
  // Создаем папку, если её нет (recursive создаст все родительские папки)
  await mkdir(parsedImagesDir, { recursive: true });
  
  // Создаем .gitkeep файл, если его нет
  try {
    await writeFile(gitkeepFile, '', { flag: 'wx' });
    console.log('✓ Created parsed_images/.gitkeep');
  } catch (error) {
    if (error.code !== 'EEXIST') {
      throw error;
    }
    // Файл уже существует, это нормально
    console.log('✓ parsed_images directory exists');
  }
} catch (error) {
  console.error('Error ensuring parsed_images directory:', error);
  process.exit(1);
}

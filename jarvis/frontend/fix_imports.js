import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function replaceImports(dir) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      replaceImports(fullPath);
    } else if (fullPath.endsWith('.ts') || fullPath.endsWith('.tsx')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      if (content.includes('@/')) {
        const relativeToSrc = path.relative(path.dirname(fullPath), path.join(__dirname, 'src'));
        let replaceStr = relativeToSrc.replace(/\\/g, '/');
        if (replaceStr === '') { replaceStr = '.'; }
        if (!replaceStr.startsWith('.')) { replaceStr = './' + replaceStr; }
        
        content = content.replace(/@\//g, replaceStr + '/');
        fs.writeFileSync(fullPath, content);
        console.log(`Updated imports in ${fullPath}`);
      }
    }
  }
}

replaceImports(path.join(__dirname, 'src'));
console.log('Finished updating imports.');

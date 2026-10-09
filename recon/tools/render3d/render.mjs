// Rendus 3D de contrôle du paquet glTF (tuiles 1000x1000 px, aucune mise à l'échelle).
// Usage : node render.mjs <fichier.glb> <vues.json> <dossier_sortie>
//   vues.json : [{"nom": "...", "oeil": [x,y,z], "cible": [x,y,z], "fov": 60}, ...]  (repère local Z-up)
import { chromium } from 'playwright-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [glb, viewsFile, outDir] = process.argv.slice(2);
const views = JSON.parse(fs.readFileSync(viewsFile, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.glb': 'model/gltf-binary' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const f = u === '/model.glb' ? path.resolve(glb) : path.join(HERE, u);
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(0, '127.0.0.1');
await new Promise((r) => server.once('listening', r));
const port = server.address().port;
const exe = process.env.CHROMIUM || '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const browser = await chromium.launch({ executablePath: exe, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1000, height: 1000 } });
page.on('console', (m) => { if (m.type() === 'error') console.error('page:', m.text()); });
await page.goto(`http://127.0.0.1:${port}/page.html`);
await page.waitForFunction('window.ready === true');
const info = await page.evaluate(async () => await window.loadModel('/model.glb'));
console.log('modèle chargé', JSON.stringify(info));
for (const v of views) {
  const url = await page.evaluate(([e, t, f]) => window.renderView(e, t, f), [v.oeil, v.cible, v.fov || 60]);
  const out = path.join(outDir, `${v.nom}.png`);
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  console.log(out);
}
await browser.close();
server.close();

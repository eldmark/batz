import test from 'node:test';
import assert from 'node:assert/strict';
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join} from 'node:path';

const WEB = new URL('../../../src/logos/web/', import.meta.url).pathname;
const files = dir => readdirSync(dir).flatMap(name => {
  const path = join(dir, name);
  return statSync(path).isDirectory() ? (name === 'vendor' || name === 'fonts' ? [] : files(path)) : path.endsWith('.css') ? [path] : [];
});

// Una llave sin cerrar en una hoja deja el resto de ella dentro de un @media (ya ocurrió con thread.css).
test('todas las hojas de estilo tienen las llaves balanceadas', () => {
  for (const file of files(WEB)) {
    const text = readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    let depth = 0;
    for (const ch of text) { if (ch === '{') depth++; if (ch === '}') depth--; assert.ok(depth >= 0, `${file}: llave de cierre de más`); }
    assert.equal(depth, 0, `${file}: ${depth} llave(s) sin cerrar`);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {PEOPLE, PEOPLE_ORDER, person} from '../../../src/logos/web/features/people/people.js';

const web = (p) => fileURLToPath(new URL('../../../src/logos/web' + p, import.meta.url));
const withImage = PEOPLE_ORDER.filter((s) => PEOPLE[s].image);
const without = PEOPLE_ORDER.filter((s) => !PEOPLE[s].image);

test('el orden cubre a todas las personas, sin repetir', () => {
  assert.equal(new Set(PEOPLE_ORDER).size, PEOPLE_ORDER.length);
  assert.deepEqual([...PEOPLE_ORDER].sort(), Object.keys(PEOPLE).sort());
  assert.equal(person('nadie'), null);
  assert.equal(person('godel').name, 'Kurt Gödel');
});
test('cada persona con imagen tiene su JPEG en disco y pesa 150 kB o menos', () => {
  assert.ok(withImage.length > 0);
  for (const s of withImage) {
    assert.match(PEOPLE[s].image, /^\/img\/people\/[a-z]+\.jpg$/, s);
    const file = web(PEOPLE[s].image);
    assert.ok(fs.existsSync(file), `falta ${file}`);
    const bytes = fs.readFileSync(file);
    assert.ok(bytes.length <= 150_000, `${s}: ${bytes.length} B`);
    assert.deepEqual([...bytes.subarray(0, 2)], [0xff, 0xd8], `${s} no es JPEG`);
  }
});
test('quien no tiene imagen la declara null y no deja un archivo huérfano', () => {
  for (const s of without) {
    assert.equal(PEOPLE[s].image, null, s);
    assert.ok(!fs.existsSync(web(`/img/people/${s}.jpg`)), `${s} tiene archivo pero image es null`);
  }
});
test('las que tienen imagen traen crédito, enlace y licencia no vacíos', () => {
  for (const s of withImage) {
    const unverified = PEOPLE[s].license === 'Sin verificar';   // foto aportada sin URL de origen
    for (const k of ['credit', 'creditUrl', 'license']) {
      assert.equal(typeof PEOPLE[s][k], 'string', `${s}.${k}`);
      if (k !== 'creditUrl' || !unverified) assert.ok(PEOPLE[s][k].trim().length > 0, `${s}.${k} vacío`);
    }
    if (PEOPLE[s].license !== 'Sin verificar') assert.match(PEOPLE[s].creditUrl, /^https:\/\/commons\.wikimedia\.org\//, s);
  }
});
test('cada persona tiene nombre y años coherentes (o null)', () => {
  for (const s of PEOPLE_ORDER) {
    const p = PEOPLE[s];
    assert.ok(p.name.trim(), s);
    for (const y of [p.born, p.died]) assert.ok(y === null || Number.isInteger(y), s);
    if (p.born !== null && p.died !== null) assert.ok(p.born < p.died, s);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {HISTORY, HISTORY_TOPICS, CARDS, CARD_TOPICS} from '../../../src/logos/web/features/learn/data.js';
import {shuffle, filterCards, emptyProgress, sanitizeProgress, loadProgress, saveProgress, clearProgress, mark, statusOf, summary, buildQueue, step, STORAGE_KEY} from '../../../src/logos/web/features/learn/deck.js';

const seeded = seed => () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;
const memory = () => { const m = new Map(); return {getItem: k => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k)}; };

test('datos: al menos 24 tarjetas, ids únicos, temas válidos y campos completos', () => {
  assert.ok(CARDS.length >= 24);
  assert.equal(new Set(CARDS.map(c => c.id)).size, CARDS.length);
  const topics = new Set(CARD_TOPICS.map(t => t.id));
  for (const c of CARDS) { assert.ok(topics.has(c.topic), c.id); for (const k of ['front', 'back', 'example']) assert.ok(c[k]?.length > 5, `${c.id}.${k}`); }
  for (const t of CARD_TOPICS) assert.ok(CARDS.some(c => c.topic === t.id), t.id);
});
test('datos: historia en orden cronológico aproximado, con campos y enlaces internos válidos', () => {
  assert.equal(new Set(HISTORY.map(h => h.id)).size, HISTORY.length);
  const topics = new Set(HISTORY_TOPICS.map(t => t.id));
  for (const h of HISTORY) {
    for (const k of ['year', 'people', 'title', 'what', 'where']) assert.ok(h[k]?.length > 3, `${h.id}.${k}`);
    assert.ok(topics.has(h.topic));
    if (h.href) assert.match(h.href, /^#\/(evaluar|demostrar|practicar|cuadernos|diccionario|inicio)$/);
    if (h.href) assert.ok(h.link);
  }
  for (const needle of ['1879', '1931', '1936', '1965', '1952']) assert.ok(HISTORY.some(h => h.year.includes(needle)), needle);
});
test('shuffle: conserva los elementos, no muta y es reproducible con la misma semilla', () => {
  const src = [1, 2, 3, 4, 5, 6, 7, 8]; const copy = [...src];
  const a = shuffle(src, seeded(7)), b = shuffle(src, seeded(7));
  assert.deepEqual(src, copy);
  assert.deepEqual(a, b);
  assert.deepEqual([...a].sort(), copy);
  assert.notDeepEqual(a, copy);
  assert.deepEqual(shuffle([], seeded(1)), []);
  assert.deepEqual(shuffle([1], () => 0.99), [1]);
});
test('filterCards: por tema y «todos»', () => {
  assert.equal(filterCards(CARDS, 'todos').length, CARDS.length);
  const err = filterCards(CARDS, 'errores');
  assert.ok(err.length >= 4 && err.every(c => c.topic === 'errores'));
  assert.equal(filterCards(CARDS, 'no-existe').length, 0);
});
test('mark / statusOf / summary: un id solo está en un estado a la vez', () => {
  let p = emptyProgress();
  p = mark(p, 'termino', 'known'); assert.equal(statusOf(p, 'termino'), 'known');
  p = mark(p, 'termino', 'review'); assert.equal(statusOf(p, 'termino'), 'review'); assert.deepEqual(p.known, []);
  p = mark(p, 'atomo', 'known');
  assert.deepEqual(summary(CARDS, p), {total: CARDS.length, known: 1, review: 1, pending: CARDS.length - 2});
  p = mark(p, 'termino', 'pending'); assert.equal(statusOf(p, 'termino'), 'pending');
  const before = emptyProgress(); mark(before, 'x', 'known'); assert.deepEqual(before, emptyProgress());
});
test('buildQueue: omite las sabidas y respeta el tema', () => {
  let p = mark(emptyProgress(), 'termino', 'known');
  const q = buildQueue(CARDS, p, {topic: 'lenguaje', rng: seeded(3)});
  assert.ok(q.every(c => c.topic === 'lenguaje' && c.id !== 'termino'));
  assert.equal(q.length, filterCards(CARDS, 'lenguaje').length - 1);
  assert.equal(buildQueue(CARDS, p, {topic: 'lenguaje', onlyOpen: false}).length, filterCards(CARDS, 'lenguaje').length);
});
test('step: vuelta circular en ambos sentidos y lista vacía', () => {
  assert.equal(step(0, 5, -1), 4); assert.equal(step(4, 5, 1), 0); assert.equal(step(2, 5, 1), 3); assert.equal(step(0, 0, 1), 0);
});
test('progreso: se guarda, se recarga y se reinicia', () => {
  const st = memory();
  const p = mark(mark(emptyProgress(), 'termino', 'known'), 'atomo', 'review');
  assert.equal(saveProgress(st, p), true);
  assert.ok(st.getItem(STORAGE_KEY));
  assert.deepEqual(loadProgress(st, CARDS), p);
  assert.equal(clearProgress(st), true);
  assert.deepEqual(loadProgress(st, CARDS), emptyProgress());
});
test('progreso: tolera almacenamiento ausente, que falla o con datos corruptos', () => {
  const boom = {getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); }, removeItem() { throw new Error('x'); }};
  assert.deepEqual(loadProgress(boom, CARDS), emptyProgress());
  assert.deepEqual(loadProgress(null, CARDS), emptyProgress());
  assert.equal(saveProgress(boom, emptyProgress()), false);
  assert.equal(clearProgress(boom), false);
  const bad = memory(); bad.setItem(STORAGE_KEY, '{no es json');
  assert.deepEqual(loadProgress(bad, CARDS), emptyProgress());
});
test('sanitizeProgress: descarta ids ajenos, duplicados y solapes', () => {
  const p = sanitizeProgress({known: ['termino', 'termino', 'zzz', 7], review: ['termino', 'atomo'], extra: 1}, CARDS);
  assert.deepEqual(p, {known: ['termino'], review: ['atomo']});
  assert.deepEqual(sanitizeProgress('x', CARDS), emptyProgress());
  assert.deepEqual(sanitizeProgress({known: 'termino'}, CARDS), emptyProgress());
});

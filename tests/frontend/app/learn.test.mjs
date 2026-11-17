import test from 'node:test';
import assert from 'node:assert/strict';
import {HISTORY, HISTORY_TOPICS, CARDS, CARD_TOPICS} from '../../../src/logos/web/features/learn/data.js';
import {PEOPLE, person, initials} from '../../../src/logos/web/features/people/people.js';
import {visibleMilestones, clampIndex, stepIndex, neighbors, isFirst, isLast, indexAfterFilter, nearestIndex, swipeDelta, trackYear, peopleOf, unknownSlugs, needsVisibleCredit, announce} from '../../../src/logos/web/features/learn/timeline.js';
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

// ───────── Línea del tiempo ─────────
test('historia: 18 hitos en orden cronológico por año de inicio', () => {
  assert.equal(HISTORY.length, 18);
  const start = h => { const m = /\d{3,4}/.exec(h.year); return m ? +m[0] : h.year.includes('a. C.') ? -400 : 1650; };
  const ys = HISTORY.map(start);
  assert.deepEqual([...ys].sort((a, b) => a - b), ys);
});
test('mapeo hito→personas: slugs válidos contra people.js, sin repetir y con el nombre en el texto', () => {
  assert.deepEqual(unknownSlugs(HISTORY, person), []);
  for (const h of HISTORY) {
    assert.ok(h.slugs.length >= 1, h.id);
    assert.equal(new Set(h.slugs).size, h.slugs.length);
    for (const slug of h.slugs) { const last = PEOPLE[slug].name.split(' ').pop(); assert.ok(h.people.includes(last), `${h.id}: ${last} en «${h.people}»`); }
  }
  const by = id => HISTORY.find(h => h.id === id).slugs;
  assert.deepEqual(by('principia').sort(), ['russell', 'whitehead']);
  assert.deepEqual(by('godel-completitud'), ['godel']);
  assert.deepEqual(by('church-turing'), ['church', 'turing']);
  assert.equal(peopleOf(HISTORY[0], person)[0].name, 'Aristóteles');
  assert.deepEqual(peopleOf({slugs: ['nadie', 'godel']}, person).map(p => p.slug), ['godel']);
  assert.deepEqual(peopleOf({}, person), []);
});
test('retratos: el archivo existe; sin foto hay iniciales; CC exige crédito visible con enlace', async () => {
  const {existsSync} = await import('node:fs');
  const used = new Set(HISTORY.flatMap(h => h.slugs));
  for (const slug of used) {
    const p = PEOPLE[slug];
    if (p.image) assert.ok(existsSync(new URL('../../../src/logos/web' + p.image, import.meta.url)), slug); else assert.ok(initials(slug).length >= 2, slug);
    if (needsVisibleCredit(p)) { assert.ok(p.credit && /^https:\/\//.test(p.creditUrl), slug); }
  }
  assert.deepEqual([...used].filter(s => needsVisibleCredit(PEOPLE[s])).sort(), ['gentzen', 'lowenheim', 'robinson', 'tarski']);
  assert.deepEqual([...used].filter(s => !PEOPLE[s].image).sort(), ['fitch', 'jaskowski']);
});
test('vecinos antes/después y límites en el primero y el último', () => {
  const list = visibleMilestones(HISTORY, 'todos');
  assert.deepEqual(neighbors(list, 0), {prev: null, next: list[1]});
  assert.deepEqual(neighbors(list, 5), {prev: list[4], next: list[6]});
  assert.deepEqual(neighbors(list, 17), {prev: list[16], next: null});
  assert.deepEqual(neighbors([], 0), {prev: null, next: null});
  assert.deepEqual(neighbors([list[0]], 0), {prev: null, next: null});
  assert.ok(isFirst(0) && !isFirst(1) && isLast(17, 18) && !isLast(16, 18) && !isLast(0, 0));
});
test('stepIndex / clampIndex: sin dar la vuelta', () => {
  assert.equal(stepIndex(0, 18, -1), 0); assert.equal(stepIndex(17, 18, 1), 17); assert.equal(stepIndex(3, 18, 1), 4);
  assert.equal(clampIndex(99, 5), 4); assert.equal(clampIndex(-3, 5), 0); assert.equal(clampIndex(NaN, 5), 0); assert.equal(clampIndex(2, 0), 0);
});
test('filtro por tema: solo recorre los hitos del tema y conserva el actual si sigue visible', () => {
  assert.equal(visibleMilestones(HISTORY, 'todos').length, 18);
  for (const t of HISTORY_TOPICS) { const l = visibleMilestones(HISTORY, t.id); assert.ok(l.length >= 1 && l.every(h => h.topic === t.id), t.id); }
  assert.equal(visibleMilestones(HISTORY, 'no-existe').length, 0);
  const lim = visibleMilestones(HISTORY, 'limites');
  assert.equal(indexAfterFilter(lim, 'godel-incompletitud'), lim.findIndex(h => h.id === 'godel-incompletitud'));
  assert.equal(indexAfterFilter(lim, 'boole'), 0);
  assert.equal(neighbors(lim, 0).prev, null);
  assert.equal(neighbors(lim, lim.length - 1).next, null);
});
test('arrastre, deslizamiento y etiquetas del hilo', () => {
  assert.equal(nearestIndex([10, 60, 110], 70), 1); assert.equal(nearestIndex([10, 60, 110], -50), 0); assert.equal(nearestIndex([10, 60, 110], 999), 2);
  assert.equal(swipeDelta(-80, 5), 1); assert.equal(swipeDelta(80, 5), -1); assert.equal(swipeDelta(20, 0), 0); assert.equal(swipeDelta(-80, 70), 0);
  assert.equal(trackYear('1847 y 1854'), '1847'); assert.equal(trackYear('década de 1880'), '1880s'); assert.equal(trackYear('s. IV a. C.'), 'IV a. C.');
  assert.equal(trackYear('s. XVII'), 'XVII'); assert.equal(trackYear('1901–1902'), '1901');
  assert.equal(announce(HISTORY[3], 3, 18), 'Hito 4 de 18: 1879, «Begriffsschrift»: cuantificadores y predicados.');
});

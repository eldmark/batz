import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {STEPS, TUTORIAL_EXERCISE, START_RULE} from '../../../src/batz/web/features/practice-tutorial/steps.js';
import {TUTORIAL_KEY, BACKUP_KEY, readTutorialState, writeTutorialState, shouldOfferTutorial, parseRefs, evaluate,
  earlierProblem, takeSnapshot, cleanRecord, finalRecord, saveBackup, readBackup, clearBackup, checkFailure}
  from '../../../src/batz/web/features/practice-tutorial/tutorial.js';

const memory = () => { const m = new Map(); return {getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k)}; };
const broken = {getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); }, removeItem() { throw new Error('x'); }};

test('la secuencia son seis pasos sobre el ejercicio 01 y todos tienen texto y objetivo', () => {
  assert.equal(TUTORIAL_EXERCISE, '01');
  assert.deepEqual(STEPS.map(s => s.id), ['objetivo', 'regla', 'citar', 'formula', 'comprobar', 'cierre']);
  for (const s of STEPS) { assert.ok(s.title && s.text && s.targets.length, s.id); }
  assert.equal(STEPS.filter(s => s.how).length, 4);   // los cuatro pasos con acción tienen «Mostrar cómo»
});
test('estado recordado: completado/omitido, valores ajenos y almacenamiento roto', () => {
  const s = memory();
  assert.equal(readTutorialState(s), null); assert.equal(shouldOfferTutorial(null), true);
  assert.equal(writeTutorialState(s, 'omitido'), true);
  assert.equal(readTutorialState(s), 'omitido'); assert.equal(shouldOfferTutorial('omitido'), false); assert.equal(shouldOfferTutorial('completado'), false);
  assert.equal(writeTutorialState(s, 'otro'), false);
  s.setItem(TUTORIAL_KEY, 'basura'); assert.equal(readTutorialState(s), null); assert.equal(shouldOfferTutorial(readTutorialState(s)), true);
  assert.equal(readTutorialState(broken), null); assert.equal(writeTutorialState(broken, 'omitido'), false);
  assert.equal(readTutorialState(null), null); assert.equal(writeTutorialState(null, 'omitido'), false);
});
test('parseRefs', () => {
  assert.deepEqual(parseRefs(''), []); assert.deepEqual(parseRefs(' 1 '), [1]); assert.deepEqual(parseRefs('1, 2'), [1, 2]);
  assert.equal(parseRefs('uno'), null); assert.equal(parseRefs('1,'), null);
});
test('regla: solo ∧E₁ cuenta; ∧E₂ y otras dan un mensaje útil', () => {
  assert.equal(evaluate('regla', {rule: 'and_e1'}).done, true);
  const e2 = evaluate('regla', {rule: 'and_e2'}); assert.equal(e2.done, false); assert.match(e2.problem, /∧E₂.*Q.*P/);
  const other = evaluate('regla', {rule: 'imp_e'}); assert.equal(other.done, false); assert.match(other.problem, /→E.*∧E₁/);
  assert.equal(evaluate('regla', {rule: 'zzz'}).done, false);
});
test('citar: solo la línea 1', () => {
  assert.equal(evaluate('citar', {refs: '1'}).done, true);
  assert.equal(evaluate('citar', {refs: ' 1 '}).done, true);
  assert.deepEqual(evaluate('citar', {refs: ''}), {done: false, problem: null});
  assert.match(evaluate('citar', {refs: '2'}).problem, /solo existe la línea 1/);
  assert.match(evaluate('citar', {refs: '1, 1'}).problem, /únicamente la línea 1/);
  assert.match(evaluate('citar', {refs: 'x'}).problem, /número de línea/);
  assert.equal(evaluate('citar', {refs: '12'}).done, false);
});
test('fórmula: P (con o sin espacios); Q y otras dan mensaje', () => {
  assert.equal(evaluate('formula', {formula: 'P'}).done, true);
  assert.equal(evaluate('formula', {formula: ' P \n'}).done, true);
  assert.deepEqual(evaluate('formula', {formula: ''}), {done: false, problem: null});
  assert.match(evaluate('formula', {formula: 'Q'}).problem, /derecha.*P/);
  assert.match(evaluate('formula', {formula: 'P ∧ Q'}).problem, /solo P/);
  assert.equal(evaluate('formula', {formula: 'p'}).done, false);
});
test('comprobar y cierre dependen de que el ejercicio esté completo; el primero de que se haya leído', () => {
  assert.equal(evaluate('comprobar', {complete: false}).done, false);
  assert.equal(evaluate('comprobar', {complete: true}).done, true);
  assert.equal(evaluate('objetivo', {}).done, false);
  assert.equal(evaluate('objetivo', {acknowledged: true}).done, true);
});
test('un cambio posterior en un campo anterior se detecta (earlierProblem)', () => {
  const ok = {rule: 'and_e1', refs: '1', formula: 'P'};
  assert.equal(earlierProblem(4, ok), null);
  assert.match(earlierProblem(4, {...ok, rule: 'and_e2'}), /∧E₂/);
  assert.match(earlierProblem(4, {...ok, refs: '2'}), /línea 1/);
  assert.match(earlierProblem(4, {...ok, refs: ''}), /Falta completar/);
  assert.equal(earlierProblem(1, {}), null);
});
test('mensaje de fallo del servidor', () => {
  assert.match(checkFailure('La regla necesita 1 referencia'), /no aceptó.*necesita 1/);
  assert.match(checkFailure(''), /no aceptó el paso\./);
});
test('registro limpio: sin jugadas, otra regla elegida, conserva revisión y archivo previo', () => {
  const snap = {moves: [{formula: 'P', rule: 'and_e1', refs: [1], params: {}}], complete: true, hints: 2, revision: 'abc', previous: [{moves: []}], editor: {formula: 'x'}};
  const c = cleanRecord(snap);
  assert.deepEqual(c, {moves: [], complete: false, hints: 0, editor: {rule: START_RULE}, revision: 'abc', previous: [{moves: []}]});
  assert.notEqual(c.previous, snap.previous);
  assert.deepEqual(cleanRecord(null), {moves: [], complete: false, hints: 0, editor: {rule: START_RULE}});
});
test('restauración: completado antes -> se restaura el original exacto (copia)', () => {
  const progress = {'01': {moves: [{formula: 'Q', rule: 'and_e2', refs: [1], params: {}}], complete: true, hints: 1, revision: 'r'}};
  const snap = takeSnapshot(progress, '01');
  progress['01'] = {moves: [{formula: 'P', rule: 'and_e1', refs: [1], params: {}}], complete: true, hints: 0};
  const back = finalRecord(snap, progress['01']);
  assert.deepEqual(back, snap); assert.notEqual(back, snap);
  assert.equal(back.moves[0].formula, 'Q');
});
test('restauración: no completado antes y el tutorial lo completó -> se conserva el avance real', () => {
  const snap = takeSnapshot({'01': {moves: [], complete: false, hints: 1}}, '01');
  const now = {moves: [{formula: 'P', rule: 'and_e1', refs: [1], params: {}}], complete: true, hints: 0};
  assert.deepEqual(finalRecord(snap, now), now);
});
test('restauración: no completado antes ni ahora (omitido a medias) -> vuelve a su estado original', () => {
  const snap = takeSnapshot({'01': {moves: [], complete: false, hints: 2, editor: {formula: 'abc'}}}, '01');
  assert.deepEqual(finalRecord(snap, {moves: [], complete: false, hints: 0, editor: {rule: 'and_e2'}}), snap);
  assert.deepEqual(finalRecord(null, {moves: [], complete: false}), {moves: [], complete: false, hints: 0});
});
test('copia de seguridad: ida y vuelta, datos rotos y almacenamiento que falla', () => {
  const s = memory(); const snap = {moves: [], complete: true, hints: 0};
  assert.equal(readBackup(s), null);
  assert.equal(saveBackup(s, snap), true); assert.deepEqual(readBackup(s), {snapshot: snap});
  assert.equal(saveBackup(s, null), true); assert.deepEqual(readBackup(s), {snapshot: null});
  s.setItem(BACKUP_KEY, '{no json'); assert.equal(readBackup(s), null);
  s.setItem(BACKUP_KEY, '[1]'); assert.equal(readBackup(s), null);
  clearBackup(s); assert.equal(s.getItem(BACKUP_KEY), null);
  assert.equal(saveBackup(broken, snap), false); assert.equal(readBackup(broken), null); clearBackup(broken); assert.equal(readBackup(null), null);
});
test('rules-guide.json: 8 familias, 22 reglas sin repetir y un ejemplo para cada una', () => {
  const guide = JSON.parse(readFileSync(new URL('../../../src/batz/web/features/practice-tutorial/rules-guide.json', import.meta.url), 'utf8'));
  assert.equal(guide.families.length, 8);
  const all = guide.families.flatMap(f => f.rules);
  assert.equal(all.length, 22); assert.equal(new Set(all).size, 22);
  assert.deepEqual(Object.keys(guide.examples).sort(), [...all].sort());
  for (const [rule, e] of Object.entries(guide.examples)) {
    assert.equal(e.moves.at(-1).formula.length > 0, true, rule);
    assert.equal(e.moves[e.focus - e.premises.length - 1].rule, rule, rule);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {buildEvaluationHtml, buildProofHtml, modelHtml, fitchHtml} from '../../../src/logos/web/features/export/export.js';

const model = {domain: [0, 'Ana'], constants: {a: 0}, functions: {f: {table: [[[0], 'Ana'], [['Ana'], 0]]}}, predicates: {P: {tuples: [[0]]}}};

test('el modelo se exporta completo y escapado', () => {
  const html = modelHtml({...model, domain: ['<b>']});
  assert.match(html, /&lt;b&gt;/); assert.doesNotMatch(html, /<b>/);
  assert.match(modelHtml(model), /\(0\)/);
});
test('evaluación: veredicto, fórmula y entorno', () => {
  const html = buildEvaluationHtml({formula: '∀x P(x)', assignment: {y: 1}, value: false, model, explanation: {value: false, formula: '∀x P(x)', summary: 'falla en 1', children: []}});
  assert.match(html, /Falso/); assert.match(html, /∀x P\(x\)/); assert.match(html, /y = 1/); assert.doesNotMatch(html, /https?:\/\//);
});
test('prueba, contramodelo e inconclusa se rotulan distinto', () => {
  const fitch = [{n: 1, depth: 0, formula: 'P(a)', label: 'Premisa', refs: []}];
  assert.match(buildProofHtml({premises: ['P(a)'], conclusion: 'P(a)', result: {status: 'proved', fitch}}), /Prueba verificada/);
  assert.match(buildProofHtml({premises: [], conclusion: 'P(a)', result: {status: 'refuted', countermodel: {model}}}), /Contramodelo verificado/);
  const open = buildProofHtml({premises: [], conclusion: 'x', result: {status: 'unknown'}});
  assert.match(open, /Búsqueda inconclusa/); assert.match(open, /no significa falso/);
});
test('fitch con subpruebas muestra la profundidad', () => { assert.match(fitchHtml([{n: 2, depth: 2, formula: 'Q', label: 'Hip', refs: []}]), /│ │ Q/); });

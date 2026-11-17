import test from 'node:test';
import assert from 'node:assert/strict';
import {TOUR_KEY, STEPS, readTourState, writeTourState, shouldOfferTour} from '../../../src/logos/web/features/tour/tour.js';

const memory = () => { const m = new Map(); return {getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, v)}; };

test('sin estado previo se ofrece en Inicio y solo ahí', () => {
  for (const hash of ['', '#', '#/inicio', '#/inicio/']) assert.equal(shouldOfferTour({state: null, hash}), true, hash);
  for (const hash of ['#/evaluar', '#/demostrar', '#/cuadernos', '#/diccionario', '#/practicar']) assert.equal(shouldOfferTour({state: null, hash}), false, hash);
});
test('completado u omitido no se vuelve a ofrecer', () => {
  for (const state of ['completado', 'omitido']) assert.equal(shouldOfferTour({state, hash: '#/inicio'}), false);
});
test('el estado se recuerda y valores ajenos se ignoran', () => {
  const s = memory();
  assert.equal(readTourState(s), null);
  assert.equal(writeTourState(s, 'omitido'), true);
  assert.equal(readTourState(s), 'omitido');
  assert.equal(writeTourState(s, 'otro'), false);
  s.setItem(TOUR_KEY, 'basura');
  assert.equal(readTourState(s), null);
});
test('tolera que no haya almacenamiento o que lance', () => {
  const broken = {getItem() { throw new Error('denegado'); }, setItem() { throw new Error('denegado'); }};
  assert.equal(readTourState(broken), null);
  assert.equal(writeTourState(broken, 'omitido'), false);
  assert.equal(readTourState(null), null);
  assert.equal(writeTourState(null, 'omitido'), false);
});
test('presenta barra lateral, herramientas y ejemplo', () => {
  assert.deepEqual(STEPS.map(s => s.id), ['sidebar', 'tools', 'example']);
});

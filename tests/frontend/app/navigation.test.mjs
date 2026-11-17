import test from 'node:test';
import assert from 'node:assert/strict';
import {routeFromHash, hashFor, isKnownHash, ROUTES} from '../../../src/logos/web/app/navigation.js';

test('raíz, vacío y hash desconocido abren Inicio', () => {
  for (const hash of ['', '#', '#/', '#/nada', undefined]) assert.equal(routeFromHash(hash), 'home');
});
test('cada ruta es ida y vuelta', () => {
  for (const {id, hash} of ROUTES) { assert.equal(hashFor(id), hash); assert.equal(routeFromHash(hash), id); assert.ok(isKnownHash(hash)); }
});
test('barra final tolerada, hash desconocido no es conocido', () => {
  assert.equal(routeFromHash('#/evaluar/'), 'evaluate');
  assert.equal(isKnownHash('#/nada'), false);
});

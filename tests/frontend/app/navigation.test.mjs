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
test('Practicar tiene ruta y el enlace anterior #practicar sigue funcionando', () => {
  assert.equal(routeFromHash('#/practicar'), 'practice');
  assert.equal(routeFromHash('#practicar'), 'practice');
  assert.ok(isKnownHash('#practicar'));
});
test('Aprender tiene ruta #/aprender con id learn', () => {
  assert.equal(routeFromHash('#/aprender'), 'learn');
  assert.equal(hashFor('learn'), '#/aprender');
  assert.ok(isKnownHash('#/aprender/'));
});
test('páginas de personas: rutas #/godel, #/turing, #/church fuera de la barra lateral', async () => {
  const {personFor} = await import('../../../src/logos/web/app/navigation.js');
  for (const slug of ['godel', 'turing', 'church']) {
    assert.equal(routeFromHash(`#/${slug}`), slug);
    assert.equal(hashFor(slug), `#/${slug}`);
    assert.equal(personFor(slug), slug);
    assert.equal(ROUTES.find(r => r.id === slug).nav, false);
  }
  assert.equal(personFor('home'), null);
  assert.ok(ROUTES.filter(r => r.nav !== false).every(r => !r.person));
});

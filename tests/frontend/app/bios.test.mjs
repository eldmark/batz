import test from 'node:test';
import assert from 'node:assert/strict';
import {BIOS, BIO_SLUGS, bio} from '../../../src/logos/web/features/people/bios.js';
import {PEOPLE, person} from '../../../src/logos/web/features/people/people.js';
import {CONNECTIONS} from '../../../src/logos/web/features/home/home.js';
import {SLIDES, stepIndex, swipeDelta, keyIndex} from '../../../src/logos/web/features/home/carousel.js';

const nonEmpty = (v) => typeof v === 'string' && v.trim().length > 0;

test('cada persona con página tiene sus campos obligatorios y ninguno vacío', () => {
  assert.deepEqual(BIO_SLUGS, ['godel', 'turing', 'church']);
  for (const slug of BIO_SLUGS) {
    const b = bio(slug), p = person(slug);
    assert.ok(p, slug);
    assert.equal(b.route, `#/${slug}`);
    for (const k of ['birthplace', 'lede']) assert.ok(nonEmpty(b[k]), `${slug}.${k}`);
    assert.ok(b.bio.length >= 3 && b.bio.length <= 5 && b.bio.every(nonEmpty), `${slug}.bio`);
    assert.ok(b.contributions.length >= 3 && b.contributions.length <= 5, `${slug}.contributions`);
    assert.ok(b.timeline.length >= 3 && b.timeline.length <= 6, `${slug}.timeline`);
    for (const e of [...b.contributions, ...b.timeline]) assert.ok(nonEmpty(e.year) && nonEmpty(e.text), slug);
    assert.ok(b.reading.length >= 1 && b.reading.every(nonEmpty));
    assert.ok(b.batz.length >= 1 && b.batz.every(i => nonEmpty(i.text) && nonEmpty(i.label) && i.href.startsWith('#/')));
    assert.ok(nonEmpty(b.carousel.contribution) && nonEmpty(b.carousel.batz));
    assert.ok(b.related.every(r => BIOS[r] && r !== slug));
    assert.ok(CONNECTIONS.some(c => c.id === b.exercise.id), `${slug} ejercicio`);
    if (p.image) assert.ok(nonEmpty(b.alt) && nonEmpty(p.credit) && (p.license === 'Sin verificar' || p.creditUrl.startsWith('https://commons.wikimedia.org/')), `${slug} retrato`);
  }
});
test('Church: la foto es aportada por el usuario y se declara sin verificar', () => {
  assert.equal(PEOPLE.church.image, '/img/people/church.jpg');
  assert.equal(PEOPLE.church.license, 'Sin verificar');
  assert.match(person('church').credit, /sin verificar/i);
});
test('los años de la ficha coinciden con people.js', () => {
  for (const slug of BIO_SLUGS) {
    const {born, died} = person(slug), years = [born, died].map(String);
    const b = bio(slug);
    assert.ok(b.timeline[0].year === years[0], `${slug} nace`);
    assert.ok(b.timeline.at(-1).year === years[1], `${slug} muere`);
  }
});
test('carrusel: tres diapositivas, vuelta circular, teclas y gesto', () => {
  assert.deepEqual(SLIDES, BIO_SLUGS);
  assert.equal(stepIndex(2, 1, 3), 0); assert.equal(stepIndex(0, -1, 3), 2);
  assert.equal(keyIndex('ArrowRight', 2, 3), 0); assert.equal(keyIndex('ArrowLeft', 0, 3), 2);
  assert.equal(keyIndex('Home', 2, 3), 0); assert.equal(keyIndex('End', 0, 3), 2); assert.equal(keyIndex('a', 0, 3), null);
  assert.equal(swipeDelta(-80, 5), 1); assert.equal(swipeDelta(80, 5), -1);
  assert.equal(swipeDelta(20, 0), 0); assert.equal(swipeDelta(-80, 70), 0);
});

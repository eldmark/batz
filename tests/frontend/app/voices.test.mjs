import test from 'node:test';
import assert from 'node:assert/strict';
import {browserSpanishVoices, chooseVoice, wordTimings, readVoicePref, saveVoicePref} from '../../../src/logos/web/features/explanation-player/events.js';

const voice = (name, lang, local = true) => ({name, lang, voiceURI: name, localService: local});
const synthesis = list => ({getVoices: () => list});

test('solo voces españolas locales, las latinoamericanas primero', () => {
  const list = browserSpanishVoices(synthesis([voice('Google español', 'es-ES', false), voice('Sabina', 'es-ES'), voice('Paulina', 'es-MX'), voice('Zira', 'en-US')]));
  assert.deepEqual(list.map(v => v.name), ['Paulina', 'Sabina']);
  assert.deepEqual(browserSpanishVoices(synthesis([])), []);
  assert.deepEqual(browserSpanishVoices(undefined), []);
});
test('elección: preferencia válida, si no navegador, si no equipo, si no nada', () => {
  const browser = [voice('Paulina', 'es-MX')], server = [{id: 'es', label: 'Español'}, {id: 'es+f3', label: 'Español femenina'}];
  assert.equal(chooseVoice({browser, server, pref: 'server:es+f3'}).id, 'es+f3');
  assert.equal(chooseVoice({browser, server, pref: 'browser:Paulina'}).kind, 'browser');
  assert.equal(chooseVoice({browser, server, pref: 'server:desaparecida'}).kind, 'browser');
  assert.equal(chooseVoice({browser: [], server, pref: 'auto'}).kind, 'server');
  assert.equal(chooseVoice({browser: [], server: [], pref: 'auto'}), null);
});
test('la boca reparte las palabras en la duración del audio, en orden y sin pasarse', () => {
  const t = wordTimings('Hola, mundo lógico.', word => word.length / 2, 3000);
  assert.deepEqual(t.map(x => x.word), ['Hola', 'mundo', 'lógico']);
  assert.equal(t[0].at, 0);
  assert.ok(t[0].at < t[1].at && t[1].at < t[2].at && t[2].at < 3000);
  assert.equal(t[0].pause, true);
  assert.deepEqual(wordTimings('', () => 1, 1000), []);
});
test('la preferencia se guarda y tolera un almacenamiento roto', () => {
  const store = new Map(); const storage = {getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, v)};
  assert.equal(readVoicePref(storage), 'auto');
  saveVoicePref(storage, 'server:es'); assert.equal(readVoicePref(storage), 'server:es');
  const broken = {getItem() { throw Error('no'); }, setItem() { throw Error('no'); }};
  assert.equal(readVoicePref(broken), 'auto'); saveVoicePref(broken, 'x');
});

const $ = (id) => document.getElementById(id);
const symbolsBody = $('symbols');
const interpretationBox = $('interpretation');
const formulaBox = $('formula');
let domain = [];
let preparedSignature = null;
let freeVariables = [];
let freeRequest = 0;
let searchRequest = 0;
let storyState = null;
let storyScene = null;
let storyTimer = null;
let storyPlaying = false;
let storyNonce = 0;
let spanishRecorder = null;
let spanishStream = null;
let spanishRecordTimer = null;

function sameValue(a, b) { return typeof a === typeof b && a === b; }

function stopStoryAudio() {
  if (storyTimer) clearTimeout(storyTimer);
  storyTimer = null;
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}

function pauseStory() {
  storyPlaying = false;
  stopStoryAudio();
  $('story-play').disabled = false;
  $('story-pause').disabled = true;
}

function clearStory() {
  storyNonce++;
  pauseStory();
  if (storyScene) storyScene.dispose();
  storyScene = null; storyState = null;
  $('story-section').hidden = true;
  $('story-visual').replaceChildren();
  $('story-2d').replaceChildren();
}

function renderStory2D(event) {
  const box = $('story-2d'); box.replaceChildren();
  if (!storyState) return;
  const model = storyState.model;
  if (!model) {
    box.append(node('p', `Regla: ${event.rule}. Referencias: ${event.refs?.join(', ') || 'ninguna'}.`, 'hint'));
    if (event.context?.length) box.append(node('p', `Hipótesis abiertas: ${event.context.join(', ')}`, 'hint'));
    return;
  }
  const focus = event.term_values?.length ? event.term_values :
    event.element !== null && event.element !== undefined ? [event.element] : Object.values(event.assignment || {});
  const nodes = node('div', undefined, 'story-domain');
  model.domain.forEach(value => {
    const active = focus.some(item => sameValue(item, value));
    const chip = node('span', valueLabel(value), `story-node ${active ? (event.value ? 'true' : 'false') : ''}`);
    nodes.append(chip);
  });
  box.append(nodes);
  if (event.relation && model.predicates[event.relation]) {
    const relation = model.predicates[event.relation];
    box.append(node('p', `${event.relation}ᴵ = {${relation.tuples.map(tupleLabel).join(', ')}}`, 'hint'));
  } else {
    box.append(node('p', `D = {${model.domain.map(valueLabel).join(', ')}}`, 'hint'));
  }
}

function renderStoryStep() {
  if (!storyState) return;
  const {events, index} = storyState;
  const event = events[index];
  const current = $('story-current'); current.replaceChildren();
  current.append(node('span', `Paso ${index + 1} de ${events.length} · nodo ${event.trace_path}`, 'hint'));
  current.append(node('strong', event.formula));
  current.append(node('p', event.text_es));
  current.append(node('span', event.value === null ? 'Paso verificado' : event.value ? 'Verdadero' : 'Falso',
    `badge ${event.value === null ? 'verified' : event.value ? 'true' : 'false'}`));
  $('story-prev').disabled = index === 0;
  $('story-next').disabled = index === events.length - 1;
  for (const [i, item] of [...$('story-list').children].entries()) {
    if (i === index) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
  }
  renderStory2D(event);
  if (storyScene) storyScene.setEvent(event);
  showSpan(event.span);
}

async function initStory3D() {
  if (!storyState?.model || !$('story-3d').checked) return;
  const nonce = storyNonce;
  try {
    const {createStoryScene} = await import('/story3d.js');
    if (nonce !== storyNonce || !storyState || !$('story-3d').checked) return;
    storyScene = createStoryScene($('story-visual'), storyState.model);
    storyScene.setEvent(storyState.events[storyState.index]);
    $('story-visual').hidden = false;
    $('story-status').textContent = 'Vista 3D local activa. La vista 2D también está disponible.';
  } catch {
    $('story-3d').checked = false;
    $('story-visual').hidden = true;
    $('story-status').textContent = 'WebGL no está disponible; sigue la vista 2D.';
  }
}

function showStory(story, model) {
  clearStory();
  if (!story?.events?.length) return;
  storyState = {events: story.events, model, index: 0};
  $('story-3d').disabled = !model;
  $('story-3d').checked = Boolean(model);
  $('story-visual').hidden = !model;
  $('story-status').textContent = model ? 'Cargando vista 3D local…' : 'Pasos del certificado en vista 2D.';
  $('story-section').hidden = false;
  $('story-list').replaceChildren();
  for (const [i, event] of story.events.entries()) {
    const item = node('li');
    const button = node('button', `${event.trace_path} · ${event.text_es}`, 'story-link');
    button.type = 'button';
    button.addEventListener('click', () => { pauseStory(); storyState.index = i; renderStoryStep(); });
    item.append(button); $('story-list').append(item);
  }
  renderStoryStep(); initStory3D();
}

function localSpanishVoice() {
  if (!('speechSynthesis' in window)) return null;
  return window.speechSynthesis.getVoices().find(voice => voice.lang.toLowerCase().startsWith('es') && voice.localService === true) || null;
}

function advanceStory() {
  if (!storyState || !storyPlaying) return;
  if (storyState.index >= storyState.events.length - 1) { pauseStory(); return; }
  storyState.index++;
  renderStoryStep(); narrateCurrent();
}

function narrateCurrent() {
  if (!storyState || !storyPlaying) return;
  stopStoryAudio();
  const event = storyState.events[storyState.index];
  const voice = $('story-voice').checked ? localSpanishVoice() : null;
  if (voice && 'SpeechSynthesisUtterance' in window) {
    const utterance = new SpeechSynthesisUtterance(event.text_es);
    utterance.lang = voice.lang; utterance.voice = voice; utterance.rate = .92;
    const index = storyState.index;
    utterance.onend = () => { if (storyPlaying && storyState?.index === index) advanceStory(); };
    utterance.onerror = () => { if (storyPlaying && storyState?.index === index) advanceStory(); };
    window.speechSynthesis.speak(utterance);
    $('story-status').textContent = `Voz local: ${voice.name}.`;
    return;
  }
  if ($('story-voice').checked) $('story-status').textContent = 'No hay voz local en español. Continúa la narración en texto.';
  storyTimer = setTimeout(advanceStory, Math.max(2200, event.text_es.length * 55));
}

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function addSymbol(name = '', kind = 'predicate', arity = 1) {
  const row = node('tr');
  const nameCell = node('td');
  const nameInput = node('input');
  nameInput.value = name;
  nameInput.placeholder = kind === 'predicate' ? 'P' : 'f';
  nameInput.setAttribute('aria-label', 'Nombre del símbolo');
  nameCell.append(nameInput);
  const kindCell = node('td');
  const kindSelect = node('select');
  for (const [value, label] of [['constant', 'Constante (función 0)'], ['function', 'Función'], ['predicate', 'Predicado']]) {
    const opt = node('option', label); opt.value = value; kindSelect.append(opt);
  }
  kindSelect.value = kind;
  kindSelect.setAttribute('aria-label', 'Tipo de símbolo');
  kindCell.append(kindSelect);
  const arityCell = node('td');
  const arityInput = node('input');
  arityInput.type = 'number'; arityInput.min = '1'; arityInput.max = '5'; arityInput.step = '1';
  arityInput.value = arity; arityInput.setAttribute('aria-label', 'Aridad');
  arityInput.disabled = kind === 'constant';
  arityCell.append(arityInput);
  const removeCell = node('td');
  const remove = node('button', undefined, 'remove');
  remove.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M2 2l10 10M12 2L2 12"/></svg>'; remove.type = 'button'; remove.setAttribute('aria-label', 'Eliminar símbolo');
  remove.addEventListener('click', () => { row.remove(); invalidateTables(); });
  removeCell.append(remove);
  row.dataset.kind = kind;
  kindSelect.addEventListener('change', () => { row.dataset.kind = kindSelect.value; arityInput.disabled = kindSelect.value === 'constant'; invalidateTables(); });
  nameInput.addEventListener('input', invalidateTables);
  arityInput.addEventListener('input', invalidateTables);
  row.append(nameCell, kindCell, arityCell, removeCell);
  symbolsBody.append(row);
}

function signature() {
  const sig = { constants: [], functions: {}, predicates: {} };
  const seen = new Set();
  for (const row of symbolsBody.rows) {
    const [name, kind, arityRaw] = [...row.querySelectorAll('input,select')].map(x => x.value.trim());
    if (!name || seen.has(name)) throw Error('Cada símbolo necesita un nombre único.');
    seen.add(name);
    if (kind === 'constant') sig.constants.push(name);
    else {
      const arity = Number(arityRaw);
      if (!Number.isInteger(arity) || arity < 1 || arity > 5) throw Error(`La aridad de ${name} debe estar entre 1 y 5.`);
      (kind === 'function' ? sig.functions : sig.predicates)[name] = arity;
    }
  }
  return sig;
}

function invalidateTables() {
  clearStory();
  searchRequest++;
  preparedSignature = null;
  interpretationBox.replaceChildren();
  $('countermodel-result').replaceChildren();
  $('model-error').hidden = true;
  refreshReady();
  updateFree();
}

function readDomain() {
  // Acepta JSON ([0,1], ["Ana","Luis"]) y también la escritura usual: 0, 1 · {a, b} · Ana, Luis.
  const text = $('domain').value.trim();
  let parsed;
  try { parsed = JSON.parse(text); }
  catch {
    const inner = text.replace(/^[\[{(]\s*/, '').replace(/\s*[\]})]$/, '');
    if (!inner.trim()) throw Error('El dominio no puede ser vacío.');
    parsed = inner.split(',').map(piece => {
      const item = piece.trim();
      const quoted = item.match(/^(["'])(.*)\1$/);  // entre comillas siempre es cadena
      if (quoted) return quoted[2];
      return /^-?\d+$/.test(item) && Number.isSafeInteger(Number(item)) ? Number(item) : item;
    });
    if (parsed.some(item => item === '')) throw Error('El dominio tiene un elemento vacío: revisa las comas.');
  }
  if (!Array.isArray(parsed) || !parsed.length || parsed.some(x => typeof x !== 'string' && !(Number.isInteger(x) && !Object.is(x, -0)))) {
    throw Error('El dominio debe ser una lista no vacía de enteros o cadenas.');
  }
  if (new Set(parsed.map(x => `${typeof x}:${x}`)).size !== parsed.length) throw Error('El dominio tiene elementos repetidos.');
  return parsed;
}

function tuples(values, arity) {
  let out = [[]];
  for (let i = 0; i < arity; i++) out = out.flatMap(prefix => values.map(value => [...prefix, value]));
  return out;
}

function valueLabel(value) { return typeof value === 'string' ? JSON.stringify(value) : String(value); }
function tupleLabel(tuple) { return `(${tuple.map(valueLabel).join(', ')})`; }

function valueSelect(label, options) {
  const select = node('select');
  select.setAttribute('aria-label', label);
  const blank = node('option', 'Selecciona un valor'); blank.value = ''; select.append(blank);
  options.forEach((value, i) => { const opt = node('option', valueLabel(value)); opt.value = String(i); select.append(opt); });
  select.addEventListener('change', () => { clearStory(); refreshReady(); });
  return select;
}

const KIND_LABEL = {constant: 'constante', function: 'función', predicate: 'predicado'};
function group(name, kind, arity, description) {
  const box = node('div', undefined, 'interpret-group'); box.dataset.kind = kind;
  const title = node('h3', name);
  title.append(node('span', arity ? `${KIND_LABEL[kind]} · aridad ${arity}` : KIND_LABEL[kind], `kind ${kind}`));
  box.append(title, node('p', description));
  interpretationBox.append(box);
  return box;
}

function table(box, headA, headB) {
  const wrap = node('div', undefined, 'table-wrap');
  const tbl = node('table');
  const thead = node('thead'); const tr = node('tr');
  tr.append(node('th', headA), node('th', headB)); thead.append(tr);
  const body = node('tbody'); tbl.append(thead, body); wrap.append(tbl); box.append(wrap);
  return body;
}

function prepare() {
  clearStory();
  searchRequest++;
  const error = $('model-error'); error.hidden = true;
  $('countermodel-result').replaceChildren();
  try {
    const sig = signature();
    const values = readDomain();
    const entries = [...Object.entries(sig.functions), ...Object.entries(sig.predicates)];
    if (entries.some(([, n]) => values.length ** n > 1024)) throw Error('La tabla supera 1024 filas. Reduce el dominio o la aridad.');
    domain = values; preparedSignature = sig; interpretationBox.replaceChildren();
    for (const name of sig.constants) {
      const box = group(name, 'constant', 0, 'Selecciona su valor en D.');
      const select = valueSelect(`Valor de ${name}`, domain); select.dataset.constant = name; box.append(select);
    }
    for (const [name, arity] of Object.entries(sig.functions)) {
      const body = table(group(name, 'function', arity, 'Completa un valor para cada entrada.'), 'Entrada', 'Valor');
      for (const args of tuples(domain, arity)) {
        const row = node('tr'); row.dataset.args = JSON.stringify(args); row.dataset.function = name;
        const val = valueSelect(`Valor de ${name}${tupleLabel(args)}`, domain);
        row.append(node('td', tupleLabel(args)), node('td')); row.lastChild.append(val); body.append(row);
      }
    }
    for (const [name, arity] of Object.entries(sig.predicates)) {
      const body = table(group(name, 'predicate', arity, 'Marca las tuplas que pertenecen a la relación.'), 'Tupla', 'Pertenece');
      for (const args of tuples(domain, arity)) {
        const row = node('tr'); row.dataset.args = JSON.stringify(args); row.dataset.predicate = name;
        const checkbox = node('input'); checkbox.type = 'checkbox'; checkbox.setAttribute('aria-label', `${name}${tupleLabel(args)} pertenece`);
        checkbox.addEventListener('change', () => { clearStory(); refreshReady(); });
        row.append(node('td', tupleLabel(args)), node('td', undefined, 'check-cell'));
        row.lastChild.append(checkbox); body.append(row);
      }
    }
    updateFree(); refreshReady();
  } catch (exc) {
    preparedSignature = null; interpretationBox.replaceChildren(); error.textContent = exc.message; error.hidden = false; refreshReady();
  }
}

function interpretation() {
  if (!preparedSignature) throw Error('Prepara primero las tablas de interpretación.');
  const data = { domain, constants: {}, functions: {}, predicates: {} };
  for (const select of interpretationBox.querySelectorAll('[data-constant]')) {
    if (select.value === '') throw Error(`Falta elegir el valor de ${select.dataset.constant}.`);
    data.constants[select.dataset.constant] = domain[Number(select.value)];
  }
  for (const [name, arity] of Object.entries(preparedSignature.functions)) {
    data.functions[name] = { arity, table: [] };
    for (const row of interpretationBox.querySelectorAll('tr[data-function]')) {
      if (row.dataset.function !== name) continue;
      const select = row.querySelector('select');
      if (select.value === '') throw Error(`Falta completar la tabla de ${name}.`);
      data.functions[name].table.push([JSON.parse(row.dataset.args), domain[Number(select.value)]]);
    }
  }
  for (const [name, arity] of Object.entries(preparedSignature.predicates)) {
    const selected = [...interpretationBox.querySelectorAll('tr[data-predicate]')]
      .filter(row => row.dataset.predicate === name && row.querySelector('input').checked)
      .map(row => JSON.parse(row.dataset.args));
    if (!selected.length) throw Error(`La relación ${name} debe tener al menos una tupla.`);
    data.predicates[name] = { arity, tuples: selected };
  }
  return data;
}

function refreshReady() {
  $('result').replaceChildren();
  let note = 'Completa la interpretación.';
  let ready = false;
  if (preparedSignature) {
    try { interpretation(); ready = true; note = formulaBox.value.trim() ? 'Modelo completo. Listo para evaluar.' : 'Modelo completo. Escribe una fórmula para evaluar.'; }
    catch (exc) { note = exc.message; }
  }
  $('ready-note').textContent = note;
  $('evaluate').disabled = !ready || !formulaBox.value.trim();
  $('export-json').disabled = !ready;
  $('find-countermodel').disabled = !preparedSignature || !formulaBox.value.trim();
}

async function api(route, payload) {
  const response = await fetch(route, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  return response.json();
}

function showSpan(span) {
  const box = $('formula-markup'); box.replaceChildren();
  const text = formulaBox.value;
  if (!span || !text) return;
  const [start, end] = span;
  box.append(document.createTextNode(text.slice(0, start)), node('mark', text.slice(start, end) || ' '), document.createTextNode(text.slice(end)));
}

function showFormulaError(error) {
  const box = $('formula-error');
  box.textContent = error?.message || '';
  box.hidden = !error;
  showSpan(error?.span);
}

async function updateFree() {
  const request = ++freeRequest;
  const area = $('assignment'); area.replaceChildren();
  freeVariables = [];
  if (!formulaBox.value.trim() || !preparedSignature) { showFormulaError(null); refreshReady(); return; }
  try {
    const result = await api('/api/free', { signature: preparedSignature, formula: formulaBox.value });
    if (request !== freeRequest) return;
    if (result.status !== 'ok') { showFormulaError(result.errors?.[0]); return; }
    showFormulaError(null);
    freeVariables = result.variables;
    if (!freeVariables.length) area.append(node('span', 'La fórmula es cerrada; no necesita asignación.', 'hint'));
    for (const variable of freeVariables) {
      const label = node('label', `${variable} ∈ D`);
      const select = valueSelect(`Valor de ${variable}`, domain); select.dataset.variable = variable;
      label.append(select); area.append(label);
    }
  } catch { if (request === freeRequest) showFormulaError({message: 'No se pudo consultar el analizador local.'}); }
  refreshReady();
}

function explanationElement(data, root = false) {
  const wrapper = node('div', undefined, 'explanation');
  const details = node('details'); details.open = root;
  const summary = node('summary');
  summary.append(node('span', data.value ? 'V' : 'F', `truth ${data.value ? '' : 'false'}`), node('code', data.formula, 'explained-formula'));
  if (data.assignment?.length) summary.append(node('span', `con ${data.assignment.map(([name, value]) => `${name} = ${valueLabel(value)}`).join(', ')}`, 'hint'));
  summary.append(node('span', data.summary));
  summary.addEventListener('click', () => showSpan(data.span));
  details.append(summary);
  if (data.details?.length) {
    const more = node('div', undefined, 'details');
    data.details.forEach(line => more.append(node('div', line)));
    details.append(more);
  }
  data.children?.forEach(child => details.append(explanationElement(child)));
  wrapper.append(details); return wrapper;
}

async function evaluateFormula() {
  clearStory();
  const resultBox = $('result'); resultBox.replaceChildren();
  const run = $('evaluate'); run.setAttribute('aria-busy', 'true'); run.textContent = 'Evaluando…';
  try {
    const model = interpretation();
    const assignment = {};
    for (const select of $('assignment').querySelectorAll('select[data-variable]')) {
      if (select.value === '') throw Error(`Asigna un valor a ${select.dataset.variable}.`);
      assignment[select.dataset.variable] = domain[Number(select.value)];
    }
    const result = await api('/api/evaluate', { signature: preparedSignature, interpretation: model, formula: formulaBox.value, assignment });
    if (result.status !== 'ok') {
      const error = result.errors?.[0] || {message: 'Entrada inválida.'};
      showFormulaError(error);
      resultBox.append(node('p', error.message, 'error'));
      return;
    }
    showFormulaError(null);
    const verdict = node('p', result.value ? 'Verdadero' : 'Falso', `verdict ${result.value ? 'true' : 'false'}`);
    verdict.append(node('small', result.explanation.summary));
    resultBox.append(verdict);
    resultBox.append(node('h3', 'Por qué'));
    const tree = explanationElement(result.explanation, true);
    const toggle = node('button', 'Desplegar todo', 'button secondary'); toggle.type = 'button';
    toggle.addEventListener('click', () => {
      const open = toggle.textContent === 'Desplegar todo';
      tree.querySelectorAll('details').forEach((item, i) => { item.open = open || i === 0; });
      toggle.textContent = open ? 'Contraer' : 'Desplegar todo';
    });
    if (result.explanation.children?.length) resultBox.append(toggle);
    resultBox.append(tree);
    showStory(result.story, result.model);
  } catch (exc) { resultBox.append(node('p', exc.message || 'No se pudo evaluar.', 'error')); }
  finally { run.removeAttribute('aria-busy'); run.textContent = 'Evaluar'; }
}

function loadSample() {
  symbolsBody.replaceChildren();
  addSymbol('a', 'constant', 0); addSymbol('P', 'predicate', 1); addSymbol('Q', 'predicate', 1);
  $('domain').value = '[0,1]'; prepare();
  interpretationBox.querySelector('[data-constant]').value = '0';
  for (const row of interpretationBox.querySelectorAll('tr[data-predicate]')) {
    const args = JSON.parse(row.dataset.args);
    row.querySelector('input').checked = row.dataset.predicate === 'P' ? args[0] === 0 : args[0] === 1;
  }
  formulaBox.value = '∀x (P(x) → Q(x))'; updateFree(); refreshReady();
  $('result').replaceChildren();
}

function exportJSON() {
  try {
    const payload = { schema_version: '1', signature: preparedSignature,
      interpretation: interpretation(), formula: formulaBox.value };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}));
    const anchor = node('a'); anchor.href = url; anchor.download = 'logos-interpretacion.json';
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('transfer-note').textContent = 'Interpretación exportada.';
  } catch (exc) { $('transfer-note').textContent = exc.message; }
}

function applyPackage(payload, model) {
  const arities = [...Object.values(payload.signature.functions), ...Object.values(payload.signature.predicates)];
  if (arities.some(n => n > 5 || model.domain.length ** n > 1024)) {
    throw Error('La interpretación supera el tamaño admitido por las tablas de la interfaz.');
  }
  symbolsBody.replaceChildren();
  for (const name of payload.signature.constants) addSymbol(name, 'constant', 0);
  for (const [name, arity] of Object.entries(payload.signature.functions)) addSymbol(name, 'function', arity);
  for (const [name, arity] of Object.entries(payload.signature.predicates)) addSymbol(name, 'predicate', arity);
  $('domain').value = JSON.stringify(model.domain);
  prepare();
  for (const select of interpretationBox.querySelectorAll('[data-constant]')) {
    const value = model.constants[select.dataset.constant];
    select.value = String(domain.findIndex(item => typeof item === typeof value && item === value));
  }
  for (const row of interpretationBox.querySelectorAll('tr[data-function]')) {
    const spec = model.functions[row.dataset.function];
    const args = row.dataset.args;
    const found = spec.table.find(([key]) => JSON.stringify(key) === args);
    const value = found[1];
    row.querySelector('select').value = String(domain.findIndex(item => typeof item === typeof value && item === value));
  }
  for (const row of interpretationBox.querySelectorAll('tr[data-predicate]')) {
    const spec = model.predicates[row.dataset.predicate];
    row.querySelector('input').checked = spec.tuples.some(item => JSON.stringify(item) === row.dataset.args);
  }
  formulaBox.value = typeof payload.formula === 'string' ? payload.formula : '';
  updateFree(); refreshReady();
}

async function importJSON(file) {
  const note = $('transfer-note'); note.textContent = '';
  try {
    if (!file) return;
    const payload = JSON.parse(await file.text());
    if (payload.schema_version !== '1') throw Error('Versión JSON no compatible.');
    const checked = await api('/api/validate', {signature: payload.signature, interpretation: payload.interpretation});
    if (checked.status !== 'ok') throw Error(checked.errors?.[0]?.message || 'Interpretación inválida.');
    applyPackage(payload, checked.model);
    note.textContent = 'Interpretación importada y validada.';
  } catch (exc) { note.textContent = `No se pudo importar: ${exc.message}`; }
  $('import-file').value = '';
}

async function searchCountermodel() {
  clearStory();
  const request = ++searchRequest;
  const box = $('countermodel-result'); box.replaceChildren();
  const button = $('find-countermodel'); button.disabled = true;
  box.append(node('p', 'Buscando modelos dentro de los límites…', 'hint'));
  try {
    const result = await api('/api/countermodel', {
      signature: preparedSignature, formula: formulaBox.value, max_size: Number($('max-size').value)
    });
    if (request !== searchRequest) return;
    box.replaceChildren();
    if (result.status === 'invalid_input') {
      const error = result.errors?.[0] || {message: 'Entrada inválida.'};
      showFormulaError(error); box.append(node('p', error.message, 'error')); return;
    }
    showFormulaError(null);
    if (result.status === 'unknown') {
      const reasons = {size_limit: 'Se agotó el tamaño máximo.', candidate_limit: 'Se alcanzó el límite de modelos.',
        timeout: 'Se agotó el tiempo.', table_limit: 'La tabla supera el límite de búsqueda.'};
      box.append(node('p', `No se encontró un contramodelo. ${reasons[result.reason] || ''} Esto no prueba validez universal. Se exploraron ${result.explored} modelos.`, 'hint'));
      return;
    }
    box.append(node('span', 'Contramodelo verificado', 'badge false'));
    box.append(node('p', `Dominio de ${result.model.domain.length} elemento(s). Se exploraron ${result.explored} modelos.`, 'hint'));
    const modelText = node('pre', JSON.stringify(result.model, null, 2), 'model-json');
    box.append(modelText);
    const load = node('button', 'Cargar este modelo en las tablas', 'button secondary'); load.type = 'button';
    load.addEventListener('click', () => {
      applyPackage({signature: preparedSignature, formula: formulaBox.value}, result.model);
      $('transfer-note').textContent = 'Contramodelo cargado en las tablas.';
    });
    box.append(load, node('h3', '¿Por qué es falsa?'), explanationElement(result.explanation, true));
    showStory(result.story, result.model);
  } catch (exc) { if (request === searchRequest) box.replaceChildren(node('p', exc.message || 'No se pudo buscar.', 'error')); }
  finally { if (request === searchRequest) refreshReady(); }
}

async function showSpanishReadings() {
  const box = $('spanish-readings'); box.replaceChildren();
  try {
    const result = await api('/api/spanish', {text: $('spanish-input').value});
    if (result.status === 'invalid_input') {
      box.append(node('p', result.errors?.[0]?.message || 'Frase no admitida.', 'error'));
      return;
    }
    if (result.status === 'ambiguous') {
      box.append(node('p', 'Hay más de una lectura. Elige la que quisiste decir.', 'hint'));
    }
    for (const reading of result.readings) {
      const row = node('div', undefined, 'spanish-reading');
      row.append(node('strong', reading.note), node('code', reading.formula));
      const use = node('button', 'Usar esta lectura y preparar el modelo', 'button secondary');
      use.type = 'button';
      use.addEventListener('click', () => {
        symbolsBody.replaceChildren();
        for (const name of reading.signature.constants) addSymbol(name, 'constant', 0);
        for (const [name, arity] of Object.entries(reading.signature.functions)) addSymbol(name, 'function', arity);
        for (const [name, arity] of Object.entries(reading.signature.predicates)) addSymbol(name, 'predicate', arity);
        formulaBox.value = reading.formula;
        prepare();
        box.replaceChildren(node('p', `Lectura ${reading.id} elegida. Completa la interpretación para evaluarla.`, 'hint'));
      });
      row.append(use); box.append(row);
    }
  } catch (exc) { box.append(node('p', exc.message || 'No se pudo traducir.', 'error')); }
}

function stopSpanishRecording() {
  if (spanishRecordTimer) clearTimeout(spanishRecordTimer);
  spanishRecordTimer = null;
  if (spanishRecorder?.state === 'recording') spanishRecorder.stop();
  $('stop-spanish').disabled = true;
}

async function recordSpanish() {
  const status = $('record-status');
  status.textContent = '';
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder ||
      !MediaRecorder.isTypeSupported('audio/webm')) {
    status.textContent = 'Este navegador no permite grabar audio WebM.'; return;
  }
  try {
    const config = await api('/api/voice/status', {});
    if (!config.available) { status.textContent = 'Configura whisper-cli y un modelo español local para usar el micrófono.'; return; }
    spanishStream = await navigator.mediaDevices.getUserMedia({audio: true});
    const chunks = [];
    spanishRecorder = new MediaRecorder(spanishStream, {mimeType: 'audio/webm'});
    spanishRecorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    spanishRecorder.onstop = async () => {
      spanishStream?.getTracks().forEach(track => track.stop()); spanishStream = null;
      $('record-spanish').disabled = false;
      const audio = new Blob(chunks, {type: 'audio/webm'});
      status.textContent = 'Transcribiendo en este equipo…';
      try {
        const response = await fetch('/api/voice/transcribe', {method: 'POST', headers: {'Content-Type': 'audio/webm'}, body: audio});
        const result = await response.json();
        if (!response.ok) throw Error(result.errors?.[0]?.message || 'No se pudo transcribir.');
        $('spanish-input').value = result.text;
        $('spanish-readings').replaceChildren();
        status.textContent = 'Transcripción lista. Revísala y pulsa «Mostrar lecturas».';
      } catch (exc) { status.textContent = exc.message; }
    };
    spanishRecorder.start();
    $('record-spanish').disabled = true; $('stop-spanish').disabled = false;
    status.textContent = 'Grabando… se detendrá a los 12 segundos.';
    spanishRecordTimer = setTimeout(stopSpanishRecording, 12000);
  } catch (exc) {
    spanishStream?.getTracks().forEach(track => track.stop()); spanishStream = null;
    status.textContent = `No se pudo iniciar la grabación: ${exc.message}`;
  }
}

async function proveFormula() {
  clearStory();
  const box = $('proof-result'); box.replaceChildren();
  const premises = $('proof-premises').value.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const conclusion = $('proof-conclusion').value.trim();
  const constants = $('proof-constants').value.split(',').map(s => s.trim()).filter(Boolean);
  const button = $('prove'); button.disabled = true;
  box.append(node('p', 'Buscando y verificando la prueba…', 'hint'));
  try {
    const result = await api('/api/proof', {premises, conclusion, constants});
    box.replaceChildren();
    if (result.status === 'invalid_input') {
      box.append(node('p', result.errors?.[0]?.message || 'Entrada inválida.', 'error')); return;
    }
    if (result.status === 'unknown') {
      box.append(node('p', `No se encontró prueba dentro de los límites (${result.reason || 'límite'}). Esto no demuestra que la conclusión sea falsa.`, 'hint'));
      return;
    }
    box.append(node('span', 'Prueba verificada', 'badge verified'));
    box.append(node('pre', result.certificate.steps.map(step =>
      `${step.id}. ${step.formula}  (${step.rule}${step.refs.length ? `: ${step.refs.join(', ')}` : ''})`).join('\n'), 'model-json'));
    showStory(result.story, null);
    $('story-section').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (exc) { box.replaceChildren(node('p', exc.message || 'No se pudo buscar la prueba.', 'error')); }
  finally { button.disabled = false; }
}

$('add-symbol').addEventListener('click', () => { addSymbol(); invalidateTables(); });
$('prepare').addEventListener('click', prepare);
$('domain').addEventListener('input', invalidateTables);
$('sample').addEventListener('click', loadSample);
$('evaluate').addEventListener('click', evaluateFormula);
$('export-json').addEventListener('click', exportJSON);
$('import-json').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', event => importJSON(event.target.files[0]));
$('find-countermodel').addEventListener('click', searchCountermodel);
$('translate-spanish').addEventListener('click', showSpanishReadings);
$('record-spanish').addEventListener('click', recordSpanish);
$('stop-spanish').addEventListener('click', stopSpanishRecording);
$('prove').addEventListener('click', proveFormula);
for (const id of ['proof-premises', 'proof-conclusion', 'proof-constants']) {
  $(id).addEventListener('input', () => { clearStory(); $('proof-result').replaceChildren(); });
}
$('story-play').addEventListener('click', () => {
  if (!storyState) return;
  if (storyState.index === storyState.events.length - 1) storyState.index = 0;
  storyPlaying = true; renderStoryStep();
  $('story-play').disabled = true; $('story-pause').disabled = false;
  narrateCurrent();
});
$('story-pause').addEventListener('click', pauseStory);
$('story-prev').addEventListener('click', () => {
  if (!storyState || storyState.index === 0) return;
  stopStoryAudio(); storyState.index--; renderStoryStep(); if (storyPlaying) narrateCurrent();
});
$('story-next').addEventListener('click', () => {
  if (!storyState || storyState.index === storyState.events.length - 1) return;
  stopStoryAudio(); storyState.index++; renderStoryStep(); if (storyPlaying) narrateCurrent();
});
$('story-replay').addEventListener('click', () => {
  if (!storyState) return;
  stopStoryAudio(); storyState.index = 0; renderStoryStep(); if (storyPlaying) narrateCurrent();
});
$('story-voice').addEventListener('change', () => { if (storyPlaying) narrateCurrent(); });
$('story-3d').addEventListener('change', () => {
  storyNonce++;
  if (storyScene) storyScene.dispose(); storyScene = null;
  $('story-visual').replaceChildren(); $('story-visual').hidden = true;
  if ($('story-3d').checked) initStory3D();
  else $('story-status').textContent = 'Vista 2D activa.';
});
formulaBox.addEventListener('input', () => { clearStory(); searchRequest++; $('result').replaceChildren(); $('countermodel-result').replaceChildren(); updateFree(); refreshReady(); });
for (const symbol of ['¬', '∧', '∨', '→', '↔', '∀', '∃', '(', ')', '=', '≠', '⊥']) {
  const button = node('button', symbol, 'key'); button.type = 'button'; button.setAttribute('aria-label', `Insertar ${symbol}`);
  button.addEventListener('click', () => {
    const start = formulaBox.selectionStart, end = formulaBox.selectionEnd;
    formulaBox.setRangeText(symbol, start, end, 'end'); formulaBox.focus();
    formulaBox.dispatchEvent(new Event('input'));
  });
  $('symbols-keyboard').append(button);
}
addSymbol('P', 'predicate', 1);
prepare();
$('story-pause').disabled = true;

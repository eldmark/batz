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

// ── Ayudantes de interfaz: plurales, avisos, contadores, botones ocupados y movimiento ──
const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const phoneLayout = () => window.matchMedia('(max-width: 720px)').matches;

/** «1 elemento», «2 elementos»: nunca «elemento(s)». */
function plural(n, one, many) { return `${n} ${n === 1 ? one : many}`; }

/** Aviso flotante que se va solo; también se cierra con la ×, o deslizándolo en el teléfono. */
function toast(message, kind = 'info', timeout = 4200) {
  const host = $('toasts');
  const box = node('div', undefined, `toast ${kind}`);
  box.append(node('span', message));
  const close = node('button', undefined, 'toast-close'); close.type = 'button'; close.setAttribute('aria-label', 'Cerrar aviso');
  close.innerHTML = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8"/></svg>';
  const dismiss = () => {
    if (box.classList.contains('leaving')) return;
    box.classList.add('leaving');
    setTimeout(() => box.remove(), reduceMotion() ? 0 : 240);
  };
  close.addEventListener('click', dismiss);
  let startX = null;
  box.addEventListener('pointerdown', event => { startX = event.clientX; });
  box.addEventListener('pointerup', event => { if (startX !== null && Math.abs(event.clientX - startX) > 56) dismiss(); startX = null; });
  box.append(close); host.append(box);
  while (host.children.length > 3) host.firstElementChild.remove();
  if (timeout) setTimeout(dismiss, timeout);
  return box;
}

/** Número que sube hasta `value` en vez de aparecer de golpe. */
function countUp(element, value, format = String) {
  if (reduceMotion() || value < 3) { element.textContent = format(value); return element; }
  const start = performance.now(), duration = Math.min(900, 320 + value * 3);
  element.textContent = format(0);
  const tick = now => {
    const t = Math.min(1, (now - start) / duration);
    element.textContent = format(Math.round(value * (1 - (1 - t) ** 3)));
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return element;
}

/** Párrafo con un número animado dentro: «Se exploraron [12] modelos». */
function countLine(before, value, after, className = 'hint', tag = 'p') {
  const line = node(tag, undefined, className);
  line.append(document.createTextNode(before), countUp(node('strong', undefined, 'count'), value), document.createTextNode(after));
  return line;
}

/** Botón de acción con estado: texto → girando → ✓ o ✗ un instante. `task` dice cómo terminó. */
async function withBusy(button, busyLabel, task) {
  const label = button.dataset.label || (button.dataset.label = button.textContent.trim());
  button.setAttribute('aria-busy', 'true');
  delete button.dataset.state;
  button.textContent = busyLabel;
  let outcome = 'fail';
  try { outcome = (await task()) || 'none'; }
  finally {
    button.removeAttribute('aria-busy');
    button.textContent = label;
    if (outcome !== 'none' && !reduceMotion()) {
      button.dataset.state = outcome;
      setTimeout(() => { if (button.dataset.state === outcome) delete button.dataset.state; }, 1100);
    }
  }
}

/** Veredicto grande que aparece letra por letra, sin desenfocar lo que dice al lector de pantalla. */
function verdictElement(word, kind, detail) {
  const verdict = node('p', undefined, `verdict ${kind}`);
  const big = node('span', undefined, 'verdict-word');
  big.append(node('span', word, 'sr-only'));
  [...word].forEach((char, i) => {
    if (char === ' ') { big.append(document.createTextNode(' ')); return; }  // la frase puede partirse entre palabras
    const letter = node('span', char, 'ch');
    letter.style.setProperty('--i', i); letter.setAttribute('aria-hidden', 'true');
    big.append(letter);
  });
  verdict.append(big);
  if (detail) verdict.append(typeof detail === 'string' ? node('small', detail) : detail);
  return verdict;
}

/** Píldora que se desliza hasta la pestaña o el filtro activo. */
function placePill(container) {
  const pill = container?.querySelector(':scope > .pill');
  const active = container?.querySelector(':scope > [aria-selected="true"], :scope > [aria-pressed="true"]');
  if (!pill || !active || !active.offsetWidth) return;
  pill.style.setProperty('--x', `${active.offsetLeft}px`);
  pill.style.setProperty('--y', `${active.offsetTop}px`);
  pill.style.setProperty('--w', `${active.offsetWidth}px`);
  pill.style.setProperty('--h', `${active.offsetHeight}px`);
  if (!container.classList.contains('has-pill')) {
    container.classList.add('has-pill');
    requestAnimationFrame(() => container.classList.add('pill-ready'));  // sin deslizarse desde 0 al cargar
  }
}
const pillHosts = () => document.querySelectorAll('.modes, .subtabs, .filters');
const pillObserver = new ResizeObserver(entries => entries.forEach(entry => placePill(entry.target)));

// Onda desde el punto de contacto: confirma el toque en botones, teclas y pestañas.
document.addEventListener('pointerdown', event => {
  const target = event.target.closest('.button, .key, .mode, .subtab, .filter');
  if (!target || target.disabled || target.getAttribute('aria-busy') === 'true' || reduceMotion()) return;
  const box = target.getBoundingClientRect();
  const size = Math.max(box.width, box.height) * 2.2;
  const wave = node('span', undefined, 'ripple');
  wave.style.cssText = `width:${size}px;height:${size}px;left:${event.clientX - box.left - size / 2}px;top:${event.clientY - box.top - size / 2}px`;
  target.append(wave);
  wave.addEventListener('animationend', () => wave.remove());
});

function stopStoryAudio() {
  if (storyTimer) clearTimeout(storyTimer);
  storyTimer = null;
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  storyScene?.talking(false);
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
  exitStoryFullscreen();
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
  if (event.kind === 'proof' || !model) {
    const rule = event.rule_label || event.rule;
    box.append(node('p', `Línea ${event.line ?? event.trace_path} · ${rule}${event.refs?.length ? ` · usa ${event.refs.join(', ')}` : ''}`, 'hint'));
    if (event.context?.length) box.append(node('p', `Hipótesis abiertas: ${event.context.join(', ')}`, 'hint'));
    return;
  }
  if (event.kind === 'search') {
    // Durante la búsqueda solo existen los elementos del tamaño que se está probando.
    const nodes = node('div', undefined, 'story-domain');
    model.domain.slice(0, event.size).forEach(value => nodes.append(node('span', valueLabel(value), `story-node ${event.phase === 'found' ? 'true' : ''}`)));
    if (!event.size) nodes.append(node('span', '…', 'story-node'));
    box.append(nodes, node('p', event.size ? `D con ${plural(event.size, 'elemento', 'elementos')}` : 'Todavía sin dominio', 'hint'));
    return;
  }
  const focus = event.term_values?.length ? event.term_values :
    event.element !== null && event.element !== undefined ? [event.element] : Object.values(event.assignment || {});
  const nodes = node('div', undefined, 'story-domain');
  model.domain.forEach(value => {
    const active = event.kind !== 'premise' && focus.some(item => sameValue(item, value));
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
  const where = event.kind === 'proof' ? `línea ${event.line}` : event.kind === 'search' ? 'búsqueda'
    : event.kind === 'premise' ? 'premisa' : `nodo ${event.trace_path}`;
  current.append(node('span', `Paso ${index + 1} de ${events.length} · ${where}`, 'hint'));
  if (event.formula) current.append(node('strong', event.formula));
  current.append(node('p', event.text_es));
  const badge = event.kind === 'search' ? ['Búsqueda acotada', 'verified'] : event.value === null ? ['Paso verificado', 'verified']
    : event.value ? ['Verdadero', 'true'] : ['Falso', 'false'];
  current.append(node('span', badge[0], `badge ${badge[1]}`));
  $('story-prev').disabled = index === 0;
  $('story-next').disabled = index === events.length - 1;
  for (const [i, item] of [...$('story-list').children].entries()) {
    if (i === index) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
  }
  // En una prueba, la línea que se narra se marca en la vista Fitch (solo con el paso a paso abierto).
  document.querySelectorAll('.fitch li.current').forEach(li => li.classList.remove('current'));
  if (event.kind === 'proof' && !$('story-section').hidden) document.querySelector(`.fitch li[data-line="${event.line}"]`)?.classList.add('current');
  renderStory2D(event);
  if (storyScene) storyScene.setEvent(event);
  if (event.kind !== 'search' && event.kind !== 'premise') showSpan(event.span);
}

async function initStory3D() {
  if (!storyState || !$('story-3d').checked || storyScene) return;
  const nonce = storyNonce;
  try {
    const {createStoryScene} = await import('/story3d.js');
    if (nonce !== storyNonce || !storyState || !$('story-3d').checked) return;
    storyScene = createStoryScene($('story-visual'), storyState.model, {onPick: pickStoryElement});
    storyScene.setEvent(storyState.events[storyState.index]);
    $('story-visual').hidden = false;
    $('story-status').textContent = storyState.model ? 'Haz clic en un elemento para ver ese caso.' : '';
  } catch {
    $('story-3d').checked = false;
    $('story-visual').hidden = true;
    $('story-status').textContent = 'WebGL no está disponible; sigue la vista 2D.';
  }
}

function showStory(story, model, host) {
  clearStory();
  if (!story?.events?.length) return;
  if (host) {
    const open = node('button', 'Ver paso a paso', 'button secondary story-open'); open.type = 'button';
    open.addEventListener('click', () => {
      $('story-section').hidden = false; renderStoryStep();
      $('story-section').scrollIntoView({behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start'}); initStory3D();
    });
    host.append(open);
  }
  storyState = {events: story.events, model, index: 0};
  $('story-3d').disabled = false;
  $('story-3d').checked = true;
  $('story-visual').hidden = false;
  $('story-status').textContent = '';
  $('story-list').replaceChildren();
  for (const [i, event] of story.events.entries()) {
    const item = node('li');
    const where = event.kind === 'proof' ? `Línea ${event.line}` : event.kind === 'search' ? 'Búsqueda'
      : event.kind === 'premise' ? 'Premisa' : event.trace_path;
    const button = node('button', `${where} · ${event.text_es}`, 'story-link');
    button.type = 'button';
    button.addEventListener('click', () => { pauseStory(); storyState.index = i; renderStoryStep(); });
    item.append(button); $('story-list').append(item);
  }
  renderStoryStep();
}

// Clic en un elemento del dominio: salta al paso donde el cuantificador en curso prueba ese caso.
function pickStoryElement(element) {
  if (!storyState) return;
  const {events, index} = storyState;
  let path = events[index].trace_path;
  while (path) {
    const owner = events.find(e => e.trace_path === path);
    if (owner?.kind === 'quantifier') {
      const depth = path.split('.').length + 1;
      const hit = events.findIndex(e => e.trace_path.startsWith(path + '.') && e.trace_path.split('.').length === depth && sameValue(e.element, element));
      if (hit >= 0) { pauseStory(); storyState.index = hit; renderStoryStep(); return; }
    }
    path = path.includes('.') ? path.slice(0, path.lastIndexOf('.')) : '';
  }
  $('story-status').textContent = 'Ese elemento no se prueba en este paso: avanza hasta un cuantificador.';
}

function localSpanishVoice() {
  if (!('speechSynthesis' in window)) return null;
  // Primero una voz latinoamericana (México, EE. UU., Latinoamérica); si no hay, cualquier español local.
  const local = window.speechSynthesis.getVoices().filter(voice => voice.lang.toLowerCase().startsWith('es') && voice.localService === true);
  return local.find(voice => /^es-(mx|us|419|gt|co|ar|cl|pe)/i.test(voice.lang)) || local[0] || null;
}

/** La casilla de voz solo se ofrece si el sistema tiene una voz local en español; si no, dice cómo instalarla. */
function refreshVoiceOption() {
  const box = $('story-voice'), help = $('voice-help');
  if (!('speechSynthesis' in window)) {
    box.checked = false; box.disabled = true;
    help.textContent = 'Este navegador no puede leer en voz alta.'; help.hidden = false;
    return;
  }
  const voice = localSpanishVoice();
  box.disabled = !voice;
  if (!voice) box.checked = false;
  const windows = /Windows/.test(navigator.userAgent);
  help.textContent = voice ? '' : windows
    ? 'No hay voz en español en este equipo. Instálala en Configuración → Hora e idioma → Voz → Agregar voces → Español, y recarga la página.'
    : 'No hay voz local en español en este equipo. Instala una en la configuración de voz del sistema y recarga la página.';
  help.hidden = Boolean(voice);
}

function advanceStory() {
  if (!storyState || !storyPlaying) return;
  if (storyState.index >= storyState.events.length - 1) {   // fin del recorrido: el avatar reacciona al valor de la fórmula
    pauseStory();
    const root = storyState.events.find(e => e.kind !== 'search' && e.kind !== 'premise');
    if (root && root.value !== null) storyScene?.verdict(root.value);
    return;
  }
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
    // La boca del avatar sigue a la voz: cada palabra que empieza abre y cierra sus vocales.
    utterance.onstart = () => storyScene?.talking(true);
    utterance.onboundary = boundary => {
      if (boundary.name && boundary.name !== 'word') return;
      const word = event.text_es.slice(boundary.charIndex, boundary.charIndex + (boundary.charLength || 12)).split(/[\s,.;:]/)[0];
      storyScene?.say(word, utterance.rate);
    };
    const finish = () => { storyScene?.talking(false); if (storyPlaying && storyState?.index === index) advanceStory(); };
    utterance.onend = finish;
    utterance.onerror = finish;
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

/** Casilla con palomita que se dibuja; la etiqueta agranda el área que se puede tocar. */
function checkBox(input) {
  const label = node('label', undefined, 'check');
  label.append(input);
  label.insertAdjacentHTML('beforeend', '<svg viewBox="0 0 20 20" aria-hidden="true"><path class="tick" d="M5 10.5l3.2 3.2L15 6.5"/></svg>');
  return label;
}

/** Interpretación legible: dominio, constantes, funciones y relaciones como tablas, no como JSON. */
function modelElement(model, {assignment = [], json = true} = {}) {
  const view = node('div', undefined, 'model-view');
  const row = (name, kind, content) => {
    const line = node('div', undefined, 'model-row');
    const head = node('span', undefined, `model-symbol ${kind}`); head.append(node('code', name));
    line.append(head, content); view.append(line); return line;
  };
  const chips = values => { const box = node('span', undefined, 'model-chips'); values.forEach(v => box.append(node('code', v, 'model-chip'))); return box; };
  row('D', 'domain', chips(model.domain.map(valueLabel)));
  for (const [name, value] of Object.entries(model.constants || {})) row(name, 'constant', chips([valueLabel(value)]));
  for (const [variable, value] of assignment) row(variable, 'variable', chips([`${valueLabel(value)} (entorno)`]));
  for (const [name, spec] of Object.entries(model.functions || {})) {
    row(name, 'function', chips(spec.table.map(([args, out]) => `${name}(${args.map(valueLabel).join(', ')}) = ${valueLabel(out)}`)));
  }
  for (const [name, spec] of Object.entries(model.predicates || {})) {
    if (spec.arity === 0) { row(name, 'predicate', chips([spec.tuples.length ? 'verdadera' : 'falsa'])); continue; }
    if (spec.arity === 2 && model.domain.length <= 6) {
      // Relación binaria: una matriz es más fácil de leer que la lista de pares.
      const grid = node('table', undefined, 'model-matrix');
      const head = node('tr'); head.append(node('th', '')); model.domain.forEach(b => head.append(node('th', valueLabel(b))));
      grid.append(head);
      for (const a of model.domain) {
        const line = node('tr'); line.append(node('th', valueLabel(a)));
        for (const b of model.domain) {
          const inside = spec.tuples.some(([x, y]) => sameValue(x, a) && sameValue(y, b));
          const cell = node('td', inside ? '✓' : '', inside ? 'in' : ''); cell.setAttribute('aria-label', `(${valueLabel(a)}, ${valueLabel(b)}) ${inside ? 'pertenece' : 'no pertenece'}`);
          line.append(cell);
        }
        grid.append(line);
      }
      row(name, 'predicate', grid);
      continue;
    }
    const items = spec.tuples.map(t => spec.arity === 1 ? valueLabel(t[0]) : tupleLabel(t));
    row(name, 'predicate', items.length ? chips(items) : node('span', '∅ (vacía)', 'hint'));
  }
  if (json) {
    const more = node('details', undefined, 'model-json-toggle');
    more.append(node('summary', 'Ver JSON'), node('pre', JSON.stringify(model, null, 2), 'model-json'));
    view.append(more);
  }
  return view;
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
  // En el teléfono la fila se vuelve tarjeta: cada campo muestra su propio rótulo.
  nameCell.dataset.label = 'Nombre'; kindCell.dataset.label = 'Tipo'; arityCell.dataset.label = 'Aridad';
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
        row.lastChild.append(checkBox(checkbox)); body.append(row);
        // Toda la fila sirve para marcar la tupla: en el teléfono es más fácil que acertar a la casilla.
        row.addEventListener('click', event => { if (!event.target.closest('label, input')) checkbox.click(); });
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
  $('model-state').textContent = ready ? '✓' : '';
  $('model-state').title = ready ? 'Modelo completo' : '';
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
  await withBusy($('evaluate'), 'Evaluando…', async () => {
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
        return 'fail';
      }
      showFormulaError(null);
      resultBox.append(verdictElement(result.value ? 'Verdadero' : 'Falso', result.value ? 'true' : 'false', result.explanation.summary));
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
      showStory(result.story, result.model, resultBox);
      if (phoneLayout()) resultBox.scrollIntoView({behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start'});
      return 'done';
    } catch (exc) { resultBox.append(node('p', exc.message || 'No se pudo evaluar.', 'error')); return 'fail'; }
  });
}

// El botón «Ejemplo» carga uno del modo en que se está.
const PROOF_SAMPLES = [
  {premises: '∀x (Humano(x) → Mortal(x))\nHumano(socrates)', conclusion: 'Mortal(socrates)', constants: 'socrates',
   note: 'Ejemplo: Sócrates es mortal. Pulsa «Buscar prueba».'},
  {premises: '∀x ∃y Ama(x, y)', conclusion: '∃y ∀x Ama(x, y)', constants: '',
   note: 'Ejemplo: ¿cambiar el orden de ∀ y ∃ conserva la verdad? Pulsa «Buscar prueba».'},
  {premises: '', conclusion: '((p → q) → p) → p', constants: '',
   note: 'Ejemplo: ley de Peirce, con letras proposicionales. Pulsa «Buscar prueba».'},
];
let proofSample = 0;
function loadProofSample() {
  const sample = PROOF_SAMPLES[proofSample++ % PROOF_SAMPLES.length];
  $('proof-premises').value = sample.premises; $('proof-conclusion').value = sample.conclusion;
  $('proof-constants').value = sample.constants;
  clearStory(); $('proof-result').replaceChildren(); checkProofSyntax();
  toast(sample.note);
}
function loadDictionarySample() {
  $('dict-query').value = 'duermen'; setPane($('mode-dictionary'), 'model'); searchDictionary(true);
  toast('Ejemplo: «duermen» se encuentra por su lema, dormir.');
}

function loadSample() {
  symbolsBody.replaceChildren();
  addSymbol('a', 'constant', 0); addSymbol('P', 'predicate', 1); addSymbol('Q', 'predicate', 1);
  $('domain').value = '0, 1'; prepare();
  interpretationBox.querySelector('[data-constant]').value = '0';
  for (const row of interpretationBox.querySelectorAll('tr[data-predicate]')) {
    const args = JSON.parse(row.dataset.args);
    row.querySelector('input').checked = row.dataset.predicate === 'P' ? args[0] === 0 : args[0] === 1;
  }
  formulaBox.value = '∀x (P(x) → Q(x))'; updateFree(); refreshReady();
  $('result').replaceChildren();
  setPane($('mode-evaluate'), 'question');
  toast('Ejemplo cargado: D = {0, 1}, P = {0}, Q = {1}.');
}

function exportJSON() {
  try {
    const payload = { schema_version: '1', signature: preparedSignature,
      interpretation: interpretation(), formula: formulaBox.value };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}));
    const anchor = node('a'); anchor.href = url; anchor.download = 'logos-interpretacion.json';
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('Interpretación exportada.', 'success');
  } catch (exc) { toast(exc.message, 'error'); }
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
  $('domain').value = model.domain.map(valueLabel).join(', ');
  // La fórmula nueva va antes de preparar: así no se consulta la vieja contra la firma nueva.
  formulaBox.value = typeof payload.formula === 'string' ? payload.formula : '';
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
  const pending = updateFree(); refreshReady();
  return pending;  // quien necesite el entorno de las variables libres espera a que aparezcan sus selectores
}

function batchRow(row) {
  const item = node('li');
  const open = node('button', undefined, 'batch-item'); open.type = 'button';
  const state = row.status !== 'ok' ? 'error' : row.matches === false ? 'mismatch' : row.value ? 'true' : 'false';
  open.append(node('span', row.status !== 'ok' ? '!' : row.value ? 'V' : 'F', `truth ${state}`), node('code', row.formula));
  const env = Object.entries(row.assignment || {});
  if (env.length) open.append(node('span', env.map(([k, v]) => `${k} = ${valueLabel(v)}`).join(', '), 'chip'));
  const note = row.status !== 'ok' ? row.error.message
    : row.matches === false ? `El archivo esperaba ${row.expected ? 'verdadero' : 'falso'}.`
    : row.matches === true ? 'Coincide con lo esperado.' : row.summary;
  open.append(node('span', note, 'batch-note'));
  open.addEventListener('click', async () => {
    formulaBox.value = row.formula;
    await updateFree();
    for (const select of $('assignment').querySelectorAll('select[data-variable]')) {
      const value = row.assignment?.[select.dataset.variable];
      const index = domain.findIndex(item => sameValue(item, value));
      if (index >= 0) select.value = String(index);
    }
    refreshReady();
    if (!$('evaluate').disabled) evaluateFormula();
  });
  item.append(open); return item;
}

async function loadFile(file) {
  try {
    if (!file) return;
    if (file.size > 500000) throw Error('El archivo pesa más de 500 kB.');
    const loaded = await api('/api/load', {text: await file.text()});
    if (loaded.status !== 'ok') throw Error(loaded.errors?.[0]?.message || 'Archivo inválido.');
    setMode('evaluate');
    applyPackage({signature: loaded.signature, formula: loaded.results[0]?.formula || ''}, loaded.model);
    const list = $('batch-list'); list.replaceChildren();
    loaded.results.forEach(row => list.append(batchRow(row)));
    $('batch').hidden = loaded.results.length < 2;
    const wrong = loaded.results.filter(r => r.status !== 'ok' || r.matches === false).length;
    const count = loaded.results.length;
    toast(`${file.name}: modelo cargado` + (count ? `, ${plural(count, 'fórmula evaluada', 'fórmulas evaluadas')}` : '') +
      (wrong ? `; ${wrong === 1 ? 'una tiene' : `${wrong} tienen`} error o un valor distinto del esperado.` : '.'), wrong ? 'warning' : 'success', 6000);
    setPane($('mode-evaluate'), 'question');
  } catch (exc) { toast(`No se pudo cargar: ${exc.message}`, 'error', 7000); }
  $('import-file').value = '';
}

const SEARCH_LIMITS = {size_limit: 'Se agotó el tamaño máximo.', candidate_limit: 'Se alcanzó el límite de modelos.',
  timeout: 'Se agotó el tiempo.', table_limit: 'La tabla supera el límite de búsqueda.'};

async function searchCountermodel() {
  clearStory();
  const request = ++searchRequest;
  const box = $('countermodel-result'); box.replaceChildren();
  const button = $('find-countermodel');
  box.append(node('p', 'Buscando modelos dentro de los límites…', 'hint searching'));
  await withBusy(button, 'Buscando…', async () => {
    try {
      const result = await api('/api/countermodel', {
        signature: preparedSignature, formula: formulaBox.value, max_size: Number($('max-size').value)
      });
      if (request !== searchRequest) return 'none';
      box.replaceChildren();
      if (result.status === 'invalid_input') {
        const error = result.errors?.[0] || {message: 'Entrada inválida.'};
        showFormulaError(error); box.append(node('p', error.message, 'error')); return 'fail';
      }
      showFormulaError(null);
      if (result.status === 'unknown') {
        box.append(countLine('No se encontró un contramodelo tras explorar ', result.explored,
          ` ${result.explored === 1 ? 'modelo' : 'modelos'}. ${SEARCH_LIMITS[result.reason] || ''} Esto no prueba que la fórmula sea válida.`));
        return 'none';
      }
      box.append(node('span', 'Contramodelo verificado', 'badge false'));
      box.append(countLine(`Dominio de ${plural(result.model.domain.length, 'elemento', 'elementos')}. Se exploraron `,
        result.explored, result.explored === 1 ? ' modelo.' : ' modelos.'));
      box.append(modelElement(result.model));
      const load = node('button', 'Cargar este modelo en las tablas', 'button secondary'); load.type = 'button';
      load.addEventListener('click', () => {
        applyPackage({signature: preparedSignature, formula: formulaBox.value}, result.model);
        setPane($('mode-evaluate'), 'model');
        toast('Contramodelo cargado en las tablas.', 'success');
      });
      box.append(load, node('h3', '¿Por qué es falsa?'), explanationElement(result.explanation, true));
      showStory(result.story, result.model, box);
      return 'done';
    } catch (exc) {
      if (request === searchRequest) box.replaceChildren(node('p', exc.message || 'No se pudo buscar.', 'error'));
      return 'fail';
    } finally { if (request === searchRequest) refreshReady(); }
  });
}

async function showSpanishReadings() {
  const box = $('spanish-readings'); box.replaceChildren();
  try {
    const result = await api('/api/spanish', {text: $('spanish-input').value});
    if (result.status === 'invalid_input') {
      box.append(node('p', result.errors?.[0]?.message || 'Frase no admitida.', 'error'));
      return;
    }
    if (result.assumptions?.length) {
      // palabras fuera del léxico: se muestra qué categoría se les supuso antes de ofrecer la fórmula
      const assumed = node('div', undefined, 'assumptions');
      assumed.append(node('strong', 'Palabras que no conocía. Supuse esto; revísalo antes de usar la fórmula:'));
      const list = node('ul');
      for (const a of result.assumptions) {
        const item = node('li');
        item.append(node('code', a.word), document.createTextNode(` es ${a.label} `),
          node('span', `${Math.round(a.probability * 100)} %`, 'chip'), document.createTextNode(' → símbolo '), node('code', a.symbol));
        const fix = node('button', 'Añadir al diccionario', 'button secondary small'); fix.type = 'button';
        fix.addEventListener('click', () => openDictionaryWith(a.word));
        item.append(fix); list.append(item);
      }
      assumed.append(list); box.append(assumed);
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
        setPane($('mode-evaluate'), 'model');
        toast('Lectura elegida: ya están los símbolos. Completa la interpretación.', 'success');
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

function proofInput() {
  return {premises: $('proof-premises').value.split(/\r?\n/).map(s => s.trim()).filter(Boolean),
    conclusion: $('proof-conclusion').value.trim(),
    constants: $('proof-constants').value.split(',').map(s => s.trim()).filter(Boolean)};
}

let proofCheckRequest = 0, proofCheckTimer = null;
function scheduleProofCheck() {
  clearTimeout(proofCheckTimer);
  proofCheckTimer = setTimeout(checkProofSyntax, 220);
}

async function checkProofSyntax() {
  const request = ++proofCheckRequest;
  const {premises, conclusion, constants} = proofInput();
  const list = $('proof-check'); const button = $('prove');
  const labels = [...premises.map((_, i) => `Premisa ${i + 1}`), ...(conclusion ? ['Conclusión'] : [])];
  const formulas = [...premises, ...(conclusion ? [conclusion] : [])];
  if (!formulas.length) { list.replaceChildren(); button.disabled = true; $('prove-note').textContent = 'Escribe al menos la conclusión.'; return; }
  let result;
  try { result = await api('/api/parse', {formulas, constants}); }
  catch { if (request === proofCheckRequest) $('prove-note').textContent = 'No se pudo consultar el analizador local.'; return; }
  if (request !== proofCheckRequest) return;
  list.replaceChildren();
  if (result.status !== 'ok') { list.append(node('li', result.errors?.[0]?.message || 'Entrada inválida.', 'bad')); button.disabled = true; return; }
  let errors = 0;
  result.results.forEach((entry, i) => {
    const item = node('li', undefined, entry.ok ? 'good' : 'bad');
    item.append(node('span', labels[i], 'syntax-label'));
    if (entry.ok) {
      item.append(node('code', entry.text));
      if (entry.free.length) item.append(node('span', `libre: ${entry.free.join(', ')}`, 'chip'));
    } else {
      errors++;
      const [start, end] = entry.error.span || [0, 0];
      const shown = node('code');
      shown.append(document.createTextNode(formulas[i].slice(0, start)), node('mark', formulas[i].slice(start, end) || '␣'), document.createTextNode(formulas[i].slice(end)));
      item.append(shown, node('span', entry.error.message, 'syntax-message'));
    }
    list.append(item);
  });
  button.disabled = errors > 0 || !conclusion;
  $('prove-note').textContent = errors ? `${errors === 1 ? 'Una fórmula tiene' : `${errors} fórmulas tienen`} error de sintaxis.`
    : !conclusion ? 'Falta la conclusión.'
    : result.mode === 'propositional' ? 'Sintaxis correcta · lógica proposicional: se decide con la tabla de verdad.' : 'Sintaxis correcta.';
}

/** Derivación en notación de Fitch: una barra por caja abierta y la hipótesis subrayada. */
function fitchElement(lines) {
  const list = node('ol', undefined, 'fitch');
  list.setAttribute('aria-label', 'Derivación en notación de Fitch');
  const lastPremise = lines.filter(line => line.rule === 'premise').at(-1)?.n;
  for (const line of lines) {
    const item = node('li', undefined, 'fitch-line');
    if (line.box_start) item.classList.add('box-start');
    if (line.rule === 'hyp' || line.rule === 'flag') item.classList.add('hyp');
    if (line.n === lastPremise) item.classList.add('last-premise');
    item.dataset.line = line.n;
    item.append(node('span', String(line.n), 'n'));
    const body = node('span', undefined, 'body');
    for (let i = 0; i < line.depth; i++) body.append(node('span', undefined, 'bar'));
    const content = node('span', undefined, 'content');
    if (line.flag) content.append(node('span', line.flag, 'flag'));
    if (line.formula) content.append(node('code', line.formula, 'f'));
    content.append(node('span', line.refs.length ? `${line.label} ${line.refs.join(', ')}` : line.label, 'why'));
    body.append(content); item.append(body); list.append(item);
  }
  return list;
}

/** Premisas verdaderas y conclusión falsa: lo que hace de un modelo un contramodelo. */
function truthList(premises, conclusion) {
  const list = node('ul', undefined, 'truth-list');
  premises.forEach((premise, i) => {
    const item = node('li'); item.append(node('span', 'V', 'truth'), node('code', premise.formula), node('span', `premisa ${i + 1}`, 'hint'));
    list.append(item);
  });
  const item = node('li'); item.append(node('span', 'F', 'truth false'), node('code', conclusion), node('span', 'conclusión', 'hint'));
  list.append(item);
  return list;
}

/** Valuación proposicional como una fila de la tabla de verdad. */
function valuationElement(valuation) {
  const table = node('table', undefined, 'valuation');
  const head = node('tr'), values = node('tr');
  for (const [letter, value] of valuation) {
    head.append(node('th', letter));
    values.append(node('td', value ? 'V' : 'F', value ? 'true' : 'false'));
  }
  table.append(head, values);
  return table;
}

/** Lleva un contramodelo de Demostrar al modo Evaluar: símbolos, tablas, conclusión y entorno. */
async function openInEvaluate(found) {
  setMode('evaluate');
  await applyPackage({signature: found.signature, formula: $('proof-conclusion').value.trim()}, found.model);
  for (const select of $('assignment').querySelectorAll('select[data-variable]')) {
    const pair = found.assignment.find(([name]) => name === select.dataset.variable);
    const index = pair ? domain.findIndex(item => sameValue(item, pair[1])) : -1;
    if (index >= 0) select.value = String(index);
  }
  refreshReady();
  setPane($('mode-evaluate'), 'question');
  toast('Contramodelo abierto en Evaluar con la conclusión: pulsa «Evaluar» para ver que es falsa.', 'success', 6000);
}

const PROOF_LIMITS = {depth: 'la profundidad', nodes: 'el número de nodos', timeout: 'el tiempo',
  too_many_atoms: 'el número de letras (más de 12)', too_many_atoms_for_kalmar: 'el tamaño del certificado de Kalmár'};

function contrastElement(contrast) {
  const box = node('div', undefined, `contrast ${contrast.verdict}`);
  const b = contrast.engine_b;
  const title = {consistent: 'Los dos motores coinciden', completeness_gap: 'El segundo motor sí la refuta',
    soundness_alarm: 'Los motores se contradicen', no_information: 'El segundo motor no decidió'}[contrast.verdict];
  box.append(node('strong', title), node('p', contrast.message, 'hint'));
  if (b.status === 'refuted') {
    const details = node('details');
    details.append(node('summary', `Refutación por resolución (${b.steps.length} cláusulas)`));
    const rule = {premise: 'premisa', negated_conclusion: 'conclusión negada', equality_axiom: 'axioma de igualdad', resolve: 'resolución', factor: 'factorización'};
    details.append(node('pre', b.steps.map(step =>
      `${String(step.id).padStart(2)}. ${step.clause}   (${rule[step.rule]}${step.parents.length ? ` ${step.parents.join(', ')}` : ''})`).join('\n'), 'model-json'));
    box.append(details);
  } else if (b.status === 'unknown') {
    box.append(node('p', `Resolución agotó sus límites (${b.reason}) tras ${b.kept} cláusulas.`, 'hint'));
  }
  return box;
}

async function proveFormula() {
  clearStory();
  const box = $('proof-result'); box.replaceChildren();
  const button = $('prove');
  await withBusy(button, 'Buscando…', async () => {
    try {
      const result = await api('/api/proof', proofInput());
      box.replaceChildren();
      if (result.status === 'invalid_input') {
        box.append(node('p', result.errors?.[0]?.message || 'Entrada inválida.', 'error')); return 'fail';
      }
      const logic = node('span', result.mode === 'propositional' ? 'Lógica proposicional' : 'Primer orden', 'chip logic');
      if (result.status === 'proved') {
        const how = result.method === 'kalmar' ? 'construidas con el lema de Kalmár' : 'de deducción natural';
        box.append(verdictElement('Demostrada', 'true', countLine('', result.fitch.length,
          ` ${result.fitch.length === 1 ? 'línea' : 'líneas'} ${how}, aceptadas por el verificador independiente.`, '', 'small')));
        const head = node('div', undefined, 'result-head'); head.append(node('h3', 'Derivación'), logic);
        box.append(head, fitchElement(result.fitch));
        if (result.contrast) box.append(contrastElement(result.contrast));
        showStory(result.story, null, box);
        return 'done';
      }
      if (result.status === 'refuted' && result.mode === 'propositional') {
        box.append(verdictElement('No se sigue', 'false', 'Esta valuación hace verdaderas las premisas y falsa la conclusión; la tabla de verdad lo confirma.'));
        const head = node('div', undefined, 'result-head'); head.append(node('h3', 'Valuación que lo refuta'), logic);
        box.append(head, valuationElement(result.valuation), truthList(result.premises, result.conclusion.formula));
        if (result.contrast) box.append(contrastElement(result.contrast));
        return 'done';
      }
      if (result.status === 'refuted') {
        const found = result.countermodel;
        box.append(verdictElement('No se sigue', 'false', countLine('Contramodelo verificado tras revisar ', found.explored,
          ` ${found.explored === 1 ? 'interpretación' : 'interpretaciones'}: las premisas son verdaderas y la conclusión, falsa.`, '', 'small')));
        const head = node('div', undefined, 'result-head'); head.append(node('h3', 'Contramodelo'), logic);
        box.append(head, modelElement(found.model, {assignment: found.assignment}), truthList(found.premises, found.explanation.formula));
        const open = node('button', 'Abrir en Evaluar', 'button secondary'); open.type = 'button';
        open.addEventListener('click', () => openInEvaluate(found));
        box.append(open);
        if (!found.loadable) {
          open.disabled = true;
          box.append(node('p', 'Este contramodelo tiene una relación vacía o una letra proposicional, y el modo Evaluar exige relaciones con al menos una tupla.', 'hint'));
        }
        box.append(node('h3', '¿Por qué falla la conclusión?'), explanationElement(found.explanation, true));
        if (result.contrast) box.append(contrastElement(result.contrast));
        showStory(found.story, found.model, box);
        return 'done';
      }
      const saturated = result.contrast?.engine_b.status === 'saturated';
      const limit = PROOF_LIMITS[result.reason] || 'los límites';
      const detail = saturated
        ? 'La resolución saturó sin contradicción, así que existe un modelo de las premisas donde la conclusión falla. No apareció entre los de 1 a 3 elementos: puede necesitar más, o ser infinito.'
        : result.reason === 'too_many_atoms_for_kalmar'
          ? 'La tabla de verdad no tiene ninguna fila con las premisas verdaderas y la conclusión falsa, así que la consecuencia vale; pero con más de 6 letras no se construye el certificado de Kalmár y la búsqueda no halló uno más corto.'
          : `No se encontró prueba dentro de ${limit}${result.search ? ', ni un contramodelo de hasta 3 elementos' : ''}. Eso no decide la consecuencia.`;
      box.append(verdictElement(saturated ? 'No se sigue' : 'Sin prueba', saturated ? 'false' : 'neutral', detail));
      if (result.contrast) box.append(contrastElement(result.contrast));
      return 'none';
    } catch (exc) { box.replaceChildren(node('p', exc.message || 'No se pudo buscar la prueba.', 'error')); return 'fail'; }
    finally { checkProofSyntax(); }
  });
}

// --- diccionario ---
const DICT_FEATURES = {N: [['M', 'Masculino'], ['F', 'Femenino'], ['C', 'Los dos']], NP: [['M', 'Masculino'], ['F', 'Femenino']],
  V: [['I', 'Sin objeto (duerme)'], ['T', 'Con objeto (admira a…)'], ['IT', 'Las dos (lee / lee un libro)']], ADJ: [['-', 'Se flexiona solo']]};
const DICT_FORMS = ['él/ella, presente', 'ellos, presente', 'él/ella, subjuntivo', 'ellos, subjuntivo', 'él/ella, pasado', 'ellos, pasado'];
let dictState = {category: '', offset: 0, request: 0};

function dictEntryRow(entry) {
  const row = node('tr');
  const word = node('td'); word.append(node('code', entry.lemma));
  if (entry.source === 'usuario') word.append(node('span', 'tuya', 'chip'));
  if (entry.source === 'auto') word.append(node('span', 'automática', 'chip'));
  const kind = node('td', undefined); kind.append(node('span', entry.category_label, `kind ${({N: 'predicate', ADJ: 'constant', V: 'function', NP: 'name'})[entry.category]}`));
  if (entry.feature_label) kind.append(node('span', entry.feature_label, 'hint'));
  if (entry.gloss) word.append(node('span', entry.gloss, 'hint gloss'));
  const remove = node('td');
  if (entry.source === 'usuario') {
    const button = node('button', 'Quitar', 'button secondary small'); button.type = 'button';
    button.addEventListener('click', async () => {
      await api('/api/lexicon/remove', {lemma: entry.lemma, category: entry.category});
      $('dict-note').textContent = `«${entry.lemma}» ya no está en tu diccionario.`; searchDictionary(true);
    });
    remove.append(button);
  }
  row.append(word, kind, node('td', entry.forms.join(' · '), 'dict-forms'), node('td'), remove);
  row.children[3].append(node('code', entry.symbol));
  return row;
}

async function searchDictionary(reset) {
  const request = ++dictState.request;
  if (reset) dictState.offset = 0;
  const result = await api('/api/lexicon/search', {query: $('dict-query').value, category: dictState.category, offset: dictState.offset});
  if (request !== dictState.request || result.status !== 'ok') return;
  const body = $('dict-results'); if (reset) body.replaceChildren();
  result.entries.forEach(entry => body.append(dictEntryRow(entry)));
  if (!result.total) { const row = node('tr'); const cell = node('td', 'No está en el diccionario. Añádela a la derecha.', 'hint'); cell.colSpan = 5; row.append(cell); body.append(row); }
  dictState.offset += result.entries.length;
  $('dict-more').hidden = dictState.offset >= result.total;
  const c = result.counts, counts = $('dict-counts');
  if (counts.dataset.total !== String(c.total)) {  // el total sube al entrar; después solo cambia el texto
    counts.dataset.total = c.total;
    counts.replaceChildren(countUp(node('strong', undefined, 'count'), c.total),
      document.createTextNode(` palabras: ${c.by_category.N} sustantivos, ${c.by_category.ADJ} adjetivos, ${c.by_category.V} verbos y ${c.by_category.NP} nombres. ` +
        (c.auto ? `${c.auto} se deducen solas (diminutivos y participios). ` : '') +
        (c.user ? `${plural(c.user, 'añadida', 'añadidas')} por ti.` : 'Ninguna añadida por ti todavía.')));
  }
  if (reset && $('dict-query').value.trim()) $('dict-note').textContent = `${plural(result.total, 'coincidencia', 'coincidencias')}.`;
  else if (reset) $('dict-note').textContent = '';
}

function dictFields() {
  const forms = [...$('dict-irregular').querySelectorAll('input[data-form]')].map(i => i.value.trim());
  const plural = $('dict-irregular').querySelector('input[data-plural]')?.value.trim();
  let extra = '';
  if ($('dict-category').value === 'V' && forms.some(Boolean)) extra = `formas=${forms.join(',')}`;
  else if (plural) extra = `pl=${plural}`;
  // significado: sinónimo de otra palabra (comparte su símbolo) o un sentido propio (símbolo aparte)
  const synonym = $('dict-synonym').value.trim().toLowerCase(), sense = $('dict-sense').value.trim().toLowerCase();
  const meaning = synonym ? `sin=${synonym}` : sense ? `sentido=${sense}` : '';
  if (meaning) extra = extra ? `${extra};${meaning}` : meaning;
  return {lemma: $('dict-lemma').value.trim(), category: $('dict-category').value, feature: $('dict-feature').value, extra};
}

function dictSetCategory(category, feature) {
  $('dict-category').value = category;
  const select = $('dict-feature'); select.replaceChildren();
  for (const [value, label] of DICT_FEATURES[category]) { const o = node('option', label); o.value = value; select.append(o); }
  if (feature && DICT_FEATURES[category].some(([v]) => v === feature)) select.value = feature;
  $('dict-feature-label').textContent = category === 'V' ? '¿Lleva objeto?' : category === 'ADJ' ? 'Flexión' : 'Género';
  select.disabled = category === 'ADJ';
  const box = $('dict-irregular'); box.replaceChildren();
  if (category === 'V') {
    box.append(node('p', 'Llena las seis formas solo si el verbo no sigue la conjugación regular.', 'hint'));
    const grid = node('div', undefined, 'dict-fields');
    DICT_FORMS.forEach(label => { const cell = node('div'); const input = node('input'); input.className = 'formal'; input.dataset.form = '1'; input.setAttribute('aria-label', label); input.placeholder = label; input.addEventListener('input', dictPreview); cell.append(input); grid.append(cell); });
    box.append(grid);
  } else if (category !== 'NP') {
    const label = node('label', 'Plural, si es irregular'); const input = node('input'); input.className = 'formal'; input.dataset.plural = '1'; input.placeholder = 'jóvenes';
    input.addEventListener('input', dictPreview); label.append(input); box.append(label);
  } else box.append(node('p', 'Los nombres propios no se flexionan.', 'hint'));
}

let dictPreviewRequest = 0;
async function dictPreview() {
  const request = ++dictPreviewRequest;
  const result = await api('/api/lexicon/preview', dictFields());
  if (request !== dictPreviewRequest) return;
  const error = $('dict-error');
  if (result.status !== 'ok') { error.textContent = result.errors?.[0]?.message || 'Datos inválidos.'; error.hidden = false; $('dict-preview').textContent = ''; $('dict-save').disabled = true; return; }
  error.hidden = true; $('dict-save').disabled = false;
  $('dict-preview').replaceChildren(node('span', result.entry.forms.join(' · ')), node('span', ' → símbolo ', 'hint'), node('code', result.entry.symbol));
}

async function dictConsult() {
  const word = $('dict-word').value.trim();
  const note = $('dict-proposal'); $('dict-form').hidden = true;
  setPane($('mode-dictionary'), 'question');
  if (!word) { note.textContent = 'Escribe una palabra.'; return; }
  const result = await api('/api/lexicon/suggest', {word});
  if (result.status !== 'ok') { note.textContent = result.errors?.[0]?.message || 'Palabra inválida.'; return; }
  if (result.found.length) {
    const e = result.found[0];
    note.textContent = `Ya está: «${e.lemma}», ${e.category_label}${e.feature_label ? ' ' + e.feature_label : ''}. Símbolo ${e.symbol}.`;
    $('dict-query').value = word; searchDictionary(true); return;
  }
  const p = result.proposal || {lemma: word.toLowerCase(), category: 'N', feature: 'M'};
  note.textContent = result.proposal ? `No está. El modelo cree que es ${p.label} (${Math.round(p.probability * 100)} %). Revisa y corrige:` : 'No está. Indica qué es:';
  $('dict-lemma').value = p.lemma; dictSetCategory(p.category, p.feature);
  $('dict-form').hidden = false; dictPreview();
}

async function dictSave() {
  await withBusy($('dict-save'), 'Guardando…', async () => {
    const result = await api('/api/lexicon/add', dictFields());
    if (result.status !== 'ok') { $('dict-error').textContent = result.errors?.[0]?.message || 'No se pudo guardar.'; $('dict-error').hidden = false; return 'fail'; }
    $('dict-form').hidden = true; $('dict-word').value = ''; $('dict-synonym').value = ''; $('dict-sense').value = '';
    $('dict-proposal').textContent = `«${result.entry.lemma}» guardada. Ya puedes usarla en una frase.`;
    toast(`«${result.entry.lemma}» quedó en tu diccionario.`, 'success');
    $('dict-query').value = result.entry.lemma; searchDictionary(true);
    return 'done';
  });
}

function openDictionaryWith(word) { setMode('dictionary'); $('dict-word').value = word; dictConsult(); }

for (const [value, label] of [['', 'Todas'], ['N', 'Sustantivos'], ['ADJ', 'Adjetivos'], ['V', 'Verbos'], ['NP', 'Nombres']]) {
  const chip = node('button', label, 'filter'); chip.type = 'button'; chip.setAttribute('aria-pressed', String(value === ''));
  chip.addEventListener('click', () => {
    dictState.category = value;
    for (const other of $('dict-filters').querySelectorAll('.filter')) other.setAttribute('aria-pressed', String(other === chip));
    placePill($('dict-filters'));
    searchDictionary(true);
  });
  $('dict-filters').append(chip);
}
{
  const pill = node('span', undefined, 'pill'); pill.setAttribute('aria-hidden', 'true');
  $('dict-filters').prepend(pill);
}
let dictTimer = null;
$('dict-query').addEventListener('input', () => { clearTimeout(dictTimer); dictTimer = setTimeout(() => searchDictionary(true), 180); });
$('dict-more').addEventListener('click', () => searchDictionary(false));
$('dict-check').addEventListener('click', dictConsult);
$('dict-word').addEventListener('keydown', event => { if (event.key === 'Enter') dictConsult(); });
$('dict-category').addEventListener('change', () => { dictSetCategory($('dict-category').value); dictPreview(); });
for (const id of ['dict-lemma', 'dict-feature', 'dict-synonym', 'dict-sense']) $(id).addEventListener('input', dictPreview);
$('dict-save').addEventListener('click', dictSave);

// --- modos ---
const MODES = ['evaluate', 'prove', 'dictionary'];
function setMode(mode) {
  const changed = document.body.dataset.mode !== mode;
  document.body.dataset.mode = mode;
  for (const name of MODES) {
    const active = name === mode;
    $(`mode-${name}`).hidden = !active;
    $(`tab-${name}`).setAttribute('aria-selected', String(active));
    $(`tab-${name}`).tabIndex = active ? 0 : -1;
  }
  placePill(document.querySelector('.modes'));
  pillHosts().forEach(placePill);
  clearStory(); $('story-section').hidden = true;
  if (mode === 'prove') checkProofSyntax();
  if (mode === 'dictionary') searchDictionary(true);
  if (changed && phoneLayout()) window.scrollTo({top: 0, behavior: 'auto'});
}

/** Teléfono: cada modo de dos paneles se recorre en dos pestañas («1 · Modelo», «2 · Fórmula»). */
function setPane(workspace, pane) {
  workspace.dataset.pane = pane;
  for (const tab of workspace.querySelectorAll(':scope > .subtabs .subtab')) {
    const active = tab.id.endsWith(pane);
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
  }
  placePill(workspace.querySelector(':scope > .subtabs'));
}
for (const workspace of [$('mode-evaluate'), $('mode-dictionary')]) {
  const tabs = [...workspace.querySelectorAll(':scope > .subtabs .subtab')];
  tabs.forEach(tab => tab.addEventListener('click', () => {
    setPane(workspace, tab.id.endsWith('question') ? 'question' : 'model');
    if (phoneLayout()) workspace.scrollIntoView({behavior: 'auto', block: 'start'});
  }));
  workspace.querySelector(':scope > .subtabs').addEventListener('keydown', event => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    const next = workspace.dataset.pane === 'model' ? 'question' : 'model';
    setPane(workspace, next); tabs.find(tab => tab.id.endsWith(next)).focus();
  });
}
$('go-question').addEventListener('click', () => { setPane($('mode-evaluate'), 'question'); $('mode-evaluate').scrollIntoView({block: 'start'}); });
for (const name of MODES) $(`tab-${name}`).addEventListener('click', () => setMode(name));
document.querySelector('.modes').addEventListener('keydown', event => {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
  const at = MODES.indexOf(document.body.dataset.mode);
  const next = MODES[(at + (event.key === 'ArrowRight' ? 1 : MODES.length - 1)) % MODES.length];
  setMode(next); $(`tab-${next}`).focus();
});
$('story-close').addEventListener('click', () => {
  pauseStory(); exitStoryFullscreen(); $('story-section').hidden = true;
  document.querySelectorAll('.fitch li.current').forEach(li => li.classList.remove('current'));
});

$('add-symbol').addEventListener('click', () => { addSymbol(); invalidateTables(); });
$('prepare').addEventListener('click', prepare);
$('domain').addEventListener('input', invalidateTables);
$('sample').addEventListener('click', () => ({evaluate: loadSample, prove: loadProofSample, dictionary: loadDictionarySample})[document.body.dataset.mode]());
$('evaluate').addEventListener('click', evaluateFormula);
$('export-json').addEventListener('click', exportJSON);
$('import-json').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', event => loadFile(event.target.files[0]));
// soltar un archivo en cualquier parte de la página también lo carga
document.addEventListener('dragover', event => { if (event.dataTransfer?.types.includes('Files')) { event.preventDefault(); document.body.classList.add('dropping'); } });
document.addEventListener('dragleave', event => { if (!event.relatedTarget) document.body.classList.remove('dropping'); });
document.addEventListener('drop', event => { if (!event.dataTransfer?.files.length) return; event.preventDefault(); document.body.classList.remove('dropping'); loadFile(event.dataTransfer.files[0]); });
$('find-countermodel').addEventListener('click', searchCountermodel);
$('translate-spanish').addEventListener('click', showSpanishReadings);
$('record-spanish').addEventListener('click', recordSpanish);
$('stop-spanish').addEventListener('click', stopSpanishRecording);
$('prove').addEventListener('click', proveFormula);
for (const id of ['proof-premises', 'proof-conclusion', 'proof-constants']) {
  $(id).addEventListener('input', () => { clearStory(); $('proof-result').replaceChildren(); scheduleProofCheck(); });
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
function buildKeyboard(container, target) {
  for (const symbol of ['¬', '∧', '∨', '→', '↔', '∀', '∃', '(', ')', '=', '≠', '⊥']) {
    const button = node('button', symbol, 'key'); button.type = 'button'; button.setAttribute('aria-label', `Insertar ${symbol}`);
    button.addEventListener('mousedown', event => event.preventDefault());  // no robar el foco al campo
    button.addEventListener('click', () => {
      const field = target();
      field.setRangeText(symbol, field.selectionStart, field.selectionEnd, 'end'); field.focus();
      field.dispatchEvent(new Event('input'));
    });
    container.append(button);
  }
}
buildKeyboard($('symbols-keyboard'), () => formulaBox);
let proofField = $('proof-premises');
for (const id of ['proof-premises', 'proof-conclusion']) $(id).addEventListener('focus', () => { proofField = $(id); });
buildKeyboard($('proof-keyboard'), () => proofField);

/** Teléfono: mientras se escribe una fórmula, el teclado lógico queda pegado encima del teclado del sistema. */
function floatKeyboard(keyboard, fields) {
  const narrow = window.matchMedia('(max-width: 720px)');
  const touch = {get matches() { return narrow.matches && (matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0); }};
  let active = null;
  const place = () => {
    if (!active) return;
    const view = window.visualViewport;
    const covered = view ? window.innerHeight - (view.height + view.offsetTop) : 0;
    keyboard.style.setProperty('--kb-bottom', `${Math.max(0, Math.round(covered))}px`);
  };
  for (const field of fields) {
    field.addEventListener('focus', () => {
      if (!touch.matches) return;
      active = field; keyboard.classList.add('floating'); document.body.classList.add('keyboard-open'); place();
    });
    field.addEventListener('blur', () => setTimeout(() => {
      if (fields.includes(document.activeElement)) return;
      active = null; keyboard.classList.remove('floating'); document.body.classList.remove('keyboard-open');
    }, 120));
  }
  window.visualViewport?.addEventListener('resize', place);
  window.visualViewport?.addEventListener('scroll', place);
}
floatKeyboard($('symbols-keyboard'), [formulaBox]);
floatKeyboard($('proof-keyboard'), [$('proof-premises'), $('proof-conclusion')]);

// ── Paso a paso en pantalla completa ──
// Va la sección entera (escena, texto del paso y controles), útil para proyectar. Con la API nativa cuando existe;
// el iPhone no la ofrece para estos elementos, así que ahí la sección cubre la ventana (respaldo).
function storyFullscreenElement() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
function storyIsFullscreen() { return $('story-section').classList.contains('is-fullscreen'); }
function syncStoryFullscreen() {
  const section = $('story-section'), fallback = section.classList.contains('story-fallback-fullscreen');
  const on = fallback || storyFullscreenElement() === section;
  section.classList.toggle('is-fullscreen', on);
  document.documentElement.classList.toggle('story-locked', fallback);
  if (!on) try { screen.orientation?.unlock?.(); } catch { /* sin bloqueo que soltar */ }
  const button = $('story-fullscreen'), label = on ? 'Salir de pantalla completa' : 'Pantalla completa';
  button.setAttribute('aria-pressed', String(on)); button.setAttribute('aria-label', label); button.title = label;
}
async function enterStoryFullscreen() {
  const section = $('story-section');
  const request = section.requestFullscreen || section.webkitRequestFullscreen;
  if (request && (document.fullscreenEnabled ?? document.webkitFullscreenEnabled ?? true)) {
    try {
      await request.call(section, {navigationUI: 'hide'});
      // teléfono en vertical: como los reproductores de video, se gira a horizontal si el sistema lo permite (Android)
      if (matchMedia('(pointer: coarse) and (orientation: portrait)').matches) screen.orientation?.lock?.('landscape')?.catch?.(() => {});
      return;
    } catch { /* sin permiso o sin soporte: respaldo */ }
  }
  section.classList.add('story-fallback-fullscreen'); syncStoryFullscreen();
}
function exitStoryFullscreen() {
  const section = $('story-section');
  if (section.classList.contains('story-fallback-fullscreen')) { section.classList.remove('story-fallback-fullscreen'); syncStoryFullscreen(); return; }
  if (storyFullscreenElement()) (document.exitFullscreen ? document.exitFullscreen() : document.webkitExitFullscreen?.())?.catch?.(() => {});
}
$('story-fullscreen').addEventListener('click', () => (storyIsFullscreen() ? exitStoryFullscreen() : enterStoryFullscreen()));
document.addEventListener('fullscreenchange', syncStoryFullscreen);
document.addEventListener('webkitfullscreenchange', syncStoryFullscreen);
document.addEventListener('keydown', event => {
  if (!storyIsFullscreen() || event.target.closest?.('input, textarea, select')) return;
  if (event.key === 'Escape') exitStoryFullscreen();          // la nativa ya sale sola; esto cubre el respaldo
  else if (event.key === 'ArrowRight') { event.preventDefault(); $('story-next').click(); }
  else if (event.key === 'ArrowLeft') { event.preventDefault(); $('story-prev').click(); }
});

// Paso a paso: en el teléfono se cambia de paso deslizando sobre la escena.
{
  let start = null;
  const stage = document.querySelector('.story-stage');
  stage.addEventListener('pointerdown', event => { start = {x: event.clientX, y: event.clientY}; });
  stage.addEventListener('pointerup', event => {
    if (!start || !storyState) return;
    const dx = event.clientX - start.x, dy = event.clientY - start.y;
    start = null;
    if (Math.abs(dx) < 56 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    $(dx < 0 ? 'story-next' : 'story-prev').click();
  });
}

if ('speechSynthesis' in window) window.speechSynthesis.addEventListener?.('voiceschanged', refreshVoiceOption);
refreshVoiceOption();
pillHosts().forEach(host => { pillObserver.observe(host); placePill(host); });
document.fonts?.ready.then(() => pillHosts().forEach(placePill));
addSymbol('P', 'predicate', 1);
prepare();
$('story-pause').disabled = true;

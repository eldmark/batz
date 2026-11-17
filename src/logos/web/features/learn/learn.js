// «Aprender»: historia de la lógica (línea de tiempo) y tarjetas de teoría. Módulo nativo, sin dependencias.
import {HISTORY, HISTORY_TOPICS, CARDS, CARD_TOPICS} from '/features/learn/data.js';
import {filterCards, buildQueue, loadProgress, saveProgress, clearProgress, mark, statusOf, summary, step} from '/features/learn/deck.js';

const STATUS_TEXT = {known: 'La sabía', review: 'Por repasar', pending: 'Sin marcar'};
const topicLabel = (list, id) => list.find(topic => topic.id === id)?.label ?? '';

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === false || value == null) continue;
    if (key === 'class') el.className = value; else if (key === 'text') el.textContent = value; else el.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat()) if (child != null) el.append(child);
  return el;
}
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

function pressedGroup(label, options, current, onPick) {
  const wrap = h('div', {class: 'filters learn-filters', role: 'group', 'aria-label': label});
  const buttons = options.map(option => {
    const b = h('button', {class: 'filter', type: 'button', 'aria-pressed': String(option.id === current), 'data-id': option.id, text: option.label});
    b.addEventListener('click', () => { buttons.forEach(x => x.setAttribute('aria-pressed', String(x === b))); onPick(option.id); });
    return b;
  });
  wrap.append(...buttons);
  return wrap;
}

// ───────── Historia ─────────
function buildHistory() {
  const section = h('section', {class: 'learn-block', id: 'learn-history', 'aria-labelledby': 'learn-history-title'});
  const title = h('h3', {id: 'learn-history-title', tabindex: '-1', text: 'Historia de la lógica matemática y de predicados'});
  const status = h('p', {class: 'hint learn-count', role: 'status'});
  const list = h('ol', {class: 'timeline'});
  const items = HISTORY.map(item => {
    const where = h('p', {class: 'tl-where'}, h('strong', {text: 'Dónde lo ves en Batz. '}), item.where);
    if (item.href) where.append(' ', h('a', {href: item.href, text: `${item.link} →`}));
    const details = h('details', {class: 'tl-card'},
      h('summary', {}, h('span', {class: 'tl-year', text: item.year}), h('span', {class: 'tl-name', text: item.title}), h('span', {class: 'tl-people', text: item.people})),
      h('div', {class: 'tl-body'}, h('p', {text: item.what}), where));
    const li = h('li', {class: 'tl-item', 'data-topic': item.topic}, h('span', {class: 'tl-node', 'aria-hidden': 'true'}), details);
    list.append(li);
    return {li, details};
  });
  let topic = 'todos';
  const apply = () => {
    let shown = 0;
    HISTORY.forEach((item, i) => { const visible = topic === 'todos' || item.topic === topic; items[i].li.hidden = !visible; if (visible) shown++; });
    status.textContent = `Se muestran ${shown} de ${HISTORY.length} hitos, en orden cronológico.`;
  };
  const filters = pressedGroup('Filtrar la historia por tema', [{id: 'todos', label: 'Todos'}, ...HISTORY_TOPICS], topic, id => { topic = id; apply(); });
  const open = h('button', {class: 'button secondary small', type: 'button', text: 'Abrir todos'});
  const close = h('button', {class: 'button secondary small', type: 'button', text: 'Cerrar todos'});
  const setAll = value => items.forEach(({li, details}) => { if (!li.hidden) details.open = value; });
  open.addEventListener('click', () => setAll(true));
  close.addEventListener('click', () => setAll(false));
  section.append(title,
    h('p', {class: 'pane-lede', text: 'Una línea de hilo con un nudo por cada hito. Abre cada nudo para ver qué aportó y dónde lo ves en Batz. Las fechas son las de la publicación original.'}),
    filters, h('div', {class: 'actions learn-actions'}, open, close), status, list);
  apply();
  return {section, title};
}

// ───────── Tarjetas ─────────
function buildCards(storage) {
  const state = {mode: 'explore', topic: 'todos', onlyOpen: true, queue: [], pos: 0, flipped: false, done: false, progress: loadProgress(storage, CARDS), saved: true};
  const section = h('section', {class: 'learn-block', id: 'learn-cards', 'aria-labelledby': 'learn-cards-title'});
  const title = h('h3', {id: 'learn-cards-title', tabindex: '-1', text: 'Conceptos como tarjetas'});

  const el = {
    stage: h('div', {class: 'fc-stage', role: 'group', 'aria-label': 'Tarjeta de estudio'}),
    status: h('p', {class: 'fc-status', 'aria-live': 'polite'}),
    card: h('div', {class: 'fc-card'}),
    tag: h('span', {class: 'fc-tag'}), front: h('p', {class: 'fc-text'}), back: h('p', {class: 'fc-text'}), example: h('p', {class: 'fc-example'}),
    progress: h('p', {class: 'fc-progress'}), bar: h('div', {class: 'fc-bar', role: 'img'}), barKnown: h('span', {class: 'fc-bar-known'}), barReview: h('span', {class: 'fc-bar-review'}),
    note: h('p', {class: 'hint', role: 'status'}), list: h('dl', {class: 'fc-list'}), listSummary: h('summary'),
  };
  el.bar.append(el.barKnown, el.barReview);
  const frontFace = h('div', {class: 'fc-face fc-front'}, h('span', {class: 'fc-side', text: 'Pregunta'}), el.tag, el.front);
  const backFace = h('div', {class: 'fc-face fc-back'}, h('span', {class: 'fc-side', text: 'Respuesta'}), el.back, el.example);
  el.card.append(h('div', {class: 'fc-inner'}, frontFace, backFace));

  const prev = h('button', {class: 'button secondary', type: 'button', text: 'Anterior'});
  const flip = h('button', {class: 'button primary fc-flip', type: 'button', 'aria-pressed': 'false', text: 'Voltear tarjeta'});
  const next = h('button', {class: 'button secondary', type: 'button', text: 'Siguiente'});
  const known = h('button', {class: 'button secondary', type: 'button', text: 'La sabía'});
  const review = h('button', {class: 'button secondary', type: 'button', text: 'Repasar'});
  const marks = h('div', {class: 'fc-marks'}, known, review);
  const done = h('div', {class: 'fc-done', hidden: true});
  el.stage.append(el.status, el.card, h('div', {class: 'actions fc-actions'}, prev, flip, next), marks);

  const current = () => state.queue[state.pos];
  const save = () => { state.saved = saveProgress(storage, state.progress); };

  function rebuild() {
    state.queue = state.mode === 'study' ? buildQueue(CARDS, state.progress, {topic: state.topic, onlyOpen: state.onlyOpen}) : filterCards(CARDS, state.topic);
    state.pos = 0; state.flipped = false; state.done = state.mode === 'study' && !state.queue.length;
    render({instant: true});
  }
  function render({instant = false} = {}) {
    const total = filterCards(CARDS, state.topic);
    const s = summary(total, state.progress);
    el.progress.textContent = `En este tema: ${s.known} sabidas, ${s.review} por repasar, ${s.pending} sin marcar, de ${s.total}.`;
    el.bar.setAttribute('aria-label', el.progress.textContent);
    el.barKnown.style.width = `${s.total ? (100 * s.known) / s.total : 0}%`;
    el.barReview.style.width = `${s.total ? (100 * s.review) / s.total : 0}%`;
    el.note.textContent = state.saved ? '' : 'No se pudo guardar el progreso en este navegador; se conserva mientras esta página siga abierta.';
    renderList();
    const study = state.mode === 'study';
    el.stage.hidden = state.done; done.hidden = !state.done; marks.hidden = !study;
    if (state.done) { renderDone(); return; }
    const card = current();
    if (!card) { el.stage.hidden = true; return; }
    if (instant) el.card.classList.add('no-anim');
    el.card.dataset.flipped = String(state.flipped);
    el.tag.textContent = topicLabel(CARD_TOPICS, card.topic);
    el.front.textContent = card.front; el.back.textContent = card.back; el.example.textContent = `Ejemplo: ${card.example}`;
    frontFace.inert = state.flipped; backFace.inert = !state.flipped;
    frontFace.setAttribute('aria-hidden', String(state.flipped)); backFace.setAttribute('aria-hidden', String(!state.flipped));
    flip.setAttribute('aria-pressed', String(state.flipped));
    el.status.textContent = `Tarjeta ${state.pos + 1} de ${state.queue.length} · ${topicLabel(CARD_TOPICS, card.topic)} · ${STATUS_TEXT[statusOf(state.progress, card.id)]}`;
    known.disabled = review.disabled = !state.flipped;
    prev.disabled = study && state.pos === 0;
    next.textContent = study && state.pos === state.queue.length - 1 ? 'Terminar ronda' : 'Siguiente';
    if (instant) requestAnimationFrame(() => requestAnimationFrame(() => el.card.classList.remove('no-anim')));
  }
  function renderList() {
    const cards = filterCards(CARDS, state.topic);
    el.listSummary.textContent = `Ver las ${cards.length} tarjetas como texto`;
    el.list.replaceChildren(...cards.flatMap(card => [
      h('dt', {text: card.front}),
      h('dd', {}, card.back, h('span', {class: 'fc-list-ex', text: ` Ejemplo: ${card.example}`}), h('span', {class: 'fc-list-st', text: STATUS_TEXT[statusOf(state.progress, card.id)]})),
    ]));
  }
  function renderDone() {
    const left = filterCards(CARDS, state.topic).filter(card => statusOf(state.progress, card.id) !== 'known').length;
    const ran = state.queue.length;
    const heading = h('p', {class: 'fc-done-title', tabindex: '-1', text: ran ? 'Ronda terminada' : 'No queda nada pendiente en este tema'});
    const back = h('button', {class: 'button secondary', type: 'button', text: 'Volver a explorar'});
    back.addEventListener('click', () => setMode('explore'));
    const text = ran
      ? `Pasaste por ${ran} tarjetas. ${left ? `Aún quedan ${left} sin saber en este tema.` : 'Ya sabes todas las de este tema.'}`
      : 'Todas las tarjetas de este tema están marcadas como sabidas. Puedes reiniciar el progreso o recorrerlas con «Explorar».';
    const actions = h('div', {class: 'actions'});
    if (left) {
      const again = h('button', {class: 'button primary', type: 'button', text: 'Nueva ronda'});
      again.addEventListener('click', () => { state.onlyOpen = true; opt.checked = true; rebuild(); });
      actions.append(again);
    }
    actions.append(back);
    done.replaceChildren(heading, h('p', {text}), actions);
    heading.focus({preventScroll: true});
  }

  function go(delta) {
    if (state.done || !state.queue.length) return;
    if (state.mode === 'study') {
      const to = state.pos + delta;
      if (to >= state.queue.length) { state.done = true; render(); return; }
      state.pos = Math.max(0, to);
    } else state.pos = step(state.pos, state.queue.length, delta);
    state.flipped = false;
    render({instant: true});
  }
  function toggle() { if (state.done) return; state.flipped = !state.flipped; render(); }
  function choose(status) {
    const card = current(); if (!card || !state.flipped) return;
    state.progress = mark(state.progress, card.id, status); save();
    go(1);
  }
  prev.addEventListener('click', () => go(-1));
  next.addEventListener('click', () => go(1));
  flip.addEventListener('click', toggle);
  el.card.addEventListener('click', event => { if (!event.target.closest('a, button')) toggle(); });
  known.addEventListener('click', () => choose('known'));
  review.addEventListener('click', () => choose('review'));
  el.stage.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); go(1); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); go(-1); }
  });

  // controles
  const topics = pressedGroup('Filtrar las tarjetas por tema', [{id: 'todos', label: 'Todas'}, ...CARD_TOPICS], state.topic, id => { state.topic = id; rebuild(); });
  const modeBtns = [['explore', 'Explorar'], ['study', 'Estudiar']].map(([id, label]) => h('button', {class: 'filter', type: 'button', 'aria-pressed': String(id === state.mode), 'data-id': id, text: label}));
  const modeGroup = h('div', {class: 'filters learn-filters', role: 'group', 'aria-label': 'Modo de las tarjetas'}, ...modeBtns);
  function setMode(mode) { state.mode = mode; modeBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === mode))); optWrap.hidden = mode !== 'study'; if (mode === 'study') state.onlyOpen = opt.checked; rebuild(); }
  modeBtns.forEach(b => b.addEventListener('click', () => setMode(b.dataset.id)));
  const opt = h('input', {type: 'checkbox', id: 'fc-only-open', checked: true});
  const optWrap = h('label', {class: 'fc-opt', for: 'fc-only-open', hidden: true}, opt, ' Omitir las que ya sé');
  opt.addEventListener('change', () => { state.onlyOpen = opt.checked; rebuild(); });
  const reset = h('button', {class: 'button secondary small', type: 'button', text: 'Reiniciar progreso'});
  let resetTimer = 0;
  const disarm = () => { clearTimeout(resetTimer); reset.textContent = 'Reiniciar progreso'; reset.dataset.armed = ''; };
  reset.addEventListener('click', () => {
    if (reset.dataset.armed !== 'yes') { reset.dataset.armed = 'yes'; reset.textContent = 'Confirmar: borrar mi progreso'; resetTimer = setTimeout(disarm, 5000); return; }
    disarm(); state.progress = {known: [], review: []}; state.saved = clearProgress(storage); rebuild();
  });
  reset.addEventListener('blur', disarm);

  const all = h('details', {class: 'fc-all'}, el.listSummary, el.list);
  section.append(title,
    h('p', {class: 'pane-lede', text: 'Teoría en tarjetas: la pregunta al frente y la respuesta, con un ejemplo, al reverso. «Explorar» las recorre en orden; «Estudiar» las baraja y te deja marcar cuáles sabías y cuáles repasar.'}),
    topics, h('div', {class: 'learn-toolbar'}, modeGroup, optWrap),
    el.stage, done,
    h('div', {class: 'fc-meter'}, el.progress, el.bar, h('div', {class: 'actions learn-actions'}, reset), el.note),
    all);
  rebuild();
  return {section, title};
}

export function initLearn(root, {storage = (() => { try { return localStorage; } catch { return null; } })()} = {}) {
  if (!root || root.dataset.ready) return;
  root.dataset.ready = 'yes';
  const history = buildHistory(), cards = buildCards(storage);
  const jump = (target) => () => { target.section.scrollIntoView({behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start'}); target.title.focus({preventScroll: true}); };
  const toHistory = h('button', {class: 'button secondary small', type: 'button', text: 'Historia de la lógica'});
  const toCards = h('button', {class: 'button secondary small', type: 'button', text: 'Conceptos como tarjetas'});
  toHistory.addEventListener('click', jump(history)); toCards.addEventListener('click', jump(cards));
  root.append(
    h('header', {class: 'learn-head'},
      h('h2', {class: 'pane-title', text: 'Aprender'}),
      h('p', {class: 'pane-lede', text: 'Dos formas de repasar la teoría que Batz aplica: cómo se llegó a la lógica de predicados y las ideas clave en tarjetas.'}),
      h('div', {class: 'actions learn-actions', role: 'group', 'aria-label': 'Ir a una parte de la página'}, toHistory, toCards)),
    history.section, cards.section);
}

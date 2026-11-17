// «Aprender»: historia de la lógica (línea de tiempo) y tarjetas de teoría. Módulo nativo, sin dependencias.
import {HISTORY, HISTORY_TOPICS, CARDS, CARD_TOPICS} from '/features/learn/data.js';
import {person, initials, lifespan} from '/features/people/people.js';
import {visibleMilestones, clampIndex, stepIndex, neighbors, isFirst, isLast, indexAfterFilter, nearestIndex, swipeDelta, trackYear, peopleOf, needsVisibleCredit, announce} from '/features/learn/timeline.js';
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

// ───────── Historia: línea del tiempo (un hito grande, con el anterior y el siguiente) ─────────
function portrait(p) {
  const mono = () => h('span', {class: 'tl-mono', 'aria-hidden': 'true', text: initials(p.slug)});
  if (!p.image) return mono();
  const img = h('img', {class: 'tl-photo', src: p.image, alt: '', width: '56', height: '56', loading: 'lazy', decoding: 'async'});
  img.addEventListener('error', () => img.replaceWith(mono()), {once: true});
  return img;
}
function personItem(p) {
  const info = h('span', {class: 'tl-who'}, h('span', {class: 'tl-pname', text: p.name}), h('span', {class: 'tl-life', text: lifespan(p.slug)}));
  const li = h('li', {class: 'tl-person', 'data-slug': p.slug}, h('span', {class: 'tl-face', title: p.image ? p.credit : 'Sin retrato con licencia verificada'}, portrait(p)), info);
  if (needsVisibleCredit(p)) info.append(h('a', {class: 'tl-credit', href: p.creditUrl, target: '_blank', rel: 'noopener noreferrer', text: `Foto: ${p.credit}`}));
  return li;
}

function buildHistory() {
  const section = h('section', {class: 'learn-block tl2-block', id: 'learn-history', 'aria-labelledby': 'learn-history-title'});
  const title = h('h3', {id: 'learn-history-title', tabindex: '-1', text: 'Historia de la lógica matemática y de predicados'});
  const count = h('p', {class: 'hint learn-count'});
  const live = h('p', {class: 'sr-only', role: 'status', 'aria-live': 'polite'});
  const state = {topic: 'todos', list: visibleMilestones(HISTORY, 'todos'), index: 0};
  let onFinish = () => {};

  const nodesList = h('ol', {class: 'tl2-nodes'});
  const track = h('div', {class: 'tl2-track', role: 'group', 'aria-label': 'Línea del tiempo: elige un hito'}, nodesList);
  const cardBody = h('div', {class: 'tl2-body'});
  const card = h('article', {class: 'tl2-card tl2-main', 'aria-label': 'Hito elegido'}, cardBody);
  const sidePrev = h('button', {class: 'tl2-side tl2-prev', type: 'button'});
  const sideNext = h('button', {class: 'tl2-side tl2-next', type: 'button'});
  const stage = h('div', {class: 'tl2-stage'}, sidePrev, card, sideNext);
  const prev = h('button', {class: 'button secondary', type: 'button', text: 'Anterior'});
  const next = h('button', {class: 'button secondary', type: 'button', text: 'Siguiente'});
  const pos = h('span', {class: 'tl2-pos'});
  const controls = h('div', {class: 'actions tl2-controls'}, prev, pos, next);
  const finishText = h('p', {class: 'tl2-finish-text'});
  const finishBtn = h('button', {class: 'button primary', type: 'button', text: 'Repasar con las tarjetas'});
  const finish = h('aside', {class: 'tl2-finish', 'aria-labelledby': 'tl2-finish-title', hidden: true},
    h('h4', {id: 'tl2-finish-title', text: 'Has recorrido la historia — ahora repásala'}), finishText, finishBtn);
  finishBtn.addEventListener('click', () => onFinish());

  function renderNodes() {
    nodesList.replaceChildren(...state.list.map((item, i) => {
      const b = h('button', {class: 'tl2-node', type: 'button', 'data-i': String(i), }, h('span', {class: 'tl2-dot', 'aria-hidden': 'true'}), h('span', {class: 'tl2-ylab', text: trackYear(item.year)}), h('span', {class: 'sr-only', text: `: ${item.year}, ${item.title}`}));
      b.addEventListener('click', () => select(i));
      return h('li', {class: 'tl2-n'}, b);
    }));
  }
  function side(btn, item, dir) {
    btn.hidden = false;
    btn.disabled = !item;
    btn.classList.toggle('is-empty', !item);
    if (!item) { btn.replaceChildren(h('span', {class: 'tl2-side-dir', text: dir < 0 ? 'Antes' : 'Después'}), h('span', {class: 'tl2-side-empty', text: dir < 0 ? 'Aquí empieza' : 'Aquí termina'})); return; }
    btn.replaceChildren(h('span', {class: 'tl2-side-dir', text: dir < 0 ? '‹ Antes' : 'Después ›'}), h('span', {class: 'tl2-side-year', text: item.year}), h('span', {class: 'tl2-side-title', text: item.title}), h('span', {class: 'tl2-side-ppl', text: item.people}));
  }
  function renderCard() {
    const item = state.list[state.index];
    const where = h('p', {class: 'tl-where'}, h('strong', {text: 'Dónde lo ves en Bat’z. '}), item.where);
    if (item.href) where.append(' ', h('a', {href: item.href, text: `${item.link} →`}));
    const folks = peopleOf(item, person);
    cardBody.replaceChildren(
      h('p', {class: 'tl2-kicker'}, h('span', {class: 'tl2-year', text: item.year}), h('span', {class: 'tl2-topic', text: topicLabel(HISTORY_TOPICS, item.topic)})),
      h('h4', {class: 'tl2-title', text: item.title}),
      folks.length ? h('ul', {class: 'tl-people-list', 'aria-label': 'Personas'}, folks.map(personItem)) : h('p', {class: 'tl-people', text: item.people}),
      h('p', {class: 'tl2-what', text: item.what}), where);
  }
  function render({animate = 0, say = false} = {}) {
    const n = state.list.length, i = state.index, item = state.list[i];
    count.textContent = `Se recorren ${n} de ${HISTORY.length} hitos, en orden cronológico.`;
    nodesList.querySelectorAll('.tl2-node').forEach((b, k) => {
      b.classList.toggle('is-past', k < i);
      if (k === i) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
      b.tabIndex = k === i ? 0 : -1;
    });
    track.style.setProperty('--n', String(n));
    track.style.setProperty('--tl-progress', n > 1 ? String(i / (n - 1)) : '0');
    renderCard();
    const {prev: before, next: after} = neighbors(state.list, i);
    side(sidePrev, before, -1); side(sideNext, after, 1);
    prev.disabled = isFirst(i); next.disabled = isLast(i, n);
    pos.textContent = `Hito ${i + 1} de ${n}`;
    finish.hidden = !isLast(i, n);
    if (!finish.hidden) finishText.textContent = `Llegaste al último hito de ${n === HISTORY.length ? 'la historia' : 'este tema'}. Las tarjetas de teoría cubren lo mismo con preguntas: el modo «Estudiar» las baraja y recuerda cuáles ya sabes.`;
    if (animate && !reduceMotion()) {
      card.classList.remove('is-in-next', 'is-in-prev'); void card.offsetWidth;
      card.classList.add(animate > 0 ? 'is-in-next' : 'is-in-prev');
    }
    const cur = nodesList.querySelector('.tl2-node[aria-current]');
    if (document.activeElement?.disabled) cur?.focus({preventScroll: true});
    if (cur) { const left = cur.offsetLeft + cur.offsetWidth / 2 - track.clientWidth / 2; track.scrollTo({left: Math.max(0, left), behavior: 'auto'}); }
    if (say) live.textContent = announce(item, i, n);
  }
  function select(index, {focus = false} = {}) {
    const to = clampIndex(index, state.list.length);
    if (to === state.index) { if (focus) nodesList.querySelector('.tl2-node[aria-current]')?.focus(); return; }
    const dir = to > state.index ? 1 : -1;
    state.index = to;
    render({animate: dir, say: true});
    if (focus) nodesList.querySelector('.tl2-node[aria-current]')?.focus({preventScroll: true});
  }
  const move = delta => select(stepIndex(state.index, state.list.length, delta));
  prev.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  sidePrev.addEventListener('click', () => move(-1));
  sideNext.addEventListener('click', () => move(1));

  const wrap = h('div', {class: 'tl2', role: 'group', 'aria-label': 'Línea del tiempo de la historia de la lógica'}, track, stage, controls, finish);
  wrap.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest('a')) return;
    const keys = {ArrowRight: () => move(1), ArrowDown: () => move(1), ArrowLeft: () => move(-1), ArrowUp: () => move(-1), Home: () => select(0), End: () => select(state.list.length - 1), PageDown: () => move(1), PageUp: () => move(-1)};
    const act = keys[event.key];
    if (!act || (event.target.matches('button') && !event.target.closest('.tl2-track') && /^Arrow(Up|Down)$/.test(event.key))) return;
    event.preventDefault();
    const inTrack = !!event.target.closest('.tl2-track');
    act();
    if (inTrack) nodesList.querySelector('.tl2-node[aria-current]')?.focus({preventScroll: true});
  });
  // Arrastrar con el ratón sobre el hilo: elige el nudo más cercano (con el dedo, el hilo se desplaza y se toca).
  let dragging = false;
  const pick = event => select(nearestIndex([...nodesList.querySelectorAll('.tl2-node')].map(b => { const r = b.getBoundingClientRect(); return r.left + r.width / 2; }), event.clientX));
  track.addEventListener('pointerdown', event => { if (event.pointerType === 'touch' || event.button !== 0) return; dragging = true; track.setPointerCapture?.(event.pointerId); track.classList.add('is-dragging'); pick(event); });
  track.addEventListener('pointermove', event => { if (dragging) pick(event); });
  const stopDrag = event => { if (!dragging) return; dragging = false; track.classList.remove('is-dragging'); track.releasePointerCapture?.(event.pointerId); nodesList.querySelector('.tl2-node[aria-current]')?.focus({preventScroll: true}); };
  track.addEventListener('pointerup', stopDrag); track.addEventListener('pointercancel', stopDrag);
  // Deslizar con el dedo sobre la tarjeta
  let touch = null;
  stage.addEventListener('touchstart', event => { const t = event.touches[0]; touch = event.touches.length === 1 ? {x: t.clientX, y: t.clientY} : null; }, {passive: true});
  stage.addEventListener('touchend', event => { if (!touch) return; const t = event.changedTouches[0]; const d = swipeDelta(t.clientX - touch.x, t.clientY - touch.y); touch = null; if (d) move(d); }, {passive: true});

  const filters = pressedGroup('Filtrar la historia por tema', [{id: 'todos', label: 'Todos'}, ...HISTORY_TOPICS], state.topic, id => {
    const currentId = state.list[state.index]?.id;
    state.topic = id; state.list = visibleMilestones(HISTORY, id);
    state.index = indexAfterFilter(state.list, currentId);
    renderNodes(); render({say: true});
  });
  section.append(title,
    h('p', {class: 'pane-lede', text: 'Elige un hito en el hilo (con un clic, las flechas del teclado o arrastrando) y verás qué aportó, quién lo hizo y dónde lo ves en Bat’z, entre el hito de antes y el de después. Las fechas son las de la publicación original.'}),
    filters, count, live, wrap);
  renderNodes(); render();
  return {section, title, setFinish: fn => { onFinish = fn; }, select: i => select(i), state};
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
  // «Repasar» desde el final de la línea del tiempo: todas las tarjetas, barajadas, en modo Estudiar.
  function startStudy() {
    state.topic = 'todos';
    topics.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.id === 'todos')));
    setMode('study');
    section.scrollIntoView({behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start'});
    (state.done ? done.querySelector('.fc-done-title') : flip)?.focus({preventScroll: true});
  }
  return {section, title, startStudy};
}

export function initLearn(root, {storage = (() => { try { return localStorage; } catch { return null; } })()} = {}) {
  if (!root || root.dataset.ready) return;
  root.dataset.ready = 'yes';
  const history = buildHistory(), cards = buildCards(storage);
  history.setFinish(() => cards.startStudy());
  const jump = (target) => () => { target.section.scrollIntoView({behavior: reduceMotion() ? 'auto' : 'smooth', block: 'start'}); target.title.focus({preventScroll: true}); };
  const toHistory = h('button', {class: 'button secondary small', type: 'button', text: 'Historia de la lógica'});
  const toCards = h('button', {class: 'button secondary small', type: 'button', text: 'Conceptos como tarjetas'});
  toHistory.addEventListener('click', jump(history)); toCards.addEventListener('click', jump(cards));
  root.append(
    h('header', {class: 'learn-head'},
      h('h2', {class: 'pane-title', text: 'Aprender'}),
      h('p', {class: 'pane-lede', text: 'Dos formas de repasar la teoría que Bat’z aplica: cómo se llegó a la lógica de predicados y las ideas clave en tarjetas.'}),
      h('div', {class: 'actions learn-actions', role: 'group', 'aria-label': 'Ir a una parte de la página'}, toHistory, toCards)),
    history.section, cards.section);
}

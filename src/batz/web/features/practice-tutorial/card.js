// Tarjeta flotante del tutorial y su controlador. No bloquea la aplicación: no es modal,
// resalta el control con un contorno y detecta cada acción por eventos del DOM.
import {STEPS, TUTORIAL_EXERCISE, NEXT_EXERCISE, TARGET_RULE, TARGET_REFS, TARGET_FORMULA} from './steps.js';
import {evaluate, earlierProblem, checkFailure, takeSnapshot, cleanRecord, finalRecord, saveBackup, clearBackup,
  readTutorialState, writeTutorialState} from './tutorial.js';

export function createRunner(api, {storage = null, doc = document, win = window} = {}) {
  const root = api.root;
  let active = false, index = 0, snapshot = null, acknowledged = false, starting = false;
  let card = null, parts = {}, listeners = [];
  const reduced = () => win.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = selector => root.querySelector(selector);
  const readUi = () => ({rule: $('#pr-rule')?.value, refs: $('#pr-refs')?.value ?? '', formula: $('#pr-formula')?.value ?? '',
    complete: Boolean($('#pr-success')?.childElementCount), acknowledged});
  const el = (tag, cls, text) => { const n = doc.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const on = (target, type, fn) => { target.addEventListener(type, fn); listeners.push([target, type, fn]); };

  function build() {
    card = el('section', 'pt-card'); card.setAttribute('role', 'dialog'); card.setAttribute('aria-modal', 'false');
    card.setAttribute('aria-labelledby', 'pt-title'); card.setAttribute('aria-describedby', 'pt-text');
    parts.thread = el('ol', 'pt-thread'); parts.thread.setAttribute('aria-hidden', 'true');
    STEPS.forEach(() => parts.thread.append(el('li')));
    parts.count = el('p', 'pt-count');
    parts.title = el('h2', 'pt-title'); parts.title.id = 'pt-title'; parts.title.tabIndex = -1;
    parts.text = el('p', 'pt-text'); parts.text.id = 'pt-text';
    parts.note = el('p', 'pt-note');
    parts.feedback = el('p', 'pt-feedback'); parts.feedback.setAttribute('aria-live', 'polite');
    parts.sr = el('p', 'pt-sr'); parts.sr.setAttribute('role', 'status'); parts.sr.setAttribute('aria-live', 'polite');
    const actions = el('div', 'pt-actions');
    const btn = (text, cls, fn) => { const b = el('button', `pt-button ${cls}`, text); b.type = 'button'; b.addEventListener('click', fn); return b; };
    parts.skip = btn('Omitir tutorial', 'pt-skip', () => finish(STEPS[index].last ? 'completado' : 'omitido'));
    parts.back = btn('Atrás', 'pt-secondary', () => go(index - 1));
    parts.how = btn('Mostrar cómo', 'pt-secondary', showHow);
    parts.next = btn('Siguiente', 'pt-primary', () => next());
    actions.append(parts.skip, parts.back, parts.how, parts.next);
    card.append(parts.thread, parts.count, parts.title, parts.text, parts.note, parts.feedback, actions, parts.sr);
    root.parentElement.insertBefore(card, root);   // antes del ejercicio en el orden de tabulación; flota con CSS
  }

  function clearTargets() { doc.querySelectorAll('.pt-target').forEach(n => n.classList.remove('pt-target')); }
  function highlight(scroll) {
    clearTargets();
    let first = null;
    for (const selector of STEPS[index].targets) { const node = $(selector); if (node) { node.classList.add('pt-target'); first ||= node; } }
    if (scroll && first) {
      const r = first.getBoundingClientRect(), limit = card.getBoundingClientRect().top;
      if (r.top < 0 || r.bottom > limit - 8) first.scrollIntoView({block: 'center', behavior: reduced() ? 'auto' : 'smooth'});
    }
  }
  const showFeedback = (text, kind = '') => { parts.feedback.textContent = text || ''; parts.feedback.className = `pt-feedback ${kind}`; parts.feedback.hidden = !text; };
  const satisfied = () => { const ui = readUi(), step = STEPS[index];
    return step.action ? evaluate(step.id, ui).done && !earlierProblem(index, ui) : step.last ? true : acknowledged; };

  function render({scroll = true, announce = true} = {}) {
    const step = STEPS[index], last = Boolean(step.last);
    parts.count.textContent = `Paso ${index + 1} de ${STEPS.length}`;
    parts.title.textContent = step.title; parts.text.textContent = step.text;
    parts.note.hidden = !last;
    if (last) parts.note.textContent = snapshot?.complete
      ? 'Ya tenías este ejercicio completo: al cerrar se restaura tu prueba anterior.'
      : 'Esta prueba queda guardada como tu ejercicio 01 completado.';
    [...parts.thread.children].forEach((li, i) => { li.className = i < index ? 'is-done' : i === index ? 'is-current' : ''; });
    parts.back.disabled = index === 0; parts.how.hidden = !step.how;
    parts.skip.textContent = last ? 'Terminar' : 'Omitir tutorial';
    parts.next.textContent = last ? `Ir al ejercicio ${NEXT_EXERCISE} →` : step.ack || 'Siguiente';
    parts.next.disabled = !last && !satisfied();
    parts.next.setAttribute('aria-disabled', String(parts.next.disabled));
    if (announce) parts.sr.textContent = `Paso ${index + 1} de ${STEPS.length}. ${step.title}. ${step.text}`;
    highlight(scroll);
    doc.documentElement.style.setProperty('--pt-h', `${card.offsetHeight}px`);
  }
  function go(i, how) { index = Math.max(0, Math.min(STEPS.length - 1, i)); showFeedback(how, 'is-good'); render(); }
  function next() { if (STEPS[index].last) return finish('completado', {goto: NEXT_EXERCISE}); if (!satisfied()) return; if (index === 0) acknowledged = true; go(index + 1); }

  // Reacción a una acción de la persona en la interfaz.
  function react() {
    if (!active) return;
    const step = STEPS[index], ui = readUi();
    if (!step.action || step.last) return;
    if (step.action === 'check') { const p = earlierProblem(index, ui); showFeedback(p, 'is-problem'); render({scroll: false, announce: false}); return; }
    const result = evaluate(step.id, ui), earlier = earlierProblem(index, ui);
    if (result.done && !earlier) return go(index + 1, null);
    showFeedback(earlier || result.problem, 'is-problem');
    render({scroll: false, announce: false});
  }
  function onChecked(e) {
    if (!active) return;
    const {ok, complete, error} = e.detail || {};
    if (ok && complete) { index = STEPS.length - 1; showFeedback('', ''); render(); return; }
    if (!ok) { showFeedback(checkFailure(error), 'is-problem'); render({scroll: false, announce: false}); }
  }
  function onView(e) {
    if (!active) return;
    const {view, id} = e.detail || {};
    if (view === 'exercise' && id === TUTORIAL_EXERCISE) { highlight(false); render({scroll: false, announce: false}); }
    else finish('omitido', {silent: true});
  }
  function showHow() {
    const step = STEPS[index];
    if (step.action === 'rule') { const s = $('#pr-rule'); s.value = TARGET_RULE; s.dispatchEvent(new Event('change', {bubbles: true})); }
    else if (step.action === 'refs') { const i = $('#pr-refs'); i.value = TARGET_REFS.join(', '); i.dispatchEvent(new Event('input', {bubbles: true})); }
    else if (step.action === 'formula') { const i = $('#pr-formula'); i.value = TARGET_FORMULA; i.dispatchEvent(new Event('input', {bubbles: true})); }
    else if (step.action === 'check') { $('#pr-check')?.click(); return; }
    // react() ya avanzó; deja constancia de lo que se hizo por la persona
    showFeedback(step.how, 'is-good');
  }

  async function start() {
    if (active || starting) return false;
    starting = true;
    try {
      snapshot = takeSnapshot(api.getProgress(), TUTORIAL_EXERCISE);
      saveBackup(storage, snapshot);
      api.setRecord(TUTORIAL_EXERCISE, cleanRecord(snapshot));
      index = 0; acknowledged = false;
      await api.open(TUTORIAL_EXERCISE);
      if (!$('#pr-rule')) { restore(); return false; }   // el ejercicio no se pudo abrir
      active = true; build();
      doc.body.classList.add('pt-active');
      for (const type of ['input', 'change']) on(root, type, e => { if (e.target.closest?.('#pr-rule, #pr-refs, #pr-formula')) react(); });
      on(root, 'click', e => { if (e.target.closest?.('.pr-line-number')) setTimeout(react, 0); });
      on(root, 'batz-practice-checked', onChecked);
      on(root, 'batz-practice-view', onView);
      on(win, 'hashchange', () => { if (!/^#\/?practicar/.test(win.location.hash)) finish('omitido', {silent: true}); });
      on(doc, 'keydown', e => { if (e.key === 'Escape' && !doc.querySelector('dialog[open]')) { e.preventDefault(); finish(STEPS[index].last ? 'completado' : 'omitido'); } });
      render({scroll: false}); parts.title.focus({preventScroll: true});
      return true;
    } finally { starting = false; }
  }
  function restore() {
    api.setRecord(TUTORIAL_EXERCISE, finalRecord(snapshot, api.getProgress()[TUTORIAL_EXERCISE]));
    clearBackup(storage); snapshot = null;
  }
  async function finish(state, {goto = null, silent = false} = {}) {
    if (!active) return;
    active = false;
    for (const [target, type, fn] of listeners) target.removeEventListener(type, fn);
    listeners = []; clearTargets(); card.remove(); card = null;
    doc.body.classList.remove('pt-active'); doc.documentElement.style.removeProperty('--pt-h');
    if (state === 'completado' || !readTutorialState(storage)) writeTutorialState(storage, state);
    restore();
    if (goto) await api.open(goto);
    else if (silent) api.refreshHome();   // el inicio ya estaba pintado: se repinta con el estado final
    else if (api.currentId() === TUTORIAL_EXERCISE) await api.open(TUTORIAL_EXERCISE);   // muestra el registro restaurado
  }
  return {start, isActive: () => active, finish};
}

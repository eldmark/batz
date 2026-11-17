// Recorrido breve y opcional de primer acceso. La lógica de estado es pura (se prueba en Node);
// el diálogo solo toca el DOM dentro de createTour.
export const TOUR_KEY = 'logos-recorrido';
export const TOUR_STATES = ['completado', 'omitido'];

/** Estado recordado: 'completado', 'omitido' o null. Tolera almacenamiento ausente o que lance. */
export function readTourState(storage) {
  try { const value = storage?.getItem(TOUR_KEY); return TOUR_STATES.includes(value) ? value : null; } catch { return null; }
}
export function writeTourState(storage, state) {
  if (!TOUR_STATES.includes(state)) return false;
  try { storage.setItem(TOUR_KEY, state); return true; } catch { return false; }
}
/** Se ofrece solo en la primera visita y solo en Inicio (hash vacío o #/inicio). */
export function shouldOfferTour({state, hash}) {
  const route = String(hash || '').replace(/\/+$/, '');
  return !state && (route === '' || route === '#' || route === '#/inicio');
}

export const STEPS = [
  {id: 'sidebar', title: 'La barra lateral', target: '#sidebar', menu: true,
    text: 'Desde aquí cambias de sección: Inicio, las herramientas y Practicar. La sección actual aparece marcada. Puedes contraerla con el botón de su cabecera.',
    textMobile: 'En el teléfono la barra lateral es un menú: se abre con el botón «Abrir el menú» de arriba a la izquierda. Ahora la ves abierta. Se cierra con Escape o tocando fuera.'},
  {id: 'tools', title: 'Razonamiento y Conocimiento', target: '#nav', menu: true,
    text: 'Razonamiento reúne Evaluar modelo, Demostrar y Practicar: comprobar fórmulas y consecuencias. Conocimiento reúne Cuadernos y Diccionario: preguntar a tus textos y consultar el léxico.'},
  {id: 'example', title: 'Ejecuta un ejemplo desde Inicio', target: '#home-body .home-exercises',
    text: 'Cada ejercicio de «Empieza con un ejemplo» tiene un botón «Abrir y cargar ejemplo»: abre la herramienta con datos listos. Después pulsa el botón principal de esa herramienta (por ejemplo «Evaluar») para ver el resultado.'},
];

export function createTour({go, openMenu = () => {}, closeMenu = () => {}, storage = null, doc = document, win = window} = {}) {
  let session = null;   // si no hay almacenamiento, al menos no se repite en esta sesión
  let root = null, index = 0, opener = null, onKey = null, onHash = null;
  const mobile = () => win.matchMedia('(max-width: 900px)').matches;
  const remembered = () => readTourState(storage) ?? session;
  const remember = state => { session = state; writeTourState(storage, state); };

  function el(tag, props = {}, ...kids) {
    const node = doc.createElement(tag);
    Object.assign(node, props);
    node.append(...kids);
    return node;
  }
  const clearTarget = () => doc.querySelectorAll('.tour-target').forEach(n => n.classList.remove('tour-target'));
  const focusables = () => [...root.querySelectorAll('button')].filter(b => !b.disabled);

  function render() {
    const step = STEPS[index], last = index === STEPS.length - 1, small = mobile();
    clearTarget();
    if (step.menu && small) openMenu(); else closeMenu();
    const target = doc.querySelector(step.target);
    if (target) {
      target.classList.add('tour-target');
      if (!step.menu) target.scrollIntoView({block: 'center', behavior: win.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    }
    root.replaceChildren(
      el('p', {className: 'tour-count', textContent: `Paso ${index + 1} de ${STEPS.length}`}),
      el('h2', {id: 'tour-title', className: 'tour-title', tabIndex: -1, textContent: step.title}),
      el('p', {id: 'tour-text', className: 'tour-text', textContent: small && step.textMobile ? step.textMobile : step.text}),
      el('div', {className: 'tour-actions'},
        el('button', {type: 'button', className: 'button secondary', id: 'tour-skip', textContent: last ? 'Cerrar' : 'Omitir recorrido', onclick: () => close(last ? 'completado' : 'omitido')}),
        index > 0 ? el('button', {type: 'button', className: 'button secondary', id: 'tour-prev', textContent: 'Anterior', onclick: () => { index--; render(); }}) : '',
        el('button', {type: 'button', className: 'button primary', id: 'tour-next', textContent: last ? 'Terminar' : 'Siguiente', onclick: () => (last ? close('completado') : (index++, render()))})));
    root.querySelector('#tour-next').focus();
    root.querySelector('#tour-title').setAttribute('aria-live', 'off');
  }

  function open({fromHelp = false} = {}) {
    if (root) return;
    opener = doc.activeElement && doc.activeElement !== doc.body ? doc.activeElement : null;
    if (fromHelp) { opener = doc.getElementById('help-button') ?? opener; go('home'); }
    index = 0;
    root = el('div', {id: 'tour', className: 'tour', role: 'dialog'});
    root.setAttribute('aria-modal', 'false');
    root.setAttribute('aria-labelledby', 'tour-title');
    root.setAttribute('aria-describedby', 'tour-text');
    doc.body.append(root);
    onKey = event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close('omitido'); return; }
      if (event.key !== 'Tab') return;
      const items = focusables(); if (!items.length) return;
      const first = items[0], last = items.at(-1);
      if (!root.contains(doc.activeElement)) { event.preventDefault(); first.focus(); }
      else if (event.shiftKey && doc.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && doc.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    doc.addEventListener('keydown', onKey, true);
    // Si se navega a otra sección, el recorrido (que habla de Inicio) se cierra sin bloquear nada.
    onHash = () => close('omitido', {restoreFocus: false});
    win.addEventListener('hashchange', onHash);
    render();
  }

  /** Cierra el diálogo. Completado solo si llegó al final; Escape u Omitir lo marcan como omitido. */
  function close(state, {restoreFocus = true} = {}) {
    if (!root) return;
    doc.removeEventListener('keydown', onKey, true);
    win.removeEventListener('hashchange', onHash);
    root.remove(); root = null;
    clearTarget(); closeMenu();
    // Reabrirlo desde Ayuda no borra un «completado» previo con un «omitido».
    if (state === 'completado' || !remembered()) remember(state);
    const back = opener && doc.contains(opener) ? opener : doc.getElementById('page-title');
    opener = null;
    if (restoreFocus) back?.focus();
  }

  /** Primera visita en Inicio: lo ofrece una vez; nunca si ya se completó u omitió. */
  function maybeOffer(hash = win.location.hash) {
    if (shouldOfferTour({state: remembered(), hash})) open();
  }
  return {open, close, maybeOffer, isOpen: () => root !== null};
}

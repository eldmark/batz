// Pantalla completa de una sola instancia; también funciona sin la API nativa.
let fallbackOwner = null;

export function createFullscreen(root, button, {onExit = () => {}} = {}) {
  const doc = root.ownerDocument, win = doc.defaultView;
  let fallback = false, saved = null, dead = false, generation = 0;
  const timers = new Set();
  const nativeElement = () => doc.fullscreenElement || doc.webkitFullscreenElement;
  const isOn = () => fallback || nativeElement() === root;

  function sync() {
    const on = isOn();
    root.classList.toggle('ep-fullscreen', on);
    button.setAttribute('aria-pressed', String(on));
    button.textContent = on ? 'Salir de pantalla completa' : 'Pantalla completa';
    if (!on && saved) restore();
  }

  function restore() {
    const state = saved; saved = null;
    const align = () => {
      if (!root.isConnected || root.hidden || !root.getClientRects().length || isOn()) return;
      const drift = root.getBoundingClientRect().top - state.top;
      if (Math.abs(drift) > 1) win.scrollTo({top: win.scrollY + drift, behavior: 'instant'});
    };
    // El navegador puede terminar de redimensionar después de fullscreenchange.
    for (const delay of [0, 150, 400]) {
      const id = win.setTimeout(() => { timers.delete(id); align(); }, delay); timers.add(id);
    }
    if (state.focus?.isConnected && state.focus.getClientRects().length) state.focus.focus({preventScroll: true});
    try { win.screen.orientation?.unlock?.(); } catch { /* sin bloqueo */ }
    onExit();
  }

  async function enter() {
    if (dead || isOn()) return;
    timers.forEach(id => win.clearTimeout(id)); timers.clear();
    const token = ++generation;
    saved = {top: root.getBoundingClientRect().top, focus: doc.activeElement};
    const request = root.requestFullscreen || root.webkitRequestFullscreen;
    if (request && (doc.fullscreenEnabled ?? doc.webkitFullscreenEnabled ?? true)) {
      try {
        await request.call(root, {navigationUI: 'hide'});
        if (dead || generation !== token) { if (nativeElement() === root) exit(); return; }
        sync();
        if (win.matchMedia('(pointer: coarse) and (orientation: portrait)').matches) {
          win.screen.orientation?.lock?.('landscape')?.catch?.(() => {});
        }
        return;
      } catch { /* respaldo para iPhone o permiso denegado */ }
    }
    if (dead || generation !== token) return;
    fallbackOwner?.exit();
    fallback = true; fallbackOwner = api;
    root.classList.add('ep-fallback-fullscreen');
    const style = doc.documentElement.style;
    api.previousOverflow = {value: style.getPropertyValue('overflow'), priority: style.getPropertyPriority('overflow')};
    style.setProperty('overflow', 'hidden');
    sync(); button.focus({preventScroll: true});
  }

  function exit() {
    ++generation;
    if (fallback) {
      fallback = false; root.classList.remove('ep-fallback-fullscreen');
      if (fallbackOwner === api) {
        const {value, priority} = api.previousOverflow;
        doc.documentElement.style.setProperty('overflow', value, priority); fallbackOwner = null;
      }
    }
    const leavingNative = nativeElement() === root;
    if (leavingNative) {
      try {
        const result = doc.exitFullscreen ? doc.exitFullscreen() : doc.webkitExitFullscreen?.();
        result?.then?.(() => { if (!dead) sync(); })?.catch?.(() => { if (saved) restore(); });
      } catch { /* ya salió */ }
    }
    root.classList.remove('ep-fullscreen');
    button.setAttribute('aria-pressed', 'false'); button.textContent = 'Pantalla completa';
    // En la API nativa el navegador restaura el foco al finalizar la transición.
    // Restaurarlo antes provocaba que luego enfocara el botón ya oculto al cerrar.
    if (saved && !leavingNative) restore();
  }

  const keyboard = event => {
    if (!isOn() || event.key !== 'Escape') return;
    event.preventDefault(); exit();
  };
  doc.addEventListener('fullscreenchange', sync);
  doc.addEventListener('webkitfullscreenchange', sync);
  doc.addEventListener('keydown', keyboard);
  const api = {enter, exit, isOn, destroy() {
    if (dead) return;
    exit(); dead = true;
    timers.forEach(id => win.clearTimeout(id)); timers.clear();
    doc.removeEventListener('fullscreenchange', sync);
    doc.removeEventListener('webkitfullscreenchange', sync);
    doc.removeEventListener('keydown', keyboard);
  }};
  return api;
}

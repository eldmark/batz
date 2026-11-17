// Helpers de presentación. No evalúan fórmulas ni completan el guion del motor.
export const valueLabel = value => typeof value === 'string' ? value : JSON.stringify(value);
const same = (a, b) => typeof a === typeof b && a === b;

export function focusValues(event) {
  if (event.term_values?.length) return event.term_values;
  if (event.element !== null && event.element !== undefined) return [event.element];
  return Object.values(event.assignment || {});
}

export function eventLabel(event) {
  if (event.kind === 'search') return 'Búsqueda acotada';
  if (event.kind === 'premise') return 'Comprobación de premisa';
  if (event.kind === 'proof') return `Línea ${event.line ?? '—'} · ${event.rule_label || event.rule || 'Deducción'}`;
  return event.trace_path ? `Comprobación · nodo ${event.trace_path}` : 'Comprobación';
}

export function eventVerdict(event) {
  if (event.kind === 'search') return {label: 'Búsqueda acotada', tone: 'neutral'};
  if (event.value === true) return {label: 'Verdadero', tone: 'true'};
  if (event.value === false) return {label: 'Falso', tone: 'false'};
  if (event.verified_by?.certificate_step !== undefined) return {label: 'Paso verificado', tone: 'neutral'};
  return {label: 'Paso del guion', tone: 'neutral'};
}

export function caseIndex(events, index, element) {
  let path = events[index]?.trace_path;
  while (path) {
    const owner = events.find(event => event.trace_path === path);
    if (owner?.kind === 'quantifier') {
      const depth = path.split('.').length + 1;
      const found = events.findIndex(event => event.trace_path?.startsWith(path + '.') &&
        event.trace_path.split('.').length === depth && same(event.element, element));
      if (found >= 0) return found;
    }
    path = path.includes('.') ? path.slice(0, path.lastIndexOf('.')) : '';
  }
  return -1;
}

export function domainPresentation(event, model) {
  const focus = event.kind === 'premise' ? [] : focusValues(event);
  return (model?.domain || []).map((value, index) => ({
    value,
    visible: event.kind !== 'search' || index < (event.size || 0),
    active: focus.some(item => same(item, value)),
  }));
}

export function localSpanishVoice(synthesis) {
  const voices = synthesis?.getVoices?.().filter(voice => voice.localService === true && /^es(?:-|$)/i.test(voice.lang)) || [];
  return voices.find(voice => /^es-(mx|us|419|gt|co|ar|cl|pe)/i.test(voice.lang)) || voices[0] || null;
}

export function readingTime(text, rate) {
  return Math.max(1800, (text || '').trim().split(/\s+/).length * 370) / rate;
}

// ── Voces: del navegador (locales) y del equipo (espeak-ng vía el servidor local) ──
const VOICE_KEY = 'logos-voz';

/** Voces españolas que el navegador ofrece como locales; las latinoamericanas primero. */
export function browserSpanishVoices(synthesis) {
  const voices = synthesis?.getVoices?.().filter(voice => voice.localService === true && /^es(?:-|$)/i.test(voice.lang)) || [];
  const latam = voice => (/^es-(mx|us|419|gt|co|ar|cl|pe)/i.test(voice.lang) ? 0 : 1);
  return [...voices].sort((a, b) => latam(a) - latam(b));
}

/** Preferencia guardada: 'auto', 'browser:<voiceURI>' o 'server:<id>'. */
export function readVoicePref(storage) {
  try { return storage?.getItem(VOICE_KEY) || 'auto'; } catch { return 'auto'; }
}
export function saveVoicePref(storage, pref) {
  try { storage?.setItem(VOICE_KEY, pref); } catch { /* sin almacenamiento: vale solo para esta sesión */ }
}

/** Elige la voz a usar. Con 'auto' o una preferencia que ya no existe: primero el navegador, luego el equipo. */
export function chooseVoice({browser = [], server = [], pref = 'auto'}) {
  if (pref.startsWith('browser:')) {
    const voice = browser.find(item => item.voiceURI === pref.slice(8));
    if (voice) return {kind: 'browser', voice, name: voice.name};
  }
  if (pref.startsWith('server:')) {
    const voice = server.find(item => item.id === pref.slice(7));
    if (voice) return {kind: 'server', id: voice.id, name: voice.label};
  }
  if (browser[0]) return {kind: 'browser', voice: browser[0], name: browser[0].name};
  if (server[0]) return {kind: 'server', id: server[0].id, name: server[0].label};
  return null;
}

/** Cuándo mover la boca en cada palabra para que el habla de duración conocida (audio generado) coincida. */
export function wordTimings(text, syllables, totalMs) {
  const words = (text || '').match(/\S+/g) || [];
  const weights = words.map(raw => {
    const word = raw.replace(/[,.;:!?¡¿()]/g, '');
    return {word, weight: Math.max(1, syllables(word)) * 185 + (/[,.;:!?)]$/.test(raw) ? 300 : 35), pause: /[,.;:!?)]$/.test(raw)};
  });
  const sum = weights.reduce((total, item) => total + item.weight, 0) || 1;
  let at = 0;
  return weights.map(item => { const entry = {word: item.word, at: Math.round(at * totalMs / sum), pause: item.pause}; at += item.weight; return entry; });
}

let serverVoicesPromise = null;
/** Vuelve a preguntar al servidor (p. ej. tras instalar espeak-ng) sin recargar la página. */
export function resetServerVoices() { serverVoicesPromise = null; }
/** Pide al servidor local las voces de espeak-ng. `reason` explica por qué no hay: 'sin-motor', 'servidor-antiguo' o 'sin-servidor'. */
export function loadServerVoices(win) {
  serverVoicesPromise ||= (async () => {
    try {
      const response = await win.fetch('/api/voice/voices', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
      if (response.status === 404) return {available: false, voices: [], hint: null, reason: 'servidor-antiguo'};
      if (!response.ok) return {available: false, voices: [], hint: null, reason: 'sin-servidor'};
      const data = await response.json();
      return {available: Boolean(data.available), voices: data.voices || [], hint: data.hint || null, reason: data.available ? null : 'sin-motor'};
    } catch { return {available: false, voices: [], hint: null, reason: 'sin-servidor'}; }
  })();
  return serverVoicesPromise;
}

/** Texto de ayuda cuando no hay ninguna voz, según la causa real. */
export function noVoiceHelp(reason, hint) {
  const tail = ' Puedes seguir leyendo y recorrer todos los pasos sin audio.';
  if (reason === 'servidor-antiguo') return 'El servidor de Bat’z que está en ejecución es una versión anterior y no ofrece voces: ciérralo y vuelve a iniciarlo con el código actual.' + tail;
  if (reason === 'sin-servidor') return 'No se pudo consultar al servidor local de Bat’z para buscar voces.' + tail;
  return `No hay una voz en español disponible. ${hint || 'Instala espeak-ng (en Arch/CachyOS: sudo pacman -S espeak-ng) y pulsa «Volver a buscar voces».'}` + tail;
}

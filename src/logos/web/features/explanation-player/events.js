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

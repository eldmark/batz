// Lógica pura de la línea del tiempo de «Aprender». Sin DOM, para probarla en Node.

/** Hitos que se recorren con un filtro de tema; 'todos' (o vacío) no filtra. */
export function visibleMilestones(history, topic) {
  return !topic || topic === 'todos' ? [...history] : history.filter(item => item.topic === topic);
}

/** Índice dentro de [0, n-1]; con n = 0 devuelve 0. */
export function clampIndex(index, n) {
  if (!n) return 0;
  return Math.min(n - 1, Math.max(0, Number.isFinite(index) ? Math.trunc(index) : 0));
}

/** Avanza o retrocede sin dar la vuelta: en los extremos se queda donde está. */
export function stepIndex(index, n, delta) { return clampIndex(index + delta, n); }

/** El «antes» y el «después» de un hito; null en el primero y en el último. */
export function neighbors(list, index) {
  const i = clampIndex(index, list.length);
  return {prev: i > 0 ? list[i - 1] : null, next: i < list.length - 1 ? list[i + 1] : null};
}

export const isFirst = index => index <= 0;
export const isLast = (index, n) => n > 0 && index >= n - 1;

/** Si cambia el filtro, conserva el hito actual cuando sigue visible; si no, el primero. */
export function indexAfterFilter(list, currentId) {
  const i = list.findIndex(item => item.id === currentId);
  return i < 0 ? 0 : i;
}

/** Arrastre: índice del nudo más cercano a una posición horizontal (centros dados). */
export function nearestIndex(centers, x) {
  let best = 0;
  centers.forEach((c, i) => { if (Math.abs(c - x) < Math.abs(centers[best] - x)) best = i; });
  return best;
}

/** Deslizar con el dedo: -1 (siguiente), 1 (anterior) o 0 si el gesto es corto o más vertical que horizontal. */
export function swipeDelta(dx, dy, min = 50) {
  if (Math.abs(dx) < min || Math.abs(dx) < Math.abs(dy) * 1.5) return 0;
  return dx < 0 ? 1 : -1;
}

/** Etiqueta corta de la fecha para el nudo del hilo. */
export function trackYear(year) {
  const decade = /^década de (\d{3})0$/.exec(year);
  if (decade) return `${decade[1]}0s`;
  const century = /^s\. ([IVX]+)( a\. C\.)?$/.exec(year);
  if (century) return `${century[1]}${century[2] ?? ''}`;
  return /\d{3,4}/.exec(year)?.[0] ?? year;
}

/** Personas de un hito resueltas contra la fuente de datos; descarta slugs desconocidos. */
export function peopleOf(item, lookup) { return (item.slugs ?? []).map(slug => lookup(slug)).filter(Boolean); }

/** Slugs que no existen en la fuente de datos (para las pruebas). */
export function unknownSlugs(history, lookup) {
  return history.flatMap(item => (item.slugs ?? []).filter(slug => !lookup(slug)).map(slug => `${item.id}:${slug}`));
}

/** Los créditos CC BY / CC BY-SA deben verse junto al retrato. */
export const needsVisibleCredit = p => /CC BY/.test(p?.license ?? '');

export function announce(item, index, n) {
  return `Hito ${index + 1} de ${n}: ${item.year}, ${item.title}.`;
}

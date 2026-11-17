// Lógica pura de las tarjetas: baraja, filtros, cola de estudio y progreso. Sin DOM, para probarla en Node.
export const STORAGE_KEY = 'logos-tarjetas';

/** Fisher–Yates sobre una copia; `rng` devuelve un número en [0, 1). */
export function shuffle(items, rng = Math.random) {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.min(i, Math.floor(rng() * (i + 1)));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** `topic` 'todos' (o vacío) no filtra. */
export function filterCards(cards, topic) {
  return !topic || topic === 'todos' ? [...cards] : cards.filter(card => card.topic === topic);
}

export function emptyProgress() { return {known: [], review: []}; }

/** Acepta cualquier cosa leída del disco: descarta ids ajenos y duplicados; un id no puede estar en las dos listas. */
export function sanitizeProgress(raw, cards) {
  const valid = new Set(cards.map(card => card.id));
  const take = list => [...new Set(Array.isArray(list) ? list.filter(id => valid.has(id)) : [])];
  const known = take(raw?.known);
  const review = take(raw?.review).filter(id => !known.includes(id));
  return {known, review};
}

export function loadProgress(storage, cards) {
  try { return sanitizeProgress(JSON.parse(storage?.getItem(STORAGE_KEY) ?? 'null'), cards); } catch { return emptyProgress(); }
}
/** Devuelve true si pudo guardar; la aplicación sigue funcionando si no. */
export function saveProgress(storage, progress) {
  try { storage.setItem(STORAGE_KEY, JSON.stringify({v: 1, ...progress})); return true; } catch { return false; }
}
export function clearProgress(storage) { try { storage?.removeItem(STORAGE_KEY); return true; } catch { return false; } }

export function statusOf(progress, id) {
  return progress.known.includes(id) ? 'known' : progress.review.includes(id) ? 'review' : 'pending';
}
/** status: 'known' | 'review' | 'pending'. Devuelve un progreso nuevo. */
export function mark(progress, id, status) {
  const known = progress.known.filter(x => x !== id), review = progress.review.filter(x => x !== id);
  if (status === 'known') known.push(id); else if (status === 'review') review.push(id);
  return {known, review};
}
export function summary(cards, progress) {
  const ids = new Set(cards.map(card => card.id));
  const known = progress.known.filter(id => ids.has(id)).length, review = progress.review.filter(id => ids.has(id)).length;
  return {total: cards.length, known, review, pending: cards.length - known - review};
}

/** Cola de estudio: tarjetas del tema, barajadas; con `onlyOpen` se omiten las que ya se saben. */
export function buildQueue(cards, progress, {topic = 'todos', onlyOpen = true, rng = Math.random} = {}) {
  const base = filterCards(cards, topic).filter(card => !onlyOpen || statusOf(progress, card.id) !== 'known');
  return shuffle(base, rng);
}

/** Índice vecino con vuelta al otro extremo. */
export function step(index, length, delta) {
  return length ? (((index + delta) % length) + length) % length : 0;
}

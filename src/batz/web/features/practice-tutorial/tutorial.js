// Lógica pura del tutorial: estado recordado, evaluación de cada paso y restauración del registro.
// No toca el DOM ni el servidor; se prueba en Node (tests/frontend/app/tutorial.test.mjs).
import {STEPS, START_RULE, TARGET_RULE, TARGET_REFS, TARGET_FORMULA} from './steps.js';

export const TUTORIAL_KEY = 'batz-practice-tutorial';
export const BACKUP_KEY = 'batz-practice-tutorial-backup';
export const TUTORIAL_STATES = ['completado', 'omitido'];

/** 'completado', 'omitido' o null. Tolera almacenamiento ausente, roto o con valores ajenos. */
export function readTutorialState(storage) {
  try { const v = storage?.getItem(TUTORIAL_KEY); return TUTORIAL_STATES.includes(v) ? v : null; } catch { return null; }
}
export function writeTutorialState(storage, state) {
  if (!TUTORIAL_STATES.includes(state)) return false;
  try { storage.setItem(TUTORIAL_KEY, state); return true; } catch { return false; }
}
/** El banner de bienvenida solo se muestra mientras no se haya completado ni omitido. */
export const shouldOfferTutorial = state => !TUTORIAL_STATES.includes(state);

export const normalizeFormula = text => String(text ?? '').replace(/\s+/g, '');
/** '1, 2' -> [1, 2]; vacío -> []; texto no numérico -> null. */
export function parseRefs(text) {
  const value = String(text ?? '').trim();
  if (!value) return [];
  return /^\d+(?:\s*,\s*\d+)*$/.test(value) ? value.split(',').map(n => Number(n.trim())) : null;
}
const sameRefs = (a, b) => a.length === b.length && a.every((n, i) => n === b[i]);

const RULE_NAMES = {and_e1: '∧E₁', and_e2: '∧E₂', and_i: '∧I', imp_e: '→E', assume: 'Hipótesis', or_i1: '∨I₁', or_i2: '∨I₂'};

/** Evalúa un paso contra el estado de la interfaz {rule, refs, formula, lines, complete}.
 *  -> {done, problem}: problem es null si falta la acción pero no hay error, o un texto útil si se equivocó. */
export function evaluateStep(id, ui) {
  switch (id) {
    case 'regla':
      if (ui.rule === TARGET_RULE) return {done: true, problem: null};
      return {done: false, problem: ui.rule === 'and_e2'
        ? 'Elegiste ∧E₂ · Extraer derecha, que saca Q. Tu objetivo es P, la parte izquierda: elige ∧E₁.'
        : `Elegiste ${RULE_NAMES[ui.rule] || 'otra regla'}. Para sacar P de P ∧ Q necesitas ∧E₁ · Extraer izquierda.`};
    case 'citar': {
      const refs = parseRefs(ui.refs);
      if (refs && sameRefs(refs, TARGET_REFS)) return {done: true, problem: null};
      if (refs && !refs.length) return {done: false, problem: null};
      if (refs === null) return {done: false, problem: 'Escribe solo el número de línea, por ejemplo: 1.'};
      return {done: false, problem: refs.some(n => n > 1)
        ? 'Por ahora solo existe la línea 1 (la premisa P ∧ Q). Cítala a ella.'
        : 'Cita únicamente la línea 1: ∧E₁ usa una sola referencia.'};
    }
    case 'formula': {
      const text = normalizeFormula(ui.formula);
      if (text === TARGET_FORMULA) return {done: true, problem: null};
      if (!text) return {done: false, problem: null};
      return {done: false, problem: text === 'Q'
        ? 'Q es la parte derecha. ∧E₁ saca la izquierda, así que escribe P.'
        : 'Con ∧E₁ de P ∧ Q obtienes exactamente P. Escribe solo P.'};
    }
    case 'comprobar':
      return {done: Boolean(ui.complete), problem: null};
    default:
      return {done: id === 'objetivo' ? Boolean(ui.acknowledged) : Boolean(ui.complete), problem: null};
  }
}
export const evaluate = evaluateStep;

/** Primer problema de los pasos de acción previos al indicado (p. ej. cambió la regla estando en la fórmula). */
export function earlierProblem(index, ui) {
  for (let i = 1; i < index && i < STEPS.length; i++) {
    if (!STEPS[i].action || STEPS[i].action === 'check') continue;
    const r = evaluate(STEPS[i].id, ui);
    if (!r.done) return r.problem || `Falta completar: ${STEPS[i].title.toLowerCase()}.`;
  }
  return null;
}

/** Un mensaje útil cuando el servidor rechazó el paso del tutorial. */
export const checkFailure = message => `El servidor no aceptó el paso${message ? `: ${message}` : ''}. Revisa la regla, la línea citada y la fórmula.`;

// ── Registro de progreso del ejercicio 01 ──
const clone = value => (value === undefined ? undefined : JSON.parse(JSON.stringify(value)));
export const takeSnapshot = (progress, id) => clone(progress?.[id]) ?? null;

/** Registro limpio para empezar: sin jugadas ni pistas y con otra regla elegida; conserva revisión y archivo previo. */
export function cleanRecord(snapshot) {
  const rec = {moves: [], complete: false, hints: 0, editor: {rule: START_RULE}};
  if (snapshot?.revision) rec.revision = snapshot.revision;
  if (Array.isArray(snapshot?.previous)) rec.previous = clone(snapshot.previous);
  return rec;
}
/** Registro que debe quedar al terminar u omitir.
 *  - Si lo tenía completado: se restaura el original (el tutorial no se lo quita ni se lo cambia).
 *  - Si no lo tenía y el tutorial lo completó: se conserva el avance real.
 *  - Si no lo tenía y no se completó: se restaura el original (sus jugadas y pistas previas). */
export function finalRecord(snapshot, current) {
  if (snapshot?.complete === true) return clone(snapshot);
  if (current?.complete === true) return clone(current);
  return snapshot ? clone(snapshot) : {moves: [], complete: false, hints: 0};
}
// Copia de seguridad por si se cierra la pestaña a mitad del tutorial.
export function saveBackup(storage, snapshot) {
  try { storage.setItem(BACKUP_KEY, JSON.stringify({snapshot})); return true; } catch { return false; }
}
export function readBackup(storage) {
  try {
    const raw = storage?.getItem(BACKUP_KEY); if (!raw) return null;
    const data = JSON.parse(raw);
    return data && typeof data === 'object' && 'snapshot' in data ? {snapshot: data.snapshot ?? null} : null;
  } catch { return null; }
}
export function clearBackup(storage) { try { storage.removeItem(BACKUP_KEY); } catch { /* sin almacenamiento */ } }

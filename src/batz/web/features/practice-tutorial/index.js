// Punto de unión con practice.js (script clásico): practice.js hace import() de este módulo y
// le pasa un puente con lo imprescindible. No define globals.
import {createRunner} from './card.js';
import {homePanel, openRulesDialog} from './guide.js';
import {readTutorialState, writeTutorialState, shouldOfferTutorial, readBackup, clearBackup, finalRecord} from './tutorial.js';
import {TUTORIAL_EXERCISE} from './steps.js';

/** api: {root, getProgress(), setRecord(id, rec), open(id), currentId(), getBank(), refreshHome()} */
export function attach(api) {
  let storage = null;
  try { storage = localStorage; } catch { /* sin almacenamiento: el tutorial sigue funcionando */ }
  const runner = createRunner(api, {storage});
  const startTutorial = () => runner.start();
  const openRules = opener => openRulesDialog({rules: api.getBank().rules, opener, onTutorial: startTutorial});
  return {
    /** Si se cerró la pestaña a mitad del tutorial, devuelve el registro del ejercicio 01 a su sitio. */
    recover() {
      const backup = readBackup(storage); if (!backup) return;
      api.setRecord(TUTORIAL_EXERCISE, finalRecord(backup.snapshot, api.getProgress()[TUTORIAL_EXERCISE]));
      clearBackup(storage);
    },
    homeGuide() {
      return homePanel({offer: shouldOfferTutorial(readTutorialState(storage)), onStart: startTutorial,
        onDismiss: () => { writeTutorialState(storage, 'omitido'); api.refreshHome(); }, onRules: openRules});
    },
    rulesButton() {
      const b = document.createElement('button'); b.type = 'button'; b.id = 'pr-rules'; b.className = 'pr-button pr-quiet pr-rules-button';
      b.textContent = 'Reglas'; b.setAttribute('aria-haspopup', 'dialog');
      b.addEventListener('click', () => openRules(b)); return b;
    },
    isActive: () => runner.isActive(),
  };
}

import {hashFor} from '../../app/navigation.js';
import {CARDS as LEARN_CARDS, HISTORY} from '../learn/data.js';
import {braid, enhanceHome} from './motion.js';
import {renderCarousel} from './carousel.js';

// Ejercicios de Practicar (src/batz/practice_bank.py, len(EXERCISES)); se verifica a mano al cambiar el banco.
export const PRACTICE_COUNT = 50;

// Inicio: tarjetas de las cuatro herramientas y tres ejercicios progresivos.
// Cada ejercicio es un dato; quien lo ejecuta (app.js) abre el módulo y carga sus entradas.
export const CARDS = [
  {route: 'evaluate', title: 'Evaluar modelo', purpose: 'Comprueba si una fórmula es verdadera en una interpretación que tú defines.', example: '∀x(P(x) → Q(x)) en un modelo explícito'},
  {route: 'prove', title: 'Demostrar', purpose: 'Pregunta si una conclusión se sigue de unas premisas, en todos los modelos.', example: '∀x(P(x) → Q(x)), P(a) ⊢ Q(a)'},
  {route: 'notebook', title: 'Cuadernos', purpose: 'Haz preguntas a tus textos y obtén respuestas con cita, prueba o contramodelo.', example: '«¿Juan aprueba?»'},
  {route: 'dictionary', title: 'Diccionario', purpose: 'Consulta palabras, formas, categorías y símbolos; añade las que falten.', example: '«abandonar»'},
];
export const EXERCISES = [
  {id: 'evaluate', route: 'evaluate', title: '1 · Evalúa una fórmula', does: 'Carga D = {0, 1}, P = {0}, Q = {1} y ∀x (P(x) → Q(x)), y te deja en el paso de la fórmula.', watch: 'Pulsa «Verificar» y observa por qué es falsa: x = 0 cumple P y no cumple Q.'},
  {id: 'prove', route: 'prove', title: '2 · Demuestra una consecuencia', does: 'Carga las premisas ∀x (Humano(x) → Mortal(x)) y Humano(socrates), con la conclusión Mortal(socrates).', watch: 'Pulsa «Buscar prueba» y sigue cada línea Fitch con su regla.'},
  {id: 'notebook', route: 'notebook', title: '3 · Consulta unas fuentes', does: 'Crea el cuaderno de ejemplo con textos en español.', watch: 'Pregunta «¿Juan aprueba?» y abre la cita que respalda la respuesta.'},
];

/** Del teorema al ejercicio: cada tarjeta carga en Demostrar un caso que ilustra un resultado de Gödel o de Turing. */
export const CONNECTIONS = [
  {id: 'goedel-completitud', route: 'prove', who: 'Gödel · completitud (1929)', title: 'Lo que se sigue, se demuestra',
   does: 'Carga ∀x (Humano(x) → Mortal(x)), Humano(socrates) ⊢ Mortal(socrates).',
   watch: 'Pulsa «Buscar prueba»: Bat’z halla la derivación y el verificador la acepta. Si en todos los modelos vale, hay prueba: ese es el puente entre Evaluar y Demostrar.',
   proof: {premises: '∀x (Humano(x) → Mortal(x))\nHumano(socrates)', conclusion: 'Mortal(socrates)', constants: 'socrates'}},
  {id: 'goedel-contramodelo', route: 'prove', who: 'Tarski y Gödel · modelos', title: 'Lo que no se sigue, tiene un contramodelo',
   does: 'Carga ∀x ∃y Ama(x, y) ⊢ ∃y ∀x Ama(x, y): cambiar el orden de ∀ y ∃ cambia el significado.',
   watch: 'Pulsa «Buscar prueba»: no hay prueba, y Bat’z muestra un modelo concreto donde las premisas son verdaderas y la conclusión falsa. Ábrelo en Evaluar.',
   proof: {premises: '∀x ∃y Ama(x, y)', conclusion: '∃y ∀x Ama(x, y)', constants: ''}},
  {id: 'turing-inconclusa', route: 'prove', who: 'Turing y Church · indecidibilidad (1936)', title: 'A veces la búsqueda no decide',
   does: 'Carga transitividad, irreflexividad y serialidad de R ⊢ ∃x ∀y ¬R(y, x).',
   watch: 'Pulsa «Buscar prueba»: queda «Búsqueda inconclusa». No decide la consecuencia: no es «falsa» ni «demostrada». No existe un algoritmo que decida toda consecuencia de primer orden.',
   proof: {premises: '∀x ∀y ∀z ((R(x, y) ∧ R(y, z)) → R(x, z))\n∀x ¬R(x, x)\n∀x ∃y R(x, y)', conclusion: '∃x ∀y ¬R(y, x)', constants: ''}},
];

const SVGNS = 'http://www.w3.org/2000/svg';
function svgEl(tag, attrs) { const el = document.createElementNS(SVGNS, tag); for (const k in attrs) el.setAttribute(k, attrs[k]); return el; }
function arrow(down) {
  const svg = svgEl('svg', {class: down ? 'arr down' : 'arr', viewBox: down ? '0 0 12 20' : '0 0 20 12', 'aria-hidden': 'true', focusable: 'false'});
  svg.append(svgEl('path', {d: down ? 'M6 1v17M1.500 13l4.500 5 4.500-5' : 'M1 6h17M13 1.5 18 6l-5 4.5'}));
  return svg;
}

let teardown = null;

export function renderHome(host, {go, runExercise}) {
  if (teardown) { teardown(); teardown = null; }
  host.replaceChildren();
  const make = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };
  const root = host.closest('.home') || host;

  // Titular: la propuesta de valor, con «hilo» subrayado por un trazo que se dibuja.
  const heading = root.querySelector('#home-heading');
  if (heading) {
    const hilo = make('span', 'hilo', 'hilo');
    hilo.append(svgEl('svg', {viewBox: '0 0 100 12', preserveAspectRatio: 'none', 'aria-hidden': 'true', focusable: 'false'}));
    hilo.lastChild.append(svgEl('path', {d: 'M2 7C14 1 26 11 40 6S66 2 78 7 92 9 98 5'}));
    heading.replaceChildren('El ', hilo, ' que une la matemática en comprobaciones');
    heading.dataset.sec = '';
  }

  // Presentación: una idea, un botón principal y uno secundario.
  const hero = make('section', undefined, 'home-hero hs'); hero.dataset.sec = '';
  const lede = make('p', 'Bat’z significa «hilo». Escribe una fórmula o un razonamiento y síguelo paso a paso: cada conclusión llega con su prueba o su contramodelo, comprobados.', 'home-lede'); lede.dataset.rv = '';
  const actions = make('div', undefined, 'home-actions'); actions.dataset.rv = '';
  const start = make('button', 'Empezar', 'button primary home-cta'); start.type = 'button';
  start.setAttribute('aria-describedby', 'home-start-note'); start.append(arrow());
  start.addEventListener('click', () => runExercise(EXERCISES[0]));
  const more = make('button', 'Ver las herramientas', 'home-link'); more.type = 'button';
  more.addEventListener('click', () => {
    const t = host.querySelector('#home-tools'); if (!t) return;
    t.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
    t.focus({preventScroll: true});
  });
  more.append(arrow(true));
  const note = make('span', 'Abre Evaluar con el primer ejercicio ya cargado.', 'sr-only'); note.id = 'home-start-note';
  actions.append(start, more, note);
  const facts = make('p', undefined, 'home-facts'); facts.dataset.rv = '';
  const fact = (n, label, route) => { const a = make('a', undefined, 'fact'); a.href = hashFor(route); const b = make('b', String(n)); b.dataset.count = String(n); a.append(b, ` ${label}`); return a; };
  facts.append(fact(LEARN_CARDS.length, 'tarjetas', 'learn'), make('span', ' · ', 'sep'), fact(HISTORY.length, 'hitos', 'learn'), make('span', ' · ', 'sep'), fact(PRACTICE_COUNT, 'ejercicios', 'practice'));
  hero.append(lede, actions, facts);

  // Herramientas: lista ligera, el ejemplo en mono.
  const tools = make('section', undefined, 'home-tools-sec hs'); tools.dataset.sec = '';
  const toolsTitle = make('h3', 'Cuatro herramientas', 'hs-title'); toolsTitle.id = 'home-tools'; toolsTitle.tabIndex = -1; toolsTitle.dataset.rv = '';
  const toolsLede = make('p', 'Cada una responde una pregunta distinta sobre una fórmula.', 'hs-lede'); toolsLede.dataset.rv = '';
  const cards = make('ul', undefined, 'home-tools');
  for (const card of CARDS) {
    const item = make('li'), link = make('a', undefined, 'home-tool'); item.dataset.rv = '';
    link.href = hashFor(card.route);
    const glow = make('span', undefined, 'tool-glow'); glow.setAttribute('aria-hidden', 'true'); glow.append(make('span', undefined, 'tool-spot'));
    const head = make('span', undefined, 'tool-head'); head.append(make('strong', card.title), arrow());
    link.append(glow, head, make('span', card.purpose, 'tool-purpose'), make('code', card.example));
    item.append(link); cards.append(item);
  }
  tools.append(toolsTitle, toolsLede, cards);

  // Ejercicios: pasos numerados.
  const exSec = make('section', undefined, 'home-exercises-sec hs'); exSec.dataset.sec = ''; exSec.setAttribute('aria-labelledby', 'home-ex-title');
  const exTitle = make('h3', 'Empieza con un ejemplo', 'hs-title'); exTitle.id = 'home-ex-title'; exTitle.dataset.rv = '';
  const exLede = make('p', 'Tres ejercicios progresivos. Cargar uno reemplaza lo que haya en esa herramienta y te avisa antes.', 'hs-lede hint'); exLede.dataset.rv = '';
  const list = make('ol', undefined, 'home-exercises');
  EXERCISES.forEach((ex, i) => {
    const item = make('li'), button = make('button', 'Abrir y cargar ejemplo', 'button secondary'); button.type = 'button'; item.dataset.rv = '';
    button.append(arrow());
    button.addEventListener('click', () => runExercise(ex));
    const num = make('span', String(i + 1), 'step-n'); num.setAttribute('aria-hidden', 'true');
    const body = make('div', undefined, 'step-body');
    body.append(make('strong', ex.title.replace(/^\d+\s*·\s*/, '')), make('p', ex.does), make('p', ex.watch, 'hint'), button);
    item.append(num, body);
    list.append(item);
  });
  exSec.append(exTitle, exLede, list);

  // Puente a Demostrar: un ejercicio por resultado de Gödel o de Turing.
  const bridge = make('section', undefined, 'home-bridge hs'); bridge.dataset.sec = ''; bridge.setAttribute('aria-labelledby', 'home-bridge-title');
  const bridgeTitle = make('h3', 'Practica lo que probaron Gödel y Turing', 'hs-title'); bridgeTitle.id = 'home-bridge-title'; bridgeTitle.dataset.rv = '';
  const bridgeList = make('ul', undefined, 'home-bridge-list');
  for (const item of CONNECTIONS) {
    const li = make('li'), button = make('button', 'Cargar en Demostrar', 'button secondary'); button.type = 'button'; li.dataset.rv = '';
    button.append(arrow());
    button.addEventListener('click', () => runExercise(item));
    li.append(make('span', item.who, 'bridge-who'), make('strong', item.title), make('p', item.does), make('p', item.watch, 'hint'), button);
    bridgeList.append(li);
  }
  bridge.append(bridgeTitle, bridgeList);

  const flow = make('div', undefined, 'home-flow');
  flow.append(braid(), hero, tools, exSec, renderCarousel({arrow}), bridge, make('span', undefined, 'home-end'));
  host.append(flow);
  teardown = enhanceHome(root);
}

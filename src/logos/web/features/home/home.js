import {hashFor} from '../../app/navigation.js';

// Inicio: tarjetas de las cuatro herramientas y tres ejercicios progresivos.
// Cada ejercicio es un dato; quien lo ejecuta (app.js) abre el módulo y carga sus entradas.
export const CARDS = [
  {route: 'evaluate', title: 'Evaluar modelo', purpose: 'Comprueba si una fórmula es verdadera en una interpretación que tú defines.', example: '∀x(P(x) → Q(x)) en un modelo explícito'},
  {route: 'prove', title: 'Demostrar', purpose: 'Pregunta si una conclusión se sigue de unas premisas, en todos los modelos.', example: '∀x(P(x) → Q(x)), P(a) ⊢ Q(a)'},
  {route: 'notebook', title: 'Cuadernos', purpose: 'Haz preguntas a tus textos y obtén respuestas con cita, prueba o contramodelo.', example: '«¿Juan aprueba?»'},
  {route: 'dictionary', title: 'Diccionario', purpose: 'Consulta palabras, formas, categorías y símbolos; añade las que falten.', example: '«abandonar»'},
];
export const EXERCISES = [
  {id: 'evaluate', route: 'evaluate', title: '1 · Evalúa una fórmula', does: 'Carga D = {0, 1}, P = {0}, Q = {1} y ∀x (P(x) → Q(x)).', watch: 'Pulsa «Evaluar» y observa por qué es falsa: x = 0 cumple P y no cumple Q.'},
  {id: 'prove', route: 'prove', title: '2 · Demuestra una consecuencia', does: 'Carga las premisas ∀x (Humano(x) → Mortal(x)) y Humano(socrates), con la conclusión Mortal(socrates).', watch: 'Pulsa «Buscar prueba» y sigue cada línea Fitch con su regla.'},
  {id: 'notebook', route: 'notebook', title: '3 · Consulta unas fuentes', does: 'Crea el cuaderno de ejemplo con textos en español.', watch: 'Pregunta «¿Juan aprueba?» y abre la cita que respalda la respuesta.'},
];

export function renderHome(host, {go, runExercise}) {
  host.replaceChildren();
  const make = (tag, text, cls) => { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (cls) el.className = cls; return el; };
  const cards = make('ul', undefined, 'home-cards');
  for (const card of CARDS) {
    const item = make('li'), link = make('a', undefined, 'home-card');
    link.href = hashFor(card.route);
    link.append(make('strong', card.title), make('span', card.purpose), make('code', card.example));
    item.append(link); cards.append(item);
  }
  const list = make('ol', undefined, 'home-exercises');
  for (const ex of EXERCISES) {
    const item = make('li'), button = make('button', 'Abrir y cargar ejemplo', 'button primary'); button.type = 'button';
    button.addEventListener('click', () => runExercise(ex));
    item.append(make('strong', ex.title), make('p', ex.does), make('p', ex.watch, 'hint'), button);
    list.append(item);
  }
  host.append(cards, make('h3', 'Empieza con un ejemplo'), make('p', 'Tres ejercicios progresivos. Cargar uno reemplaza lo que haya en esa herramienta y te avisa antes.', 'hint'), list);
}

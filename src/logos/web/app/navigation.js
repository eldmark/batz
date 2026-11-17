// Rutas de la aplicación: funciones puras, sin DOM, para poder probarlas en Node.
export const ROUTES = [
  {id: 'home', hash: '#/inicio', title: 'Inicio'},
  {id: 'evaluate', hash: '#/evaluar', title: 'Evaluar modelo'},
  {id: 'prove', hash: '#/demostrar', title: 'Demostrar'},
  {id: 'practice', hash: '#/practicar', title: 'Practicar'},
  {id: 'notebook', hash: '#/cuadernos', title: 'Cuadernos'},
  {id: 'dictionary', hash: '#/diccionario', title: 'Diccionario'},
  {id: 'learn', hash: '#/aprender', title: 'Aprender'},
  // Páginas de personas: no están en la barra lateral (`nav: false`); `person` es la clave en people.js.
  {id: 'godel', hash: '#/godel', title: 'Kurt Gödel', nav: false, person: 'godel'},
  {id: 'turing', hash: '#/turing', title: 'Alan Turing', nav: false, person: 'turing'},
  {id: 'church', hash: '#/church', title: 'Alonzo Church', nav: false, person: 'church'},
];

const byId = new Map(ROUTES.map(route => [route.id, route]));
const byHash = new Map(ROUTES.map(route => [route.hash, route]));

/** Un hash desconocido, o ninguno, lleva a Inicio. */
export function routeFromHash(hash) {
  if (hash === '#practicar') return 'practice';   // enlace anterior al rediseño
  return (byHash.get(String(hash || '').replace(/\/+$/, '')) ?? byId.get('home')).id;
}
export function hashFor(id) { return (byId.get(id) ?? byId.get('home')).hash; }
export function titleFor(id) { return (byId.get(id) ?? byId.get('home')).title; }
export function isKnownHash(hash) { return hash === '#practicar' || byHash.has(String(hash || '').replace(/\/+$/, '')); }
/** Clave de people.js si la ruta es la página de una persona; si no, null. */
export function personFor(id) { return byId.get(id)?.person ?? null; }

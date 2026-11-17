// Rutas de la aplicación: funciones puras, sin DOM, para poder probarlas en Node.
export const ROUTES = [
  {id: 'home', hash: '#/inicio', title: 'Inicio'},
  {id: 'evaluate', hash: '#/evaluar', title: 'Evaluar modelo'},
  {id: 'prove', hash: '#/demostrar', title: 'Demostrar'},
  {id: 'notebook', hash: '#/cuadernos', title: 'Cuadernos'},
  {id: 'dictionary', hash: '#/diccionario', title: 'Diccionario'},
];

const byId = new Map(ROUTES.map(route => [route.id, route]));
const byHash = new Map(ROUTES.map(route => [route.hash, route]));

/** Un hash desconocido, o ninguno, lleva a Inicio. */
export function routeFromHash(hash) {
  return (byHash.get(String(hash || '').replace(/\/+$/, '')) ?? byId.get('home')).id;
}
export function hashFor(id) { return (byId.get(id) ?? byId.get('home')).hash; }
export function titleFor(id) { return (byId.get(id) ?? byId.get('home')).title; }
export function isKnownHash(hash) { return byHash.has(String(hash || '').replace(/\/+$/, '')); }

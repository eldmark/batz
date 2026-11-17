// Casos de ejemplo de Evaluar: cada uno trae modelo completo, fórmula y el valor que debe salir.
// `expected` documenta el resultado esperado; la prueba de navegador lo comprueba contra el motor real.
const cycle = [[0, 1], [1, 2], [2, 0]];
const leq = [[0, 0], [0, 1], [0, 2], [1, 1], [1, 2], [2, 2]];
const mod = (n, f) => Array.from({length: n}, (_, i) => i).flatMap(x => Array.from({length: n}, (_, y) => [[x, y], f(x, y)]));

export const EXAMPLE_GROUPS = [
  {title: 'Cuantificadores básicos', items: [
    {id: 'todo-p-q-falsa', title: 'Todo P es Q (falsa)', formula: '∀x (P(x) → Q(x))', expected: false,
     domain: [0, 1], constants: {}, functions: {}, predicates: {P: [[0]], Q: [[1]]},
     note: 'x = 0 cumple P pero no Q, así que la implicación falla en 0.'},
    {id: 'todo-p-q-verdadera', title: 'Todo P es Q (verdadera)', formula: '∀x (P(x) → Q(x))', expected: true,
     domain: [0, 1], constants: {}, functions: {}, predicates: {P: [[0]], Q: [[0], [1]]},
     note: 'Todo elemento que cumple P también cumple Q.'},
    {id: 'existe-p', title: 'Existe un elemento con P', formula: '∃x P(x)', expected: true,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {P: [[1]]},
     note: 'Basta un testigo: x = 1.'},
    {id: 'ninguno-p', title: 'Ninguno cumple P (falsa)', formula: '¬∃x P(x)', expected: false,
     domain: [0, 1], constants: {}, functions: {}, predicates: {P: [[0]]},
     note: 'P(0) es verdadera, así que sí existe un elemento con P.'},
    {id: 'negar-todos', title: 'Negar «para todo»', formula: '¬∀x P(x) ↔ ∃x ¬P(x)', expected: true,
     domain: [0, 1], constants: {}, functions: {}, predicates: {P: [[0]]},
     note: 'Equivalencia clásica entre ¬∀ y ∃¬.'},
  ]},
  {title: 'Relaciones', items: [
    {id: 'todos-tienen-sucesor', title: 'Todos tienen a alguien (ciclo)', formula: '∀x ∃y R(x, y)', expected: true,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {R: cycle},
     note: 'En un ciclo, cada nodo apunta a otro.'},
    {id: 'alguien-para-todos', title: 'Alguien a quien todos apuntan (ciclo)', formula: '∃y ∀x R(x, y)', expected: false,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {R: cycle},
     note: 'Cambiar el orden de ∃ y ∀ cambia el significado.'},
    {id: 'reflexiva', title: 'Reflexiva (≤)', formula: '∀x R(x, x)', expected: true,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {R: leq}},
    {id: 'transitiva', title: 'Transitiva (≤)', formula: '∀x ∀y ∀z ((R(x, y) ∧ R(y, z)) → R(x, z))', expected: true,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {R: leq}},
    {id: 'simetrica-falla', title: 'Simétrica (falla en el ciclo)', formula: '∀x ∀y (R(x, y) → R(y, x))', expected: false,
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {R: cycle},
     note: 'R(0, 1) es verdadera, pero R(1, 0) no.'},
    {id: 'variable-libre', title: 'Variables libres con entorno', formula: 'P(x) ∧ R(x, y)', expected: true, assignment: {x: 2, y: 0},
     domain: [0, 1, 2], constants: {}, functions: {}, predicates: {P: [[0], [2]], R: cycle},
     note: 'La fórmula no es cerrada: el resultado depende de x e y.'},
  ]},
  {title: 'Funciones, constantes e igualdad', items: [
    {id: 'sucesor', title: 'Sucesor en el ciclo', formula: '∀x (P(x) → P(s(x)))', expected: false,
     domain: [0, 1, 2], constants: {a: 0}, functions: {s: [[[0], 1], [[1], 2], [[2], 0]]}, predicates: {P: [[0], [2]]},
     note: 'P(0) es verdadera pero P(s(0)) = P(1) no.'},
    {id: 'conmutativa', title: 'Suma módulo 2 es conmutativa', formula: '∀x ∀y (suma(x, y) = suma(y, x))', expected: true,
     domain: [0, 1], constants: {}, functions: {suma: mod(2, (x, y) => (x + y) % 2)}, predicates: {P: [[0]]}},
    {id: 'neutro', title: 'Existe elemento neutro', formula: '∃e ∀x suma(x, e) = x', expected: true,
     domain: [0, 1], constants: {}, functions: {suma: mod(2, (x, y) => (x + y) % 2)}, predicates: {P: [[0]]},
     note: 'e = 0 es el neutro de la suma módulo 2.'},
    {id: 'dos-elementos', title: 'Hay al menos dos elementos', formula: '∃x ∃y ¬(x = y)', expected: true,
     domain: [0, 1], constants: {}, functions: {}, predicates: {P: [[0]]}},
    {id: 'constante', title: 'Una constante con nombre', formula: 'P(a) ∧ ¬Q(a)', expected: true,
     domain: [0, 1], constants: {a: 0}, functions: {}, predicates: {P: [[0]], Q: [[1]]}},
  ]},
  {title: 'Con nombres (para exponer)', items: [
    {id: 'estudiantes', title: 'Todos los estudiantes aprueban', formula: '∀x (Estudiante(x) → Aprueba(x))', expected: false,
     domain: ['Ana', 'Luis', 'Marta'], constants: {}, functions: {},
     predicates: {Estudiante: [['Ana'], ['Luis']], Aprueba: [['Ana'], ['Marta']]},
     note: 'Luis es estudiante y no aprueba.'},
    {id: 'alguien-aprueba', title: 'Algún estudiante aprueba', formula: '∃x (Estudiante(x) ∧ Aprueba(x))', expected: true,
     domain: ['Ana', 'Luis', 'Marta'], constants: {}, functions: {},
     predicates: {Estudiante: [['Ana'], ['Luis']], Aprueba: [['Ana'], ['Marta']]},
     note: 'Ana es estudiante y aprueba.'},
  ]},
];

export const EXAMPLES = EXAMPLE_GROUPS.flatMap(group => group.items);
export const defaultExample = EXAMPLES[0];

/** Frases en español listas para «Escribir en español». */
export const SPANISH_PHRASES = [
  'Todos los estudiantes leyeron un libro',
  'Todo estudiante aprueba',
  'Algún estudiante aprueba',
  'Todos los perros ladran',
  'Todo humano es mortal',
  'Ningún perro vuela',
  'Algún animal no ladra',
  'Ana lee un libro',
];

/** Formato de paquete que usa la interfaz: firma y modelo serializados. */
export function examplePackage(example) {
  const signature = {constants: Object.keys(example.constants),
    functions: Object.fromEntries(Object.entries(example.functions).map(([name, table]) => [name, table[0][0].length])),
    predicates: Object.fromEntries(Object.entries(example.predicates).map(([name, tuples]) => [name, tuples[0].length]))};
  const model = {domain: example.domain, constants: example.constants,
    functions: Object.fromEntries(Object.entries(example.functions).map(([name, table]) => [name, {arity: table[0][0].length, table}])),
    predicates: Object.fromEntries(Object.entries(example.predicates).map(([name, tuples]) => [name, {arity: tuples[0].length, tuples}]))};
  return {signature, model, formula: example.formula};
}

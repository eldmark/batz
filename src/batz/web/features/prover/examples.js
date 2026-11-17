// Casos que se comprueban con /api/proof; expected es el veredicto esperado.
export const PROOF_EXAMPLE_GROUPS = [
  {title: 'Reglas proposicionales', items: [
    {id: 'modus-ponens', title: 'Modus ponens', premises: 'p → q\np', conclusion: 'q', constants: '', expected: 'proved',
     note: 'De «si p, entonces q» y p se obtiene q.'},
    {id: 'modus-tollens', title: 'Modus tollens', premises: 'p → q\n¬q', conclusion: '¬p', constants: '', expected: 'proved',
     note: 'Si q es falsa y p implica q, entonces p es falsa.'},
    {id: 'cadena', title: 'Cadena de implicaciones', premises: 'p → q\nq → r', conclusion: 'p → r', constants: '', expected: 'proved',
     note: 'Supón p y encadena las dos implicaciones para llegar a r.'},
    {id: 'conjuncion', title: 'Construir una conjunción', premises: 'p\nq', conclusion: 'p ∧ q', constants: '', expected: 'proved',
     note: 'Dos premisas permiten reunir p y q en una conjunción.'},
    {id: 'casos', title: 'Razonamiento por casos', premises: 'p ∨ q\np → r\nq → r', conclusion: 'r', constants: '', expected: 'proved',
     note: 'Tanto el caso p como el caso q llevan a r.'},
  ]},
  {title: 'Cuantificadores y relaciones', items: [
    {id: 'socrates', title: 'Sócrates es mortal', premises: '∀x (Humano(x) → Mortal(x))\nHumano(socrates)', conclusion: 'Mortal(socrates)', constants: 'socrates', expected: 'proved',
     note: 'Aplica la premisa universal a Sócrates y usa modus ponens.'},
    {id: 'testigo', title: 'De un caso a una existencia', premises: 'Estudiante(ana)\nAprueba(ana)', conclusion: '∃x (Estudiante(x) ∧ Aprueba(x))', constants: 'ana', expected: 'proved',
     note: 'Ana sirve como testigo de que algún estudiante aprueba.'},
    {id: 'universal', title: 'Encadenar dos reglas universales', premises: '∀x (P(x) → Q(x))\n∀x (Q(x) → R(x))', conclusion: '∀x (P(x) → R(x))', constants: '', expected: 'proved',
     note: 'Razona con un elemento arbitrario y después generaliza.'},
    {id: 'existencial', title: 'Transportar una existencia', premises: '∃x P(x)\n∀x (P(x) → Q(x))', conclusion: '∃x Q(x)', constants: '', expected: 'proved',
     note: 'El testigo de P también cumple Q, aunque no sepamos su nombre.'},
    {id: 'relacion', title: 'Aplicar una relación simétrica', premises: '∀x ∀y (Amigo(x, y) → Amigo(y, x))\nAmigo(ana, luis)', conclusion: 'Amigo(luis, ana)', constants: 'ana, luis', expected: 'proved',
     note: 'Instancia la regla con Ana y Luis para invertir la relación.'},
  ]},
  {title: 'Lógica clásica sin premisas', items: [
    {id: 'identidad', title: 'Una proposición se implica a sí misma', premises: '', conclusion: 'p → p', constants: '', expected: 'proved',
     note: 'Abre una hipótesis p y ciérrala para obtener p → p.'},
    {id: 'peirce', title: 'Ley de Peirce', premises: '', conclusion: '((p → q) → p) → p', constants: '', expected: 'proved',
     note: 'Una tautología clásica que no necesita premisas.'},
  ]},
  {title: 'Inferencias inválidas: buscar un contramodelo', items: [
    {id: 'afirmar-consecuente', title: 'Afirmar el consecuente', premises: 'p → q\nq', conclusion: 'p', constants: '', expected: 'refuted',
     note: 'q podría ser verdadera y p falsa. Busca el contramodelo.'},
    {id: 'generalizar-caso', title: 'Un caso no demuestra «todos»', premises: 'P(a)', conclusion: '∀x P(x)', constants: 'a', expected: 'refuted',
     note: 'P(a) no dice qué ocurre con los demás elementos del dominio.'},
    {id: 'orden-cuantificadores', title: 'Cambiar el orden de ∀ y ∃', premises: '∀x ∃y Ama(x, y)', conclusion: '∃y ∀x Ama(x, y)', constants: '', expected: 'refuted',
     note: 'Que cada persona ame a alguien no exige que todas amen a la misma persona.'},
  ]},
];

export const PROOF_EXAMPLES = PROOF_EXAMPLE_GROUPS.flatMap(group => group.items);

// Datos del tutorial «Tu primera prueba en 2 minutos». Se hace sobre el ejercicio 01 real
// (premisa P ∧ Q, objetivo P). Sin lógica: la evaluación vive en tutorial.js.
export const TUTORIAL_EXERCISE = '01';
export const NEXT_EXERCISE = '02';
export const START_RULE = 'and_e2';   // el tutorial empieza con otra regla elegida, para que elegir ∧E₁ sea una acción real
export const TARGET_RULE = 'and_e1';
export const TARGET_REFS = [1];
export const TARGET_FORMULA = 'P';

export const STEPS = [
  {id: 'objetivo', title: 'Mira el objetivo y la premisa', targets: ['.pr-goal', '.pr-line'], ack: 'Entendido',
    text: 'Arriba está tu OBJETIVO: la fórmula P. Debajo, en la línea 1, la premisa P ∧ Q, que ya es verdadera por hipótesis. Tu trabajo es llegar de la una a la otra con pasos verificados.'},
  {id: 'regla', title: 'Elige la regla', targets: ['#pr-rule'], action: 'rule',
    text: 'Abre «1. Elige la regla» y selecciona ∧E₁ · Extraer izquierda: de una conjunción A ∧ B sacas A, la parte izquierda.',
    how: 'Elegí ∧E₁ por ti.'},
  {id: 'citar', title: 'Cita la línea 1', targets: ['#pr-refs', '.pr-line-number'], action: 'refs',
    text: 'En «2. Cita las líneas» escribe 1, o toca el número 01 de la premisa. Las líneas se citan en el orden que pide la regla; aquí solo hay una.',
    how: 'Cité la línea 1 por ti.'},
  {id: 'formula', title: 'Escribe la fórmula nueva', targets: ['#pr-formula'], action: 'formula',
    text: 'En «3. Escribe la nueva fórmula» escribe P, lo que obtienes de P ∧ Q con ∧E₁.',
    how: 'Escribí P por ti.'},
  {id: 'comprobar', title: 'Pulsa «Comprobar paso»', targets: ['#pr-check'], action: 'check',
    text: 'Pulsa «Comprobar paso» (o Ctrl / ⌘ + Enter). El servidor verifica la línea: si es correcta se añade como línea 2 con una marca verificada.',
    how: 'Pulsé «Comprobar paso» por ti.'},
  {id: 'cierre', title: 'Ya tienes tu primera prueba', targets: ['#pr-success'], last: true,
    text: 'La línea 2 quedó verificada y llegó al objetivo. Cuando lo necesites: «Necesito una pista» ayuda sin restar nada, «Deshacer» quita la última línea, «Reiniciar» empieza de cero y «Reglas» abre las reglas y la chuleta. El ejercicio 02 te espera.'},
];

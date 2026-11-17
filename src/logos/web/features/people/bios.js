// Fichas de las tres personas con página propia (#/godel, #/turing, #/church) y datos del carrusel de Inicio.
// Solo datos verificables; un dato incierto se omite (null) en lugar de suponerse.
// Los años, retratos y créditos salen de people.js, que es la fuente única.
export const BIO_SLUGS = ['godel', 'turing', 'church'];

export const BIOS = {
  godel: {
    route: '#/godel',
    birthplace: 'Brünn, entonces Imperio austrohúngaro (hoy Brno)',
    deathplace: 'Princeton, Nueva Jersey',
    alt: 'Retrato fotográfico de Kurt Gödel, joven, con gafas redondas, traje y corbata a cuadros.',
    lede: 'Mostró que la lógica de primer orden es completa y que la aritmética formal no lo es.',
    carousel: {
      contribution: 'Demostró que, en lógica de primer orden, lo que es verdadero en todos los modelos tiene demostración (1929), y que ningún sistema formal consistente de la aritmética, con axiomas efectivos, demuestra todos sus enunciados (1931).',
      batz: 'Evaluar mira un modelo; Demostrar mira todos. La completitud es el puente entre ambos.',
    },
    bio: [
      'Kurt Gödel nació en 1906 en Brünn, hoy Brno, entonces parte del Imperio austrohúngaro.',
      'Estudió en la Universidad de Viena. Presentó en 1929 su tesis doctoral, dirigida por Hans Hahn, sobre la completitud del cálculo de predicados de primer orden; se publicó como artículo en 1930.',
      'En 1931 publicó los teoremas de incompletitud: en un sistema formal consistente, con axiomas dados por un procedimiento efectivo y capaz de expresar la aritmética elemental, hay enunciados que el sistema no puede ni demostrar ni refutar. Tampoco puede demostrar su propia consistencia.',
      'Entre 1938 y 1940 publicó la prueba de que el axioma de elección y la hipótesis generalizada del continuo son consistentes con los demás axiomas de la teoría de conjuntos (ZF), usando el universo construible L.',
      'Se instaló en Estados Unidos en 1940 y trabajó en el Instituto de Estudios Avanzados de Princeton, donde murió en 1978.',
    ],
    contributions: [
      {year: '1929', text: 'Completitud de la lógica de primer orden: toda fórmula válida es demostrable (tesis; publicada en 1930).'},
      {year: '1931', text: 'Teoremas de incompletitud, con el método de la numeración de Gödel.'},
      {year: '1938–1940', text: 'Publica la consistencia del axioma de elección y de la hipótesis generalizada del continuo mediante el universo construible L.'},
    ],
    batz: [
      {text: 'La completitud: si una conclusión vale en todos los modelos, existe una prueba. «Demostrar» busca esa prueba y «Evaluar» comprueba una fórmula en un solo modelo.', href: '#/demostrar', label: 'Abrir Demostrar'},
      {text: 'Un contramodelo muestra por qué una conclusión no se sigue; puedes abrirlo y evaluarlo en un modelo concreto.', href: '#/evaluar', label: 'Abrir Evaluar'},
    ],
    exercise: {id: 'goedel-completitud', label: 'Cargar el ejemplo de completitud en Demostrar'},
    timeline: [
      {year: '1906', text: 'Nace en Brünn (hoy Brno).'},
      {year: '1929', text: 'Presenta en Viena su tesis doctoral sobre la completitud.'},
      {year: '1931', text: 'Publica los teoremas de incompletitud.'},
      {year: '1938–1940', text: 'Publica la consistencia del axioma de elección y de la hipótesis generalizada del continuo.'},
      {year: '1940', text: 'Se instala en Estados Unidos y trabaja en el Instituto de Estudios Avanzados de Princeton.'},
      {year: '1978', text: 'Muere en Princeton.'},
    ],
    reading: [
      '«Über formal unentscheidbare Sätze der Principia Mathematica und verwandter Systeme I», Kurt Gödel (1931).',
      '«The Consistency of the Continuum Hypothesis», Kurt Gödel (1940).',
      '«Gödel’s Proof», Ernest Nagel y James R. Newman (1958).',
      '«Gödel, Escher, Bach», Douglas Hofstadter (1979).',
    ],
    related: ['turing', 'church'],
  },
  turing: {
    route: '#/turing',
    birthplace: 'Londres',
    deathplace: 'Wilmslow, Inglaterra',
    alt: 'Retrato fotográfico de Alan Turing con la mirada hacia un lado, de chaqueta de tweed, camisa y corbata oscura.',
    lede: 'Definió qué es calcular con un algoritmo y mostró que hay preguntas que ningún algoritmo responde.',
    carousel: {
      contribution: 'En 1936 definió la máquina de Turing y probó que ningún algoritmo decide el problema de decisión de la lógica de primer orden.',
      batz: 'Por eso una búsqueda de prueba puede quedar «inconclusa», y eso no equivale a «falso».',
    },
    bio: [
      'Alan Turing nació en Londres en 1912. Estudió matemáticas en el King’s College de Cambridge, del que fue elegido fellow en 1935.',
      'En 1936 escribió «On Computable Numbers, with an Application to the Entscheidungsproblem» (publicado en 1936–1937). Describe las máquinas que hoy llevan su nombre y muestra que el problema de decisión de la lógica de primer orden no tiene solución algorítmica. Church llegó al mismo resultado ese año, por otro camino.',
      'Estudió en Princeton y se doctoró en 1938 bajo la dirección de Alonzo Church.',
      'Durante la Segunda Guerra Mundial trabajó en Bletchley Park, en el descifrado de las comunicaciones alemanas. Después diseñó el ACE, un computador para el National Physical Laboratory.',
      'En 1950 publicó «Computing Machinery and Intelligence», donde propone el juego de imitación, conocido como test de Turing. Murió en 1954.',
    ],
    contributions: [
      {year: '1936', text: 'La máquina de Turing y la indecidibilidad del problema de decisión (Entscheidungsproblem).'},
      {year: '1939–1945', text: 'Criptoanálisis en Bletchley Park.'},
      {year: '1945', text: 'Diseño del computador ACE.'},
      {year: '1950', text: 'El juego de imitación, o test de Turing.'},
    ],
    batz: [
      {text: 'Cuando «Demostrar» responde «Búsqueda inconclusa», no hay prueba ni contramodelo todavía: no existe un algoritmo que decida toda consecuencia de primer orden.', href: '#/demostrar', label: 'Abrir Demostrar'},
    ],
    exercise: {id: 'turing-inconclusa', label: 'Cargar el ejemplo inconcluso en Demostrar'},
    timeline: [
      {year: '1912', text: 'Nace en Londres.'},
      {year: '1936', text: 'Escribe «On Computable Numbers» (publicado en 1936–1937).'},
      {year: '1938', text: 'Se doctora en Princeton bajo Alonzo Church.'},
      {year: '1939–1945', text: 'Trabaja en Bletchley Park.'},
      {year: '1950', text: 'Publica «Computing Machinery and Intelligence».'},
      {year: '1954', text: 'Muere en Wilmslow.'},
    ],
    reading: [
      '«On Computable Numbers, with an Application to the Entscheidungsproblem», Alan Turing (1936).',
      '«Computing Machinery and Intelligence», Alan Turing (1950).',
      '«Alan Turing: The Enigma», Andrew Hodges (1983).',
    ],
    related: ['church', 'godel'],
  },
  church: {
    route: '#/church',
    birthplace: 'Washington D. C.',
    deathplace: null,
    alt: 'Fotografía en blanco y negro de Alonzo Church, de perfil, con camisa y corbata, señalando con la mano una pizarra con fórmulas.',
    lede: 'Creó el cálculo lambda y demostró, en 1936, que la validez en lógica de primer orden es indecidible.',
    carousel: {
      contribution: 'Creó el cálculo lambda en los años treinta y en 1936 demostró que no hay algoritmo que decida la validez en lógica de primer orden, el mismo año que Turing.',
      batz: 'Su resultado, junto con el de Turing, explica por qué Demostrar puede responder «búsqueda inconclusa».',
    },
    bio: [
      'Alonzo Church nació en 1903 en Washington D. C. Se doctoró en la Universidad de Princeton en 1927, con Oswald Veblen, y enseñó allí desde 1929; más tarde pasó a la UCLA.',
      'En los años treinta desarrolló el cálculo lambda, un formalismo para definir funciones por abstracción y aplicación, base teórica de los lenguajes de programación funcionales.',
      'En 1936 publicó un resultado sobre la indecidibilidad del problema de decisión de la lógica de primer orden. Turing llegó a la misma conclusión ese año con otro método.',
      'Ese mismo año propuso identificar las funciones calculables de manera efectiva con las definibles en el cálculo lambda. Junto con la caracterización de Turing por máquinas, es lo que se conoce como la tesis de Church–Turing: es una tesis y no un teorema, porque identifica una noción informal con una formal.',
      'Fue uno de los fundadores del Journal of Symbolic Logic (1936) y dirigió las tesis doctorales de Alan Turing (1938) y de Stephen Kleene. Murió en 1995.',
    ],
    contributions: [
      {year: 'Años 30', text: 'El cálculo lambda, un modelo de cómputo basado en funciones.'},
      {year: '1936', text: 'Indecidibilidad del problema de decisión de la lógica de primer orden.'},
      {year: '1936', text: 'La tesis de Church: calculable de manera efectiva equivale a definible en el cálculo lambda (o recursivo).'},
      {year: '1936', text: 'Cofundación del Journal of Symbolic Logic.'},
    ],
    batz: [
      {text: 'La indecidibilidad de la lógica de primer orden es la razón de fondo de que «Demostrar» pueda terminar sin veredicto. Esa respuesta nunca equivale a «falso» ni a una demostración.', href: '#/demostrar', label: 'Abrir Demostrar'},
    ],
    exercise: {id: 'turing-inconclusa', label: 'Cargar el ejemplo inconcluso en Demostrar'},
    timeline: [
      {year: '1903', text: 'Nace en Washington D. C.'},
      {year: '1927', text: 'Se doctora en Princeton.'},
      {year: 'Años 30', text: 'Desarrolla el cálculo lambda.'},
      {year: '1936', text: 'Publica su resultado sobre el problema de decisión y propone la tesis de Church.'},
      {year: '1938', text: 'Dirige la tesis doctoral de Alan Turing.'},
      {year: '1995', text: 'Muere.'},
    ],
    reading: [
      '«An Unsolvable Problem of Elementary Number Theory», Alonzo Church (1936).',
      '«A Note on the Entscheidungsproblem», Alonzo Church (1936).',
      '«The Calculi of Lambda-Conversion», Alonzo Church (1941).',
      '«Introduction to Mathematical Logic», Alonzo Church (1944; edición revisada de 1956).',
    ],
    related: ['turing', 'godel'],
  },
};

export function bio(slug) { return Object.prototype.hasOwnProperty.call(BIOS, slug) ? BIOS[slug] : null; }

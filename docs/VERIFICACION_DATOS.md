# Verificación de datos históricos y matemáticos

Contraste de los textos de `learn/data.js`, `people/bios.js`, `people/people.js` y `home/home.js` con fuentes consultadas el 2026-11-17. No se envió ningún dato del proyecto en las consultas.

Fuentes (abreviaturas): **SEP** = Stanford Encyclopedia of Philosophy; **WP** = Wikipedia en inglés (API y páginas); **MT** = MacTutor.
Veredictos: correcta / corregida / eliminada / no verificada (no se pudo contrastar con fuente consultada).

## Correcciones

| Afirmación (antes) | Archivo | Veredicto | Fuente(s) | Nota |
|---|---|---|---|---|
| Löwenheim (1915) y Skolem (1920) probaron que todo conjunto numerable de sentencias con modelo tiene uno numerable | learn/data.js (hito y tarjeta) | corregida | https://en.wikipedia.org/wiki/L%C3%B6wenheim%E2%80%93Skolem_theorem ; https://plato.stanford.edu/entries/logic-firstorder-emergence/ | Löwenheim 1915: una sentencia satisfacible lo es en un modelo numerable. Skolem 1920 (con elección) y 1922 (sin ella): teorías numerables. Se atribuye cada versión a su autor. |
| «Los axiomas de primer orden no pueden fijar el tamaño de un modelo infinito» | learn/data.js | corregida | https://en.wikipedia.org/wiki/L%C3%B6wenheim%E2%80%93Skolem_theorem | La versión descendente sola no lo dice (hace falta la ascendente); se reformula a lo que sí implica. |
| Gödel «se doctora en 1929» | bios.js | corregida | https://plato.stanford.edu/entries/goedel/ ; https://mathshistory.st-andrews.ac.uk/Biographies/Godel/ ; https://en.wikipedia.org/wiki/Kurt_G%C3%B6del | SEP y MT dan 1929 para la tesis; WP dice que el título se concedió en 1930. Se dice «presentó su tesis en 1929 (dirigida por Hahn); publicada en 1930». |
| Gödel «entre 1938 y 1940 probó» consistencia de AC y CH | bios.js | corregida | https://plato.stanford.edu/entries/goedel/ ; https://en.wikipedia.org/wiki/Kurt_G%C3%B6del | 1938–1940 son las fechas de publicación (la monografía es de 1940); la SEP da 1935–1937 para obtener los resultados. Además es la hipótesis **generalizada** del continuo, respecto de ZF. |
| «ningún sistema formal de la aritmética lo abarca todo» | bios.js (carrusel) | corregida | https://plato.stanford.edu/entries/goedel-incompleteness/ | Se añaden las condiciones: consistente y con axiomas efectivos. |
| Incompletitud: «toda teoría consistente» | learn/data.js (hito y tarjeta) | corregida | https://plato.stanford.edu/entries/goedel-incompleteness/ | Gödel (1931) usó ω-consistencia; Rosser (1936) la rebajó a consistencia. Se añade; en la tarjeta, también el segundo teorema. |
| Completitud: «Si Γ ⊨ φ entonces Γ ⊢ φ. Gödel la demostró en 1929» | learn/data.js (tarjeta) | corregida | https://en.wikipedia.org/wiki/G%C3%B6del%27s_completeness_theorem | Gödel 1929 es para fórmulas válidas; la prueba con conjuntos arbitrarios es de Henkin (tesis 1947, publicada 1949). Con WP; la SEP no da el año de Henkin. |
| Peano: signos «∈, ∩, ∪ y ⊃» | learn/data.js | corregida | https://en.wikipedia.org/wiki/Arithmetices_principia,_nova_methodo_exposita | WP confirma ∈, ⊂, ∩, ∪; no pude confirmar ⊃ en las fuentes consultadas, así que se retira. |
| Peano: «Russell reconoció su influencia al adoptar esa notación» | learn/data.js | corregida | https://en.wikipedia.org/wiki/Giuseppe_Peano | Confirmado solo que Russell se impresionó en el congreso de París de 1900 y estudió su obra; «adoptar» no se confirmó. |
| Peirce 1885: título con minúscula; «cuantificadores sobre un dominio»; Schröder «desde 1890» | learn/data.js | corregida | https://plato.stanford.edu/entries/logic-firstorder-emergence/ ; https://en.wikipedia.org/wiki/Charles_Sanders_Peirce ; https://en.wikipedia.org/wiki/Ernst_Schr%C3%B6der_(mathematician) | Título: «…A Contribution to the Philosophy of Notation». Peirce introdujo la notación (SEP). Vorlesungen: tres volúmenes, 1890–1905. |
| Frege: «primer sistema formal con cuantificadores» | learn/data.js | corregida | https://en.wikipedia.org/wiki/Gottlob_Frege ; https://plato.stanford.edu/entries/logic-firstorder-emergence/ | Se matiza a «primera lógica de predicados axiomatizada». |
| Tarski: «versión alemana de 1935»; «es la base de la semántica de modelos» | learn/data.js | corregida | https://en.wikipedia.org/wiki/Tarski%27s_undefinability_theorem ; https://plato.stanford.edu/entries/tarski-truth/ | Studia Philosophica 1 consta como 1935 o 1936 según el catálogo; se pone «1935–1936». «Una base», no «la». |
| ∀I: constante nueva «que no aparezca en premisas ni hipótesis abiertas» | learn/data.js | corregida | Matemática estándar (sin fuente web consultada) | Falta la condición de que tampoco aparezca en la conclusión ∀x φ(x). |
| Consecuencia lógica: «todo modelo que…» | learn/data.js | corregida | Matemática estándar (sin fuente web consultada) | Se explicita «con toda asignación» (relevante si hay variables libres). |
| Paradoja de Skolem sin fecha ni precisión | learn/data.js | corregida | https://plato.stanford.edu/entries/logic-firstorder-emergence/ | Skolem 1922; se aclara ZFC y que en ella se demuestran conjuntos no numerables. |
| Church: «Introduction to Mathematical Logic» (1956) | bios.js | corregida | https://en.wikipedia.org/wiki/Alonzo_Church | WP da 1944. La edición revisada de 1956 se mantiene por conocimiento general, no por la fuente. |
| Tesis de Church: «calculable ≡ definible en cálculo lambda» | bios.js | corregida | https://plato.stanford.edu/entries/church-turing/ | Church la formuló con recursividad y con λ-definibilidad. |

## Afirmaciones confirmadas sin cambios

| Afirmación | Archivo | Veredicto | Fuente(s) | Nota |
|---|---|---|---|---|
| Aristóteles: «Analíticos primeros», silogismo; primer estudio formal de la lógica que se conserva | data.js | correcta | https://plato.stanford.edu/entries/aristotle-logic/ | La SEP dice «earliest formal study of logic that we have». |
| Leibniz: cálculo del razonamiento, no llegó a construirlo | data.js | correcta | https://plato.stanford.edu/entries/leibniz-logic-influence/ | La SEP lo describe como programa inviable en su época. «Resolver disputas calculando» (calculemus) no se encontró en la fuente: no verificada la frase literal. |
| Boole: 1847 «Mathematical Analysis of Logic», 1854 «Laws of Thought»; dos valores (0, 1) | data.js | correcta | https://plato.stanford.edu/entries/boole/ | |
| Russell: paradoja 1901, carta a Frege 1902, Grundgesetze afectado | data.js | correcta | https://en.wikipedia.org/wiki/Russell%27s_paradox | Zermelo la halló antes sin publicarla; no se menciona en el texto. |
| Principia Mathematica: tres volúmenes 1910–1913; teoría de tipos | data.js | correcta | https://en.wikipedia.org/wiki/Principia_Mathematica | |
| Programa de Hilbert en los años 20; Bernays | data.js | correcta | https://plato.stanford.edu/entries/hilbert-program/ | La SEP lo sitúa desde 1921–22. |
| Hilbert–Ackermann 1928: lógica de primer orden, completitud y Entscheidungsproblem como problemas abiertos | data.js | correcta | https://plato.stanford.edu/entries/logic-firstorder-emergence/ ; https://en.wikipedia.org/wiki/Entscheidungsproblem | La SEP confirma la completitud; el problema de decisión, WP. |
| Completitud: tesis 1929, publicada 1930 | data.js | correcta | SEP y MT (Gödel), https://en.wikipedia.org/wiki/G%C3%B6del%27s_completeness_theorem | Se añade el director, Hahn. |
| Incompletitud 1931 | data.js, bios.js | correcta | https://plato.stanford.edu/entries/goedel-incompleteness/ | |
| Tarski: verdad 1933 (polaco), consecuencia 1936, recursión | data.js | correcta | https://plato.stanford.edu/entries/tarski-truth/ ; https://plato.stanford.edu/entries/model-theory/ | |
| Gentzen 1934 y Jaśkowski 1934, deducción natural | data.js | correcta | https://plato.stanford.edu/entries/natural-deduction/ | La SEP fecha el artículo de Gentzen en 1934 (a veces 1935). |
| Fitch 1952 «Symbolic Logic: An Introduction», formato de subpruebas | data.js | correcta | https://plato.stanford.edu/entries/natural-deduction/ ; https://en.wikipedia.org/wiki/Frederic_Fitch | |
| Church y Turing 1936, independientes, Entscheidungsproblem | data.js, bios.js, home.js | correcta | https://plato.stanford.edu/entries/church-turing/ ; https://en.wikipedia.org/wiki/Alan_Turing | Church unos meses antes. |
| Robinson 1965, «A Machine-Oriented Logic Based on the Resolution Principle» | data.js | correcta | https://en.wikipedia.org/wiki/John_Alan_Robinson | J. ACM 12(1), 1965. |
| Gödel: Brünn 1906, Viena, Princeton 1978, EE. UU. en 1940, numeración, lectura (1931, 1940, Nagel–Newman 1958, Hofstadter 1979) | bios.js | correcta | MT, SEP y WP de Gödel | Gödel nació el 28-IV-1906 y murió el 14-I-1978. |
| Turing: Londres 1912, fellow de King's 1935, doctorado Princeton 1938 con Church, Bletchley, ACE (NPL), 1950 en Mind, muerte 1954 en Wilmslow | bios.js | correcta | https://en.wikipedia.org/wiki/Alan_Turing ; https://en.wikipedia.org/wiki/Computing_Machinery_and_Intelligence | «Estudió en Princeton» (1936–38) correcto. Artículo de 1936 enviado en mayo y publicado en dos partes (30-XI y 23-XII de 1936). |
| Hodges, «Alan Turing: The Enigma», 1983 | bios.js | correcta | https://en.wikipedia.org/wiki/Alan_Turing:_The_Enigma | |
| Church: Washington D. C. 1903, doctorado 1927 con Veblen, Princeton desde 1929, UCLA, JSL 1936, alumnos Kleene y Turing, muerte 1995; «Calculi of Lambda-Conversion» 1941 | bios.js | correcta | https://en.wikipedia.org/wiki/Alonzo_Church ; https://en.wikipedia.org/wiki/Stephen_Cole_Kleene | Kleene, doctorado 1934 con Church. |
| JSL fundado en 1936 | bios.js | correcta (parcial) | https://en.wikipedia.org/wiki/Journal_of_Symbolic_Logic ; Church (WP) | El año consta en ambas; «cofundador» solo en la ficha de Church. |
| Fechas de nacimiento y muerte de 21 de las 22 personas | people.js | correcta | Páginas de WP de cada persona (en.wikipedia.org/wiki/<nombre>) | Todas coinciden. **David Hilbert (1862–1943) no se consultó: no verificada.** |
| «Bat'z» significa «hilo» | home.js | correcta | https://maya.nmai.si.edu/sites/default/files/resources/Significado%20de%20los%20dias%20del%20calendario%20sagrado%20maya.pdf (resultado de búsqueda) | Día B'atz' del Cholq'ij (k'iche'), «hilo». No se abrió el PDF; se apoya en el resumen de la búsqueda. |

## Revisión matemática de las 33 tarjetas

Revisadas una a una. Sin error en: firma, término, átomo, fórmula, libre, ligada, sentencia, modelo, asignación, satisfacción, verdad, satisfacible, validez, contramodelo, regla, derivación, deducción natural, subprueba, corrección, consistencia, decidibilidad, compacidad y las seis de errores comunes. Los ejemplos se comprobaron a mano (por ejemplo, el contramodelo D = {0, 1}, R = {(0,1), (1,0)} falsifica ∃y∀x R(x, y) y satisface ∀x∃y R(x, y)). Cambios: consecuencia, ∀I, completitud, incompletitud y Löwenheim–Skolem (ver arriba). Esta revisión es matemática propia, contrastada con las definiciones estándar (SEP lógica clásica y teoría de modelos, parcialmente consultadas); no hay una fuente única para cada tarjeta.

El ejemplo de `home.js` «transitividad, irreflexividad y serialidad de R ⊢ ∃x ∀y ¬R(y, x)» es inválido (contramodelo: los enteros con <) y sus premisas solo tienen modelos infinitos; por eso la búsqueda queda inconclusa. Comprobado a mano.

## No verificado

- Texto de `alt` de las fotos y atribución/licencia de la foto de Church (ya marcada «sin verificar» en `people.js`).
- Afirmaciones sobre el comportamiento de Bat'z (p. ej. «resolución como segunda opinión»): no son hechos históricos; dependen del código.
- Leibniz: la frase «las disputas se resolverían calculando» (no se halló en la SEP consultada).
- Peano: ⊃ (retirado) y «axiomas en notación simbólica» (WP no lo confirma, se mantiene por ser el contenido conocido de la obra).
- Peirce 1885: revista exacta (American Journal of Mathematics) no confirmada; no figura en el texto.
- Turing 1936: «escribió en 1936» es correcto como fecha de terminación (28-V-1936); trabajó desde 1935.
- Gödel doctorado: las fuentes discrepan (1929 vs. 1930); el texto lo dice con cautela.

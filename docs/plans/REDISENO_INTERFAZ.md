# Rediseño de Bat’z (antes LOGOS): navegación, herramientas y explicación guiada

Fecha: 2026-11-16. Estado: **implementado e integrado** (ver
[INTEGRACION.md](entregas/INTEGRACION.md) y [ARQUITECTURA.md](../ARQUITECTURA.md)).
El texto de abajo es la especificación original, que se conserva como referencia
de criterios de aceptación; la interfaz actual puede diferir en detalles de
nombre (por ejemplo, los botones se llaman «Cargar ejemplo» e «Importar modelo»).
Base de código revisada al escribirlo: `40e636a`.

## 1. Decisiones y alcance

El usuario pidió reorganizar la interfaz conservando sus colores y prefirió
el avatar recibido de `main`. Aprobó explicitar su ubicación mostrando los pasos
de las comprobaciones y pidió instrucciones para dos agentes en paralelo.

La orientación de trabajo propuesta es un laboratorio de lógica para estudiantes:
Evaluar y Demostrar encabezan Razonamiento; Cuadernos y Diccionario forman
Conocimiento. No consta una respuesta explícita a la pregunta sobre convertir
Cuadernos en el centro del producto. Usar esta orientación como supuesto de
trabajo, sin bloquear los cambios comunes a ambos enfoques.

Conservar:

- Los valores de `tokens.css` y su significado: verde para identidad y predicados,
  ciruela para acciones principales, azul para funciones, amarillo para constantes
  y resaltados; verdadero y falso también deben llevar texto o símbolos.
- Literata para títulos, IBM Plex Sans para interfaz y explicaciones, JetBrains
  Mono NL para expresiones formales. Fuentes, Three.js y recursos locales.
- `assets/avatar/logos-avatar.blend` y `src/logos/web/avatar/logos.glb`, con sus
  animaciones, boca y parpadeo. Se puede ajustar el encuadre y el escenario.
- Evaluación por archivos, variables libres, entrada española y por voz,
  elección de lecturas, árboles, Fitch, contramodelos y edición del léxico.
- Verificadores, límites de búsqueda, formatos de datos y funcionamiento local.

No ampliar este encargo a rehacer el motor lógico, entrenar modelos, crear chat
generativo, cambiar el avatar, añadir cuentas o migrar el stack.

## 2. Estado del proyecto y puntos de intervención

| Pieza actual | Uso en el rediseño |
|---|---|
| `src/logos/web/index.html` | Cuatro módulos y una sección global de paso a paso; añadir Inicio y el nuevo contenedor de aplicación. |
| `src/logos/web/app.js` | Estado, renderizado y eventos concentrados; extraer por responsabilidades de manera gradual. |
| `src/logos/web/style.css` | Estilos globales y móviles; separar layout y estilos por función. |
| `src/logos/web/story3d.js` | Escena, avatar, selección, labios y parpadeo; reutilizar. |
| `src/logos/story.py`, `proof_story.py` | Eventos derivados de trazas o certificados verificados; conservar contrato. |
| `src/logos/countermodels.py` | Relato de búsqueda, premisas y comprobación; preservar sus diferencias. |
| `src/logos/notebook.py` | Fuentes, lecturas, preguntas, citas, pruebas y contramodelos ya implementados. |
| `src/logos/tree.py` | Árbol de estructura y evaluación; conservar todas sus entradas de interfaz. |
| `src/logos/server.py:Handler.do_GET` | Lista explícita de recursos; registrar los nuevos módulos y estilos. |

Punto de control anterior al rediseño: suite de 297 pruebas correcta, dos omitidas
en esa ejecución; las cuatro pruebas de `test_project_integration.LocalHTTP`
pasaron también fuera del sandbox. Volver a verificar sobre cada entrega.

## 3. Navegación y estado

```text
LOGOS · Laboratorio de lógica
Inicio
RAZONAMIENTO
  Evaluar modelo
  Demostrar
CONOCIMIENTO
  Cuadernos
  Diccionario
```

- Sidebar persistente de unos 240 px en escritorio y colapsable con etiquetas
  accesibles cuando solo se ven iconos. Recordar la preferencia de colapso.
- En móvil, menú lateral con botón, cierre por Escape y fondo, gestión de foco
  y `aria-expanded`. Cerrar al navegar.
- Header con sección activa, ayuda contextual y acciones específicas. Importar
  un modelo y añadir una fuente son acciones distintas, rotuladas como tales.
- Rutas hash: `#/inicio`, `#/evaluar`, `#/demostrar`, `#/cuadernos`,
  `#/diccionario`. Raíz sin hash abre Inicio. Hash desconocido lleva a Inicio.
- Atrás/Adelante y recarga deben resolver la ruta; actualizar título y enlace
  activo. Usar enlaces de navegación, no semántica de tabs para las páginas.
- Un único landmark `main`; las secciones inactivas no reciben foco.
- Cambiar de sección conserva borradores, tablas, resultados, búsqueda y
  selección. Pausa el reproductor. No es obligatorio persistir todo tras cerrar
  el navegador; una recarga debe restaurar la ruta, no promete restaurar un
  borrador no guardado. Los cuadernos mantienen su persistencia existente.
- Las respuestas asíncronas deben estar vinculadas a la petición y revisión
  de entradas que las produjo; descartar respuestas obsoletas.
- Cargar un ejemplo encima de datos existentes debe anunciar el reemplazo y
  ofrecer recuperación del estado anterior. Navegar no debe cargar ejemplos.

## 4. Inicio

Pregunta central: «¿Qué quieres aprender o comprobar hoy?».

Cuatro tarjetas con propósito, ejemplo y acceso directo:

| Tarjeta | Ejemplo |
|---|---|
| Evaluar modelo: comprobar verdad en una interpretación | `∀x(P(x) → Q(x))`, junto con un modelo explícito. |
| Demostrar: consecuencia desde premisas | `∀x(P(x) → Q(x)), P(a) ⊢ Q(a)`. |
| Cuadernos: preguntas respaldadas por fuentes | «¿Juan aprueba?». |
| Diccionario: palabras, formas, categorías y símbolos | «abandonar». |

«Empieza con un ejemplo» ofrece tres ejercicios progresivos: evaluación,
demostración y consulta de fuentes. Cada ejercicio abre su módulo, carga datos
coherentes y explica qué ejecutar y qué observar. Eliminar el ejemplo global
cuyo significado cambia sin indicación de módulo.

## 5. Evaluar modelo

Recorrido: Construir modelo → Escribir fórmula → Evaluar y comprender.

Escritorio: dominio, símbolos, aridades y tablas a la izquierda; fórmula,
asignaciones, acción y resultado a la derecha. Es una guía visual, no un
asistente que bloquee la edición entre pasos.

- Resultado inmediatamente bajo la fórmula, con valor y significado.
- Mantener Razones / Árbol y, dentro del árbol, Evaluación / Estructura.
- Errores junto a sus entradas y acción para llegar a la entrada relevante.
- Entrada española, lecturas y búsqueda de contramodelos como herramientas
  secundarias desplegables. Conservar teclado lógico, importación y lotes.
- Móvil: vistas Modelo / Fórmula y resultado, con resumen del modelo disponible.
- Explicación guiada debajo del resultado, expandible al ancho del área de
  trabajo. La expansión ocupa una fila posterior a los paneles; no se crea
  otro reproductor ni se reinicia el estado al cambiar de tamaño.

## 6. Demostrar

Izquierda: premisas, conclusión, constantes, errores y acción principal.
Derecha: estado, prueba Fitch, justificación y contramodelo cuando exista.

- Explicar junto al planteamiento que se estudia consecuencia en todos los
  modelos, a diferencia de evaluar en una interpretación concreta.
- Conservar árboles de premisas y conclusión, ámbito de hipótesis y números
  de línea. Resaltar la línea activa de la narración solo en la prueba de origen.
- Diferenciar prueba verificada, contramodelo verificado y búsqueda inconclusa.
- Los detalles de motores y contraste quedan desplegables después del significado
  del resultado, conservando cualquier alarma real de discrepancia.
- Reproductor debajo de la prueba o del contramodelo, expandible al ancho del
  trabajo. No mostrar elementos de un dominio inventado en una prueba sin modelo.

## 7. Cuadernos

En escritorio amplio, tres paneles: Fuentes / Preguntas y respuestas / Evidencia.

- Fuentes: selector de cuaderno, fuentes activas, altas/importación, oraciones
  pendientes y acceso a lectura ampliada del texto completo.
- Preguntas: pregunta, respuesta resumida, estado e historial existente.
- Evidencia: premisas usadas, citas, prueba Fitch o contramodelos y «Ver pasos».
- Una cita abre la fuente y la oración exactas, con resaltado y retorno claro
  a la evidencia. Conservar selección al cambiar entre vistas móviles.
- Mantener elección de lecturas, palabras supuestas, fuentes contradictorias,
  respuestas negativas y respuestas insuficientes con sus significados actuales.
- Pantallas intermedias: evidencia desplegable. Móvil: Fuentes / Preguntas /
  Evidencia. No comprimir tres columnas dentro del teléfono.
- «Ver pasos» abre el reproductor en una fila debajo de los paneles, vinculado
  a la respuesta seleccionada. Una nueva pregunta no debe narrar la anterior.

## 8. Diccionario

Búsqueda y filtros arriba, resultados como área principal, detalles de la entrada
seleccionada en un panel contextual. En móvil, abrir detalles con vuelta a la
consulta y posición anterior.

«Añadir palabra» abre el formulario contextual, conservando propuesta, lema,
categoría, irregularidades, sinónimos, sentidos y vista previa. Al venir desde
una palabra desconocida del evaluador o cuaderno, precargarla y ofrecer volver
al origen sin perder lo escrito. Respetar la separación entre léxico base y
entradas editables del usuario.

## 9. Ubicación y funcionamiento del modelo 3D

El avatar es parte del reproductor transversal «Explicación guiada», asociado a
un resultado. No es una página ni aparece permanentemente al entrar a una herramienta.

```text
RESULTADO Y JUSTIFICACIÓN
Veredicto · Razones / Árbol o prueba Fitch · Evidencia
[Abrir explicación guiada]

EXPLICACIÓN GUIADA · Evaluación / Prueba / Contramodelo · Paso 3 de 7
┌─────────────────────────────────┬────────────────────────────────┐
│ Avatar 3D                       │ Fórmula o regla del paso       │
│ Elementos del dominio, si existe│ Asignación / referencias       │
│ Etiquetas y resaltado actual    │ Texto y resultado de este paso │
└─────────────────────────────────┴────────────────────────────────┘
Anterior · Reproducir/Pausar · Siguiente · Repetir paso · Desde el inicio
Voz · Velocidad · 2D/3D · Minimizar · Cerrar · Pantalla completa
```

- Evaluación: recorrer fórmula, asignaciones y pertenencia a relaciones.
- Demostración: sincronizar regla, referencias e hipótesis con la línea Fitch.
- Cuadernos: conectar la prueba con las premisas y citas existentes. Una línea
  derivada no se presenta como una cita literal de la fuente.
- Contramodelo: distinguir búsqueda, verificación de premisas y evaluación de
  la conclusión falsa. No añadir detalles que el guion no contiene.
- Escena, texto, resaltado externo y narración comparten un único paso activo.
- Apertura a petición, sin voz automática. 3D bajo carga diferida; errores de
  WebGL o del recurso conservan texto, controles y representación 2D.
- Minimizar pausa y conserva paso. Restaurar conserva paso. Cerrar deja la
  explicación cerrada y pausada; volver a abrir el mismo resultado conserva paso.
- Cambiar de módulo pausa. Editar sus entradas invalida el resultado/reproductor
  asociado; una explicación anterior se marca desactualizada y no se reproduce.
- Móvil: escena arriba, texto debajo y controles accesibles. Pantalla completa
  conserva el contexto y devuelve foco y desplazamiento al salir.
- Voz local española opcional, preferencia latinoamericana y labios sincronizados;
  conservar respaldo para voces sin avisos por palabra. Velocidad también controla
  el avance automático sin voz. Nunca suprimir el texto por activar el audio.
- Un resultado inconcluso sin eventos no ofrece un recorrido de comprobación
  inventado; muestra el estado y los límites disponibles.

El contrato ejecutable previsto se define en
[EXPLANATION_PLAYER.md](../specs/EXPLANATION_PLAYER.md).

## 10. Estructura técnica prevista

```text
src/logos/web/
  app.js                         # arranque y composición
  app/{shell,navigation}.js
  features/
    home/
    evaluator/
    prover/
    notebooks/
    dictionary/
    explanation-player/          # API pública: index.js
  shared/                        # API, DOM, fórmulas, árboles, Fitch, ejemplos
  styles/                        # layout y estilos de módulos
  tokens.css                     # conservar valores
  story3d.js                     # adaptador de escena existente
```

Extraer por fases, con dependencias explícitas y montaje/desmontaje. El reproductor
no importa el estado de los módulos; comunica cambios mediante callbacks.
Conservar las API Python. Los contratos de historias actuales son la entrada;
normalizar para presentación sin mover lógica formal a JavaScript. El servidor
debe servir los nuevos archivos con MIME correcto mediante una lista controlada,
sin abrir acceso arbitrario a archivos del sistema o al repositorio.

## 11. Fases y aceptación

El orden funcional siguiente admite el trabajo paralelo descrito en
[REDISENO_PARALELO.md](REDISENO_PARALELO.md).

| Fase | Entrega | Criterio de cierre |
|---|---|---|
| F0 | Contrato y diagnóstico | Ambos agentes leen documentos y respetan propietarios. |
| F1 | Shell, navegación, Inicio | Rutas, recarga, Atrás/Adelante, foco y borradores funcionan. |
| F2 | Evaluador | Evaluación verdadera/falsa, variables libres, errores, lotes, español y árboles preservados. |
| F3 | Reproductor compartido | Pasos sincronizados, 2D/3D, voz, velocidad, minimización y pantalla completa verificados. |
| F4 | Demostrador | Fitch, árboles, contramodelos y estado inconcluso conservan su significado. |
| F5 | Cuadernos | Fuentes/preguntas/evidencia, citas exactas y estados especiales funcionan. |
| F6 | Diccionario | Consultar, filtrar, detallar, añadir y volver al origen funciona. |
| F7 | Integración y accesibilidad | Recorridos completos en escritorio y móvil, teclado, sin WebGL y sin voz. |

La ayuda contextual, estados vacíos, foco, contraste y alternativas al color se
implementan en cada fase. F7 los audita; no se posponen hasta el final.

En el primer acceso, ofrecer un recorrido breve y opcional que presente sidebar,
herramientas y ejecución de un ejemplo. Se puede omitir, cerrar y volver a abrir
desde Ayuda; recordar si fue completado u omitido. Cada módulo tiene ayuda
contextual propia (dominio y relaciones, consecuencia lógica, citas o léxico).
El tutorial no reemplaza las etiquetas y explicaciones necesarias para usarlo.

## 12. Validación final

- Suite Python completa y pruebas HTTP cuando el entorno permita puertos locales.
- Pruebas de navegador de navegación con estado, descartes asíncronos, interacción
  con árboles, fuentes/citas y reproductor. No basta con validar sintaxis.
- Escritorio amplio (1440 px), portátil (1024 px), tablet (768 px) y teléfono
  (390 y 360 px), además de teléfono horizontal. Las tablas y árboles grandes
  pueden desplazarse dentro de su contenedor; la página no desborda horizontalmente.
- Teclado: navegación, editor, paneles, menú, reproductor y pantalla completa.
- Simular ausencia de voz española, WebGL fallido, carga 3D fallida y movimiento
  reducido. El contenido lógico sigue siendo comprensible.
- Probar un resultado verdadero, uno falso, una prueba, un contramodelo y una
  búsqueda inconclusa; cuaderno con lectura ambigua, contradicción y sin premisas.
- Confirmar funcionamiento sin solicitudes a CDN o servicios externos.
- Informar comandos ejecutados, resultados, omisiones y limitaciones reales.

No prometer sincronización audible comprobada si no hay una voz local disponible
ni afirmar prueba en teléfono real cuando solo se usó emulación.

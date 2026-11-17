# Integración del rediseño (Bat’z)

Rama integrada: `rediseno/claude-interfaz` (worktree `../proyecto1-claude`). No se fusionó a `main` ni se publicó.
Base común: `ea78374`. Ramas fusionadas: `rediseno/codex-reproductor`, `rediseno/recorrido`, `rediseno/a11y`,
`rediseno/diccionario`, `rediseno/responsive`, `rediseno/banner`, `rediseno/aprender` (todas locales).

## Estado por fase

| Fase | Estado | Notas |
|---|---|---|
| F0 contrato | hecho | Propiedad de archivos respetada; `story3d.js` (de Codex) se tocó una vez, ver «Encuadre» en la entrega Claude. |
| F1 shell, rutas, Inicio | hecho | Incluye banner Gödel/Turing, recorrido de primer acceso, `#practicar` heredado. |
| F2 Evaluar | hecho, rehecho como asistente de 3 pasos a petición del usuario | 18 casos de ejemplo comprobados contra el motor; escritura en español. |
| F3 reproductor | integrado | Una instancia por módulo (Evaluar, Demostrar, Cuadernos); retirado el paso a paso heredado (HTML, JS, CSS). |
| F4 Demostrar | hecho | Prueba verificada / contramodelo verificado / búsqueda inconclusa rotulados; «Ir a la entrada» en errores de sintaxis. |
| F5 Cuadernos | hecho | Fuentes / Preguntas y respuestas / Evidencia; citas con retorno. |
| F6 Diccionario | hecho | Detalle contextual, añadir palabra, volver al origen. |
| F7 accesibilidad y responsive | auditado con herramientas; correcciones aplicadas | Solo emulación de Chromium. |

## Verificación realizada sobre la rama integrada

- `PYTHONPATH=src:tests python3 -m unittest discover -s tests`: 315 pruebas, correctas, 1 omitida (en la rama de entrega actual son 325, con 1 omitida, y 48 de Node).
- `node --test` sobre cada archivo de `tests/frontend/app/` (bios, export, learn, navigation, people, tour).
- Playwright (Chromium): las 6 rutas a 1440 y 390 px sin errores de consola ni desborde horizontal; flujo completo
  Evaluar → Resultado → Explicación guiada → contramodelo; los 18 ejemplos de Evaluar dan el valor esperado;
  Demostrar y Cuadernos con reproductor y resaltado de la línea Fitch; lectura en español que añade símbolos al modelo.
- Informes de los agentes (axe-core 0 violaciones en 1440/390 px; barrido de desborde en 1440, 1024, 768, 390, 360 y 844×390;
  fallos simulados de WebGL, GLB y voz; 0 solicitudes externas): ver las secciones F6, F7 y Banner de `CLAUDE.md`.

## No verificado o pendiente

- Teléfono real, lector de pantalla real y voz española real: no se probaron (solo emulación y ausencia de voz simulada).
- `tests/frontend/player/check.cjs` (15 recorridos del reproductor de Codex) no se volvió a ejecutar sobre la rama integrada.
- Evaluar: no se repitió el barrido de responsive tras rehacerlo como asistente (solo 1440 y 390 px, flujo principal).
  Casillas de las tablas de interpretación de 22 px en móvil; la fila entera ya conmuta, pero no se midió.
- Cuadernos con fuentes contradictorias: la cabecera dice «Sí» y la contradicción va solo en el aviso inferior.
- Logotipo: reconstruido en vectores desde las capturas que envió el usuario (no es el archivo original).
- Las fotos del banner son de dominio público verificadas en Commons (`img/CREDITOS.md`); los pies enlazan a Commons.
- Quedan ramas y worktrees locales (`proyecto1-dict`, `-tour`, `-a11y`, `-resp`, `-banner`, `/tmp/logos-codex-reproductor`)
  para retirar cuando el usuario decida; nada se publicó.

## Añadido después de la primera integración

Inicio: tarjetas «Practica lo que probaron Gödel y Turing»; exportar resultados (HTML e impresión/PDF) de Evaluar y Demostrar; sección Aprender (`#/aprender`, 18 hitos históricos y 33 tarjetas; fechas y atribuciones sin contrastar con fuentes externas); nombre Bat’z y logotipo.

## Segunda ronda (landing, personas, línea del tiempo)

Carrusel de Gödel, Turing y Church en Inicio y páginas `#/godel`, `#/turing`, `#/church` (biografías con solo datos verificables; Church sin retrato libre); línea del tiempo de Aprender con tarjetas «antes/después», retratos de 19 de 22 personas con licencia verificada (`img/CREDITOS.md`) y cierre hacia el modo Estudiar; landing minimalista y micro-interacciones; resumen técnico en `docs/ARQUITECTURA.md`.
Corregido tras la lectura técnica: exportación del contramodelo proposicional (la valuación llega como pares) y marcado como desactualizada de la explicación de Demostrar al editar premisas. Pendiente conocido (sección 8 de `ARQUITECTURA.md`): `app.js` monolítico, `do_POST` sin captura de algunas excepciones, sin comprobación de `Origin`/`Host`, documentación de contratos desactualizada.

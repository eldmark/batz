# Integración del rediseño (Batz)

Rama integrada: `rediseno/claude-interfaz` (worktree `../proyecto1-claude`). No se fusionó a `main` ni se publicó.
Base común: `ea78374`. Ramas fusionadas: `rediseno/codex-reproductor`, `rediseno/recorrido`, `rediseno/a11y`,
`rediseno/diccionario`, `rediseno/responsive`, `rediseno/banner` (todas locales).

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

- `PYTHONPATH=src:tests python3 -m unittest discover -s tests`: 315 pruebas, correctas, 1 omitida.
- `node --test tests/frontend/app/navigation.test.mjs` (4) y `tour.test.mjs` (5), ejecutados sobre cada archivo.
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
- Logotipo definitivo de Batz: pendiente de que lo envíe el usuario; hay una marca provisional (`.brand-mark`).
- Las fotos del banner son de dominio público verificadas en Commons (`img/CREDITOS.md`); los pies enlazan a Commons.
- Quedan ramas y worktrees locales (`proyecto1-dict`, `-tour`, `-a11y`, `-resp`, `-banner`, `/tmp/logos-codex-reproductor`)
  para retirar cuando el usuario decida; nada se publicó.

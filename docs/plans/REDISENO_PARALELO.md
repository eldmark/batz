# Ejecución en paralelo: Claude y Codex

Fecha: 2026-11-16. Este protocolo divide la implementación del
[plan de interfaz](REDISENO_INTERFAZ.md). Contrato compartido:
[EXPLANATION_PLAYER.md](../specs/EXPLANATION_PLAYER.md).

## 1. Organización

Dos agentes, dos ramas y dos directorios de trabajo separados. No ejecutar ambos
agentes editando el mismo checkout, aunque prometan usar archivos distintos:
el índice, los cambios de rama y los commits serían compartidos.

Claude es responsable de aplicación e integración. Codex es responsable del
reproductor y escena 3D. Esta asignación es operativa; ambos deben mantener la
corrección y el estilo del proyecto.

Estado al documentar: rama local `main`, HEAD `40e636a`, 13 commits por delante
de `origin/main`. No hacer reset a `origin/main` ni crear ramas directamente
desde el remoto: se perdería la base local del visor de árboles y del merge.
Si HEAD cambió, inspeccionar y conservar los commits nuevos.

## 2. Preparar la base común una sola vez

El coordinador debe registrar estos documentos en un commit antes de separar
el trabajo. Los comandos son instrucciones, no constancia de que se ejecutaron:

```bash
git status --short --branch
git add AGENTS.md README.md docs/00-README-ROADMAP.md docs/plans/REDISENO_INTERFAZ.md docs/plans/REDISENO_PARALELO.md docs/specs/EXPLANATION_PLAYER.md
git commit -m "Documenta el rediseño de LOGOS y el trabajo paralelo"
git rev-parse HEAD
```

Revisar antes que esos archivos solo contengan los cambios de documentación
esperados. Registrar el hash resultante como BASE_COMUN y usarlo para ambos
worktrees. Sustituir el marcador por ese hash real:

```bash
git worktree add -b rediseno/claude-interfaz ../proyecto1-claude BASE_COMUN
git worktree add -b rediseno/codex-reproductor ../proyecto1-codex BASE_COMUN
```

Si los agentes trabajan en máquinas distintas, transferir primero la base común
mediante el flujo Git autorizado o un bundle. Un agente no puede empezar desde
un hash que su clon todavía no tiene. No publicar ramas como efecto lateral de
preparar esta documentación; hacerlo cuando el usuario lo solicite o autorice.

Si las ramas o worktrees ya existen, inspeccionarlos y reutilizar según su estado;
no borrarlos ni recrearlos a la fuerza.

## 3. Propiedad de archivos

| Propietario | Archivos o directorios que puede editar |
|---|---|
| Claude | `src/logos/web/index.html`, `app.js`, `style.css`; nuevos `web/app/`, `web/shared/`, `web/styles/`; `web/features/home/`, `evaluator/`, `prover/`, `notebooks/`, `dictionary/`. |
| Claude | `src/logos/server.py`, exclusivamente servicio de recursos estáticos necesario para el frontend; pruebas HTTP asociadas. |
| Claude | Nuevas pruebas en `tests/frontend/app/`; `docs/plans/entregas/CLAUDE.md`. |
| Codex | Nuevo `src/logos/web/features/explanation-player/`; `src/logos/web/story3d.js`. |
| Codex | Nuevas pruebas, fixtures y demo en `tests/frontend/player/`; `docs/plans/entregas/CODEX.md`. |
| Coordinador / Claude al integrar | Ajustes de conexión del reproductor, registro de todos sus recursos y `docs/plans/entregas/INTEGRACION.md`. |
| Congelados para ambos | Valores de `tokens.css`, `.blend`, `.glb`, fuentes, vendor, motores y APIs lógicas Python. |
| Contratos compartidos | Este protocolo, el plan, `EXPLANATION_PLAYER.md` y `AGENTS.md`: no editarlos unilateralmente durante el paralelo. |

`web/` en esta tabla abrevia `src/logos/web/`. Codex no extrae borrando código
de `app.js`; lo lee como referencia y desarrolla su módulo en sus propios archivos.
Claude retira el reproductor antiguo al conectar el nuevo durante integración.

Si aparece una necesidad fuera del reparto, anotarla en la entrega con archivo,
motivo y cambio propuesto. El propietario lo aplica o se reasigna explícitamente.
No crear una segunda implementación de la misma función para evitar coordinar.

## 4. Frente Claude: aplicación y pantallas

Orden de trabajo:

1. Leer `AGENTS.md`, plan y contrato. Ejecutar verificación inicial y registrar base.
2. Crear shell, sidebar, header, Inicio y rutas hash. Preservar estado al navegar.
3. Extraer utilidades y módulos sin alterar resultados del núcleo ni dependencias.
4. Reorganizar Evaluar y Demostrar conservando árboles, lotes, español, Fitch,
   contramodelos, errores y estados inconclusos.
5. Implementar Cuadernos en fuentes/preguntas/evidencia y Diccionario con consulta
   principal y edición contextual. Incorporar ayuda y accesibilidad en cada paso.
6. Preparar los hosts y callbacks del reproductor según el contrato. Mientras la
   rama Codex no esté integrada, mantener operativo el reproductor legado: no
   importar un archivo inexistente ni dejar botones sin comportamiento.
7. Completar la prueba de navegación y regresiones de cada pantalla. Registrar
   cambios y puntos de conexión en `docs/plans/entregas/CLAUDE.md`.
8. Integrar la rama Codex conforme a la sección 7 y retirar el reproductor legado.

El código de composición es propiedad de Claude. Puede usar un adaptador temporal
interno para el reproductor legado, pero su API de destino debe ser la documentada.
No crear un falso reproductor final que marque cumplido el trabajo de Codex.

## 5. Frente Codex: reproductor y representación 3D

Orden de trabajo:

1. Leer `AGENTS.md`, plan y contrato. Inspeccionar eventos reales y la escena actual.
2. Implementar `features/explanation-player/index.js` con la API pública, estado
   y DOM propios. Copiar/adaptar comportamiento del legado sin editar `app.js`.
3. Incorporar texto, 2D, controles, minimización, invalidación y callbacks.
4. Conectar escena existente, selección de elementos y resaltados internos.
   Mantener avatar, animaciones, labios y parpadeo, con movimiento reducido.
5. Implementar voz local opcional, velocidades, cancelación segura, pantalla
   completa, respaldo y limpieza de recursos. Evitar audio simultáneo entre instancias.
6. Entregar demo aislada y pruebas de estados, carreras asíncronas y fallos.
7. Registrar API final, archivos a servir, receta de demo, pruebas y limitaciones
   en `docs/plans/entregas/CODEX.md`. Crear commits que se puedan integrar.

No implementar otra navegación general, otras pantallas o lógica de dominio.
No cambiar el backend para que encaje con datos inventados por el reproductor.

## 6. Formato de entrega de cada agente

Cada uno escribe su archivo de entrega, sin editar el del compañero:

```text
Base común:
Rama y último commit:
Estado: en curso / listo para integrar / integrado
Fases o requisitos completados:
Archivos añadidos o modificados:
API pública o puntos de conexión:
Recursos nuevos que debe servir Python:
Comandos de prueba y resultados:
Pruebas de navegador y tamaños usados:
Omisiones y limitaciones verificables:
Trabajo pendiente y propietario:
```

Marcar «listo para integrar» solo con cambios guardados en commits y árbol de
trabajo limpio. No declarar «integrado» basándose únicamente en la demo aislada.
No convertir las pruebas omitidas en pruebas aprobadas.

## 7. Integración (una sola persona/agente)

Claude, como integrador asignado, o el coordinador si el usuario lo cambia:

1. Confirmar misma base, ramas limpias y entregas disponibles. Revisar los diffs
   y cualquier desviación de propiedad antes de fusionar.
2. En la rama de aplicación, fusionar la rama local del reproductor:
   `git merge --no-ff rediseno/codex-reproductor`. No ejecutar merges simultáneos.
3. Registrar todos los JS/CSS nuevos en el servidor; comprobar código 200 y MIME.
   No habilitar un servidor de archivos sin restricciones para resolver imports.
4. Importar `createExplanationPlayer`, añadir `player.css` y conectar los hosts.
   Adaptar `showStory` y llamadas existentes a `load/open` con IDs por revisión.
5. Conectar Fitch, selección de fórmulas y citas por callbacks dentro del resultado
   correcto. Pausar al navegar e invalidar cuando cambian entradas.
6. Retirar DOM, variables, listeners, timers, voz y fullscreen del reproductor
   legado. Comprobar que no queden IDs duplicados ni dos sistemas reproduciendo.
7. Ejecutar validación integrada del plan y del contrato, incluida prueba sin red.
8. Escribir `docs/plans/entregas/INTEGRACION.md` con resultados, incidencias y
   estado de cada fase. Solo entonces dar el rediseño por terminado.

No fusionar a `main` ni publicar el resultado automáticamente si el encargo del
agente solo abarca su frente. Entregar la rama integrada para revisión; seguir
las instrucciones expresas del usuario sobre merge o publicación.

## 8. Verificación y entorno

Comandos de referencia desde la raíz de cada worktree:

```bash
PYTHONPATH=src:tests python3 -m unittest discover -s tests
PYTHONPATH=src:tests python3 -m unittest test_project_integration.LocalHTTP
node --input-type=module --check < src/logos/web/app.js
node --input-type=module --check < src/logos/web/features/explanation-player/index.js
git diff --check
```

El comando del nuevo módulo solo aplica cuando exista. Sintaxis correcta no
sustituye pruebas de comportamiento en navegador. Usar herramientas disponibles;
si se necesita instalar una herramienta, documentar esa dependencia y no introducir
un nuevo stack de aplicación como efecto de las pruebas.

Cada agente usará sus propios puertos y directorios temporales para cuadernos y
léxico de prueba (`LOGOS_NOTEBOOKS`, `LOGOS_LEXICON`). No alterar datos personales
en `datos/` ni probar borrado sobre cuadernos reales. Si el sandbox omite HTTP,
informarlo y ejecutar esas pruebas con permisos adecuados cuando sea posible.

No hacer `git add -A` en un directorio compartido ni descartar cambios ajenos.
No repetir un pull sobre un merge pendiente sin revisar primero `git status`.

## 9. Mensajes listos para iniciar cada agente

### Para Claude

> Implementa el frente Claude del rediseño de LOGOS en esta rama/worktree.
> Lee AGENTS.md, docs/plans/REDISENO_INTERFAZ.md,
> docs/specs/EXPLANATION_PLAYER.md y docs/plans/REDISENO_PARALELO.md.
> Eres responsable de shell, Inicio, navegación, Evaluar, Demostrar, Cuadernos,
> Diccionario y composición final. Respeta la propiedad de archivos: Codex trabaja
> en paralelo en explanation-player y story3d.js. Conserva colores, fuentes,
> avatar y corrección matemática. Mantén el reproductor legado operativo hasta
> integrar el nuevo. Documenta tus commits, validación y pendientes en
> docs/plans/entregas/CLAUDE.md. Como integrador, conecta la entrega Codex cuando
> esté lista; no declares terminado antes de verificar ambas partes juntas.

### Para Codex

> Implementa el frente Codex del rediseño de LOGOS en esta rama/worktree.
> Lee AGENTS.md, docs/plans/REDISENO_INTERFAZ.md,
> docs/specs/EXPLANATION_PLAYER.md y docs/plans/REDISENO_PARALELO.md.
> Eres responsable del reproductor transversal en
> src/logos/web/features/explanation-player/ y de story3d.js. Cumple la API
> createExplanationPlayer documentada. Conserva el avatar de main, eventos
> verificados, animaciones y labios. Incluye 2D, controles, voz opcional,
> velocidad, minimización, invalidación y pantalla completa. No edites app.js,
> index.html, style.css ni server.py: Claude es su propietario. Entrega demo y
> pruebas aisladas en tests/frontend/player/ y registra commits, recursos a servir,
> resultados y limitaciones en docs/plans/entregas/CODEX.md. No integres a main.

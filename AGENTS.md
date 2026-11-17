# Trabajo de agentes en Bat’z (antes LOGOS)

## Rediseño de interfaz autorizado

Antes de implementar el rediseño, leer en este orden:

1. [Plan y criterios de aceptación](docs/plans/REDISENO_INTERFAZ.md).
2. [Contrato entre la aplicación y el reproductor](docs/specs/EXPLANATION_PLAYER.md).
3. [Reparto y protocolo para Claude y Codex](docs/plans/REDISENO_PARALELO.md).

El rediseño está implementado e integrado (ver `docs/plans/entregas/INTEGRACION.md`; resumen técnico en `docs/ARQUITECTURA.md`).
Estos tres documentos siguen siendo la referencia de sus criterios y contratos.
Cada agente debe identificar su frente antes de editar y respetar la propiedad
de archivos del protocolo. No lanzar agentes adicionales por iniciativa propia.

Conservar la paleta de `src/batz/web/tokens.css`, las fuentes locales y el avatar
de `main` integrado en `40e636a`. No sustituir el GLB ni el archivo Blender.
Reutilizar los motores, árboles y eventos verificados existentes. Una búsqueda
inconclusa nunca equivale a falsedad ni a una demostración.

El rediseño adapta la interfaz del proyecto actual: Python y JavaScript con
módulos nativos. No introducir un framework, un bundler ni una dependencia de
servicios externos como parte de este trabajo sin una nueva decisión del usuario.

## Documentación de referencia

- Corrección matemática y alcance: `docs/plans/PLAN_MM3032.md`.
- Contratos existentes: `docs/specs/JSON_CONTRACTS.md`.
- Guiones semánticos: `src/batz/story.py`.
- Guiones de pruebas: `src/batz/proof_story.py`.
- Pruebas: `PYTHONPATH=src:tests python3 -m unittest discover -s tests`.

Los planes históricos no reflejan necesariamente la interfaz actual. Para el
rediseño, usar los tres documentos anteriores; para semántica y verificadores,
mantener las especificaciones del núcleo.

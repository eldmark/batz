# Revisión del equipo: lo que no se puede automatizar

Todo lo de esta lista necesita una persona. Las pruebas automáticas, los 51 casos de español y `scripts/validate_demo.py` ya pasan; esto es lo que falta para firmar la entrega. Marca cada casilla con nombre y fecha.

| Hecho | Tarea | Cómo | Quién · fecha |
|---|---|---|---|
| [ ] | **Fecha de entrega y de defensa (Q2)** | Anotarla en `docs/plans/PLAN_MM3032.md` §7. Sin ella no se pueden recortar los aportes. | |
| [ ] | **Revisión cruzada de las especificaciones** | Cada integrante lee `docs/specs/FORMAL_LANGUAGE.md`, `SEMANTICS.md` y `ACCEPTANCE_FIXTURES.md`, revisa ejemplos y condiciones laterales y deja sus observaciones en `docs/decisions/OPEN_QUESTIONS.md`. | |
| [ ] | **Ensayo de defensa** | Cada integrante responde en voz alta las 15 preguntas de `docs/DEFENSA.md` y evalúa una fórmula **no preparada** que proponga otra persona, prediciendo el resultado antes de pulsar «Evaluar». | |
| [ ] | **Recorrido en la computadora de entrega** | `python3 evaluador.py` (o `docker compose up --build`) en esa máquina. Recorrer los tres modos con «Ejemplo», cargar `ejemplos/grafo.logos` y abrir un paso a paso con la vista 3D. | |
| [ ] | **Ensayo audible de la narración** | Instalar una voz en español: en Windows, Configuración → Hora e idioma → Voz → Agregar voces → Español, y recargar la página. En el paso a paso, marcar «Leer en voz alta» y comprobar que se entiende y que la boca del avatar se mueve con las palabras. | |
| [ ] | **Entrada por voz** | En la máquina de la demo: `powershell -ExecutionPolicy Bypass -File scripts\instalar_voz.ps1`. En «Escribir la fórmula en español», «Grabar frase», decir «Todos los estudiantes leen un libro» y revisar la transcripción. | |
| [ ] | **Confirmar las decisiones del léxico** | Las 55 dudas ya están decididas y aplicadas; leer el resumen «Decisiones tomadas» de `docs/validation/LEXICO-AUDITORIA.md` (5 minutos) y revertir con `src/logos/lexicon.tsv` lo que no convenza, por ejemplo «perra»/«zorra», que es decisión docente. | |
| [ ] | **Teléfono real** | Abrir la interfaz desde un teléfono en la misma red. Comprobar las sub-pestañas, el teclado lógico encima del teclado del sistema y el paso a paso deslizando. Para eso hay que levantar el servidor con `--host 0.0.0.0` solo durante la prueba. | |
| [ ] | **Preguntas abiertas del equipo** | `docs/plans/PLAN_MM3032.md` §7: integrantes y quién defiende qué, si se exige ventana nativa, constantes como funciones 0-arias. | |

## Lo que ya se verificó automáticamente (2026-11-13)

- Pruebas unitarias e integración: `PYTHONPATH=src:tests python3 -m unittest discover -s tests`.
- 51 casos de la gramática del español: `scripts/report_spanish.py`.
- Recorrido reproducible por HTTP: `PYTHONPATH=src python3 scripts/validate_demo.py --seed 20261102`.
- Interfaz en Chrome, de escritorio y con teléfono emulado (360 y 390 px, pantalla táctil): 70 comprobaciones que cubren pestañas, vista Fitch, contramodelos, valuaciones, abrir en Evaluar, boca del avatar, teclado flotante, deslizar en el paso a paso, objetivos de toque, ausencia de desborde y de errores de consola, y «reducir movimiento».

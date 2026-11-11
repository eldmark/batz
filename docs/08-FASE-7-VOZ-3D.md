# Fase 7 — Narración, voz y mundo 3D

> Estado del extra (2026-11-02): implementados guiones deterministas para trazas semánticas y certificados verificados, vista 3D local con Three.js, voz local del navegador cuando existe y vista 2D permanente. Pasan pruebas de API, rechazo de trazas o certificados alterados y ensayo visual automatizado en Brave. La reproducción de voz aún requiere una máquina con voz local en español. Whisper sigue siendo opcional y no está implementado.

## Objetivo
Convertir pruebas y contramodelos verificados en explicaciones orales y animaciones sincronizadas.

## Arquitectura
`resultado verificado -> ExplanationBuilder determinista -> AnimationEvents + NarrationScript -> Three.js / TTS`.

## Tareas
1. ExplanationBuilder basado en reglas y plantillas, sin permitir que TTS/LLM invente matemáticas.
2. TTS inicialmente con síntesis del navegador; evaluar alternativas solo si aporta valor.
3. Three.js/React Three Fiber para dominio, objetos, relaciones, cuantificadores y cambios de verdad.
4. Blender opcional para assets GLB/glTF; no usar Blender como motor lógico.
5. Sincronizar eventos visuales con pasos y frases, con pausa, avance, retroceso y replay.
6. Whisper opcional como entrada de voz a español controlado; confirmar transcripción y parsing.
7. Fallback 2D si WebGL o audio fallan.

## Precisión narrativa
De `¬CamisaRoja(Carlos)` no inferir `¬Estudiante(Carlos)` a partir de `CamisaRoja(x)→Estudiante(x)`. Explicar ausencia de conclusión en lugar de inventar negación.

## Gate
Cada frase narrada está respaldada por un paso o evaluación verificable; sincronización y fallback funcionan.

La parte verificable del gate está cubierta por `story.py` y `proof_story.py`: ambos validan antes de crear eventos. La sincronización visual, los controles y el fallback están implementados en `web/app.js` y `web/story3d.js`. En Brave sin pantalla se comprobó el canvas 3D, los siete pasos del ejemplo, avance, retroceso, pausa, repetición, cambio a 2D y narración de una prueba de tres pasos, sin excepciones JavaScript. La máquina de ensayo no tenía voces locales en español; se comprobó el aviso y la continuidad en texto, pero no la reproducción audible.

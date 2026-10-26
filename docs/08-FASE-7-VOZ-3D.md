# Fase 7 — Narración, voz y mundo 3D

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

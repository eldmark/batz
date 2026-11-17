# Ensayo final de Bat’z para MM3032

## Qué comprobé

Corrí el programa como servidor local, con un modelo distinto del que aparece al pulsar «Cargar ejemplo». Probé 12 fórmulas generadas con la semilla `20261102`, tres entradas inválidas, la búsqueda de contramodelos y dos lecturas de una frase ambigua en español. El resultado completo está en [`demo-2026-11-02.json`](demo-2026-11-02.json). Cualquiera puede repetirlo con:

```bash
PYTHONPATH=src python3 scripts/validate_demo.py --seed 20261102
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

El primer comando arranca un servidor temporal en `127.0.0.1`, hace las solicitudes y lo cierra. Solo necesita Python y la biblioteca estándar. La huella SHA-256 del código evaluado quedó en el JSON para saber si se repite el ensayo sobre la misma versión.

| Comprobación | Resultado del ensayo del 2026-11-02 |
|---|---|
| Archivos de la interfaz | HTML, JavaScript y CSS respondieron `200`; el HTML no carga recursos externos |
| Fórmulas no usadas en el ejemplo de la UI | 12 de 12 respondieron `ok`; el valor coincidió con la raíz de su explicación |
| Entradas inválidas | Aridad, variable libre sin asignación y relación vacía dieron `invalid_input` sin valor |
| Contramodelo | Se encontró uno de tamaño 2 para `∀x P(x)`, y la evaluación independiente de ese modelo dio falso |
| Límite honesto | Con tamaño máximo 1, la misma búsqueda respondió `unknown` sin modelo |
| Español controlado inicial | «Todos los estudiantes leyeron un libro» dio dos lecturas. En el mismo modelo, una fue verdadera y la otra falsa; ninguna se eligió por defecto |
| Narración verificada | Los eventos de evaluación citaron nodos de traza, una prueba de tres pasos citó cada paso del certificado y una búsqueda `unknown` no produjo guion |
| 3D local | Brave dibujó el canvas y los dos elementos del ejemplo; el cambio a 2D mostró los mismos dos elementos y retiró el canvas |
| Controles y voz | Avance, retroceso, pausa y repetición funcionaron en Brave; sin voz local en español, apareció el aviso y siguió la narración en texto |
| Rendimiento HTTP local | 100 evaluaciones; mediana 1,50 ms, percentil 95 de 1,64 ms, máximo 1,93 ms en esta máquina |
| Suite | 162 pruebas ejecutadas, una omitida dentro del sandbox; la prueba HTTP pasó por separado con permiso de red local |

El tiempo medido sirve para esta máquina y esta fórmula, no es una promesa de rendimiento para cualquier entrada. La búsqueda de contramodelos también tiene límites propios de tiempo, candidatos y tamaño de tablas.

## Recorrido en pantalla para la entrega

```bash
PYTHONPATH=src python3 -m batz.server --port 8765
```

Abrir `http://127.0.0.1:8765/`. El núcleo y la interfaz funcionan sin internet; el navegador solo necesita llegar a ese servidor local.

1. Pulsar «Cargar ejemplo» y evaluar `∀x (P(x) → Q(x))`. Debe salir **Falso** con `x=0` como contraejemplo. Abrir el árbol y revisar que el texto resaltado corresponde al paso.
2. Cambiar la fórmula a `∃x P(x)`. Debe salir **Verdadero** con `x=0` como testigo.
3. Escribir `P(x)` y elegir `x=1` en el entorno. Debe salir **Falso**. Si se deja la asignación vacía, no debe aparecer un valor.
4. Escribir `P(a,a)`. Debe aparecer un error de aridad y ningún badge de verdad.
5. Escribir `∀x P(x)` y buscar un contramodelo hasta tamaño 2. Debe encontrarse uno. Cargarlo en las tablas y evaluar de nuevo: debe salir **Falso**.
6. Repetir la búsqueda con tamaño máximo 1. Debe salir `unknown`, sin afirmar que la fórmula sea válida.
7. Exportar el modelo como JSON, importarlo y comprobar que dominio, símbolos, tablas y fórmula quedaron iguales.
8. Pedir a otra persona que proponga una fórmula nueva sobre la firma declarada. Predecir el valor a mano y compararlo con la explicación.
9. Abrir «Escribir en español controlado», poner «Todos los estudiantes leyeron un libro» y comprobar que aparecen dos fórmulas. Elegir una de forma explícita; luego completar la nueva interpretación. Este adaptador aún cubre solo un fragmento pequeño.
10. En «Narración y dominio», avanzar, retroceder, pausar y repetir. Comprobar que la esfera resaltada corresponde al elemento o tupla del paso. Desactivar 3D para ver la misma información en 2D. Activar la voz solo si el navegador tiene una voz local en español.
11. En «Prueba verificada», poner `P → Q` y `P` como premisas, `Q` como conclusión. Deben aparecer tres pasos aceptados y narrados. Probar `P ⊢ Q`: el sistema debe responder `unknown` sin narrar una prueba.

La interacción de los pasos 1, 10 y 11 se comprobó en Brave sin pantalla: el resultado fue **Falso**, aparecieron siete eventos, se dibujó la escena 3D, funcionaron los controles, el cambio a 2D mostró dos elementos y la prueba `P → Q, P ⊢ Q` mostró tres pasos. No hubo excepciones JavaScript. La captura y el ensayo usaron la fórmula de ejemplo; durante la entrega queda por hacer el recorrido con una fórmula nueva propuesta por otra persona. No se pudo comprobar sonido audible porque el navegador de ensayo no tenía ninguna voz local en español.

La [captura de la escena 3D](brave-3d-2026-11-02.png) deja constancia de los dos elementos visibles en Brave.

## Si algo falla durante la exposición

- Si el puerto `8765` ya está ocupado, arrancar con otro, por ejemplo `--port 8766`, y abrir la dirección que imprime el servidor.
- Si la página no abre, comprobar que el proceso de Python sigue activo y que la dirección empieza por `http://127.0.0.1:`. El ensayo `scripts/validate_demo.py` sirve para mostrar el núcleo y la API sin depender de la vista.
- Si la búsqueda agota sus límites, explicar `unknown` y mostrar el contramodelo ya exportado. No llamarlo prueba de validez.
- Si la computadora de entrega no tiene navegador disponible, usar el JSON del ensayo y la ejecución por consola. El resultado matemático lo calcula el mismo núcleo de Python.

## Pendientes que requieren personas

La revisión cruzada de lenguaje, semántica y fixtures debe firmarla el equipo en `docs/decisions/OPEN_QUESTIONS.md`. También falta el ensayo en pantalla de esta lista con una fórmula propuesta por otra persona y la confirmación de si el docente exige una ventana nativa. No puedo dar por realizados esos pasos desde la suite automática.

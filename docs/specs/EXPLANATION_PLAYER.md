# Contrato del reproductor de explicaciones

Fecha: 2026-11-16. Estado: contrato de implementación acordado en documentación;
los módulos y métodos siguientes todavía no existen en la base `40e636a`.

Leer junto a [REDISENO_INTERFAZ.md](../plans/REDISENO_INTERFAZ.md) y
[REDISENO_PARALELO.md](../plans/REDISENO_PARALELO.md).

## 1. Propiedad y límites

Codex implementa el reproductor y su escena. Claude implementa sus puntos de
montaje, el adaptador desde los resultados de cada módulo y los resaltados
externos. El reproductor no busca elementos de Fitch, fórmulas o fuentes mediante
selectores globales: informa mediante callbacks y el módulo resuelve el destino.

El contrato se puede implementar sin modificar Python. Cualquier incompatibilidad
se documenta antes de modificar esta interfaz pública. No cambiar silenciosamente
firmas en una sola rama.

## 2. Recursos públicos

```text
/features/explanation-player/index.js
/features/explanation-player/player.css
/story3d.js
```

`index.js` exporta `createExplanationPlayer`. Puede importar archivos privados
relativos dentro de su directorio. Codex enumera los recursos adicionales en su
entrega; Claude registra esos archivos en el servidor con MIME correcto. Mantener
las rutas existentes de avatar, Three.js y fuentes.

El estilo está acotado al componente mediante clases `ep-*` o un contenedor
`[data-explanation-player]`; no redefinir `body`, `.pane`, `.button`, `h2` o los
tokens globales. Usar las variables de color y tipografía existentes. El componente
debe funcionar dentro de un host con `min-width: 0` y sin ancho fijo obligatorio.

## 3. API JavaScript pública

```js
import {createExplanationPlayer} from '/features/explanation-player/index.js';

const player = createExplanationPlayer({
  host,                         // HTMLElement vacío, propiedad de este componente
  onStepChange: ({resultId, event, index, total}) => {},
  onStateChange: snapshot => {},
});

player.load({
  resultId: 'evaluate:12',        // único por resultado/revisión dentro de la sesión
  origin: 'evaluate',            // evaluate | prove | notebook
  kind: 'evaluation',            // evaluation | proof | countermodel
  title: 'Evaluación semántica',
  story: response.story,         // objeto existente {schema_version, events, ...}
  model: response.model,         // formato serializado actual; null en pruebas
});

player.open();
player.pause();
player.minimize();
player.invalidate('El modelo cambió. Vuelve a evaluar.');
player.close();
player.clear();
player.getSnapshot();
player.destroy();
```

Todos los métodos son síncronos desde el punto de vista del consumidor. La carga
de Three.js, GLB y voces se gestiona internamente con estados de carga y error.
No se exige que `load` espere a cargar 3D para representar el texto.

### Semántica de métodos

| Método | Efecto |
|---|---|
| `load(payload)` | Carga un nuevo resultado cerrado, pausado y en índice 0. Un `resultId` nuevo reinicia el recorrido; el mismo ID conserva el paso y estado, y no sustituye datos por debajo. |
| `open()` | Expande y representa el paso actual; no activa reproducción ni voz. Inicia carga diferida de 3D si la preferencia lo permite. |
| `pause()` | Cancela voz y temporizadores de avance/boca. Conserva paso y apertura. |
| `minimize()` | Pausa y deja una franja con título, paso y acción de restaurar. |
| `close()` | Pausa y cierra la presentación conservando el resultado y el índice para reabrirlo. |
| `invalidate(reason)` | Pausa, marca desactualizado y muestra el motivo. Inhabilita reproducción y avance hasta cargar un resultado nuevo. |
| `clear()` | Cancela actividad, elimina resultado y libera escena/recursos asociados. Queda vacío. |
| `getSnapshot()` | Devuelve un objeto nuevo con el estado público indicado abajo. |
| `destroy()` | Limpia audio, eventos, observadores, timers, WebGL y DOM propio. La instancia deja de usarse. |

`pause`, `close`, `clear` y `destroy` deben tolerar su repetición y no fallar si
no hay resultado o la carga 3D sigue pendiente. Una carga pendiente de una revisión
anterior no puede recrear una escena después de `clear`, `load` nuevo o `destroy`.

```js
// Snapshot público; index es base cero y vale null cuando no hay eventos.
{
  resultId: null,        // string | null
  origin: null,          // evaluate | prove | notebook | null
  kind: null,            // evaluation | proof | countermodel | null
  status: 'empty',       // empty | ready | stale
  presentation: 'closed',// closed | minimized | expanded
  index: null,
  total: 0,
  playing: false,
  voiceEnabled: false,
  threeDEnabled: true,
  rate: 1,
}
```

Un guion vacío queda `empty`, no permite abrir un recorrido y no invoca
`onStepChange`. Puede conservar metadatos del resultado para diagnóstico.

`onStepChange` se emite al cargar un guion no vacío y cada vez que cambia el
paso, incluyendo saltos desde la escena o lista. La repetición del mismo paso
puede emitirlo de nuevo. `onStateChange` refleja cambios públicos, sin generar
bucles por llamar a `getSnapshot`. El índice visible es `index + 1`.

## 4. Eventos existentes: conservar el significado

Pasar los eventos del backend sin exigir un nuevo esquema de API. Tratar los
campos opcionales como opcionales y conservar campos desconocidos.

| Familia | Campos relevantes | Representación |
|---|---|---|
| Semántica | `id`, `trace_path`, `kind`, `formula`, `value`, `text_es`, `span`, `assignment`, `element`, `relation`, `term_values`, `verified_by` | Fórmula, asignaciones, dominio, pertenencia a relaciones y valor del paso. |
| Prueba | Los comunes, más `line`, `step_id`, `rule`, `rule_label`, `refs`, `context`, `depth`, `steps` | Línea Fitch, regla, referencias e hipótesis abiertas; `value` puede ser null. |
| Búsqueda | `kind: 'search'`, `phase`, `size` y demás campos disponibles en el guion real | Progreso acotado de búsqueda; no rotularlo como una inferencia verificada. |
| Premisas de un contramodelo | `kind: 'premise'` y campos del guion real | Comprobación de premisas antes de la conclusión; conservar rutas distintas. |

Referencias de implementación: `src/logos/story.py`, `proof_story.py` y
`countermodels.py`. Para fixtures usar salidas reales de las API, no asumir que
un evento de búsqueda contiene todos los campos de un evento semántico.

El componente no evalúa fórmulas, deriva reglas ni decide qué cita respalda una
línea. No cambia `false`, `null`, `unknown` o estados de evidencia por conveniencia
visual. No marca un campo ausente como «verificado» por defecto.

## 5. Integración de aplicación y resaltados (Claude)

El propietario de cada módulo conserva una instancia asociada a su host. Puede
mover el host a una fila de ancho completo sin reconstruir el reproductor.

1. Al recibir un resultado vigente, asignar `resultId` nuevo y llamar a `load`.
2. El botón «Explicación guiada» llama a `open` y desplaza el foco/scroll desde
   la aplicación cuando corresponda. `load` no desplaza la página.
3. En `onStepChange`, comprobar ID y revisión antes de resaltar la fórmula,
   árbol o línea Fitch dentro del contenedor de ese resultado.
4. En una prueba, usar el mapa de citas que ya posee Cuadernos; no inferir
   procedencia por coincidencia de texto ni atribuir fuentes a cada línea derivada.
5. Al ocultar un módulo, llamar a `pause`, salir de pantalla completa y retirar
   sus resaltados externos. Conservar la instancia y borradores.
6. Al editar una entrada relevante, llamar a `invalidate`, retirar resaltados
   y descartar cualquier respuesta asíncrona de la revisión anterior.
7. Al eliminar el resultado, llamar a `clear` o `destroy`, según el ciclo de vida.

En distintos módulos puede haber instancias pausadas. Codex implementa coordinación
interna entre instancias del reproductor para que solo una reproduzca a la vez,
sin exponer objetos en `window`. Claude pausa explícitamente al navegar.

## 6. Interacción y ciclo de vida (Codex)

- Reproducir, pausar, anterior, siguiente, repetir paso, desde el inicio y
  selección de un paso de la lista. Deshabilitar extremos correctamente.
- `Repetir paso` no vuelve al comienzo; reanuda/narra el paso actual a petición.
- Velocidades iniciales ofrecidas: 0.75, 1, 1.25 y 1.5. La misma preferencia
  controla narración y avance automático sin audio.
- Al cambiar de velocidad, voz o paso, cancelar callbacks y timers del estado
  previo antes de reanudar. `onend`/`onerror` obsoletos no avanzan otro resultado.
- Audio desactivado al principio. Seleccionar voz española local, preferir
  latinoamericana y responder a `voiceschanged`. Si falta, explicar y permitir
  seguir sin voz. Nunca exigir audio para avanzar.
- Reutilizar sincronización labial por sílabas y respaldo sin eventos de palabra.
- 3D opcional, con 2D y texto completos; distinguir `0` de ausencia de elemento.
- Seleccionar un elemento salta al caso que realmente contiene el guion, dentro
  del cuantificador correspondiente; no inventar casos por completar la escena.
- Salir de pantalla completa al cerrar, minimizar, invalidar o destruir.
  Conservar respaldo para navegadores sin API nativa y restaurar scroll y foco.
- Pausar al ocultarse la pestaña. No acumular audio o avances durante la ausencia.
- Respetar movimiento reducido, liberar escenas y evitar múltiples bucles de
  animación. Mantener la comprensión sin parpadeo ni animaciones decorativas.
- Controles y estado accesibles por teclado; anuncios de paso concisos, sin
  anunciar automáticamente el guion completo ni cada cuadro de animación.

## 7. Prueba aislada y aceptación del contrato

Codex entrega `tests/frontend/player/preview.html`, fixtures y la receta para
servirlos en local, sin modificar el servidor de producción en su rama. Puede
usar un servidor estático local desde la raíz web con una copia temporal de la
demo, sin escribir recursos de prueba en rutas reservadas al otro agente.

Verificar como mínimo:

- Evaluación con `0` y `1`, prueba sin modelo y relato de contramodelo.
- Identidad del evento entre texto, escena y `onStepChange`.
- Voz inexistente, carga GLB fallida y WebGL inexistente.
- Minimizar/abrir conserva índice; cargar ID nuevo reinicia; ID repetido no reinicia.
- Invalidar impide continuar; finalizar audio viejo no avanza un resultado nuevo.
- Dos instancias no hablan a la vez; destruir durante carga no deja escena ni voz.
- Pantalla completa y su respaldo conservan paso, scroll y foco al salir.
- Redimensionar y mover el host no reinicia la explicación.

La prueba aislada facilita el desarrollo paralelo. La aceptación final requiere
los mismos recorridos con las API y pantallas reales, a cargo de la integración.

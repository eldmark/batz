# Ejecutar y publicar Bat’z

Cómo se ejecuta Bat’z en un equipo propio y cómo se publica una demo gratuita para que otra persona la abra con un enlace. Lo que se sabe del código (qué escribe en disco, qué lanza) está comprobado; lo que depende de un servicio externo (Render, Hugging Face) es lo que decían sus paneles y su documentación **al redactar esto** y puede haber cambiado: se marca donde importa.

## 1. Qué hay que saber antes de elegir dónde publicar

Bat’z **no es una página estática**. Es un servidor de Python (`src/batz/server.py`, solo librería estándar) que sirve la interfaz y una API JSON, y que:

- **Guarda estado en disco**: los cuadernos (`datos/cuadernos/*.json`, o la carpeta de `BATZ_NOTEBOOKS`) y las palabras que se añaden al diccionario (`datos/lexico_usuario.tsv`, o el archivo de `BATZ_LEXICON`). El estado es **del servidor, no del navegador**: todos los visitantes comparten los mismos cuadernos y palabras.
- **Lanza un proceso del sistema** para la voz de la explicación: `espeak-ng` (`voice_output.py`). Sin él la narración sigue funcionando con las voces del navegador, o en texto.
- **Hace cálculo pesado en la petición**: una búsqueda de prueba o de contramodelos puede ocupar la CPU varios segundos (topes de unos 2 s de resolución, 3 s de prueba y 2 s de contramodelos).
- **No tiene autenticación** ni comprueba `Origin`/`Host` (ver [ARQUITECTURA.md](ARQUITECTURA.md) §7).

## 2. En un equipo propio

### 2.1 Docker (recomendado)

No hace falta tener Python. Desde la raíz del repositorio:

```bash
docker compose up --build        # abrir http://127.0.0.1:8765
docker compose down              # detener
```

- Publica **solo en `127.0.0.1`** del equipo. Otro puerto: `BATZ_PORT=9000 docker compose up --build`.
- La imagen (`python:3.12-slim`) instala `espeak-ng`, así que la voz de la explicación se genera dentro del contenedor. **No** incluye la transcripción por voz (whisper.cpp), que es opcional.
- `./datos` se monta como volumen: los cuadernos y palabras añadidas sobreviven a reconstruir la imagen.
- Tiene un `HEALTHCHECK` que consulta `/` cada 10 s.

### 2.2 Sin Docker

```bash
python3 evaluador.py                          # abre el navegador en http://127.0.0.1:8765
python3 evaluador.py --port 9000 --no-browser # otro puerto, sin abrir el navegador
```

Solo requiere Python 3.10 o posterior. `--host` cambia la dirección en que escucha; **no uses `--host 0.0.0.0` en una red que no controles**: no hay autenticación y cualquiera podría usar el servidor y modificar los cuadernos y el diccionario. Para la voz en Linux: `sudo pacman -S espeak-ng`, `sudo apt install espeak-ng` o `sudo dnf install espeak-ng`.

## 3. Hosting gratuito

### 3.1 Vercel: no encaja

Vercel está pensado para sitios estáticos y funciones **sin servidor**. Bat’z no cabe por cuatro razones:

1. El servidor es un proceso de Python que escucha en un puerto de forma continua; Vercel ejecuta funciones por petición.
2. Guarda cuadernos y léxico **en disco**, y el disco de una función de Vercel es efímero y no compartido entre invocaciones.
3. Lanza `espeak-ng`, un programa del sistema que ese entorno no ofrece.
4. Los tiempos límite de una función son cortos; las búsquedas de prueba pueden tardar varios segundos.

Reescribir el servidor como funciones sin servidor cambiaría la arquitectura y el modelo de estado; no se hace.

### 3.2 Render, plan gratuito (recomendado)

Render ejecuta **contenedores Docker** como «Web Service», que es exactamente lo que ya tiene el proyecto. En la raíz del repositorio hay un `render.yaml` (un «Blueprint») que describe ese servicio con el `Dockerfile` y el puerto que usa Bat’z.

**Pasos, con el panel de Render:**

1. El repositorio debe estar en GitHub (o GitLab/Bitbucket) y contener `render.yaml`, `Dockerfile` y el código. Si el repositorio es privado, Render pedirá permiso para leerlo.
2. En [dashboard.render.com](https://dashboard.render.com), con tu cuenta: **New → Blueprint**.
3. Conecta la cuenta de GitHub y elige el repositorio (y la rama que contiene `render.yaml`).
4. Render lee el archivo y muestra el servicio que va a crear. Revisa que el plan sea **Free** y pulsa **Apply**.
5. Espera a que termine el primer despliegue: construye la imagen (unos minutos) y la arranca. Cuando el estado sea **Live**, la URL aparece arriba del servicio, con la forma `https://<nombre>.onrender.com`.
6. Abre esa URL y pon el enlace en el README, en el marcador `<!-- DEMO_URL -->`.

Si el Blueprint no detectara el puerto, en el servicio abre **Environment** y define `PORT=8765` (el puerto en que escucha Bat’z según el `Dockerfile`). Cada `git push` a la rama conectada vuelve a desplegar.

**Qué esperar del plan gratuito (según Render al redactar esto; compruébalo en su documentación):**

- **Se duerme** tras unos 15 minutos sin visitas. La primera visita después **tarda unos 30–60 s** en despertar el servicio (se verá una página de espera de Render). Conviene abrirlo uno o dos minutos antes de una revisión o una exposición.
- **El disco es efímero.** Cada vez que el servicio se reinicia, se redespliega o despierta de un sueño, se pierde lo escrito en disco: **los cuadernos y las palabras añadidas al diccionario desaparecen**. El diccionario base y los 50 ejercicios están en el código y no se pierden.
- **El estado es compartido entre visitantes**: quien entre ve los cuadernos y palabras que otros crearon (mientras no se reinicie).
- **Recursos limitados** (poca CPU y memoria): las búsquedas pesadas pueden tardar más que en un equipo propio, y el gratuito tiene un tope mensual de horas de ejecución.
- No incluye transcripción por voz (whisper). La voz de la explicación sí funciona (`espeak-ng` va en la imagen) y suena en el equipo del visitante a partir del audio que genera el servidor.

### 3.3 Alternativa: Hugging Face Spaces (Docker)

Un «Space» de tipo Docker ejecuta también el `Dockerfile` del repositorio.

1. En huggingface.co: **New → Space**, **SDK: Docker**, hardware **CPU basic** (gratuito).
2. El Space es un repositorio git propio: sube a él el contenido del proyecto (`git remote add space https://huggingface.co/spaces/<usuario>/<nombre>` y `git push space <rama>:main`).
3. El `README.md` **de ese repositorio** debe empezar con una cabecera de configuración. Hugging Face espera el puerto **7860** por defecto; como Bat’z escucha en 8765, indícalo así (o cambia el puerto del `CMD` y de `EXPOSE` en el `Dockerfile` a 7860):

   ```yaml
   ---
   title: Batz
   sdk: docker
   app_port: 8765
   ---
   ```

4. Hugging Face construye la imagen y publica el Space en `https://huggingface.co/spaces/<usuario>/<nombre>`.

Limitaciones iguales o parecidas a Render: el disco del Space es **efímero** (se pierde lo guardado al reiniciar o redesplegar, salvo que se contrate almacenamiento persistente), el estado es compartido entre visitantes y los Spaces gratuitos se duermen cuando pasa un tiempo sin visitas (la duración la fija Hugging Face; compruébala en su documentación). Hugging Face ejecuta el contenedor con un usuario no administrador: el `Dockerfile` ya crea un usuario sin privilegios y deja `/app/datos` a su nombre, pero no se ha probado el despliegue en Spaces.

## 4. Aviso de privacidad para la demo pública

> **La demo pública es de uso compartido.** Los cuadernos que se crean y las palabras que se añaden al diccionario quedan en el servidor y **cualquier otra persona que abra el enlace puede verlos, modificarlos o borrarlos**. No escribas datos personales ni textos que no quieras que otros lean. Lo que se guarda se pierde cuando el servicio se reinicia, pero hasta entonces es visible para todos.
>
> En el navegador solo se guardan preferencias (barra lateral, voz elegida, progreso de Practicar y de las tarjetas de estudio). Bat’z no usa analítica ni carga recursos de terceros: tipografías, Three.js y el avatar se sirven desde el propio servidor.

Para revisar el proyecto con datos propios, usa la ejecución local (sección 2): ahí todo queda en tu equipo.

## 5. Lista de comprobación antes de enviar el enlace

- [ ] Abrir la URL y esperar a que el servicio despierte; comprobar que Inicio carga con tipografías e imágenes.
- [ ] Evaluar un caso de ejemplo y abrir «Explicación guiada» (el avatar 3D necesita WebGL; sin él queda la vista 2D).
- [ ] En Demostrar, ejecutar los tres ejercicios de Inicio (Gödel/Turing).
- [ ] Probar la voz del reproductor («Probar voz») y comprobar que hay al menos una opción.
- [ ] Avisar de que el servicio puede tardar en despertar y de que lo escrito se pierde al reiniciar.

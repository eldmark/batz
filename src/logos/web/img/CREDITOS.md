# Créditos de imágenes

Licencias verificadas el 2026-11-17 con la API de Wikimedia Commons (`prop=imageinfo&iiprop=extmetadata`, campo `LicenseShortName`).
Los retratos de `people/` son copias reducidas (hasta 480 px de ancho, escala de grises, JPEG de menos de 150 kB); el duotono se aplica solo con CSS. Las imágenes más pequeñas en origen (Löwenheim, Ackermann, Gentzen, Whitehead) conservan su ancho original: no se ampliaron. En Schröder se recortó la tira con el rótulo inferior.
Los datos de cada persona (años, crédito, licencia) viven en `features/people/people.js`, que es la fuente única. Las licencias CC BY-SA exigen mostrar el crédito de forma visible junto al retrato.

| Persona | Archivo | Autor | Licencia | Origen | Verificado |
|---|---|---|---|---|---|
| Aristóteles | `people/aristoteles.jpg` | Copia romana de Lisipo (foto: Jastrow, 2006) | Dominio público | https://commons.wikimedia.org/wiki/File:Aristotle_Altemps_Inv8575.jpg | 2026-11-17 |
| Gottfried Wilhelm Leibniz | `people/leibniz.jpg` | Christoph Bernhard Francke | Dominio público | https://commons.wikimedia.org/wiki/File:Christoph_Bernhard_Francke_-_Bildnis_des_Philosophen_Leibniz_(ca._1695)_(cropped)2.jpg | 2026-11-17 |
| George Boole | `people/boole.jpg` | Autor desconocido (National Portrait Gallery, Londres) | Dominio público | https://commons.wikimedia.org/wiki/File:George_Boole_by_unknown_artist_1847.jpg | 2026-11-17 |
| Gottlob Frege | `people/frege.jpg` | Autor desconocido | Dominio público | https://commons.wikimedia.org/wiki/File:Young_frege.jpg | 2026-11-17 |
| Charles Sanders Peirce | `people/peirce.jpg` | Napoleon Sarony | Dominio público | https://commons.wikimedia.org/wiki/File:Charles_Sanders_Peirce.jpg | 2026-11-17 |
| Ernst Schröder | `people/schroder.jpg` | Autor no indicado | Dominio público | https://commons.wikimedia.org/wiki/File:Ernst_schroeder.jpg | 2026-11-17 |
| Giuseppe Peano | `people/peano.jpg` | Autor desconocido | Dominio público | https://commons.wikimedia.org/wiki/File:Giuseppe_Peano.jpg | 2026-11-17 |
| Bertrand Russell | `people/russell.jpg` | Bassano Ltd | Dominio público | https://commons.wikimedia.org/wiki/File:Bertrand_Russell_in_1936.jpg | 2026-11-17 |
| Alfred North Whitehead | `people/whitehead.jpg` | Autor desconocido | Dominio público | https://commons.wikimedia.org/wiki/File:ANWhitehead.jpg | 2026-11-17 |
| Leopold Löwenheim | `people/lowenheim.jpg` | Autor desconocido (MacTutor, Univ. de St Andrews) | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Lowenheim_Portrait.jpg | 2026-11-17 |
| Thoralf Skolem | `people/skolem.jpg` | Autor desconocido (Oslo Museum) | Dominio público | https://commons.wikimedia.org/wiki/File:ThoralfSkolem-OB.F06426c.jpg | 2026-11-17 |
| David Hilbert | `people/hilbert.jpg` | Autor desconocido | Dominio público | https://commons.wikimedia.org/wiki/File:Hilbert.jpg | 2026-11-17 |
| Wilhelm Ackermann | `people/ackermann.jpg` | Autor desconocido | Dominio público | https://commons.wikimedia.org/wiki/File:Ackermann_Wilhelm.jpg | 2026-11-17 |
| Paul Bernays | `people/bernays.jpg` | Autor desconocido (ETH-Bibliothek) | Dominio público | https://commons.wikimedia.org/wiki/File:ETH-BIB-Bernays,_Paul_(1888-1977)-Portrait-Portr_00025_(cropped).tif | 2026-11-17 |
| Kurt Gödel | `people/godel.jpg` | Autor desconocido; Kurt Gödel Papers, Shelby White and Leon Levy Archives Center, Institute for Advanced Study | Dominio público | https://commons.wikimedia.org/wiki/File:Young_Kurt_G%C3%B6del_as_a_student_in_1925.jpg | 2026-11-17 |
| Alan Turing | `people/turing.jpg` | Elliott & Fry | Dominio público | https://commons.wikimedia.org/wiki/File:Alan_Turing_(1951).jpg | 2026-11-17 |
| Alfred Tarski | `people/tarski.jpg` | George Bergman (Oberwolfach Photo Collection) | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Alfred_Tarski_1968_(as-is,_cropped).jpg | 2026-11-17 |
| Gerhard Gentzen | `people/gentzen.jpg` | Eckart Menzler-Trott (Oberwolfach Photo Collection) | CC BY-SA 2.0 DE | https://commons.wikimedia.org/wiki/File:Gerhard_Gentzen.jpg | 2026-11-17 |
| John Alan Robinson | `people/robinson.jpg` | David Monniaux | CC BY-SA 3.0 | https://commons.wikimedia.org/wiki/File:John_Alan_Robinson_IMG_0493.jpg | 2026-11-17 |

`godel.jpg` y `turing.jpg` se conservan además en `img/` porque el banner de Inicio todavía las usa.

## Personas sin imagen

La interfaz muestra sus iniciales; no se usó ninguna foto sin licencia verificada.

- Alonzo Church: en Commons solo aparece un homónimo (presidente de la Universidad de Georgia), no el lógico; no hay retrato libre verificable.
- Stanisław Jaśkowski: solo hay fotos de su lápida (CC BY / CC BY-SA), no un retrato.
- Frederic Fitch: ninguna imagen en Commons.

## Notas

- Los datos de autor «desconocido» son los que declara Commons; la etiqueta de licencia es la de Commons, no una opinión propia. La foto de Bertrand Russell lleva en Commons un aviso de reclamaciones de terceros sobre derechos (etiqueta «Public domain»).
- La identidad de la persona retratada se comprobó a ojo solo contra el título del archivo y la categoría en Commons.

Para sustituir un retrato: reemplazar el archivo con el mismo nombre (menos de 150 kB), actualizar esta tabla y `people.js`. Si el archivo falta, el banner muestra una tarjeta con las iniciales (texto alternativo en `features/home/home.js`, `BANNER.people`).

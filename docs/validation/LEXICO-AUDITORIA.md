# Auditoría del léxico del español

> Revisión asistida por máquina de `src/batz/lexicon.tsv` (1499 lemas: 639 N, 283 ADJ, 329 V, 248 NP), hecha el 2026-11-13 sobre el commit `d47980d`.
> **La revisión humana sigue haciendo falta.** El script aplica reglas y listas de excepciones; no sabe más español que esas listas, y que una palabra no salga señalada no garantiza que esté bien. El léxico sigue «pendiente de revisión humana» hasta que una persona firme la tabla de dudas de abajo.

## Qué se revisó

`scripts/auditar_lexico.py` carga las entradas con `batz.lexicon` y revisa **lo que el generador produce de verdad** (plural, femenino y las seis formas verbales), comparándolo con reglas escritas aparte: acentuación y silabeo para los plurales, terminaciones y excepciones conocidas para el género, listas de verbos irregulares, de cambio de raíz y de hiato, y el uso con o sin objeto de verbos muy comunes. También cruza el léxico con las palabras que ya trae `spanish_grammar.txt`: `spanish_cyk.py` deja que esas palabras conserven su categoría por encima del diccionario y `spanish_semantics.py` conserva sus símbolos, así que una forma del léxico que coincide con una de ellas se pierde.

Cada aviso trae lema, categoría, línea, regla, formas generadas, arreglo sugerido y confianza:
**alta** = error gramatical claro (forma mal escrita o mal flexionada); **media** = problema probable que pide criterio; **baja** = punto para revisar.

## Cómo repetirlo

Desde la raíz del repositorio (solo biblioteca estándar; no hace falta `PYTHONPATH`):

```bash
python scripts/auditar_lexico.py                         # informe completo
python scripts/auditar_lexico.py --confianza alta        # solo errores claros
python scripts/auditar_lexico.py --formato markdown      # la tabla de dudas de abajo, con columna de visto bueno
python scripts/auditar_lexico.py --formato tsv > auditoria.tsv            # para una hoja de cálculo
python scripts/auditar_lexico.py src/batz/lexicon.tsv datos/lexico_usuario.tsv   # base y altas del usuario juntas
PYTHONPATH="src;tests" python -m unittest tests.test_lexicon_audit       # en Linux/macOS, "src:tests"
```

La salida es determinista. La prueba falla si vuelve a aparecer un error de confianza alta que se pueda corregir en el TSV.

## Recuento por regla

| Regla | Qué comprueba | Antes (alta / media / baja) | Después |
|---|---|---|---|
| `formato` | Fila mal formada: categoría, género o uso, opciones de «extra», lema o formas no válidas | 0 / 0 / 0 | 0 / 0 / 0 |
| `duplicado` | Entradas repetidas o en conflicto, lemas que son formas de otro lema, formas compartidas | 0 / 0 / 0 | 0 / 0 / 0 |
| `genero` | Género del sustantivo frente a excepciones conocidas (mano, día, problema…) y terminaciones (-ión, -dad, -aje…) | 0 / 1 / 0 | 0 / 1 / 0 |
| `genero_comun` | Sustantivos de persona comunes en cuanto al género («el/la paciente») marcados solo M o F | 0 / 3 / 4 | 0 / 3 / 4 |
| `a_tonica` | Femeninos con a- tónica («el águila», «un hada»), que la gramática no sabe escribir así | 0 / 0 / 2 | 0 / 0 / 2 |
| `plural` | Plural generado frente a las reglas: tildes (exámenes, canciones), -z → -ces, invariables en -s, préstamos | 2 / 0 / 0 | 0 / 0 / 0 |
| `femenino` | Femenino del adjetivo: -o → -a, -or → -ora salvo comparativos, -és → -esa, invariables y la marca inv | 2 / 0 / 0 | 1 / 0 / 0 |
| `verbo_irregular` | Verbos irregulares sin formas= y coherencia interna de formas= | 0 / 0 / 0 | 0 / 0 / 0 |
| `cambio_raiz` | Verbos con cambio de raíz (pensar, volver, pedir) sin cambio= o con un valor distinto | 0 / 0 / 0 | 0 / 0 / 0 |
| `ortografia_verbal` | Cambios ortográficos (-car, -gar, -zar, -guar, -ger, -gir, -guir, -quir, -cer, -cir, -uir, -eer, -ñir) y tildes (envía, evalúa, prohíbe, monosílabos sin tilde) | 1 / 0 / 0 | 0 / 0 / 0 |
| `uso_verbal` | Uso con o sin objeto (I/T/IT) de verbos muy comunes; verbos modales e impersonales | 0 / 11 / 13 | 0 / 11 / 13 |
| `nombre_propio` | Nombres propios: mayúscula, tilde, género y choques con palabras comunes | 0 / 8 / 1 | 0 / 8 / 1 |
| `gramatica` | Formas que la gramática ya trae con otra categoría (existe, una) o que quedan tapadas por ella | 0 / 1 / 4 | 0 / 1 / 4 |
| `palabra_cerrada` | Artículos, preposiciones, pronombres, ser/estar/haber y otras palabras funcionales en la lista abierta | 0 / 0 / 0 | 0 / 0 / 0 |
| `simbolo` | Homónimos que comparten el mismo símbolo lógico (primo: pariente y número primo) | 0 / 0 / 4 | 0 / 0 / 4 |
| `aula` | Vocabulario vulgar o con un doble sentido ofensivo frecuente | 0 / 0 / 2 | 0 / 0 / 2 |
| **Total** | | **5 / 24 / 30** | **1 / 24 / 30** |

## Correcciones aplicadas (confianza alta)

Solo se tocó la columna «extra» de cuatro filas; el orden, los comentarios y los finales de línea del archivo no cambian.

| Línea | Antes | Después | Motivo |
|---|---|---|---|
| 138 | `robot  N  M` → plural «robotes» | `pl=robots` → «robots» | Préstamo acabado en -t: plural en -s. |
| 251 | `crimen  N  M` → plural «crimenes» | `pl=crímenes` → «crímenes» | Llana en -n: el plural es esdrújula y lleva tilde (como examen → exámenes). |
| 893 | `marrón  ADJ  -` → «marrona», «marronas» | `inv` → «marrón», «marrones» | El color «marrón» no cambia en femenino («camisa marrón»). |
| 1154 | `evaluar  V  T` → «evalua, evaluan, evalue, evaluen» | `formas=evalúa,evalúan,evalúe,evalúen,evaluó,evaluaron` | Los verbos en -uar (salvo -guar y -cuar) acentúan la u. |

Efecto visible: «Todos los crímenes son malos», «Todos los robots trabajan» y «Juan evalúa a María» ya se analizan sin supuestos del etiquetador, y «Ninguna camisa es marrón» se acepta (antes se rechazaba sugiriendo «marrona»).

## Error claro que el TSV no podía corregir: arreglado en el generador

**`español` (ADJ, línea 902).** El femenino es «española», pero el generador daba «español» y el formato no tiene una opción para un femenino irregular: «María es español» se aceptaba y «María es española» pasaba por el etiquetador con el símbolo `Españolo`. **Arreglado (2026-11-13)** en `src/batz/lexicon.py`: los adjetivos en -ol forman el femenino en -ola, como los gentilicios en -és y -án que ya estaban. «María es española» da `Español(maria)` sin supuestos, «María es español» se rechaza sugiriendo «española», y `tests/test_lexicon.py` lo cubre. `español` es el único adjetivo del léxico en -ol. La fila 1 de la tabla queda resuelta; si se vuelve a correr el script, ya no aparece.

## Decisiones tomadas (2026-11-13)

Las 54 dudas restantes se decidieron con criterio lingüístico y quedan marcadas en la columna «Visto bueno». Una persona del equipo debe confirmarlas de un vistazo antes de la entrega; este resumen está pensado para eso.

- **Género común (C):** azúcar, soldado, piloto, paciente, poeta, juez, huésped, cliente. «Una paciente duerme» y «Alguna juez ama a Juan» ya se aceptan.
- **Verbos con y sin objeto (IT):** pasear, pescar, enseñar, beber, discutir, aplaudir, cambiar, pintar, entender, morder, bailar, saltar, sufrir, mejorar, ayudar, cazar, comprender, oír, vencer. «Juan bebe» ya se acepta.
- **Quitados:** el verbo modal «poder» (sin infinitivo no dice nada) y los nombres propios que coinciden con palabras comunes (Ángel, Clara, Victoria, Blanca, Dolores, Flor, Norma, Violeta): generaban lecturas falsas como `∀x (Flor(x) → x = clara)`. Quedan 240 nombres propios.
- **Gramática:** «escribe», «estudia», «aprueba» y sus formas también llevan objeto (`spanish_grammar.txt`): «Juan escribe un libro» da `∃x (Libro(x) ∧ Escribir2(juan, x))`. Los 51 casos siguen cumpliendo.
- **Sin cambio, a propósito:** «existe» sigue siendo «hay»; a- tónica (hada, águila) y el homógrafo «una»/«unir» son límites de la gramática; los verbos impersonales y los homónimos con un símbolo se mantienen; «Miriam» sin tilde; «perra» y «zorra» nombran al animal (revisable por el docente).
- **Etiquetador reentrenado** con el léxico revisado (semilla 3032): 96,3 % en palabras nunca vistas y 99,6 % en la categoría gruesa (`docs/validation/ETIQUETADOR-ESPANOL.md`). Baja un poco respecto del 97,1 % anterior porque ahora hay más etiquetas con dos usos o dos géneros.

Tras estas decisiones, `scripts/auditar_lexico.py` da 0 avisos de confianza alta, 1 media y 14 bajas, todos de los que se mantienen a propósito.

## Dudas para decidir (55 avisos)

Ninguno se aplicó. Para decidir rápido:

- **Género común** (filas 3–5, 26–29). Con M solo, «La paciente duerme» se rechaza. Pasar a C es seguro: no cambia las formas en masculino.
- **`azúcar`** (fila 2): con F solo se rechaza «el azúcar», que es el uso más común.
- **Uso de verbos** (filas 6–15, 32–35, 38–42). Ejemplo: «Juan bebe» se rechaza porque `beber` es T. Con IT se aceptan más frases: las lecturas con objeto siguen dando `Beber2` y las nuevas, sin objeto, dan `Beber`.
- **Modal e impersonales** (16, 36, 37, 43, 44): `poder` sin infinitivo, y `llover`/`nevar`/`amanecer`/`anochecer` con sujeto obligatorio.
- **Nombres propios que coinciden con palabras** (17–24). El analizador pasa todo a minúsculas: «Toda flor es clara» da dos lecturas, una de ellas `∀x (Flor(x) → x = clara)`, y «Juan tiene dolores» da `Tener2(juan, dolores)`.
- **Choques con la gramática** (25, 46–49). «Todos los hombres existen» se analiza y «Todo hombre existe» no, porque `existe` es la palabra «hay» de la gramática. «Juan escribió un libro» se acepta y «Juan escribe un libro» no, porque la gramática solo trae «escribe», «estudia» y «aprueba» sin objeto. Esto último se arregla en `spanish_grammar.txt`, no en el léxico, y de esas palabras dependen los 51 casos.
- **a- tónica** (30, 31), **homónimos** con un solo símbolo (50–53), **aula** (54, 55) y **Míriam** (45): decisiones de criterio.

| # | Confianza | Regla | Lema | Formas generadas | Problema | Arreglo sugerido | Visto bueno |
|---|---|---|---|---|---|---|---|
| 1 | alta | femenino | **español** (ADJ, l. 902) | español · español · españoles · españoles | el femenino es «española» y se genera «español» | **resuelto en lexicon.py (regla -ol → -ola)** | [x] |
| 2 | media | genero | **azúcar** (N, l. 548) | azúcar → azúcares | «azúcar» es de género ambiguo y lo más común es el masculino («el azúcar»); con F solo se rechaza ese uso | cambiar el género F → C | [x] aplicado: C |
| 3 | media | genero_comun | **soldado** (N, l. 59) | soldado → soldados | es común en cuanto al género: «el soldado» y «la soldado» | cambiar el género M → C | [x] aplicado: C |
| 4 | media | genero_comun | **piloto** (N, l. 304) | piloto → pilotos | es común en cuanto al género: «el piloto» y «la piloto» | cambiar el género M → C | [x] aplicado: C |
| 5 | media | genero_comun | **paciente** (N, l. 317) | paciente → pacientes | es común en cuanto al género: «el paciente» y «la paciente» | cambiar el género M → C | [x] aplicado: C |
| 6 | media | uso_verbal | **pasear** (V, l. 965) | pasea, pasean, pasee, paseen, paseó, pasearon | uso I, pero lo normal es IT: «Juan pasea» / «Juan pasea al perro» | cambiar el uso I → IT | [x] aplicado: IT |
| 7 | media | uso_verbal | **pescar** (V, l. 971) | pesca, pescan, pesque, pesquen, pescó, pescaron | uso I, pero lo normal es IT: «Juan pesca» / «Juan pesca un pez» | cambiar el uso I → IT | [x] aplicado: IT |
| 8 | media | uso_verbal | **enseñar** (V, l. 1013) | enseña, enseñan, enseñe, enseñen, enseñó, enseñaron | uso T, pero lo normal es IT: «La profesora enseña» / «La profesora enseña lógica» | cambiar el uso T → IT | [x] aplicado: IT |
| 9 | media | uso_verbal | **beber** (V, l. 1033) | bebe, beben, beba, beban, bebió, bebieron | uso T, pero lo normal es IT: «Juan bebe» / «Juan bebe agua» | cambiar el uso T → IT | [x] aplicado: IT |
| 10 | media | uso_verbal | **discutir** (V, l. 1040) | discute, discuten, discuta, discutan, discutió, discutieron | uso T, pero lo normal es IT: «Los vecinos discuten» / «Los vecinos discuten el plan» | cambiar el uso T → IT | [x] aplicado: IT |
| 11 | media | uso_verbal | **aplaudir** (V, l. 1041) | aplaude, aplauden, aplauda, aplaudan, aplaudió, aplaudieron | uso T, pero lo normal es IT: «El público aplaude» / «El público aplaude a la actriz» | cambiar el uso T → IT | [x] aplicado: IT |
| 12 | media | uso_verbal | **cambiar** (V, l. 1071) | cambia, cambian, cambie, cambien, cambió, cambiaron | uso T, pero lo normal es IT: «El clima cambia» / «Juan cambia la rueda» | cambiar el uso T → IT | [x] aplicado: IT |
| 13 | media | uso_verbal | **pintar** (V, l. 1124) | pinta, pintan, pinte, pinten, pintó, pintaron | uso T, pero lo normal es IT: «Ana pinta» / «Ana pinta un cuadro» | cambiar el uso T → IT | [x] aplicado: IT |
| 14 | media | uso_verbal | **entender** (V, l. 1182) | entiende, entienden, entienda, entiendan, entendió, entendieron | uso T, pero lo normal es IT: «Juan entiende» / «Juan entiende la pregunta» | cambiar el uso T → IT | [x] aplicado: IT |
| 15 | media | uso_verbal | **morder** (V, l. 1194) | muerde, muerden, muerda, muerdan, mordió, mordieron | uso T, pero lo normal es IT: «El perro muerde» / «El perro muerde un hueso» | cambiar el uso T → IT | [x] aplicado: IT |
| 16 | media | uso_verbal | **poder** (V, l. 1219) | puede, pueden, pueda, puedan, pudo, pudieron | verbo modal: sin infinitivo («puede nadar») no dice nada, y la gramática no admite infinitivos | quitar la fila o dejarla para usos elípticos («Juan puede») | [x] fila quitada |
| 17 | media | nombre_propio | **Ángel** (NP, l. 1302) | ángel | en minúsculas coincide con ángel (N); el analizador no distingue mayúsculas y añade lecturas como «x = angel» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 18 | media | nombre_propio | **Clara** (NP, l. 1395) | clara | en minúsculas coincide con claro (ADJ); el analizador no distingue mayúsculas y añade lecturas como «x = clara» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 19 | media | nombre_propio | **Victoria** (NP, l. 1420) | victoria | en minúsculas coincide con victoria (N); el analizador no distingue mayúsculas y añade lecturas como «x = victoria» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 20 | media | nombre_propio | **Blanca** (NP, l. 1432) | blanca | en minúsculas coincide con blanco (ADJ); el analizador no distingue mayúsculas y añade lecturas como «x = blanca» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 21 | media | nombre_propio | **Dolores** (NP, l. 1437) | dolores | en minúsculas coincide con dolor (N); el analizador no distingue mayúsculas y añade lecturas como «x = dolores» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 22 | media | nombre_propio | **Flor** (NP, l. 1444) | flor | en minúsculas coincide con flor (N); el analizador no distingue mayúsculas y añade lecturas como «x = flor» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 23 | media | nombre_propio | **Norma** (NP, l. 1465) | norma | en minúsculas coincide con norma (N); el analizador no distingue mayúsculas y añade lecturas como «x = norma» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 24 | media | nombre_propio | **Violeta** (NP, l. 1476) | violeta | en minúsculas coincide con violeta (ADJ); el analizador no distingue mayúsculas y añade lecturas como «x = violeta» | quitar el nombre o aceptar la lectura extra | [x] nombre quitado |
| 25 | media | gramatica | **existir** (V, l. 960) | existe, existen, exista, existan, existió, existieron | «existe» ya es palabra de la gramática (Hay) y esa forma de «existir» no se puede usar | quitar la fila o aceptar el hueco | [x] se acepta el hueco: «existe» es «hay» |
| 26 | baja | genero_comun | **poeta** (N, l. 31) | poeta → poetas | también se dice «la poeta» (además de «la poetisa», que no está en el léxico) | cambiar el género M → C, o añadir «poetisa» como N F | [x] aplicado: C |
| 27 | baja | genero_comun | **juez** (N, l. 254) | juez → jueces | también se dice «la juez» (además de «la jueza», que no está en el léxico) | cambiar el género M → C, o añadir «jueza» como N F | [x] aplicado: C |
| 28 | baja | genero_comun | **huésped** (N, l. 284) | huésped → huéspedes | también se dice «la huésped» (además de «la huéspeda», que no está en el léxico) | cambiar el género M → C, o añadir «huéspeda» como N F | [x] aplicado: C |
| 29 | baja | genero_comun | **cliente** (N, l. 316) | cliente → clientes | también se dice «la cliente» (además de «la clienta», que no está en el léxico) | cambiar el género M → C, o añadir «clienta» como N F | [x] aplicado: C |
| 30 | baja | a_tonica | **hada** (N, l. 597) | hada → hadas | femenino con a- tónica: se dice «el hada», «un hada», pero la gramática solo acepta «una hada», «alguna hada»… | nada en el léxico; es un límite de la gramática *(no se arregla en el TSV)* | [x] límite de la gramática; sin cambio |
| 31 | baja | a_tonica | **águila** (N, l. 1505) | águila → águilas | femenino con a- tónica: se dice «el águila», «un águila», pero la gramática solo acepta «una águila», «alguna águila»… | nada en el léxico; es un límite de la gramática *(no se arregla en el TSV)* | [x] límite de la gramática; sin cambio |
| 32 | baja | uso_verbal | **bailar** (V, l. 928) | baila, bailan, baile, bailen, bailó, bailaron | uso I, pero lo normal es IT: «Ana baila» / «Ana baila un tango» | cambiar el uso I → IT | [x] aplicado: IT |
| 33 | baja | uso_verbal | **saltar** (V, l. 934) | salta, saltan, salte, salten, saltó, saltaron | uso I, pero lo normal es IT: «El gato salta» / «El gato salta el muro» | cambiar el uso I → IT | [x] aplicado: IT |
| 34 | baja | uso_verbal | **sufrir** (V, l. 944) | sufre, sufren, sufra, sufran, sufrió, sufrieron | uso I, pero lo normal es IT: «Juan sufre» / «Juan sufre un accidente» | cambiar el uso I → IT | [x] aplicado: IT |
| 35 | baja | uso_verbal | **mejorar** (V, l. 977) | mejora, mejoran, mejore, mejoren, mejoró, mejoraron | uso I, pero lo normal es IT: «El enfermo mejora» / «Juan mejora el programa» | cambiar el uso I → IT | [x] aplicado: IT |
| 36 | baja | uso_verbal | **amanecer** (V, l. 994) | amanece, amanecen, amanezca, amanezcan, amaneció, amanecieron | verbo impersonal: en su uso normal no lleva sujeto («llueve»), pero la gramática siempre pide uno | quitar la fila o mantenerla para usos figurados | [x] se mantiene (usos figurados) |
| 37 | baja | uso_verbal | **anochecer** (V, l. 995) | anochece, anochecen, anochezca, anochezcan, anocheció, anochecieron | verbo impersonal: en su uso normal no lleva sujeto («llueve»), pero la gramática siempre pide uno | quitar la fila o mantenerla para usos figurados | [x] se mantiene (usos figurados) |
| 38 | baja | uso_verbal | **ayudar** (V, l. 1012) | ayuda, ayudan, ayude, ayuden, ayudó, ayudaron | uso T, pero lo normal es IT: «Juan ayuda» / «Juan ayuda a Ana» | cambiar el uso T → IT | [x] aplicado: IT |
| 39 | baja | uso_verbal | **cazar** (V, l. 1060) | caza, cazan, cace, cacen, cazó, cazaron | uso T, pero lo normal es IT: «El león caza» / «El león caza una cebra» | cambiar el uso T → IT | [x] aplicado: IT |
| 40 | baja | uso_verbal | **comprender** (V, l. 1076) | comprende, comprenden, comprenda, comprendan, comprendió, comprendieron | uso T, pero lo normal es IT: «Juan comprende» / «Juan comprende el problema» | cambiar el uso T → IT | [x] aplicado: IT |
| 41 | baja | uso_verbal | **oír** (V, l. 1222) | oye, oyen, oiga, oigan, oyó, oyeron | uso T, pero lo normal es IT: «Juan no oye» / «Juan oye un ruido» | cambiar el uso T → IT | [x] aplicado: IT |
| 42 | baja | uso_verbal | **vencer** (V, l. 1241) | vence, vencen, venza, venzan, venció, vencieron | uso T, pero lo normal es IT: «Juan vence» / «Juan vence al rival» | cambiar el uso T → IT | [x] aplicado: IT |
| 43 | baja | uso_verbal | **llover** (V, l. 1247) | llueve, llueven, llueva, lluevan, llovió, llovieron | verbo impersonal: en su uso normal no lleva sujeto («llueve»), pero la gramática siempre pide uno | quitar la fila o mantenerla para usos figurados | [x] se mantiene (usos figurados) |
| 44 | baja | uso_verbal | **nevar** (V, l. 1248) | nieva, nievan, nieve, nieven, nevó, nevaron | verbo impersonal: en su uso normal no lleva sujeto («llueve»), pero la gramática siempre pide uno | quitar la fila o mantenerla para usos figurados | [x] se mantiene (usos figurados) |
| 45 | baja | nombre_propio | **Miriam** (NP, l. 1462) | miriam | la ortografía académica escribe «Míriam» (llana acabada en -m), aunque muchas personas lo escriben sin tilde | escribir «Míriam» o dejarlo como está | [x] se mantiene «Miriam», la grafía más usada |
| 46 | baja | gramatica | **unir** (V, l. 1146) | une, unen, una, unan, unió, unieron | «una» ya es palabra de la gramática (DetE_FS, Indef_FS) y esa forma de «unir» no se puede usar | nada que hacer en el léxico; es un homógrafo *(no se arregla en el TSV)* | [x] homógrafo; sin cambio |
| 47 | baja | gramatica | **escribir** (V, l. 1159) | escribe, escriben, escriba, escriban, escribió, escribieron | la gramática ya trae estas formas con otra categoría y manda ella; se pierde escriba: VTsub_S; escriban: VTsub_P; escribe: VT_S; escriben: VT_P | nada en el léxico; para usarlas habría que tocar spanish_grammar.txt (de esas palabras dependen los 51 casos) *(no se arregla en el TSV)* | [x] arreglado en spanish_grammar.txt (también con objeto) |
| 48 | baja | gramatica | **estudiar** (V, l. 1160) | estudia, estudian, estudie, estudien, estudió, estudiaron | la gramática ya trae estas formas con otra categoría y manda ella; se pierde estudia: VT_S; estudian: VT_P; estudie: VTsub_S; estudien: VTsub_P | nada en el léxico; para usarlas habría que tocar spanish_grammar.txt (de esas palabras dependen los 51 casos) *(no se arregla en el TSV)* | [x] arreglado en spanish_grammar.txt (también con objeto) |
| 49 | baja | gramatica | **aprobar** (V, l. 1240) | aprueba, aprueban, apruebe, aprueben, aprobó, aprobaron | la gramática ya trae estas formas con otra categoría y manda ella; se pierde aprueba: VT_S; aprueban: VT_P; apruebe: VTsub_S; aprueben: VTsub_P | nada en el léxico; para usarlas habría que tocar spanish_grammar.txt (de esas palabras dependen los 51 casos) *(no se arregla en el TSV)* | [x] arreglado en spanish_grammar.txt (también con objeto) |
| 50 | baja | simbolo | **primo** (N, l. 56) | primo → primos | el sustantivo y el adjetivo «primo» (pariente / número primo) dan el mismo predicado Primo | nada obligatorio; si molesta, quitar una de las dos entradas | [x] se acepta el símbolo compartido |
| 51 | baja | simbolo | **dulce** (N, l. 214) | dulce → dulces | el sustantivo y el adjetivo «dulce» (golosina / de sabor dulce) dan el mismo predicado Dulce | nada obligatorio; si molesta, quitar una de las dos entradas | [x] se acepta el símbolo compartido |
| 52 | baja | simbolo | **lógico** (N, l. 314) | lógico → lógicos | el sustantivo y el adjetivo «lógico» (especialista en lógica / razonable) dan el mismo predicado Logico | nada obligatorio; si molesta, quitar una de las dos entradas | [x] se acepta el símbolo compartido |
| 53 | baja | simbolo | **paciente** (N, l. 317) | paciente → pacientes | el sustantivo y el adjetivo «paciente» (persona enferma / que tiene paciencia) dan el mismo predicado Paciente | nada obligatorio; si molesta, quitar una de las dos entradas | [x] se acepta el símbolo compartido |
| 54 | baja | aula | **perra** (N, l. 628) | perra → perras | además de la hembra del perro, se usa como insulto contra mujeres | decisión docente: mantener o quitar la fila | [x] se mantiene: nombra al animal (decisión revisable por el docente) |
| 55 | baja | aula | **zorra** (N, l. 634) | zorra → zorras | además de la hembra del zorro, es un insulto vulgar muy frecuente contra mujeres | decisión docente: mantener o quitar la fila | [x] se mantiene: nombra al animal (decisión revisable por el docente) |

## Lo que no apareció

No hay filas mal formadas, duplicadas ni en conflicto, ni palabras funcionales (artículos, preposiciones, pronombres, ser/estar/haber) en la lista abierta. Las trampas de género conocidas están bien (mano, día, problema, planeta, flor, avión…). Los 40 verbos con `cambio=` llevan el valor correcto, los 48 con `formas=` son coherentes y ningún irregular conocido se conjuga como regular. No se señalan los homógrafos legítimos, como `bajo` (adjetivo y preposición), `mañana` y `tarde` (sustantivo y adverbio) o `entre` (de «entrar» y preposición): la gramática no usa esas palabras funcionales.

Cobertura, no errores: hay femeninos sin su masculino (`directora`, `enfermera`, `esposa`, `novia`), y muchos sustantivos de persona no tienen femenino (`médica`, `científica`…).

## Pruebas

- `PYTHONPATH="src;tests" python -m unittest discover -s tests`: 221 pruebas, todas correctas (las 217 de antes más las 4 nuevas de `tests/test_lexicon_audit.py`).
- `PYTHONPATH=src python scripts/report_spanish.py --check`: 51 de 51 casos cumplen. Al regenerarse, `docs/validation/ESPANOL-51-CASOS.md` queda idéntico.

## Etiquetador

No hace falta reentrenarlo por estas cuatro correcciones. El etiquetador solo actúa sobre palabras que no están en el diccionario, y «crímenes», «robots», «evalúa» y «marrón» ya están. Además, esos lemas son 4 de los 1551 de los que salió su entrenamiento. Conviene reentrenarlo (`scripts/train_spanish_tagger.py`, que necesita numpy y reescribe `spanish_tagger.json` y `ETIQUETADOR-ESPANOL.md`) una sola vez, cuando la revisión humana cierre la tabla. Los cambios de uso I/T/IT y de género alteran los ejemplos de entrenamiento.

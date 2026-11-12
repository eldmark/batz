# Etiquetador de palabras fuera del léxico

> Documento generado por `scripts/train_spanish_tagger.py`. No se edita a mano.

## Qué hace

La gramática del español controlado tiene un léxico cerrado. Cuando una frase trae una palabra que no está, el etiquetador propone su categoría (sustantivo, adjetivo, verbo con o sin objeto, nombre propio, con género y número). La frase se analiza con esa propuesta por la misma gramática, y la interfaz muestra qué se supuso. El etiquetador no elige entre lecturas ni decide nada lógico.

## Modelo y datos

- Regresión logística multinomial, 18 etiquetas, 1094 rasgos (terminaciones de 1 a 4 letras, mayúscula, tilde, longitud y las palabras funcionales vecinas).
- Entrenada por descenso de gradiente por lotes (64) sobre la entropía cruzada, con penalización L2 y tasa de aprendizaje decreciente.
- 17605 ejemplos de entrenamiento, generados con plantillas a partir de 476 lemas. Las etiquetas son correctas por construcción.
- **Partición por lema** (70 % / 15 % / 15 %): validación y prueba solo contienen palabras que el modelo nunca vio.
- Las conversaciones de clase no se usaron para entrenar: casi no contienen frases en lenguaje natural. Sirven de prueba final (abajo).

## Ajuste de hiperparámetros

| Tasa de aprendizaje | L2 | Mejor época | Exactitud en validación | Exactitud en la última época |
|---|---|---|---|---|
| 0.1 | 0.0 | 11 | 0.964 | 0.963 |
| 0.1 | 0.0001 | 13 | 0.964 | 0.963 |
| 0.1 | 0.001 | 11 | 0.963 | 0.963 |
| 0.5 | 0.0 | 11 | 0.975 | 0.969 |
| 0.5 | 0.0001 | 11 | 0.974 | 0.969 |
| 0.5 | 0.001 | 6 | 0.971 | 0.965 |
| 2.0 | 0.0 | 13 | 0.976 | 0.966 |
| 2.0 | 0.0001 | 5 | 0.976 **← elegido** | 0.962 |
| 2.0 | 0.001 | 9 | 0.972 | 0.954 |

## Resultado en palabras nunca vistas

- Exactitud con etiqueta completa (categoría, género y número): **94.4%** sobre 4426 palabras.
- Exactitud de la categoría gruesa (sustantivo / adjetivo / verbo con objeto / verbo sin objeto / nombre): **99.5%**.

Confusiones más frecuentes (real → propuesta):

- N_MP → N_FP: 68
- N_FP → N_MP: 40
- Adj_MP → Adj_FP: 24
- N_MS → N_FS: 21
- Adj_FS → Adj_MS: 20
- Adj_FP → Adj_MP: 12
- N_FS → N_MS: 10
- Adj_FS → VI_S: 9

La gramática corrige parte de estos errores: una etiqueta que no concuerda con el resto de la frase no produce ningún árbol, y por eso se prueban las dos más probables.

## Frases de clase (prueba de extremo a extremo)

**19 de 20** dan la fórmula esperada. Las frases y sus fórmulas esperadas están en `docs/specs/espanol/frases_clase.tsv`.

| Frase | Esperada | Obtenida | Supuestos | Cumple |
|---|---|---|---|---|
| Todos los estudiantes aprobaron | `∀x (Estudiante(x) → Aprobar(x))` | `∀x (Estudiante(x) → Aprobar(x))` | aprobaron→VI_P (92%) | sí |
| Existe un estudiante que aprueba | `∃x (Estudiante(x) ∧ Aprobar(x))` | `∃x (Estudiante(x) ∧ Aprobar(x))` |  | sí |
| Todos los hombres son mortales | `∀x (Hombre(x) → Mortal(x))` | `∀x (Hombre(x) → Mortal(x))` | hombres→N_MP (100%); mortales→Adj_MP (56%) | sí |
| Sócrates es un hombre | `Hombre(socrates)` | `Hombre(socrates)` | Sócrates→NProp_M (90%); hombre→N_MS (100%) | sí |
| Sócrates es mortal | `Mortal(socrates)` | `Mortal(socrates)` | Sócrates→NProp_M (90%); mortal→Adj_MS (34%) | sí |
| Ningún perro vuela | `¬∃x (Perro(x) ∧ Vuelar(x))` | `¬∃x (Perro(x) ∧ Vuelar(x))` | perro→N_MS (100%); vuela→VI_S (99%) | sí |
| Todos los perros ladran | `∀x (Perro(x) → Ladrar(x))` | `∀x (Perro(x) → Ladrar(x))` | perros→N_MP (100%); ladran→VI_P (98%) | sí |
| Algún gato duerme | `∃x (Gato(x) ∧ Duermer(x))` | `∃x (Gato(x) ∧ Duermer(x))` | duerme→VI_S (98%) | sí |
| Carlos respeta a Lucía | `Respetar2(carlos, lucia)` | `Respetar2(carlos, lucia)` | Carlos→NProp_M (60%); respeta→VT_S (98%); Lucía→NProp_F (98%) | sí |
| Todo filósofo admira a Sócrates | `∀x (Filosofo(x) → Admirar2(x, socrates))` | `∀x (Filosofo(x) → Admirar2(x, socrates))` | filósofo→N_MS (100%); admira→VT_S (100%); Sócrates→NProp_M (96%) | sí |
| Hay una mujer que canta | `∃x (Mujer(x) ∧ Cantar(x))` | `∃x (Mujer(x) ∧ Cantar(x))` | mujer→N_FS (92%); canta→VI_S (76%) | sí |
| Ninguna ballena es un pez | `¬∃x (Ballena(x) ∧ Pez(x))` | rechazada: Palabra fuera del léxico: ballena |  | **no** |
| Todos los números primos son impares | `∀x (Numero(x) ∧ Primo(x) → Impar(x))` | `∀x (Numero(x) ∧ Primo(x) → Impar(x))` | números→N_MP (100%); primos→Adj_MP (99%); impares→Adj_MP (54%) | sí |
| Si Carlos canta, entonces Lucía baila | `Cantar(carlos) → Bailar(lucia)` | `Cantar(carlos) → Bailar(lucia)` | Carlos→NProp_M (39%); canta→VI_S (94%); Lucía→NProp_F (98%); baila→VI_S (100%) | sí |
| Carlos es valiente y honesto | `Valiente(carlos) ∧ Honesto(carlos)` | `Valiente(carlos) ∧ Honesto(carlos)` | Carlos→NProp_M (51%); valiente→Adj_MS (46%); honesto→Adj_MS (64%) | sí |
| Todas las ballenas nadan | `∀x (Ballena(x) → Nadar(x))` | `∀x (Ballena(x) → Nadar(x))` | ballenas→N_FP (100%); nadan→VI_P (98%) | sí |
| Algunos políticos mienten | `∃x (Politico(x) ∧ Mienter(x))` | `∃x (Politico(x) ∧ Mienter(x))` | políticos→N_MP (100%); mienten→VI_P (99%) | sí |
| Cada niño quiere a un perro | `∀x (Niño(x) → ∃y (Perro(y) ∧ Quierer2(x, y)))` | `∀x (Niño(x) → ∃y (Perro(y) ∧ Quierer2(x, y)))` / `∃y (Perro(y) ∧ ∀x (Niño(x) → Quierer2(x, y)))` | niño→N_MS (97%); quiere→VT_S (99%); perro→N_MS (100%) | sí |
| No hay ningún triángulo que sea cuadrado | RECHAZA | rechazada: Palabra fuera del léxico: triángulo |  | sí |
| Perros los todos ladran | RECHAZA | rechazada: Palabra fuera del léxico: Perros |  | sí |

## Límites

- Distingue verbo con objeto de verbo sin objeto sobre todo por lo que sigue; al final de frase la forma no basta.
- El nombre del predicado es un lema aproximado sin tildes (`perros` → `Perro`, `ladran` → `Ladrar`); con verbos irregulares puede no coincidir entre formas.
- Las listas de lemas las escribió el asistente y no tienen revisión humana.

## Cómo repetir

```bash
PYTHONPATH=src python3 scripts/train_spanish_tagger.py
```

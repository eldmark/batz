# Etiquetador de palabras fuera del léxico

> Documento generado por `scripts/train_spanish_tagger.py`. No se edita a mano.

## Qué hace

La gramática del español controlado tiene un léxico cerrado. Cuando una frase trae una palabra que no está, el etiquetador propone su categoría (sustantivo, adjetivo, verbo con o sin objeto, nombre propio, con género y número). La frase se analiza con esa propuesta por la misma gramática, y la interfaz muestra qué se supuso. El etiquetador no elige entre lecturas ni decide nada lógico.

## Modelo y datos

- Regresión logística multinomial, 18 etiquetas, 2640 rasgos (terminaciones de 1 a 4 letras, mayúscula, tilde, longitud y las palabras funcionales vecinas).
- Entrenada por descenso de gradiente por lotes (64) sobre la entropía cruzada, con penalización L2 y tasa de aprendizaje decreciente.
- 26408 ejemplos de entrenamiento, generados con plantillas a partir de 2372 lemas. Las etiquetas son correctas por construcción.
- **Partición por lema** (70 % / 15 % / 15 %): validación y prueba solo contienen palabras que el modelo nunca vio.
- Las conversaciones de clase no se usaron para entrenar: casi no contienen frases en lenguaje natural. Sirven de prueba final (abajo).

## Ajuste de hiperparámetros

| Tasa de aprendizaje | L2 | Mejor época | Exactitud en validación | Exactitud en la última época |
|---|---|---|---|---|
| 0.1 | 0.0 | 14 | 0.972 | 0.972 |
| 0.1 | 0.0001 | 14 | 0.972 | 0.972 |
| 0.1 | 0.001 | 14 | 0.972 | 0.972 |
| 0.5 | 0.0 | 14 | 0.977 | 0.977 |
| 0.5 | 0.0001 | 10 | 0.977 | 0.976 |
| 0.5 | 0.001 | 14 | 0.974 | 0.974 |
| 2.0 | 0.0 | 14 | 0.979 **← elegido** | 0.979 |
| 2.0 | 0.0001 | 10 | 0.978 | 0.977 |
| 2.0 | 0.001 | 10 | 0.975 | 0.975 |

## Resultado en palabras nunca vistas

- Exactitud con etiqueta completa (categoría, género y número): **96.4%** sobre 4427 palabras.
- Exactitud de la categoría gruesa (sustantivo / adjetivo / verbo con objeto / verbo sin objeto / nombre): **99.9%**.

Confusiones más frecuentes (real → propuesta):

- NProp_F → NProp_M: 45
- N_FP → N_MP: 24
- N_MP → N_FP: 23
- NProp_M → NProp_F: 20
- Adj_MP → Adj_FP: 14
- N_FS → N_MS: 9
- Adj_MS → Adj_FS: 9
- N_MS → N_FS: 3

La gramática corrige parte de estos errores: una etiqueta que no concuerda con el resto de la frase no produce ningún árbol, y por eso se prueban las dos más probables.

## Frases de clase (prueba de extremo a extremo)

**25 de 25** dan la fórmula esperada. Las frases y sus fórmulas esperadas están en `docs/specs/espanol/frases_clase.tsv`.

| Frase | Esperada | Obtenida | Supuestos | Cumple |
|---|---|---|---|---|
| Todos los estudiantes aprobaron | `∀x (Estudiante(x) → Aprobar(x))` | `∀x (Estudiante(x) → Aprobar(x))` |  | sí |
| Existe un estudiante que aprueba | `∃x (Estudiante(x) ∧ Aprobar(x))` | `∃x (Estudiante(x) ∧ Aprobar(x))` |  | sí |
| Todos los hombres son mortales | `∀x (Hombre(x) → Mortal(x))` | `∀x (Hombre(x) → Mortal(x))` |  | sí |
| Sócrates es un hombre | `Hombre(socrates)` | `Hombre(socrates)` |  | sí |
| Sócrates es mortal | `Mortal(socrates)` | `Mortal(socrates)` |  | sí |
| Ningún perro vuela | `¬∃x (Perro(x) ∧ Volar(x))` | `¬∃x (Perro(x) ∧ Volar(x))` |  | sí |
| Todos los perros ladran | `∀x (Perro(x) → Ladrar(x))` | `∀x (Perro(x) → Ladrar(x))` |  | sí |
| Algún gato duerme | `∃x (Gato(x) ∧ Dormir(x))` | `∃x (Gato(x) ∧ Dormir(x))` |  | sí |
| Carlos respeta a Lucía | `Respetar2(carlos, lucia)` | `Respetar2(carlos, lucia)` |  | sí |
| Todo filósofo admira a Sócrates | `∀x (Filosofo(x) → Admirar2(x, socrates))` | `∀x (Filosofo(x) → Admirar2(x, socrates))` |  | sí |
| Hay una mujer que canta | `∃x (Mujer(x) ∧ Cantar(x))` | `∃x (Mujer(x) ∧ Cantar(x))` |  | sí |
| Ninguna ballena es un pez | `¬∃x (Ballena(x) ∧ Pez(x))` | `¬∃x (Ballena(x) ∧ Pez(x))` |  | sí |
| Todos los números primos son impares | `∀x (Numero(x) ∧ Primo(x) → Impar(x))` | `∀x (Numero(x) ∧ Primo(x) → Impar(x))` |  | sí |
| Si Carlos canta, entonces Lucía baila | `Cantar(carlos) → Bailar(lucia)` | `Cantar(carlos) → Bailar(lucia)` |  | sí |
| Carlos es valiente y honesto | `Valiente(carlos) ∧ Honesto(carlos)` | `Valiente(carlos) ∧ Honesto(carlos)` |  | sí |
| Todas las ballenas nadan | `∀x (Ballena(x) → Nadar(x))` | `∀x (Ballena(x) → Nadar(x))` |  | sí |
| Algunos políticos mienten | `∃x (Politico(x) ∧ Mentir(x))` | `∃x (Politico(x) ∧ Mentir(x))` |  | sí |
| Cada niño quiere a un perro | `∀x (Niño(x) → ∃y (Perro(y) ∧ Querer2(x, y)))` | `∀x (Niño(x) → ∃y (Perro(y) ∧ Querer2(x, y)))` / `∃y (Perro(y) ∧ ∀x (Niño(x) → Querer2(x, y)))` |  | sí |
| No hay ningún triángulo que sea cuadrado | RECHAZA | rechazada: Palabra fuera del léxico: sea |  | sí |
| Perros los todos ladran | RECHAZA | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal |  | sí |
| Si una persona es humana, entonces es mortal | `∀x (Persona(x) ∧ Humano(x) → Mortal(x))` | `∀x (Persona(x) ∧ Humano(x) → Mortal(x))` |  | sí |
| Si Juan estudia, aprueba | `Estudiar(juan) → Aprobar(juan)` | `Estudiar(juan) → Aprobar(juan)` |  | sí |
| Todos los unicornios galopan | `∀x (Unicornio(x) → Galopar(x))` | `∀x (Unicornio(x) → Galopar(x))` | unicornios→N_MP (100%); galopan→VI_P (100%) | sí |
| Los políticos mienten | RECHAZA | rechazada: «Los» solo no dice cuántos: empieza con «todos los», «algunos», «ningún» o «un». |  | sí |
| si una persona es humano entonces es mortal | RECHAZA | rechazada: «humano» no concuerda en género con su sujeto. ¿Quisiste decir «humana»? |  | sí |

## Límites

- Distingue verbo con objeto de verbo sin objeto sobre todo por lo que sigue; al final de frase la forma no basta.
- El nombre del predicado es un lema aproximado sin tildes (`perros` → `Perro`, `ladran` → `Ladrar`); con verbos irregulares puede no coincidir entre formas.
- El diccionario base lo generó un modelo de lenguaje y no tiene revisión humana.
- Estas cifras miden palabras que **no** están en el diccionario; las que sí están no pasan por el etiquetador.

## Cómo repetir

```bash
PYTHONPATH=src python3 scripts/train_spanish_tagger.py
```

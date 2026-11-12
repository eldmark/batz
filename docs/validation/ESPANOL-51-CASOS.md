# Español controlado: los 51 casos de la especificación

> Documento generado por `scripts/report_spanish.py`. No se edita a mano: se vuelve a generar.

**Resultado: 51 de 51 casos cumplen.** 39 frases se aceptan (6 con más de una lectura) y 12 se rechazan a propósito.

Cómo se lee cada fila:

- **Esperado** es el número mínimo de árboles sintácticos distintos que fija la especificación; `0` significa que la frase debe rechazarse.
- **Lecturas** son las fórmulas distintas que se le ofrecen a la persona. Nunca se elige una en silencio.
- Una frase aceptada cumple si tiene al menos los árboles esperados, produce alguna lectura y cada lectura vuelve a leerse como fórmula bien formada. Una rechazada cumple si no produce ningún árbol ni ninguna lectura.

| # | Frase | Esperado | Árboles | Lecturas | Cumple |
|---|---|---|---|---|---|
| 1 | Todos los estudiantes leen un libro. | 1 | 1 | `∀x (Estudiante(x) → ∃y (Libro(y) ∧ Leer2(x, y)))`<br>`∃y (Libro(y) ∧ ∀x (Estudiante(x) → Leer2(x, y)))` | sí |
| 2 | Todo estudiante que estudia aprueba. | 1 | 1 | `∀x (Estudiante(x) ∧ Estudiar(x) → Aprobar(x))` | sí |
| 3 | Ningún estudiante lee. | 1 | 1 | `¬∃x (Estudiante(x) ∧ Leer(x))` | sí |
| 4 | Juan no lee ningún libro. | 1 | 1 | `¬∃x (Libro(x) ∧ Leer2(juan, x))` | sí |
| 5 | Ningún estudiante no lee. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 6 | Juan lee ningún libro. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 7 | Juan es un estudiante. | 1 | 1 | `Estudiante(juan)` | sí |
| 8 | Juan es Pedro. | 1 | 1 | `juan = pedro` | sí |
| 9 | María es alto. | 0 | 0 | rechazada: «alto» no concuerda en género con su sujeto. ¿Quisiste decir «alta»? | sí |
| 10 | Todos los estudiantes lee. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 11 | Si Juan lee, entonces María estudia y Pedro estudia. | 2 | 2 | `Leer(juan) → Estudiar(maria) ∧ Estudiar(pedro)`<br>`(Leer(juan) → Estudiar(maria)) ∧ Estudiar(pedro)` | sí |
| 12 | Juan lee y María estudia o Pedro estudia. | 2 | 2 | `Leer(juan) ∧ (Estudiar(maria) ∨ Estudiar(pedro))`<br>`Leer(juan) ∧ Estudiar(maria) ∨ Estudiar(pedro)` | sí |
| 13 | Juan y María leen. | 1 | 1 | `Leer(juan) ∧ Leer(maria)` | sí |
| 14 | Juan, Pedro y Ana leen. | 1 | 1 | `Leer(juan) ∧ Leer(pedro) ∧ Leer(ana)` | sí |
| 15 | Juan y María lee. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 16 | Hay un estudiante que lee. | 1 | 1 | `∃x (Estudiante(x) ∧ Leer(x))` | sí |
| 17 | No hay ningún estudiante que lea. | 1 | 1 | `¬∃x (Estudiante(x) ∧ Leer(x))` | sí |
| 18 | Solo los estudiantes leen. | 1 | 1 | `∀x (Leer(x) → Estudiante(x))` | sí |
| 19 | Solo Juan lee. | 1 | 1 | `∀x (Leer(x) → x = juan)` | sí |
| 20 | Juan se ama. | 1 | 1 | `Amar2(juan, juan)` | sí |
| 21 | Juan ama a María. | 1 | 1 | `Amar2(juan, maria)` | sí |
| 22 | Juan ve a todos los estudiantes. | 1 | 1 | `∀x (Estudiante(x) → Ver2(juan, x))` | sí |
| 23 | Juan lee si y solo si María lee. | 1 | 1 | `Leer(juan) ↔ Leer(maria)` | sí |
| 24 | O bien Juan lee o bien María lee. | 1 | 1 | `(Leer(juan) ∨ Leer(maria)) ∧ ¬(Leer(juan) ∧ Leer(maria))` | sí |
| 25 | Juan es joven. | 2 | 2 | `Joven_sust(juan)`<br>`Joven_adj(juan)` | sí |
| 26 | Todos los estudiantes no leen. | 1 | 1 | `∀x (Estudiante(x) → ¬Leer(x))`<br>`¬∀x (Estudiante(x) → Leer(x))` | sí |
| 27 | Juan lee. | 1 | 1 | `Leer(juan)` | sí |
| 28 | El estudiante lee. | 0 | 0 | rechazada: «El» solo no dice cuántos: empieza con «todos los», «algunos», «ningún» o «un». | sí |
| 29 | Los estudiantes leen. | 0 | 0 | rechazada: «Los» solo no dice cuántos: empieza con «todos los», «algunos», «ningún» o «un». | sí |
| 30 | Juan leyó un libro. | 1 | 1 | `∃x (Libro(x) ∧ Leer2(juan, x))` | sí |
| 31 | Todo estudiante inteligente aprueba. | 1 | 1 | `∀x (Estudiante(x) ∧ Inteligente(x) → Aprobar(x))` | sí |
| 32 | Juan es alto y inteligente. | 1 | 1 | `Alto(juan) ∧ Inteligente(juan)` | sí |
| 33 | María no ve a nadie. | 1 | 1 | `¬∃x Ver2(maria, x)` | sí |
| 34 | Si algún estudiante lee, Juan aprueba. | 1 | 1 | `∃x (Estudiante(x) ∧ Leer(x)) → Aprobar(juan)` | sí |
| 35 | Juan lea. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 36 | Juan lee y escribe. | 1 | 1 | `Leer(juan) ∧ Escribir(juan)` | sí |
| 37 | Juan ama al estudiante. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 38 | Juan lee y Ana lee y Pedro lee y María lee y Juan estudia. | 14 | 14 | `Leer(juan) ∧ Leer(ana) ∧ Leer(pedro) ∧ Leer(maria) ∧ Estudiar(juan)` | sí |
| 39 | Todo estudiante que conoce a algún profesor que ama a toda persona inteligente que lee un libro aprueba. | 1 | 1 | `∀x (Estudiante(x) ∧ ∃y (Profesor(y) ∧ ∀z (Persona(z) ∧ Inteligente(z) ∧ ∃u (Libro(u) ∧ Leer2(z, u)) → Amar2(y, z)) ∧ Conocer2(x, y)) → Aprobar(x))` | sí |
| 40 | Juan o María lee. | 1 | 1 | `Leer(juan) ∨ Leer(maria)` | sí |
| 41 | Juan o María leen. | 1 | 1 | `Leer(juan) ∨ Leer(maria)` | sí |
| 42 | Juan, Pedro o Ana estudian. | 1 | 1 | `Estudiar(juan) ∨ Estudiar(pedro) ∨ Estudiar(ana)` | sí |
| 43 | Juan o María es alta. | 0 | 0 | rechazada: «alta» no concuerda en género con su sujeto. ¿Quisiste decir «alto»? | sí |
| 44 | Dos estudiantes leen. | 1 | 2 | `∃x ∃y (x ≠ y ∧ Estudiante(x) ∧ Leer(x) ∧ Estudiante(y) ∧ Leer(y))`<br>`∃x ∃y (x ≠ y ∧ Estudiante(x) ∧ Leer(x) ∧ Estudiante(y) ∧ Leer(y)) ∧ ¬∃z ∃u ∃v (z ≠ u ∧ z ≠ v ∧ u ≠ v ∧ Estudiante(z) ∧ Leer(z) ∧ Estudiante(u) ∧ Leer(u) ∧ Estudiante(v) ∧ Leer(v))` | sí |
| 45 | Al menos dos estudiantes leen un libro. | 1 | 2 | `∃x ∃y (x ≠ y ∧ Estudiante(x) ∧ ∃z (Libro(z) ∧ Leer2(x, z)) ∧ Estudiante(y) ∧ ∃u (Libro(u) ∧ Leer2(y, u)))` | sí |
| 46 | Exactamente una persona lee. | 1 | 1 | `∃x (Persona(x) ∧ Leer(x)) ∧ ¬∃y ∃z (y ≠ z ∧ Persona(y) ∧ Leer(y) ∧ Persona(z) ∧ Leer(z))` | sí |
| 47 | A lo sumo tres profesores aprueban. | 1 | 1 | `¬∃x ∃y ∃z ∃u (x ≠ y ∧ x ≠ z ∧ x ≠ u ∧ y ≠ z ∧ y ≠ u ∧ z ≠ u ∧ Profesor(x) ∧ Aprobar(x) ∧ Profesor(y) ∧ Aprobar(y) ∧ Profesor(z) ∧ Aprobar(z) ∧ Profesor(u) ∧ Aprobar(u))` | sí |
| 48 | Hay al menos dos libros. | 1 | 1 | `∃x ∃y (x ≠ y ∧ Libro(x) ∧ Libro(y))` | sí |
| 49 | Juan conoce a exactamente dos profesoras. | 1 | 1 | `∃x ∃y (x ≠ y ∧ Profesora(x) ∧ Conocer2(juan, x) ∧ Profesora(y) ∧ Conocer2(juan, y)) ∧ ¬∃z ∃u ∃v (z ≠ u ∧ z ≠ v ∧ u ≠ v ∧ Profesora(z) ∧ Conocer2(juan, z) ∧ Profesora(u) ∧ Conocer2(juan, u) ∧ Profesora(v) ∧ Conocer2(juan, v))` | sí |
| 50 | Exactamente dos estudiante lee. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |
| 51 | Al menos un estudiantes leen. | 0 | 0 | rechazada: Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal | sí |

## Frases con más de una lectura

**Todos los estudiantes leen un libro.**

- `∀x (Estudiante(x) → ∃y (Libro(y) ∧ Leer2(x, y)))` — Cada miembro puede tener un objeto distinto
- `∃y (Libro(y) ∧ ∀x (Estudiante(x) → Leer2(x, y)))` — Un mismo objeto sirve para todos

**Si Juan lee, entonces María estudia y Pedro estudia.**

- `Leer(juan) → Estudiar(maria) ∧ Estudiar(pedro)` — Lectura de la gramática controlada
- `(Leer(juan) → Estudiar(maria)) ∧ Estudiar(pedro)` — Lectura de la gramática controlada

**Juan lee y María estudia o Pedro estudia.**

- `Leer(juan) ∧ (Estudiar(maria) ∨ Estudiar(pedro))` — Lectura de la gramática controlada
- `Leer(juan) ∧ Estudiar(maria) ∨ Estudiar(pedro)` — Lectura de la gramática controlada

**Juan es joven.**

- `Joven_sust(juan)` — Lectura de la gramática controlada
- `Joven_adj(juan)` — Lectura de la gramática controlada

**Todos los estudiantes no leen.**

- `∀x (Estudiante(x) → ¬Leer(x))` — Ninguno del grupo cumple el predicado
- `¬∀x (Estudiante(x) → Leer(x))` — No todos los miembros del grupo lo cumplen

**Dos estudiantes leen.**

- `∃x ∃y (x ≠ y ∧ Estudiante(x) ∧ Leer(x) ∧ Estudiante(y) ∧ Leer(y))` — Al menos esa cantidad
- `∃x ∃y (x ≠ y ∧ Estudiante(x) ∧ Leer(x) ∧ Estudiante(y) ∧ Leer(y)) ∧ ¬∃z ∃u ∃v (z ≠ u ∧ z ≠ v ∧ u ≠ v ∧ Estudiante(z) ∧ Leer(z) ∧ Estudiante(u) ∧ Leer(u) ∧ Estudiante(v) ∧ Leer(v))` — Exactamente esa cantidad

## Cómo repetir la comprobación

```bash
PYTHONPATH=src python3 scripts/report_spanish.py --check
PYTHONPATH=src:tests python3 -m unittest tests.test_spanish_full
```

# Fixtures y criterios de aceptación

> Estado: borrador de Fase 0. Los fixtures viven en `tests/proof_corpus.py` (secuentes) y `docs/specs/espanol/casos_borde.txt` (español). Comando: `PYTHONPATH=src:tests python3 -m unittest discover -s tests` (137 pruebas).

## 1. Qué cuenta como «aceptado»

| Tipo de fixture | Criterio de aceptación |
|---|---|
| **Secuente válido** (`VALID`, 88) | El buscador devuelve `proved`; el checker acepta el certificado; el JSON se reconstruye y se vuelve a aceptar; **cada paso** es válido (`ctx ⊨ φ`) en todos los modelos pequeños; la conclusión se sigue de las premisas en modelos de 1 a 3 elementos |
| **Secuente no válido** (`INVALID`, 22) | El buscador devuelve `unknown` (nunca `proved`) y **existe** un contramodelo de ≤ 3 elementos que la suite encuentra por fuerza bruta |
| **Proposicional** (cualquier fórmula) | `decide` siempre da `proved` o `counterexample`, jamás `unknown`; el oráculo de tabla de verdad y el resultado coinciden |
| **Ejercicios de clase** (`CLASS_*`) | Los dos caminos (buscador y Kalmár) producen certificados aceptados; la convención de Kalmár de `kalmar_sequent` coincide con la de clase |
| **Certificado inválido** | `verify` lanza `ProofError` con el **código esperado** y el paso culpable |
| **Entrada mal formada** | `invalid_input` con `stage`, `code` y `span` correctos |

Un fixture que falle **bloquea** la fase. Cambiar el resultado esperado de un fixture es un cambio de semántica y necesita aprobación humana.

## 2. Categorías de secuentes válidos

| Grupo | Ejemplos | Cant. |
|---|---|---|
| Proposicional | modus ponens/tollens, silogismos, De Morgan, distributiva, Peirce, tercio excluido, explosión | 28 |
| Cuantificadores | Barbara, conmutación `∀∀`/`∃∃`, `∃∀ → ∀∃`, `¬∀ ↔ ∃¬`, distribución, `∃x(D(x)→∀yD(y))` (bebedor) | 37 |
| **Bordes de cuantificadores** | cuantificador vacuo (`A ⊢ ∀x A`), `∀x P(x) ⊢ ∃x P(x)` (dominio no vacío), sombreado (`∀x(P(x) ∧ ∃x Q(x))`), alfa-renombrado, funciones anidadas `P(f(f(a)))` | 14 |
| Igualdad | reflexividad, simetría, transitividad, Leibniz, congruencia, `∃x x = a` | 9 |

## 3. Casos no válidos y qué protegen

| Secuente | Error que se quiere evitar |
|---|---|
| `∀x(P→Q) ⊬ ∀x(Q→P)` | Aceptar la conversa |
| `∀x∃y R ⊬ ∃y∀x R` | Confundir el orden de cuantificadores |
| `∀x∃y R(x,y) ⊬ ∃y R(y,y)` | **Captura de variable** al instanciar |
| `P(y) ⊬ ∀x P(x)` | Generalizar sobre una variable libre de una hipótesis (`∀I`) |
| `∃x P(x) ⊬ P(y)`; `∃x P(x), Q(y) ⊬ ∃x(P(x)∧Q(x))` | Variable propia mal usada (`∃E`) |
| `P(a) ⊬ ∀x P(x)`; `∃x P(x) ⊬ P(a)` | Generalizar o instanciar una constante |
| `⊬ ∃x∃y x ≠ y`; `⊬ ∀x∀y x = y` | Suponer cardinalidad del dominio |
| `A → B ⊬ B → A`, `A ∨ B ⊬ A` | Falacias proposicionales |

Las condiciones laterales de `∀I`, `∃E` y la captura tienen además **pruebas negativas directas** sobre certificados forjados (`tests/test_proof_checker.py`), porque son la fuente típica de errores.

## 4. Fixtures de clase (fuente: cerebro, jul–ago 2026)

Salen de las conversaciones de repaso de deducción natural. Se leen con `propositional=True` porque en clase las letras son minúsculas.

| id | Contenido |
|---|---|
| `clase-contrapositiva` | `p → q ⊢ ¬q → ¬p` |
| `clase-silogismo-disyuntivo-casos` | `p ∨ q, p → r, q → r ⊢ r` |
| `clase-conjuncion-doble-elim` | `p ∧ q ⊢ q ∧ p` |
| `kalmar-1` … `kalmar-5` | Lema de Kalmár: literales de la valuación ⊢ `φ` si vale, `¬φ` si no. `p→q` (V,V); `p∨q` (F,F); `(p∧q)→r` (V,V,F); `p→(q∨r)` (V,F,F); `(p→q)∨¬r` (V,F,V) |

**Pendiente (equipo):** agregar los ejercicios de clase restantes (el PDF de repaso, la «Actividad en clase 6» sobre lenguaje de primer orden y árboles). Formato en §6.

## 5. Pruebas de propiedades (generadores propios, semilla fija)

| Propiedad | Muestras |
|---|---|
| `parse(print(f)) == f`, Unicode y ASCII | 2000 fórmulas |
| Sustitución: variables libres, invarianza alfa | 700 |
| Evaluador contra implementación independiente | 2300 |
| Fórmula ↔ JSON ↔ fórmula | 500 |
| Buscador contra tabla de verdad (proposicional) | 600 + estrés de 4000 fuera de la suite |
| Lema de Kalmár a través del buscador | 400 fórmulas × 2 valuaciones |
| Kalmár produce certificado para toda consecuencia tautológica | 500 |
| **Fuzz del checker:** todo certificado alterado que se acepte debe ser semánticamente correcto | > 1000 rechazos, 0 aceptaciones incorrectas |
| Leyes de cuantificadores en **todos** los modelos de tamaño 1–3 | 10 válidas, 6 con contramodelo |

## 6. Cómo agregar un fixture

1. **Secuente de clase o de práctica:** agregar una tupla `(premisas, conclusión, constantes)` a `VALID` o `INVALID` en `tests/proof_corpus.py`, o `(id, premisas, conclusión)` a `CLASS_SEQUENTS`.
2. Si no estás seguro de si es válido: ponlo en `INVALID` primero; si el buscador lo prueba, la suite falla y se revisa a mano. Si el oráculo de modelos no encuentra contramodelo, se mueve a revisión (puede ser válido y difícil).
3. **Frase en español:** una línea `<árboles esperados>| frase` en `casos_borde.txt` (`0` = rechazo).
4. Correr la suite completa. Un fixture nuevo que falle se discute antes de «arreglar» el código.

## 7. Qué no cubren estos fixtures

- La validez universal de las leyes: la fuerza bruta cubre dominios de 1 a 3 elementos, no prueba nada en general. La garantía viene del cálculo y del checker.
- Fórmulas de primer orden más difíciles que las del corpus: el buscador es incompleto, y el corpus lo escribió un solo autor.
- La interfaz, la voz y el 3D (Fases 6–7).

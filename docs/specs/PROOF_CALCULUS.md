# Cálculo de pruebas: deducción natural clásica

> Estado: **borrador para revisión** (Fase 0/3). Lo implementa el checker `src/batz/proof/checker.py`, que sigue esta tabla regla por regla. El buscador (`search.py`) no puede importar el checker ni al revés.

## 1. Forma de los juicios

Un juicio es `Γ ⊢ φ`: `Γ` es el **conjunto de hipótesis abiertas** (fórmulas sin descargar) de las que depende `φ`. Es la presentación de Prawitz con las hipótesis abiertas explícitas, de modo que cada paso es verificable por sí solo.

- Las fórmulas se comparan **salvo alfa-equivalencia** (`alpha_equiv`). Un conjunto de fórmulas se entiende igual: dos fórmulas alfa-equivalentes cuentan como la misma.
- `Γ \ {A}` quita de `Γ` toda fórmula alfa-equivalente a `A`. Si `A ∉ Γ`, no pasa nada: la **descarga vacua** es válida.
- `ψ[x:=t]` es la sustitución que evita captura (`substitute`).
- El checker **recalcula** el contexto de cada paso; el contexto declarado debe coincidir, o se rechaza.

## 2. Reglas

`Γᵢ` es el contexto del paso referenciado `i`. Un paso nuevo solo puede referenciar pasos anteriores.

| Regla (id) | Premisas | Conclusión y contexto |
|---|---|---|
| Hipótesis (`assume`) | — | `{A} ⊢ A` |
| ∧I (`and_i`) | `Γ₁⊢A`, `Γ₂⊢B` | `Γ₁∪Γ₂ ⊢ A∧B` |
| ∧E (`and_e1`, `and_e2`) | `Γ⊢A∧B` | `Γ ⊢ A` / `Γ ⊢ B` |
| ∨I (`or_i1`, `or_i2`) | `Γ⊢A` / `Γ⊢B` | `Γ ⊢ A∨B` (con `B` / `A` cualquiera) |
| ∨E (`or_e`) | `Γ₁⊢A∨B`, `Γ₂⊢C`, `Γ₃⊢C` | `Γ₁ ∪ (Γ₂\{A}) ∪ (Γ₃\{B}) ⊢ C` |
| →I (`imp_i`) | `Γ⊢B` | `Γ\{A} ⊢ A→B` |
| →E (`imp_e`) | `Γ₁⊢A→B`, `Γ₂⊢A` | `Γ₁∪Γ₂ ⊢ B` |
| ¬I (`not_i`) | `Γ⊢⊥` | `Γ\{A} ⊢ ¬A` |
| ¬E (`not_e`) | `Γ₁⊢A`, `Γ₂⊢¬A` | `Γ₁∪Γ₂ ⊢ ⊥` |
| ⊥E (`bot_e`) | `Γ⊢⊥` | `Γ ⊢ C` (cualquier `C`) |
| RAA (`raa`) | `Γ⊢⊥` | `Γ\{¬A} ⊢ A` |
| ↔I (`iff_i`) | `Γ₁⊢A→B`, `Γ₂⊢B→A` | `Γ₁∪Γ₂ ⊢ A↔B` |
| ↔E (`iff_e1`, `iff_e2`) | `Γ₁⊢A↔B`, `Γ₂⊢A` / `Γ₂⊢B` | `Γ₁∪Γ₂ ⊢ B` / `Γ₁∪Γ₂ ⊢ A` |
| ∀I (`all_i`) | `Γ⊢ψ[x:=y]` | `Γ ⊢ ∀xψ` |
| ∀E (`all_e`) | `Γ⊢∀xψ` | `Γ ⊢ ψ[x:=t]` |
| ∃I (`ex_i`) | `Γ⊢ψ[x:=t]` | `Γ ⊢ ∃xψ` |
| ∃E (`ex_e`) | `Γ₁⊢∃xψ`, `Γ₂⊢C` | `Γ₁ ∪ (Γ₂\{ψ[x:=y]}) ⊢ C` |
| =I (`eq_i`) | — | `∅ ⊢ t = t` |
| =E (`eq_e`) | `Γ₁⊢s=t`, `Γ₂⊢φ[x:=s]` | `Γ₁∪Γ₂ ⊢ φ[x:=t]` |

La fórmula declarada del paso debe ser **alfa-equivalente** a la conclusión de la tabla. Los parámetros `A`, `B`, `C`, `ψ`, `x` se **leen de la fórmula declarada** o de las premisas, nunca de etiquetas del buscador.

### Parámetros

| Regla | Parámetro | Significado |
|---|---|---|
| `all_i` | `var = y` | variable propia (eigenvariable) |
| `ex_e` | `var = y` | variable propia |
| `all_e`, `ex_i` | `term = t` | término instanciado |
| `eq_i` | `term = t` | término de `t = t` |
| `eq_e` | `var = x`, `template = φ` | `φ` es el contexto donde se reemplaza `x` |

### Condiciones laterales

- **∀I:** `y` no es libre en ninguna fórmula de `Γ` (el contexto de la premisa), y `y` no es libre en `∀xψ`.
- **∃E:** `y` no es libre en `Γ₁`, ni en `Γ₂\{ψ[x:=y]}`, ni en `C`, ni en `∃xψ`.
- **∀E / ∃I / =E:** la sustitución evita la captura por renombrado de ligadas. Para ∃I, ∀E y =E, el término puede tener cualquier variable libre.
- **Final:** el último paso tiene la conclusión del certificado, y su contexto está incluido en las premisas del certificado (salvo alfa-equivalencia). Solo las premisas pueden quedar abiertas.
- **Estructura:** los ids son `1..n` consecutivos y toda referencia apunta a un id menor.

## 3. Por qué es correcto (corrección del cálculo)

Se prueba que cada regla preserva `Γ ⊨ φ`: *toda estructura y asignación que satisface `Γ` satisface `φ`*. Por inducción sobre los pasos, la conclusión final cumple `premisas ⊨ conclusión`.

- **Propositivas:** cada regla es la lectura semántica del conectivo (§3 de `SEMANTICS.md`). En las que descargan (`→I`, `¬I`, `RAA`, `∨E`) se razona por casos sobre si la hipótesis descargada es verdadera en la estructura. `⊥` es falsa siempre, así que `Γ⊨⊥` implica que `Γ` es insatisfacible y de ahí todo se sigue (`⊥E`, `¬I`, `RAA`). `RAA` es donde entra la lógica clásica (bivalencia).
- **∀E:** si `∀xψ` vale con `s`, vale `ψ` con `s[x↦⟦t⟧ₛ]`, y el lema de sustitución da `ψ[x:=t]`. **∃I** es el recíproco.
- **∀I:** si `Γ ⊨ ψ[x:=y]` con `y` no libre en `Γ`, cambiar el valor de `y` no altera si `Γ` se satisface. Entonces `Γ ⊨ ψ[x:=y]` vale para todo valor de `y` y, por lo tanto, para todo `d∈D`; eso es `∀xψ`. La condición «`y` no libre en `∀xψ`» evita que `y` sea una variable libre de la conclusión.
- **∃E:** de `∃xψ` hay un `d` que hace verdadera `ψ`; con `y` no libre en `Γ₂\{…}`, ni en `C`, el valor de `C` no depende de `y`, así que se concluye `C` con ese `d`.
- **=I / =E:** la igualdad es identidad en `D`; =E es el principio de sustitución de iguales (lema de sustitución semántico).
- **Las condiciones laterales son lo único que impide** derivaciones inválidas como `P(y) ⊢ ∀xP(x)`, `∃xP(x) ⊢ P(y)` o `∃xR(x,y) ⊢ ∃zR(z,z)`. Cada una tiene su prueba negativa en la suite.

Además de este argumento, la suite comprueba la corrección por **fuerza bruta**: cada paso de cada certificado es válido (`Γ ⊨ φ`) en modelos pequeños (dominios de 1 a 3 elementos). Esto detecta errores de implementación, pero **no sustituye** al argumento: un modelo pequeño no prueba validez universal. Además, un fuzz de mutaciones exige que todo certificado alterado que el checker acepte sea semánticamente correcto.

## 4. Certificado

Contrato (borrador; el definitivo irá en `JSON_CONTRACTS.md`):

```json
{"schema_version": "1",
 "constants": ["a"],
 "premises": ["∀x (P(x) → Q(x))", "P(a)"],
 "conclusion": "Q(a)",
 "steps": [
   {"id": 1, "formula": "∀x (P(x) → Q(x))", "context": ["∀x (P(x) → Q(x))"], "rule": "assume", "refs": [], "params": {}},
   {"id": 2, "formula": "P(a) → Q(a)", "context": ["∀x (P(x) → Q(x))"], "rule": "all_e", "refs": [1], "params": {"term": "a"}},
   {"id": 3, "formula": "P(a)", "context": ["P(a)"], "rule": "assume", "refs": [], "params": {}},
   {"id": 4, "formula": "Q(a)", "context": ["∀x (P(x) → Q(x))", "P(a)"], "rule": "imp_e", "refs": [2, 3], "params": {}}
 ]}
```

`constants` lista los nombres que se leen como constantes al reconstruir las fórmulas (regla D-2).

## 5. Resultados del buscador

| Estado | Significado |
|---|---|
| `proved` | El buscador construyó un certificado **y el checker lo aceptó** |
| `inconsistent` | Se probó `premisas ⊢ B ∧ ¬B` (certificado aceptado por el checker) |
| `unknown` | Se agotó la profundidad, los nodos o el tiempo. **No** significa que sea falso ni inválido |
| `invalid_input` | Error léxico, sintáctico o semántico en la entrada |

El buscador es **incompleto**: la validez de FOL es indecidible (semidecidible). `unknown` nunca se interpreta como `falso`. Para refutar existe el contramodelo (Fase 4).

## 6. Estrategia del buscador (resumen)

Búsqueda dirigida por la meta, con profundización iterativa sobre las decisiones no invertibles:
1. **Reglas invertibles** (se aplican sin retroceso): ∧I, →I, ¬I, ↔I, ∀I con variable fresca, ∧E, ↔E, →E cuando ya está el antecedente, ∨E y ∃E (una sola vez por hipótesis), detección de contradicción `A`/`¬A` y de `⊥`.
2. **Reglas con elección** (cuestan profundidad): ∨I, ∃I con testigo, ∀E con términos candidatos, →E probando el antecedente, ¬E probando la negada, RAA, y reescritura por igualdad.
3. Límites configurables de profundidad, nodos y tiempo.

Nada de esto afecta la corrección: lo que el buscador devuelve se verifica de nuevo, paso a paso, por el checker.

## Presentación en notación de Fitch (2026-11-13)

El certificado usa contextos explícitos (`Γ ⊢ φ` en cada paso); la interfaz lo muestra en notación de Fitch (`src/batz/proof/fitch.py`). Solo cambia la presentación:

- Las premisas van primero, una por línea, separadas del resto por una raya.
- Cada hipótesis que una regla descarga abre una caja: →I y ¬I suponen la hipótesis, RAA supone la negación de la conclusión, ∨E abre dos cajas (una por disyunto) y ∃E una con el testigo. ∀I abre una caja sin hipótesis, marcada con su variable nueva; ∃E marca la suya junto al testigo.
- Una línea cita líneas visibles (de su caja o de una que la contiene) y las cajas cerradas como rangos `i–j`.
- Los pasos que no dependen de lo que supone una caja se escriben antes de abrirla, para que sigan visibles después de cerrarla; lo que menciona la variable nueva se queda dentro.
- Si la conclusión de una caja ya estaba escrita afuera, se repite dentro como «Reiteración».

`check_layout` comprueba la fidelidad: cada línea con regla coincide con su paso del certificado (misma regla, misma fórmula y mismas fórmulas citadas, en orden); cada caja empieza con lo que su regla descarga y termina en la premisa correspondiente; ningún paso del certificado queda sin línea. Se aplica a todo el corpus de pruebas y a certificados de Kalmár (`tests/test_fitch.py`).

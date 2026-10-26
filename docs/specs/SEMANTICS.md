# Semántica de LOGOS (lógica de primer orden clásica)

> Estado: **borrador para revisión** (Fase 0). Implementada en `src/logos/model.py` y `src/logos/semantics.py`. La sintaxis está en `FORMAL_LANGUAGE.md`.

## 1. Estructuras

Una **estructura finita** `𝓜` sobre una firma consta de:

| Componente | Definición |
|---|---|
| Dominio `D` | Conjunto finito **no vacío** de elementos (enteros o cadenas, distintos entre sí) |
| Constantes | Cada constante `c` tiene `c^𝓜 ∈ D` |
| Funciones | Cada `f` de aridad `n ≥ 1` tiene una **tabla total** `f^𝓜 : Dⁿ → D` |
| Predicados | Cada `P` de aridad `n ≥ 0` tiene una extensión `P^𝓜 ⊆ Dⁿ`. Aridad 0: `P^𝓜 = {()}` (verdadero) o `∅` (falso) |

Reglas de validez, verificadas al construir el modelo (un modelo inválido no existe):
- `D` no vacío, sin elementos repetidos. Elementos: `int` o `str` (no `bool`).
- Las tablas de funciones son totales: exactamente `|D|ⁿ` entradas, con argumentos y valores en `D`.
- Las tuplas de predicados están en `Dⁿ`.
- Un nombre no puede ser a la vez constante y función.

Un **modelo es una estructura finita**. Un modelo debe interpretar **todo** símbolo de la fórmula: no hay valor por omisión. Un símbolo sin interpretación, o con otra aridad, es un error y no "falso".

## 2. Asignaciones

Una asignación `s` va de variables a `D`. Notación: `s[x↦d]` es `s` con `x` reasignada a `d`.

- Evaluar una fórmula **abierta** exige una asignación explícita de todas sus variables libres. Sin ella es error (`unassigned_variable`); no se supone ningún valor ni ningún cuantificador implícito.
- Una **sentencia** (fórmula cerrada) no necesita asignación.
- Todo valor de la asignación debe estar en `D`.

## 3. Evaluación

**Términos** (`⟦t⟧ₛ ∈ D`):
- `⟦x⟧ₛ = s(x)`
- `⟦c⟧ₛ = c^𝓜`
- `⟦f(t₁,…,tₙ)⟧ₛ = f^𝓜(⟦t₁⟧ₛ,…,⟦tₙ⟧ₛ)`

**Fórmulas** (`𝓜, s ⊨ φ`):

| Fórmula | Es verdadera cuando |
|---|---|
| `⊥` | **nunca** |
| `P(t₁,…,tₙ)` | `(⟦t₁⟧ₛ,…,⟦tₙ⟧ₛ) ∈ P^𝓜` |
| `t₁ = t₂` | `⟦t₁⟧ₛ` y `⟦t₂⟧ₛ` son **el mismo elemento** de `D` (identidad) |
| `¬φ` | no `𝓜, s ⊨ φ` |
| `φ ∧ ψ` | ambas |
| `φ ∨ ψ` | al menos una (disyunción **inclusiva**) |
| `φ → ψ` | no `φ`, o `ψ` (implicación **material**) |
| `φ ↔ ψ` | `φ` y `ψ` tienen el mismo valor |
| `∀x φ` | `𝓜, s[x↦d] ⊨ φ` **para todo** `d ∈ D` |
| `∃x φ` | `𝓜, s[x↦d] ⊨ φ` **para algún** `d ∈ D` |

Consecuencias que se prueban en la suite:
- **Sombreado:** en `∀x (P(x) ∧ ∃x Q(x))` la `x` de `Q` es la del `∃` interno.
- **Dominio no vacío:** `∀x P(x) → ∃x P(x)` es verdadera en todo modelo.
- **Cuantificador sobre dominio de un elemento:** `∀x∀y x = y` es verdadera si y solo si `|D| = 1`.
- **Orden de cuantificadores:** `∃y∀x R(x,y)` implica `∀x∃y R(x,y)`, pero no al revés.
- `∀x(P(x)→Q(x))` **no** implica `∀x(Q(x)→P(x))`.

## 4. Verdad, consecuencia y alcance de los resultados

- `𝓜 ⊨ φ` (sentencia) es verdad en **ese** modelo concreto.
- **Consecuencia:** `Γ ⊨ φ` si **todo** modelo (de cualquier tamaño, incluso infinito) que hace verdaderas todas las de `Γ` hace verdadera `φ`.
- Un **contramodelo finito** (`𝓜 ⊨ Γ` y `𝓜 ⊭ φ`) **refuta** `Γ ⊨ φ`. Se comprueba con `is_countermodel`.
- Que **no** se encuentre contramodelo hasta tamaño `N` **no** prueba la consecuencia, y la verdad en un modelo finito **no** es validez universal. Solo una prueba verificada por el checker (Fase 3) establece validez.
- `no demostrable` no significa `falso`: son resultados distintos (`unknown`).

## 5. Trazas semánticas

`evaluate` devuelve un árbol de evaluación completo, sin cortocircuito:
- Átomos: guardan el valor de cada argumento.
- Conectivos: un hijo por subfórmula.
- Cuantificadores: **un hijo por cada elemento** de `D`, en el orden del dominio, con el elemento instanciado.

`check_trace` re-verifica cada nodo localmente (átomos contra el modelo, conectivos y cuantificadores contra sus hijos), así que una traza alterada se rechaza.

## 6. Errores (`invalid_input`, etapa `semantic`)

`invalid_model`, `missing_interpretation`, `model_arity_mismatch`, `unassigned_variable`, `invalid_assignment`, `invalid_trace`. Los de fórmula llevan el `span` del símbolo cuando la fórmula viene de texto.

## 7. Serialización (borrador del contrato `FiniteModel`)

```json
{"schema_version": "1",
 "domain": [1, 2],
 "constants": {"a": 1},
 "functions": {"f": {"arity": 1, "table": [[[1], 2], [[2], 1]]}},
 "predicates": {"R": {"arity": 2, "tuples": [[1, 2], [2, 1]]}, "S": {"arity": 0, "tuples": []}}}
```

Forma canónica: dominio en su orden, símbolos ordenados por nombre, tablas y tuplas ordenadas por posición en el dominio. El contrato definitivo irá en `JSON_CONTRACTS.md`.

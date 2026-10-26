# Lenguaje formal de LOGOS (fragmento para Fase 1)

> Estado: **borrador mínimo para desbloquear la Fase 1**. Cubre solo sintaxis, precedencia y reglas de símbolos. La semántica (`SEMANTICS.md`), el cálculo de pruebas y los contratos JSON siguen pendientes de Fase 0. Las decisiones marcadas **[D]** necesitan aprobación del equipo.

## 1. Alfabeto y tokens

| Token | Unicode | ASCII equivalente |
|---|---|---|
| negación | `¬` | `~` `!` |
| conjunción | `∧` | `&` `/\` |
| disyunción | `∨` | `\|` `\/` |
| implicación | `→` | `->` |
| bicondicional | `↔` | `<->` |
| universal | `∀` | `forall` |
| existencial | `∃` | `exists` |
| falsedad | `⊥` | `_|_` |
| igualdad / desigualdad | `=` `≠` | `=` `!=` |
| puntuación | `( ) ,` | igual |

- Espacios, tabs y saltos de línea separan tokens y se ignoran.
- Identificador: una letra seguida de letras, dígitos, `_` o `'`. `forall` y `exists` son palabras reservadas.
- **Mayúscula inicial** → nombre de predicado. **Minúscula inicial** → nombre de variable, constante o función.
- Los offsets de los errores son índices de caracteres (code points) sobre el texto original.

## 2. Gramática (EBNF)

```ebnf
formula   = iff ;
iff       = implies [ "↔" implies ] ;               (* no asociativo *)
implies   = or [ "→" implies ] ;                    (* asociativo a la derecha *)
or        = and { "∨" and } ;                       (* asociativo a la izquierda *)
and       = unary { "∧" unary } ;                   (* asociativo a la izquierda *)
unary     = "¬" unary
          | ( "∀" | "∃" ) variable unary
          | "⊥"
          | "(" formula ")"
          | atom ;
atom      = PRED [ "(" term { "," term } ")" ]
          | term ( "=" | "≠" ) term ;
term      = IDENT_MIN [ "(" term { "," term } ")" ] ;
variable  = IDENT_MIN ;
```

`⊥` es una fórmula atómica sin variables, falsa en toda estructura (extensión de Fase 3, necesaria para el cálculo de deducción natural). `t1 ≠ t2` es azúcar sintáctico: el AST contiene `Not(Eq(t1, t2))`.

## 3. Precedencia (de mayor a menor)

1. `¬`, `∀x`, `∃x` (prefijos, mismo nivel)
2. `∧`
3. `∨`
4. `→` (derecha)
5. `↔` (no asociativo: `A ↔ B ↔ C` es error, hay que poner paréntesis)

**[D-1]** El cuantificador liga fuerte, como la negación. `∀x P(x) → Q(x)` se lee `(∀x P(x)) → Q(x)`. Para cubrir una conjunción o implicación hay que escribir `∀x (P(x) → Q(x))`. Es la convención de Huth–Ryan; evita que el alcance "se coma" el resto de la fórmula sin que se vea.

## 4. Variables, constantes y funciones

**[D-2]** Un identificador sin paréntesis se resuelve así:
1. Si está ligado por un cuantificador exterior → **variable ligada**.
2. Si está declarado en `constants` al llamar al parser → **constante**.
3. Si no → **variable libre**.

Una constante nunca se puede cuantificar (error semántico). Con paréntesis, un identificador en minúscula es una **función** de aridad ≥ 1. Un predicado sin paréntesis tiene aridad 0 (`P`, lógica proposicional).

## 5. Tabla de símbolos y aridad

- La aridad de cada función y predicado es fija: la declarada en la firma o, si no hay firma, la de su primer uso.
- Un uso con otra aridad es error semántico con la ubicación del símbolo.
- Un mismo nombre no puede ser a la vez variable, constante y función dentro de una fórmula.
- Modo estricto: todo símbolo no variable debe estar declarado en la firma.

## 6. Errores

Todo error es un `invalid_input` con `stage` (`lexical`, `syntactic`, `semantic`), `code` estable, mensaje y `span` `[inicio, fin)`. Se reporta el primer error; el parser no intenta recuperarse.

## 7. Garantías de la Fase 1

- AST inmutable; los constructores rechazan nodos mal formados (no existe un AST inválido).
- `parse(print(φ)) == φ` de forma **estructural** (más fuerte que alfa-equivalencia).
- La sustitución es simultánea y evita captura de variables.
- Ni el lexer ni el parser evalúan ni demuestran nada.

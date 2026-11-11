# LOGOS

Laboratorio de lógica de primer orden. Plan vigente del proyecto MM3032 (evaluador semántico): `docs/plans/PLAN_MM3032.md`. Fases originales en `docs/`.

## Fachada del proyecto MM3032 (M1)

```python
from logos import Signature, evaluar, libres

firma = Signature(constants={"a"}, predicates={"P": 1})
datos = {"domain": [0, 1], "constants": {"a": 0},
         "predicates": {"P": {"arity": 1, "tuples": [[0]]}}}
libres("P(x)", firma)               # ('x',)
resultado = evaluar(firma, datos, "P(x)", {"x": 0})
resultado.status, resultado.value   # ('ok', True)
```

`interpretacion` acepta un objeto o texto JSON con el formato de `FiniteModel`; la fachada exige exactamente los símbolos de la firma, relaciones no vacías y predicados de aridad positiva. Un error devuelve `status='invalid_input'`, diagnósticos en `errors` y ningún valor ni traza.

## Interfaz local (M2–M4)

```bash
python3 evaluador.py
```

Con Docker (no hace falta tener Python instalado):

```bash
docker compose up --build      # detener: docker compose down
```

La interfaz queda en `http://127.0.0.1:8765/`, publicada solo en este equipo. Otro puerto: `LOGOS_PORT=9000 docker compose up --build`.

Abre `http://127.0.0.1:8765/` y pulsa «Cargar ejemplo». La explicación se construye desde una traza verificada; cada nodo tiene un resumen, detalles desplegables y posición en la fórmula. Guía de defensa: `docs/DEFENSA.md`.

La sección «Explorar contramodelos» busca una interpretación estricta que falsifique una **sentencia**. Usa tamaños de dominio 1–3, hasta 5000 candidatos o 2 segundos; si no encuentra uno, devuelve `unknown` y no afirma validez universal. Un hallazgo se puede cargar en las tablas. «Exportar JSON» guarda firma, interpretación y fórmula; «Importar JSON» valida el modelo antes de cargarlo.

## Ensayo final reproducible

```bash
PYTHONPATH=src python3 scripts/validate_demo.py --seed 20261102
```

El reporte y el recorrido para la entrega están en `docs/validation/ENSAYO-MM3032.md`. El ensayo usa solo HTTP local y deja claro cuáles comprobaciones necesitan una persona frente al navegador.

## Español controlado inicial

El panel «Escribir en español controlado» reconoce un fragmento pequeño y muestra todas sus lecturas. Por ejemplo, «Todos los estudiantes leyeron un libro» produce dos alcances de cuantificadores; hay que elegir uno antes de preparar el modelo. Las frases fuera del fragmento se rechazan. La especificación amplia y los casos todavía no cubiertos están en `docs/specs/SPANISH_CONTROLLED.md`.

## Narración y vista 3D opcionales

Al evaluar una fórmula o hallar un contramodelo, «Narración y dominio» recorre los nodos verificados con pausa, avance, retroceso y repetición. La vista 3D usa Three.js incluido localmente; la vista 2D queda disponible si WebGL falla. La voz solo se activa si el usuario la marca y el navegador ofrece una voz local en español. «Prueba verificada» busca un certificado acotado y narra únicamente sus pasos aceptados por el checker. Si la búsqueda agota el límite, responde `unknown` sin narrar una prueba.

La procedencia y la licencia de Three.js están en `docs/THIRD_PARTY.md`.

## Fases 1 a 3: compilador, semántica finita y pruebas (`src/logos/`)

```
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

Solo librería estándar de Python (≥ 3.10). Sintaxis y símbolos: `docs/specs/FORMAL_LANGUAGE.md`. Semántica: `docs/specs/SEMANTICS.md`. Cálculo de pruebas: `docs/specs/PROOF_CALCULUS.md`. Contratos JSON: `docs/specs/JSON_CONTRACTS.md`. Arquitectura, plan y decisiones: `docs/architecture/`, `docs/plans/`, `docs/decisions/`.

```python
from logos import parse, to_string, substitute, Var
f = parse("∀x (P(x) → Q(x))")
to_string(f, ascii=True)   # 'forall x (P(x) -> Q(x))'
from logos import FiniteModel, is_true, evaluate
m = FiniteModel(["a"], predicates={"P": (1, []), "Q": (1, [("a",)])})
is_true(m, parse("∀x (Q(x) → P(x))"))   # False: contramodelo de la conversa
```

```python
from logos.proof import prove_text, format_certificate
r = prove_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", constants=["a"])
r.status                          # 'proved' (solo si el checker aceptó el certificado)
print(format_certificate(r.certificate))
```

El buscador (`proof/search.py`) es incompleto: devuelve `unknown` (nunca "falso") al agotar profundidad, nodos o tiempo. El checker (`proof/checker.py`) no depende del buscador.

Lógica proposicional (siempre hay veredicto: prueba o contramodelo verificado):

```python
from logos import decide, parse
v = decide([parse("p → q", propositional=True)], parse("¬q → ¬p", propositional=True))
v.status, v.method                # ('proved', 'search'); el respaldo completo es 'kalmar'
```

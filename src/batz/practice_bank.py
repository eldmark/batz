"""Contenido fijo del taller: enunciados, pistas y certificados de referencia."""
import hashlib
import json

def step(formula, rule, refs=(), **params):
    return dict(formula=formula, rule=rule, refs=list(refs), params=params)


def exercise(id, title, topic, premises, goal, rules, solution, hints, **extra):
    return dict(id=id, title=title, topic=topic, premises=premises, goal=goal,
                rules=rules, solution=solution, hints=hints, constants=extra.pop("constants", []), **extra)


EXERCISES = [
    exercise("01", "Lo que ya sabes", "Extraer una conjunción", ["P ∧ Q"], "P",
             ["and_e1", "and_e2"], [step("P", "and_e1", [1])],
             ["Una conjunción afirma sus dos partes. Puedes recuperar cualquiera de ellas.",
              "Selecciona ∧E₁ y cita la línea 1.", "Escribe P y comprueba tu paso."],
             intro="Tu primera prueba: recupera una de las dos afirmaciones de la premisa."),
    exercise("02", "Una consecuencia lleva a otra", "Encadenar implicaciones",
             ["P → Q", "Q → R", "P"], "R", ["imp_e"],
             [step("Q", "imp_e", [1, 3]), step("R", "imp_e", [2, 4])],
             ["Primero busca qué puedes obtener a partir de P.",
              "Con P → Q y P obtienes Q. La implicación se cita primero.",
              "Usa el Q obtenido junto con Q → R para llegar a R."],
             intro="No necesitas llegar al objetivo de un solo salto. Construye una línea intermedia."),
    exercise("03", "Juntar las piezas", "Construir una conjunción", ["P", "Q"], "Q ∧ P",
             ["and_i"], [step("Q ∧ P", "and_i", [2, 1])],
             ["El orden de las referencias determina el orden de la conjunción.",
              "Selecciona ∧I. Cita primero Q y después P.", "Escribe Q ∧ P y usa las referencias 2, 1."],
             intro="Las referencias tienen orden: selecciona primero la que irá a la izquierda."),
    exercise("04", "Suponer para demostrar", "Descargar una hipótesis", [], "P → P",
             ["assume", "imp_i"], [step("P", "assume"), step("P → P", "imp_i", [1])],
             ["Una implicación se puede demostrar suponiendo su antecedente.",
              "Añade P con la regla Hipótesis. Esa línea todavía depende de P.",
              "Cita esa línea con →I y escribe P → P. La hipótesis queda descargada."],
             intro="Aquí no hay premisas. Puedes suponer P temporalmente y después descargar esa suposición."),
    exercise("05", "Dos afirmaciones incompatibles", "Reconocer una contradicción",
             ["P", "¬P"], "⊥", ["not_e"], [step("⊥", "not_e", [1, 2])],
             ["Una afirmación y su negación no pueden cumplirse juntas.",
              "La regla ¬E recibe primero P y después ¬P.", "Cita 1, 2 y escribe ⊥."],
             intro="Conoce el símbolo ⊥: registra la contradicción entre una afirmación y su negación."),
    exercise("06", "Abrir una alternativa", "Introducir una disyunción",
             ["P"], "P ∨ Q", ["or_i1"], [step("P ∨ Q", "or_i1", [1])],
             ["Para afirmar P o Q basta con tener una prueba de P.",
              "Selecciona ∨I₁: conserva P a la izquierda y añade Q a la derecha.",
              "Cita la línea 1 y escribe P ∨ Q."],
             intro="No necesitas demostrar ambas alternativas. Una prueba de P basta para introducir P ∨ Q."),
    exercise("07", "Del todo a un caso", "Particularizar un universal",
             ["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", ["all_e", "imp_e"],
             [step("P(a) → Q(a)", "all_e", [1], term="a"), step("Q(a)", "imp_e", [3, 2])],
             ["Lo que se cumple para todo x se cumple en particular para a.",
              "Usa ∀E con la primera premisa e indica a como término.",
              "Obtén P(a) → Q(a). Después aplica →E con esa línea y P(a)."],
             constants=["a"], intro="La constante a designa un individuo. ∀E reemplaza la variable cuantificada por el término elegido."),
    exercise("08", "Un testigo es suficiente", "Introducir un existencial",
             ["P(a) ∧ Q(a)"], "∃x Q(x)", ["and_e2", "ex_i"],
             [step("Q(a)", "and_e2", [1]), step("∃x Q(x)", "ex_i", [2], term="a")],
             ["Necesitas un caso concreto de Q antes de afirmar que existe alguno.",
              "Extrae Q(a) con ∧E₂.", "Usa ∃I sobre Q(a), escribe ∃x Q(x) e indica a como testigo."],
             constants=["a"], intro="Para demostrar una existencia basta presentar un testigo y una prueba de que cumple la propiedad."),
    exercise("09", "Cambiar sin cambiar", "Sustituir iguales", ["a = b", "P(a)"], "P(b)",
             ["eq_e"], [step("P(b)", "eq_e", [1, 2], var="x", template="P(x)")],
             ["Si a y b son iguales, una propiedad de a también es una propiedad de b.",
              "Usa =E. Cita primero a = b y después P(a).",
              "Escribe P(b). Usa x como variable y P(x) como plantilla: P(a) se transforma en P(b)."],
             constants=["a", "b"], intro="La plantilla señala dónde sustituir: P(x) convierte la igualdad a = b en el paso de P(a) a P(b)."),
    exercise("10", "El punto de partida", "Reflexividad de la igualdad", [], "f(a) = f(a)",
             ["eq_i"], [step("f(a) = f(a)", "eq_i", term="f(a)")],
             ["Todo término es igual a sí mismo, incluso cuando contiene una función.",
              "Selecciona =I. No necesitas citar ninguna línea.", "Escribe f(a) = f(a) e indica f(a) como término."],
             constants=["a"], intro="Cierra la introducción con una prueba sin premisas: la igualdad de un término consigo mismo."),
]


CATEGORIES = [
    dict(id="introduction", title="Introducción", start=1, end=10,
         description="Aprende las herramientas. Pruebas cortas, una idea nueva a la vez."),
    dict(id="challenge", title="Desafío", start=11, end=40,
         description="Encuentra la estrategia. Combina hipótesis, casos, testigos e igualdad."),
    dict(id="legend", title="Modo Leyenda", start=41, end=50,
         description="Construye pruebas profundas. Lógica clásica, testigos anidados e inducción."),
]


class Proof:
    """Referencias calculadas al redactar; no se genera contenido al jugar."""
    def __init__(self, premises):
        self.count = len(premises)
        self.moves = []

    def add(self, formula, rule, *refs, **params):
        self.moves.append(step(formula, rule, refs, **params))
        return self.count + len(self.moves)

    def instance(self, ref, formula, term):
        return self.add(formula, "all_e", ref, term=term)

    def replace(self, equality, source, formula, template):
        return self.add(formula, "eq_e", equality, source, var="w", template=template)


def level(number, title, topic, premises, goal, author, hints, intro, constants=()):
    p = Proof(premises)
    author(p)
    EXERCISES.append(exercise(f"{number:02}", title, topic, premises, goal,
                             list(dict.fromkeys(m["rule"] for m in p.moves)), p.moves,
                             hints, intro=intro, constants=list(constants)))


def _11(p):
    h = p.add("P ∧ Q", "assume")
    a = p.add("P", "and_e1", h)
    b = p.add("Q", "and_e2", h)
    pair = p.add("Q ∧ P", "and_i", b, a)
    p.add("(P ∧ Q) → (Q ∧ P)", "imp_i", pair)


level(11, "Cambiar el orden", "Conmutatividad bajo una hipótesis", [], "(P ∧ Q) → (Q ∧ P)", _11,
      ["Trabaja hacia atrás: para demostrar la implicación, supone su antecedente.",
       "Extrae las dos partes de P ∧ Q y reconstruye Q ∧ P.",
       "Cierra con →I citando la conjunción reconstruida: se descarga P ∧ Q."],
      "Empieza el desafío: combina extracción, construcción y descarga en una sola prueba.")


def _12(p):
    h = p.add("P", "assume")
    q = p.add("Q", "imp_e", 1, h)
    r = p.add("R", "imp_e", 2, q)
    p.add("P → R", "imp_i", r)


level(12, "Construir un puente", "Composición de implicaciones", ["P → Q", "Q → R"], "P → R", _12,
      ["No tienes P como premisa, pero puedes usarlo como hipótesis temporal.",
       "Encadena las dos implicaciones bajo esa hipótesis para obtener R.",
       "Descarga P con →I. Las dos implicaciones originales siguen siendo premisas."],
      "Demuestra una nueva implicación sin afirmar que su antecedente sea verdadero.")


def _13(p):
    nq = p.add("¬Q", "assume")
    a = p.add("P", "assume")
    q = p.add("Q", "imp_e", 1, a)
    bot = p.add("⊥", "not_e", q, nq)
    np = p.add("¬P", "not_i", bot)
    p.add("¬Q → ¬P", "imp_i", np)


level(13, "Mirar al contrario", "Contraposición", ["P → Q"], "¬Q → ¬P", _13,
      ["Hay dos hipótesis que abrir: ¬Q para la implicación y P para demostrar ¬P.",
       "P produce Q; Q y la hipótesis ¬Q producen ⊥.",
       "Usa primero ¬I para descargar P y después →I para descargar ¬Q."],
      "La clave está en descargar las hipótesis en el orden correcto.")


def _14(p):
    a = p.add("P", "assume")
    bot = p.add("⊥", "not_e", a, 2)
    q1 = p.add("Q", "bot_e", bot)
    q2 = p.add("Q", "assume")
    p.add("Q", "or_e", 1, q1, q2)


level(14, "Descartar lo imposible", "Disyunción con una rama contradictoria", ["P ∨ Q", "¬P"], "Q", _14,
      ["No borres P de la disyunción sin justificarlo. Resuelve los dos casos.",
       "Bajo P obtienes ⊥ y luego Q con ⊥E. En el otro caso supones Q.",
       "∨E combina la disyunción y los dos Q, descargando las hipótesis de cada rama."],
      "Una de las alternativas es imposible. Demuestra cómo eso permite conservar la otra.")


def _15(p):
    n = p.add("¬P", "assume")
    bot = p.add("⊥", "not_e", 1, n)
    p.add("¬¬P", "not_i", bot)


level(15, "Negar la negación", "Introducción de doble negación", ["P"], "¬¬P", _15,
      ["Para demostrar ¬¬P, considera temporalmente ¬P.",
       "P y ¬P dan una contradicción.", "¬I descarga ¬P; la conclusión es ¬¬P."],
      "Una negación puede tener otra negación como argumento. Sigue su estructura con cuidado.")


def _16(p):
    n = p.add("¬P", "assume")
    bot = p.add("⊥", "not_e", n, 1)
    p.add("P", "raa", bot)


level(16, "Volver a afirmar", "Reducción al absurdo clásica", ["¬¬P"], "P", _16,
      ["La reducción al absurdo permite demostrar P refutando la hipótesis ¬P.",
       "Cita ¬P primero y ¬¬P después para obtener ⊥ con ¬E.",
       "Usa RAA, cita la contradicción y escribe P. Se descarga ¬P."],
      "Distingue ¬I de RAA: una concluye una negación y la otra descarga la negación de su objetivo.")


def _17(p):
    a = p.add("P", "assume")
    r1 = p.add("R", "imp_e", 2, a)
    b = p.add("Q", "assume")
    r2 = p.add("R", "imp_e", 3, b)
    p.add("R", "or_e", 1, r1, r2)


level(17, "Dos caminos, una conclusión", "Eliminación de la disyunción", ["P ∨ Q", "P → R", "Q → R"], "R", _17,
      ["Aunque no sabes qué alternativa se cumple, las dos pueden llevarte a R.",
       "Supón P y aplica P → R. Por separado, supón Q y aplica Q → R.",
       "Con ∨E cita primero P ∨ Q y después los resultados R de ambas ramas."],
      "Completa una prueba por casos sin convertir ninguna alternativa en una premisa permanente.")


def _18(p):
    h = p.add("P ∧ (Q ∨ R)", "assume")
    a = p.add("P", "and_e1", h)
    dis = p.add("Q ∨ R", "and_e2", h)
    q = p.add("Q", "assume")
    pq = p.add("P ∧ Q", "and_i", a, q)
    left = p.add("(P ∧ Q) ∨ (P ∧ R)", "or_i1", pq)
    r = p.add("R", "assume")
    pr = p.add("P ∧ R", "and_i", a, r)
    right = p.add("(P ∧ Q) ∨ (P ∧ R)", "or_i2", pr)
    both = p.add("(P ∧ Q) ∨ (P ∧ R)", "or_e", dis, left, right)
    p.add("(P ∧ (Q ∨ R)) → ((P ∧ Q) ∨ (P ∧ R))", "imp_i", both)


level(18, "Repartir una certeza", "Distributividad", [], "(P ∧ (Q ∨ R)) → ((P ∧ Q) ∨ (P ∧ R))", _18,
      ["Supón el antecedente. P será un recurso compartido por los dos casos de Q ∨ R.",
       "Bajo Q construye P ∧ Q y añade la alternativa derecha. Bajo R construye P ∧ R y añade la izquierda.",
       "Combina las dos disyunciones con ∨E; después descarga el antecedente con →I."],
      "Una prueba por casos puede reutilizar una afirmación que ambas ramas comparten.")


def _19(p):
    h = p.add("(P ∧ Q) ∨ (P ∧ R)", "assume")
    left = p.add("P ∧ Q", "assume")
    a = p.add("P", "and_e1", left)
    q = p.add("Q", "and_e2", left)
    dis1 = p.add("Q ∨ R", "or_i1", q)
    out1 = p.add("P ∧ (Q ∨ R)", "and_i", a, dis1)
    right = p.add("P ∧ R", "assume")
    b = p.add("P", "and_e1", right)
    r = p.add("R", "and_e2", right)
    dis2 = p.add("Q ∨ R", "or_i2", r)
    out2 = p.add("P ∧ (Q ∨ R)", "and_i", b, dis2)
    out = p.add("P ∧ (Q ∨ R)", "or_e", h, out1, out2)
    p.add("((P ∧ Q) ∨ (P ∧ R)) → (P ∧ (Q ∨ R))", "imp_i", out)


level(19, "Encontrar lo común", "Factorizar mediante casos", [], "((P ∧ Q) ∨ (P ∧ R)) → (P ∧ (Q ∨ R))", _19,
      ["La estructura exterior del antecedente exige separar dos casos, no extraer P directamente.",
       "En cada caso recupera P y construye Q ∨ R. Combínalos con ∧I.",
       "Los dos casos deben terminar exactamente en P ∧ (Q ∨ R). Cierra ∨E y luego →I."],
      "Reconstruye la misma conclusión desde dos hipótesis compuestas diferentes.")


def _20(p):
    h = p.add("(P ∧ Q) → R", "assume")
    a = p.add("P", "assume")
    b = p.add("Q", "assume")
    pair = p.add("P ∧ Q", "and_i", a, b)
    r = p.add("R", "imp_e", h, pair)
    qr = p.add("Q → R", "imp_i", r)
    pr = p.add("P → (Q → R)", "imp_i", qr)
    p.add("((P ∧ Q) → R) → (P → (Q → R))", "imp_i", pr)


level(20, "Una condición a la vez", "Currificación", [], "((P ∧ Q) → R) → (P → (Q → R))", _20,
      ["Abre las tres hipótesis que sugieren las tres implicaciones del objetivo.",
       "Con P y Q construye el antecedente que necesita (P ∧ Q) → R.",
       "Tras obtener R, descarga Q, después P y finalmente (P ∧ Q) → R."],
      "Transforma una condición conjunta en dos condiciones sucesivas, sin perder ninguna dependencia.")


def _21(p):
    h = p.add("P → (Q → R)", "assume")
    pair = p.add("P ∧ Q", "assume")
    a = p.add("P", "and_e1", pair)
    b = p.add("Q", "and_e2", pair)
    qr = p.add("Q → R", "imp_e", h, a)
    r = p.add("R", "imp_e", qr, b)
    out = p.add("(P ∧ Q) → R", "imp_i", r)
    p.add("(P → (Q → R)) → ((P ∧ Q) → R)", "imp_i", out)


level(21, "Reunir las condiciones", "Descurrificación", [], "(P → (Q → R)) → ((P ∧ Q) → R)", _21,
      ["Ahora la hipótesis exterior ofrece una implicación cuyo resultado es otra implicación.",
       "Supón P ∧ Q, extrae ambas partes y aplica →E dos veces.",
       "Primero descarga P ∧ Q; después descarga P → (Q → R)."],
      "La prueba inversa requiere una estrategia distinta: desarmar y aplicar, en lugar de reunir.")


def _22(p):
    a = p.add("P", "assume")
    q = p.add("Q", "iff_e1", 1, a)
    r = p.add("R", "iff_e1", 2, q)
    forward = p.add("P → R", "imp_i", r)
    c = p.add("R", "assume")
    q2 = p.add("Q", "iff_e2", 2, c)
    p2 = p.add("P", "iff_e2", 1, q2)
    backward = p.add("R → P", "imp_i", p2)
    p.add("P ↔ R", "iff_i", forward, backward)


level(22, "Ida y vuelta", "Transitividad de equivalencias", ["P ↔ Q", "Q ↔ R"], "P ↔ R", _22,
      ["Un bicondicional necesita dos implicaciones, una en cada dirección.",
       "Desde P usa ↔E₁ dos veces. Desde R usa ↔E₂ dos veces.",
       "Descarga las hipótesis para obtener P → R y R → P; combínalas con ↔I."],
      "No basta con demostrar una sola dirección. Haz explícito el recorrido de vuelta.")


def _23(p):
    a = p.add("P", "assume")
    dis = p.add("P ∨ Q", "or_i1", a)
    bot = p.add("⊥", "not_e", dis, 1)
    np = p.add("¬P", "not_i", bot)
    b = p.add("Q", "assume")
    dis2 = p.add("P ∨ Q", "or_i2", b)
    bot2 = p.add("⊥", "not_e", dis2, 1)
    nq = p.add("¬Q", "not_i", bot2)
    p.add("¬P ∧ ¬Q", "and_i", np, nq)


level(23, "Ninguna alternativa", "Primera ley de De Morgan", ["¬(P ∨ Q)"], "¬P ∧ ¬Q", _23,
      ["Demuestra por separado cada negación del objetivo.",
       "Suponer P permite introducir P ∨ Q y contradecir la premisa. Haz lo mismo con Q.",
       "Descarga cada suposición con ¬I y reúne ¬P y ¬Q con ∧I."],
      "Descubre por qué negar una disyunción obliga a negar sus dos alternativas.")


def _24(p):
    h = p.add("¬(¬P ∨ ¬Q)", "assume")
    np = p.add("¬P", "assume")
    dis = p.add("¬P ∨ ¬Q", "or_i1", np)
    bot = p.add("⊥", "not_e", dis, h)
    a = p.add("P", "raa", bot)
    nq = p.add("¬Q", "assume")
    dis2 = p.add("¬P ∨ ¬Q", "or_i2", nq)
    bot2 = p.add("⊥", "not_e", dis2, h)
    b = p.add("Q", "raa", bot2)
    pair = p.add("P ∧ Q", "and_i", a, b)
    end = p.add("⊥", "not_e", pair, 1)
    p.add("¬P ∨ ¬Q", "raa", end)


level(24, "Romper la conjunción", "De Morgan por reducción al absurdo", ["¬(P ∧ Q)"], "¬P ∨ ¬Q", _24,
      ["No puedes saber qué parte falla. Usa RAA suponiendo la negación de toda la disyunción objetivo.",
       "Bajo esa hipótesis, refuta ¬P para obtener P; refuta ¬Q para obtener Q.",
       "P ∧ Q contradice la premisa. La última RAA descarga ¬(¬P ∨ ¬Q)."],
      "Una disyunción puede demostrarse indirectamente aunque no puedas elegir de antemano un lado.")


def _25(p):
    a = p.add("P", "assume")
    np = p.add("¬P", "assume")
    bot = p.add("⊥", "not_e", a, np)
    out1 = p.add("Q ∨ R", "bot_e", bot)
    r = p.add("R", "assume")
    out2 = p.add("Q ∨ R", "or_i2", r)
    inner = p.add("Q ∨ R", "or_e", 2, out1, out2)
    q = p.add("Q", "assume")
    out3 = p.add("Q ∨ R", "or_i1", q)
    p.add("Q ∨ R", "or_e", 1, inner, out3)


level(25, "Cruce de alternativas", "Resolución mediante casos anidados", ["P ∨ Q", "¬P ∨ R"], "Q ∨ R", _25,
      ["Separa P y Q. La rama Q es directa; la rama P necesita estudiar la segunda disyunción.",
       "Bajo P, los casos ¬P y R llegan a Q ∨ R por contradicción o por introducción de disyunción.",
       "Cierra primero los casos de ¬P ∨ R; después los de P ∨ Q. Revisa las dependencias de cada resultado."],
      "Tu primera prueba con casos dentro de otros casos. El orden de las descargas es parte del desafío.")


def _26(p):
    both = p.instance(1, "P(u) ∧ Q(u)", "u")
    a = p.add("P(u)", "and_e1", both)
    p.add("∀x P(x)", "all_i", a, var="u")


level(26, "Un caso verdaderamente arbitrario", "Generalización universal", ["∀x (P(x) ∧ Q(x))"], "∀x P(x)", _26,
      ["Elige una variable libre nueva, como u; no una constante concreta.",
       "Particulariza la premisa en u y extrae P(u). No supongas P(u).",
       "Usa ∀I e indica u como variable propia. Ninguna hipótesis abierta depende de u."],
      "La diferencia entre un individuo concreto y uno arbitrario se vuelve decisiva al generalizar.")


def _27(p):
    h = p.add("P(u)", "assume")
    link = p.instance(1, "P(u) → Q(u)", "u")
    q = p.add("Q(u)", "imp_e", link, h)
    exists = p.add("∃x Q(x)", "ex_i", q, term="u")
    p.add("∃x Q(x)", "ex_e", 2, exists, var="u")


level(27, "Un testigo que no puede escapar", "Eliminación del existencial", ["∀x (P(x) → Q(x))", "∃x P(x)"], "∃x Q(x)", _27,
      ["La existencia de P no te da P(a) para una constante elegida. Trabaja bajo P(u), con u nueva.",
       "Obtén Q(u), luego ∃x Q(x) usando u como testigo.",
       "∃E cita la premisa existencial y tu conclusión existencial; indica u para descargar P(u)."],
      "Puedes usar temporalmente un testigo desconocido siempre que su nombre no escape a la conclusión.")


def _28(p):
    h = p.add("P(u) ∧ Q(u)", "assume")
    a = p.add("P(u)", "and_e1", h)
    b = p.add("Q(u)", "and_e2", h)
    ea = p.add("∃x P(x)", "ex_i", a, term="u")
    eb = p.add("∃x Q(x)", "ex_i", b, term="u")
    pair = p.add("(∃x P(x)) ∧ (∃x Q(x))", "and_i", ea, eb)
    p.add("(∃x P(x)) ∧ (∃x Q(x))", "ex_e", 1, pair, var="u")


level(28, "Un origen, dos existencias", "Separar propiedades de un testigo", ["∃x (P(x) ∧ Q(x))"], "(∃x P(x)) ∧ (∃x Q(x))", _28,
      ["Abre la hipótesis P(u) ∧ Q(u) para un testigo nuevo.",
       "Extrae ambas propiedades e introduce sus existenciales por separado.",
       "Construye la conjunción objetivo antes de eliminar el testigo con ∃E."],
      "Un mismo testigo puede justificar dos existencias, pero la conclusión no tiene que nombrarlo.")


def _29(p):
    h = p.add("P(u) ∨ Q(u)", "assume")
    a = p.add("P(u)", "assume")
    ep = p.add("∃x P(x)", "ex_i", a, term="u")
    left = p.add("(∃x P(x)) ∨ (∃x Q(x))", "or_i1", ep)
    b = p.add("Q(u)", "assume")
    eq = p.add("∃x Q(x)", "ex_i", b, term="u")
    right = p.add("(∃x P(x)) ∨ (∃x Q(x))", "or_i2", eq)
    both = p.add("(∃x P(x)) ∨ (∃x Q(x))", "or_e", h, left, right)
    p.add("(∃x P(x)) ∨ (∃x Q(x))", "ex_e", 1, both, var="u")


level(29, "No sabes cuál, pero existe", "Casos dentro de un existencial", ["∃x (P(x) ∨ Q(x))"], "(∃x P(x)) ∨ (∃x Q(x))", _29,
      ["Primero introduce un testigo nuevo de la disyunción; después separa sus dos casos.",
       "Cada rama debe producir la disyunción completa de existenciales, no solo su propio existencial.",
       "Cierra ∨E antes de ∃E. Así descargas primero las alternativas y después el testigo."],
      "Combina dos tipos de alcance: las ramas de una disyunción y el nombre temporal de un testigo.")


def _30(p):
    e = p.add("∃x P(x)", "assume")
    h = p.add("P(u)", "assume")
    n = p.instance(1, "¬P(u)", "u")
    bot = p.add("⊥", "not_e", h, n)
    closed = p.add("⊥", "ex_e", e, bot, var="u")
    p.add("¬∃x P(x)", "not_i", closed)


level(30, "No queda ningún testigo", "Negar una existencia", ["∀x ¬P(x)"], "¬∃x P(x)", _30,
      ["Supón que sí existe un P y estudia un testigo nuevo u.",
       "La premisa universal da ¬P(u), que contradice P(u).",
       "Elimina u con ∃E sobre ⊥. Solo entonces descarga ∃x P(x) con ¬I."],
      "Una contradicción no contiene al testigo, pero todavía debes justificar la descarga de su hipótesis.")


def _31(p):
    h = p.add("¬∃x ¬P(x)", "assume")
    nu = p.add("¬P(u)", "assume")
    exists = p.add("∃x ¬P(x)", "ex_i", nu, term="u")
    bot = p.add("⊥", "not_e", exists, h)
    a = p.add("P(u)", "raa", bot)
    universal = p.add("∀x P(x)", "all_i", a, var="u")
    final = p.add("⊥", "not_e", universal, 1)
    p.add("∃x ¬P(x)", "raa", final)


level(31, "Encontrar una excepción", "Dualidad clásica de cuantificadores", ["¬∀x P(x)"], "∃x ¬P(x)", _31,
      ["Supón que no existe ninguna excepción y busca una contradicción con ¬∀x P(x).",
       "Para un u arbitrario, suponer ¬P(u) produciría una excepción. Usa RAA para obtener P(u).",
       "Generaliza P(u), contradice la premisa y descarga ¬∃x ¬P(x) con una última RAA."],
      "La ausencia de un universal se convierte en una existencia mediante razonamiento clásico.")


def _32(p):
    outer = p.instance(1, "∀y R(u,y)", "u")
    atom = p.instance(outer, "R(u,v)", "v")
    inner = p.add("∀x R(x,v)", "all_i", atom, var="u")
    p.add("∀y ∀x R(x,y)", "all_i", inner, var="v")


level(32, "Cambiar el orden del todo", "Intercambiar universales", ["∀x ∀y R(x,y)"], "∀y ∀x R(x,y)", _32,
      ["Desciende hasta R(u,v) con dos particularizaciones y dos variables nuevas.",
       "Reconstruye primero ∀x R(x,v), generalizando u.",
       "Generaliza después v para introducir el cuantificador exterior ∀y."],
      "El orden de reconstrucción es el inverso del orden en que aparecen los cuantificadores objetivo.")


def _33(p):
    outer = p.add("∃y R(u,y)", "assume")
    atom = p.add("R(u,v)", "assume")
    inner = p.add("∃x R(x,v)", "ex_i", atom, term="u")
    out = p.add("∃y ∃x R(x,y)", "ex_i", inner, term="v")
    closed = p.add("∃y ∃x R(x,y)", "ex_e", outer, out, var="v")
    p.add("∃y ∃x R(x,y)", "ex_e", 1, closed, var="u")


level(33, "Dos nombres prestados", "Intercambiar existenciales", ["∃x ∃y R(x,y)"], "∃y ∃x R(x,y)", _33,
      ["Usa dos testigos distintos: u para el existencial exterior y v para el interior.",
       "Desde R(u,v) introduce primero ∃x R(x,v), luego el objetivo completo.",
       "Elimina primero v y luego u. Ninguno puede quedar libre en las otras hipótesis al descargarlo."],
      "Dos existencias anidadas requieren dos descargas independientes, no un intercambio de letras.")


def _34(p):
    same = p.add("a = a", "eq_i", term="a")
    p.replace(1, same, "b = a", "w = a")


level(34, "Invertir una igualdad", "Simetría derivada", ["a = b"], "b = a", _34,
      ["La simetría no es un botón especial: puedes construirla con reflexividad y sustitución.",
       "Empieza demostrando a = a con =I.",
       "En =E usa a = b, después a = a, y la plantilla w = a con variable w."],
      "Deriva una propiedad de la igualdad usando únicamente sus reglas básicas.", constants=["a", "b"])


def _35(p):
    same = p.add("f(a) = f(a)", "eq_i", term="f(a)")
    ab = p.replace(1, same, "f(a) = f(b)", "f(a) = f(w)")
    p.replace(2, ab, "f(a) = f(c)", "f(a) = f(w)")


level(35, "Iguales bajo una función", "Congruencia y encadenamiento", ["a = b", "b = c"], "f(a) = f(c)", _35,
      ["Construye una igualdad reflexiva que ya contenga f(a).",
       "La plantilla f(a) = f(w) permite cambiar solo el argumento de la derecha.",
       "Sustituye a por b con la primera premisa y luego b por c con la segunda."],
      "Las plantillas pueden entrar dentro de funciones. Elige con precisión qué ocurrencia cambiar.", constants=["a", "b", "c"])


def _36(p):
    h = p.add("P(u) ∧ ∀y (P(y) → y = u)", "assume")
    unique = p.add("∀y (P(y) → y = u)", "and_e2", h)
    ia = p.instance(unique, "P(a) → a = u", "a")
    au = p.add("a = u", "imp_e", ia, 2)
    ib = p.instance(unique, "P(b) → b = u", "b")
    bu = p.add("b = u", "imp_e", ib, 3)
    refl = p.add("b = b", "eq_i", term="b")
    ub = p.replace(bu, refl, "u = b", "w = b")
    ab = p.replace(ub, au, "a = b", "a = w")
    p.add("a = b", "ex_e", 1, ab, var="u")


level(36, "Solo puede ser uno", "Unicidad, testigos e igualdad", ["∃x (P(x) ∧ ∀y (P(y) → y = x))", "P(a)", "P(b)"], "a = b", _36,
      ["El testigo u del existencial es un individuo con P al que todos los P son iguales.",
       "Obtén a = u y b = u particularizando la propiedad de unicidad.",
       "Invierte b = u mediante reflexividad y sustitución; encadena a = u con u = b y descarga u."],
      "La igualdad final no puede mencionar al testigo temporal que usaste para demostrarla.", constants=["a", "b"])


def _37(p):
    i = p.instance(1, "∀y ∀z ((R(a,y) ∧ R(y,z)) → R(a,z))", "a")
    j = p.instance(i, "∀z ((R(a,b) ∧ R(b,z)) → R(a,z))", "b")
    k = p.instance(j, "(R(a,b) ∧ R(b,c)) → R(a,c)", "c")
    pair = p.add("R(a,b) ∧ R(b,c)", "and_i", 2, 3)
    ac = p.add("R(a,c)", "imp_e", k, pair)
    j2 = p.instance(i, "∀z ((R(a,c) ∧ R(c,z)) → R(a,z))", "c")
    k2 = p.instance(j2, "(R(a,c) ∧ R(c,d)) → R(a,d)", "d")
    pair2 = p.add("R(a,c) ∧ R(c,d)", "and_i", ac, 4)
    p.add("R(a,d)", "imp_e", k2, pair2)


level(37, "Una relación que llega lejos", "Reutilizar una ley universal", ["∀x ∀y ∀z ((R(x,y) ∧ R(y,z)) → R(x,z))", "R(a,b)", "R(b,c)", "R(c,d)"], "R(a,d)", _37,
      ["La transitividad se aplica dos veces. Primero demuestra R(a,c).",
       "Particulariza x=a, y=b, z=c. Después reutiliza la instancia con x=a para y=c, z=d.",
       "Cada aplicación necesita una conjunción de relaciones construida con ∧I antes de →E."],
      "Una ley de tres variables no se aplica de golpe: elige y reutiliza sus instancias.", constants=["a", "b", "c", "d"])


ADD_ZERO = "∀x (suma(x,cero) = x)"
ADD_SUCC = "∀x ∀y (suma(x,s(y)) = s(suma(x,y)))"
LEFT_ZERO = "∀x (suma(cero,x) = x)"
IND_ZERO = "(suma(cero,cero) = cero ∧ ∀x (suma(cero,x) = x → suma(cero,s(x)) = s(x))) → ∀x (suma(cero,x) = x)"


def _38(p):
    base = p.instance(1, "suma(s(cero),cero) = s(cero)", "s(cero)")
    rec = p.instance(2, "∀y (suma(s(cero),s(y)) = s(suma(s(cero),y)))", "s(cero)")
    one = p.instance(rec, "suma(s(cero),s(cero)) = s(suma(s(cero),cero))", "cero")
    p.replace(base, one, "suma(s(cero),s(cero)) = s(s(cero))", "suma(s(cero),s(cero)) = s(w)")


level(38, "Uno más uno", "Aritmética desde sus axiomas", [ADD_ZERO, ADD_SUCC], "suma(s(cero),s(cero)) = s(s(cero))", _38,
      ["cero es 0; s es sucesor; suma es suma. Particulariza el primer axioma con s(cero).",
       "Particulariza el segundo con s(cero) y después con cero.",
       "Sustituye suma(s(cero),cero) por s(cero) dentro del sucesor del resultado."],
      "La prueba aritmética de la primera versión reaparece aquí, después de dominar igualdad y cuantificadores.", constants=["cero"])


def _39(p):
    base = p.instance(1, "suma(s(cero),cero) = s(cero)", "s(cero)")
    rec = p.instance(2, "∀y (suma(s(cero),s(y)) = s(suma(s(cero),y)))", "s(cero)")
    one = p.instance(rec, "suma(s(cero),s(cero)) = s(suma(s(cero),cero))", "cero")
    computed = p.replace(base, one, "suma(s(cero),s(cero)) = s(s(cero))", "suma(s(cero),s(cero)) = s(w)")
    two = p.instance(rec, "suma(s(cero),s(s(cero))) = s(suma(s(cero),s(cero)))", "s(cero)")
    p.replace(computed, two, "suma(s(cero),s(s(cero))) = s(s(s(cero)))", "suma(s(cero),s(s(cero))) = s(w)")


level(39, "Calcular es demostrar", "Recursión y resultados intermedios", [ADD_ZERO, ADD_SUCC], "suma(s(cero),s(s(cero))) = s(s(s(cero)))", _39,
      ["Para demostrar 1 + 2 = 3 necesitarás primero el resultado 1 + 1 = 2.",
       "Conserva la instancia del segundo axioma con x=s(cero). Puedes usarla con y=cero y con y=s(cero).",
       "Reescribe primero suma(s(cero),cero) y luego suma(s(cero),s(cero)), siempre dentro del sucesor."],
      "Reutiliza un pequeño lema aritmético en una segunda aplicación de la recursión.", constants=["cero"])


def prove_left_zero(p, zero=1, succ=2, induction=3):
    base = p.instance(zero, "suma(cero,cero) = cero", "cero")
    hyp = p.add("suma(cero,u) = u", "assume")
    rec = p.instance(succ, "∀y (suma(cero,s(y)) = s(suma(cero,y)))", "cero")
    inst = p.instance(rec, "suma(cero,s(u)) = s(suma(cero,u))", "u")
    changed = p.replace(hyp, inst, "suma(cero,s(u)) = s(u)", "suma(cero,s(u)) = s(w)")
    cond = p.add("suma(cero,u) = u → suma(cero,s(u)) = s(u)", "imp_i", changed)
    universal = p.add("∀x (suma(cero,x) = x → suma(cero,s(x)) = s(x))", "all_i", cond, var="u")
    pair = p.add("suma(cero,cero) = cero ∧ ∀x (suma(cero,x) = x → suma(cero,s(x)) = s(x))", "and_i", base, universal)
    return p.add(LEFT_ZERO, "imp_e", induction, pair)


level(40, "El primer infinito", "Construir una prueba por inducción", [ADD_ZERO, ADD_SUCC, IND_ZERO], LEFT_ZERO, prove_left_zero,
      ["La tercera premisa es la instancia de inducción que necesitas. Debes demostrar su caso base y su paso inductivo.",
       "Para el paso, supone suma(cero,u)=u. La recursión y una sustitución dan suma(cero,s(u))=s(u).",
       "Descarga la hipótesis, generaliza u y une el paso universal con el caso base. Aplica la instancia de inducción con →E."],
      "cero, s y suma representan cero, sucesor y suma. La inducción es una premisa explícita: debes construir sus dos condiciones, no comprobar unos cuantos números.", constants=["cero"])


def _41(p):
    h = p.add("(P → Q) → P", "assume")
    np = p.add("¬P", "assume")
    a = p.add("P", "assume")
    bot = p.add("⊥", "not_e", a, np)
    q = p.add("Q", "bot_e", bot)
    cond = p.add("P → Q", "imp_i", q)
    again = p.add("P", "imp_e", h, cond)
    bot2 = p.add("⊥", "not_e", again, np)
    out = p.add("P", "raa", bot2)
    p.add("((P → Q) → P) → P", "imp_i", out)


level(41, "La vuelta de Peirce", "Lógica clásica con hipótesis anidadas", [], "((P → Q) → P) → P", _41,
      ["La hipótesis exterior pide P → Q. Para construirla, empieza suponiendo que el objetivo P es falso.",
       "Bajo ¬P, una suposición P produce contradicción y por ello Q. Descarga P para obtener P → Q.",
       "La hipótesis exterior vuelve a darte P. Contradice ¬P, descarga esta con RAA y cierra la implicación exterior."],
      "Bienvenido a Modo Leyenda. Una implicación debe construirse dentro de la negación de tu propio objetivo.")


def _42(p):
    h = p.add("¬((P → Q) ∨ (Q → P))", "assume")
    a = p.add("P", "assume")
    qp = p.add("Q → P", "imp_i", a)
    dis = p.add("(P → Q) ∨ (Q → P)", "or_i2", qp)
    bot = p.add("⊥", "not_e", dis, h)
    q = p.add("Q", "bot_e", bot)
    pq = p.add("P → Q", "imp_i", q)
    out = p.add("(P → Q) ∨ (Q → P)", "or_i1", pq)
    bot2 = p.add("⊥", "not_e", out, h)
    p.add("(P → Q) ∨ (Q → P)", "raa", bot2)


level(42, "Una dirección debe ceder", "Disyunción de implicaciones", [], "(P → Q) ∨ (Q → P)", _42,
      ["No puedes escoger de antemano una dirección. Supón la negación de toda la disyunción.",
       "Bajo P puedes introducir Q → P, aunque no uses Q. Esa dirección contradice la hipótesis exterior y te permite obtener Q.",
       "Descarga P para construir P → Q. Introduce ahora la otra alternativa y usa la contradicción para cerrar con RAA."],
      "Explota una descarga vacía legítima: demostrar B permite concluir A → B sin tener que usar A.")


def _43(p):
    h = p.add("¬((∀x P(x)) ∨ Q)", "assume")
    q = p.add("Q", "assume")
    dis = p.add("(∀x P(x)) ∨ Q", "or_i2", q)
    bot = p.add("⊥", "not_e", dis, h)
    nq = p.add("¬Q", "not_i", bot)
    cases = p.instance(1, "P(u) ∨ Q", "u")
    a = p.add("P(u)", "assume")
    b = p.add("Q", "assume")
    bot2 = p.add("⊥", "not_e", b, nq)
    a2 = p.add("P(u)", "bot_e", bot2)
    each = p.add("P(u)", "or_e", cases, a, a2)
    universal = p.add("∀x P(x)", "all_i", each, var="u")
    out = p.add("(∀x P(x)) ∨ Q", "or_i1", universal)
    bot3 = p.add("⊥", "not_e", out, h)
    p.add("(∀x P(x)) ∨ Q", "raa", bot3)


level(43, "Una alternativa que no depende de x", "Cuantificadores, casos y razonamiento clásico", ["∀x (P(x) ∨ Q)"], "(∀x P(x)) ∨ Q", _43,
      ["Q no depende de x. Supón que la disyunción objetivo es falsa y demuestra primero ¬Q.",
       "Para u arbitrario, la premisa da P(u) ∨ Q. La rama Q contradice ¬Q; ambas ramas terminan en P(u).",
       "Generaliza solo después de cerrar los casos. Introduce (∀x P(x)) ∨ Q y termina por RAA."],
      "Mover un cuantificador a través de una disyunción exige aprovechar que la otra alternativa no contiene su variable.")


def _44(p):
    goal = "∃x (P(x) → ∀y P(y))"
    h = p.add(f"¬({goal})", "assume")
    np = p.add("¬P(u)", "assume")
    a = p.add("P(u)", "assume")
    bot = p.add("⊥", "not_e", a, np)
    everything = p.add("∀y P(y)", "bot_e", bot)
    cond = p.add("P(u) → ∀y P(y)", "imp_i", everything)
    exists = p.add(goal, "ex_i", cond, term="u")
    bot2 = p.add("⊥", "not_e", exists, h)
    pu = p.add("P(u)", "raa", bot2)
    allp = p.add("∀y P(y)", "all_i", pu, var="u")
    cond2 = p.add("P(u) → ∀y P(y)", "imp_i", allp)
    exists2 = p.add(goal, "ex_i", cond2, term="u")
    bot3 = p.add("⊥", "not_e", exists2, h)
    p.add(goal, "raa", bot3)


level(44, "El testigo inesperado", "Principio del bebedor en lógica clásica", [], "∃x (P(x) → ∀y P(y))", _44,
      ["El dominio no vacío y la implicación material hacen posible este teorema. Supón que no existe el testigo objetivo.",
       "Bajo ¬P(u), suponer P(u) permite concluir ∀y P(y) por contradicción. Eso construye el testigo prohibido: deduce P(u) por RAA.",
       "Generaliza P(u). Ahora ∀y P(y) permite construir otra vez la implicación y el existencial; contradice la hipótesis exterior."],
      "Un teorema sorprendente sin premisas. Debes coordinar dos reducciones al absurdo y una generalización válida.")


def _45(p):
    h = p.add("f(u) = f(v)", "assume")
    refl = p.add("g(f(u)) = g(f(u))", "eq_i", term="g(f(u))")
    lift = p.replace(h, refl, "g(f(u)) = g(f(v))", "g(f(u)) = g(w)")
    u = p.instance(1, "g(f(u)) = u", "u")
    v = p.instance(1, "g(f(v)) = v", "v")
    left = p.replace(u, lift, "u = g(f(v))", "w = g(f(v))")
    right = p.replace(v, left, "u = v", "u = w")
    cond = p.add("f(u) = f(v) → u = v", "imp_i", right)
    inner = p.add("∀y (f(u) = f(y) → u = y)", "all_i", cond, var="v")
    p.add("∀x ∀y (f(x) = f(y) → x = y)", "all_i", inner, var="u")


level(45, "Deshacer revela el origen", "Una inversa izquierda implica inyectividad", ["∀x (g(f(x)) = x)"], "∀x ∀y (f(x) = f(y) → x = y)", _45,
      ["Toma u y v arbitrarios y supone f(u)=f(v). Necesitas introducir g sin una regla especial de congruencia.",
       "Desde g(f(u))=g(f(u)), sustituye f(u) por f(v) solo a la derecha. Particulariza la premisa en u y en v.",
       "Reescribe ambos lados para obtener u=v. Descarga la igualdad supuesta y generaliza v, después u."],
      "Construye la inyectividad a partir de la capacidad de deshacer f; cada paso de congruencia debe justificarse.")


def _46(p):
    exists = p.instance(1, "∃y ∀z (R(u,z) ↔ z = y)", "u")
    h = p.add("∀z (R(u,z) ↔ z = k)", "assume")
    pair = p.add("R(u,v) ∧ R(u,t)", "assume")
    rv = p.add("R(u,v)", "and_e1", pair)
    rt = p.add("R(u,t)", "and_e2", pair)
    iv = p.instance(h, "R(u,v) ↔ v = k", "v")
    it = p.instance(h, "R(u,t) ↔ t = k", "t")
    vk = p.add("v = k", "iff_e1", iv, rv)
    tk = p.add("t = k", "iff_e1", it, rt)
    same = p.add("t = t", "eq_i", term="t")
    kt = p.replace(tk, same, "k = t", "w = t")
    vt = p.replace(kt, vk, "v = t", "v = w")
    cond = p.add("(R(u,v) ∧ R(u,t)) → v = t", "imp_i", vt)
    inner = p.add("∀z ((R(u,v) ∧ R(u,z)) → v = z)", "all_i", cond, var="t")
    middle = p.add("∀y ∀z ((R(u,y) ∧ R(u,z)) → y = z)", "all_i", inner, var="v")
    closed = p.add("∀y ∀z ((R(u,y) ∧ R(u,z)) → y = z)", "ex_e", exists, middle, var="k")
    p.add("∀x ∀y ∀z ((R(x,y) ∧ R(x,z)) → y = z)", "all_i", closed, var="u")


level(46, "Una relación con un único destino", "Unicidad y tres generalizaciones", ["∀x ∃y ∀z (R(x,z) ↔ z = y)"], "∀x ∀y ∀z ((R(x,y) ∧ R(x,z)) → y = z)", _46,
      ["Fija un origen arbitrario u. El existencial te presta un destino k; su hipótesis es ∀z(R(u,z) ↔ z=k).",
       "Supón dos destinos v y t. Los bicondicionales dan v=k y t=k; deriva v=t mediante igualdad.",
       "Descarga la conjunción, generaliza t y v, elimina k con ∃E y solo al final generaliza u."],
      "Convierte la descripción de un destino único en una ley global de funcionalidad, sin dejar escapar el destino prestado.")


def _47(p):
    outer = p.instance(2, "∃x (g(x) = u)", "u")
    gv = p.add("g(v) = u", "assume")
    inner = p.instance(1, "∃x (f(x) = v)", "v")
    ft = p.add("f(t) = v", "assume")
    same = p.add("g(f(t)) = g(f(t))", "eq_i", term="g(f(t))")
    first = p.replace(ft, same, "g(f(t)) = g(v)", "g(f(t)) = g(w)")
    second = p.replace(gv, first, "g(f(t)) = u", "g(f(t)) = w")
    out = p.add("∃x (g(f(x)) = u)", "ex_i", second, term="t")
    ci = p.add("∃x (g(f(x)) = u)", "ex_e", inner, out, var="t")
    co = p.add("∃x (g(f(x)) = u)", "ex_e", outer, ci, var="v")
    p.add("∀y ∃x (g(f(x)) = y)", "all_i", co, var="u")


level(47, "Llegar desde dos funciones", "Sobreyectividad de una composición", ["∀y ∃x (f(x) = y)", "∀y ∃x (g(x) = y)"], "∀y ∃x (g(f(x)) = y)", _47,
      ["Trabaja hacia atrás desde un destino u: primero busca una preimagen v por g, después una preimagen t de v por f.",
       "Los testigos dan g(v)=u y f(t)=v. Construye g(f(t))=u con reflexividad y dos sustituciones.",
       "Introduce el existencial usando t, elimina t, elimina v y generaliza u. El orden de descargas es esencial."],
      "Elige testigos en el orden inverso al de la composición y prueba que el resultado no depende de sus nombres.")


def _48(p):
    ep = p.add("∃x P(x)", "assume")
    a = p.add("P(u)", "assume")
    inst = p.instance(1, "P(u) ↔ Q(u)", "u")
    q = p.add("Q(u)", "iff_e1", inst, a)
    eq = p.add("∃x Q(x)", "ex_i", q, term="u")
    closed = p.add("∃x Q(x)", "ex_e", ep, eq, var="u")
    forward = p.add("(∃x P(x)) → (∃x Q(x))", "imp_i", closed)
    eq2 = p.add("∃x Q(x)", "assume")
    b = p.add("Q(v)", "assume")
    inst2 = p.instance(1, "P(v) ↔ Q(v)", "v")
    a2 = p.add("P(v)", "iff_e2", inst2, b)
    ep2 = p.add("∃x P(x)", "ex_i", a2, term="v")
    closed2 = p.add("∃x P(x)", "ex_e", eq2, ep2, var="v")
    backward = p.add("(∃x Q(x)) → (∃x P(x))", "imp_i", closed2)
    p.add("(∃x P(x)) ↔ (∃x Q(x))", "iff_i", forward, backward)


level(48, "Equivalentes incluso al existir", "Dos pruebas con testigos independientes", ["∀x (P(x) ↔ Q(x))"], "(∃x P(x)) ↔ (∃x Q(x))", _48,
      ["El objetivo exige dos implicaciones. Cada una necesita su propio razonamiento existencial.",
       "En la primera dirección usa P(u), particulariza el bicondicional, obtén Q(u) y presenta un testigo de Q.",
       "Elimina u antes de cerrar la primera implicación. Repite en sentido contrario con v y ↔E₂; termina con ↔I."],
      "Demuestra una equivalencia completa coordinando dos ámbitos de testigos y dos descargas de implicación.")


MUL_ZERO = "∀x (producto(x,cero) = cero)"
MUL_SUCC = "∀x ∀y (producto(x,s(y)) = suma(producto(x,y),x))"


def _49(p):
    left_zero = prove_left_zero(p)
    zero = p.instance(4, "producto(u,cero) = cero", "u")
    rec = p.instance(5, "∀y (producto(u,s(y)) = suma(producto(u,y),u))", "u")
    one = p.instance(rec, "producto(u,s(cero)) = suma(producto(u,cero),u)", "cero")
    simplified = p.replace(zero, one, "producto(u,s(cero)) = suma(cero,u)", "producto(u,s(cero)) = suma(w,u)")
    identity = p.instance(left_zero, "suma(cero,u) = u", "u")
    final = p.replace(identity, simplified, "producto(u,s(cero)) = u", "producto(u,s(cero)) = w")
    p.add("∀x (producto(x,s(cero)) = x)", "all_i", final, var="u")


level(49, "Un lema que abre otra operación", "Inducción y multiplicación por uno", [ADD_ZERO, ADD_SUCC, IND_ZERO, MUL_ZERO, MUL_SUCC], "∀x (producto(x,s(cero)) = x)", _49,
      ["Primero demuestra ∀x suma(cero,x)=x con la instancia de inducción. Ese lema todavía no es una premisa.",
       "Para u arbitrario, la recursión del producto da producto(u,s(cero))=suma(producto(u,cero),u).",
       "Reescribe producto(u,cero) como cero; usa el lema de suma por la izquierda para llegar a u. Generaliza sin hipótesis pendientes."],
      "Construye un lema por inducción y úsalo para demostrar una propiedad de una operación distinta. producto representa la multiplicación.", constants=["cero"])


LEFT_SUCC = "∀x ∀y (suma(s(x),y) = s(suma(x,y)))"
IND_SUCC = "∀x ((suma(s(x),cero) = s(suma(x,cero)) ∧ ∀y (suma(s(x),y) = s(suma(x,y)) → suma(s(x),s(y)) = s(suma(x,s(y))))) → ∀y (suma(s(x),y) = s(suma(x,y))))"
IND_COMM = "∀x ((suma(x,cero) = suma(cero,x) ∧ ∀y (suma(x,y) = suma(y,x) → suma(x,s(y)) = suma(s(y),x))) → ∀y (suma(x,y) = suma(y,x)))"


def reverse_equality(p, ref, left, right):
    same = p.add(f"{left} = {left}", "eq_i", term=left)
    return p.replace(ref, same, f"{right} = {left}", f"w = {left}")


def prove_left_successor(p):
    # Inducción sobre el segundo argumento, con v como parámetro arbitrario.
    first = p.instance(1, "suma(s(v),cero) = s(v)", "s(v)")
    second = p.instance(1, "suma(v,cero) = v", "v")
    inverse = reverse_equality(p, second, "suma(v,cero)", "v")
    base = p.replace(inverse, first, "suma(s(v),cero) = s(suma(v,cero))", "suma(s(v),cero) = s(w)")
    hyp = p.add("suma(s(v),t) = s(suma(v,t))", "assume")
    rec1 = p.instance(2, "∀y (suma(s(v),s(y)) = s(suma(s(v),y)))", "s(v)")
    rec2 = p.instance(rec1, "suma(s(v),s(t)) = s(suma(s(v),t))", "t")
    use_hyp = p.replace(hyp, rec2, "suma(s(v),s(t)) = s(s(suma(v,t)))", "suma(s(v),s(t)) = s(w)")
    rec3 = p.instance(2, "∀y (suma(v,s(y)) = s(suma(v,y)))", "v")
    rec4 = p.instance(rec3, "suma(v,s(t)) = s(suma(v,t))", "t")
    inverse2 = reverse_equality(p, rec4, "suma(v,s(t))", "s(suma(v,t))")
    end = p.replace(inverse2, use_hyp, "suma(s(v),s(t)) = s(suma(v,s(t)))", "suma(s(v),s(t)) = s(w)")
    cond = p.add("suma(s(v),t) = s(suma(v,t)) → suma(s(v),s(t)) = s(suma(v,s(t)))", "imp_i", end)
    universal = p.add("∀y (suma(s(v),y) = s(suma(v,y)) → suma(s(v),s(y)) = s(suma(v,s(y))))", "all_i", cond, var="t")
    pair = p.add("suma(s(v),cero) = s(suma(v,cero)) ∧ ∀y (suma(s(v),y) = s(suma(v,y)) → suma(s(v),s(y)) = s(suma(v,s(y))))", "and_i", base, universal)
    instance = p.instance(4, "(suma(s(v),cero) = s(suma(v,cero)) ∧ ∀y (suma(s(v),y) = s(suma(v,y)) → suma(s(v),s(y)) = s(suma(v,s(y))))) → ∀y (suma(s(v),y) = s(suma(v,y)))", "v")
    inner = p.add("∀y (suma(s(v),y) = s(suma(v,y)))", "imp_e", instance, pair)
    return p.add(LEFT_SUCC, "all_i", inner, var="v")


def _50(p):
    zero_lemma = prove_left_zero(p)
    succ_lemma = prove_left_successor(p)
    # Tercera inducción: ahora sobre la conmutatividad, con u como parámetro.
    right_zero = p.instance(1, "suma(u,cero) = u", "u")
    left_zero = p.instance(zero_lemma, "suma(cero,u) = u", "u")
    inverse = reverse_equality(p, left_zero, "suma(cero,u)", "u")
    base = p.replace(inverse, right_zero, "suma(u,cero) = suma(cero,u)", "suma(u,cero) = w")
    hyp = p.add("suma(u,t) = suma(t,u)", "assume")
    rec = p.instance(2, "∀y (suma(u,s(y)) = s(suma(u,y)))", "u")
    inst = p.instance(rec, "suma(u,s(t)) = s(suma(u,t))", "t")
    use_hyp = p.replace(hyp, inst, "suma(u,s(t)) = s(suma(t,u))", "suma(u,s(t)) = s(w)")
    succ = p.instance(succ_lemma, "∀y (suma(s(t),y) = s(suma(t,y)))", "t")
    succ_at_u = p.instance(succ, "suma(s(t),u) = s(suma(t,u))", "u")
    inverse2 = reverse_equality(p, succ_at_u, "suma(s(t),u)", "s(suma(t,u))")
    end = p.replace(inverse2, use_hyp, "suma(u,s(t)) = suma(s(t),u)", "suma(u,s(t)) = w")
    cond = p.add("suma(u,t) = suma(t,u) → suma(u,s(t)) = suma(s(t),u)", "imp_i", end)
    universal = p.add("∀y (suma(u,y) = suma(y,u) → suma(u,s(y)) = suma(s(y),u))", "all_i", cond, var="t")
    pair = p.add("suma(u,cero) = suma(cero,u) ∧ ∀y (suma(u,y) = suma(y,u) → suma(u,s(y)) = suma(s(y),u))", "and_i", base, universal)
    instance = p.instance(5, "(suma(u,cero) = suma(cero,u) ∧ ∀y (suma(u,y) = suma(y,u) → suma(u,s(y)) = suma(s(y),u))) → ∀y (suma(u,y) = suma(y,u))", "u")
    inner = p.add("∀y (suma(u,y) = suma(y,u))", "imp_e", instance, pair)
    p.add("∀x ∀y (suma(x,y) = suma(y,x))", "all_i", inner, var="u")


level(50, "El orden deja de importar", "Conmutatividad de la suma: tres inducciones", [ADD_ZERO, ADD_SUCC, IND_ZERO, IND_SUCC, IND_COMM], "∀x ∀y (suma(x,y) = suma(y,x))", _50,
      ["Divide la prueba en tres lemas: cero por la izquierda, sucesor por la izquierda y conmutatividad. Las tres instancias de inducción están dadas; sus condiciones no.",
       "Para el segundo lema fija v e induce en t: prueba suma(s(v),t)=s(suma(v,t)). Necesitarás invertir igualdades para reescribir en la dirección correcta.",
       "Para la última inducción fija u. El caso base usa el primer lema; el paso usa la recursión, la hipótesis suma(u,t)=suma(t,u) y el segundo lema. Descarga, generaliza t, aplica inducción y generaliza u."],
      "La prueba final construye sus propios lemas. Solo tienes los dos axiomas de suma y tres instancias explícitas de inducción: ninguna propiedad de conmutatividad se regala.", constants=["cero"])


# La identidad depende del problema matemático, no de su título ni de sus pistas.
# Permite conservar pruebas compatibles y apartar borradores de versiones previas.
for _ex in EXERCISES:
    _number = int(_ex["id"])
    _ex["category"] = next(c["id"] for c in CATEGORIES if c["start"] <= _number <= c["end"])
    _spec = {k: _ex[k] for k in ("premises", "goal", "constants")}
    _ex["revision"] = hashlib.sha256(json.dumps(_spec, sort_keys=True).encode()).hexdigest()[:12]



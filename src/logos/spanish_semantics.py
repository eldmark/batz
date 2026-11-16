"""Composición determinista de los árboles de español controlado a FOL."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .ast import And, Const, Eq, Exists, Forall, Iff, Implies, Not, Or, Pred, Var
from .spanish_cyk import Tree
from .spanish_tagger import plain
from . import lexicon

# Símbolos de palabras fuera del léxico, propuestos por el etiquetador para la frase en curso:
# {("N" | "Adj" | "V", palabra): predicado}. `spanish.translate_spanish` lo llena y lo vacía.
EXTRA = {}
# Sentido elegido para cada palabra con varios significados en la lectura que se está componiendo.
SENSE = {}


NOUN = {"estudiante": "Estudiante", "libro": "Libro", "profesor": "Profesor",
        "profesora": "Profesora", "persona": "Persona", "gato": "Gato", "joven": "Joven_sust"}
ADJ = {"inteligente": "Inteligente", "alto": "Alto", "alta": "Alto",
       "rojo": "Rojo", "roja": "Rojo", "joven": "Joven_adj"}
VERB = {"lee": "Leer", "leyó": "Leer", "lea": "Leer", "estudia": "Estudiar",
        "estudie": "Estudiar", "aprueba": "Aprobar", "apruebe": "Aprobar",
        "escribe": "Escribir", "escriba": "Escribir", "ama": "Amar", "ame": "Amar",
        "conoce": "Conocer", "conozca": "Conocer", "ve": "Ver", "vea": "Ver"}
PLURAL = {"leen": "Leer", "leyeron": "Leer", "lean": "Leer", "estudian": "Estudiar",
          "estudien": "Estudiar", "aprueban": "Aprobar", "aprueben": "Aprobar",
          "escriben": "Escribir", "escriban": "Escribir", "aman": "Amar",
          "amen": "Amar", "conocen": "Conocer", "conozcan": "Conocer",
          "ven": "Ver", "vean": "Ver"}
ADJ_FORMS = {"inteligentes": "Inteligente", "altos": "Alto", "altas": "Alto",
             "rojos": "Rojo", "rojas": "Rojo", "jóvenes": "Joven_adj"}
NOUN_FORMS = {"estudiantes": "Estudiante", "libros": "Libro", "profesores": "Profesor",
              "profesoras": "Profesora", "personas": "Persona", "gatos": "Gato",
              "jóvenes": "Joven_sust"}
NUMBER = {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
          "2": 2, "3": 3, "4": 4, "5": 5}


def kind(tree: Tree) -> str:
    return tree.symbol.split("_", 1)[0]


def leaf(tree: Tree) -> str:
    if tree.text: return tree.text
    return " ".join(leaf(child) for child in tree.children)


def and_all(items):
    items = list(items)
    if not items: raise ValueError("Conjunción vacía")
    result = items[0]
    for item in items[1:]: result = And(result, item)
    return result


def or_all(items):
    items = list(items)
    if not items: raise ValueError("Disyunción vacía")
    result = items[0]
    for item in items[1:]: result = Or(result, item)
    return result


def normalize(formula):
    """Reagrupa cadenas asociativas sin cambiar el orden de sus miembros."""
    if isinstance(formula, (And, Or)):
        op = type(formula)
        terms = []
        def collect(item):
            item = normalize(item)
            if isinstance(item, op): collect(item.left); collect(item.right)
            else: terms.append(item)
        collect(formula.left); collect(formula.right)
        return (and_all if op is And else or_all)(terms)
    if isinstance(formula, (Implies, Iff)):
        return type(formula)(normalize(formula.left), normalize(formula.right))
    if isinstance(formula, Not): return Not(normalize(formula.operand))
    if isinstance(formula, (Forall, Exists)): return type(formula)(formula.var, normalize(formula.body))
    return formula


@dataclass(frozen=True)
class NP:
    mode: str
    nominal: Tree | None = None
    name: Const | None = None
    names: tuple[Const, ...] = ()
    count: int = 0


class Composer:
    def __init__(self): self.next_var = 0

    def fresh(self):
        index = self.next_var
        self.next_var += 1
        return Var(("x", "y", "z", "u", "v", "w")[index] if index < 6 else f"x{index + 1}")

    def nominal(self, tree: Tree, term):
        if kind(tree) in ("N", "Adj"):
            word = leaf(tree)
            table = NOUN | NOUN_FORMS if kind(tree) == "N" else ADJ | ADJ_FORMS
            symbol = (table.get(word) or SENSE.get((kind(tree), word)) or lexicon.symbol(kind(tree), word)
                      or EXTRA[(kind(tree), word)])
            return Pred(symbol, (term,))
        if kind(tree) == "Pred":
            if len(tree.children) == 1: return self.nominal(tree.children[0], term)
            return And(self.nominal(tree.children[0], term), self.nominal(tree.children[2], term))
        if kind(tree) == "Rel": return self.vp(tree.children[1], term)
        if kind(tree) == "Nom": return and_all(self.nominal(child, term) for child in tree.children)
        raise ValueError(f"Nominal no previsto: {tree.symbol}")

    def np(self, tree: Tree) -> NP:
        k = kind(tree)
        if k in ("SNany", "SNnegAny", "Obj", "ObjNeg", "SNex") and len(tree.children) == 1:
            return self.np(tree.children[0])
        if k == "Nom": return NP("exists", nominal=tree)
        if k in ("Obj", "ObjNeg") and len(tree.children) == 2:
            return self.np(tree.children[1])
        if k.startswith("NProp"):
            return NP("name", name=Const(plain(leaf(tree))))
        if k in ("ListM", "ListF", "ListAny", "OListM", "OListF", "OListAny", "NPAny"):
            names = tuple(Const(plain(leaf(child))) for child in self.name_leaves(tree))
            return NP("or_names" if k.startswith("OList") else "and_names", names=names)
        if k in ("SN", "SNneg", "SNex"):
            if len(tree.children) == 1:
                child = tree.children[0]
                if kind(child) in ("NProp", "ListM", "ListF", "OListM", "OListF", "Alguien", "Nadie", "Nom"):
                    if kind(child) == "Alguien": return NP("exists")
                    if kind(child) == "Nadie": return NP("none")
                    if kind(child) == "Nom": return NP("exists", nominal=child)
                    return self.np(child)
            if len(tree.children) == 2:
                det, nominal = tree.children
                if kind(det) in ("Alguien", "Nadie"):
                    return NP("exists" if kind(det) == "Alguien" else "none", nominal=nominal)
                d = kind(det)
                if d == "DetU": mode = "forall"
                elif d == "DetE": mode = "exists"
                elif d == "DetNo": mode = "none"
                elif d == "DetNum":
                    word = leaf(det.children[-1]).split()[-1]
                    count = NUMBER[word]
                    marker = kind(det.children[0])
                    mode = "exact" if marker == "Exactamente" else "at_most" if marker == "ALoSumo" else "at_least"
                    if marker == "Num": mode = "bare_number"
                    return NP(mode, nominal=nominal, count=count)
                else: raise ValueError(f"Determinante no previsto: {d}")
                return NP(mode, nominal=nominal)
        raise ValueError(f"SN no previsto: {tree.symbol}")

    def name_leaves(self, tree):
        if kind(tree) == "NProp": return (tree,)
        return tuple(item for child in tree.children for item in self.name_leaves(child))

    def apply(self, np: NP, body):
        if np.mode == "name": return body(np.name)
        if np.mode in ("and_names", "or_names"):
            forms = [body(name) for name in np.names]
            return (and_all if np.mode == "and_names" else or_all)(forms)
        if np.mode in ("forall", "exists", "none"):
            var = self.fresh()
            predicate = body(var)
            if np.nominal:
                restrict = self.nominal(np.nominal, var)
                predicate = Implies(restrict, predicate) if np.mode == "forall" else And(restrict, predicate)
            result = (Forall if np.mode == "forall" else Exists)(var.name, predicate)
            return Not(result) if np.mode == "none" else result
        if np.mode in ("at_least", "at_most", "exact", "bare_number"):
            n = np.count
            if np.mode == "at_most": return Not(self.at_least(n + 1, np.nominal, body))
            if np.mode == "exact":
                return And(self.at_least(n, np.nominal, body), Not(self.at_least(n + 1, np.nominal, body)))
            return self.at_least(n, np.nominal, body)
        raise ValueError(f"Cuantificador no previsto: {np.mode}")

    def at_least(self, n, nominal, body):
        variables = [self.fresh() for _ in range(n)]
        parts = [Not(Eq(a, b)) for i, a in enumerate(variables) for b in variables[i + 1:]]
        for var in variables:
            if nominal: parts.append(self.nominal(nominal, var))
            extra = body(var)
            if extra is not None: parts.append(extra)
        result = and_all(parts)
        for var in reversed(variables): result = Exists(var.name, result)
        return result

    def vp(self, tree: Tree, subject):
        k = kind(tree)
        if k in ("SV", "SVsub"):
            parts = tree.children
            if len(parts) == 1: return self.vp(parts[0], subject)
            if len(parts) == 3 and kind(parts[1]) in ("Y", "Ox"):
                op = And if kind(parts[1]) == "Y" else Or
                return op(self.vp(parts[0], subject), self.vp(parts[2], subject))
            if kind(parts[0]) == "No" and len(parts) == 2:
                return Not(self.vp(parts[1], subject))
            if kind(parts[0]) == "No" and len(parts) == 3:
                return Not(self.transitive(parts[1], parts[2], subject, negative_object=True))
        if k == "SVpos":
            parts = tree.children
            if len(parts) == 1: return self.vp(parts[0], subject)
            if kind(parts[0]) == "Se":
                verb = self.verb(parts[1]); return Pred(verb + "2", (subject, subject))
            if kind(parts[0]) == "VT": return self.transitive(parts[0], parts[1], subject)
            if kind(parts[0]) == "Cop":
                if len(parts) == 2 and kind(parts[1]) == "NProp": return Eq(subject, self.np(parts[1]).name)
                return self.nominal(parts[-1], subject)
        if k == "VI" or k == "VIsub": return Pred(self.verb(tree), (subject,))
        if k == "VT" or k == "VTsub": raise ValueError("Verbo transitivo sin objeto")
        if k == "SVsub" and len(tree.children) == 2:
            return self.transitive(tree.children[0], tree.children[1], subject)
        if len(tree.children) == 2 and kind(tree.children[0]) == "VTsub":
            return self.transitive(tree.children[0], tree.children[1], subject)
        raise ValueError(f"Predicado verbal no previsto: {tree.symbol}")

    def verb(self, tree):
        word = leaf(tree)
        return (VERB.get(word) or PLURAL.get(word) or SENSE.get(("V", word)) or lexicon.symbol("V", word)
                or EXTRA[("V", word)])

    def transitive(self, verb_tree, obj_tree, subject, negative_object=False):
        name = self.verb(verb_tree) + "2"
        obj = self.np(obj_tree)
        if negative_object and obj.mode == "none":
            obj = NP("exists", nominal=obj.nominal)
        return self.apply(obj, lambda value: Pred(name, (subject, value)))

    def sentence(self, tree: Tree):
        if kind(tree) == "S": return self.sentence(tree.children[0])
        if kind(tree) != "O": raise ValueError(f"Oración no prevista: {tree.symbol}")
        parts = tree.children
        k = tuple(kind(p) for p in parts)
        if len(parts) == 2 and k[0] == "SN":
            return self.apply(self.np(parts[0]), lambda term: self.vp(parts[1], term))
        if len(parts) == 2 and k[0] == "SNneg":
            return self.apply(self.np(parts[0]), lambda term: self.vp(parts[1], term))
        if k[:1] == ("Solo",):
            var = self.fresh()
            if len(parts) == 3:
                return Forall(var.name, Implies(self.vp(parts[2], var), Eq(var, self.np(parts[1]).name)))
            return Forall(var.name, Implies(self.vp(parts[3], var), self.nominal(parts[2], var)))
        if k[:1] == ("Hay",):
            if len(parts) == 2:
                return self.existence(self.np(parts[1]))
            var = self.fresh()
            return Exists(var.name, self.nominal(parts[2], var))
        if k[:2] == ("No", "Hay"):
            if len(parts) == 3: return Not(self.existence(self.np(parts[2])))
        if k[:1] == ("No",) and len(parts) == 2 and kind(parts[1]) == "Hay":
            raise ValueError("Falta objeto existencial")
        if k[:1] == ("No",) and len(parts) == 3 and k[1] == "Hay":
            return Not(self.existence(self.np(parts[2])))
        if k[:2] == ("No", "Hay") and len(parts) == 3:
            return Not(self.existence(self.np(parts[2])))
        if k[:1] == ("NoEsCierto",): return Not(self.sentence(parts[1]))
        if k[:1] == ("Obien",):
            a, b = self.sentence(parts[1]), self.sentence(parts[3])
            return And(Or(a, b), Not(And(a, b)))
        if k[:2] == ("Si", "SNc"):
            # «Si un N hace A, entonces hace B»: el consecuente no repite el sujeto. Con sujeto
            # indefinido es una afirmación general sobre cualquier N; con nombre propio, una implicación.
            subject, first, second = parts[1], parts[2], parts[-1]
            if len(subject.children) == 1:
                name = self.np(subject.children[0]).name
                return Implies(self.vp(first, name), self.vp(second, name))
            var = self.fresh()
            return Forall(var.name, Implies(And(self.nominal(subject.children[1], var), self.vp(first, var)),
                                            self.vp(second, var)))
        if k[:1] == ("Si",):
            return Implies(self.sentence(parts[1]), self.sentence(parts[-1]))
        if len(parts) == 3 and k[1] in ("Y", "Ox", "Si", "SoloSi", "Ssi"):
            a, b = self.sentence(parts[0]), self.sentence(parts[2])
            return {"Y": And, "Ox": Or, "Si": lambda x, y: Implies(y, x),
                    "SoloSi": Implies, "Ssi": Iff}[k[1]](a, b)
        raise ValueError(f"Oración no prevista: {k}")

    def existence(self, np):
        if np.nominal is None: raise ValueError("Existencial sin restricción")
        if np.mode == "forall": raise ValueError("Existencial universal")
        if np.mode == "none": np = NP("exists", nominal=np.nominal)
        if np.mode in ("at_least", "at_most", "exact", "bare_number"):
            return self.apply(np, lambda _: None)
        var = self.fresh()
        return Exists(var.name, self.nominal(np.nominal, var))


def readings(tree: Tree):
    composer = Composer()
    formula = normalize(composer.sentence(tree))
    # La ambigüedad cuantitativa y algunos alcances no cambian el árbol sintáctico.
    sn = tree.children[0].children[0] if tree.children and tree.children[0].children else None
    if sn and kind(sn) == "SN" and len(sn.children) == 2 and kind(sn.children[0]) == "DetNum" and kind(sn.children[0].children[0]) == "Num":
        other = Composer()
        np = other.np(sn)
        exact = NP("exact", nominal=np.nominal, count=np.count)
        return ((formula, "Al menos esa cantidad"),
                (normalize(other.apply(exact, lambda term: other.vp(tree.children[0].children[1], term))), "Exactamente esa cantidad"))
    if sn and kind(sn) == "SN" and len(sn.children) == 2 and kind(sn.children[0]) == "DetU":
        vp = tree.children[0].children[1]
        if kind(vp) == "SV" and len(vp.children) == 2 and kind(vp.children[0]) == "No":
            subject = Var("x")
            body = Composer().vp(vp.children[1], subject)
            wide = Not(Forall("x", Implies(Composer().nominal(sn.children[1], subject), body)))
            return ((formula, "Ninguno del grupo cumple el predicado"),
                    (normalize(wide), "No todos los miembros del grupo lo cumplen"))
        inner = vp.children[0] if kind(vp) == "SV" and len(vp.children) == 1 else vp
        if kind(inner) == "SVpos" and len(inner.children) == 2 and kind(inner.children[0]) == "VT":
            obj = inner.children[1]
            if kind(obj) == "Obj": obj = obj.children[-1]
            if kind(obj) == "SNany": obj = obj.children[0]
            if kind(obj) == "SN" and len(obj.children) == 2 and kind(obj.children[0]) == "DetE":
                x, y = Var("x"), Var("y")
                c = Composer()
                relation = Pred(c.verb(inner.children[0]) + "2", (x, y))
                shared = Exists("y", And(c.nominal(obj.children[1], y),
                                         Forall("x", Implies(c.nominal(sn.children[1], x), relation))))
                return ((formula, "Cada miembro puede tener un objeto distinto"),
                        (normalize(shared), "Un mismo objeto sirve para todos"))
    return ((formula, "Lectura de la gramática controlada"),)

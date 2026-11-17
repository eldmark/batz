"""Entrada estricta del proyecto MM3032; no cambia la semántica general de FiniteModel."""
from __future__ import annotations

from collections.abc import Mapping
import json

from .ast import is_pred_name, is_term_name
from .errors import BatzError, SCHEMA_VERSION
from .model import FiniteModel
from .symbols import Signature


def _bad(message):
    raise BatzError("semantic", "invalid_model", message)


def _mapping(value, label):
    if not isinstance(value, Mapping):
        _bad(f"{label} debe ser un objeto")
    return value


def _arity(value, label, minimum):
    if type(value) is not int or value < minimum:
        _bad(f"{label} necesita aridad >= {minimum}")


def _signature(signature):
    if not isinstance(signature, Signature):
        _bad("la firma debe ser una Signature")
    constants = set(signature.constants)
    functions = _mapping(signature.functions, "funciones de la firma")
    predicates = _mapping(signature.predicates, "predicados de la firma")
    for name in constants:
        if not is_term_name(name):
            _bad(f"nombre de constante inválido: {name!r}")
    for name, arity in functions.items():
        if not is_term_name(name):
            _bad(f"nombre de función inválido: {name!r}")
        _arity(arity, f"la función '{name}'", 1)
    for name, arity in predicates.items():
        if not is_pred_name(name):
            _bad(f"nombre de predicado inválido: {name!r}")
        _arity(arity, f"el predicado '{name}'", 1)
    overlap = constants & set(functions)
    if overlap:
        _bad(f"'{sorted(overlap)[0]}' no puede ser constante y función")


def _same_symbols(actual, declared, label):
    missing = set(declared) - set(actual)
    extra = set(actual) - set(declared)
    if missing:
        _bad(f"falta interpretar {label}: {', '.join(sorted(missing))}")
    if extra:
        _bad(f"{label} no declarado: {', '.join(sorted(extra))}")


def build_interpretation(signature, data):
    """Construye un modelo desde el formato JSON de FiniteModel, con reglas MM3032.

    Las constantes representan las funciones de aridad cero en la interfaz.
    Los predicados deben tener aridad positiva y extensión no vacía.
    """
    _signature(signature)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            _bad(f"JSON de interpretación inválido: {exc.msg}")
    data = _mapping(data, "la interpretación")
    if "schema_version" in data and data["schema_version"] != SCHEMA_VERSION:
        _bad("schema_version no soportada")
    if "domain" not in data:
        _bad("falta el dominio")
    if not isinstance(data["domain"], list):
        _bad("el dominio debe ser una lista")
    domain = data["domain"]
    if not domain:
        _bad("el dominio no puede ser vacío")
    if any(type(value) not in (int, str) for value in domain):
        _bad("el dominio solo admite enteros y cadenas")
    def in_domain(value):
        return type(value) in (int, str) and any(type(value) is type(d) and value == d for d in domain)
    constants = _mapping(data.get("constants", {}), "constantes")
    functions = _mapping(data.get("functions", {}), "funciones")
    predicates = _mapping(data.get("predicates", {}), "predicados")
    _same_symbols(constants, signature.constants, "constante")
    _same_symbols(functions, signature.functions, "función")
    _same_symbols(predicates, signature.predicates, "predicado")
    for name, value in constants.items():
        if not in_domain(value):
            _bad(f"la constante '{name}' debe valer un elemento del dominio")

    fs, ps = {}, {}
    for name, arity in signature.functions.items():
        spec = _mapping(functions[name], f"la función '{name}'")
        if spec.get("arity") != arity or type(spec.get("arity")) is not int:
            _bad(f"aridad incorrecta de la función '{name}'")
        rows = spec.get("table")
        if not isinstance(rows, list):
            _bad(f"la tabla de '{name}' debe ser una lista")
        table = {}
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 2 or not isinstance(row[0], (list, tuple)):
                _bad(f"fila inválida en la tabla de '{name}'")
            try:
                key = tuple(row[0])
                if len(key) != arity or any(not in_domain(x) for x in key) or not in_domain(row[1]):
                    _bad(f"entrada inválida en la tabla de '{name}'")
                if key in table:
                    _bad(f"tupla duplicada en la tabla de '{name}': {key!r}")
                table[key] = row[1]
            except TypeError:
                _bad(f"tupla inválida en la tabla de '{name}'")
        fs[name] = (arity, table)

    for name, arity in signature.predicates.items():
        spec = _mapping(predicates[name], f"el predicado '{name}'")
        if spec.get("arity") != arity or type(spec.get("arity")) is not int:
            _bad(f"aridad incorrecta del predicado '{name}'")
        tuples = spec.get("tuples")
        if not isinstance(tuples, list) or not tuples:
            _bad(f"la relación '{name}' no puede ser vacía")
        if any(not isinstance(row, (list, tuple)) or len(row) != arity or
               any(not in_domain(x) for x in row) for row in tuples):
            _bad(f"tupla inválida en la relación '{name}'")
        ps[name] = (arity, tuples)

    try:
        return FiniteModel(data["domain"], constants, fs, ps)
    except BatzError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        _bad(f"interpretación mal formada: {exc}")

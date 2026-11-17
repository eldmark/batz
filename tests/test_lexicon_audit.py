"""Auditoría del léxico: el léxico base no tiene errores claros corregibles y las reglas los detectan."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from batz.lexicon import Entry

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("auditar_lexico", ROOT / "scripts" / "auditar_lexico.py")
audit = sys.modules.setdefault("auditar_lexico", importlib.util.module_from_spec(_spec))
_spec.loader.exec_module(audit)


def flags(*entries):
    return {(a.lema, a.regla, a.confianza) for a in audit.auditar_entradas(entries)}


class LexiconAudit(unittest.TestCase):
    def test_base_lexicon_has_no_fixable_clear_errors(self):
        avisos = audit.auditar(*audit.cargar([audit.lexicon.BASE]))
        self.assertEqual([a for a in avisos if a.confianza == "alta" and a.corregible], [])
        self.assertEqual(avisos, audit.auditar(*audit.cargar([audit.lexicon.BASE])))      # determinista

    def test_rules_catch_known_errors(self):
        cases = [
            (Entry("caos", "N", "M"), "plural"), (Entry("carácter", "N", "M"), "plural"),
            (Entry("jersey", "N", "M"), "plural"),
            (Entry("mano", "N", "M"), "genero"), (Entry("canción", "N", "M"), "genero"),
            (Entry("paisaje", "N", "F"), "genero"),
            (Entry("marrón", "ADJ", "-"), "femenino"), (Entry("cortés", "ADJ", "-"), "femenino"),
            (Entry("rojo", "ADJ", "-", "inv"), "femenino"),
            (Entry("pensar", "V", "IT"), "cambio_raiz"), (Entry("pedir", "V", "T", "cambio=ue"), "cambio_raiz"),
            (Entry("tener", "V", "T"), "verbo_irregular"),
            (Entry("prohibir", "V", "T"), "ortografia_verbal"), (Entry("reunir", "V", "T"), "ortografia_verbal"),
            (Entry("aislar", "V", "T"), "ortografia_verbal"),
            (Entry("el", "N", "M"), "palabra_cerrada"), (Entry("estar", "V", "I"), "palabra_cerrada"),
            (Entry("Jose", "NP", "M"), "nombre_propio"), (Entry("pedro", "NP", "M"), "nombre_propio"),
            (Entry("mierda", "N", "F"), "aula"), (Entry("casa", "N", "F", "cambio=ie"), "formato"),
        ]
        for entry, rule in cases:
            with self.subTest(lemma=entry.lemma):
                self.assertIn((entry.lemma, rule, "alta"), flags(entry))

    def test_correct_entries_raise_no_clear_error(self):
        good = [Entry("perro", "N", "M"), Entry("examen", "N", "M", "pl=exámenes"), Entry("país", "N", "M"),
                Entry("crisis", "N", "F", "pl=crisis"), Entry("problema", "N", "M"), Entry("mano", "N", "F"),
                Entry("joven", "ADJ", "-", "pl=jóvenes"), Entry("trabajador", "ADJ", "-"),
                Entry("mejor", "ADJ", "-", "inv"), Entry("inglés", "ADJ", "-"),
                Entry("pensar", "V", "IT", "cambio=ie"), Entry("seguir", "V", "T", "cambio=i"),
                Entry("construir", "V", "T"), Entry("leer", "V", "IT"), Entry("buscar", "V", "T"),
                Entry("enviar", "V", "T", "formas=envía,envían,envíe,envíen,envió,enviaron"),
                Entry("reír", "V", "I", "formas=ríe,ríen,ría,rían,rio,rieron"),
                Entry("José", "NP", "M"), Entry("Rocío", "NP", "F"),
                # el generador resuelve estas ortografías por regla: no hacen falta formas= (regresión)
                Entry("evaluar", "V", "T"), Entry("averiguar", "V", "T"), Entry("guiar", "V", "T"), Entry("gruñir", "V", "I"),
                Entry("paraguas", "N", "M"), Entry("origen", "N", "M"), Entry("bit", "N", "M"),
                Entry("autobús", "N", "M"), Entry("crimen", "N", "M"), Entry("robot", "N", "M"), Entry("lunes", "N", "M"),
                Entry("compás", "N", "M"), Entry("banco", "N", "M", "sentido=asiento"), Entry("can", "N", "M", "sin=perro")]
        self.assertEqual([a for a in audit.auditar_entradas(good) if a.confianza == "alta"], [])

    def test_skipped_and_conflicting_rows_are_reported_with_their_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lexico.tsv"
            path.write_text("# comentario\nperro\tN\tM\t\ngato\tX\tM\t\nperro\tN\tF\t\n", encoding="utf-8")
            found = {(a.lema, a.regla, a.linea) for a in audit.auditar(*audit.cargar([path]))}
        self.assertIn(("gato", "formato", 3), found)       # categoría desconocida: el cargador la ignora
        self.assertIn(("perro", "duplicado", 4), found)    # mismo lema y categoría, otro género


if __name__ == "__main__":
    unittest.main()

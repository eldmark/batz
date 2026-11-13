#!/usr/bin/env python3
"""Auditoría del léxico del español: señala errores probables para que una persona decida.

    python scripts/auditar_lexico.py                          # informe del léxico base
    python scripts/auditar_lexico.py --confianza alta         # solo los avisos de confianza alta
    python scripts/auditar_lexico.py --formato markdown       # tabla con columna de visto bueno
    python scripts/auditar_lexico.py --formato tsv            # una fila por aviso (hoja de cálculo)
    python scripts/auditar_lexico.py src/logos/lexicon.tsv datos/lexico_usuario.tsv   # varios archivos juntos

Las entradas se cargan con `logos.lexicon` y se revisa lo que el generador produce de verdad
(plural, femenino y las seis formas verbales). Esas formas se comparan con reglas escritas aquí
aparte, con listas de excepciones conocidas y con las palabras que ya trae la gramática
(`spanish_grammar.txt`). Cada aviso dice lema, categoría, regla, formas generadas, arreglo
sugerido y confianza:

    alta   error gramatical claro: una forma mal escrita o mal flexionada.
    media  problema probable que pide criterio (género común, uso del verbo, choque con la gramática).
    baja   punto para revisar (homónimos, vocabulario delicado, límites de la gramática).

Solo usa la biblioteca estándar, no modifica ningún archivo y su salida es determinista.
Que no haya avisos no significa que el léxico esté revisado: la revisión humana sigue haciendo falta.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from logos import lexicon  # noqa: E402
from logos.spanish_cyk import GRAMMAR  # noqa: E402
from logos.spanish_tagger import TAGS, plain  # noqa: E402

CONFIANZAS = ("alta", "media", "baja")
REGLAS = {
    "formato": "Fila mal formada: categoría, género o uso, opciones de «extra», lema o formas no válidas",
    "duplicado": "Entradas repetidas o en conflicto, lemas que son formas de otro lema, formas compartidas",
    "genero": "Género del sustantivo frente a excepciones conocidas (mano, día, problema…) y terminaciones (-ión, -dad, -aje…)",
    "genero_comun": "Sustantivos de persona comunes en cuanto al género («el/la paciente») marcados solo M o F",
    "a_tonica": "Femeninos con a- tónica («el águila», «un hada»), que la gramática no sabe escribir así",
    "plural": "Plural generado frente a las reglas: tildes (exámenes, canciones), -z → -ces, invariables en -s, préstamos",
    "femenino": "Femenino del adjetivo: -o → -a, -or → -ora salvo comparativos, -és → -esa, invariables y la marca inv",
    "verbo_irregular": "Verbos irregulares sin formas= y coherencia interna de formas=",
    "cambio_raiz": "Verbos con cambio de raíz (pensar, volver, pedir) sin cambio= o con un valor distinto",
    "ortografia_verbal": "Cambios ortográficos (-car, -gar, -zar, -guar, -ger, -gir, -guir, -quir, -cer, -cir, -uir, -eer, -ñir) "
                         "y tildes (envía, evalúa, prohíbe, monosílabos sin tilde)",
    "uso_verbal": "Uso con o sin objeto (I/T/IT) de verbos muy comunes; verbos modales e impersonales",
    "nombre_propio": "Nombres propios: mayúscula, tilde, género y choques con palabras comunes",
    "gramatica": "Formas que la gramática ya trae con otra categoría (existe, una) o que quedan tapadas por ella",
    "palabra_cerrada": "Artículos, preposiciones, pronombres, ser/estar/haber y otras palabras funcionales en la lista abierta",
    "simbolo": "Homónimos que comparten el mismo símbolo lógico (primo: pariente y número primo)",
    "aula": "Vocabulario vulgar o con un doble sentido ofensivo frecuente",
}

# --- listas de referencia ---------------------------------------------------------------------

# Palabras funcionales: la gramática las trata aparte o no son predicados.
CERRADAS = set("""
el la lo los las un una unos unas al del
a ante bajo cabe con contra de desde durante en entre hacia hasta mediante para por según sin so sobre tras versus vía
yo tú él ella ello nosotros nosotras vosotros vosotras ellos ellas usted ustedes me te se nos os le les mí ti sí
conmigo contigo consigo mi tu su mis tus sus mío mía tuyo tuya suyo suya nuestro nuestra vuestro vuestra
este esta esto ese esa eso aquel aquella aquello estos estas esos esas aquellos aquellas
que qué quien quienes quién quiénes cual cuales cuál cuáles cuyo cuya donde dónde cuando cuándo como cómo cuanto cuánto
alguien nadie algo nada uno alguno alguna algunos algunas algún ninguno ninguna ningún todo toda todos todas cada
cualquier cualquiera varios varias mucho mucha muchos muchas poco poca pocos pocas otro otra otros otras mismo misma ambos ambas
y e o u ni pero sino aunque porque pues si mas mientras
ser estar haber
cero dos tres cuatro cinco seis siete ocho nueve diez
no muy más menos tan también tampoco ya aún aun solo solamente siempre nunca jamás exactamente entonces aquí allí ahí hoy ayer quizá quizás
""".split())
# Homógrafos con un uso abierto legítimo: no se señalan (bajo, alto, sobre = carta, sino = destino…).
HOMOGRAFOS = {("bajo", "ADJ"), ("sobre", "N"), ("sino", "N"), ("solo", "ADJ"), ("uno", "N"), ("nada", "N"), ("todo", "N")}

# Género de sustantivos (no de persona) que suelen confundirse. Valor: géneros aceptables.
GENERO_CONOCIDO = {
    **dict.fromkeys("mano foto moto libido polio seo nao".split(), "F"),
    "mamá": "F",
    **dict.fromkeys("día mapa planeta cometa tranvía sofá papá idioma problema programa sistema tema teorema axioma poema "
                    "clima drama dilema esquema lema emblema enigma dogma diagrama crucigrama telegrama fantasma "
                    "aroma diploma síntoma trauma panorama prisma fonema estigma carisma cisma plasma magma "
                    "sintagma lexema morfema holograma pijama".split(), "M"),
    **dict.fromkeys("flor labor coliflor sal miel piel hiel cárcel señal pared red sed ley imagen razón sartén "
                    "crisis tesis hipótesis dosis síntesis nariz leche carne noche tarde llave calle nube fuente gente "
                    "clase frase muerte suerte sangre fiebre torre nieve mente serpiente liebre base parte nave ave "
                    "agua alma arma aula águila hada hacha área ala ancla arpa haba hambre".split(), "F"),
    **dict.fromkeys("análisis énfasis paréntesis oasis éxtasis color dolor amor calor olor sabor valor honor error "
                    "pez lápiz arroz avión camión corazón sillón jabón puente coche diente pie postre aceite nombre".split(), "M"),
    "mar": "MC", "azúcar": "MC", "arte": "MC", "radio": "MFC",
}
TERMINACIONES_F = ("ción", "sión", "xión", "dad", "tad", "tud", "umbre", "itis", "triz", "ncia", "eza")
EXCEPCIONES_ION = {"avión", "camión", "gorrión", "sarampión", "aluvión", "bastión", "centurión", "anfitrión", "guion"}

# Personas: comunes en cuanto al género (DRAE «com.»): «el/la paciente». Si hay femenino propio, va aparte.
COMUNES = set("""estudiante cantante testigo joven líder colega atleta guía policía espía astronauta paciente piloto
soldado modelo agente intérprete cónyuge rehén mártir militar rival adolescente representante terapeuta psiquiatra
pediatra homicida suicida patriota compatriota""".split())
FEMENINO_PROPIO = {"cliente": "clienta", "juez": "jueza", "huésped": "huéspeda", "poeta": "poetisa",
                   "presidente": "presidenta", "jefe": "jefa", "comediante": "comedianta", "pariente": "parienta"}
COSAS_EN_ISTA = set("revista pista lista vista arista conquista entrevista amatista autopista".split())  # no son personas

PLURAL_EXCEPCIONES = {
    "carácter": ("caracteres",), "régimen": ("regímenes",), "espécimen": ("especímenes",), "club": ("clubes", "clubs"),
    "álbum": ("álbumes",), "récord": ("récords",), "sándwich": ("sándwiches",), "fax": ("faxes",), "tórax": ("tórax",),
    "clímax": ("clímax",), "menú": ("menús",), "esquí": ("esquís",), "champú": ("champús",), "no": ("noes",),
    "sí": ("síes",), "jersey": ("jerséis",), "lord": ("lores",), "máster": ("másteres",),
}
INVARIABLES_ADJ = set("mejor peor mayor menor superior inferior anterior posterior exterior interior ulterior citerior "
                      "marrón cortés descortés afín ruin común".split())
FEMENINO_ESPECIAL = {"español": "española", "mongol": "mongola", "andaluz": "andaluza"}

# Verbos: irregulares que el generador no puede derivar (necesitan formas=). Compuestos por terminación.
IRREGULARES = set("""ser estar haber ir dar ver prever saber caber poder querer andar desandar jugar oler errar
adquirir inquirir erguir yacer asir""".split())
BASES_IRREGULARES = ("tener", "poner", "venir", "hacer", "facer", "decir", "traer", "ducir", "caer", "valer", "salir",
                     "querer", "oír", "eír")
CAMBIO = {
    **dict.fromkeys("""pensar cerrar empezar comenzar despertar sentar calentar recomendar encomendar enmendar atravesar
        confesar manifestar merendar apretar quebrar sembrar regar fregar negar renegar nevar temblar gobernar acertar
        tropezar encerrar entender atender extender tender defender perder encender ascender descender verter
        preferir referir conferir diferir inferir transferir interferir sentir consentir presentir resentir mentir
        desmentir divertir convertir advertir invertir herir hervir sugerir requerir digerir arrepentir""".split(), "ie"),
    **dict.fromkeys("""contar descontar costar acostar encontrar recordar acordar mostrar demostrar probar aprobar comprobar
        reprobar volar soñar rodar sonar tronar colgar rogar almorzar forzar esforzar reforzar renovar poblar soldar
        morder mover conmover promover remover volver devolver envolver revolver resolver absolver disolver llover doler
        soler torcer retorcer cocer dormir morir""".split(), "ue"),
    **dict.fromkeys("""pedir despedir impedir expedir servir repetir competir seguir conseguir perseguir proseguir
        elegir reelegir corregir regir vestir revestir investir medir rendir gemir teñir reñir ceñir derretir""".split(), "i"),
}
# -iar con hiato (envía) y verbos con hiato en la raíz (prohíbe); los demás -iar no llevan tilde (estudia).
HIATO_IAR = set("""ampliar ansiar arriar ataviar averiar chirriar confiar contrariar criar desafiar desconfiar descarriar
desviar enfriar enviar espiar esquiar expiar extasiar extraviar fiar fotografiar guiar hastiar inventariar liar malcriar
piar porfiar resfriar rociar telegrafiar vaciar variar estriar""".split())
IAR_SIN_TILDE = set("""abreviar acariciar agobiar agraviar aliviar angustiar anunciar apreciar asfixiar asociar cambiar
codiciar columpiar conciliar contagiar copiar denunciar despreciar diferenciar divorciar elogiar ensuciar envidiar estudiar
evidenciar financiar incendiar iniciar injuriar intercambiar licenciar lidiar limpiar mediar negociar obsequiar odiar
plagiar potenciar premiar presenciar presagiar principiar pronunciar refugiar remediar renunciar saciar sentenciar
silenciar sitiar testimoniar vendimiar viciar auxiliar paliar repatriar expatriar historiar agriar vidriar""".split())
HIATO_RAIZ = set("""prohibir cohibir reunir rehusar aislar aullar maullar aunar ahumar ahijar enraizar aupar rehuir
prohijar sahumar embaular europeizar""".split())
MODALES = {"poder", "deber", "soler"}
IMPERSONALES = {"llover", "nevar", "granizar", "tronar", "lloviznar", "relampaguear", "amanecer", "anochecer", "atardecer"}

# Uso de verbos muy comunes: (uso esperado, confianza si no coincide, ejemplo).
USO = {
    **{v: ("IT", "media", ej) for v, ej in {
        "comer": "«Juan come» / «Juan come pan»", "beber": "«Juan bebe» / «Juan bebe agua»",
        "leer": "«Ana lee» / «Ana lee un libro»", "escribir": "«Ana escribe» / «Ana escribe una carta»",
        "cantar": "«Ana canta» / «Ana canta una canción»", "hablar": "«Juan habla» / «Juan habla inglés»",
        "estudiar": "«Juan estudia» / «Juan estudia lógica»", "pintar": "«Ana pinta» / «Ana pinta un cuadro»",
        "dibujar": "«Ana dibuja» / «Ana dibuja un árbol»", "cocinar": "«Juan cocina» / «Juan cocina arroz»",
        "morder": "«El perro muerde» / «El perro muerde un hueso»", "entender": "«Juan entiende» / «Juan entiende la pregunta»",
        "enseñar": "«La profesora enseña» / «La profesora enseña lógica»", "aprender": "«Juan aprende» / «Juan aprende lógica»",
        "aplaudir": "«El público aplaude» / «El público aplaude a la actriz»",
        "discutir": "«Los vecinos discuten» / «Los vecinos discuten el plan»",
        "cambiar": "«El clima cambia» / «Juan cambia la rueda»", "pasear": "«Juan pasea» / «Juan pasea al perro»",
        "pescar": "«Juan pesca» / «Juan pesca un pez»", "ganar": "«Juan gana» / «Juan gana el partido»",
        "perder": "«Juan pierde» / «Juan pierde las llaves»", "jugar": "«Los niños juegan» / «Juegan un partido»",
        "esperar": "«Juan espera» / «Juan espera a Ana»", "pensar": "«Juan piensa» / «Juan piensa una idea»",
        "correr": "«Juan corre» / «Juan corre una maratón»", "mirar": "«Juan mira» / «Juan mira el cielo»",
        "escuchar": "«Juan escucha» / «Juan escucha música»"}.items()},
    **{v: ("IT", "baja", ej) for v, ej in {
        "comprender": "«Juan comprende» / «Juan comprende el problema»", "bailar": "«Ana baila» / «Ana baila un tango»",
        "ayudar": "«Juan ayuda» / «Juan ayuda a Ana»", "sufrir": "«Juan sufre» / «Juan sufre un accidente»",
        "mejorar": "«El enfermo mejora» / «Juan mejora el programa»", "oír": "«Juan no oye» / «Juan oye un ruido»",
        "vencer": "«Juan vence» / «Juan vence al rival»", "saltar": "«El gato salta» / «El gato salta el muro»",
        "cazar": "«El león caza» / «El león caza una cebra»"}.items()},
    **{v: ("I", "media", "sin objeto directo") for v in
       "dormir llegar nacer morir ir venir caminar nadar llorar reír sonreír existir vivir trabajar viajar crecer caer".split()},
    **{v: ("T", "media", "con objeto directo") for v in
       "tener hacer querer amar odiar conocer buscar comprar necesitar usar dar decir poner traer construir encontrar".split()},
}

# Nombres que llevan tilde en español (sin tilde → con tilde).
NOMBRES_CON_TILDE = {plain(n).casefold(): n for n in """José María Lucía Sofía Andrés Tomás Nicolás Ramón Rubén Simón
Víctor Héctor César Óscar Raúl Iván Adrián Álvaro Ángel Ángela Bárbara Mónica Verónica Inés Rocío Jesús Martín Joaquín
Agustín Benjamín Sebastián Fabián Germán Darío Elías Néstor Débora Estefanía Penélope Antígona Platón Sócrates
Aristóteles Pitágoras Arquímedes Napoleón Colón Bolívar Jazmín Belén Julián Damián Cristóbal Efraín Lázaro Ángeles
Dámaso""".split()}
NOMBRES_TILDE_DUDOSA = {"miriam": "Míriam"}  # llana acabada en -m: la RAE la escribe con tilde
NOMBRES_F_EN_O = {"Rocío", "Rosario", "Amparo", "Consuelo", "Socorro", "Sagrario"}
NOMBRES_M_EN_A = {"Luca", "Borja", "Bautista", "Jeremías", "Isaías", "Matías", "Tobías"}

# Homónimos de sustantivo y adjetivo con significados distintos que acaban en el mismo predicado.
HOMONIMOS = {"primo": "pariente / número primo", "paciente": "persona enferma / que tiene paciencia",
             "dulce": "golosina / de sabor dulce", "lógico": "especialista en lógica / razonable"}

VULGARES = set("""puta puto mierda coño joder cabrón cabrona pendejo pendeja culo polla chingar chingada verga pinche
marica maricón gilipollas hostia carajo cojones follar""".split())
DOBLE_SENTIDO = {"zorra": "además de la hembra del zorro, es un insulto vulgar muy frecuente contra mujeres",
                 "perra": "además de la hembra del perro, se usa como insulto contra mujeres",
                 "cerda": "además de la hembra del cerdo, se usa como insulto", "coger": "es vulgar en buena parte de América"}

# --- fonología y ortografía -----------------------------------------------------------------

VOCALES = "aeiouáéíóúü"
FUERTES = "aeoáéó"
TILDE = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
SIN_TILDE = {v: k for k, v in TILDE.items()}


def _vocal(w, i):
    c = w[i]
    if c == "u" and 0 < i < len(w) - 1 and w[i - 1] in "gq" and w[i + 1] in "eéií":
        return False                                     # u muda: que, qui, gue, gui
    if c in VOCALES:
        return True
    return c == "y" and i == len(w) - 1 and i > 0 and w[i - 1] in VOCALES   # rey, hoy, muy


def _hiato(a, b):
    if a in FUERTES and b in FUERTES:
        return True
    if (a in "íú" and b in FUERTES) or (b in "íú" and a in FUERTES):
        return True
    return a == b


def nucleos(w):
    """Núcleos silábicos (inicio, fin): los diptongos van juntos y los hiatos aparte (le-er, pa-ís, dios)."""
    out, i = [], 0
    while i < len(w):
        if not _vocal(w, i):
            i += 1
            continue
        j = i + 1
        while j < len(w) and _vocal(w, j) and not _hiato(w[j - 1], w[j]):
            j += 1
        out.append((i, j))
        i = j
    return out


def tonica(w):
    """(índice del núcleo tónico, núcleos), por la tilde o por las reglas generales de acentuación."""
    ns = nucleos(w)
    for k, (a, b) in enumerate(ns):
        if any(c in SIN_TILDE for c in w[a:b]):
            return k, ns
    if len(ns) < 2:
        return len(ns) - 1, ns
    return (len(ns) - 2 if w[-1] in "aeiouns" else len(ns) - 1), ns


def con_tilde(w, k):
    """Pone tilde al núcleo k: en la vocal abierta; en ui/iu, en la segunda."""
    a, b = nucleos(w)[k]
    seg = w[a:b]
    pos = next((i for i, c in enumerate(seg) if c in "aeo"), len(seg) - 1)
    return w[:a + pos] + TILDE.get(seg[pos], seg[pos]) + w[a + pos + 1:]


def sin_tilde_final(w):
    """Quita la tilde del último núcleo, salvo la que marca hiato (país, raíz, baúl)."""
    ns = nucleos(w)
    if not ns:
        return w
    a, b = ns[-1]
    for i in range(a, b):
        c = w[i]
        if c in SIN_TILDE:
            if c in "íú" and ((i > 0 and _vocal(w, i - 1)) or (i + 1 < len(w) and _vocal(w, i + 1))):
                return w
            return w[:i] + SIN_TILDE[c] + w[i + 1:]
    return w


def plurales_esperados(w):
    """Plurales correctos según la ortografía, o None si la regla general no basta."""
    if w in PLURAL_EXCEPCIONES:
        return set(PLURAL_EXCEPCIONES[w])
    k, ns = tonica(w)
    n, last = len(ns), w[-1]
    if last in "aeiouáéó":
        return {w + "s"}
    if last in "íú":
        return {w + "es", w + "s"}
    if last == "z":
        return {w[:-1] + "ces"}
    if last in "sx":
        if n <= 1:
            return {w + "es"}                                # mes → meses, dios → dioses
        return {sin_tilde_final(w) + "es"} if k == n - 1 else {w}   # inglés → ingleses; crisis, lunes
    if last == "y":
        return {w + "es"}                                    # rey → reyes
    if last in "lrndj":
        if k <= n - 3:
            return None                                      # esdrújula en consonante: régimen → regímenes
        if last == "n" and n >= 2 and k == n - 2 and not any(c in SIN_TILDE for c in w):
            return {con_tilde(w, n - 2) + "es"}              # examen → exámenes, joven → jóvenes
        return {sin_tilde_final(w) + "es"} if k == n - 1 else {w + "es"}   # canción → canciones; árbol → árboles
    return {w + "s"}                                         # préstamo en otra consonante: robot → robots


def femeninos_esperados(w):
    """(femeninos correctos del adjetivo, confianza de la regla)."""
    if w in INVARIABLES_ADJ:
        return {w}, "alta"
    if w in FEMENINO_ESPECIAL:
        return {FEMENINO_ESPECIAL[w]}, "alta"
    if w.endswith("o"):
        return {w[:-1] + "a"}, "alta"
    if w.endswith("or"):
        return {w + "a"}, "alta"
    if w.endswith(("án", "ín", "ón", "és")):
        return {sin_tilde_final(w) + "a"}, "alta"
    if w.endswith(("ete", "ote")):
        return {w[:-1] + "a"}, "media"                       # regordete → regordeta
    return {w}, "alta"


def _es_monosilabo_con_tilde(form):
    return form != "dé" and any(c in SIN_TILDE for c in form) and len(nucleos(form)) == 1


def _sin_tilde_monosilabos(forms):
    return [sin_tilde_final(f) if _es_monosilabo_con_tilde(f) else f for f in forms]


# --- carga --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Aviso:
    confianza: str
    regla: str
    lema: str
    categoria: str
    formas: str
    problema: str
    arreglo: str
    corregible: bool = True      # el arreglo es una edición del TSV
    archivo: str = ""
    linea: int = 0

    def clave(self):
        return (CONFIANZAS.index(self.confianza), list(REGLAS).index(self.regla), self.archivo, self.linea,
                self.lema, self.problema)


def _nombre(ruta):
    try:
        return ruta.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(ruta)


def cargar(rutas):
    """[(Entry, archivo, línea, columnas)] leídas con `lexicon._read`, y las filas que ese cargador ignora."""
    filas, ignoradas = [], []
    for ruta in rutas:
        fuente = "base" if ruta.resolve() == lexicon.BASE.resolve() else "usuario"
        entradas = iter(lexicon._read(ruta, fuente))
        for n, line in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.split("\t")
            lemma, category = cols[0].strip(), (cols + [""])[1].strip()
            if category in lexicon.CATEGORIES and lemma:
                entry = next(entradas)
                assert (entry.lemma, entry.category) == (lemma, category), (ruta, n)
                filas.append((entry, _nombre(ruta), n, len(cols)))
            else:
                ignoradas.append((_nombre(ruta), n, line))
    return filas, ignoradas


def palabras_de_la_gramatica():
    """{palabra: categorías} de las palabras sueltas que trae `spanish_grammar.txt` (como hace `spanish_cyk`)."""
    lines = GRAMMAR.read_text(encoding="utf-8").splitlines()
    heads = {line.split("->", 1)[0].strip() for line in lines if "->" in line}
    sueltas = defaultdict(set)
    for line in lines:
        if "->" not in line:
            continue
        head, body = (s.strip() for s in line.split("->", 1))
        for alternative in body.split("|"):
            words = alternative.split()
            if len(words) == 1 and words[0] not in heads:
                sueltas[words[0]].add(head)
    return dict(sueltas)


def formas_de(e):
    """Lo que produce hoy el diccionario para la entrada, con nombres fijos."""
    f = e.forms()
    if e.category == "N":
        g = "M" if "N_MS" in f else "F"
        if f"N_{g}S" not in f:
            raise ValueError("falta el género (M, F o C)")
        return {"sing": f[f"N_{g}S"][0], "pl": f[f"N_{g}P"][0]}
    if e.category == "ADJ":
        return {"ms": f["Adj_MS"][0], "fs": f["Adj_FS"][0], "mp": f["Adj_MP"][0], "fp": f["Adj_FP"][0]}
    if e.category == "V":
        k = "VI" if "VI_S" in f else "VT"
        (s3, pret_s), (p3, pret_p) = f[f"{k}_S"], f[f"{k}_P"]
        return {"s3": s3, "p3": p3, "sub_s": f[f"{k}sub_S"][0], "sub_p": f[f"{k}sub_P"][0],
                "pret_s": pret_s, "pret_p": pret_p}
    return {"np": next(iter(f.values()))[0]}


SEIS = ("s3", "p3", "sub_s", "sub_p", "pret_s", "pret_p")


def texto_formas(e, fm):
    if not fm:
        return "—"
    if e.category == "N":
        return f"{fm['sing']} → {fm['pl']}"
    if e.category == "ADJ":
        return " · ".join(fm[k] for k in ("ms", "fs", "mp", "fp"))
    if e.category == "V":
        return ", ".join(fm[k] for k in SEIS)
    return fm["np"]


def _formas_opcion(forms):
    return "formas=" + ",".join(forms)


def _donde(fila):
    return f"{fila[1]}:{fila[2]}" if fila[1] else f"línea {fila[2]}"


# --- reglas -------------------------------------------------------------------------------------

class Auditoria:
    def __init__(self, filas, ignoradas=()):
        self.filas = filas
        self.ignoradas = ignoradas
        self.avisos = []
        self.formas = {}
        self.gramatica = palabras_de_la_gramatica()
        self.cerradas_gramatica = {w for w, heads in self.gramatica.items() if not heads & set(TAGS)}

    def avisar(self, fila, confianza, regla, problema, arreglo, corregible=True):
        e, archivo, linea = fila[:3]
        self.avisos.append(Aviso(confianza, regla, e.lemma, e.category, texto_formas(e, self.formas.get(id(e))),
                                 problema, arreglo, corregible, archivo, linea))

    def ejecutar(self):
        for archivo, linea, texto in self.ignoradas:
            self.avisos.append(Aviso("alta", "formato", texto.split("\t")[0].strip() or "—", "?", "—",
                                     "el cargador ignora esta fila (categoría desconocida o lema vacío)",
                                     "corregir la categoría (N, ADJ, V, NP) o quitar la fila", True, archivo, linea))
        validas = []
        for fila in self.filas:
            e = fila[0]
            self.formato(fila)
            try:
                self.formas[id(e)] = formas_de(e)
            except Exception as exc:          # el generador puede lanzar LogosError, KeyError…
                self.avisar(fila, "alta", "formato", f"no se puede flexionar: {exc}", "corregir la fila")
                continue
            for value in self.formas[id(e)].values():
                if not value or not value.isalpha():
                    self.avisar(fila, "alta", "formato", f"forma no válida: «{value}»", "revisar pl= o formas=")
            validas.append(fila)
        for fila in validas:
            e = fila[0]
            getattr(self, {"N": "sustantivo", "ADJ": "adjetivo", "V": "verbo", "NP": "nombre_propio"}[e.category])(fila)
            self.cerrada_y_aula(fila)
        self.duplicados(validas)
        self.choques_con_la_gramatica(validas)
        return sorted(set(self.avisos), key=Aviso.clave)

    # -- formato --
    def formato(self, fila):
        e, _, _, columnas = fila
        opts = e.options()
        if not all(ch.isalpha() for ch in e.lemma):
            self.avisar(fila, "alta", "formato", "el lema debe ser una sola palabra, solo letras", "corregir el lema")
        if e.category != "NP" and e.lemma != e.lemma.casefold():
            self.avisar(fila, "media", "formato", "lema con mayúsculas en una categoría abierta", f"escribir «{e.lemma.casefold()}»")
        allowed = {"N": "MFC", "NP": "MF", "V": ("I", "T", "IT"), "ADJ": ("-",)}[e.category]
        if e.feature not in allowed or (e.category in ("N", "NP") and len(e.feature) != 1):
            self.avisar(fila, "alta", "formato", f"«{e.feature}» no vale como género o uso de {e.category}",
                        "usar " + " / ".join(allowed))
        if columnas > 4:
            self.avisar(fila, "media", "formato", "la fila tiene más de cuatro columnas y el cargador ignora el resto",
                        "unir el extra en la cuarta columna, separado por «;»")
        valid = {"N": {"pl"}, "ADJ": {"pl", "inv"}, "V": {"cambio", "formas"}, "NP": set()}[e.category]
        for key in sorted(opts):
            if key not in valid:
                self.avisar(fila, "alta", "formato", f"la opción «{key}» no se aplica a {e.category} y se ignora",
                            f"quitar «{key}» o cambiar la categoría")
        if e.category == "V" and "cambio" in opts:
            if opts["cambio"] not in ("ue", "ie", "i"):
                self.avisar(fila, "alta", "formato", f"cambio={opts['cambio']} no existe", "usar cambio=ue, ie o i")
            elif "formas" in opts:
                self.avisar(fila, "media", "formato", "cambio= no tiene efecto cuando hay formas=", "quitar cambio=")
            elif {"ue": "o", "ie": "e", "i": "e"}[opts["cambio"]] not in e.lemma.casefold()[:-2]:
                self.avisar(fila, "alta", "formato", "la raíz no tiene la vocal que cambia: cambio= no hace nada",
                            "revisar cambio=")

    # -- sustantivos --
    def sustantivo(self, fila):
        e = fila[0]
        w, g, fm = e.lemma.casefold(), e.feature, self.formas[id(e)]
        conocido = GENERO_CONOCIDO.get(w)
        if conocido and g not in conocido:
            if len(conocido) == 1 and g != "C":
                self.avisar(fila, "alta", "genero", f"«{w}» es {'femenino' if conocido == 'F' else 'masculino'}",
                            f"cambiar el género {g} → {conocido}")
            elif len(conocido) == 1:
                self.avisar(fila, "media", "genero", f"«{w}» solo es {'femenino' if conocido == 'F' else 'masculino'}; "
                            "C admite también el otro artículo", f"cambiar el género C → {conocido}")
            else:
                self.avisar(fila, "media", "genero", f"«{w}» es de género ambiguo y lo más común es el masculino "
                            f"(«el {w}»); con {g} solo se rechaza ese uso", f"cambiar el género {g} → C")
        elif not conocido and w not in COMUNES and w not in FEMENINO_PROPIO:
            if w.endswith(TERMINACIONES_F) or (w.endswith("ión") and w not in EXCEPCIONES_ION):
                if g != "F":
                    self.avisar(fila, "alta" if g == "M" else "media", "genero",
                                "las palabras en -ción, -sión, -dad, -tad, -tud, -umbre, -eza… son femeninas",
                                f"cambiar el género {g} → F")
            elif (w.endswith("aje") or (w.endswith("or") and w not in ("sor",))) and g == "F":
                self.avisar(fila, "alta", "genero", "las palabras en -aje y -or son masculinas (salvo flor, labor)",
                            "cambiar el género F → M")
            elif plain(w).endswith("o") and g == "F":
                self.avisar(fila, "media", "genero", "femenino acabado en -o (las excepciones conocidas son mano, foto, moto…)",
                            "comprobar el género")
            elif plain(w).endswith("a") and g == "M" and not w.endswith(("ista", "eta", "ota", "cida", "arca", "crata", "nauta")):
                self.avisar(fila, "media", "genero", "masculino acabado en -a que no está entre las excepciones conocidas "
                            "(día, mapa, problema…)", "comprobar el género")
        if w in COMUNES and g != "C":
            self.avisar(fila, "media", "genero_comun", f"es común en cuanto al género: «el {w}» y «la {w}»",
                        f"cambiar el género {g} → C")
        elif w.endswith("ista") and w not in COSAS_EN_ISTA and g != "C":
            self.avisar(fila, "media", "genero_comun", f"los sustantivos de persona en -ista son comunes: «el/la {w}»",
                        f"cambiar el género {g} → C")
        elif w in FEMENINO_PROPIO and g == "M":
            fem = FEMENINO_PROPIO[w]
            if not any(o[0].lemma.casefold() == fem and o[0].category == "N" for o in self.filas):
                self.avisar(fila, "baja", "genero_comun", f"también se dice «la {w}» (además de «la {fem}», que no está en el léxico)",
                            f"cambiar el género M → C, o añadir «{fem}» como N F")
        if g in ("F", "C") and plain(w).startswith(("a", "ha")):
            k, ns = tonica(w)
            if k == 0 and len(ns) >= 2:
                self.avisar(fila, "baja", "a_tonica", f"femenino con a- tónica: se dice «el {w}», «un {w}», pero la gramática "
                            f"solo acepta «una {w}», «alguna {w}»…", "nada en el léxico; es un límite de la gramática", False)
        self.revisar_plural(fila, w, fm["pl"], e.options().get("pl"))

    def revisar_plural(self, fila, singular, generado, dado):
        esperado = plurales_esperados(singular)
        if esperado is None or generado in esperado:
            return
        mejor = sorted(esperado)[0]
        origen = f"pl={dado}" if dado else "el plural generado"
        self.avisar(fila, "alta", "plural", f"{origen} es «{generado}»; lo correcto es «{'» o «'.join(sorted(esperado))}»",
                    f"{'cambiar' if dado else 'añadir'} pl={mejor}")

    # -- adjetivos --
    def adjetivo(self, fila):
        e = fila[0]
        w, fm, opts = e.lemma.casefold(), self.formas[id(e)], e.options()
        esperado, confianza = femeninos_esperados(w)
        if "inv" in opts and esperado != {w}:
            self.avisar(fila, confianza, "femenino", f"«inv» impide el femenino «{sorted(esperado)[0]}»", "quitar inv")
        elif fm["fs"] not in esperado:
            fem = sorted(esperado)[0]
            if esperado == {w}:
                self.avisar(fila, confianza, "femenino", f"el adjetivo no cambia en femenino, pero se genera «{fm['fs']}»",
                            "añadir inv")
            else:
                self.avisar(fila, confianza, "femenino", f"el femenino es «{fem}» y se genera «{fm['fs']}»",
                            f"el formato no puede expresar «{fem}»: hace falta cambiar lexicon.py "
                            f"(p. ej., una opción fem={fem})", False)
        self.revisar_plural(fila, fm["ms"], fm["mp"], opts.get("pl"))
        if fm["fs"] != fm["ms"]:
            esperado_fp = plurales_esperados(fm["fs"])
            if esperado_fp and fm["fp"] not in esperado_fp:
                self.avisar(fila, "alta", "plural", f"el femenino plural es «{sorted(esperado_fp)[0]}» y se genera «{fm['fp']}»",
                            "revisar pl=")

    # -- verbos --
    def verbo(self, fila):
        e = fila[0]
        inf, opts, fm = e.lemma.casefold(), e.options(), self.formas[id(e)]
        stem, cls = inf[:-2], plain(inf[-2:])
        dadas = "formas" in opts
        forms = [fm[k] for k in SEIS]
        if (inf in IRREGULARES or inf.endswith(BASES_IRREGULARES)) and not dadas:
            self.avisar(fila, "alta", "verbo_irregular", "verbo irregular: el generador lo conjuga como regular",
                        "añadir formas= con las seis formas")
        esperado, actual = CAMBIO.get(inf), opts.get("cambio")
        if esperado and dadas:
            if esperado in ("ie", "ue") and esperado not in plain(fm["s3"]):
                self.avisar(fila, "alta", "cambio_raiz", f"formas= no trae el cambio {esperado} en el presente",
                            "revisar formas=")
        elif esperado and actual != esperado:
            self.avisar(fila, "alta", "cambio_raiz",
                        f"cambia la raíz ({esperado}) y {'no tiene cambio=' if not actual else f'tiene cambio={actual}'}",
                        f"{'añadir' if not actual else 'poner'} cambio={esperado}")
        elif actual and not esperado and not dadas and inf not in IRREGULARES:
            self.avisar(fila, "baja", "cambio_raiz", f"cambio={actual} en un verbo que no está entre los de cambio conocido",
                        "comprobar la conjugación")
        if not dadas:
            self.ortografia(fila, inf, stem, cls, fm)
        else:
            self.coherencia_formas(fila, inf, cls, fm)
        corregidas = self.tildes(fila, inf, stem, fm, dadas) or forms
        for form in forms:
            if _es_monosilabo_con_tilde(form):
                self.avisar(fila, "alta", "ortografia_verbal", f"«{form}» es monosílabo y no lleva tilde",
                            "poner " + _formas_opcion(_sin_tilde_monosilabos(corregidas)))
        self.uso(fila, inf, e.feature)

    def ortografia(self, fila, inf, stem, cls, fm):
        sub, forms = fm["sub_s"], [fm[k] for k in SEIS]

        def mal(problema, arreglo_forms=None):
            self.avisar(fila, "alta", "ortografia_verbal", problema,
                        "añadir " + _formas_opcion(arreglo_forms) if arreglo_forms else "añadir formas= corregidas")

        def subj(nuevo):
            return forms[:2] + [nuevo, nuevo + "n"] + forms[4:]

        if cls == "ar":
            for tail, ok, fix in (("car", "que", lambda s: s[:-2] + "que"), ("gar", "gue", lambda s: s[:-1] + "ue"),
                                  ("guar", "güe", lambda s: s[:-2] + "üe"), ("zar", "ce", lambda s: s[:-2] + "ce")):
                if inf.endswith(tail) and not sub.endswith(ok):
                    mal(f"en -{tail} el subjuntivo es «…{ok}» y se genera «{sub}»", subj(fix(sub)))
            return
        if inf.endswith(("ger", "gir")) and not sub.endswith("ja"):
            mal(f"en -ger/-gir el subjuntivo lleva j y se genera «{sub}»")
        if inf.endswith("guir") and not sub.endswith("ga"):
            mal(f"en -guir el subjuntivo es «…ga» y se genera «{sub}»")
        if inf.endswith("quir") and not sub.endswith("ca"):
            mal(f"en -quir el subjuntivo es «…ca» y se genera «{sub}»", subj(sub[:-3] + "ca"))
        if inf in ("mecer", "remecer"):
            if not sub.endswith("eza"):
                mal(f"«{inf}» no lleva zc: el subjuntivo es «…eza» y se genera «{sub}»", subj(sub[:-3] + "za"))
        elif inf.endswith(("cer", "cir")):
            if stem[-2:-1] in VOCALES:
                if not sub.endswith("zca"):
                    mal(f"vocal + -cer/-cir: el subjuntivo es «…zca» y se genera «{sub}»", subj(sub[:-2] + "zca"))
            elif not sub.endswith("za"):
                mal(f"consonante + -cer/-cir: el subjuntivo es «…za» y se genera «{sub}»", subj(sub[:-3] + "za"))
        if inf.endswith(("uir", "üir")) and not inf.endswith(("guir", "quir")):
            if not (fm["s3"].endswith("uye") and sub.endswith("uya") and fm["pret_s"].endswith("uyó")):
                mal("en -uir se intercala y: «construye», «construya», «construyó»")
        if inf.endswith(("eer", "aer", "oer")) and not (fm["pret_s"].endswith("yó") and fm["pret_p"].endswith("yeron")):
            mal("vocal + -er: el pasado es «…yó», «…yeron» (leyó)")
        if stem.endswith(("ñ", "ll")) and (fm["pret_s"], fm["pret_p"]) != (stem + "ó", stem + "eron"):
            mal("tras ñ o ll se pierde la i del pasado: «gruñó», «gruñeron»", forms[:4] + [stem + "ó", stem + "eron"])

    def tildes(self, fila, inf, stem, fm, dadas):
        """Avisa si faltan las tildes del presente; devuelve las seis formas corregidas cuando sabe calcularlas."""
        s3 = fm["s3"]
        if inf.endswith("uar") and not inf.endswith(("guar", "cuar")):
            necesita, motivo = "ú", "los verbos en -uar acentúan la u: «evalúa», «continúa»"
        elif inf in HIATO_IAR:
            necesita, motivo = "í", "este verbo en -iar lleva tilde en el presente: «envía», «esquía»"
        elif inf in HIATO_RAIZ:
            necesita, motivo = "íú", "hay hiato en la raíz: «prohíbe», «reúne», «aísla»"
        else:
            if inf.endswith("iar") and inf not in IAR_SIN_TILDE and not dadas:
                self.avisar(fila, "baja", "ortografia_verbal", f"verbo en -iar sin clasificar: se conjuga «{s3}» sin tilde",
                            "comprobar si es como «estudia» (bien) o como «envía» (añadir formas=)")
            return
        if any(c in necesita for c in s3):
            return
        i = max(stem.rfind("i"), stem.rfind("u"))
        if dadas or i < 0:
            self.avisar(fila, "alta", "ortografia_verbal", f"{motivo}; se genera «{s3}»", "revisar formas=")
            return
        tildada = stem[:i] + TILDE[stem[i]] + stem[i + 1:]
        forms = [fm[k] for k in SEIS]
        fixed = _sin_tilde_monosilabos(
            [tildada + f[len(stem):] if f.startswith(stem) and k < 4 else f for k, f in enumerate(forms)])
        self.avisar(fila, "alta", "ortografia_verbal", f"{motivo}; se genera «{s3}»", "añadir " + _formas_opcion(fixed))
        return fixed

    def coherencia_formas(self, fila, inf, cls, fm):
        s3, p3, sub_s, sub_p, pret_s, pret_p = (plain(fm[k]) for k in SEIS)
        problemas = []
        if p3 != s3 + "n" and inf != "ser":
            problemas.append("el plural del presente no es el singular + n")
        if sub_p != sub_s + "n":
            problemas.append("el plural del subjuntivo no es el singular + n")
        if not pret_p.endswith("ron"):
            problemas.append("el pasado plural no acaba en -ron")
        if not (pret_s.endswith("o") or pret_s == "fue"):
            problemas.append("el pasado singular no acaba en -o/-ó")
        if inf not in ("ir", "ser", "haber") and s3[-1:] != ("a" if cls == "ar" else "e"):
            problemas.append(f"el presente de un verbo en -{cls} debería acabar en -{'a' if cls == 'ar' else 'e'}")
        if sub_s[-1:] != ("e" if cls == "ar" else "a"):
            problemas.append(f"el subjuntivo de un verbo en -{cls} debería acabar en -{'e' if cls == 'ar' else 'a'}")
        for p in problemas:
            self.avisar(fila, "media", "verbo_irregular", f"formas= poco coherente: {p}", "revisar formas=")

    def uso(self, fila, inf, feature):
        if inf in MODALES:
            self.avisar(fila, "media", "uso_verbal", "verbo modal: sin infinitivo («puede nadar») no dice nada, y la "
                        "gramática no admite infinitivos", "quitar la fila o dejarla para usos elípticos («Juan puede»)")
        if inf in IMPERSONALES:
            self.avisar(fila, "baja", "uso_verbal", "verbo impersonal: en su uso normal no lleva sujeto («llueve»), "
                        "pero la gramática siempre pide uno", "quitar la fila o mantenerla para usos figurados", True)
        if inf in USO:
            esperado, confianza, ejemplo = USO[inf]
            if feature != esperado:
                self.avisar(fila, confianza, "uso_verbal", f"uso {feature}, pero lo normal es {esperado}: {ejemplo}",
                            f"cambiar el uso {feature} → {esperado}")

    # -- nombres propios --
    def nombre_propio(self, fila):
        e = fila[0]
        name = e.lemma
        if not (name[:1].isupper() and name[1:] == name[1:].lower()):
            self.avisar(fila, "alta", "nombre_propio", "un nombre propio se escribe con mayúscula inicial y el resto en minúscula",
                        f"escribir «{name[:1].upper() + name[1:].lower()}»")
        key = plain(name).casefold()
        if key in NOMBRES_CON_TILDE and name != NOMBRES_CON_TILDE[key] and plain(name) == name:
            self.avisar(fila, "alta", "nombre_propio", f"se escribe «{NOMBRES_CON_TILDE[key]}»",
                        f"escribir «{NOMBRES_CON_TILDE[key]}»")
        if key in NOMBRES_TILDE_DUDOSA and name != NOMBRES_TILDE_DUDOSA[key]:
            self.avisar(fila, "baja", "nombre_propio", f"la ortografía académica escribe «{NOMBRES_TILDE_DUDOSA[key]}» "
                        "(llana acabada en -m), aunque muchas personas lo escriben sin tilde",
                        f"escribir «{NOMBRES_TILDE_DUDOSA[key]}» o dejarlo como está")
        if key.endswith("a") and e.feature == "M" and name not in NOMBRES_M_EN_A:
            self.avisar(fila, "media", "nombre_propio", "nombre masculino acabado en -a", "comprobar el género")
        if key.endswith("o") and e.feature == "F" and name not in NOMBRES_F_EN_O:
            self.avisar(fila, "media", "nombre_propio", "nombre femenino acabado en -o", "comprobar el género")

    # -- palabras funcionales y aula --
    def cerrada_y_aula(self, fila):
        e = fila[0]
        w = e.lemma.casefold()
        if e.category != "NP" and w in CERRADAS and (w, e.category) not in HOMOGRAFOS:
            self.avisar(fila, "alta", "palabra_cerrada", "palabra funcional (artículo, preposición, pronombre, cuantificador, "
                        "ser/estar/haber…): no es un predicado de la lista abierta", "quitar la fila")
        if w in VULGARES:
            self.avisar(fila, "alta", "aula", "palabra vulgar", "quitar la fila")
        elif w in DOBLE_SENTIDO:
            self.avisar(fila, "baja", "aula", DOBLE_SENTIDO[w], "decisión docente: mantener o quitar la fila")

    # -- relaciones entre entradas --
    def duplicados(self, filas):
        grupos = defaultdict(list)
        for fila in filas:
            grupos[(fila[0].lemma.casefold(), fila[0].category)].append(fila)
        for (_, cat), filas_grupo in sorted(grupos.items()):
            for fila in filas_grupo[1:]:
                primera = filas_grupo[0]
                igual = (fila[0].feature, fila[0].extra) == (primera[0].feature, primera[0].extra)
                self.avisar(fila, "alta", "duplicado",
                            f"{'repite' if igual else 'contradice'} la entrada de {_donde(primera)}"
                            + ("" if igual else f" ({primera[0].feature} {primera[0].extra}".rstrip() + ")"),
                            "dejar una sola fila")
        simbolos = defaultdict(set)
        for fila in filas:
            e = fila[0]
            simbolos[(e.symbol, e.category)].add(e.lemma)
        for fila in filas:
            e = fila[0]
            otros = sorted(simbolos[(e.symbol, e.category)] - {e.lemma})
            if otros:
                self.avisar(fila, "media", "duplicado", f"comparte el símbolo {e.symbol} con «{', '.join(otros)}»",
                            "quitar una de las dos o distinguirlas")
        primera = {}                         # (categoría, forma) → primera fila que la produce: su símbolo es el que vale
        derivadas = defaultdict(set)         # (categoría, forma que no es lema) → lemas que la producen
        for fila in filas:
            e = fila[0]
            tapadas = defaultdict(set)       # fila previa → formas suyas que esta entrada también produce
            for tag, values in sorted(e.forms().items()):
                for form in values:
                    previa = primera.setdefault((e.category, form), fila)
                    if previa[0].symbol != e.symbol:
                        tapadas[id(previa[0])].add((form, previa))
                    if tag not in ("N_MS", "N_FS", "Adj_MS") and e.category in ("N", "ADJ"):
                        derivadas[(e.category, form)].add(e.lemma)
            for pares in tapadas.values():
                previa = next(iter(pares))[1]
                lista = "», «".join(sorted(form for form, _ in pares))
                verbo = "sale" if len(pares) == 1 else "salen"
                self.avisar(fila, "media", "duplicado", f"«{lista}» ya {verbo} de «{previa[0].lemma}» ({_donde(previa)}) y el "
                            f"analizador usará el símbolo {previa[0].symbol}", "quitar una de las dos o distinguirlas")
        for fila in filas:
            e = fila[0]
            fuentes = sorted(derivadas.get((e.category, e.lemma.casefold()), set()) - {e.lemma})
            if fuentes:
                self.avisar(fila, "media", "duplicado", f"parece una forma de «{', '.join(fuentes)}», no un lema",
                            "quitar la fila")
        homonimos = defaultdict(set)
        for fila in filas:
            homonimos[fila[0].lemma.casefold()].add(fila[0].category)
        for fila in filas:
            e = fila[0]
            w = e.lemma.casefold()
            if e.category == "N" and w in HOMONIMOS and "ADJ" in homonimos[w]:
                self.avisar(fila, "baja", "simbolo", f"el sustantivo y el adjetivo «{w}» ({HOMONIMOS[w]}) dan el mismo "
                            f"predicado {e.symbol}", "nada obligatorio; si molesta, quitar una de las dos entradas", True)

    def choques_con_la_gramatica(self, filas):
        comunes = defaultdict(set)
        for fila in filas:
            e = fila[0]
            if e.category != "NP":
                for values in e.forms().values():
                    for form in values:
                        comunes[form].add(f"{e.lemma} ({e.category})")
        for fila in filas:
            e = fila[0]
            forms = e.forms()
            fm = self.formas[id(e)]
            tapadas, cerradas = defaultdict(set), []
            for tag, values in sorted(forms.items()):
                for form in values:
                    if form in self.cerradas_gramatica:
                        cerradas.append((tag, form))
                    elif form in self.gramatica and tag not in self.gramatica[form]:
                        tapadas[form].add(tag)
            for form in sorted({f for _, f in cerradas} if e.category != "NP" else ()):   # NP: lo avisa abajo
                heads = ", ".join(sorted(self.gramatica[form]))
                presente = e.category != "V" or form in (fm.get("s3"), fm.get("p3"))
                self.avisar(fila, "media" if presente else "baja", "gramatica",
                            f"«{form}» ya es palabra de la gramática ({heads}) y esa forma de «{e.lemma}» no se puede usar",
                            "quitar la fila o aceptar el hueco" if presente else "nada que hacer en el léxico; es un homógrafo", presente)
            if tapadas:
                detalle = "; ".join(f"{f}: {', '.join(sorted(t))}" for f, t in sorted(tapadas.items()))
                self.avisar(fila, "baja", "gramatica", f"la gramática ya trae estas formas con otra categoría y manda ella; "
                            f"se pierde {detalle}", "nada en el léxico; para usarlas habría que tocar spanish_grammar.txt "
                            "(de esas palabras dependen los 51 casos)", False)
            if e.category == "NP":
                w = e.lemma.casefold()
                if w in self.cerradas_gramatica:
                    self.avisar(fila, "alta", "nombre_propio", f"«{w}» es una palabra de la gramática", "quitar la fila")
                elif w in comunes:
                    self.avisar(fila, "media", "nombre_propio", f"en minúsculas coincide con {', '.join(sorted(comunes[w]))}; "
                                f"el analizador no distingue mayúsculas y añade lecturas como «x = {plain(w)}»",
                                "quitar el nombre o aceptar la lectura extra")


def auditar(filas, ignoradas=()):
    """Lista ordenada de avisos para `filas` = [(Entry, archivo, línea, columnas)]."""
    return Auditoria(filas, ignoradas).ejecutar()


def auditar_entradas(entradas):
    """Atajo para pruebas: audita objetos `lexicon.Entry` sueltos."""
    return auditar([(e, "", i, 4) for i, e in enumerate(entradas, 1)])


# --- salida -------------------------------------------------------------------------------------

def recuento(avisos):
    c = Counter((a.regla, a.confianza) for a in avisos)
    return {regla: tuple(c[(regla, conf)] for conf in CONFIANZAS) for regla in REGLAS}


def informe_texto(avisos, filas, rutas):
    cats = Counter(f[0].category for f in filas)
    total = Counter(a.confianza for a in avisos)
    out = [f"Auditoría del léxico: {', '.join(_nombre(r) for r in rutas)}",
           f"{len(filas)} entradas: " + ", ".join(f"{cats[c]} {c}" for c in lexicon.CATEGORIES),
           "Avisos: " + " · ".join(f"{total[c]} {c}" for c in CONFIANZAS), "",
           f"{'Regla':<18}  alta  media  baja"]
    for regla, (a, m, b) in recuento(avisos).items():
        out.append(f"{regla:<18}  {a:>4}  {m:>5}  {b:>4}")
    for conf in CONFIANZAS:
        grupo = [a for a in avisos if a.confianza == conf]
        if not grupo:
            continue
        out += ["", f"== {conf} ({len(grupo)}) =="]
        for a in grupo:
            donde = f"{a.archivo}:{a.linea}" if a.archivo else f"#{a.linea}"
            out += [f"[{a.regla}] {a.lema} ({a.categoria}) · {donde}",
                    f"    formas:   {a.formas}", f"    problema: {a.problema}",
                    f"    arreglo:  {a.arreglo}{'' if a.corregible else '  (no se arregla editando el TSV)'}"]
    out += ["", "Esto es una ayuda: la revisión humana del léxico sigue haciendo falta."]
    return "\n".join(out)


def informe_markdown(avisos):
    cell = lambda s: str(s).replace("|", "\\|")
    out = ["| # | Confianza | Regla | Lema | Formas generadas | Problema | Arreglo sugerido | Visto bueno |",
           "|---|---|---|---|---|---|---|---|"]
    for i, a in enumerate(avisos, 1):
        arreglo = a.arreglo + ("" if a.corregible else " *(no se arregla en el TSV)*")
        out.append(f"| {i} | {a.confianza} | {a.regla} | **{cell(a.lema)}** ({a.categoria}, l. {a.linea}) | "
                   f"{cell(a.formas)} | {cell(a.problema)} | {cell(arreglo)} | [ ] |")
    return "\n".join(out)


def informe_tsv(avisos):
    out = ["confianza\tregla\tlema\tcategoria\tarchivo\tlinea\tformas\tproblema\tarreglo\tcorregible_en_tsv"]
    for a in avisos:
        out.append("\t".join(map(str, (a.confianza, a.regla, a.lema, a.categoria, a.archivo, a.linea, a.formas,
                                       a.problema, a.arreglo, "sí" if a.corregible else "no"))))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Señala errores probables del léxico del español.")
    ap.add_argument("archivos", nargs="*", type=Path, help="TSV a revisar juntos (por defecto, src/logos/lexicon.tsv)")
    ap.add_argument("--confianza", default="alta,media,baja",
                    help="confianzas a mostrar, separadas por comas (p. ej. «alta» o «media,baja»)")
    ap.add_argument("--formato", choices=("texto", "markdown", "tsv"), default="texto")
    args = ap.parse_args(argv)
    niveles = [c.strip() for c in args.confianza.split(",") if c.strip()]
    if not niveles or any(c not in CONFIANZAS for c in niveles):
        ap.error("--confianza admite alta, media y baja")
    rutas = args.archivos or [lexicon.BASE]
    filas, ignoradas = cargar(rutas)
    avisos = [a for a in auditar(filas, ignoradas) if a.confianza in niveles]
    texto = {"texto": lambda: informe_texto(avisos, filas, rutas), "markdown": lambda: informe_markdown(avisos),
             "tsv": lambda: informe_tsv(avisos)}[args.formato]()
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()

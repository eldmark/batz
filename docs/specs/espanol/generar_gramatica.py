"""Genera la gramática v0 del español controlado expandiendo rasgos g∈{M,F}, n∈{S,P}."""
G, N = "MF", "SP"
L = []
def r(h, *alts): L.append(f"{h} -> " + " | ".join(alts))

# Léxico (forma normalizada -> categoría con rasgos)
LEX = {
 "NProp_M": "juan pedro", "NProp_F": "maría ana",
 "N_MS": "estudiante libro profesor gato joven", "N_MP": "estudiantes libros profesores gatos jóvenes",
 "N_FS": "estudiante profesora persona joven", "N_FP": "estudiantes profesoras personas jóvenes",
 "Adj_MS": "inteligente alto rojo joven", "Adj_MP": "inteligentes altos rojos jóvenes",
 "Adj_FS": "inteligente alta roja joven", "Adj_FP": "inteligentes altas rojas jóvenes",
 "VI_S": "lee estudia aprueba escribe leyó", "VI_P": "leen estudian aprueban escriben leyeron",
 "VIsub_S": "lea estudie apruebe escriba", "VIsub_P": "lean estudien aprueben escriban",
 "VT_S": "lee ama conoce ve leyó", "VT_P": "leen aman conocen ven leyeron",
 "VTsub_S": "lea ame conozca vea", "VTsub_P": "lean amen conozcan vean",
 "Cop_S": "es", "Cop_P": "son",
 "DetU_MS": "todo cada", "DetU_FS": "toda cada", "DetU_MP": "todos los", "DetU_FP": "todas las",
 "DetE_MS": "algún un", "DetE_FS": "alguna una", "DetE_MP": "algunos", "DetE_FP": "algunas",
 "DetNo_MS": "ningún", "DetNo_FS": "ninguna", "Def_MP": "los", "Def_FP": "las",
 "Indef_MS": "un", "Indef_FS": "una",
 # Numerales (v1). "dos" a secas es ambiguo (al menos / exactamente): lo resuelve la semántica preguntando.
 "Num": "dos tres cuatro cinco 2 3 4 5",
}
for cat, words in LEX.items():
    if cat in ("DetU_MP", "DetU_FP"):
        r(cat, words)              # multipalabra: "todos los"
    else:
        r(cat, *words.split())
for h, w in {"Si": "si", "Ent": "entonces", "Coma": ",", "Y": "y", "Ox": "o", "No": "no",
             "Que": "que", "A": "a", "Se": "se", "Hay": "hay | existe", "Solo": "solo",
             "Alguien": "alguien", "Nadie": "nadie", "SoloSi": "solo si", "Ssi": "si y solo si",
             "NoEsCierto": "no es cierto que", "Obien": "o bien",
             "AlMenos": "al menos", "Exactamente": "exactamente", "ALoSumo": "a lo sumo"}.items():
    r(h, w)

r("S", "O")
r("O", "Si O Ent O", "Si O Coma Ent O", "Si O Coma O", "O Si O", "O SoloSi O", "O Ssi O",
  "O Y O", "O Ox O", "NoEsCierto O", "Obien O Obien O", "Hay SNex", "No Hay SNnegAny",
  "Hay Alguien Rel_MS", "No Hay Nom_MP", "No Hay Nom_FP")
for g in G:
    for n in N:
        gn = g + n
        r("O", f"SN_{gn} SV_{gn}", f"Solo Def_{g}P Nom_{g}P SV_{g}P" if n == "P" else f"Solo NProp_{g} SV_{gn}")
        r(f"Nom_{gn}", f"N_{gn}", f"N_{gn} Adj_{gn}", f"N_{gn} Rel_{gn}", f"N_{gn} Adj_{gn} Rel_{gn}")
        r(f"Rel_{gn}", f"Que SV_{gn}", f"Que SVsub_{gn}")
        r(f"SN_{gn}", f"DetU_{gn} Nom_{gn}", f"DetE_{gn} Nom_{gn}", f"DetNum_{gn} Nom_{gn}")
        r("SNex", f"DetNum_{gn} Nom_{gn}")
        r(f"Pred_{gn}", f"Adj_{gn}", f"N_{gn}", f"Pred_{gn} Y Pred_{gn}")
        svpos = [f"VI_{n}", f"VT_{n} Obj", f"Se VT_{n}", f"Cop_{n} Pred_{gn}"]
        if n == "S":
            svpos += [f"Cop_S Indef_{g}S N_{g}S", "Cop_S NProp_M", "Cop_S NProp_F"]
        r(f"SVpos_{gn}", *svpos)
        r(f"SV_{gn}", f"SVpos_{gn}", f"No SVpos_{gn}", f"No VT_{n} ObjNeg",
          f"SV_{gn} Y SV_{gn}", f"SV_{gn} Ox SV_{gn}")
        r(f"SVsub_{gn}", f"VIsub_{n}", f"VTsub_{n} Obj", f"No VIsub_{n}", f"No VTsub_{n} ObjNeg")
        r("SNex", f"DetE_{gn} Nom_{gn}", f"Nom_{g}P")
        r("SNany", f"SN_{gn}")
    r(f"SN_{g}S", f"NProp_{g}")
    r(f"SNneg_{g}S", f"DetNo_{g}S Nom_{g}S")
    r("O", f"SNneg_{g}S SVpos_{g}S")
    r("SNnegAny", f"SNneg_{g}S")
# Determinantes numéricos (v1): singular con un/una, plural con Num.
for g in G:
    r(f"DetNum_{g}S", f"AlMenos Indef_{g}S", f"Exactamente Indef_{g}S", f"ALoSumo Indef_{g}S")
    r(f"DetNum_{g}P", "Num", "AlMenos Num", "Exactamente Num", "ALoSumo Num")
r("SN_MS", "Alguien", "Alguien Rel_MS")
r("SNneg_MS", "Nadie", "Nadie Rel_MS")
r("Obj", "SNany", "A SNany")
r("ObjNeg", "SNnegAny", "A SNnegAny")
# Coordinación de nombres propios (lectura distributiva)
r("NPAny", "NProp_M", "NProp_F")
r("ListF", "NProp_F Y NProp_F", "NProp_F Coma ListF")
r("ListM", "NProp_M Y NPAny", "NProp_F Y NProp_M", "NProp_M Coma ListAny", "NProp_F Coma ListM")
r("ListAny", "ListM", "ListF")
r("SN_MP", "ListM"); r("SN_FP", "ListF")
# Sujeto disyuntivo (v1): "Juan o María lee/leen" -> L(j) ∨ L(m); el verbo admite singular o plural.
r("OListF", "NProp_F Ox NProp_F", "NProp_F Coma OListF")
r("OListM", "NProp_M Ox NPAny", "NProp_F Ox NProp_M", "NProp_M Coma OListAny", "NProp_F Coma OListM")
r("OListAny", "OListM", "OListF")
for n in N:
    r(f"SN_M{n}", "OListM"); r(f"SN_F{n}", "OListF")
print("\n".join(L))

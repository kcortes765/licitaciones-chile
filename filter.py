import json
from pathlib import Path

with open(Path(__file__).parent / "licitaciones_hoy.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Total licitaciones hoy:", data["Cantidad"])
print()

keywords = ["obra", "construc", "infraestructura", "edifici", "paviment", "vialidad",
            "puente", "estructur", "civil", "mantenim", "reparaci", "conservaci",
            "habilitaci", "mejoramiento", "reposici", "demolici", "instalaci"]

obras = []
for lic in data["Listado"]:
    nombre = lic["Nombre"].lower()
    if any(kw in nombre for kw in keywords):
        obras.append(lic)

print("Licitaciones obras/construccion:", len(obras))
print()

activas = [o for o in obras if o["CodigoEstado"] == 5]
cerradas = [o for o in obras if o["CodigoEstado"] == 6]
adjudicadas = [o for o in obras if o["CodigoEstado"] == 8]

print("  Publicadas (abiertas):", len(activas))
print("  Cerradas:", len(cerradas))
print("  Adjudicadas:", len(adjudicadas))
print()

print("=== LICITACIONES DE OBRAS ABIERTAS ===")
for o in activas:
    print("  [%s] %s" % (o["CodigoExterno"], o["Nombre"]))
    print("    Cierre:", o["FechaCierre"])
    print()

print("=== LICITACIONES DE OBRAS CERRADAS HOY (primeras 10) ===")
for o in cerradas[:10]:
    print("  [%s] %s" % (o["CodigoExterno"], o["Nombre"]))
    print("    Cierre:", o["FechaCierre"])
    print()

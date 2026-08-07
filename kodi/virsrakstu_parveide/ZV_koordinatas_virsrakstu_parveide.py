import csv
import sys
from pathlib import Path

import pandas as pd


# ==========================================================
# KONFIGURĀCIJA
# ==========================================================

projekts = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\DARIJUMU KOORDINATAS\DARIJUMI AR ZV"
)

sakuma_mape = projekts / "SAKOTNEJAS DATNES"
publ_mape = projekts / "DATNES PUBLICĒŠANAI"

publ_mape.mkdir(parents=True, exist_ok=True)

print("📁 Projekts :", projekts)
print("📥 Ievade  :", sakuma_mape)
print("📤 Izvade  :", publ_mape)


# ==========================================================
# KOLONNU SHĒMA
# ==========================================================

jaunie_virsraksti = [
    "ParCadNr",
    "DeaId",
    "Valz1",
    "Valz2",
    "Valz3",
    "Valz4",
    "Valz5",
    "KoordX",
    "KoordY",
    "DdN",
    "DdE",
]


# ==========================================================
# CSV APSTRĀDE
# ==========================================================

csv_faili = list(sakuma_mape.glob("*.csv"))

if len(csv_faili) == 0:
    print("❌ Mapē 'SAKOTNEJAS DATNES' nav atrasts neviens CSV fails.")
    sys.exit(1)

if len(csv_faili) > 1:
    print("❌ Mapē atrasti vairāki CSV faili. Atstāj tikai vienu apstrādājamo failu.")
    for fails in csv_faili:
        print(f"   - {fails.name}")
    sys.exit(1)

ievades_fails = csv_faili[0]
izvades_fails = publ_mape / ievades_fails.name

print(f"\n📂 Apstrādāju: {ievades_fails.name}")

try:
    df = pd.read_csv(
        ievades_fails,
        encoding="utf-8",
        dtype=str,
        sep=";"
    )

    print("✅ Dati nolasīti.")

except Exception as e:
    print(f"❌ Neizdevās nolasīt CSV failu:\n{e}")
    sys.exit(1)

try:
    if len(df.columns) != len(jaunie_virsraksti):
        raise ValueError(
            f"Kolonnu skaits nesakrīt: "
            f"failā={len(df.columns)} "
            f"vs shēmā={len(jaunie_virsraksti)}"
        )

    df.columns = jaunie_virsraksti

    df.to_csv(
        izvades_fails,
        index=False,
        encoding="utf-8-sig",
        sep=",",
        quoting=csv.QUOTE_ALL
    )

    print(f"✅ Pārveidotais fails saglabāts:")
    print(f"   {izvades_fails}")

except Exception as e:
    print(f"❌ Kļūda saglabājot failu:\n{e}")
    sys.exit(1)


print("\n==============================")
print("KOPSAVILKUMS")
print("==============================")
print("✅ CSV veiksmīgi apstrādāts.")
print(f"📄 Fails : {ievades_fails.name}")
print(f"📂 Saglabāts : {izvades_fails}")

sys.exit(0)
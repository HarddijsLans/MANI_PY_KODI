import csv
import sys
from pathlib import Path

import pandas as pd


# ==========================================================
# KONFIGURĀCIJA
# ==========================================================

projekts = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\VIRSRAKSTU PARVEIDE\DARIJUMI AR ZVB"
)

sakuma_mape = projekts / "SAKOTNEJAS DATNES"
publ_mape = projekts / "DATNES PUBLICESANAI"

publ_mape.mkdir(parents=True, exist_ok=True)

print("📁 Projekts :", projekts)
print("📥 Ievade   :", sakuma_mape)
print("📤 Izvade   :", publ_mape)


# ==========================================================
# KOLONNU SHĒMA
# ==========================================================

sakotnejie_virsraksti = [
    "BUICADNR",
    "DEAID",
    "KoordX",
    "KoordY",
    "DdN",
    "DdE",
]

jaunie_virsraksti = [
    "BuiCadNr",
    "DeaId",
    "KoordX",
    "KoordY",
    "DdN",
    "DdE",
]


# ==========================================================
# CSV FAILA MEKLĒŠANA
# ==========================================================

csv_faili = list(sakuma_mape.glob("*.csv"))

if len(csv_faili) == 0:
    print("❌ Mapē 'SAKOTNEJAS DATNES' nav atrasts neviens CSV fails.")
    sys.exit(1)

if len(csv_faili) > 1:
    print(
        "❌ Mapē atrasti vairāki CSV faili. "
        "Atstāj tikai vienu apstrādājamo failu."
    )

    for fails in csv_faili:
        print(f"   - {fails.name}")

    sys.exit(1)


ievades_fails = csv_faili[0]
izvades_fails = publ_mape / ievades_fails.name

print(f"\n📂 Apstrādāju: {ievades_fails.name}")


# ==========================================================
# DATNES NOLASĪŠANA
# ==========================================================

try:
    df = pd.read_csv(
        ievades_fails,
        encoding="utf-8",
        dtype=str,
        sep=";",
        keep_default_na=False
    )

    print("✅ Dati nolasīti.")

except Exception as e:
    print(f"❌ Neizdevās nolasīt CSV failu:\n{e}")
    sys.exit(1)


# ==========================================================
# VIRSRakstu SAKĀRTOŠANA
# ==========================================================

# Noņemam iespējamās liekās atstarpes no kolonnu nosaukumiem
df.columns = df.columns.str.strip()


# ==========================================================
# STRUKTŪRAS PĀRBAUDE
# ==========================================================

try:
    if len(df.columns) != len(sakotnejie_virsraksti):
        raise ValueError(
            f"Kolonnu skaits nesakrīt: "
            f"failā={len(df.columns)} "
            f"vs paredzēts={len(sakotnejie_virsraksti)}"
        )

    faktiskie_virsraksti = list(df.columns)

    if faktiskie_virsraksti != sakotnejie_virsraksti:
        raise ValueError(
            "Sākotnējie kolonnu nosaukumi neatbilst paredzētajai shēmai.\n\n"
            f"Failā:     {faktiskie_virsraksti}\n"
            f"Paredzēts: {sakotnejie_virsraksti}"
        )

    print("✅ Kolonnu struktūra pārbaudīta.")

except Exception as e:
    print(f"❌ Nederīga CSV struktūra:\n{e}")
    sys.exit(1)


# ==========================================================
# KOLONNU NOSAUKUMU MAIŅA
# ==========================================================

df.columns = jaunie_virsraksti

print("✅ Kolonnu nosaukumi pārveidoti.")


# ==========================================================
# TUKŠO VĒRTĪBU KONTROLE
# ==========================================================

tuksas_vertibas = {}

for kolonna in df.columns:
    skaits = (df[kolonna].astype(str).str.strip() == "").sum()
    tuksas_vertibas[kolonna] = skaits


# ==========================================================
# SAGLABĀŠANA
# ==========================================================

try:
    df.to_csv(
        izvades_fails,
        index=False,
        encoding="utf-8-sig",
        sep=",",
        quoting=csv.QUOTE_ALL
    )

    print("✅ Pārveidotais fails saglabāts.")

except Exception as e:
    print(f"❌ Neizdevās saglabāt CSV failu:\n{e}")
    sys.exit(1)


# ==========================================================
# KOPSAVILKUMS
# ==========================================================

print("\n==============================")
print("KOPSAVILKUMS")
print("==============================")

print("✅ CSV veiksmīgi apstrādāts.")
print(f"📄 Fails       : {ievades_fails.name}")
print(f"📊 Datu rindas : {len(df)}")
print(f"📋 Kolonnas    : {len(df.columns)}")

print("\nTUKŠĀS VĒRTĪBAS")

for kolonna, skaits in tuksas_vertibas.items():
    print(f"{kolonna:<10}: {skaits}")

print(f"\n📂 Saglabāts:")
print(f"   {izvades_fails}")

sys.exit(0)
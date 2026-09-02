import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# LADP publicējamās ZV koordinātas
# Versija: 1.0
# Funkcionalitāte:
# - ievades CSV datņu atrašana
# - ievades datnes nosaukuma validācija
# - prefiksa pārbaude, neņemot vērā lielos/mazos burtus
# - perioda sākuma un beigu datumu validācija
# - pārbaude, ka sākuma datums nav vēlāks par beigu datumu
# - pārbaude, ka beigu gada un sākuma gada starpība ir tieši 10
# - no vairākām derīgām datnēm izvēlas datni ar jaunāko beigu datumu
# - CSV ielāde ar semikolu kā atdalītāju
# - UTF-8-SIG kodējuma izmantošana CSV ielādei
# - datu ielāde teksta formātā
# - sākotnējo kolonnu nosaukumu normalizācija
# - kolonnu skaita validācija
# - kolonnu nosaukumu un stingrās secības validācija
# - kolonnu nosaukumu pārveidošana
# - publicējamā CSV faila saglabāšana
# - izvades datnes nosaukumam pievieno "_parveidota"
# - komata izmantošana kā izvades CSV atdalītājam
# - UTF-8-SIG kodējuma izmantošana izvades failam
# - visu CSV lauku saglabāšana pēdiņās
# - apstrādes kopsavilkuma izvadīšana konsolē
# ============================================================


# ============================================================
# KONFIGURĀCIJA
# ============================================================

projekts = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\VIRSRAKSTU PARVEIDE\DARIJUMI AR ZV"
)

sakuma_mape = projekts / "SAKOTNEJAS DATNES"
publ_mape = projekts / "DATNES PUBLICESANAI"

publ_mape.mkdir(parents=True, exist_ok=True)

print("📁 Projekts :", projekts)
print("📥 Ievade   :", sakuma_mape)
print("📤 Izvade   :", publ_mape)


# ============================================================
# KOLONNU SHĒMA
# ============================================================

sakotnejie_virsraksti = [
    "PARCADNR",
    "DEAID",
    "VALZ_NAME1",
    "VALZ_NAME2",
    "VALZ_NAME3",
    "VALZ_NAME4",
    "VALZ_NAME5",
    "KoordX",
    "KoordY",
    "DdN",
    "DdE",
]

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


# ============================================================
# DATNES NOSAUKUMA NOTEIKUMI
# ============================================================

prefikss = "ZV_vertibu_zonas_un_koordinatas_"

nosaukuma_paraugs = re.compile(
    rf"^{re.escape(prefikss)}(\d{{8}})-(\d{{8}})\.csv$",
    re.IGNORECASE
)


# ============================================================
# IEVADES MAPES PĀRBAUDE
# ============================================================

if not sakuma_mape.exists():
    print(
        "\n❌ Ievades mape neeksistē:\n"
        f"   {sakuma_mape}"
    )
    sys.exit(1)

if not sakuma_mape.is_dir():
    print(
        "\n❌ Norādītais ievades ceļš nav mape:\n"
        f"   {sakuma_mape}"
    )
    sys.exit(1)


# ============================================================
# IEVADES CSV DATŅU ATRAŠANA UN NOSAUKUMA VALIDĀCIJA
# ============================================================

derigas_datnes = []

for fails in sakuma_mape.iterdir():

    if not fails.is_file():
        continue

    if fails.suffix.lower() != ".csv":
        continue

    sakritiba = nosaukuma_paraugs.fullmatch(fails.name)

    if sakritiba is None:
        continue

    sakuma_datums_teksts = sakritiba.group(1)
    beigu_datums_teksts = sakritiba.group(2)

    try:
        sakuma_datums = datetime.strptime(
            sakuma_datums_teksts,
            "%d%m%Y"
        ).date()

        beigu_datums = datetime.strptime(
            beigu_datums_teksts,
            "%d%m%Y"
        ).date()

    except ValueError:
        continue

    if sakuma_datums > beigu_datums:
        continue

    if beigu_datums.year - sakuma_datums.year != 10:
        continue

    derigas_datnes.append(
        (
            fails,
            sakuma_datums,
            beigu_datums
        )
    )


# ============================================================
# DERĪGĀS DATNES IZVĒLE
# ============================================================

if len(derigas_datnes) == 0:
    print(
        "\n❌ Mapē 'SAKOTNEJAS DATNES' nav atrasta neviena "
        "prasībām atbilstoša CSV datne."
    )

    print(
        "\nParedzētā nosaukuma struktūra:"
        "\nZV_vertibu_zonas_un_koordinatas_DDMMYYYY-DDMMYYYY.csv"
    )

    sys.exit(1)


derigas_datnes.sort(
    key=lambda x: x[2],
    reverse=True
)

ievades_fails = derigas_datnes[0][0]
sakuma_datums = derigas_datnes[0][1]
beigu_datums = derigas_datnes[0][2]


# ============================================================
# IZVADES DATNES NOSAUKUMA IZVEIDE
# ============================================================

izvades_nosaukums = (
    f"{ievades_fails.stem}_parveidota.csv"
)

izvades_fails = publ_mape / izvades_nosaukums


print(f"\n📂 Apstrādāju: {ievades_fails.name}")
print(
    "📅 Periods     : "
    f"{sakuma_datums.strftime('%d.%m.%Y')} - "
    f"{beigu_datums.strftime('%d.%m.%Y')}"
)

if len(derigas_datnes) > 1:
    print(
        f"ℹ️ Atrastas {len(derigas_datnes)} derīgas datnes. "
        "Izvēlēta datne ar jaunāko perioda beigu datumu."
    )


# ============================================================
# CSV DATNES NOLASĪŠANA
# ============================================================

try:
    df = pd.read_csv(
        ievades_fails,
        encoding="utf-8-sig",
        dtype=str,
        sep=";",
        keep_default_na=False
    )

    print("✅ Dati nolasīti.")

except Exception as e:
    print(f"❌ Neizdevās nolasīt CSV datni:\n{e}")
    sys.exit(1)


# ============================================================
# KOLONNU NOSAUKUMU NORMALIZĀCIJA
# ============================================================

df.columns = df.columns.str.strip()


# ============================================================
# STRUKTŪRAS VALIDĀCIJA
# ============================================================

faktiskie_virsraksti = list(df.columns)

if len(faktiskie_virsraksti) != len(sakotnejie_virsraksti):
    print(
        "\n❌ Nederīga CSV struktūra:"
        "\nKolonnu skaits nesakrīt."
    )

    print(f"   Failā     : {len(faktiskie_virsraksti)}")
    print(f"   Paredzēts : {len(sakotnejie_virsraksti)}")

    sys.exit(1)


if faktiskie_virsraksti != sakotnejie_virsraksti:
    print(
        "\n❌ Nederīga CSV struktūra:"
        "\nKolonnu nosaukumi vai to secība neatbilst "
        "paredzētajai shēmai."
    )

    print("\nFailā:")
    print(faktiskie_virsraksti)

    print("\nParedzēts:")
    print(sakotnejie_virsraksti)

    sys.exit(1)


print("✅ Kolonnu struktūra pārbaudīta.")


# ============================================================
# KOLONNU NOSAUKUMU PĀRVEIDOŠANA
# ============================================================

df.columns = jaunie_virsraksti

print("✅ Kolonnu nosaukumi pārveidoti.")


# ============================================================
# PUBLICĒJAMĀ CSV FAILA SAGLABĀŠANA
# ============================================================

try:
    df.to_csv(
        izvades_fails,
        index=False,
        encoding="utf-8-sig",
        sep=",",
        quoting=csv.QUOTE_ALL
    )

    print("✅ Pārveidotā datne saglabāta.")

except Exception as e:
    print(f"❌ Neizdevās saglabāt CSV datni:\n{e}")
    sys.exit(1)


# ============================================================
# KOPSAVILKUMS
# ============================================================

print("\n========================================")
print("KOPSAVILKUMS")
print("========================================")

print("✅ CSV veiksmīgi apstrādāts.")
print(f"📄 Ievades datne : {ievades_fails.name}")
print(f"📄 Izvades datne : {izvades_fails.name}")
print(f"📊 Datu rindas   : {len(df)}")
print(f"📋 Kolonnas      : {len(df.columns)}")

print("\n📂 Saglabāts:")
print(f"   {izvades_fails}")

print("\n✅ Darbs pabeigts.")

sys.exit(0)
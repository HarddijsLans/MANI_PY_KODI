import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import openpyxl


# ============================================================
# LADP publicējamās ZVB koordinātas
# Versija: 1.2
# Funkcionalitāte:
# - ievades CSV faila atrašana
# - pārbaude, ka ievades mapē ir tieši viens CSV fails
# - ievades faila nosaukuma validācija
# - prefiksa ZVB_koordinatas_ validācija,
#   neņemot vērā lielos/mazos burtus
# - datumu formāta DDMMYYYY-DDMMYYYY validācija faila nosaukumā
# - abu datumu kalendārā derīguma validācija
# - sākuma un beigu datuma secības validācija
# - pārbaude, ka beigu gada un sākuma gada starpība ir 10 gadi
# - CSV faila ielāde ar semikolu kā atdalītāju
# - UTF-8-SIG kodējuma izmantošana CSV ielādei
# - datu ielāde teksta formātā
# - sākotnējo kolonnu nosaukumu normalizācija
# - kolonnu skaita validācija
# - kolonnu nosaukumu un secības validācija
# - kolonnu nosaukumu pārveidošana:
#     BUICADNR -> BuiCadNr
#     DEAID    -> DeaId
#     KoordX   -> KoordX
#     KoordY   -> KoordY
#     DdN      -> DdN
#     DdE      -> DdE
# - tukšo vērtību uzskaite
# - sufiksa _parveidota pievienošana gala datnes nosaukumam
# - publicējamā CSV faila saglabāšana
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
    r"\VIRSRAKSTU PARVEIDE\DARIJUMI AR ZVB"
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


# ============================================================
# IEVADES CSV FAILA ATRAŠANA
# ============================================================

if not sakuma_mape.exists():
    print("❌ Mape 'SAKOTNEJAS DATNES' neeksistē.")
    print(f"   {sakuma_mape}")
    sys.exit(1)

csv_faili = [
    fails
    for fails in sakuma_mape.iterdir()
    if fails.is_file() and fails.suffix == ".csv"
]

if len(csv_faili) == 0:
    print(
        "❌ Mapē 'SAKOTNEJAS DATNES' "
        "nav atrasts neviens .csv fails."
    )
    sys.exit(1)

if len(csv_faili) > 1:
    print(
        "❌ Mapē 'SAKOTNEJAS DATNES' "
        "atrasti vairāki CSV faili."
    )
    print("   Atstāj tikai vienu apstrādājamo CSV failu.")

    for fails in csv_faili:
        print(f"   - {fails.name}")

    sys.exit(1)

ievades_fails = csv_faili[0]

print(f"\n📂 Atrasts fails: {ievades_fails.name}")


# ============================================================
# IEVADES FAILA NOSAUKUMA VALIDĀCIJA
# ============================================================

nosaukuma_paraugs = re.compile(
    r"^ZVB_koordinatas_(\d{8})-(\d{8})$",
    re.IGNORECASE
)

atbilstiba = nosaukuma_paraugs.fullmatch(ievades_fails.stem)

if atbilstiba is None:
    print("❌ Nederīgs ievades faila nosaukums.")
    print("   Nosaukumam jāatbilst struktūrai:")
    print("   ZVB_koordinatas_DDMMYYYY-DDMMYYYY.csv")
    print("   Piemērs:")
    print("   ZVB_koordinatas_01012016-31082026.csv")
    sys.exit(1)

sakuma_datums_teksts = atbilstiba.group(1)
beigu_datums_teksts = atbilstiba.group(2)


# ============================================================
# DATUMU VALIDĀCIJA FAILA NOSAUKUMĀ
# ============================================================

try:
    sakuma_datums = datetime.strptime(
        sakuma_datums_teksts,
        "%d%m%Y"
    ).date()

except ValueError:
    print("❌ Faila nosaukumā ir nederīgs sākuma datums.")
    print(f"   {sakuma_datums_teksts}")
    sys.exit(1)

try:
    beigu_datums = datetime.strptime(
        beigu_datums_teksts,
        "%d%m%Y"
    ).date()

except ValueError:
    print("❌ Faila nosaukumā ir nederīgs beigu datums.")
    print(f"   {beigu_datums_teksts}")
    sys.exit(1)

if sakuma_datums > beigu_datums:
    print(
        "❌ Sākuma datums nedrīkst būt vēlāks "
        "par beigu datumu."
    )
    print(f"   Sākuma datums: {sakuma_datums:%d.%m.%Y}")
    print(f"   Beigu datums : {beigu_datums:%d.%m.%Y}")
    sys.exit(1)

gadu_starpiba = beigu_datums.year - sakuma_datums.year

if gadu_starpiba != 10:
    print(
        "❌ Beigu gada un sākuma gada starpībai "
        "jābūt tieši 10."
    )
    print(f"   Sākuma gads: {sakuma_datums.year}")
    print(f"   Beigu gads : {beigu_datums.year}")
    print(f"   Starpība   : {gadu_starpiba}")
    sys.exit(1)

print("✅ Faila nosaukums atbilst prasībām.")
print(f"✅ Sākuma datums: {sakuma_datums:%d.%m.%Y}")
print(f"✅ Beigu datums : {beigu_datums:%d.%m.%Y}")
print(f"✅ Gadu starpība: {gadu_starpiba}")


# ============================================================
# IZVADES FAILA NOSAUKUMS
# ============================================================

izvades_fails = publ_mape / (
    f"{ievades_fails.stem}_parveidota.csv"
)

print(f"\n📂 Apstrādāju: {ievades_fails.name}")


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
    print(f"❌ Neizdevās nolasīt CSV failu:\n{e}")
    sys.exit(1)


# ============================================================
# KOLONNU NOSAUKUMU NORMALIZĀCIJA
# ============================================================

df.columns = df.columns.str.strip()


# ============================================================
# STRUKTŪRAS VALIDĀCIJA
# ============================================================

try:
    if len(df.columns) != len(sakotnejie_virsraksti):
        raise ValueError(
            "Kolonnu skaits nesakrīt: "
            f"failā={len(df.columns)}, "
            f"paredzēts={len(sakotnejie_virsraksti)}"
        )

    faktiskie_virsraksti = list(df.columns)

    if faktiskie_virsraksti != sakotnejie_virsraksti:
        raise ValueError(
            "Sākotnējie kolonnu nosaukumi vai to secība "
            "neatbilst paredzētajai struktūrai.\n"
            f"Failā:     {faktiskie_virsraksti}\n"
            f"Paredzēts: {sakotnejie_virsraksti}"
        )

    print("✅ Kolonnu struktūra pārbaudīta.")

except Exception as e:
    print(f"❌ Nederīga CSV struktūra:\n{e}")
    sys.exit(1)


# ============================================================
# KOLONNU NOSAUKUMU PĀRVEIDOŠANA
# ============================================================

df.columns = jaunie_virsraksti

print("✅ Kolonnu nosaukumi pārveidoti.")


# ============================================================
# TUKŠO VĒRTĪBU UZSKAITE
# ============================================================

tuksas_vertibas = {}

for kolonna in df.columns:
    skaits = (
        df[kolonna]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    tuksas_vertibas[kolonna] = skaits


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

    print("✅ Pārveidotais fails saglabāts.")

except Exception as e:
    print(f"❌ Neizdevās saglabāt CSV failu:\n{e}")
    sys.exit(1)


# ============================================================
# KOPSAVILKUMS
# ============================================================

print("\n========================================")
print("KOPSAVILKUMS")
print("========================================")

print("✅ CSV veiksmīgi apstrādāts.")
print(f"📄 Sākotnējais fails : {ievades_fails.name}")
print(f"📄 Gala fails        : {izvades_fails.name}")
print(f"📅 Sākums            : {sakuma_datums:%d.%m.%Y}")
print(f"📅 Beigas            : {beigu_datums:%d.%m.%Y}")
print(f"📊 Datu rindas       : {len(df)}")
print(f"📋 Kolonnas          : {len(df.columns)}")

print("\nTUKŠĀS VĒRTĪBAS")
print("----------------------------------------")

for kolonna, skaits in tuksas_vertibas.items():
    print(f"{kolonna:<10}: {skaits}")

print("\n📂 Saglabāts:")
print(f"   {izvades_fails}")

print("\n✅ Darbs pabeigts.")

sys.exit(0)
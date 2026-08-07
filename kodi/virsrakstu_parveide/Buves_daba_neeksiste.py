import pandas as pd
from pathlib import Path
import csv

print("Programma uzsākta")

# Mape, kur atrodas XLSX datne
folder = Path(r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\B DABA NAV")

print(f"Meklē XLSX datni mapē: {folder}")

required_columns = [
    "Administratīvā teritorija",
    "Administratīvi teritoriālā vienība",
    "Būves kadastra apzīmējums",
    "Būves nosaukums",
    "Būves adrese",
    "Būves masveida apsekošanas datums",
    "Būves kadastrālās uzmērīšanas datums",
    "Stāvu skaits",
    "Apbūves laukums",
    "Ārsienu materiāls",
    "Būves fiskālā kadastrālā vērtība, EUR",
    "Būves universālā kadastrālā vērtība, EUR",
    "Pazīmes uzlikšanas datums",
    "Zemes vienības kadastra apzīmējums",
    "Zemes vienības adrese",
    "Dati atlasīti uz",
]

# Atrod visas XLSX datnes
xlsx_files = list(folder.glob("*.xlsx"))

print(f"Atrastas XLSX datnes: {len(xlsx_files)}")

if len(xlsx_files) == 0:
    raise Exception("Mapē nav atrasta neviena XLSX datne")

# Izvēlas jaunāko XLSX datni
input_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)

# CSV datne tiks saglabāta tajā pašā mapē
output_file = input_file.with_suffix(".csv")

print(f"Izvēlēta XLSX datne: {input_file.name}")
print(f"CSV datne: {output_file.name}")

# Nolasa XLSX datni
print("Notiek XLSX datnes nolasīšana...")
df = pd.read_excel(input_file)

print(f"Nolasītas rindas: {len(df)}")
print(f"Nolasītas kolonnas: {len(df.columns)}")

# Pārbauda kolonnas
print("Notiek kolonnu pārbaude...")

actual_columns = list(df.columns)

missing_columns = [col for col in required_columns if col not in actual_columns]
extra_columns = [col for col in actual_columns if col not in required_columns]

if missing_columns:
    raise Exception(f"XLSX datnē trūkst kolonnu: {missing_columns}")

if extra_columns:
    raise Exception(f"XLSX datnē ir liekas kolonnas: {extra_columns}")

print("Kolonnu pārbaude veiksmīga")

# Sakārto kolonnas vajadzīgajā secībā
print("Notiek kolonnu sakārtošana...")
df = df[required_columns]

# Pārsauc kolonnas CSV failam
print("Notiek kolonnu pārsaukšana...")

df = df.rename(columns={
    "Administratīvā teritorija": "AdmtKind",
    "Administratīvi teritoriālā vienība": "AdmtKindTer",
    "Būves kadastra apzīmējums": "BuiCadNr",
    "Būves nosaukums": "BuiName",
    "Būves adrese": "AdrBuiFull",
    "Būves masveida apsekošanas datums": "BuiInspectionDate",
    "Būves kadastrālās uzmērīšanas datums": "BuifInspectionDate",
    "Stāvu skaits": "BuiGroundFloor",
    "Apbūves laukums": "BuiConstrArea",
    "Ārsienu materiāls": "MaterialKind",
    "Būves fiskālā kadastrālā vērtība, EUR": "BuiFiscKV",
    "Būves universālā kadastrālā vērtība, EUR": "BuiUnivKV",
    "Pazīmes uzlikšanas datums": "JnBuiDateTo",
    "Zemes vienības kadastra apzīmējums": "ParCadNr",
    "Zemes vienības adrese": "AdrParFull",
    "Dati atlasīti uz": "Data"
})

print("Kolonnu pārsaukšana pabeigta")

# Saglabā CSV formātā ar UTF-8 BOM kodējumu
print("Notiek CSV datnes saglabāšana...")

df.to_csv(
    output_file,
    index=False,
    sep=",",
    encoding="utf-8-sig",
    quoting=csv.QUOTE_ALL
)

print("CSV datne veiksmīgi izveidota")
print(f"Saglabāšanas vieta: {output_file}")
print("Programma pabeigta")
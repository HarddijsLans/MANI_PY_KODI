import pandas as pd
from pathlib import Path
import csv

print("Programma uzsākta")

folder = Path(r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\PIRMSREGISTRETAS BUVES")

print(f"Meklē XLSX datni mapē: {folder}")

required_columns = [
    "Administratīvā teritorija",
    "Administratīvi teritoriālā vienība",
    "Būves kadastra apzīmējums",
    "Būves nosaukums",
    "Būves adrese",
    "Stāvu skaits",
    "Apbūves laukums",
    "Ārsienu materiāls",
    "Būves reģistrēšanas datums",
    "Zemes vienības kadastra apzīmējums",
    "Zemes vienības adrese",
    "Dati atlasīti uz",
]

xlsx_files = list(folder.glob("*.xlsx"))

print(f"Atrastas XLSX datnes: {len(xlsx_files)}")

if len(xlsx_files) == 0:
    raise Exception("Mapē nav atrasta neviena XLSX datne")

input_file = max(xlsx_files, key=lambda f: f.stat().st_mtime)
output_file = input_file.with_suffix(".csv")

print(f"Izvēlēta XLSX datne: {input_file.name}")
print(f"CSV datne: {output_file.name}")

print("Notiek XLSX datnes nolasīšana...")
df = pd.read_excel(input_file)

print(f"Nolasītas rindas: {len(df)}")
print(f"Nolasītas kolonnas: {len(df.columns)}")

print("Notiek kolonnu pārbaude...")

actual_columns = list(df.columns)

missing_columns = [col for col in required_columns if col not in actual_columns]
extra_columns = [col for col in actual_columns if col not in required_columns]

if missing_columns:
    raise Exception(f"XLSX datnē trūkst kolonnu: {missing_columns}")

if extra_columns:
    raise Exception(f"XLSX datnē ir liekas kolonnas: {extra_columns}")

print("Kolonnu pārbaude veiksmīga")

print("Notiek kolonnu sakārtošana...")
df = df[required_columns]

print("Notiek kolonnu pārsaukšana...")

df = df.rename(columns={
    "Administratīvā teritorija": "AdmtKind",
    "Administratīvi teritoriālā vienība": "AdmtKindTer",
    "Būves kadastra apzīmējums": "BuiCadNr",
    "Būves nosaukums": "BuiName",
    "Būves adrese": "AdrBuiFull",
    "Stāvu skaits": "BuiGroundFloor",
    "Apbūves laukums": "BuiConstrArea",
    "Ārsienu materiāls": "MaterialKind",
    "Būves reģistrēšanas datums": "BuiRegDate",
    "Zemes vienības kadastra apzīmējums": "ParCadNr",
    "Zemes vienības adrese": "AdrParFull",
    "Dati atlasīti uz": "Data"
})

print("Kolonnu pārsaukšana pabeigta")

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
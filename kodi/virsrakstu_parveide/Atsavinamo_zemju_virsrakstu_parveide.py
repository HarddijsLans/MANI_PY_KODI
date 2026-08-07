import csv
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd


# ==========================================================
# PALĪGFUNKCIJAS
# ==========================================================

def norm(s: str) -> str:
    """Normalizē nosaukumu salīdzināšanai: mazajiem, bez atstarpēm/pasvītrām."""
    return "".join(ch for ch in s.lower() if ch not in {" ", "_"})


def find_child_dir(parent: Path, wanted_names) -> Optional[Path]:
    """Meklē bērna mapi pēc nosaukuma neatkarīgi no reģistra/atstarpēm/pasvītrām."""
    if isinstance(wanted_names, str):
        wanted_names = [wanted_names]

    wanted_norms = {norm(w) for w in wanted_names}

    if not parent.exists():
        return None

    for p in parent.iterdir():
        if p.is_dir() and norm(p.name) in wanted_norms:
            return p

    return None


def wait_for_file_ready(file_path: Path, timeout_seconds: int = 60) -> bool:
    """
    Gaida, līdz fails eksistē, nav .crdownload un izmērs vairs nemainās.
    """
    end_time = time.time() + timeout_seconds
    previous_size = -1

    while time.time() < end_time:
        if file_path.exists() and not Path(str(file_path) + ".crdownload").exists():
            current_size = file_path.stat().st_size

            if current_size > 0 and current_size == previous_size:
                return True

            previous_size = current_size

        time.sleep(1)

    return False


def move_file_replace(source: Path, target: Path) -> None:
    """Pārvieto failu, aizstājot esošo mērķa failu, ja tāds ir."""
    if target.exists():
        target.unlink()

    shutil.move(str(source), str(target))


# ==========================================================
# KONFIGURĀCIJA
# ==========================================================

base = Path(r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE")
downloads_mape = Path(r"C:\Users\hardijslans\Downloads")

projekta_mape = find_child_dir(
    base,
    ["Atsavinamas_zemes", "ATSAVINAMAS ZEMES"]
)

if projekta_mape is None:
    print("❌ Neatradu projektu mapi zem:", base)
    sys.exit(1)

projekts = projekta_mape

sakuma_mape = find_child_dir(
    projekts,
    ["Sakuma_datnes", "Sākuma_datnes"]
)

if sakuma_mape is None:
    print("❌ Neatradu mapi 'Sakuma_datnes' projektā:", projekts)
    sys.exit(1)

publ_mape = find_child_dir(
    projekts,
    ["Datnes_publicesanai", "Datnes_publicēšanai"]
)

if publ_mape is None:
    publ_mape = projekts / "Datnes_publicesanai"
    publ_mape.mkdir(parents=True, exist_ok=True)

print("📁 Projekts :", projekts)
print("⬇ Downloads:", downloads_mape)
print("📥 Ievade  :", sakuma_mape)
print("📤 Izvade  :", publ_mape)


# ==========================================================
# FAILU SHĒMAS
# ==========================================================

faili_info = {
    "1_pielikums.csv": [
        "AdmtKind",
        "AdmtKindTer",
        "BuiCadNrList",
        "ParCadNr",
        "PurList",
        "DivParCadNr",
        "DateDeDisPr",
        "ParArea",
        "ParCadVal",
        "ParShareAmount",
        "ParcelArea",
        "ProArPar",
        "ParPrice",
        "ParcelTotalArea",
        "TotalCadVal",
        "TotDispPric",
    ],
    "2_pielikums.csv": [
        "AdmtKind",
        "AdmtKindTer",
        "PregCadNr",
        "Std",
        "OwnerSharParts",
        "JoPropSharParts",
        "DivParCadNr",
        "ParcelArea",
        "ParPrice",
        "Date",
        "EndDate",
    ],
}


kopsavilkums: List[Tuple[str, str, str]] = []


# ==========================================================
# 1. FAILU PĀRVIETOŠANA NO DOWNLOADS UZ SAKUMA_DATNES
# ==========================================================

print("\n==============================")
print("FAILU PĀRVIETOŠANA")
print("==============================")

for fails in faili_info.keys():
    source = downloads_mape / fails
    target = sakuma_mape / fails

    print(f"\n📦 Pārbaudu: {source}")

    if not wait_for_file_ready(source, timeout_seconds=60):
        msg = f"Fails nav atrasts vai nav gatavs lejupielādēšanai: {source}"
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))
        continue

    try:
        move_file_replace(source, target)
        print(f"✅ Pārvietots → {target}")
    except Exception as e:
        msg = f"Neizdevās pārvietot failu: {e}"
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))


# ==========================================================
# 2. CSV VIRSRĀKSTU PĀRVEIDE
# ==========================================================

print("\n==============================")
print("CSV VIRSRĀKSTU PĀRVEIDE")
print("==============================")

for fails, jaunie_virsraksti in faili_info.items():
    orig_cels = sakuma_mape / fails
    jaunais_cels = publ_mape / f"parveidots_{fails}"

    print(f"\n📂 Apstrādāju: {orig_cels}")

    if not orig_cels.exists():
        msg = "Ievades fails nav atrasts."
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))
        continue

    try:
        df = pd.read_csv(
            orig_cels,
            encoding="utf-8",
            dtype=str,
            sep=";"
        )

        print("✅ Dati nolasīti.")

    except Exception as e:
        msg = f"Nolasīšana: {e}"
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))
        continue

    try:
        if len(df.columns) != len(jaunie_virsraksti):
            raise ValueError(
                f"Kolonnu skaits nesakrīt: "
                f"failā={len(df.columns)} vs shēmā={len(jaunie_virsraksti)}"
            )

        df.columns = jaunie_virsraksti

        df.to_csv(
            jaunais_cels,
            index=False,
            encoding="utf-8-sig",
            sep=",",
            quoting=csv.QUOTE_ALL
        )

        print(f"✅ Saglabāts → {jaunais_cels}")

        kopsavilkums.append(
            (fails, "OK", f"Saglabāts: {jaunais_cels.name}")
        )

    except Exception as e:
        msg = f"Saglabāšana: {e}"
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))


# ==========================================================
# KOPSAVILKUMS + EXIT CODE
# ==========================================================

print("\n==============================")
print("KOPSAVILKUMS")
print("==============================")

for nosaukums, statuss, inf in kopsavilkums:
    print(f"{nosaukums}: {statuss} – {inf}")

if any(statuss == "FAIL" for _, statuss, _ in kopsavilkums):
    sys.exit(1)

sys.exit(0)

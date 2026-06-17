import csv
import re
from pathlib import Path
import pandas as pd
import sys
from typing import Optional, List, Tuple

# ====== Palīgfunkcijas ======
def norm(s: str) -> str:
    """Normalizē nosaukumu salīdzināšanai: mazajiem, bez atstarpēm/pasvītrām."""
    return "".join(ch for ch in s.lower() if ch not in {" ", "_"})

def find_child_dir(parent: Path, wanted_names) -> Optional[Path]:
    """
    Meklē bērna mapi pēc nosaukuma(-iem) neatkarīgi no reģistra un atstarpēm/pasvītrām.
    wanted_names: str vai [str, ...]
    """
    if isinstance(wanted_names, str):
        wanted_names = [wanted_names]

    wanted_norms = {norm(w) for w in wanted_names}

    if not parent.exists():
        return None

    for p in parent.iterdir():
        if p.is_dir() and norm(p.name) in wanted_norms:
            return p

    return None

# ====== Konfigurācija ======
base = Path(r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE")

# Meklē mapi "Atsavinamas_zemes" / "ATSAVINAMAS ZEMES"
projekta_mape = find_child_dir(base, ["Atsavinamas_zemes", "ATSAVINAMAS ZEMES"])

if projekta_mape is not None:
    projekts = projekta_mape
else:
    print("❌ Neatradu projektu mapi 'Atsavinamas_zemes' / 'ATSAVINAMAS ZEMES' zem:", base)
    sys.exit(1)

# Atrodam apakšmapes
sakuma_mape = find_child_dir(projekta_mape, ["Sakuma_datnes", "Sākuma_datnes"])

if not sakuma_mape:
    print("❌ Neatradu mapi 'Sakuma_datnes' projektā:", projekta_mape)
    sys.exit(1)

publ_mape = find_child_dir(projekta_mape, ["Datnes_publicesanai", "Datnes_publicēšanai"])

if not publ_mape:
    publ_mape = projekts / "Datnes_publicesanai"
    publ_mape.mkdir(parents=True, exist_ok=True)

print("📁 Projekts:", projekts)
print("📥 Ievade :", sakuma_mape)
print("📤 Izvade :", publ_mape)

# Failu saraksts un virsrakstu aizstāšana
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
        "TotDispPric"
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
        "EndDate"
    ],
}

kopsavilkums: List[Tuple[str, str, str]] = []

# ====== Apstrāde ======
for fails, jaunie_virsraksti in faili_info.items():

    orig_cels = sakuma_mape / fails
    jaunais_cels = publ_mape / f"parveidots_{fails}"

    print(f"\n📂 Apstrādāju: {orig_cels}")

    if not orig_cels.exists():
        msg = "Ievades fails nav atrasts."
        print(f"❌ {msg}")
        kopsavilkums.append((fails, "FAIL", msg))
        continue

    # 1) Nolasīšana
    try:
        df = pd.read_csv(
            orig_cels,
            encoding="utf-8",
            dtype=str,
            sep=";"
        )

        print("✅ 1. daļa: dati nolasīti.")

    except Exception as e:
        print(f"❌ Nevar nolasīt {fails}: {e}")
        kopsavilkums.append((fails, "FAIL", f"Nolasīšana: {e}"))
        continue

    # 2) Datumu apstrāde IZŅEMTA

    # 3) Virsrakstu validācija + saglabāšana
    try:

        if len(df.columns) != len(jaunie_virsraksti):
            raise ValueError(
                f"Kolonnu skaits nesakrīt: "
                f"failā={len(df.columns)} vs shēmā={len(jaunie_virsraksti)}"
            )

        # Aizstājam kolonnu nosaukumus
        df.columns = jaunie_virsraksti

        # Saglabājam:
        # - UTF-8 BOM
        # - komats kā atdalītājs
        # - visas kolonnas un vērtības pēdiņās
        df.to_csv(
            jaunais_cels,
            index=False,
            encoding="utf-8-sig",
            sep=",",
            quoting=csv.QUOTE_ALL
        )

        print(f"✅ 3. daļa: saglabāts → {jaunais_cels}")

        kopsavilkums.append(
            (fails, "OK", f"Saglabāts: {jaunais_cels.name}")
        )

    except Exception as e:
        print(f"❌ Neizdevās saglabāt {fails}: {e}")

        kopsavilkums.append(
            (fails, "FAIL", f"Saglabāšana: {e}")
        )

# ====== Kopsavilkums ======
print("\n— KOPSAVILKUMS —")

for nosaukums, statuss, inf in kopsavilkums:
    print(f"{nosaukums}: {statuss} – {inf}")
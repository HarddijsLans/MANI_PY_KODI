from datetime import datetime
from pathlib import Path
import sys

from openpyxl import load_workbook


# ============================================================
# KONFIGURĀCIJA
# ============================================================

SAKOTNEJO_DATNU_MAPE = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\VIRSRAKSTU PARVEIDE\DARIJUMI AR ZV\SAKOTNEJAS DATNES"
)

PUBLICESANAS_MAPE = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\VIRSRAKSTU PARVEIDE\DARIJUMI AR ZV\DATNES PUBLICESANAI"
)

DATNES_PREFIKSS = "zv_vertibu_zonas_un_koordinatas_01012016-"

DATUMA_FORMATS = "%d%m%Y"

PARVEIDOTAS_DATNES_PIELIKUMS = "_parveidota"

# Rinda, kurā atrodas kolonnu virsraksti.
VIRSRAKSTU_RINDA = 1


KOLONNU_NOSAUKUMI = {
    "PARCADNR": (
        "Darījumā iekļautās zemes vienības kadastra apzīmējums"
    ),
    "DEAID": (
        "Darījuma identifikators, kas izmantojams ieraksta "
        "sasaistīšanai ar darījuma datiem"
    ),
    "VALZ_NAME1": (
        "Lauksaimniecībā izmantojamās zemes zonējums"
    ),
    "VALZ_NAME2": (
        "Meža zemes zonējums"
    ),
    "VALZ_NAME3": (
        "Dzīvojamo māju apbūves zonējums"
    ),
    "VALZ_NAME4": (
        "Rūpnieciskās ražošanas objektu apbūves zonējums"
    ),
    "VALZ_NAME5": (
        "Komercobjektu apbūves zonējums"
    ),
    "KoordX": (
        "Adresācijas objekta centroīda X koordināta, "
        "LKS-92 koordinātu sistēmā"
    ),
    "KoordY": (
        "Adresācijas objekta centroīda Y koordināta, "
        "LKS-92 koordinātu sistēmā"
    ),
    "DdN": (
        "Adresācijas objekta centroīda koordinātas platums "
        "(Latitude) decimālgrādos"
    ),
    "DdE": (
        "Adresācijas objekta centroīda koordinātas garums "
        "(Longitude) decimālgrādos"
    ),
}


# ============================================================
# FAILA ATRAŠANA
# ============================================================

def iegut_datumu_no_nosaukuma(datne: Path) -> datetime:
    """
    Iegūst DDMMYYYY datumu no datnes nosaukuma.

    Piemērs:
    zv_vertibu_zonas_un_koordinatas_01012016-30052026.xlsx
    """
    nosaukums = datne.stem

    if not nosaukums.startswith(DATNES_PREFIKSS):
        raise ValueError(
            "Datnes nosaukums neatbilst noteiktajam prefiksam."
        )

    datuma_teksts = nosaukums.removeprefix(DATNES_PREFIKSS)

    if len(datuma_teksts) != 8:
        raise ValueError(
            "Datumam datnes nosaukumā jābūt tieši 8 cipariem."
        )

    if not datuma_teksts.isdigit():
        raise ValueError(
            "Datums datnes nosaukumā satur simbolus, kas nav cipari."
        )

    return datetime.strptime(datuma_teksts, DATUMA_FORMATS)


def atrast_jaunako_datni() -> Path:
    """
    Atrod sākotnējo XLSX datni ar jaunāko datumu nosaukumā.
    """
    if not SAKOTNEJO_DATNU_MAPE.exists():
        raise FileNotFoundError(
            "Sākotnējo datņu mape neeksistē:\n"
            f"{SAKOTNEJO_DATNU_MAPE}"
        )

    kandidati = []

    for datne in SAKOTNEJO_DATNU_MAPE.glob(
        f"{DATNES_PREFIKSS}*.xlsx"
    ):
        # Ignorē Excel pagaidu datnes.
        if datne.name.startswith("~$"):
            continue

        # Ignorē jau pārveidotas datnes.
        if datne.stem.endswith(PARVEIDOTAS_DATNES_PIELIKUMS):
            continue

        try:
            datnes_datums = iegut_datumu_no_nosaukuma(datne)
            kandidati.append((datnes_datums, datne))

        except ValueError as kluda:
            print()
            print(
                "BRĪDINĀJUMS: izlaista neatbilstoši nosaukta datne:"
            )
            print(f"  {datne.name}")
            print(f"  Iemesls: {kluda}")

    if not kandidati:
        raise FileNotFoundError(
            "Netika atrasta neviena atbilstoša sākotnējā datne.\n\n"
            "Sagaidāmais nosaukuma formāts:\n"
            f"{DATNES_PREFIKSS}DDMMYYYY.xlsx"
        )

    _, jaunaka_datne = max(
        kandidati,
        key=lambda ieraksts: ieraksts[0],
    )

    return jaunaka_datne


def izveidot_rezultata_celu(sakotneja_datne: Path) -> Path:
    """
    Izveido rezultāta datnes nosaukumu un pilno ceļu.
    """
    rezultata_nosaukums = (
        f"{sakotneja_datne.stem}"
        f"{PARVEIDOTAS_DATNES_PIELIKUMS}.xlsx"
    )

    return PUBLICESANAS_MAPE / rezultata_nosaukums


# ============================================================
# VIRSRAKSTU MAIŅA
# ============================================================

def nomainit_lapas_virsrakstus(darba_lapa) -> int:
    """
    Maina tikai norādītās darba lapas pirmās rindas virsrakstus.

    Neviena datu šūna zem virsrakstu rindas netiek mainīta.
    """
    atrastie_virsraksti = set()
    parveidoto_skaits = 0

    for suna in darba_lapa[VIRSRAKSTU_RINDA]:
        esosais_nosaukums = suna.value

        if esosais_nosaukums in KOLONNU_NOSAUKUMI:
            suna.value = KOLONNU_NOSAUKUMI[esosais_nosaukums]

            atrastie_virsraksti.add(esosais_nosaukums)
            parveidoto_skaits += 1

    trukstosi_virsraksti = [
        nosaukums
        for nosaukums in KOLONNU_NOSAUKUMI
        if nosaukums not in atrastie_virsraksti
    ]

    if trukstosi_virsraksti:
        trukstoso_saraksts = "\n".join(
            f"  - {nosaukums}"
            for nosaukums in trukstosi_virsraksti
        )

        raise ValueError(
            f"Darba lapā '{darba_lapa.title}' nav atrasti visi "
            "nepieciešamie kolonnu virsraksti.\n\n"
            "Trūkstošie virsraksti:\n"
            f"{trukstoso_saraksts}"
        )

    return parveidoto_skaits


def parveidot_datni(
    sakotneja_datne: Path,
    rezultata_datne: Path,
) -> tuple[int, str]:
    """
    Atver Excel datni un maina tikai pirmās rindas virsrakstus.

    Datu šūnu vērtības netiek nolasītas datu tabulā un netiek
    pārveidotas.
    """
    try:
        darbgramata = load_workbook(
            filename=sakotneja_datne,
            data_only=False,
        )

    except PermissionError as kluda:
        raise PermissionError(
            "Sākotnējo datni nevar atvērt. Iespējams, tā pašlaik "
            "ir atvērta programmā Excel."
        ) from kluda

    except Exception as kluda:
        raise RuntimeError(
            f"Neizdevās atvērt Excel datni.\n"
            f"Tehniskā informācija: {kluda}"
        ) from kluda

    # Tiek izmantota darbgrāmatas aktīvā lapa.
    darba_lapa = darbgramata.active

    parveidoto_skaits = nomainit_lapas_virsrakstus(
        darba_lapa
    )

    PUBLICESANAS_MAPE.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        darbgramata.save(rezultata_datne)

    except PermissionError as kluda:
        raise PermissionError(
            "Rezultāta datni nevar saglabāt. Iespējams, datne ar "
            "šādu nosaukumu pašlaik ir atvērta programmā Excel."
        ) from kluda

    except Exception as kluda:
        raise RuntimeError(
            f"Neizdevās saglabāt rezultāta datni.\n"
            f"Tehniskā informācija: {kluda}"
        ) from kluda

    finally:
        darbgramata.close()

    return parveidoto_skaits, darba_lapa.title


# ============================================================
# GALVENĀ PROGRAMMA
# ============================================================

def main() -> None:
    print("=" * 70)
    print("ZV DATNES KOLONNU VIRSRAKSTU PĀRVEIDOŠANA")
    print("=" * 70)

    sakotneja_datne = atrast_jaunako_datni()

    rezultata_datne = izveidot_rezultata_celu(
        sakotneja_datne
    )

    print()
    print("Atrasta sākotnējā datne:")
    print(f"  {sakotneja_datne}")

    print()
    print("Rezultāta datne:")
    print(f"  {rezultata_datne}")

    if rezultata_datne.exists():
        print()
        print(
            "BRĪDINĀJUMS: rezultāta datne jau eksistē un tiks "
            "pārrakstīta."
        )

    parveidoto_skaits, lapas_nosaukums = parveidot_datni(
        sakotneja_datne=sakotneja_datne,
        rezultata_datne=rezultata_datne,
    )

    print()
    print("-" * 70)
    print("PĀRVEIDOŠANA VEIKSMĪGI PABEIGTA")
    print("-" * 70)

    print(f"Apstrādātā darba lapa: {lapas_nosaukums}")
    print(f"Nomainīto virsrakstu skaits: {parveidoto_skaits}")

    print()
    print("Mainītas tikai virsrakstu rindas šūnas.")
    print("Datu rindas nav pārveidotas.")

    print()
    print("Pārveidotā datne saglabāta:")
    print(f"  {rezultata_datne}")

    print("=" * 70)


if __name__ == "__main__":
    try:
        main()

    except Exception as kluda:
        print()
        print("=" * 70)
        print("KĻŪDA")
        print("=" * 70)
        print(str(kluda))
        print("=" * 70)

        sys.exit(1)
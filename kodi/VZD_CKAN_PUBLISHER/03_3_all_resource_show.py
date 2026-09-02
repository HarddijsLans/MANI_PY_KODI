"""
===============================================================================
03_3_conforms_to.py
===============================================================================

Mērķis
------
1. Nolasīt vienu konkrētu CKAN resursu.
2. No resursa iegūt lauka "conformsTo" vērtību.
3. Nolasīt JSON saturu no "conformsTo" norādītā URL.
4. Parādīt pilnu JSON saturu terminālī.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

HTTP metodes
------------
1. GET uz CKAN Action API
2. GET uz conformsTo norādīto JSON URL

Parametri
---------
id : Resursa ID

Rezultāts
---------
Terminālī tiek parādīta:
- resursa pamatinformācija;
- conformsTo URL;
- pilns JSON saturs no šī URL.

Drošības līmenis
----------------
Tikai lasa datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import json
import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


# -----------------------------------------------------------------------------
# 1. Izvēlētais resurss
# -----------------------------------------------------------------------------

RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"


# -----------------------------------------------------------------------------
# 2. CKAN resource_show Action API adrese
# -----------------------------------------------------------------------------

resource_show_url = f"{CKAN_BASE_URL}/api/3/action/resource_show"


# -----------------------------------------------------------------------------
# 3. Autorizācijas galvene
# -----------------------------------------------------------------------------

headers = {
    "Authorization": CKAN_API_TOKEN
}


# -----------------------------------------------------------------------------
# 4. resource_show parametri
# -----------------------------------------------------------------------------

params = {
    "id": RESOURCE_ID
}


print("1. Nolasu resursu no CKAN...")


try:
    # -------------------------------------------------------------------------
    # 5. Nolasām resursu
    # -------------------------------------------------------------------------

    response = requests.get(
        resource_show_url,
        headers=headers,
        params=params,
        timeout=30
    )

    print(f"CKAN HTTP statuss: {response.status_code}")
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        print("\nCKAN atgrieza kļūdu:")
        print(json.dumps(data, ensure_ascii=False, indent=4))
        raise SystemExit

    resource = data["result"]

    print("\nResurss")
    print("-" * 80)
    print(f"Nosaukums  : {resource.get('name')}")
    print(f"Resursa ID : {resource.get('id')}")
    print(f"Formāts    : {resource.get('format')}")
    print("-" * 80)


    # -------------------------------------------------------------------------
    # 6. Iegūstam conformsTo vērtību
    # -------------------------------------------------------------------------

    conforms_to_url = resource.get("conformsTo")

    if not conforms_to_url:
        print("\nResursam nav aizpildīts lauks 'conformsTo'.")
        raise SystemExit

    print("\n2. Atrasts conformsTo URL:")
    print(conforms_to_url)


    # -------------------------------------------------------------------------
    # 7. Nolasām conformsTo URL norādīto saturu
    # -------------------------------------------------------------------------

    print("\n3. Nolasu JSON saturu no conformsTo URL...")

    metadata_response = requests.get(
        conforms_to_url,
        timeout=30
    )

    print(f"JSON HTTP statuss: {metadata_response.status_code}")
    metadata_response.raise_for_status()


    # -------------------------------------------------------------------------
    # 8. Pārbaudām, vai saņemtais saturs ir JSON
    # -------------------------------------------------------------------------

    metadata_json = metadata_response.json()


    # -------------------------------------------------------------------------
    # 9. Parādām pilnu JSON saturu
    # -------------------------------------------------------------------------

    print("\nPilns conformsTo JSON saturs:")
    print("=" * 80)

    print(
        json.dumps(
            metadata_json,
            ensure_ascii=False,
            indent=4
        )
    )

    print("=" * 80)


except requests.exceptions.Timeout:
    print("\nKļūda: pieprasījums pārsniedza 30 sekunžu gaidīšanas laiku.")


except requests.exceptions.ConnectionError as error:
    print("\nSavienojuma kļūda:")
    print(error)


except requests.exceptions.HTTPError as error:
    print("\nHTTP kļūda:")
    print(error)


except requests.exceptions.RequestException as error:
    print("\nHTTP pieprasījuma kļūda:")
    print(error)


except json.JSONDecodeError as error:
    print("\nSaņemtais conformsTo saturs nav derīgs JSON:")
    print(error)


except KeyError as error:
    print("\nCKAN atbildē nav sagaidītā lauka:")
    print(error)


except Exception as error:
    print("\nNezināma kļūda:")
    print(error)
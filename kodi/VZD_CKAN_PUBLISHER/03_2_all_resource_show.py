"""
===============================================================================
03_2_resource_show.py
===============================================================================

Mērķis
------
Nolasīt vienu konkrētu CKAN resursu un terminālī parādīt pilnu informāciju,
ko CKAN Action API darbība resource_show atgriež par šo resursu.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

HTTP metode
-----------
GET

Parametri
---------
id : Resursa ID

Rezultāts
---------
Terminālī tiek parādīts pilns resource_show atgrieztais "result" objekts
JSON formātā.

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
# 1. Resurss, kuru vēlamies nolasīt
# -----------------------------------------------------------------------------

RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"


# -----------------------------------------------------------------------------
# 2. CKAN Action API adrese
# -----------------------------------------------------------------------------

url = f"{CKAN_BASE_URL}/api/3/action/resource_show"


# -----------------------------------------------------------------------------
# 3. HTTP pieprasījuma galvenes
# -----------------------------------------------------------------------------

headers = {
    "Authorization": CKAN_API_TOKEN
}


# -----------------------------------------------------------------------------
# 4. HTTP pieprasījuma parametri
# -----------------------------------------------------------------------------

params = {
    "id": RESOURCE_ID
}


print("Nolasu pilnu resursa informāciju no CKAN...")


try:

    # -------------------------------------------------------------------------
    # 5. Nosūtām GET pieprasījumu CKAN
    # -------------------------------------------------------------------------

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print(f"HTTP statuss: {response.status_code}")

    # Ja HTTP statuss norāda kļūdu, izraisām izņēmumu
    response.raise_for_status()


    # -------------------------------------------------------------------------
    # 6. CKAN JSON atbildi pārvēršam Python objektā
    # -------------------------------------------------------------------------

    data = response.json()


    # -------------------------------------------------------------------------
    # 7. Pārbaudām CKAN Action API rezultātu
    # -------------------------------------------------------------------------

    if not data.get("success"):
        print("\nCKAN atgrieza kļūdu:")
        print(json.dumps(data, ensure_ascii=False, indent=4))
        raise SystemExit


    # -------------------------------------------------------------------------
    # 8. Paņemam resursa objektu no CKAN atbildes
    # -------------------------------------------------------------------------

    resource = data["result"]


    # -------------------------------------------------------------------------
    # 9. Parādām pilnu resursa informāciju
    # -------------------------------------------------------------------------

    print("\nPilna CKAN resource_show atbilde (result):")
    print("=" * 80)

    print(
        json.dumps(
            resource,
            ensure_ascii=False,
            indent=4
        )
    )

    print("=" * 80)


except requests.exceptions.RequestException as error:

    print("\nHTTP pieprasījuma kļūda:")
    print(error)


except ValueError as error:

    print("\nCKAN atbilde nav derīgs JSON:")
    print(error)


except KeyError as error:

    print("\nCKAN atbildē nav sagaidītā lauka:")
    print(error)


except Exception as error:

    print("\nNezināma kļūda:")
    print(error)
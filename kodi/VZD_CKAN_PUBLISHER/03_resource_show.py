"""
===============================================================================
03_resource_show.py
===============================================================================

Mērķis
------
Nolasīt informāciju par vienu konkrētu CKAN resursu.

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
Terminālī tiek parādīta izvēlētā resursa informācija.

Drošības līmenis
----------------
Tikai lasa datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

url = f"{CKAN_BASE_URL}/api/3/action/resource_show"

headers = {
    "Authorization": CKAN_API_TOKEN
}

params = {
    "id": RESOURCE_ID
}

print("Nolasu resursu no CKAN...")

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print(f"HTTP statuss: {response.status_code}")

    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        print("CKAN atgrieza kļūdu:")
        print(data)
        raise SystemExit

    resource = data["result"]

    print("\nResurss")
    print("-" * 70)
    print(f"Nosaukums    : {resource.get('name')}")
    print(f"Resursa ID   : {resource.get('id')}")
    print(f"Formāts      : {resource.get('format')}")
    print(f"Apraksts     : {resource.get('description')}")
    print(f"URL          : {resource.get('url')}")
    print(f"Izveidots    : {resource.get('created')}")
    print(f"Mainīts      : {resource.get('last_modified')}")
    print(f"Datnes izmērs: {resource.get('size')}")
    print("-" * 70)

except requests.exceptions.RequestException as error:
    print("HTTP pieprasījuma kļūda:")
    print(error)

except ValueError as error:
    print("CKAN atbilde nav derīgs JSON:")
    print(error)

except KeyError as error:
    print("CKAN atbildē nav sagaidītā lauka:")
    print(error)

except Exception as error:
    print("Nezināma kļūda:")
    print(error)
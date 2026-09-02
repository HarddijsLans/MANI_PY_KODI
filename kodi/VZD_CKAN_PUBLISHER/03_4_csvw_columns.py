"""
===============================================================================
03_4_csvw_columns.py
===============================================================================

Mērķis
------
1. Nolasīt konkrētu CKAN resursu.
2. Iegūt lauka "conformsTo" URL.
3. Nolasīt CSVW metadatu JSON.
4. No tableSchema.columns izdrukāt CSV kolonnu aprakstus.

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

Rezultāts
---------
Terminālī tiek parādīts:
- resursa nosaukums;
- conformsTo URL;
- katras CSV kolonnas tehniskais nosaukums;
- cilvēkam saprotamais nosaukums;
- apraksts;
- datu tips;
- garums.

Drošības līmenis
----------------
Tikai lasa datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import json
import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"

HEADERS = {
    "Authorization": CKAN_API_TOKEN
}

PARAMS = {
    "id": RESOURCE_ID
}


def main():
    print("1. Nolasu resursu no CKAN...")

    resource_response = requests.get(
        RESOURCE_SHOW_URL,
        headers=HEADERS,
        params=PARAMS,
        timeout=30
    )

    print(f"CKAN HTTP statuss: {resource_response.status_code}")
    resource_response.raise_for_status()

    ckan_data = resource_response.json()

    if not ckan_data.get("success"):
        print("\nCKAN atgrieza kļūdu:")
        print(json.dumps(ckan_data, ensure_ascii=False, indent=4))
        raise SystemExit(1)

    resource = ckan_data["result"]

    print("\nResurss")
    print("-" * 80)
    print(f"Nosaukums  : {resource.get('name')}")
    print(f"Resursa ID : {resource.get('id')}")
    print(f"Formāts    : {resource.get('format')}")
    print("-" * 80)

    conforms_to_url = resource.get("conformsTo")

    if not conforms_to_url:
        print("\nResursam nav aizpildīts lauks 'conformsTo'.")
        raise SystemExit(1)

    print("\n2. Atrasts conformsTo URL:")
    print(conforms_to_url)

    print("\n3. Nolasu CSVW metadatu JSON...")

    metadata_response = requests.get(
        conforms_to_url,
        timeout=30
    )

    print(f"JSON HTTP statuss: {metadata_response.status_code}")
    metadata_response.raise_for_status()

    metadata = metadata_response.json()

    table_schema = metadata.get("tableSchema", {})
    columns = table_schema.get("columns", [])

    if not columns:
        print("\nCSVW JSON nesatur tableSchema.columns.")
        raise SystemExit(1)

    print(f"\nAtrasto kolonnu skaits: {len(columns)}")
    print("=" * 80)

    for index, column in enumerate(columns, start=1):
        datatype = column.get("datatype", {})

        technical_name = column.get("name")
        title = column.get("titles")
        description = column.get("dc:description")
        base_type = datatype.get("base")
        length = datatype.get("length")

        print(f"\n{index}. kolonna")
        print("-" * 80)
        print(f"Tehniskais nosaukums : {technical_name}")
        print(f"Nosaukums             : {title}")
        print(f"Apraksts              : {description}")
        print(f"Datu tips             : {base_type}")
        print(f"Garums                : {length}")

    print("\n" + "=" * 80)
    print("Kolonnu datu vārdnīca nolasīta veiksmīgi.")


if __name__ == "__main__":
    try:
        main()

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
        print("\nSaņemtais saturs nav derīgs JSON:")
        print(error)

    except KeyError as error:
        print("\nCKAN atbildē nav sagaidītā lauka:")
        print(error)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
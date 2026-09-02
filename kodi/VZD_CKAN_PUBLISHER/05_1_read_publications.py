"""
===============================================================================
05_1_read_publications.py
===============================================================================

Mērķis
------
Nolasīt publications.json un pārbaudīt abu resursu konfigurāciju.

Drošības līmenis
----------------
Tikai lasa lokālo konfigurācijas failu.
Nesazinās ar CKAN un neko portālā nemaina.
===============================================================================
"""

import json
from pathlib import Path


PUBLICATIONS_FILE = (
    Path(__file__).parent / "publications.json"
)


def main() -> None:
    if not PUBLICATIONS_FILE.exists():
        raise FileNotFoundError(
            f"Konfigurācijas fails nav atrasts:\n"
            f"{PUBLICATIONS_FILE}"
        )

    with PUBLICATIONS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    publications = config.get("publications")

    if not isinstance(publications, list):
        raise ValueError(
            "publications.json nesatur sarakstu 'publications'."
        )

    print(
        f"Atrasti konfigurētie resursi: "
        f"{len(publications)}"
    )

    for index, publication in enumerate(
        publications,
        start=1
    ):
        print("\n" + "-" * 80)
        print(f"{index}. resurss")
        print("-" * 80)

        print(
            f"Ieslēgts   : "
            f"{publication.get('enabled')}"
        )
        print(
            f"Nosaukums  : "
            f"{publication.get('name')}"
        )
        print(
            f"Resursa ID : "
            f"{publication.get('resource_id')}"
        )
        print(
            f"Datne      : "
            f"{publication.get('local_file')}"
        )

        local_file = Path(
            publication.get("local_file", "")
        )

        if local_file.is_file():
            print("Datne eksistē: Jā")
        else:
            print("Datne eksistē: Nē")

    print("\n" + "=" * 80)
    print("publications.json nolasīts veiksmīgi.")


if __name__ == "__main__":
    try:
        main()

    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError
    ) as error:
        print("\nKonfigurācijas kļūda:")
        print(error)
        raise SystemExit(1)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)
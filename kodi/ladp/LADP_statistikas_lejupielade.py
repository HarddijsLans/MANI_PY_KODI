import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import logging

BASE_URL = "https://data.gov.lv/lv/statistika"

OUTPUT_FOLDER = r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\LADP STATISTIKA\DATNES"
LOG_FOLDER = r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\LADP STATISTIKA\LOG"

MAX_RETRIES = 3
TIMEOUT = 30
VZD_IESTADE = "Valsts zemes dienests"


def setup_logging():
    os.makedirs(LOG_FOLDER, exist_ok=True)

    log_file = os.path.join(LOG_FOLDER, "VZD_dati.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8"
    )


def parse_lejupielades(value):
    try:
        return int(
            value.strip()
            .replace(" ", "")
            .replace("\xa0", "")
        )
    except ValueError:
        return None


def get_data_from_page(url, page_number):
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=TIMEOUT
            )

            if response.status_code != 200:
                if attempt < MAX_RETRIES:
                    time.sleep(2)
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            cards = soup.find_all(
                "div",
                class_="card dati-card dati-card-table col-sm-12"
            )

            page_data = []
            today = datetime.now().strftime("%Y-%m-%d")

            for card in cards:
                body = card.find("div", class_="card-body")
                if not body:
                    continue

                rows = body.find_all("a", class_="dati-card-row")

                for row in rows:
                    columns = row.find_all(
                        "div",
                        class_=lambda x: x and x.startswith("col-sm")
                    )

                    if len(columns) < 4:
                        continue

                    num_pk = columns[0].text.strip()

                    datu_kopa = (
                        columns[1].find("b").text.strip()
                        if columns[1].find("b")
                        else columns[1].text.strip()
                    )

                    iestade = columns[2].text.strip()
                    lejupielades = parse_lejupielades(columns[3].text)

                    page_data.append([
                        num_pk,
                        datu_kopa,
                        iestade,
                        lejupielades,
                        today
                    ])

            if attempt > 1:
                logging.warning(
                    f"{page_number}. lapas nolasīšana izdevās tikai ar {attempt}. mēģinājumu"
                )

            return "SUCCESS", page_data, soup

        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES:
                time.sleep(2)

    return "ERROR", [], None


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    setup_logging()
    logging.info("Skripta izpilde uzsākta")

    all_pages_data = []
    processed_pages = 0
    current_url = BASE_URL

    while current_url:
        page_number = processed_pages + 1

        status, page_data, soup = get_data_from_page(
            current_url,
            page_number
        )

        if status == "ERROR":
            logging.error(
                f"Neizdevās nolasīt {page_number}. lapu pēc {MAX_RETRIES} mēģinājumiem"
            )
            logging.error("Izpilde pārtraukta")
            print(
                f"❌ Neizdevās nolasīt {page_number}. lapu pēc {MAX_RETRIES} mēģinājumiem."
            )
            return

        if page_data:
            all_pages_data.extend(page_data)

        processed_pages += 1

        next_page = soup.find("a", {"rel": "next"}) if soup else None

        if next_page and next_page.get("href"):
            current_url = next_page["href"]

            if not current_url.startswith("http"):
                current_url = BASE_URL + current_url
        else:
            current_url = None

    if not all_pages_data:
        logging.error("Netika atrasti dati nevienā lapā")
        print("⚠️ Netika atrasti dati nevienā lapā.")
        return

    df = pd.DataFrame(
        all_pages_data,
        columns=[
            "num_pk",
            "datu_kopa",
            "iestade",
            "lejupielades",
            "lejupielades_datums"
        ]
    )

    df = df[
        df["iestade"].str.contains(
            VZD_IESTADE,
            case=False,
            na=False
        )
    ].copy()

    if df.empty:
        logging.error("Pēc VZD filtra netika atrasts neviens ieraksts")
        print("⚠️ Pēc VZD filtra netika atrasts neviens ieraksts.")
        return

    df["num_pk"] = pd.to_numeric(
        df["num_pk"],
        errors="coerce"
    ).astype("Int64")

    df["lejupielades"] = pd.to_numeric(
        df["lejupielades"],
        errors="coerce"
    )

    history_file_path = os.path.join(
        OUTPUT_FOLDER,
        "VZD_dati_history.csv"
    )

    if os.path.exists(history_file_path):
        history_df = pd.read_csv(
            history_file_path,
            encoding="utf-8-sig"
        )
        history_df = pd.concat(
            [history_df, df],
            ignore_index=True
        )
    else:
        history_df = df

    history_df.to_csv(
        history_file_path,
        index=False,
        encoding="utf-8-sig"
    )

    logging.info(
        f"Apstrādātas {processed_pages} lapas, iegūti {len(df)} VZD ieraksti"
    )
    logging.info("Izpilde pabeigta veiksmīgi")

    print(f"✅ Vēstures fails aktualizēts: {history_file_path}")
    print(f"✅ Apstrādātas {processed_pages} lapas, iegūti {len(df)} VZD ieraksti.")


if __name__ == "__main__":
    main()
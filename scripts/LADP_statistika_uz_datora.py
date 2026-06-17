import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

# Funkcija, lai iegūtu datus no katras lapas
def get_data_from_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="card dati-card dati-card-table col-sm-12")

        all_data = []
        today = datetime.now().strftime("%Y-%m-%d")

        for card in cards:
            body = card.find("div", class_="card-body")
            if body:
                rows = body.find_all("a", class_="dati-card-row")
                for row in rows:
                    columns = row.find_all("div", class_=lambda x: x and x.startswith("col-sm"))
                    if len(columns) >= 4:
                        numurs = columns[0].text.strip()
                        datu_kopa = columns[1].find("b").text.strip() if columns[1].find("b") else columns[1].text.strip()
                        iestade = columns[2].text.strip()
                        lejupielades = columns[3].text.strip()

                        all_data.append([numurs, datu_kopa, iestade, lejupielades, today])

        return all_data, soup
    else:
        print(f"Neizdevās ielādēt lapu, statusa kods: {response.status_code}")
        return [], None

# Datu vākšana
base_url = "https://data.gov.lv/lv/statistika"
current_url = base_url
all_data = []

while current_url:
    print(f"Apstrādājam lapu: {current_url}")
    page_data, soup = get_data_from_page(current_url)
    if page_data:
        all_data.extend(page_data)

    next_page = soup.find('a', {'rel': 'next'})
    if next_page and next_page.get('href'):
        current_url = next_page['href']
        if not current_url.startswith("http"):
            current_url = base_url + current_url
    else:
        current_url = None

# Ja ir dati, saglabājam
if all_data:
    df = pd.DataFrame(all_data, columns=["Numurs", "Datu kopa", "Iestāde", "Lejupielādes", "Lejupielādes datums"])

    # Saglabāšanas ceļš (pielāgo pēc vajadzības)
    folder_path = r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\LADP STATISTIKA"  # Mapae kur saglabāt
    filename = f"LADP_statistika_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    save_path = os.path.join(folder_path, filename) 
  


    # Saglabā CSV failā
    df.to_csv(save_path, index=False, encoding='utf-8-sig')


    print(f"Dati saglabāti failā: {save_path}")
else:
    print("Nav datu, ko saglabāt.")
5.0
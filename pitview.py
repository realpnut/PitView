import time
import requests


def get_drivers():
    with open("numbers.txt", "r") as plik:
        raw = plik.read()

    numbrs = [int(x.strip()) for x in raw.split(",") if x.strip()]

    for numer in numbrs:
        time.sleep(0.4)

        url = f"https://api.openf1.org/v1/drivers?driver_number={numer}&session_key=11342"

        response = requests.get(url)
        data = response.json()

        if isinstance(data, list) and data:
            driver = data[0]

            print(
                f"{driver['broadcast_name']} | "
                f"{driver['driver_number']} | "
                f"{driver['name_acronym']}"
            )
            print(f"Driver Number:     {driver['driver_number']}")
            print(f"Driver Name:       {driver['full_name']}")
            print(f"Team Name:         {driver['team_name']}")
            print("-" * 40)

        elif isinstance(data, dict):
            print(f"Numer {numer}: API zwróciło błąd: {data}")
            print("-" * 40)

        else:
            print(f"Numer {numer}: API nie zwróciło danych dla tej sesji!")
            print("-" * 40)


get_drivers()

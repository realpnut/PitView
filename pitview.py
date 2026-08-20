import os
import time
import threading
import requests
import readchar
from datetime import datetime, timezone


def drivers():
    with open("numbers.txt", "r") as file:
        raw = file.read()

    nums = [int(x.strip()) for x in raw.split(",") if x.strip()]

    for num in nums:
        time.sleep(0.4)

        url = f"https://api.openf1.org/v1/drivers?driver_number={num}&session_key=11342"

        res = requests.get(url)
        dat = res.json()

        if isinstance(dat, list) and dat:
            drv = dat[0]

            print(
                f"{drv['broadcast_name']} | "
                f"{drv['driver_number']} | "
                f"{drv['name_acronym']}"
            )
            print(f"Driver Number:     {drv['driver_number']}")
            print(f"Driver Name:       {drv['full_name']}")
            print(f"Team Name:         {drv['team_name']}")
            print("-" * 40)

        elif isinstance(dat, dict):
            print(f"Number {num}: API returned an error: {dat}")
            print("-" * 40)

        else:
            print(f"Number {num}: API returned no data for this session!")
            print("-" * 40)


def exit_key(stop):
    while not stop.is_set():
        key = readchar.readchar()

        if key.lower() == "c":
            stop.set()
            break


def data(url, params=None, headers=None):
    res = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=10
    )

    if res.status_code != 200:
        raise Exception(
            f"API {res.status_code}: {res.text[:150]}"
        )

    dat = res.json()

    if isinstance(dat, dict):
        if "error" in dat:
            raise Exception(dat["error"])

        if "message" in dat:
            raise Exception(dat["message"])

    return dat


def sessions(base, headers):
    year = datetime.now(timezone.utc).year

    ses = data(
        f"{base}/sessions",
        params={"year": year},
        headers=headers
    )

    if not isinstance(ses, list):
        return []

    return [
        x
        for x in ses
        if isinstance(x, dict)
    ]


def current_session(base, headers):
    ses = sessions(base, headers)

    now = datetime.now(timezone.utc)

    for s in ses:
        try:
            start = datetime.fromisoformat(
                s["date_start"].replace("Z", "+00:00")
            )

            end = datetime.fromisoformat(
                s["date_end"].replace("Z", "+00:00")
            )
        except (KeyError, ValueError, TypeError):
            continue

        if (
            start <= now <= end
            and not s.get("is_cancelled", False)
        ):
            return s

    return None


def latest_session(base, headers):
    ses = sessions(base, headers)

    if not ses:
        return None

    ses.sort(
        key=lambda x: x.get("date_start", ""),
        reverse=True
    )

    return ses[0]


def lap_time(value):
    if not isinstance(value, (int, float)):
        return "-"

    mins = int(value // 60)
    secs = value % 60

    return f"{mins}:{secs:06.3f}"


def session_name(s):
    typ = s.get("session_type", "")

    names = {
        "Practice": "PRACTICE",
        "Qualifying": "QUALIFYING",
        "Race": "RACE",
        "Sprint": "SPRINT",
        "Sprint Qualifying": "SPRINT QUALIFYING",
        "Sprint Shootout": "SPRINT SHOOTOUT"
    }

    return names.get(
        typ,
        typ.upper() if typ else "UNKNOWN"
    )


def live():
    base = "https://api.openf1.org/v1"

    token = os.getenv("OPENF1_TOKEN")

    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    stop = threading.Event()

    key_thread = threading.Thread(
        target=exit_key,
        args=(stop,),
        daemon=True
    )

    key_thread.start()

    while not stop.is_set():
        try:
            ses = current_session(
                base,
                headers
            )

            os.system("cls" if os.name == "nt" else "clear")

            if ses is None:
                latest = latest_session(
                    base,
                    headers
                )

                if latest:
                    latest_name = session_name(latest)
                    latest_country = latest.get(
                        "country_name",
                        "-"
                    )
                else:
                    latest_name = "-"
                    latest_country = "-"

                print(f"""
+--------------------------------------------------------------+
|                         PITVIEW                              |
+--------------------------------------------------------------+
|                                                              |
|                  NO SESSION IN PROGRESS                      |
|                                                              |
|  Latest session: {latest_name:<40}    |
|  Country:        {latest_country:<40}    |
|                                                              |
|  PITVIEW is waiting for the next session.                    |
|                                                              |
|  Press C to close                                            |
|                                                              |
+--------------------------------------------------------------+
""")

                if stop.wait(10):
                    break

                continue

            key = ses["session_key"]
            name = session_name(ses)
            country = ses.get("country_name", "-")

            drv_data = data(
                f"{base}/drivers",
                params={"session_key": key},
                headers=headers
            )

            if not isinstance(drv_data, list):
                raise Exception("Invalid drivers response")

            drv = {}

            for d in drv_data:
                if not isinstance(d, dict):
                    continue

                num = d.get("driver_number")

                if num is None:
                    continue

                drv[num] = {
                    "acr": d.get(
                        "name_acronym",
                        "-"
                    ),
                    "team": d.get(
                        "team_name",
                        "-"
                    )
                }

            pos_data = data(
                f"{base}/position",
                params={"session_key": key},
                headers=headers
            )

            lap_data = data(
                f"{base}/laps",
                params={"session_key": key},
                headers=headers
            )

            if not isinstance(pos_data, list):
                raise Exception("Invalid position response")

            if not isinstance(lap_data, list):
                raise Exception("Invalid laps response")

            pos = {}

            for p in pos_data:
                if not isinstance(p, dict):
                    continue

                num = p.get("driver_number")

                if num not in drv:
                    continue

                date = p.get("date", "")

                if (
                    num not in pos
                    or date > pos[num].get(
                        "date",
                        ""
                    )
                ):
                    pos[num] = p

            laps = {}

            for l in lap_data:
                if not isinstance(l, dict):
                    continue

                num = l.get("driver_number")

                if num not in drv:
                    continue

                date = l.get("date_start", "")

                if (
                    num not in laps
                    or date > laps[num].get(
                        "date_start",
                        ""
                    )
                ):
                    laps[num] = l

            dat = []

            for num, p in pos.items():
                d = drv[num]
                l = laps.get(num, {})

                dat.append({
                    "pos": p.get(
                        "position",
                        "-"
                    ),
                    "num": num,
                    "acr": d["acr"],
                    "team": d["team"],
                    "lap": l.get(
                        "lap_number",
                        "-"
                    ),
                    "time": lap_time(
                        l.get("lap_duration")
                    )
                })

            dat.sort(
                key=lambda x: (
                    x["pos"]
                    if isinstance(x["pos"], int)
                    else 999
                )
            )

            rows = ""

            for d in dat:
                rows += (
                    f"| {str(d['pos']):<4} "
                    f"| {str(d['num']):<6} "
                    f"| {d['acr']:<8} "
                    f"| {d['team']:<20} "
                    f"| {str(d['lap']):<6} "
                    f"| {d['time']:<12} |\n"
                )

            if not rows:
                rows = (
                    "| No live timing data available                                  |\n"
                )

            print(f"""
+--------------------------------------------------------------------------+
|                                  PITVIEW                                 |
+--------------------------------------------------------------------------+
|  {country:<30}{name:<39}|
+------+--------+----------+----------------------+--------+--------------+
| POS  | NUMBER | ACRONYM  | TEAM                 | LAP    | LAP TIME     |
+------+--------+----------+----------------------+--------+--------------+
{rows.rstrip()}
+------+--------+----------+----------------------+--------+--------------+
| Drivers: {len(dat):<10}Session: {name:<35}|
|                                                                          |
| Refresh: 4s                                      Press C to close       |
+--------------------------------------------------------------------------+
""")

            if stop.wait(4):
                break

        except requests.RequestException as error:
            os.system("cls" if os.name == "nt" else "clear")

            err = str(error)[:51]

            print(f"""
+--------------------------------------------------------------+
|                         PITVIEW                              |
+--------------------------------------------------------------+
|                                                              |
|  CONNECTION ERROR                                            |
|  {err:<58}|
|                                                              |
|  Press C to close                                            |
|                                                              |
+--------------------------------------------------------------+
""")

            if stop.wait(5):
                break

        except Exception as error:
            os.system("cls" if os.name == "nt" else "clear")

            err = str(error)[:51]

            print(f"""
+--------------------------------------------------------------+
|                         PITVIEW                              |
+--------------------------------------------------------------+
|                                                              |
|  ERROR: {err:<51}|
|                                                              |
|  Press C to close                                            |
|                                                              |
+--------------------------------------------------------------+
""")

            if stop.wait(5):
                break


while True:
    os.system("cls" if os.name == "nt" else "clear")

    print(f"""
+--------------------------------------------------------------+
|                         PITVIEW                              |
+--------------------------------------------------------------+
|                                                              |
|  Press 1 to view live results                                |
|  Press 2 to view this season's drivers                       |
|  Press x to quit                                             |
|                                                              |
+--------------------------------------------------------------+""")

    choice = readchar.readchar()

    if choice == "1":
        live()
    elif choice == "2":
        drivers()
        input("Press Enter to return to the main menu...")
    elif choice.lower() == "x" or choice == "0":
        break

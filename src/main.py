import os
from dotenv import load_dotenv
import requests
import time
from datetime import datetime

load_dotenv()

SECRET_KEY = os.getenv("BKK_API_KEY")

endpoint = "https://futar.bkk.hu/api/query/v1/ws/otp/api/where/arrivals-and-departures-for-stop.json"
becsi_ut_stopid = "BKK_F02743"
kelenfold_stopid = "BKK_F02744"
BKK_YELLOW = "\033[38;5;220m"
RESET = "\033[0m"
BLUE = '\033[38;5;26m'
last_successful_update = None

def get_route_number(stop_time, references):
    trip_id = stop_time["tripId"]
    trip = references["trips"][trip_id]

    route_id = trip["routeId"]
    route = references["routes"][route_id]

    return route["shortName"]

def get_stop_times(stop_id):
    params = {
    "key": SECRET_KEY,
    "onlyDepartures": True,
    "minutesBefore": 0,
    "minutesAfter": 60,
    "stopId": stop_id,
    }

    response = requests.get(
    url=endpoint, 
    params=params,
    timeout=15)

    response.raise_for_status()
    data = response.json()

    return {
    "stop_times": data["data"]["entry"]["stopTimes"],
    "references": data["data"]["references"]
    }

def get_departure_time(stop_time):
    if "predictedDepartureTime" in stop_time:
        return stop_time["predictedDepartureTime"]
    
    return stop_time["departureTime"]

def create_departures(stop_data):
    departures = []
    for stop_time in stop_data["stop_times"]: 
        departure = {
            "route_number": get_route_number(stop_time=stop_time, references=stop_data["references"]),
            "departure_time": get_departure_time(stop_time),
            "terminus": stop_time["stopHeadsign"],
            "is_predicted": "predictedDepartureTime" in stop_time,
            "wheelchair_accessible": stop_time["wheelchairAccessible"]
        }
        departures.append(departure)
    return departures

def get_next_departures():
    becsi_data = get_stop_times(becsi_ut_stopid)
    kelenfold_data = get_stop_times(kelenfold_stopid)
    current_time = time.time()

    becsi_departures = create_departures(becsi_data)
    kelenfold_departures = create_departures(kelenfold_data)
    
    all_departures = becsi_departures + kelenfold_departures
    all_departures.sort(key=lambda departure: departure["departure_time"])
    last_successful_update = datetime.now()
    return all_departures[:5], current_time, last_successful_update

def display_departures(departures, current_time, last_successful_update):
    print("\033[2J\033[H", end="")
    print(f"{BKK_YELLOW}JÁRAT   IRÁNY                           INDULÁS{RESET}")
    print(f"{BKK_YELLOW}------------------------------------------------{RESET}")
    for departure in departures:
        minutes_until_departure = round((departure["departure_time"] - current_time) / 60)

        marker_text = ""
        if departure["terminus"] in (
        "Kelenföld vasútállomás M",
        "Népliget M",
        ):
            marker_text += "R"
        route_text = departure["route_number"]
        terminus_text = departure["terminus"]
        status_text = "(élő)" if departure["is_predicted"] else "(menetrendi)"
        if departure["wheelchair_accessible"]:
            marker_text += "A"
        if minutes_until_departure <= 0:
            departure_text = "MOST"
        else:
            departure_text = f"{minutes_until_departure} perc"

        route_text = f'{route_text:<4}'
        terminus_text = f'{terminus_text:<32}'
        departure_text = f'{departure_text:>8}'
        status_text = f'{status_text:<12}'
 
        txt = (
            f"{BKK_YELLOW}"
            f"{marker_text:<3}"
            f'{route_text}'
            f'{terminus_text}'
            f"{departure_text:>8} "
            f"{status_text}"
            f"{RESET}"
        )
        print(txt)
    print(f"{BKK_YELLOW}R - Rita irány                  {RESET}", end="")
    print(f"{BKK_YELLOW}A - akadálymentesített{RESET}")
    print(f"{BLUE}Frissítve: {last_successful_update.strftime("%H:%M:%S")} {RESET}")

def display_error(message, last_successful_update):
    print("\033[2J\033[H", end="")
    print("BKK KIJELZŐ")
    print("------------")
    print(message)
    print("Újrapróbálkozás...")
    if last_successful_update:
        print(f'Az utolsó frissítés: {last_successful_update.strftime("%H:%M:%S")}')
    else: 
        print("Még nem történt sikeres frissítés.")

while True:
    try:
        next_departures, current_time, last_successful_update = get_next_departures()
        display_departures(
            departures=next_departures,
            current_time=current_time,
            last_successful_update=last_successful_update
        )
    except requests.exceptions.Timeout:
        display_error(
            message="A BKK API nem válaszolt időben.",
            last_successful_update=last_successful_update
            )

    except requests.exceptions.ConnectionError:
        display_error(
            message="Nincs hálózati kapcsolat.",
            last_successful_update=last_successful_update
            )

    except requests.exceptions.HTTPError as error:
        display_error(
            message=f"HTTP-hiba történt: {error}",
            last_successful_update=last_successful_update
            )

    except Exception as error:
        display_error(
            message=f"Váratlan hiba történt: {type(error).__name__}: {error}",
            last_successful_update=last_successful_update
        )
    except KeyboardInterrupt:
        print("\nA kijelző leállítva.")
        break

    time.sleep(15)

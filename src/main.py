import os
from dotenv import load_dotenv
import requests
import time

load_dotenv()

SECRET_KEY = os.getenv("BKK_API_KEY")

endpoint = "https://futar.bkk.hu/api/query/v1/ws/otp/api/where/arrivals-and-departures-for-stop.json"
becsi_ut_stopid = "BKK_F02743"
kelenfold_stopid = "BKK_F02744"

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
    "current_time": data["currentTime"] / 1000,
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
            "is_predicted": "predictedDepartureTime" in stop_time
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
    return all_departures[:5], current_time

def display_departures(departures, current_time):
    os.system("cls")
    for departure in departures:
        minutes_until_departure = round((departure["departure_time"] - current_time) / 60)

        if departure["is_predicted"]:
            txt = f'{departure["route_number"]} - {departure["terminus"]} - {minutes_until_departure} perc múlva (becsült)'
        else:
            txt = f'{departure["route_number"]} - {departure["terminus"]} - {minutes_until_departure} perc múlva (menetrendi)'
            
        print(txt)

while True:
    next_departures, current_time = get_next_departures()
    display_departures(departures=next_departures,current_time=current_time)
    time.sleep(10)


import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("aviation_key")


def aviation_funtion(query):

    url = "http://api.aviationstack.com/v1/flights"
    para = {"access_key": api_key, "limit": 5}

    request = requests.get(url, params=para)

    data = request.json()

    flights = []

    if "data" in data:
        for flight in data["data"][:5]:
            airline = flight.get("airline", {}).get("name", "unknown")
            departure = flight.get("departure", {}).get("airport", "unknown")
            arival = flight.get("arrival", {}).get("airport", "unknown")
            status = flight.get("flight_status", "unknown")

            flights.append(f"""
    airline:{airline}
    departure:{departure}
    arival:{arival}
    status:{status}
""")

    return "\n".join(flights)
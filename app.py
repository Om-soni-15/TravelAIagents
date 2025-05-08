import streamlit as st
from datetime import date
from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents.agent_types import AgentType
import os
from datetime import datetime, timedelta
import pytz
import requests
import urllib.parse
import json
from dotenv import load_dotenv
import time

# ============================
# Gemini API Key Setup
# ============================
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HOTELS_API_KEY = os.getenv("Hotels_API_KEY")
IRCTC_API_KEY = os.getenv("IRCTC_API_KEY")

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")

#  Weather Fetching Func

def get_maps_places(location, search_text="Most Popular places in "):
    search_query = search_text + location
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json?query=" + \
                 urllib.parse.quote(search_query) + \
                 f"&radius=20000&key={WEATHER_API_KEY}"

    search_response = requests.get(search_url)
    if search_response.status_code != 200:
        raise Exception(
            f"Failed to fetch search results. Received: {search_response.status_code} {search_response.reason}"
        )
    search_data = search_response.json()
    return search_data["results"][0]["geometry"]["location"]
def get_weather(destination):
    destination_info = get_maps_places(destination)
    url = f"https://weather.googleapis.com/v1/forecast/days:lookup?key={WEATHER_API_KEY}&location.latitude={destination_info["lat"]}&location.longitude={destination_info["lng"]}&days=10"
    response = requests.get(url)
    data = response.json()
    return data


def parse_weather_data(destination, start_date, end_date):
    weather_data = get_weather(destination)
    forecast_days = weather_data['forecastDays']
    time_zone = pytz.timezone(weather_data['timeZone']['id'])

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    forecast_map = {
        datetime(year=day['displayDate']['year'],
                 month=day['displayDate']['month'],
                 day=day['displayDate']['day']).date(): day
        for day in forecast_days
    }
    current_date = start

    day_counter = 1
    parsed_weather = {}

    while current_date <= end:
        day_key = f"Day {day_counter}"
        if current_date in forecast_map:

            day = forecast_map[current_date]
            day_info = day['daytimeForecast']
            night_info = day['nighttimeForecast']
            sun = day['sunEvents']

            parsed_weather[day_key] = {
                "condition_day": day_info['weatherCondition']['description']['text'],
                "condition_night": night_info['weatherCondition']['description']['text'],
                "max_temp": day['maxTemperature']['degrees'],
                "min_temp": day['minTemperature']['degrees'],
                "feels_like_max": day['feelsLikeMaxTemperature']['degrees'],
                "feels_like_min": day['feelsLikeMinTemperature']['degrees'],
                "humidity_day": day_info['relativeHumidity'],
                "humidity_night": night_info['relativeHumidity'],
                "rain_chance": day_info['precipitation']['probability']['percent'],
                "sunrise": datetime.fromisoformat(sun['sunriseTime'].replace("Z", "+00:00")).astimezone(
                    time_zone).strftime("%I:%M %p"),
                "sunset": datetime.fromisoformat(sun['sunsetTime'].replace("Z", "+00:00")).astimezone(
                    time_zone).strftime("%I:%M %p")
            }
        else:
            parsed_weather[day_key] = "Weather data not available for this day"
        current_date += timedelta(days=1)
        day_counter += 1

    return parsed_weather

# Hotels fetching func
def get_destination_data(query):
    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
    querystring = {"query": query}

    headers = {
        "x-rapidapi-key":HOTELS_API_KEY ,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

    data = response.json()

    if not data["status"] or not data["data"]:
        raise ValueError("No destination data found")

    # Pick the top result (most relevant)
    top_result = data["data"][0]

    destination_data = {
        "name": top_result.get("name"),
        "dest_id": top_result.get("dest_id"),
        "latitude": top_result.get("latitude"),
        "longitude": top_result.get("longitude"),
        "nr_hotels": top_result.get("nr_hotels"),
        "image_url": top_result.get("image_url")
    }
    return destination_data


def search_hotels(city_name, start_date, end_date, adults):
    destination_info = get_destination_data(city_name)
    if not destination_info:
        print("Destination not found.")
        return None

    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    headers = {
        "x-rapidapi-key": HOTELS_API_KEY,
        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
    }
    country_code = destination_info.get("cc1", "IN")

    all_hotels = []
    page_number = 1
    max_pages = 5  # Set a reasonable limit to avoid excessive API calls
    has_more_pages = True

    while has_more_pages and page_number <= max_pages:
        params = {
            "dest_id": destination_info["dest_id"],
            "search_type": destination_info.get("search_type", "city").upper(),
            "adults": str(adults),
            "children_age": "0,17",
            "room_qty": "1",
            "page_number": str(page_number),
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": "INR",
            "country_code": country_code,
            "arrival_date": start_date,
            "departure_date": end_date
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise exception for HTTP errors

            data = response.json()

            # Check the structure of the response
            if isinstance(data, dict) and "data" in data:
                if "hotels" in data["data"] and isinstance(data["data"]["hotels"], list):
                    current_page_hotels = data["data"]["hotels"]
                    all_hotels.extend(current_page_hotels)

                    # Check if there are more pages
                    if len(current_page_hotels) == 0:
                        has_more_pages = False
                        print(f"No more hotels found after page {page_number - 1}")
                    elif "meta" in data["data"]:
                        meta = data["data"]["meta"]
                        if isinstance(meta, dict) and "page_number" in meta and "total_pages" in meta:
                            current_page = int(meta["page_number"])
                            total_pages = int(meta["total_pages"])
                            print(f"Page {current_page} of {total_pages}")

                            if current_page >= total_pages:
                                has_more_pages = False
                                print("Reached the last page")
                        else:
                            # If we can't determine total pages but got results, try the next page
                            print(f"Got {len(current_page_hotels)} hotels on page {page_number}")
                else:
                    print("No hotels data found in the response")
                    has_more_pages = False
            else:
                print("Unexpected response format")
                has_more_pages = False

            page_number += 1

            # Add a delay to avoid rate limiting
            time.sleep(1.5)

        except Exception as e:
            print(f"Error fetching page {page_number}: {str(e)}")
            break

    print(f"Total hotels collected: {len(all_hotels)}")
    return {
        "total_hotels": len(all_hotels),
        "hotels": all_hotels
    }

def parse_hotel_info(city_name, start_date, end_date,adults):
    hotels_data =search_hotels(city_name, start_date, end_date,adults)
    results = []
    for hotel in hotels_data["hotels"]:
        prop = hotel["property"]
        price_info = prop["priceBreakdown"]
        total = round(price_info["grossPrice"]["value"] + price_info["excludedPrice"]["value"])
        info = {
            "name": prop["name"],
            "rating": f'{prop.get("accuratePropertyClass", "N/A")} out of 5',
            "review_score": f'{prop.get("reviewScore", "N/A")} ({prop.get("reviewScoreWord", "")})',
            "review_count": prop.get("reviewCount", "N/A"),
            "checkin": prop["checkin"],
            "checkout": prop["checkout"],
            "price(incl_taxes)": total,
            "free_cancellation": "YES" if "Free cancellation" in hotel["accessibilityLabel"] else "NO",
            "no_prepayment": "YES" if "No prepayment" in hotel["accessibilityLabel"] else "NO",
            "photo": prop["photoUrls"][0] if prop.get("photoUrls") else "No image",
            "longitude": prop.get("longitude", "N/A"),
            "latitude": prop.get("latitude", "N/A")
        }
        results.append(info)
    return results

# train details
def get_station_code(city_name):
    prompt = f"What is the main railway station code (IRCTC code) for the city {city_name}? Just return the station code, nothing else."
    response = llm.invoke(prompt)
    return response.content.strip().upper()
def get_train_details(from_station: str, to_station: str, date_of_journey: str):
    url = "https://irctc1.p.rapidapi.com/api/v3/trainBetweenStations"

    querystring = {
        "fromStationCode": from_station,
        "toStationCode": to_station,
        "dateOfJourney": date_of_journey
    }

    headers = {
        "x-rapidapi-host": "irctc1.p.rapidapi.com",
        "X-RapidAPI-Key": IRCTC_API_KEY
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}")

    data = response.json()

    if data.get("status") != True or "data" not in data:
        raise Exception("Invalid API response")

    trains_info = []
    for train in data["data"]:
        trains_info.append({
            "train_name": train.get("train_name"),
            "train_number": train.get("train_number"),
            "departure_time": train.get("from_std"),
            "arrival_time": train.get("to_std"),
            "duration": train.get("duration"),
            "classes": train.get("class_type", [])
        })

    return trains_info

def get_trains_to_and_from_city(from_city, to_city, start_date, end_date):
    try:
        from_station = get_station_code(from_city)
        to_station = get_station_code(to_city)

        # Get trains to the city (arrival)
        trains_to_city = get_train_details(from_station, to_station, start_date)

        # Get trains from the city (departure)
        trains_from_city = get_train_details(to_station, from_station, end_date)

        return {
            "to_city": {
                "from": from_city,
                "to": to_city,
                "date": start_date,
                "trains": trains_to_city
            },
            "from_city": {
                "from": to_city,
                "to": from_city,
                "date": end_date,
                "trains": trains_from_city
            }
        }

    except Exception as e:
        return {"error": str(e)}



# Tool Wrapper
class WeatherTool:
    def __call__(self, to_city: str, start_date: str, end_date: str) -> str:
        try:
            weather = parse_weather_data(to_city, start_date, end_date)
            return json.dumps(weather, indent=2)
        except Exception as e:
            return f"Could not get weather data. Error: {str(e)}"

class HotelTool:
    def __call__(self, to_city: str,start_date:str, end_date:str,adults) -> str:
        try:
            return parse_hotel_info(to_city,start_date, end_date,adults)
        except Exception as e:
            return f"Hotel tool failed: {str(e)}"

class TrainTool:
    def __call__(self,from_city: str, to_city: str, start_date: str,end_date: str) -> str:
        try :
            return get_trains_to_and_from_city(from_city, to_city, start_date, end_date)
        except Exception as e:
            return f"Trains tool failed:{str(e)}"


# LangChain Tools Setup
tools = [
    Tool(
        name="get_weather_forecast",
        func=lambda x: WeatherTool()(to_city, str(start_date), str(end_date)),
        description="Gets summarized weather for trip days. Used internally in itinerary planning."
    ),
    Tool(
        name="get_hotels",
        func=lambda x: HotelTool()(to_city,start_date, end_date,adults),
        description="Gives list of hotels data in given city and number of adults"
    ),
    Tool(
        name="get_trains",
        func=lambda x: TrainTool()(from_city, to_city, start_date,end_date),
        description="Gives list of trains, for from_city to to_city on start_date and to_city to from_city on end_date"
    )
]


agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

# ============================
# Streamlit App
# ============================
st.set_page_config(page_title="AI Travel Planner", page_icon="🌍")
st.title("🤖 AI Travel Planner")

from_city = st.text_input("From City", "Delhi")
to_city = st.text_input("To City", "Varanasi")
start_date = st.date_input("Start Date", date.today())
end_date = st.date_input("End Date")
adults = st.number_input("Number of adults traveling", value=2, min_value=1)
budget = st.number_input("Budget (INR)", min_value=5000, value=15000)

if st.button("Generate Itinerary"):
    with st.spinner("Generating..."):
        query = f"""
                Plan a detailed family trip from {from_city} to {to_city}:
                - Dates: {start_date} to {end_date}
                - Number of People: {adults}
                - Budget: ₹{budget}
                
                Include:
                1. How to reach (train/bus/flight):
                    -steps for getting train data 
                            1) call get_trains once for {from_city} to {to_city}
                            2) it will return a list of trains data including train name ,departure ,arrival, duration,price for both on start date and end date.
                            3) your task is suggest best 3 trains for traveling to city and 3 trains for returning.(suggestion includes minimum travel duration,all night travel is prefered for saving time in trip, and classes availbale should be good)
                            4) give train names, travel time ,departure and arrival and classes.
                            if api fails to fetch train data then tell 'no train data found due to api limit exausted' nothing else.
                2. Local travel options(Don't give this at above or below of itinerary ,instead of give this with day wise plan for better understanding)
                3. Places to visit each day (with timings and time needed at each place)
                4. What to pack
                5. Call `get_hotels` once and get all hotel information. 
                    - You are a travel assistant. Based on the itinerary you have made, recommend top 3 best-reviewed hotels for a trip to {to_city}.
                    - Total budget: ₹{budget} for {adults} people
                    - Hotels should be affordable, well-reviewed , and closer to most of the places in the itinerary so user has to travel minimum.(do this by comparing lat,long of hotels) 
                    - cleanliness, and service.
                    - Give names, short description, and approx price per night ,also tell this hotel is near by this famous location(i.e hotel is near to kashi vishwanath temple), aslo provide link of photo (in hotels_data output there is one output like photo.)
                    if api fails to fetch hotels data then tell 'no hotel data found due to api limit exausted' nothing else.
                6. Total estimated cost breakdown
                7. Call `get_weather_forecast` once for the full range: {to_city}, {start_date}, {end_date}'.
                    - For Day 1: summarize  full weather info and say like this: temp will be around this to this,no humidity,if places are hill station then only tell about sunrise  and sunsets .
                    - From Day 2 onward:
                    - If weather is similar, just write: "Weather similar to Day 1"
                    - If weather changes (e.g., rain, high temp, strong wind), highlight only key changes or alerts.
                    - If weather is not available, just write: "Weather similar to Day 1"
                    if api fails to fetch weather data then tell 'no weather data found due to api limit exausted' nothing else.
                    
                important notes -> Add weather information only in day wise planning not outside it ,add outside only if it is only one day planning.
                                -> output should be in markdown format for better user experience in app and do not include extra unneccessary things.
                                 
                """

        result = agent.run(query)
        st.success("Travel itinerary generated successfully")
        st.markdown(result, unsafe_allow_html=True)



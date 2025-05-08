# 🌍 AI Travel Planner

**AI Travel Planner** is an intelligent itinerary planner built using **Streamlit**, **LangChain**, and the **Gemini API**. It helps users plan trips by automatically generating detailed travel plans including transportation options (like trains), weather forecasts, hotel suggestions, and activity recommendations—all tailored to your budget and preferences.

---

## 🚀 Features

- 📅 Smart Itinerary Generation using LLM (Gemini 1.5 Pro)
- ☁️ 10-Day Weather Forecast for the travel location
- 🏨 Hotel Search and Suggestions with pricing & facilities
- 🚆 IRCTC Train Search for both departure and return
- 🎯 Budget-Conscious Planning
- 🌐 Integrated with LangChain Agents and Tools
- 🖥️ Simple & interactive Streamlit UI

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **LLM**: Gemini 1.5 Pro via `langchain_google_genai`
- **APIs Used**:
  - Google Maps Places API
  - Google Weather API
  - Booking.com Hotels API (via RapidAPI)
  - IRCTC Train API (via RapidAPI)

---

## 🧠 How It Works

1. **User Input**:
   - Origin and destination cities
   - Start and end dates
   - Number of travelers
   - Budget

2. **LangChain Agent** uses three tools:
   - `get_weather_forecast`: Fetches detailed weather reports
   - `get_hotels`: Searches hotels based on location and dates
   - `get_trains`: Retrieves trains between origin and destination

3. **LLM (Gemini)** generates a comprehensive itinerary combining all fetched data.

---

## 🔧 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Om-soni-15/TravelAIagents.git
   cd TravelAIagents

2. **Install dependencies**:
  ```bash
   pip install -r requirements.txt
3. **Set up .env file** :
  Create a .env file in the root directory with your API keys:
    GEMINI_API_KEY=your_gemini_api_key
    WEATHER_API_KEY=your_google_weather_api_key
    HOTELS_API_KEY=your_rapidapi_hotels_api_key
    IRCTC_API_KEY=your_rapidapi_irctc_api_key
4. **Run the app** :
   ```bash
    streamlit run app.py
 

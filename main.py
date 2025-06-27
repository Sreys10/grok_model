from fastapi import FastAPI, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langserve import add_routes
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Load environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
weather_api_key = os.getenv("WEATHERAPI_API_KEY")

# Initialize Groq model
model = ChatGroq(model="Gemma2-9b-It", groq_api_key=groq_api_key)

# Define request model
class RecommendationRequest(BaseModel):
    user_prompt: str
    location: str
    date: str = None

app = FastAPI(
    title="Product Recommendation Agent",
    description="An AI agent that recommends products based on user needs, location, weather, and season.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_uv_risk(uv_index: float):
    if uv_index <= 2: return "Low"
    elif uv_index <= 5: return "Moderate"
    elif uv_index <= 7: return "High"
    elif uv_index <= 10: return "Very High"
    else: return "Extreme"

def get_weather(location: str):
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {'key': weather_api_key, 'q': location, 'aqi': 'no'}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        current = data['current']
        return {
            'temperature': current['temp_c'],
            'conditions': current['condition']['text'],
            'description': current['condition']['text'],
            'humidity': current['humidity'],
            'wind_speed': current['wind_kph'],
            'feels_like': current['feelslike_c'],
            'uv_index': current['uv'],
            'is_day': current['is_day'] == 1,
            'precipitation': current['precip_mm']
        }
    except Exception as e:
        logger.error(f"Weather API error: {str(e)}")
        return None

def get_product_categories():
    try:
        response = requests.get("https://dummyjson.com/products/categories", timeout=5)
        response.raise_for_status()
        categories = response.json()
        if isinstance(categories, list):
            return [str(category) for category in categories]
        return []
    except Exception as e:
        logger.error(f"Categories API error: {str(e)}")
        return []

def get_season(date_str: str = None):
    date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    month = date.month
    if month in [12, 1, 2]: return "winter"
    elif month in [3, 4, 5]: return "spring"
    elif month in [6, 7, 8]: return "summer"
    else: return "autumn"

system_template = """
You are a professional product recommendation assistant. Recommend products based on:
1. User's request: {user_prompt}
2. Weather: {weather_conditions} ({temperature}°C, feels like {feels_like}°C)
3. Season: {season}
4. UV Index: {uv_index} ({uv_risk})
5. Precipitation: {precipitation} mm
6. Time: {day_night}

Guidelines:
- Recommend specific, practical products
- Consider weather and season
- Provide brief explanations
- Format as bullet points
- Only suggest plausible products

Available Categories: {categories}
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_template),
    ("user", "{user_prompt}")
])

chain = prompt_template | model | StrOutputParser()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.post("/recommend")
async def recommend_products(request: RecommendationRequest):
    try:
        weather = get_weather(request.location) or {
            'temperature': 'unknown', 'feels_like': 'unknown',
            'conditions': 'unknown', 'description': 'unknown',
            'humidity': 'unknown', 'wind_speed': 'unknown',
            'uv_index': 'unknown', 'precipitation': 'unknown',
            'is_day': True
        }
        
        uv_risk = get_uv_risk(weather['uv_index']) if weather['uv_index'] != 'unknown' else "unknown"
        season = get_season(request.date)
        categories = get_product_categories()
        categories_str = ", ".join(categories) if categories else "No categories available"
        
        inputs = {
            "user_prompt": request.user_prompt,
            "location": request.location,
            "temperature": weather['temperature'],
            "feels_like": weather['feels_like'],
            "weather_conditions": weather['conditions'],
            "weather_description": weather['description'],
            "humidity": weather['humidity'],
            "wind_speed": weather['wind_speed'],
            "uv_index": weather['uv_index'],
            "uv_risk": uv_risk,
            "precipitation": weather['precipitation'],
            "day_night": "Day" if weather['is_day'] else "Night",
            "season": season,
            "categories": categories_str
        }
        
        recommendations = chain.invoke(inputs)
        
        return {
            "recommendations": recommendations,
            "weather": weather,
            "season": season,
            "location": request.location
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

add_routes(app, chain, path="/chain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
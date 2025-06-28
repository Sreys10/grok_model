from fastapi import FastAPI, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define request model
class RecommendationRequest(BaseModel):
    user_prompt: str

app = FastAPI(
    title="Complete Product Recommender",
    description="Displays products with images, prices, and all details",
    version="6.0"
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

model = ChatGroq(model="Gemma2-9b-It", groq_api_key=os.getenv("GROQ_API_KEY"))

def search_dummyjson_products(query: str, limit: int = 5):
    """Search products on DummyJSON API"""
    try:
        response = requests.get(
            "https://dummyjson.com/products/search",
            params={'q': query, 'limit': limit},
            timeout=10
        )
        response.raise_for_status()
        products = response.json().get('products', [])
        
        # Format product data consistently
        formatted_products = []
        for product in products:
            formatted_products.append({
                'id': product.get('id'),
                'title': product.get('title', 'Unknown Product'),
                'description': product.get('description', 'No description available'),
                'price': f"${product.get('price', 0):.2f}",
                'discount': product.get('discountPercentage', 0),
                'rating': product.get('rating', 0),
                'stock': product.get('stock', 0),
                'brand': product.get('brand', 'Unknown Brand'),
                'category': product.get('category', 'Uncategorized'),
                'thumbnail': product.get('thumbnail', '/static/no-image.png'),
                'images': product.get('images', [])
            })
        return formatted_products
    except Exception as e:
        logger.error(f"Product search error: {str(e)}")
        return []

def extract_product_names(text_recommendations: str):
    """Extract product names from AI recommendations"""
    product_names = []
    for line in text_recommendations.split('\n'):
        if line.strip().startswith('-'):
            # Extract product name before parenthesis
            product_name = re.sub(r'\(.*?\)', '', line[1:]).strip()
            product_names.append(product_name)
    return product_names

system_prompt = """
You are a shopping assistant that recommends real products from our inventory.
When user asks: {user_prompt}

Recommend 3-5 specific products with:
- Exact product names that exist in our database
- Brief reason for recommendation in parentheses
- Format: "- Product Name (reason)"

Example:
- iPhone 15 (latest model with great camera)
- Samsung Galaxy Book3 (powerful laptop for work)
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "{user_prompt}")
])

chain = prompt_template | model | StrOutputParser()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.post("/recommend")
async def recommend_products(request: RecommendationRequest):
    try:
        # Get text recommendations from AI
        text_recs = chain.invoke({"user_prompt": request.user_prompt})
        
        # Extract product names from recommendations
        product_names = extract_product_names(text_recs)
        
        # Search for each product in DummyJSON
        products = []
        for name in product_names[:5]:  # Limit to 5 products
            found_products = search_dummyjson_products(name, limit=1)
            if found_products:
                products.append(found_products[0])  # Take the first match
        
        return {
            "text_recommendations": text_recs,
            "products": products
        }
        
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
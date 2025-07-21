import json
import re
import requests
from typing import Dict, Any, Optional


class OllamaConnector:
    """Connector for Ollama local LLM"""
    
    def __init__(self, model: str = "gemma:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.7) -> str:
        """Generate text using Ollama"""
        if not prompt or not prompt.strip():
            return "Error: Empty prompt provided"
            
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": max(0.0, min(1.0, temperature))  # Clamp temperature
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return f"LLM Error: {result['error']}"
                
            response_text = result.get("response", "").strip()
            if not response_text:
                return "Error: Empty response from LLM"
                
            return response_text
        except requests.exceptions.Timeout:
            return "Error: Request to LLM timed out"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Make sure it's running with 'ollama run llama3'"
        except requests.exceptions.RequestException as e:
            return f"Error: Ollama request failed - {str(e)}"
        except json.JSONDecodeError:
            return "Error: Invalid JSON response from Ollama"
        except Exception as e:
            return f"Error: Unexpected error - {str(e)}"
    
    def classify_intent(self, user_query: str) -> Dict[str, Any]:
        """Classify user intent using JSON-only prompt"""
        if not user_query or not user_query.strip():
            return {"intent": "unknown", "city": None, "days": None, "cuisine": None}
            
        # Escape quotes in user query to prevent JSON issues
        safe_query = user_query.replace('"', '\\"')
        
        prompt = f"""You are a travel query classifier. Extract intent and entities from user queries.

TASK: Return only a JSON object with these exact keys: intent, city, days, cuisine

USER QUERY: "{safe_query}"

INTENT must be one of:
- "weather_lookup" for weather questions
- "hotspots_list" for attractions/sightseeing
- "food_reco" for restaurant/food recommendations  
- "trip_plan" for multi-day itineraries

CITY: Extract any city name mentioned (capitalize properly). If no city mentioned, use null.
DAYS: Extract number of days for trips. If not mentioned, use null.
CUISINE: Extract cuisine type for food queries. If not mentioned, use null.

Examples:
"weather in Tokyo" → {{"intent":"weather_lookup","city":"Tokyo","days":null,"cuisine":null}}
"best ramen restaurants in Kyoto" → {{"intent":"food_reco","city":"Kyoto","days":null,"cuisine":"ramen"}}
"what's the best fast food in Kyoto" → {{"intent":"food_reco","city":"Kyoto","days":null,"cuisine":"fast food"}}
"Kyoto best restaurant" → {{"intent":"food_reco","city":"Kyoto","days":null,"cuisine":null}}
"attractions in Tokyo" → {{"intent":"hotspots_list","city":"Tokyo","days":null,"cuisine":null}}
"3 day trip to Kyoto" → {{"intent":"trip_plan","city":"Kyoto","days":3,"cuisine":null}}
"what to see in Kyoto" → {{"intent":"hotspots_list","city":"Kyoto","days":null,"cuisine":null}}

Now classify: "{safe_query}"

JSON:"""
        
        response = self.generate(prompt, temperature=0.3)
        
        print(f"🔍 [LLM] Raw response: {response[:200]}...")  # Show first 200 chars
        
        # Handle error responses from generate()
        if response.startswith("Error:"):
            print(f"❌ [LLM] Error in generate(): {response}")
            return {"intent": "unknown", "city": None, "days": None, "cuisine": None, "error": response}
        
        # Try to extract JSON from response
        try:
            # Handle case where LLM might add extra text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                
                # Clean malformed JSON with explanatory text in values
                # Fix patterns like: "city": "KYOTO" (capitalized) -> "city": "KYOTO"
                json_str = re.sub(r'"([^"]+)"\s*\([^)]+\)', r'"\1"', json_str)
                # Fix patterns like: "city": KYOTO (no quotes) -> "city": "KYOTO"
                json_str = re.sub(r':\s*([A-Za-z][A-Za-z0-9_]*)\s*\(', r': "\1" (', json_str)
                # Remove any remaining parenthetical explanations after values
                json_str = re.sub(r'"\s*\([^)]+\)', r'"', json_str)
                
                print(f"🔍 [LLM] Extracted JSON: {json_str}")
                parsed = json.loads(json_str)
                
                # Validate required fields exist
                if "intent" not in parsed:
                    parsed["intent"] = "unknown"
                if "city" not in parsed:
                    parsed["city"] = None
                if "days" not in parsed:
                    parsed["days"] = None
                if "cuisine" not in parsed:
                    parsed["cuisine"] = None
                
                # Normalize city name to lowercase for file matching
                if parsed["city"] and isinstance(parsed["city"], str):
                    parsed["city"] = parsed["city"].strip().lower()
                    
                return parsed
            else:
                # Fallback parsing
                print(f"❌ [LLM] No JSON found in response")
                return {"intent": "unknown", "city": None, "days": None, "cuisine": None}
        except json.JSONDecodeError as e:
            print(f"❌ [LLM] JSON decode error: {str(e)}")
            return {"intent": "unknown", "city": None, "days": None, "cuisine": None}
    
    def format_response(self, intent: str, data: Dict[str, Any], **kwargs) -> str:
        """Format response based on intent and data"""
        if intent == "weather_lookup":
            return self._format_weather(data, kwargs.get("city", ""))
        elif intent == "hotspots_list":
            return self._format_hotspots(data, kwargs.get("city", ""))
        elif intent == "food_reco":
            return self._format_restaurants(data, kwargs.get("city", ""), kwargs.get("cuisine"))
        elif intent == "trip_plan":
            return self._format_trip_plan(data, kwargs.get("city", ""), kwargs.get("days", 1))
        else:
            return "I couldn't understand your request. Please try asking about weather, hotspots, restaurants, or trip planning."
    
    def _format_weather(self, weather_data: Dict[str, Any], city: str) -> str:
        """Format weather data into natural language"""
        if not weather_data or "error" in weather_data:
            return f"Sorry, I couldn't find weather information for {city}."
        
        current = weather_data.get("current", {})
        if not current:
            return f"Sorry, weather data for {city} is incomplete."
            
        # Ensure we have basic weather info
        temp = current.get('temperature', 'Unknown')
        conditions = current.get('conditions', 'Unknown')
        wind = current.get('wind', 'Unknown')
        
        prompt = f"""Given this weather data for {city}:
Temperature: {temp}°C
Conditions: {conditions}
Wind: {wind}

Write a brief, natural weather report in 1-2 sentences."""
        
        response = self.generate(prompt, temperature=0.5)
        
        # If LLM fails, provide fallback
        if response.startswith("Error:"):
            return f"The weather in {city} is currently {temp}°C with {conditions} conditions and {wind}."
            
        return response
    
    def _format_hotspots(self, hotspots_data: Dict[str, Any], city: str) -> str:
        """Format hotspots into natural language"""
        if not hotspots_data or "error" in hotspots_data or not hotspots_data.get("hotspots"):
            return f"Sorry, I couldn't find hotspot information for {city}."
        
        hotspots = hotspots_data["hotspots"][:3]  # Top 3
        if not hotspots:
            return f"No attractions found for {city}."
            
        # Safe extraction with fallbacks
        hotspot_list = []
        for h in hotspots:
            name = h.get('name', 'Unknown attraction')
            description = h.get('description', 'No description available')
            hotspot_list.append(f"- {name}: {description}")
        
        hotspot_text = "\n".join(hotspot_list)
        
        prompt = f"""Given these top attractions in {city}:
{hotspot_text}

Write a brief, engaging summary of must-visit places in 2-3 sentences."""
        
        response = self.generate(prompt, temperature=0.5)
        
        # If LLM fails, provide fallback
        if response.startswith("Error:"):
            return f"Top attractions in {city} include: " + ", ".join([h.get('name', 'Unknown') for h in hotspots]) + "."
            
        return response
    
    def _format_restaurants(self, restaurant_data: Dict[str, Any], city: str, cuisine: Optional[str]) -> str:
        """Format restaurant recommendations"""
        if not restaurant_data or "error" in restaurant_data or not restaurant_data.get("restaurants"):
            return f"Sorry, I couldn't find restaurant information for {city}."
        
        restaurants = restaurant_data["restaurants"]
        if cuisine:
            # Filter by cuisine if specified
            filtered = [r for r in restaurants if cuisine and cuisine.lower() in r.get("cuisine", "").lower()]
            restaurants = filtered if filtered else restaurants[:3]
        else:
            restaurants = restaurants[:3]
        
        if not restaurants:
            cuisine_msg = f" for {cuisine}" if cuisine else ""
            return f"No restaurants found{cuisine_msg} in {city}."
        
        # Safe extraction with fallbacks
        resto_list = []
        for r in restaurants:
            name = r.get('name', 'Unknown restaurant')
            specialty = r.get('specialty', 'No specialty listed')
            price_range = r.get('price_range', '$')
            resto_list.append(f"- {name}: {specialty} ({price_range})")
        
        resto_text = "\n".join(resto_list)
        
        prompt = f"""Given these restaurant recommendations in {city}:
{resto_text}

Write a brief, appetizing summary of dining options in 2-3 sentences."""
        
        response = self.generate(prompt, temperature=0.5)
        
        # If LLM fails, provide fallback
        if response.startswith("Error:"):
            names = [r.get('name', 'Unknown') for r in restaurants]
            return f"Great dining options in {city} include: " + ", ".join(names) + "."
            
        return response
    
    def _format_trip_plan(self, all_data: Dict[str, Any], city: str, days: int) -> str:
        """Format a multi-day trip itinerary"""
        weather = all_data.get("weather", {})
        hotspots = all_data.get("hotspots", {}).get("hotspots", [])
        restaurants = all_data.get("restaurants", {}).get("restaurants", [])
        
        # Validate inputs
        if not city or not city.strip():
            return "Sorry, I need a city name to plan a trip."
            
        if days <= 0 or days > 14:
            return "Sorry, I can only plan trips between 1 and 14 days."
        
        if not hotspots or not restaurants:
            return f"Sorry, I need more information to plan a trip to {city}."
        
        # Ensure we have enough data for the number of days
        if len(hotspots) < days:
            hotspots = hotspots * ((days // len(hotspots)) + 1)  # Repeat if needed
        if len(restaurants) < days:
            restaurants = restaurants * ((days // len(restaurants)) + 1)
        
        try:
            prompt = f"""You are a travel planner.
City: {city}  Days: {days}

WEATHER: {json.dumps(weather.get('forecast', [])[:days], ensure_ascii=False)}
HOTSPOTS: {json.dumps(hotspots[:min(len(hotspots), days*2)], ensure_ascii=False)}
RESTAURANTS: {json.dumps(restaurants[:min(len(restaurants), days*2)], ensure_ascii=False)}

Create a {days}-day itinerary for {city}.
Write a friendly, natural trip plan in paragraph form. Include specific places and restaurants for each day."""
            
            response = self.generate(prompt, temperature=0.5)
            
            # If LLM fails, provide basic fallback
            if response.startswith("Error:"):
                basic_plan = f"Here's a {days}-day plan for {city}: "
                for i in range(min(days, len(hotspots))):
                    day_num = i + 1
                    hotspot = hotspots[i].get('name', f'Attraction {day_num}')
                    restaurant = restaurants[i % len(restaurants)].get('name', f'Restaurant {day_num}')
                    basic_plan += f"Day {day_num}: Visit {hotspot} and dine at {restaurant}. "
                return basic_plan
                
            return response
            
        except Exception as e:
            return f"Sorry, I encountered an error planning your trip to {city}. Please try again."
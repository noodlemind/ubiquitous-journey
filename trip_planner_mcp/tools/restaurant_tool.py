import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from difflib import get_close_matches


class RestaurantTool:
    """Tool for fetching restaurant data from local JSON files"""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to data/restaurants relative to project root
            self.data_dir = Path(__file__).parent.parent / "data" / "restaurants"
    
    def get_restaurants(self, city: str, cuisine: Optional[str] = None, 
                       price_range: Optional[str] = None) -> Dict[str, Any]:
        """Fetch restaurant data for a given city, optionally filtered by cuisine or price"""
        if not city or not city.strip():
            return {
                "error": "City name is required",
                "available_cities": self._get_available_cities()
            }
        
        # Sanitize city name to prevent path traversal attacks
        safe_city = "".join(c for c in city.lower() if c.isalnum() or c in ('-', '_')).strip()
        if not safe_city:
            return {
                "error": f"Invalid city name: {city}",
                "available_cities": self._get_available_cities()
            }
        
        city_file = self.data_dir / f"{safe_city}.json"
        
        if not city_file.exists():
            # Try fuzzy matching for similar city names
            available_cities = [f.stem for f in self.data_dir.glob("*.json") if f.is_file()]
            matches = get_close_matches(safe_city, available_cities, n=1, cutoff=0.6)
            
            if matches:
                print(f"🔍 [RESTAURANT TOOL] City '{city}' not found, using fuzzy match: '{matches[0]}'")
                city_file = self.data_dir / f"{matches[0]}.json"
                safe_city = matches[0]
            else:
                return {
                    "error": f"Restaurant data not available for {city}",
                    "available_cities": self._get_available_cities()
                }
        
        try:
            with open(city_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate data structure
            if not isinstance(data, dict):
                return {"error": f"Invalid restaurant data format for {city}"}
                
            if "city" not in data:
                data["city"] = city.title()
                
            if "restaurants" not in data:
                data["restaurants"] = []
            
            restaurants = data.get("restaurants", [])
            
            # Apply filters with validation
            if cuisine and cuisine.strip():
                safe_cuisine = cuisine.strip().lower()
                restaurants = [
                    r for r in restaurants 
                    if isinstance(r, dict) and safe_cuisine in r.get("cuisine", "").lower()
                ]
            
            if price_range and price_range.strip():
                safe_price_range = price_range.strip()
                restaurants = [
                    r for r in restaurants 
                    if isinstance(r, dict) and r.get("price_range", "") == safe_price_range
                ]
            
            # Update data with filtered results
            data["restaurants"] = restaurants
            if cuisine and cuisine.strip():
                data["filtered_by_cuisine"] = cuisine
            if price_range and price_range.strip():
                data["filtered_by_price"] = price_range
            
            return data
            
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in restaurant data file for {city}: {str(e)}"}
        except FileNotFoundError:
            return {
                "error": f"Restaurant data file not found for {city}",
                "available_cities": self._get_available_cities()
            }
        except PermissionError:
            return {"error": f"Permission denied reading restaurant data for {city}"}
        except Exception as e:
            return {"error": f"Unexpected error reading restaurant data for {city}: {str(e)}"}
    
    def get_top_restaurants(self, city: str, cuisine: Optional[str] = None, 
                           limit: int = 3) -> List[Dict[str, Any]]:
        """Get top-rated restaurants for a city"""
        if limit <= 0:
            return []
            
        data = self.get_restaurants(city, cuisine)
        
        if "error" in data:
            return []
        
        restaurants = data.get("restaurants", [])
        if not restaurants:
            return []
        
        # Filter valid restaurants and sort by rating
        valid_restaurants = [r for r in restaurants if isinstance(r, dict)]
        sorted_restaurants = sorted(valid_restaurants, key=lambda x: x.get("rating", 0), reverse=True)
        return sorted_restaurants[:limit]
    
    def get_by_price_range(self, city: str, price_range: str) -> List[Dict[str, Any]]:
        """Get restaurants by price range ($, $$, $$$, $$$$)"""
        if not price_range or not price_range.strip():
            return []
            
        data = self.get_restaurants(city, price_range=price_range)
        
        if "error" in data:
            return []
        
        restaurants = data.get("restaurants", [])
        # Filter to ensure we only return valid restaurant dictionaries
        return [r for r in restaurants if isinstance(r, dict)]
    
    def _get_available_cities(self) -> list:
        """Get list of cities with available restaurant data"""
        try:
            if not self.data_dir.exists():
                return []
            
            cities = []
            for file in self.data_dir.glob("*.json"):
                if file.is_file():  # Ensure it's actually a file
                    cities.append(file.stem.capitalize())
            return sorted(cities)
        except Exception:
            return []
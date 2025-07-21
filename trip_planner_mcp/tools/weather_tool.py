import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from difflib import get_close_matches


class WeatherTool:
    """Tool for fetching weather data from local JSON files"""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to data/weather relative to project root
            self.data_dir = Path(__file__).parent.parent / "data" / "weather"
    
    def get_weather(self, city: str) -> Dict[str, Any]:
        """Fetch weather data for a given city"""
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
                print(f"🔍 [WEATHER TOOL] City '{city}' not found, using fuzzy match: '{matches[0]}'")
                city_file = self.data_dir / f"{matches[0]}.json"
                safe_city = matches[0]  # Update for consistent logging
            else:
                return {
                    "error": f"Weather data not available for {city}",
                    "available_cities": self._get_available_cities()
                }
        
        try:
            with open(city_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Validate that we got actual weather data
            if not isinstance(data, dict):
                return {"error": f"Invalid weather data format for {city}"}
                
            # Ensure required structure exists
            if "city" not in data:
                data["city"] = city.title()
                
            return data
            
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in weather data file for {city}: {str(e)}"}
        except FileNotFoundError:
            return {
                "error": f"Weather data file not found for {city}",
                "available_cities": self._get_available_cities()
            }
        except PermissionError:
            return {"error": f"Permission denied reading weather data for {city}"}
        except Exception as e:
            return {"error": f"Unexpected error reading weather data for {city}: {str(e)}"}
    
    def _get_available_cities(self) -> list:
        """Get list of cities with available weather data"""
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
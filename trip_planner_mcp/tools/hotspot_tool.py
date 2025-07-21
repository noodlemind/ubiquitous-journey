import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from difflib import get_close_matches


class HotspotTool:
    """Tool for fetching hotspot/attraction data from local JSON files"""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to data/hotspots relative to project root
            self.data_dir = Path(__file__).parent.parent / "data" / "hotspots"
    
    def get_hotspots(self, city: str, hotspot_type: Optional[str] = None) -> Dict[str, Any]:
        """Fetch hotspot data for a given city, optionally filtered by type"""
        if not city or not city.strip():
            return {
                "error": "City name is required",
                "available_cities": self._get_available_cities()
            }
        
        # Sanitize city name
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
                print(f"🔍 [HOTSPOT TOOL] City '{city}' not found, using fuzzy match: '{matches[0]}'")
                city_file = self.data_dir / f"{matches[0]}.json"
                safe_city = matches[0]
            else:
                return {
                    "error": f"Hotspot data not available for {city}",
                    "available_cities": self._get_available_cities()
                }
        
        try:
            with open(city_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate data structure
            if not isinstance(data, dict):
                return {"error": f"Invalid hotspot data format for {city}"}
                
            if "city" not in data:
                data["city"] = city.title()
                
            if "hotspots" not in data:
                data["hotspots"] = []
            
            # Filter by type if specified
            if hotspot_type and hotspot_type.strip() and "hotspots" in data:
                safe_type = hotspot_type.strip().lower()
                filtered_hotspots = [
                    h for h in data["hotspots"] 
                    if isinstance(h, dict) and h.get("type", "").lower() == safe_type
                ]
                data["hotspots"] = filtered_hotspots
                data["filtered_by"] = hotspot_type
            
            return data
            
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in hotspot data file for {city}: {str(e)}"}
        except FileNotFoundError:
            return {
                "error": f"Hotspot data file not found for {city}",
                "available_cities": self._get_available_cities()
            }
        except PermissionError:
            return {"error": f"Permission denied reading hotspot data for {city}"}
        except Exception as e:
            return {"error": f"Unexpected error reading hotspot data for {city}: {str(e)}"}
    
    def get_top_hotspots(self, city: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get top-rated hotspots for a city"""
        if limit <= 0:
            return []
            
        data = self.get_hotspots(city)
        
        if "error" in data:
            return []
        
        hotspots = data.get("hotspots", [])
        if not hotspots:
            return []
        
        # Filter valid hotspots and sort by rating
        valid_hotspots = [h for h in hotspots if isinstance(h, dict)]
        sorted_hotspots = sorted(valid_hotspots, key=lambda x: x.get("rating", 0), reverse=True)
        return sorted_hotspots[:limit]
    
    def _get_available_cities(self) -> list:
        """Get list of cities with available hotspot data"""
        try:
            if not self.data_dir.exists():
                return []
            
            cities = []
            for file in self.data_dir.glob("*.json"):
                if file.is_file():
                    cities.append(file.stem.capitalize())
            return sorted(cities)
        except Exception:
            return []
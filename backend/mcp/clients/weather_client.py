from typing import Any, Dict, Optional
from datetime import date
import httpx
import json
from ..base_client import BaseMCPClient, MCPClientError


class WeatherMCPClient(BaseMCPClient):
    """
    MCP Client for OpenWeather API
    Fetches local weather based on IP geolocation
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("OPENWEATHER_API_KEY")
        self.http_client: Optional[httpx.AsyncClient] = None
        self.location: Optional[Dict[str, Any]] = None

    async def connect(self) -> bool:
        """Establish connection and detect location"""
        try:
            self.http_client = httpx.AsyncClient(timeout=30.0)

            # Get location from IP
            await self._detect_location()

            self.logger.info(f"Weather client connected - Location: {self.location.get('city', 'Unknown')}")
            return True
        except Exception as e:
            raise MCPClientError(f"Failed to connect to Weather API: {str(e)}")

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def _detect_location(self) -> None:
        """Detect location based on IP address"""
        try:
            # Use ipapi.co for free IP geolocation
            response = await self.http_client.get("https://ipapi.co/json/")
            response.raise_for_status()
            data = response.json()

            self.location = {
                "city": data.get("city", "Unknown"),
                "region": data.get("region", ""),
                "country": data.get("country_name", ""),
                "lat": data.get("latitude"),
                "lon": data.get("longitude"),
                "timezone": data.get("timezone", "UTC")
            }
        except Exception as e:
            self.logger.warning(f"Failed to detect location: {e}, using default")
            # Fallback to a default location (New York)
            self.location = {
                "city": "New York",
                "region": "NY",
                "country": "United States",
                "lat": 40.7128,
                "lon": -74.0060,
                "timezone": "America/New_York"
            }

    async def fetch_data(
        self,
        start_date: date,
        end_date: Optional[date] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch current weather and forecast

        Returns:
            Dictionary with 'current' and 'forecast' keys
        """
        if not self.location:
            await self._detect_location()

        current = await self.fetch_current_weather()
        forecast = await self.fetch_forecast()

        return {
            "current": current,
            "forecast": forecast,
            "location": self.location
        }

    async def fetch_current_weather(self) -> Dict[str, Any]:
        """Fetch current weather conditions"""
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": self.location["lat"],
                "lon": self.location["lon"],
                "appid": self.api_key,
                "units": "imperial"  # Fahrenheit
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return {
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "wind_speed": data["wind"]["speed"],
                "visibility": data.get("visibility", 0) / 1609.34,  # Convert to miles
                "pressure": data["main"]["pressure"]
            }

        except Exception as e:
            self.logger.error(f"Error fetching current weather: {str(e)}")
            raise MCPClientError(f"Failed to fetch current weather: {str(e)}")

    async def fetch_forecast(self) -> list:
        """Fetch 3-day forecast"""
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "lat": self.location["lat"],
                "lon": self.location["lon"],
                "appid": self.api_key,
                "units": "imperial",
                "cnt": 8  # 8 * 3-hour intervals = 24 hours
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            forecast = []
            for item in data["list"][:8]:  # Next 24 hours
                forecast.append({
                    "time": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "description": item["weather"][0]["description"],
                    "precipitation_chance": item.get("pop", 0) * 100  # Probability of precipitation
                })

            return forecast

        except Exception as e:
            self.logger.error(f"Error fetching forecast: {str(e)}")
            return []

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to OpenWeather API"""
        try:
            if not self.location:
                await self._detect_location()

            current = await self.fetch_current_weather()

            return {
                "connected": True,
                "location": f"{self.location['city']}, {self.location['region']}",
                "current_temp": current["temperature"],
                "timestamp": None
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "timestamp": None
            }

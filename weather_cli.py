import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
from tabulate import tabulate

class WeatherLogger:
    def __init__(self, api_key: str, data_file: str = "weather_data.json"):
        self.api_key = api_key
        self.data_file = data_file
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        
    def load_data(self) -> List[Dict]:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def save_data(self, data: List[Dict]) -> None:
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def kelvin_to_celsius(self, kelvin: float) -> float:
        return round(kelvin - 273.15, 2)
    
    def is_duplicate(self, city: str, existing_data: List[Dict]) -> bool:
        current_time = datetime.utcnow()
        two_hours_ago = current_time - timedelta(hours=2)
        
        for entry in existing_data:
            if entry['city'].lower() == city.lower():
                entry_time = datetime.fromisoformat(entry['utc_timestamp'])
                if entry_time > two_hours_ago:
                    return True
        return False
    
    async def fetch_weather(self, session: aiohttp.ClientSession, city: str) -> Optional[Dict]:
        try:
            url = f"{self.base_url}?q={city}&appid={self.api_key}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_info = {
                        'city': data['name'],
                        'temperature_celsius': self.kelvin_to_celsius(data['main']['temp']),
                        'weather_description': data['weather'][0]['description'],
                        'humidity': data['main']['humidity'],
                        'utc_timestamp': datetime.utcnow().isoformat(),
                        'local_timestamp': datetime.now().isoformat()
                    }
                    return weather_info
                else:
                    print(f"Error fetching data for {city}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching data for {city}: {str(e)}")
            return None
    
    async def fetch_multiple_cities(self, cities: List[str]) -> List[Dict]:
        existing_data = self.load_data()
        new_entries = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for city in cities:
                city = city.strip()
                if not self.is_duplicate(city, existing_data):
                    tasks.append(self.fetch_weather(session, city))
            
            if tasks:
                results = await asyncio.gather(*tasks)
                new_entries = [result for result in results if result is not None]
        
        if new_entries:
            all_data = existing_data + new_entries
            self.save_data(all_data)
            print(f"Successfully logged weather data for {len(new_entries)} cities")
        
        return new_entries
    
    def view_all_logs(self) -> None:
        data = self.load_data()
        
        table_data = []
        for entry in data:
            table_data.append([
                entry['city'],
                f"{entry['temperature_celsius']}°C",
                entry['weather_description'].title(),
                f"{entry['humidity']}%",
                entry['local_timestamp'][:19]
            ])
        
        headers = ['City', 'Temperature', 'Description', 'Humidity', 'Timestamp']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    def get_city_averages(self) -> None:
        data = self.load_data()
        if not data:
            print("No data available for the avg temp")
        
        city_temps = {}
        for entry in data:
            city = entry['city']
            temp = entry['temperature_celsius']
            
            if city not in city_temps:
                city_temps[city] = []
            city_temps[city].append(temp)
            
        for city, temps in city_temps.items():
            avg_temp = round(sum(temps) / len(temps), 2)
            print(f"{city}: {avg_temp}°C (based on {len(temps)} readings)")
    
    def get_hottest_coldest(self) -> None:
        data = self.load_data()
        if not data:
            print("No weather data found")
            return
        
        if len(data) == 0:
            return
        
        hottest = max(data, key=lambda x: x['temperature_celsius'])
        coldest = min(data, key=lambda x: x['temperature_celsius'])
        
        print(f"Hottest: {hottest['city']} - {hottest['temperature_celsius']}°C")
        print(f"Recorded on: {hottest['local_timestamp'][:19]}")
        print(f"Coldest: {coldest['city']} - {coldest['temperature_celsius']}°C")
        print(f"Recorded on: {coldest['local_timestamp'][:19]}")
        

        current_time = datetime.now()
        twenty_four_hours_ago = current_time - timedelta(hours=24)
        
        recent_data = []
        for entry in data:
            entry_time = datetime.fromisoformat(entry['local_timestamp'])
            if entry_time > twenty_four_hours_ago:
                recent_data.append(entry)
        
        if recent_data:
            recent_hottest = max(recent_data, key=lambda x: x['temperature_celsius'])
            recent_coldest = min(recent_data, key=lambda x: x['temperature_celsius'])
            print(f"Hottest: {recent_hottest['city']} - {recent_hottest['temperature_celsius']}°C")
            print(f"Coldest: {recent_coldest['city']} - {recent_coldest['temperature_celsius']}°C")
        else:
            print("\nNo data from the last 24 hours found.")
    
    def plot_temperature_trend(self) -> None:
        data = self.load_data()
        if not data:
            print("No weather data found!")
            return
        cities = list(set(entry['city'] for entry in data))
        
        print("\nAvailable cities:")
        for i, city in enumerate(cities, 1):
            print(f"{i}. {city}")
        
        try:
            choice = int(input("\nSelect city number: ")) - 1
            if choice < 0 or choice >= len(cities):
                print("Invalid choice!")
                return
            
            selected_city = cities[choice]
            
            city_data = [entry for entry in data if entry['city'] == selected_city]
            city_data.sort(key=lambda x: x['local_timestamp'])
                        
            timestamps = [datetime.fromisoformat(entry['local_timestamp']) for entry in city_data]
            temperatures = [entry['temperature_celsius'] for entry in city_data]

            plt.figure(figsize=(12, 6))
            plt.plot(timestamps, temperatures, marker='o', linestyle='-', linewidth=2, markersize=6)
            plt.title(f'Temperature Trend for {selected_city}', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Temperature (°C)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            os.makedirs('plots', exist_ok=True)
        
            filename = f"plots/{selected_city.lower().replace(' ', '_')}_temp_trend.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"\nPlot saved as: {filename}")
            

            plt.show()
            
        except ValueError:
            print("Please enter a valid number!")
        except Exception as e:
            print(f"Error creating plot: {str(e)}")

def main():
    api_key = input("Enter your OpenWeatherMap API key: ").strip()
    if not api_key:
        print("API key is required!")
        return
    
    logger = WeatherLogger(api_key)
    
    while True:
        print("="*20)
        print("1. Fetch and log weather for cities")
        print("2. View all logs (as table)")
        print("3. Get city-wise average temperature")
        print("4. Show hottest and coldest cities")
        print("5. Plot temperature trend for a city")
        print("6. Exit")
        print("="*20)
        
        try:
            choice = input("Select an option from(1 to 6): ").strip()
            
            if choice == '1':
                cities_input = input("Enter city names (comma-separated): ").strip()
                if cities_input:
                    cities = [city.strip() for city in cities_input.split(',')]
                    print(f"Fetching weather data for: {', '.join(cities)}")
                    asyncio.run(logger.fetch_multiple_cities(cities))
                else:
                    print("Please enter at least one city name!")
            
            elif choice == '2':
                logger.view_all_logs()
            
            elif choice == '3':
                logger.get_city_averages()
            
            elif choice == '4':
                logger.get_hottest_coldest()
            
            elif choice == '5':
                logger.plot_temperature_trend()
            
            elif choice == '6':
                print("Thank you")
                break
            
            else:
                print("Invalid choice! Please select 1-6.")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"An error occurred: {str(e)}")
main()
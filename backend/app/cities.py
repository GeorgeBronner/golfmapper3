# Dictionary of the 50 largest US cities and 5 largest Alabama cities with coordinates (latitude, longitude)
# Define the Enum class properly for FastAPI to create a dropdown
from enum import Enum

class CityName(str, Enum):
    # Define each city as a separate enum value
    # This needs to be explicit enum values, not dynamic __members__
    NEW_YORK = "New York"
    LOS_ANGELES = "Los Angeles"
    CHICAGO = "Chicago"
    HOUSTON = "Houston"
    PHOENIX = "Phoenix"
    PHILADELPHIA = "Philadelphia"
    SAN_ANTONIO = "San Antonio"
    SAN_DIEGO = "San Diego"
    DALLAS = "Dallas"
    SAN_JOSE = "San Jose"
    AUSTIN = "Austin"
    JACKSONVILLE = "Jacksonville"
    FORT_WORTH = "Fort Worth"
    COLUMBUS = "Columbus"
    INDIANAPOLIS = "Indianapolis"
    CHARLOTTE = "Charlotte"
    SAN_FRANCISCO = "San Francisco"
    SEATTLE = "Seattle"
    DENVER = "Denver"
    WASHINGTON_DC = "Washington DC"
    BOSTON = "Boston"
    EL_PASO = "El Paso"
    NASHVILLE = "Nashville"
    DETROIT = "Detroit"
    OKLAHOMA_CITY = "Oklahoma City"
    PORTLAND = "Portland"
    LAS_VEGAS = "Las Vegas"
    MEMPHIS = "Memphis"
    LOUISVILLE = "Louisville"
    BALTIMORE = "Baltimore"
    MILWAUKEE = "Milwaukee"
    ALBUQUERQUE = "Albuquerque"
    TUCSON = "Tucson"
    FRESNO = "Fresno"
    SACRAMENTO = "Sacramento"
    MESA = "Mesa"
    KANSAS_CITY = "Kansas City"
    ATLANTA = "Atlanta"
    LONG_BEACH = "Long Beach"
    COLORADO_SPRINGS = "Colorado Springs"
    RALEIGH = "Raleigh"
    OMAHA = "Omaha"
    MIAMI = "Miami"
    OAKLAND = "Oakland"
    MINNEAPOLIS = "Minneapolis"
    TULSA = "Tulsa"
    CLEVELAND = "Cleveland"
    WICHITA = "Wichita"
    ARLINGTON = "Arlington"
    NEW_ORLEANS = "New Orleans"
    BIRMINGHAM = "Birmingham"
    HUNTSVILLE = "Huntsville"
    MONTGOMERY = "Montgomery"
    MOBILE = "Mobile"
    TUSCALOOSA = "Tuscaloosa"

us_cities = {
    # 50 largest US cities by population
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Chicago": (41.8781, -87.6298),
    "Houston": (29.7604, -95.3698),
    "Phoenix": (33.4484, -112.0740),
    "Philadelphia": (39.9526, -75.1652),
    "San Antonio": (29.4241, -98.4936),
    "San Diego": (32.7157, -117.1611),
    "Dallas": (32.7767, -96.7970),
    "San Jose": (37.3382, -121.8863),
    "Austin": (30.2672, -97.7431),
    "Jacksonville": (30.3322, -81.6557),
    "Fort Worth": (32.7555, -97.3308),
    "Columbus": (39.9612, -82.9988),
    "Indianapolis": (39.7684, -86.1581),
    "Charlotte": (35.2271, -80.8431),
    "San Francisco": (37.7749, -122.4194),
    "Seattle": (47.6062, -122.3321),
    "Denver": (39.7392, -104.9903),
    "Washington DC": (38.9072, -77.0369),
    "Boston": (42.3601, -71.0589),
    "El Paso": (31.7619, -106.4850),
    "Nashville": (36.1627, -86.7816),
    "Detroit": (42.3314, -83.0458),
    "Oklahoma City": (35.4676, -97.5164),
    "Portland": (45.5051, -122.6750),
    "Las Vegas": (36.1699, -115.1398),
    "Memphis": (35.1495, -90.0490),
    "Louisville": (38.2527, -85.7585),
    "Baltimore": (39.2904, -76.6122),
    "Milwaukee": (43.0389, -87.9065),
    "Albuquerque": (35.0844, -106.6504),
    "Tucson": (32.2226, -110.9747),
    "Fresno": (36.7378, -119.7871),
    "Sacramento": (38.5816, -121.4944),
    "Mesa": (33.4152, -111.8315),
    "Kansas City": (39.0997, -94.5786),
    "Atlanta": (33.7490, -84.3880),
    "Long Beach": (33.7701, -118.1937),
    "Colorado Springs": (38.8339, -104.8214),
    "Raleigh": (35.7796, -78.6382),
    "Omaha": (41.2565, -95.9345),
    "Miami": (25.7617, -80.1918),
    "Oakland": (37.8044, -122.2711),
    "Minneapolis": (44.9778, -93.2650),
    "Tulsa": (36.1540, -95.9928),
    "Cleveland": (41.4993, -81.6944),
    "Wichita": (37.6872, -97.3301),
    "Arlington": (32.7357, -97.1081),
    "New Orleans": (29.9511, -90.0715),

    # 5 largest Alabama cities
    "Birmingham": (33.5186, -86.8104),
    "Huntsville": (34.7304, -86.5861),
    "Montgomery": (32.3792, -86.3077),
    "Mobile": (30.6954, -88.0399),
    "Tuscaloosa": (33.2098, -87.5692)
}

# Example of accessing the data
print(f"New York coordinates: {us_cities['New York']}")
print(f"Birmingham coordinates: {us_cities['Birmingham']}")
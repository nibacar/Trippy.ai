import googlemaps
import re  # For removing HTML tags

api_key = 'AIzaSyCr1WhJtX6cLLu6UCMUVGiKm4mnmuGD6E8'
gmaps = googlemaps.Client(key=api_key)

def geocode_address(address):
    geocode_result = gmaps.geocode(address)
    location = geocode_result[0]['geometry']['location']
    return location

def reverse_geocode(lat, lng):
    reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
    return reverse_geocode_result[0]['formatted_address']

def calc_dist(origins, destinations):
    distance_matrix = gmaps.distance_matrix(origins, destinations, mode='driving')
    distance = distance_matrix['rows'][0]['elements'][0]['distance']['text']
    duration = distance_matrix['rows'][0]['elements'][0]['duration']['text']
    print(f"Distance: {distance}, Duration: {duration}")
    return distance, duration

def get_directions(origin, destination):
    directions = gmaps.directions(origin, destination, mode='driving')
    steps = directions[0]['legs'][0]['steps']
    
    print(f"\nDriving directions from {origin} to {destination}:\n")
    for i, step in enumerate(steps):
        # Remove HTML tags like <b>, <div>, etc.
        instruction = re.sub('<[^<]+?>', '', step['html_instructions'])
        print(f"{i+1}. {instruction}")

# Example Usage:
print("Location:", geocode_address('New York, NY'))
print("Reverse Geocode:", reverse_geocode(40.7127753, -74.0059728))
calc_dist(['New York, NY'], ['Los Angeles, CA'])
get_directions('New York, NY', 'Los Angeles, CA')

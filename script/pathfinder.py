import googlemaps

api_key = 'AIzaSyBezo_DR2t44RmfP--NIZ3v9iclRclfoHQ'
gmaps = googlemaps.Client(key=api_key)

def geocode_address(address):
    geocode_result = gmaps.geocode(address)
    location = geocode_result[0]['geometry']['location']
    return location

print(geocode_address('New York, NY'))

def reverse_geocode(lat, lng):
    reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
    return reverse_geocode_result[0]['formatted_address']

print(reverse_geocode(40.7127753, -74.0059728))

def calc_dist(origins, destinations):
    distance_matrix = gmaps.distance_matrix(origins, destinations, mode='driving')
    distance = distance_matrix['rows'][0]['elements'][0]['distance']['text']
    duration = distance_matrix['rows'][0]['elements'][0]['duration']['text']
    print(distance, duration)

calc_dist(['New York, NY'], ['Los Angeles, CA'])

def get_directions(origin, destination):
    directions = gmaps.directions(origin, destination, mode='driving')
    steps = directions[0]['legs'][0]['steps']
    for step in steps:
        print(step['html_instructions'])

print(get_directions('New York, NY', 'Los Angeles, CA'))

# Kuwait Taxi Rank, Site C, Khayelitsha - verified GPS
CODETA_START = [-34.01519, 18.64867]  # Kuwait Taxi Rank, Site C, Khayelitsha

ROUTE_COORDS = {
# All verified taxi rank coordinates + real road waypoints via N2
    "Claremont": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.96500, 18.56000],  # N2 highway midpoint
        [-33.98163, 18.46642],  # Claremont Taxi Rank
    ],
    "Wynberg": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.98800, 18.64500],  # N2 on-ramp
        [-33.96000, 18.58000],  # N2 west
        [-33.95000, 18.55000],  # Crossroads
        [-33.94500, 18.52000],  # M5 off-ramp
        [-33.97000, 18.48000],  # M5 south
        [-33.99470, 18.46310],  # Wynberg Taxi Rank, Maynard St
    ],
    "Cape Town": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.98800, 18.64500],  # N2 on-ramp
        [-33.96000, 18.58000],  # N2 west
        [-33.95000, 18.55000],  # Crossroads
        [-33.94000, 18.51000],  # N2 past Pinelands
        [-33.93000, 18.48000],  # De Waal Drive
        [-33.92345, 18.42614],  # Cape Town Taxi Rank, Adderley St
    ],
    "Mitchell's Plain": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-34.00200, 18.68000],  # Towards N2 east
        [-34.01000, 18.66000],  # N2 towards Mitchells Plain
        [-34.02000, 18.64000],  # Westridge area
        [-34.03500, 18.62500],  # Westridge Mall
        [-34.04430, 18.61470],  # Mitchell's Plain Town Centre Rank
    ],
    "Mitchell's Plain (Trek)": [
        [-34.01519, 18.64867],
        [-34.01000, 18.66000],
        [-34.04430, 18.61470],  # Mitchell's Plain Town Centre Rank
    ],
    "Nyanga": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.98800, 18.64500],  # N2 on-ramp
        [-33.97000, 18.61000],  # N2 west
        [-33.97560, 18.56080],  # Nyanga Taxi Rank
    ],
    "Gugulethu": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.98800, 18.64500],  # N2
        [-33.97000, 18.61000],  # N2 west
        [-33.96510, 18.54330],  # Gugulethu NY1
    ],
    "Langa": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.97000, 18.61000],
        [-33.96510, 18.54330],  # Gugulethu
        [-33.94860, 18.52470],  # Langa Taxi Rank
    ],
    "Bellville": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-33.98800, 18.64500],  # N2
        [-33.96000, 18.58000],  # N2 west
        [-33.95000, 18.55000],  # N2/N1 area
        [-33.93000, 18.55000],  # N1 north
        [-33.90514, 18.63089],  # Bellville Taxi Rank
    ],
    "Parow": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.95000, 18.55000],
        [-33.93000, 18.55000],
        [-33.90514, 18.63089],  # Bellville
        [-33.89720, 18.59280],  # Parow Taxi Rank
    ],
    "Eersterivier": [
        [-34.01519, 18.64867],  # Kuwait Taxi Rank Site C
        [-34.00200, 18.68000],  # Towards N2 east
        [-33.98000, 18.70000],  # N2 east
        [-33.95000, 18.72000],  # Eersterivier area
        [-33.94440, 18.73170],  # Eersterivier Taxi Rank
    ],
    "Delft": [
        [-34.01519, 18.64867],
        [-34.00200, 18.68000],
        [-33.97360, 18.70190],  # Delft Taxi Rank
    ],
    "Mfuleni": [
        [-34.01519, 18.64867],
        [-34.00500, 18.72000],
        [-34.00890, 18.72890],  # Mfuleni Taxi Rank
    ],
    "Kuils River": [
        [-34.01519, 18.64867],
        [-33.98000, 18.70000],
        [-33.93190, 18.73390],  # Kuils River Taxi Rank
    ],
    "Blackheath": [
        [-34.01519, 18.64867],
        [-33.98000, 18.70000],
        [-33.93190, 18.73390],
        [-33.91530, 18.73310],  # Blackheath Taxi Rank
    ],
    "Stellenbosch": [
        [-34.01519, 18.64867],
        [-33.98000, 18.70000],
        [-33.93190, 18.73390],
        [-33.93690, 18.86440],  # Stellenbosch Taxi Rank, Bird St
    ],
    "Paarl": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],  # Via Bellville
        [-33.80000, 18.80000],
        [-33.73420, 18.96310],  # Paarl Taxi Rank
    ],
    "Woodstock": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96000, 18.58000],
        [-33.94000, 18.51000],
        [-33.93000, 18.46000],
        [-33.92440, 18.44500],  # Woodstock Taxi Rank, Albert Rd
    ],
    "Athlone": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.97000, 18.61000],
        [-33.96510, 18.54330],  # Gugulethu
        [-33.95970, 18.49170],  # Athlone Taxi Rank, Klipfontein Rd
    ],
    "Mowbray": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96000, 18.58000],
        [-33.95000, 18.55000],
        [-33.94500, 18.52000],
        [-33.95000, 18.47360],  # Mowbray Taxi Rank
    ],
    "Epping": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96510, 18.54330],
        [-33.92860, 18.54470],  # Epping Taxi Rank
    ],
    "Pinelands": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96000, 18.58000],
        [-33.94080, 18.50640],  # Pinelands Taxi Rank
    ],
    "Goodwood": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96510, 18.54330],
        [-33.90030, 18.54860],  # Goodwood Taxi Rank
    ],
    "N1 City": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96000, 18.58000],
        [-33.93000, 18.55000],
        [-33.90690, 18.52830],  # N1 City Taxi Rank
    ],
    "Century City": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96000, 18.58000],
        [-33.93000, 18.55000],
        [-33.89000, 18.51140],  # Century City Taxi Rank
    ],
    "Somerset": [
        [-34.01519, 18.64867],
        [-33.92345, 18.42614],  # Via Cape Town CBD
        [-34.08330, 18.85000],  # Somerset West Taxi Rank
    ],
    "Sea Point": [
        [-34.01519, 18.64867],
        [-33.92345, 18.42614],  # Cape Town CBD
        [-33.91970, 18.38140],  # Sea Point Taxi Rank, Main Rd
    ],
    "Grabouw": [
        [-34.01519, 18.64867],
        [-33.93690, 18.86440],  # Stellenbosch
        [-34.15470, 19.01280],  # Grabouw Taxi Rank
    ],
    "Atlantis": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],  # Bellville
        [-33.58190, 18.49030],  # Atlantis Taxi Rank
    ],
    "Malmesbury": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],  # Bellville
        [-33.45940, 18.72920],  # Malmesbury Taxi Rank
    ],
    "Fishhoek": [
        [-34.01519, 18.64867],
        [-33.99470, 18.46310],  # Wynberg
        [-34.13830, 18.42750],  # Fish Hoek Taxi Rank
    ],
    "Blue Route": [
        [-34.01519, 18.64867],
        [-33.98163, 18.46642],  # Claremont
        [-34.03190, 18.44330],  # Blue Route Mall Taxi Rank
    ],
    "Tygerberg": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],  # Bellville
        [-33.87140, 18.62470],  # Tygerberg Taxi Rank
    ],
    "Elsies": [
        [-34.01519, 18.64867],
        [-33.98800, 18.64500],
        [-33.96510, 18.54330],
        [-33.92080, 18.55500],  # Elsies River Taxi Rank
    ],
    "Panorama": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],  # Bellville
        [-33.85970, 18.56690],  # Panorama Taxi Rank
    ],
    "Bothasig": [
        [-34.01519, 18.64867],
        [-33.90514, 18.63089],
        [-33.86970, 18.52890],  # Bothasig Taxi Rank
    ],
    "Killarney": [
        [-34.01519, 18.64867],
        [-33.92345, 18.42614],  # Cape Town CBD
        [-33.91000, 18.38690],  # Killarney Gardens Taxi Rank
    ],
    "Bracken Gate": [
        [-34.01519, 18.64867],
        [-34.01500, 18.62000],
        [-34.04330, 18.59170],  # Bracken Gate Taxi Rank
    ],
    "Centre Point": [
        [-34.01519, 18.64867],
        [-34.00200, 18.68000],
        [-34.04430, 18.61470],  # Centre Point (near Mitchells Plain)
    ],
    "Paddocks": [
        [-34.01519, 18.64867],
        [-33.92345, 18.42614],  # Cape Town CBD
        [-33.90030, 18.41330],  # Paddocks Taxi Rank
    ],
    "Parden Island": [
        [-34.01519, 18.64867],
        [-33.92345, 18.42614],
        [-33.88970, 18.49060],  # Paarden Eiland Taxi Rank
    ],
}

def get_route_coords(route_name: str):
    return ROUTE_COORDS.get(route_name, [
        CODETA_START,
        [-33.92345, 18.42614],  # Default Cape Town CBD
    ])

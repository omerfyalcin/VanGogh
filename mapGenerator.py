#!/usr/bin/env python3

import folium
import requests
import json

artist_id = "Q5582"  # Q5582 is van Gogh's wikidata id

# function to get SPARQL query result form Wikidata query endpoint as a
# dictionary


def get_query_result(query):
    wd_sparql = 'https://query.wikidata.org/sparql?format=json&query='
    r = requests.get(wd_sparql + query)
    res = json.loads(r.text)['results']['bindings']
    return res


# the query that'll provide the information for the map
map_query = '''
SELECT ?painting ?paintingLabel ?coord ?imagelink ?location ?locationLabel ?officialwebsite
WHERE
{
  ?painting wdt:P31 wd:Q3305213.
  ?painting wdt:P170 wd:''' + artist_id + '''.
  ?painting wdt:P276 ?location.
  ?painting wdt:P18 ?imagelink.
  ?location wdt:P625 ?coord.
  ?location wdt:P856 ?officialwebsite.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}
'''

# run the query
paintings_info = get_query_result(map_query)

# the API returns entities as URIs in the form http://www.wikidata.org/entity/QXXXXX
# function to extract the id (QXXXXX part)


def extract_id(field):
    return field['value'].split('/')[-1]


locations = {}
for item in paintings_info:
    location_id = extract_id(item['location'])
    painting_id = extract_id(item['painting'])
    if location_id not in locations:
        locations[location_id] = {painting_id: [item]}
    else:
        if painting_id not in locations[location_id]:
            locations[location_id][painting_id] = [item]
        else:
            locations[location_id][painting_id] += [item]

total_items = 0
for location_id in locations:
    for painting_id in locations[location_id]:
        total_items += len(locations[location_id][painting_id])

# make sure locations captured all the returned items
assert total_items == len(paintings_info)


# clean information, retain parts necessary for map
info = {}
for location_id in locations:
    counter = 0
    info[location_id] = {}
    info[location_id]['paintings'] = {}
    for painting_id in locations[location_id]:
        counter = counter + 1
        item = locations[location_id][painting_id][0]
        # if more than one result is returned with same painting id and same
        # location, record location information only on the first iteration
        if counter == 1:
            info[location_id]['location_name'] = item['locationLabel']['value']
            info[location_id]['location_coord'] = item['coord']['value'].split(
                'Point(')[-1].split(')')[0].split(' ')
            info[location_id]['location_coord'].reverse()
            info[location_id]['location_website'] = item['officialwebsite']['value']
        info[location_id]['paintings'][painting_id] = {}
        info[location_id]['paintings'][painting_id]['painting_name'] = item['paintingLabel']['value']
        info[location_id]['paintings'][painting_id]['imagelink'] = item['imagelink']['value']


# start from 30 lat, 0 long, since most paintings and people are in the
# Northern hemisphere.
map = folium.Map(
    location=[
        30,
        0],
    zoom_start=3,
    min_zoom=3,
    tiles="OpenStreetMap")

# put information in info on to map
for location_id in info:
    coord = info[location_id]['location_coord']
    html = '<h4 style="font-size:14px" ><strong><a href="{officialwebsite}" style = "color:black" target="_blank">{name}</a></strong></h4>'.format(
        name=info[location_id]['location_name'], officialwebsite=info[location_id]['location_website']) + '\n' + '<ul>'
    paired = sorted([[item['painting_name'], item['imagelink']]
                    for item in list(info[location_id]['paintings'].values())])
    html += '\n'.join(['<li><a href="{imagelink}" target="_blank">{painting_name}</a></li>'.format(
        imagelink=value[1], painting_name=value[0]) for value in paired])
    html += '</ul>'
    map.add_child(
        folium.Marker(
            coord,
            popup=folium.Popup(
                html,
                max_width=500,
                max_height=300)))

map.save('vanGogh.html')

# imports
import pandas as pd
import numpy as np
import requests
import json
import warnings

# fetch the google api keys
google_keys = [line.strip() for line in open('../../google-api-keys.txt', 'r')]
current_key = 0

def get_key():
    """
    returns: the current google api key
    """
    return google_keys[current_key]

def next_key():
    """
    sets current_key + 1 iff there is another key in the file, does nothing otherwise
    returns: True iff there is another key, false otherwise
    """
    global current_key
    n = current_key + 1
    if n >= len(google_keys):
        print('warning: Tried to switch keys, but there is no key left!!!')
        return False
    else:
        current_key = n
        print('info: Switching Key')
        return True

def cantons():
    """
    returns: a dict containing all cantons. Mapping the canton abbreviation to a list of different spellings of the canton
    """
    return  {
        'AG': ['Aargau'],
        'AR': ['Appenzell Ausserrhoden'], 
        'AI': ['Appenzell Innerrhoden'], 
        'BL': ['Basel-Land', 'Basel Land'], 
        'BS': ['Basel-Stadt', 'Basel Stadt'], 
        'BE': ['Bern'], 
        'FR': ['Fribourg', 'Freiburg'] ,  
        'GE': ['Genève', 'Genf'], 
        'GL': ['Glarus'], 
        'GR': ['Graubünden', 'Grischuns', 'Grigioni'],  
        'JU': ['Jura'],  
        'LU': ['Luzern'], 
        'NE': ['Neuchâtel', 'Neuenburg'], 
        'NW': ['Nidwalden'], 
        'OW': ['Obwalden'], 
        'SG': ['St.Gallen', 'St. Gallen'], 
        'SH': ['Schaffhausen'], 
        'SZ': ['Schwyz'], 
        'SO': ['Solothurn'], 
        'TG': ['Thurgau'], 
        'TI': ['Ticino', 'Tessin'], 
        'UR': ['Uri'], 
        'VD': ['Vaud', 'Waadt'], 
        'VS': ['Valais', 'Wallis'], 
        'ZG': ['Zug'],
        'ZH': ['Zürich']
    }

def find_canton_substring(name):
    """
    name: string
    returns: The canton abbreviation of a canton iff a canton name appears in the given string. othervise returns numpy.nan
    """
    for (canton_abbrev, canton_names) in cantons().items():
        for cn in canton_names:
            if cn in name:
                return canton_abbrev
    return np.nan

def find_canton_geonames(name):    
    url_search = 'http://api.geonames.org/searchJSON'
    params = {
        'name': name,
        'country': 'CH',
        'username': 'ada_account',
        'formatted': 'true',
        'type': 'json',
        'style': 'FULL',
        'fuzzy': '0.7',
        'orderby': 'relevance'
    }

    r = requests.get(url_search, params=params)
    answer = json.loads(r.text)
    ret = np.nan
    if answer['totalResultsCount'] != 0:
        #take the first since they are ordered by relevance
        ret = answer['geonames'][0]['adminCode1']
    return ret
    

def query_google_place_textsearch(query):
    """
    query: string - the query to be sent
    key: string - a api key registered with google
    returns: the full answer of the query as a python object
    """
    url_google_places = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    params = {
        'query' : query,
        'key': get_key()
    }
    r = requests.get(url_google_places, params=params)
    return json.loads(r.text)

def parse_google_place_textsearch_answer(answer):
    """
    answer: the answer of a google places textsearch
    returns: a dict: {
        number_answers: int # the number of answers
        #for each number answer
        0 : {
            place_id
            address
            geometry
            longitude 
            latitude
        }
        1: {
            ...
        }
    
    
    }
    """
    #print(answer)
    answer_map = {}
    results = answer['results']
    answer_map['status'] = answer['status']
    answer_map['number_answers'] = len(results)
    for idx, result in enumerate(results):
        answer_map[idx] = {}
        answer_map[idx]['place_id'] = result['place_id']
        answer_map[idx]['address'] = result['formatted_address']
        answer_map[idx]['geometry'] = result['geometry']
        answer_map[idx]['longitude'] = result['geometry']['location']['lng']
        answer_map[idx]['latitude'] = result['geometry']['location']['lat']
        
    return answer_map
    
def google_place_textsearch_for(uni_name):
    """
    uni_name: string
    returns: the parsed answers from google places textsearch
    """
    print('***************************************')
    print('query: '+ uni_name)
    query_res = query_google_place_textsearch(uni_name)
    print(query_res) # print the res
    if query_res['status'] == 'OVER_QUERY_LIMIT' and next_key():
        # if the key is over the query limit, and there is another key: try again ;)
        query_res = query_google_place_textsearch(uni_name)
        print('---------')
        print(query_res) # print the res again
    
    return parse_google_place_textsearch_answer(query_res)
    
def query_geonames_with_position(longitude, latitude):
    """
    makes a geonames request for the given longitude & latitude
    returns: the answers from geonames as a python object
    """
    #print('query for'+str(longitude)+' '+str(latitude))
    url_geonames_position = 'http://api.geonames.org/findNearbyJSON'
    params = { 
            'lat': latitude,
            'lng': longitude,
            'username': 'ada_account',
            'formatted': 'true',
            'type': 'json',
            'style': 'FULL',
            'orderby': 'relevance'
        }
    r = requests.get(url_geonames_position, params=params)
    return json.loads(r.text)
    
def cantons_from_geonames_answer(answer):
    """
    reads the canton abbreviations from the geonames answer
    returns: the canton abbreviations for a given query answer
    """
    #print(answer)
    canton_abbrevs = []
    for res in answer['geonames']:
        canton_abbrevs.append(res['adminCode1'])
    return canton_abbrevs
    
def cantons_for_university(uni_name):
    """
    uni_name: string
    returns: a list of candidate cantons for the given university name
    """
    google_res = google_place_textsearch_for(uni_name)
    #print(google_res)
    ctn_abbrevs = []
    for i in range(0, google_res['number_answers']):
        lat = google_res[i]['latitude']
        lng = google_res[i]['longitude']
        [ctn_abbrevs.append(c) for c in cantons_from_geonames_answer(query_geonames_with_position(lng, lat))]
        
    #print(ctn_abbrevs)
    return ctn_abbrevs
    
    
def canton_for_university(uni_name):
    """
    uni_name: string
    returns: a canton for the given university name, or numpy.nan if none was found
    """
    ctn_abbrevs = cantons_for_university(uni_name)
    
    # sanitize the cantons array:
    # (remove all entries that are not canton abbrevs)
    ctn_abbrevs = [c for c in ctn_abbrevs if c in list(cantons().keys())]
    # (remove duplicates)
    ctn_abbrevs = list(set(ctn_abbrevs))
    
    # ----- take the right canton ----
    # 0 results from google: try to match a substring. if no match take NaN
    # 1 result: take it
    # > 1 result: try substring, if no match warn the user and take the first one.
    
    ctn = np.nan
    if len(ctn_abbrevs) == 0:
        ctn = find_canton_substring(uni_name)
        
    if len(ctn_abbrevs) == 1:
        ctn = ctn_abbrevs[0]
        
    if len(ctn_abbrevs) > 1:
        ctn = find_canton_substring(uni_name)
        if ctn == np.nan:
            ctn = ctn_abbrevs[0]
        warnings.warn('several different cantons for '+ uni_name+' ('+str(ctn_abbrevs)+'). Taking: '+ str(ctn))
    return ctn

def map_universities_to_cantons(uni_names):
    """
    uni_names: list(string)
    returns: a mapping from each uni name to the canton, or nan if none is found
    """
    uni_canton_mapping = {}
    for uni_name in uni_names:
        uni_canton_mapping[uni_name] = canton_for_university(uni_name)
    return uni_canton_mapping
    
    
def get_language(abrev): 
    """
    returns: the list of languages of a canton. The list is sorted by main language
    """
    lang =   {
        'AG': ['D'],
        'AR': ['D'], 
        'AI': ['D'], 
        'BL': ['D'], 
        'BS': ['D'], 
        'BE': ['D', 'FR'], 
        'FR': ['FR', 'D'] ,  
        'GE': ['FR'], 
        'GL': ['D'], 
        'GR': ['D'],  
        'JU': ['FR'],  
        'LU': ['D'], 
        'NE': ['FR'], 
        'NW': ['D'], 
        'OW': ['D'], 
        'SG': ['D'], 
        'SH': ['D'], 
        'SZ': ['D'], 
        'SO': ['D'], 
        'TG': ['D'], 
        'TI': ['IT'], 
        'UR': ['D'], 
        'VD': ['FR'], 
        'VS': ['FR', 'D'], 
        'ZG': ['D'],
        'ZH': ['D']
    }
    return lang.get(abrev)
    






















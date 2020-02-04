#!/usr/bin/env python
# coding: utf-8

# # The Wine bar project 

# ### Introduction & Business problem

# In case my career as Data scientist fails (*let's hope it doesn't*), I want to open a wine bar in Paris, France. <br/> 
# Of course wine, **I'm french !** <br/>
# 
# The problem is that, from my experience, Paris has multiple areas where people go out for a drink and these areas are not concentrated but rather spread around the city. <br/>
# 
# Therefore, where is the best location to open a new wine bar to ensure enough clients to be successful ? <br/>
# 
# To ensure success, I need the bar to be in a location where the concentration of venues such as theaters, cinemas, restaurants demonstrates an active life in the area. Using the Foursquare data, I will geolocate the venues and find the best spot to open my wine bar.

# ### Data section

# To provide an analytical answer to the business problem of where to open my future wine bar in Paris I will do :<br/>
# - A segmentation of Paris inner-city using a .geojson file
# - Venues data related to the neighborhoods using Foursquare API (Category of the venue, customer rating, ...)

# ### Methodology

#  Section which represents the main component of the report where you discuss and describe any exploratory data analysis that you did, any inferential statistical testing that you performed, if any, and what machine learnings were used and why.

# In[1]:


import pandas as pd
import numpy as np
import requests
from pandas.io.json import json_normalize # tranform JSON file into a pandas dataframe
import folium # map rendering library
import json # library to handle JSON files
from geopy.geocoders import Nominatim # convert an address into latitude and longitude values
import geopy.distance
from math import sqrt


# #### Loading the Paris coordinates

# In[2]:


with open('arrondissements.geojson') as json_data:
    parisarr = json.load(json_data)
    
par_data = parisarr['features']
colnames = ['PostCode', 'Neighborhood', 'Latitude', 'Longitude']
dfparis = pd.DataFrame(columns=colnames)


# In[3]:


for d in par_data: 
    latlon = d['properties']['geom_x_y']
    code = d['properties']['c_ar']    
    neigh = d['properties']['l_aroff']
    
    lat = latlon[0]
    lon = latlon[1]
    dfparis= dfparis.append({'PostCode' : code, 'Neighborhood' : neigh, 'Latitude' : lat, 'Longitude' : lon}, ignore_index=True)   

dfparis.head()


# In[4]:


address = 'Paris, France'

geolocator = Nominatim(user_agent="par_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of Paris are {}, {}.'.format(latitude, longitude))


# #### Creation of a map of Paris, using Follium

# In[5]:


# create map of Paris using latitude and longitude values
map_paris = folium.Map(location=[latitude, longitude], zoom_start=12)

# add markers to map
for lat, lng, label in zip(dfparis['Latitude'], dfparis['Longitude'], dfparis['Neighborhood']):
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=0.7,
        parse_html=False).add_to(map_paris)  
    
map_paris


# The above map shows Paris with the the center coordinates of its 20 arrondissements (neighborhoods).

# In[6]:


df_coor = dfparis[['Latitude', 'Longitude']]
dfparis['Distance from center'] = ''


# In[7]:


#Function to calculate the distance of center coordinates of each neighborgood to the center of Paris
def calc_xy_distance(coords_1, coords_2):
    return geopy.distance.vincenty(coords_1, coords_2).m


# In[8]:


for i in range(0, len(df_coor)):
    dfparis['Distance from center'][i] = calc_xy_distance((df_coor['Latitude'][i], df_coor['Longitude'][i]), (latitude, longitude))
    
dfparis.head()


# Now let's identify the venues around each of these center coordinates of the city using the **Foursquare API**.

# #### Foursquare

# Let's use Foursquare API to get info on wine bars in each neighborhood.<br/>
# 
# We're interested in venues in 'Night life' category, since the density will indicate the activity of the area. Also, we are interested in areas where there is a good density of bars, nightclubs and pubs but less wine bars. We will include in out list only venues that have 'wine bar' in the category name.

# In[9]:


#Foursquare Credentials
CLIENT_ID = 'JO31W52NKMLMEQBPQ3GSRBK3FKRXIIJLIFKSRNDDTC5K1Q23' # your Foursquare ID
CLIENT_SECRET = 'XVGAMH0OCJG03ALF5ONIWJN3CJ5TOMKTST0ECRVRKQVCVHNL' # your Foursquare Secret


# Let's send a query to retrieve the venues using Foursquare API. To do so, we will send a query to Foursquare for each Paris' neighborhood coordinates and look for venues in the *Night life* category. <br/>

# In[10]:


# Category IDs corresponding to Night life, Bars and Wine bar were taken from Foursquare web site (https://developer.foursquare.com/docs/resources/categories):

category_id = '4d4b7105d754a06376d81259' #Night life
#= '4bf58dd8d48988d116941735' #Bar
sub_category_id = '4bf58dd8d48988d123941735' #Wine bar category


# In[26]:


bars = {}
wine_bars = {}
location_bars = []  


# In[30]:


for i in range(0, len(dfparis)):
    lat = dfparis['Latitude'][i]
    lon = dfparis['Longitude'][i]
    
    venues = get_venues_near_location(lat, lon, category_id, CLIENT_ID, CLIENT_SECRET, radius=500, limit=100)    
    area_bars = []
    
    for venue in venues:
        venue_id = venue[0]
        venue_name = venue[1]        
        venue_categories = venue[2]        
        venue_latlon = venue[3]
        venue_address = venue[4]
        venue_distance = venue[5]        
        venue_bar = (venue_id, venue_name, venue_latlon[0], venue_latlon[1], venue_address, venue_distance)
        
        if venue_categories[0][1] == sub_category_id:
            wine_bars[venue_id] = venue_bar


# In[31]:


wine_bars


# In[19]:


def is_bar(categories, specific_filter=None):
    wine_words = ['bar', 'wine', 'sausage', 'cheese', 'charcuterie', 'fromage', 'vin']
    wine = False
    specific = False
    for c in categories:
        category_name = c[0].lower()
        category_id = c[1]
        for r in wine_words:
            if r in category_name:
                bar = True
        if 'fast food' in category_name:
            restaurant = False
        if not(specific_filter is None) and (category_id in specific_filter):
            specific = True
            bar = True
    return bar, specific

def get_categories(categories):
    return [(cat['name'], cat['id']) for cat in categories]

def get_venues_near_location(lat, lon, category, client_id, client_secret, radius=500, limit=100):
    version = '20180724'
    url = 'https://api.foursquare.com/v2/venues/explore?client_id={}&client_secret={}&v={}&ll={},{}&categoryId={}&radius={}&limit={}'.format(
        client_id, client_secret, version, lat, lon, category, radius, limit)
    try:
        results = requests.get(url).json()['response']['groups'][0]['items']
        venues = [(item['venue']['id'],
                   item['venue']['name'],
                   get_categories(item['venue']['categories']),
                   (item['venue']['location']['lat'], item['venue']['location']['lng']),
                   format_address(item['venue']['location']),
                   item['venue']['location']['distance']) for item in results]        
    except:
        venues = []
    return venues


# In[12]:


LIMIT = 100 # limit of number of venues returned by Foursquare API

radius = 500 # define radius
# create URL
url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
    CLIENT_ID, 
    CLIENT_SECRET, 
    VERSION, 
    latitude, 
    longitude, 
    radius, 
    LIMIT)
url # display URL


# In[ ]:





# In[13]:


results = requests.get(url).json()
results


# In[ ]:





# In[ ]:





# ### Results

# In[ ]:





# In[ ]:





# ### Discussion

# In[ ]:





# In[ ]:





# ### Conclusion

# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





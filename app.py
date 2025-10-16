import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import osmnx as ox

# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="expanded")

st.title("Relocation Navigator")

# Sidebar ----------------------------------------------------
st.sidebar.markdown("## Sidebar")
address = st.sidebar.text_input("Enter an address:", value ="Skaldevägen 60")
POI_radius=st.sidebar.slider('Show PoIs within X m', min_value=100, max_value=3000, value=500)

# Main --------------------------------------------------------

# If user enters an address => find latitude and longitude
if st.sidebar.button("Go!"):
    

    if address:
        geolocator = Nominatim(user_agent="Navigator")
        location = geolocator.geocode(address)
    
        if location:
            lat, lon = location.latitude, location.longitude
            st.write(f"Coordinates: {lat}, {lon}")
            
            m = folium.Map(location=[lat, lon], zoom_start=14)
           
            # Add address marker
            folium.Marker([lat, lon], popup=address, icon=folium.Icon(color='red', icon='home')).add_to(m)
            folium.Circle(
                    location=[lat, lon],
                    radius=POI_radius,  # in meters
                    color='blue',       # outline color
                    fill=True,
                    fill_color='blue',  # fill color
                    fill_opacity=0.2,   # transparency (0 = invisible, 1 = opaque)
                    weight=2            # outline thickness
                    ).add_to(m)

            # Built environment: get POIs within 500m
            tags = {
                'amenity':{ 'types':['cafe', 'restaurant', 'bar', 'fast_food', 'pub'],
                           'color':'orange',
                           'icon':'cutlery'
                           },
                'shop': {'types':['supermarket', 'convenience', 'bakery'],
                         'color':'green',
                         'icon':'shopping-cart'
                         },
                'leisure': {'types': ['dog_park', 'fitness_centre','ice_rink', 'nature_reserve'],
                              'color':"blue",
                              'icon': "star"
                              }
            }
            
            #subset the dictionary so that it contains only the keys and types = readable in ox.features_from_point()
            osm_tags = {key: info['types'] for key, info in tags.items()}
            

            pois = ox.features_from_point((lat, lon), tags=osm_tags, dist=POI_radius)
           
     
            for key,item in tags.items():
                feature_layer = folium.FeatureGroup(name=key)
                
                if key in pois.columns:
                    filtered_pois = pois[pois[key].notna() & pois['name'].notna()]
                else:
                    print(f"Column '{key}' not found. Available columns: {list(pois.columns)}")
                    filtered_pois = pois.copy()  # or handle differently
               # Filter POIs for this key
               # filtered_pois = pois[pois[key].notna()]
                
                for idx, row in filtered_pois.iterrows():
                    lon_, lat_ = row.geometry.centroid.xy
                    folium.Marker(
                        location=[lat_[0], lon_[0]],
                        popup= f"<div style='font-size:12px; font-family:Arial; white-space:nowrap;'><b>{row.get(key,'N/A').capitalize()}</b><br>{row.get('name', 'Unnamed')}",
                        icon = folium.Icon(color=item['color'], icon=item['icon'])
                        
                        ).add_to(feature_layer)
                         
                feature_layer.add_to(m)
    
            # Add LayerControl for toggleable layers
            folium.LayerControl().add_to(m)
            st_folium(m, width=700, height=500)
            st.write(pois[['amenity', 'shop', 'name', 'geometry']])
            
        else:
            st.error("Address not found!")


#Next steps:
# Create tab Built environment
#    -aggregate number of supermarkets, other shops, restaurants, cafes
#    -a pie chart of sqare meter area: residential area, industry, retail, etc - from Open street map
#    - a polygon of the selected radius





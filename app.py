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
    
            # Built environment: get POIs within 500m
            tags = {
                'amenity': ['cafe', 'restaurant', 'bar', 'fast_food', 'pub'],
                'shop': ['supermarket', 'convenience', 'bakery']
            }
            pois = ox.features_from_point((lat, lon), tags=tags, dist=POI_radius)
           
            # Create separate FeatureGroups for layers
            amenity_layer = folium.FeatureGroup(name="Amenities")
            shop_layer = folium.FeatureGroup(name="Shops")
    
            # Filter amenities and add markers
            amenity_pois = pois[pois['amenity'].notna()]
            for idx, row in amenity_pois.iterrows():
                lon_, lat_ = row.geometry.centroid.xy
                folium.Marker(
                    [lat_[0], lon_[0]],
                    popup=row.get('name', 'Unnamed'),
                    icon=folium.Icon(color='orange', icon='glyphicon glyphicon-cutlery')
                ).add_to(amenity_layer)
    
            # Filter shops and add markers
            shop_pois = pois[pois['shop'].notna()]
            for idx, row in shop_pois.iterrows():
                lon_, lat_ = row.geometry.centroid.xy
                folium.Marker(
                    [lat_[0], lon_[0]],
                    popup=row.get('name', 'Unnamed'),
                    icon=folium.Icon(color='green', icon='shopping-cart')
                ).add_to(shop_layer)
    
            # Add layers to map
            amenity_layer.add_to(m)
            shop_layer.add_to(m)
    
            # Add LayerControl for toggleable layers
            folium.LayerControl().add_to(m)
            st_folium(m, width=700, height=500)
            st.write(pois[['amenity', 'shop', 'name', 'geometry']])
            
        else:
            st.error("Address not found!")
#else:
#     m = folium.Map(location=[59.3327, 18.0656], zoom_start=11)
     
# Display the map


import streamlit as st
import streamlit.web.bootstrap
import folium 
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="expanded")

st.title("Relocation Navigator")

#Sidebar ----------------------------------------------------
st.sidebar.markdown("## Sidebar")
address = st.sidebar.text_input("Enter an address:")



#Main --------------------------------------------------------
st.write("Map")

# Create map
m = folium.Map(location=[59.3327, 18.0656], zoom_start=11)

#If user enters an address => find latitude and longitude
if address:
    geolocator = Nominatim(user_agent="Navigator")
    location = geolocator.geocode(address)

    #if longitude and latitude are provided => add marker to the map
    if location:
        lat, lon = location.latitude, location.longitude
        st.write(f"Coordinates: {lat}, {lon}")

        # add address marker
        folium.Marker([lat, lon], popup=address).add_to(m)

    else:
        st.error("Address not found!")
        
# Display the map
st_map = st_folium(m, width=700, height=500)




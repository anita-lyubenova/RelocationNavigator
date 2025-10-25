import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from folium.features import GeoJson, GeoJsonPopup
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events



geolocator = Nominatim(user_agent="Navigator")

@st.cache_data(show_spinner=True, show_time = True)
def geocode_address(address):
    geolocator = Nominatim(user_agent="Navigator")
    return geolocator.geocode(address)

@st.cache_data(show_spinner=True, show_time = True)
def get_osm_features(lat, lon, tags, dist):
    return ox.features_from_point((lat, lon), tags=tags, dist=dist)

@st.cache_data
def load_pie_index():
    df = pd.read_excel("OSM features.xlsx", sheet_name="pie_index")
    df = df.dropna(subset=["key", "value"])
    df["key"] = df["key"].astype(str).str.strip()
    df["value"] = df["value"].astype(str).str.strip()
    return df

pie_index = load_pie_index()

def clip_to_circle(gdf, lat, lon, radius):
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    proj_crs = gdf.estimate_utm_crs()
    gdf_proj = gdf.to_crs(proj_crs)
    center = Point(lon, lat)
    circle = gpd.GeoSeries([center], crs=4326).to_crs(proj_crs).buffer(radius)
    return gpd.clip(gdf_proj, circle).to_crs(4326)



def melt_tags(gdf, tag_keys):
    melted = (
        gdf[tag_keys]
        .stack()
        .reset_index()
        .rename(columns={"level_2": "key", 0: "value"})
    )
    melted = melted.merge(gdf.reset_index()[["id", "geometry"]], on="id")
    melted = melted.drop(columns="element")
    melted = gpd.GeoDataFrame(melted, geometry="geometry", crs=gdf.crs)
    return melted

# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="expanded")

st.title("Relocation Navigator 2")

# Sidebar ----------------------------------------------------
st.sidebar.markdown("## Sidebar")
address = st.sidebar.text_input("Enter an address:", value ="Skaldevägen 60")
POI_radius=st.sidebar.slider('Show PoIs within X m', min_value=100, max_value=3000, value=500)

# Main --------------------------------------------------------

# If user enters an address => find latitude and longitude
if st.sidebar.button("Go!"):
    

    if address:
        
        location = geocode_address(address)

        if location:
            lat, lon = location.latitude, location.longitude
            st.write(f"Coordinates: {lat}, {lon}")
            
            
            #Map --------------------------------------------------------------
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
             # amenity and shops POIs within 500m
           

            # Pie chart------------------------------------------------------------------------------------------------------
            # Built environment: get POIs within 500m
            tags0 = {
                'landuse': True,   # True → all landuse values
                'natural': True,   # all natural features
                'leisure': True,    # all leisure features
                'amenity':True,
                'shop':True,
                'building': True,
            }
     
            all_features = get_osm_features(lat, lon, tags0, POI_radius)
           
            all_features=melt_tags(all_features, tags0.keys())
            
            polygon_features = all_features[all_features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
            
            clipped=clip_to_circle(gdf=polygon_features, lat=lat, lon=lon, radius=POI_radius)
            
            #Copmute square meter area per key and value-----------------------
            # Project to metric CRS for accurate areas
            proj_crs = clipped.estimate_utm_crs()
            clipped = clipped.to_crs(proj_crs)
            clipped["area_m2"] = clipped.geometry.area
           
            pie_data = clipped.merge(
                pie_index, on=["key", "value"], how="left"
                ).groupby(["pie_cat"]).agg(
                    total_area_m2 = ("area_m2", "sum"),
                    values_included=("value", lambda x: ", ".join(sorted(x.unique())))).reset_index()
            
            pie_data["values_included"] = (
                pie_data["values_included"]           
                .str.replace("_", " ")     
            )
            #pie chart----------------------------------------------------
            fig = px.pie(
                pie_data,
                names="pie_cat",
                values="total_area_m2",
                title="Area by Landuse Category",
                # hover_data={
                #     "values_included": True
                # },
                color_discrete_sequence=px.colors.qualitative.Set3)
            # fig.update_traces(
            #     textinfo="percent+label",
            #     pull=[0.05]*len(pie_data),
            #     hovertemplate="<b>%{label}</b><br>%{value:,.0f} m²<br>%{customdata}")
         
            # fig.update_traces(
            #     textinfo="percent+label",
            #     pull=[0.05] * len(pie_data),
            #     # customdata=pie_data["total_area_m2"],  # Add this line
            #     # hovertemplate="<b>%{label}</b><br>%{value:,.0f} m²<br>%{customdata}",
            #  )

                
            col1,col2 = st.columns(2)    
            
            with col1:
                st.subheader("Map with Points of interest")
                st_folium(m, width=700, height=500)
            with col2:
                st.subheader("Land use distribution")
                # st.plotly_chart(fig,
                #                 use_container_width=False,
                #                 key="landuse_pie",
                #                 on_select ="rerun")
                clicked = plotly_events(fig, click_event=True, select_event=False, override_height=500)

                if clicked:
                    st.write("You clicked:", clicked[0]['label'])


        


        else:
            st.error("Address not found!")


#Next steps:
# Create tab Built environment
#    -aggregate number of supermarkets, other shops, restaurants, cafes
#    -a pie chart of sqare meter area: residential area, industry, retail, etc - from Open street map
#    - a polygon of the selected radius





import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import plotly.express as px
#import xlrd
#from folium import GeoJson, GeoJsonTooltip

geolocator = Nominatim(user_agent="Navigator")

@st.cache_data(show_spinner=True, show_time = True)
def geocode_address(address):
    geolocator = Nominatim(user_agent="Navigator")
    return geolocator.geocode(address)

@st.cache_data(show_spinner=True, show_time = True)
def get_osm_features(lat, lon, tags, dist):
    return ox.features_from_point((lat, lon), tags=tags, dist=dist)

@st.cache_data
def load_pie_index(sheet):
    df = pd.read_excel("OSM features.xls", sheet_name=sheet)
    df = df.dropna(subset=["key", "value"])
    df["key"] = df["key"].astype(str).str.strip()
    df["value"] = df["value"].astype(str).str.strip()
    return df



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

#get pie index 
pie_index = load_pie_index("pie_index")
#Create a color to category mapping
unique_cats = pie_index["pie_cat"].unique()
#palette = px.colors.qualitative.Pastel1+px.colors.qualitative.Pastel2
#palette = plt.colormaps.get('Set3').colors
palette = px.colors.qualitative.Light24
color_lookup = {
    cat: palette[i % len(palette)]
    for i, cat in enumerate(sorted(unique_cats))
}

list(pie_index)
color_lookup.get(pie_index['pie_cat'][1], "gray")

ms_index  = load_pie_index("Multiselect")
ms_index = ms_index[ms_index['Multiselect'].notna()]

ms_cats = ms_index['Category'].unique()


fig_height=650
# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="collapsed")

st.title("Relocation Navigator 2")




## applying style
nopad = """<style>
div[data-testid = 'stMainBlockContainer']{padding: 0rem 0rem 0rem 1rem;} 
</style>
"""
st.markdown(nopad, unsafe_allow_html=True)

st.markdown(
    """
    <style>
    /* Make the label and pill buttons inline */
    div.stButtonGroup {
        display: flex !important;       /* set label to be on the same line as buttons */
        align-items: top;            /* vertical align label and pills */
        gap: 10px;                      /* space between label and buttons */
    }
    
    div.stButtonGroup label {
        white-space: nowrap !important; /* prevent label from breaking */
        flex-shrink: 0;                 /* don’t allow the label to shrink */
        margin-bottom: 0 !important;
    }
    
    div.stButtonGroup label div[data-testid='stMarkdownContainer'] p {
        font-weight: bold !important;
        margin: 0;  /* optional: remove default margin */
    }
    </style>
    """,
    unsafe_allow_html=True
)



# Main --------------------------------------------------------
cont_input = st.container()
col_address, col_features = cont_input.columns(spec= [0.3, 0.7], gap="small", border=True)

with col_address:
    address = st.text_input("Enter an address:", value ="Skaldevägen 60")
    POI_radius=st.slider('Show PoIs within X m', min_value=100, max_value=3000, value=500)

with col_features:
   
    
    selected_poi = []

    # Loop through all categories
    for category in ms_index["Category"].unique():
        options = ms_index.loc[ms_index["Category"] == category, "Multiselect"].dropna().unique().tolist()
        
        # Dynamically generate a pills input for each category
        selected = st.pills(
            label=category,
            options=options,
            key=f"poi_{category.replace(' ', '_')}_input",  # unique key
            selection_mode="multi"
        )
        
        # Store the selected values
        selected_poi.extend(selected)
        
if selected_poi:
    poi_tags=ms_index[ms_index['Multiselect'].isin(selected_poi)][["key", "value"]].groupby("key")["value"].apply(list).to_dict()

#Built environment: get POIs within 500m
tags0 = {
    'landuse': True,   # True → all landuse values
    'natural': True,   # all natural features
    'leisure': True,    # all leisure features
    'amenity':True,
   # 'shop':True,
    'building': True,
}


# If user enters an address => find latitude and longitude
if st.button("Go!"):
    
    if address:
        
        location = geocode_address(address)

        if location:
            lat, lon = location.latitude, location.longitude
            st.write(f"Coordinates: {lat}, {lon}")
            
            
            all_features = get_osm_features(lat, lon, tags0, POI_radius)
            #transform to long format
            all_features=melt_tags(all_features, tags0.keys())
            # Pie chart------------------------------------------------------------------------------------------------------
            # get only polygons
            polygon_features = all_features[all_features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
            
            clipped=clip_to_circle(gdf=polygon_features, lat=lat, lon=lon, radius=POI_radius)
            
            #Copmute square meter area per key and value-----------------------
            # Project to metric CRS for accurate areas
            proj_crs = clipped.estimate_utm_crs()
            clipped = clipped.to_crs(proj_crs)
            clipped["area_m2"] = clipped.geometry.area
            
            pie_data0 = clipped.merge(pie_index, on=["key", "value"], how="left")
            #pie_data0['pie_cat'] =pie_data0['pie_cat'].fillna('other')
            pie_data0 =pie_data0[pie_data0['pie_cat'].notna()] #remove polygons that are not in the pie index
            
            pie_data = pie_data0.groupby(["pie_cat"]).agg(
                total_area_m2 = ("area_m2", "sum"),
                values_included=("value", lambda x: ", ".join(sorted(x.unique())))).reset_index() #concantenate all values within the pie_category

            pie_data["values_included"] = (pie_data["values_included"].str.replace("_", " ")) #remove underscores from the column (for the popup)
            
            #pie chart----------------------------------------------------
            fig = px.pie(
                pie_data,
                names="pie_cat",
                values="total_area_m2",
                hover_data=["values_included"],
                color='pie_cat',
                color_discrete_map=color_lookup)
            fig.update_traces(
                textinfo="percent+label",
                pull=[0.05]*len(pie_data),
                hovertemplate="<b>%{label}</b><br>%{value:,.0f} m²<br>%{customdata}")
            
            fig.update_layout(height=fig_height)
         
           #Map --------------------------------------------------------------
            keys = pie_data.sort_values("total_area_m2", ascending=False)["pie_cat"].unique()
            m = folium.Map(location=[lat, lon], zoom_start=14)         
            # Add address marker
            folium.Marker([lat, lon], popup=address, icon=folium.Icon(color='red', icon='home')).add_to(m)
            folium.Circle(
                location=[lat, lon],
                radius=POI_radius,  # in meters
                color='red',       
                fill=False,
                weight=2            
                ).add_to(m)
            
            landuse_layer = folium.FeatureGroup(name="Land use distribution")
            
            folium.GeoJson(
                data=pie_data0,  # All data at once
                style_function=lambda feature: {
                    "fillColor": color_lookup.get(feature["properties"]["pie_cat"]),
                    "color": "black",
                    "weight": 0.3,
                    "fillOpacity": 0.5,
                },
                popup=folium.GeoJsonPopup(
                    fields=["pie_cat", "key", "value"],
                    aliases=["In pie chart", "OSM key", "OSM value"]
                )
            ).add_to(landuse_layer)
            
            landuse_layer.add_to(m)
            
            if selected_poi:
                ms_poi = get_osm_features(lat, lon, poi_tags, POI_radius)
                st.write(ms_poi)
                
                poi_layer = folium.FeatureGroup(name="Points of Interest")
                
                
            folium.LayerControl().add_to(m)
            
            
            col1,col2 = st.columns(2, gap="small", border=True)    
            
            with col1:
                st.subheader("Map with Points of interest")
                st_folium(m)
                
            with col2:
                st.subheader("Land use distribution")
                st.plotly_chart(fig,
                                use_container_width=True,
                                key="landuse_pie",
                                config = {'height': fig_height})
                


        else:
            st.error("Address not found!")


#Next steps:
# Create tab Built environment
#    -aggregate number of supermarkets, other shops, restaurants, cafes
#    -a pie chart of sqare meter area: residential area, industry, retail, etc - from Open street map
#    - a polygon of the selected radius





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

# -- Set page config
apptitle = 'Navigator'
st.set_page_config(page_title=apptitle,
                   layout="wide",
                   initial_sidebar_state="expanded")

st.title("Relocation Navigator 1")

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
            tags = {
                 'amenity':{ 'types':['cafe', 'restaurant', 'bar', 'fast_food', 'pub'],
                            'color':'orange',
                            'icon':'cutlery'
                            },
                 'shop': {'types':['supermarket', 'convenience', 'bakery'],
                          'color':'green',
                          'icon':'shopping-cart'
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
            #st_folium(m, width=700, height=500)
            #st.write(pois[['amenity', 'shop', 'name', 'geometry']])
            


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
            all_features = ox.features_from_point((lat, lon),tags=tags0, dist=POI_radius)
            polygon_features = all_features[all_features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
            
            #add a columns indicating the key (tag_key) and value (tag_value) of the OSM feature
            tag_keys = list(tags0.keys())
            
            def detect_key_and_value(row):
                for key in tag_keys:
                    if pd.notna(row.get(key)):
                        return key, row[key]
                return None, None
            
            all_features['tag_key'], all_features['tag_value'] = zip(*all_features.apply(detect_key_and_value, axis=1))
            polygon_features['tag_key'], polygon_features['tag_value'] = zip(*polygon_features.apply(detect_key_and_value, axis=1))
           
            #Clip polygons within the circle-----------------------------------
            # 0 Ensure the polygons have a CRS ---
            if polygon_features.crs is None:
                polygon_features = polygon_features.set_crs("EPSG:4326")
            
            #1. Pick a metric CRS (for buffer in meters) ---
            proj_crs = polygon_features.estimate_utm_crs()
            
            #2 Project both polygons and center point ---
            pf_proj = polygon_features.to_crs(proj_crs)
            center = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(proj_crs).iloc[0]
            
            #3Create the circular polygon (real geometry in meters) ---
            circle_poly = center.buffer(POI_radius)
            
            # 4 Convert it into a GeoDataFrame ---
            circle_gdf = gpd.GeoDataFrame({"geometry": [circle_poly]}, crs=proj_crs)
            
            # 5 CLIP polygons to circle (this is the key part) ---
            clipped_proj = gpd.clip(pf_proj, circle_gdf)
            
            # 6 Reproject back to WGS84 for Folium ---
            clipped = clipped_proj.to_crs("EPSG:4326")
            circle_gdf_wgs = circle_gdf.to_crs("EPSG:4326")
            
            #Copmute square meter area per key and value-----------------------
            # Project to metric CRS for accurate areas
            proj_crs = clipped.estimate_utm_crs()
            gdf_proj = clipped.to_crs(proj_crs)
            gdf_proj["area_m2"] = gdf_proj.geometry.area
            
            # List of keys
            keys = list(tags0.keys())
            
            # Store results
            detailed_stats = []
            
            for key in keys:
                subset = gdf_proj[gdf_proj[key].notna()]
                if len(subset) == 0:
                    continue
                grouped = subset.groupby(key).agg(
                    count=("geometry", "count"),
                    total_area_m2=("area_m2", "sum")
                ).reset_index()
                grouped["total_area_m2"] = grouped["total_area_m2"].round(0).astype(int)
                grouped["key"] = key
                grouped = grouped.rename(columns={key: "value"})  # rename grouped column to "value"
                detailed_stats.append(grouped)
            # Combine all keys
            stats_df = pd.concat(detailed_stats, ignore_index=True)
            
            # Reorder columns
            stats_df = stats_df[["key", "value", "count", "total_area_m2"]]
            
            # Optional: sort by key and total area
            stats_df = stats_df.sort_values(["key", "total_area_m2"], ascending=[True, False]) 
            
            
            
            #read and clean pie chart index, specifying the categories to be visualized and their links to teh key-value pairs
            pie_index = pd.read_excel("OSM features.xlsx",sheet_name='pie_index')
            # Clean up whitespace and drop empty rows
            pie_index = pie_index.dropna(subset=["key", "value"])
            pie_index["key"] = pie_index["key"].astype(str).str.strip()
            pie_index["value"] = pie_index["value"].astype(str).str.strip()
            
            #Filter the pie index such that it only includes key-value pairs existing in the polygon features

            available_pairs = []
            for key in polygon_features.columns:
                if key in pie_index["key"].unique():
                    valid_values = polygon_features[key].dropna().unique()
                    available_pairs.extend([(key, v) for v in valid_values])
            
            available_df = pd.DataFrame(available_pairs, columns=["key", "value"])
            
            # --- 3️⃣ Filter pie_index for only those key-value pairs present in polygon_features ---
            pie_index_filtered = pie_index.merge(available_df, on=["key", "value"], how="inner")
                
            
            #Create pie chart data-----------------------------------------
            # Merge on key/value to get pie category for each landuse/building type
            pie_data = stats_df.merge(pie_index_filtered, on=["key", "value"], how="inner")
            
            # Group by pie category and value to compute stats
            pie_detail = (
                pie_data.groupby(["pie_cat", "value"], as_index=False)
                .agg(total_area_m2=("total_area_m2", "sum"))
                .sort_values(["pie_cat", "total_area_m2"], ascending=[True, False])
            )
            
            # Then aggregate to the pie category level (for pie chart totals)
            pie_summary = (
                pie_detail.groupby("pie_cat", as_index=False)
                .agg(
                    total_area_m2=("total_area_m2", "sum"),
                    values_included=("value", lambda x: ", ".join(sorted(x.unique())))
                )
                .sort_values("total_area_m2", ascending=False)
            )
            
            # Clean up number formatting
            pie_summary["total_area_m2"] = pie_summary["total_area_m2"].round(0).astype(int)
            
            #pie chart----------------------------------------------------
            fig = px.pie(
                pie_summary,
                names="pie_cat",
                values="total_area_m2",
                title="Area by Landuse Category",
                hover_data={
                    "values_included": True
                },
             color_discrete_sequence=px.colors.qualitative.Set3,)
            fig.update_traces(textinfo="percent+label", pull=[0.05]*len(pie_summary))
           
         
           
                
            col1,col2 = st.columns(2)    
            
            with col1:
                st.subheader("Map with Points of interest")
                st_folium(m, width=700, height=500)
            with col2:
                st.subheader("Land use distribution")
                st.plotly_chart(fig,use_container_width=False, key="landuse_pie")
                
        else:
            st.error("Address not found!")


#Next steps:
# Create tab Built environment
#    -aggregate number of supermarkets, other shops, restaurants, cafes
#    -a pie chart of sqare meter area: residential area, industry, retail, etc - from Open street map
#    - a polygon of the selected radius





""" Create rent heatmap using Rentcast API """
import os
import json
import folium
import requests
import pandas as pd
import geopandas as gpd

API_KEY = os.getenv('RENTCAST_APIKEY')

def rentcast_api():
    """ Call Rentcast API to get rental data """
    
    def paginate_request(offset=0):
        url = f'https://api.rentcast.io/v1/listings/rental/long-term?city=San%20Francisco&state=CA&status=Active&limit=500&offset={offset}'
        headers = {
            'X-Api-Key': API_KEY,
            'accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Error: {response.json()}")
        return response.json()
    
    data_json_1 = paginate_request(0) # 0-500
    data_json_2 = paginate_request(500) # 501-1001
    data_json_3 = paginate_request(1000) # 1002-1502

    data = []
    data.extend(data_json_1)
    data.extend(data_json_2)
    data.extend(data_json_3)

    with open('response.json', 'w', encoding="UTF-8") as f:
        json.dump(data, f, indent=4)
    return data

def rentcast_fake_api():
    """ Fake API response """
    with open('response.json', 'r', encoding="UTF-8") as f:
        return json.load(f)

def json_to_data(rent_json):
    """ convert json to DataFrame """
    df = pd.DataFrame(rent_json)
    return df

def folium_map(df):
    """ Create a folium map """
    # Create a base map
    m = folium.Map(location=[37.7749, -122.4194], zoom_start=13)
    # folium.GeoJson("sf_neighborhoods.geojson").add_to(m)

    neighborhoods = gpd.read_file("sf_neighborhoods.geojson")
    merged = neighborhoods.merge(df, left_on='neighborhood', right_on='neighborhood')


    # Add the choropleth layer
    folium.Choropleth(
        geo_data=merged,
        name='choropleth',
        data=merged,
        columns=['neighborhood', 'price_per_sqft'],
        key_on='feature.properties.neighborhood',
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Ratio Price'
    ).add_to(m)

    # Add the markers in the middle of the neighborhoods
    for _, row in merged.iterrows():
        # Calculate the centroid of the neighborhood
        centroid = row['geometry'].centroid
        folium.Marker(
            location=[centroid.y, centroid.x],  # Centroid coordinates
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12pt; font-weight: bold;">${row["price_per_sqft"]:.2f}/ft<sup>2</sup></div>'
            )
        ).add_to(m)


    # Optional: Add a layer control panel
    folium.LayerControl().add_to(m)

    # Save the map to an HTML file
    m.save('neighborhood_choropleth.html')


def get_heat_data(df):
    """ Get the heatmap data """
    neighborhoods = gpd.read_file("sf_neighborhoods.geojson")

    n_df = pd.DataFrame(neighborhoods.neighborhood)
    n_df["total_price"] = float(0)
    n_df["average_price"] = float(0)
    n_df["ratio_price"] = float(0)
    
    n_df["total_sqft"] = float(0)
    n_df["average_sqft"] = float(0)
    n_df["price_per_sqft"] = float(0)
    points_gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude,crs='EPSG:4326')) # WGS 84

    # neighborhoods = neighborhoods.to_crs(epsg=4326) # WGS 84
    # points_gdf = points_gdf.to_crs(epsg=4326) # WGS 84

    points_within = gpd.sjoin(points_gdf, neighborhoods, how='inner')

    # Cast price and sqft to float
    points_within["price"] = points_within["price"].astype(float)
    points_within["squareFootage"] = points_within["squareFootage"].astype(float)

    # Add points to the map
    for _, row in points_within.iterrows():
        # Price
        n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_price"] += row["price"]
        n_df.loc[n_df["neighborhood"] == row["neighborhood"], "average_price"] = n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_price"] / len(points_within[points_within["neighborhood"] == row["neighborhood"]])
        
        # Sqft
        if row["squareFootage"] and row["squareFootage"] > 0:
            n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_sqft"] += row["squareFootage"]
            n_df.loc[n_df["neighborhood"] == row["neighborhood"], "average_sqft"] = n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_sqft"] / len(points_within[points_within["neighborhood"] == row["neighborhood"]])
    
    n_df["ratio_price"] = n_df["average_price"] / n_df["average_price"].max()
    n_df["price_per_sqft"] = n_df["average_price"] / n_df["average_sqft"]

    return n_df

def main():
    """ Main """
    # rent_json = rentcast_api() # 50 requests per month limit
    rent_json = rentcast_fake_api()

    df = json_to_data(rent_json)

    neighborhood_prices_df = get_heat_data(df)
    folium_map(neighborhood_prices_df)
    
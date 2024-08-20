""" Create rent heatmap using Rentcast API """
import os
import json
import datetime as dt
import folium
import requests
import pandas as pd
import geopandas as gpd
import branca.colormap as cm
from IPython.display import display

API_KEY = os.getenv('RENTCAST_APIKEY')

def rentcast_api():
    """ Call Rentcast API to get rental data """

    # Get current date
    today = dt.datetime.now().strftime('%Y-%m-%d')

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
    return data, today

def rentcast_fake_api():
    """ Fake API response """
    with open('response.json', 'r', encoding="UTF-8") as f:
        return json.load(f)

def json_to_data(rent_json):
    """ convert json to DataFrame """
    df = pd.DataFrame(rent_json)
    return df

def folium_map(proc_df, full_df):
    """ Create a folium map """

    # Create a base map
    m = folium.Map(location=[37.7749, -122.4194], zoom_start=13) # San Francisco coordinates
    # folium.GeoJson("sf_neighborhoods.geojson").add_to(m) # Adds the neighborhood boundaries to the map

    neighborhoods = gpd.read_file("sf_neighborhoods.geojson")
    merged = neighborhoods.merge(proc_df, left_on='neighborhood', right_on='neighborhood')

    # Add the choropleth layer
    folium.Choropleth(
        geo_data=merged,
        name='Heatmap',
        data=merged,
        columns=['neighborhood', 'price_per_sqft'],
        key_on='feature.properties.neighborhood',
        fill_color="Spectral_r",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Ratio Price'
    ).add_to(m)

    # Create a FeatureGroup for the rentals
    rental_group = folium.FeatureGroup(name="Rentals").add_to(m)

    # Add a point for each lat/long in the dataset, color-coded by price
    for _, row in full_df.iterrows():

        n_avg = proc_df[proc_df["neighborhood"] == row["neighborhood"]]["price_per_sqft"].values[0] # neighborhood price/sqft
        a_ = row["price_per_sqft"] # apartment price/sqft
        if a_ == 0:
            a_ = n_avg
        spectral_cm = cm.LinearColormap(['green', 'yellow', 'red'], vmin=n_avg-1, vmax=n_avg+1)

        simple_cm = "black"
        if a_ < n_avg-0.25:
            simple_cm = "green"
        elif a_ > n_avg+0.25:
            simple_cm = "red"
        else:
            simple_cm = "orange"

        price = int(row["price"])
        sqFT = int(row["squareFootage"]) if not pd.isna(row["squareFootage"]) else "-"
        beds = int(row["bedrooms"]) if not pd.isna(row["bedrooms"]) else "-"
        baths = int(row["bathrooms"]) if not pd.isna(row["bathrooms"]) else "-"

        address_search = f'https://www.google.com/search?q={row["formattedAddress"].replace(" ", "+")}'

        popup_html = f'''
        <div style="font-size: 24pt; font-weight: bold;">
            ${price}<br>
            {sqFT}ft<sup>2</sup>
        </div>
        <div style="font-size: 12pt;">
            {beds} Bed, {baths} Bath<br>
            <a href="{address_search}" target="_blank">{row["formattedAddress"]}</a>
        </div>
        '''
        icon = folium.Icon(color=simple_cm, icon='glyphicon glyphicon-map-marker')
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            radius=10,
            icon=icon,
            # color=spectral_cm(a_),
            # fill=True,
            # fill_color=spectral_cm(a_),
            # fill_opacity=1,
            popup=folium.Popup(popup_html,max_width=500),
        ).add_to(rental_group)

    # Create a FeatureGroup for the text
    text_group = folium.FeatureGroup(name="Price per Sqft and Units").add_to(m)

    # Add the text in the middle of the neighborhoods
    for _, row in merged.iterrows():
        # Calculate the centroid of the neighborhood
        centroid = row['geometry'].centroid
        folium.Marker(
            location=[centroid.y, centroid.x],  # Centroid coordinates
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12pt; font-weight: bold; white-space: nowrap;">${row["price_per_sqft"]:.2f}/ft<sup>2</sup><br>{int(row["samples"])} Units</div>'
            )
        ).add_to(text_group)


    # Optional: Add a layer control panel
    folium.LayerControl().add_to(m)

    m.keep_in_front(rental_group)


    # Add a JavaScript slider for filtering
    slider_html = '''
        <div id="slider-container" style="position: fixed; bottom: 50px; left: 50px; z-index:9999;">
            <input id="price-slider" type="range" min="1000" max="2000" step="100" value="2000"
                oninput="updateMap(this.value)">
            <label for="price-slider">Max Price: <span id="slider-value">2000</span></label>
        </div>
        <script>
            function updateMap(value) {
                document.getElementById("slider-value").textContent = value;
                var markers = document.getElementsByClassName("leaflet-interactive");
                var popups = document.getElementsByClassName("leaflet-popup-content-wrapper");
                for (var i = 0; i < markers.length; i++) {
                    var marker = markers[i];
                    var price = parseInt(popups[i].innerText.split("$")[1].split("\\n")[0]);
                    if (price > value) {
                        marker.style.display = "none";
                    } else {
                        marker.style.display = "block";
                    }
                }
            }
        </script>
    '''

    # Add the slider HTML to the map
    # m.get_root().html.add_child(folium.Element(slider_html))

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

    n_df["samples"] = float(0)

    points_gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude,crs='EPSG:4326')) # WGS 84

    # neighborhoods = neighborhoods.to_crs(epsg=4326) # WGS 84
    # points_gdf = points_gdf.to_crs(epsg=4326) # WGS 84

    points_within = gpd.sjoin(points_gdf, neighborhoods, how='inner')

    # Cast price and sqft to float
    points_within["price"] = points_within["price"].astype(float)
    points_within["squareFootage"] = points_within["squareFootage"].astype(float)

    points_within["price_per_sqft"] = float(0)

    # Add points to the map
    for _, row in points_within.iterrows():

        # Check if the square footage is not null
        if not pd.isna(row["squareFootage"]) and row["squareFootage"] > 0:
            points_within.loc[points_within["id_left"]==row["id_left"],"price_per_sqft"] = row["price"] / row["squareFootage"]
        else:
            points_within.loc[points_within["id_left"]==row["id_left"],"price_per_sqft"] = 0

        # Samples
        n_df.loc[n_df["neighborhood"] == row["neighborhood"], "samples"] += 1

        # Price
        n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_price"] += row["price"]
        n_df.loc[n_df["neighborhood"] == row["neighborhood"], "average_price"] = n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_price"] / len(points_within[points_within["neighborhood"] == row["neighborhood"]])

        # Sqft
        if row["squareFootage"] and row["squareFootage"] > 0:
            n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_sqft"] += row["squareFootage"]
            n_df.loc[n_df["neighborhood"] == row["neighborhood"], "average_sqft"] = n_df.loc[n_df["neighborhood"] == row["neighborhood"], "total_sqft"] / len(points_within[points_within["neighborhood"] == row["neighborhood"]])

    n_df["ratio_price"] = n_df["average_price"] / n_df["average_price"].max()
    n_df["price_per_sqft"] = n_df["average_price"] / n_df["average_sqft"]

    f_df = points_within

    return n_df, f_df

def main():
    """ Main """
    today = dt.datetime.now().strftime('%Y-%m-%d')
    # rent_json, today = rentcast_api() # 50 requests per month limit
    rent_json = rentcast_fake_api()

    df = json_to_data(rent_json)

    neighborhood_prices_df, full_df = get_heat_data(df)
    folium_map(neighborhood_prices_df, full_df)
    # print(rent_json)

if __name__ == '__main__':
    main()

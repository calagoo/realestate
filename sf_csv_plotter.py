""" GENERATING HEATMAP WITH REAL ESTATE DATA """

import pandas as pd
import matplotlib.pyplot as plt

# Load the data
FILENAME = "Neighborhood_zhvi_uc_condo_tier_0.33_0.67_sm_sa_month.csv"
data = pd.read_csv(FILENAME)

sf_data = data[data['Metro'] == 'San Francisco-Oakland-Berkeley, CA']



# Plot the data per RegionName
reg_price = sf_data[['RegionName', sf_data.columns[-1]]]

# Plot the data per RegionName
reg_price = sf_data[['RegionName', sf_data.columns[-1]]]
reg_price = reg_price.dropna()
reg_price = reg_price.sort_values(by=reg_price.columns[-1], ascending=False)
reg_price = reg_price.head(45)
# reg_price = reg_price.tail(45)

plt.figure(figsize=(10, 10))
plt.scatter(reg_price['RegionName'], reg_price[reg_price.columns[-1]])
plt.xticks(rotation=45)
plt.ylabel('Price')
plt.xlabel('Region Name')
plt.title('Price per Region Name')
plt.tight_layout()
plt.show()

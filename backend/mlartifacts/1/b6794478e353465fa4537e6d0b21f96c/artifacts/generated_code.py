import matplotlib.pyplot as plt
import seaborn as sns

# Filter the dataframe for 'Entire home/apt' listings in Manhattan that cost more than $400 a night
manhattan_listings = df[(df['room_type'] == 'Entire home/apt') & (df['neighbourhood_group'] == 'Manhattan') & (df['price'] > 400)]

# Create a scatter plot to visualize the locations of the listings
plt.figure(figsize=(10,6))
sns.scatterplot(x='longitude', y='latitude', data=manhattan_listings, hue='price', palette='coolwarm')
plt.title('Locations of Entire Home/Apt Listings in Manhattan Over $400/Night')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.savefig('output_chart.png')
plt.close()

# Store the result in a variable
result = manhattan_listings
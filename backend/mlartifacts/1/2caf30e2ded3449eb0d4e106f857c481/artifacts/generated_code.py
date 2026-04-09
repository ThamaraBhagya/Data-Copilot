import matplotlib.pyplot as plt
import seaborn as sns

# Group by neighbourhood and calculate the count of rentals and average price
neighbourhood_rentals = df.groupby('neighbourhood')['id'].count().reset_index()
neighbourhood_rentals.columns = ['neighbourhood', 'count']
neighbourhood_prices = df.groupby('neighbourhood')['price'].mean().reset_index()

# Merge the two dataframes
neighbourhood_data = neighbourhood_rentals.merge(neighbourhood_prices, on='neighbourhood')

# Sort the dataframe by count in descending order
neighbourhood_data = neighbourhood_data.sort_values(by='count', ascending=False)

# Create a bar plot to visualize the most popular neighbourhoods and their average prices
plt.figure(figsize=(10,6))
sns.barplot(x='neighbourhood', y='count', data=neighbourhood_data.head(10))
plt.title('Most Popular Neighbourhoods for Rentals')
plt.xlabel('Neighbourhood')
plt.ylabel('Count of Rentals')
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig('output_chart.png')
plt.close()

# Store the result in a variable
result = neighbourhood_data.head(10)
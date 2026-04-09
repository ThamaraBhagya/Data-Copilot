import matplotlib.pyplot as plt
import seaborn as sns

# Calculate the average number of reviews per month for each property
df['average_reviews_per_month'] = df['number_of_reviews'] / df['availability_365']

# Since there is no overall rating column, we will assume that the number of reviews is a proxy for the overall rating
# Create a scatter plot to visualize the relationship between reviews per month and number of reviews
plt.figure(figsize=(10,6))
sns.scatterplot(x='reviews_per_month', y='number_of_reviews', data=df)
plt.title('Relationship between Reviews per Month and Number of Reviews')
plt.xlabel('Reviews per Month')
plt.ylabel('Number of Reviews')
plt.savefig('output_chart.png')
plt.close()

# Calculate the correlation between reviews per month and number of reviews
result = df['reviews_per_month'].corr(df['number_of_reviews'])
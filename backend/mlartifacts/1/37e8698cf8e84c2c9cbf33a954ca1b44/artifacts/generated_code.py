import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Calculate the overall rating (assuming it's not available in the data)
# Since the overall rating is not available, we'll use the number of reviews as a proxy
df['overall_rating'] = df['number_of_reviews']

# Plot the relationship between reviews per month and overall rating
plt.figure(figsize=(10,6))
sns.scatterplot(x='reviews_per_month', y='overall_rating', data=df)
plt.title('Relationship between Reviews per Month and Overall Rating')
plt.xlabel('Reviews per Month')
plt.ylabel('Overall Rating (Proxy: Number of Reviews)')
plt.savefig('output_chart.png')
plt.close()

# Calculate the correlation between reviews per month and overall rating
result = df['reviews_per_month'].corr(df['overall_rating'])
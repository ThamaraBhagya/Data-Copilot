import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Group by Category and Region, and calculate total sales
df_grouped = df.groupby(['Category', 'Region'])['Sales'].sum().reset_index()

# Sort the grouped data by Sales in descending order
df_sorted = df_grouped.sort_values(by='Sales', ascending=False)

# Select top 10 products by sales
top_products = df_sorted.head(10)

# Create a bar chart
plt.figure(figsize=(10,6))
sns.barplot(x='Category', y='Sales', hue='Region', data=top_products)
plt.title('Top-selling products by category and region')
plt.xlabel('Category')
plt.ylabel('Sales')
plt.legend(title='Region')
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig('output_chart.png')
plt.close()

# Store the result in a variable
result = top_products
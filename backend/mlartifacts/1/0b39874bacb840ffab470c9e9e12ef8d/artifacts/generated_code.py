import pandas as pd
import matplotlib.pyplot as plt

# Group by Region and calculate total sales
region_sales = df.groupby('Region')['Sales'].sum().reset_index()

# Sort by total sales in descending order
region_sales = region_sales.sort_values(by='Sales', ascending=False)

# Store the result in the 'result' variable
result = region_sales.head(1)['Region'].values[0]

# Plot a bar chart of the top regions by total sales
plt.figure(figsize=(10,6))
plt.bar(region_sales['Region'], region_sales['Sales'])
plt.xlabel('Region')
plt.ylabel('Total Sales')
plt.title('Regions by Total Sales')
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig('output_chart.png')
plt.close()
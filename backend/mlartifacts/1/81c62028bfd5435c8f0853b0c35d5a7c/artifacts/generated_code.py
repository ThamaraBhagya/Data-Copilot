import pandas as pd
import matplotlib.pyplot as plt

# Group by Category and calculate total sales
result = df.groupby('Category')['Sales'].sum().reset_index()

# Sort the result in descending order
result = result.sort_values(by='Sales', ascending=False)

# Print the result
print(result)

# Create a bar chart
plt.figure(figsize=(10,6))
plt.bar(result['Category'], result['Sales'])
plt.xlabel('Category')
plt.ylabel('Total Sales')
plt.title('Total Sales by Category')
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig('output_chart.png')
plt.close()
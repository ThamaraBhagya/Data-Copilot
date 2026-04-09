import pandas as pd
import matplotlib.pyplot as plt

# Convert Order Date to datetime with dayfirst=True
df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)

# Group by Order Date and calculate total sales
df_grouped = df.groupby('Order Date')['Sales'].sum().reset_index()

# Plot line chart
plt.figure(figsize=(10,6))
plt.plot(df_grouped['Order Date'], df_grouped['Sales'], marker='o')
plt.title('Sales Over Time')
plt.xlabel('Order Date')
plt.ylabel('Sales')
plt.grid(True)
plt.savefig('output_chart.png')
plt.close()

result = 'output_chart.png'
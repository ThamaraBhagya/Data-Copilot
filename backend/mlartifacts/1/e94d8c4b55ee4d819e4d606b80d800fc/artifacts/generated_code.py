import matplotlib.pyplot as plt
import seaborn as sns

# Calculate profit (assuming 20% profit margin)
df['Profit'] = df['Sales'] * 0.2

# Create scatter plot
plt.figure(figsize=(10,6))
sns.scatterplot(x='Sales', y='Profit', data=df, hue='Region')

# Set labels and title
plt.xlabel('Sales')
plt.ylabel('Profit')
plt.title('Sales vs Profit by Region')

# Save plot
plt.savefig('output_chart.png')
plt.close()
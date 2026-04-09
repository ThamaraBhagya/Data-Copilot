import matplotlib.pyplot as plt
import seaborn as sns

sns.set()
plt.figure(figsize=(10,8))
sns.scatterplot(data=df, x='longitude', y='latitude', hue='neighbourhood_group')
plt.title('Scatter plot of longitude and latitude by neighborhood group')
plt.savefig('output_chart.png')
plt.close()
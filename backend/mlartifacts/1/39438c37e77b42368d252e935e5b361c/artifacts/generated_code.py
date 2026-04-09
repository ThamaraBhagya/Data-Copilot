import matplotlib.pyplot as plt

movies = df[df['type'] == 'Movie'].shape[0]
tv_series = df[df['type'] == 'TV Show'].shape[0]

plt.figure(figsize=(8, 8))
plt.pie([movies, tv_series], labels=['Movies', 'TV Series'], autopct='%1.1f%%')
plt.title('Movies vs TV Series')
plt.savefig('output_chart.png')
plt.close()
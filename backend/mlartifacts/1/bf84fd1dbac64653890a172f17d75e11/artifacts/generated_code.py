import matplotlib.pyplot as plt

# Count the number of Movies and TV Shows
movie_count = (df['type'] == 'Movie').sum()
tv_show_count = (df['type'] == 'TV Show').sum()

# Create a pie chart
plt.figure(figsize=(8, 8))
plt.pie([movie_count, tv_show_count], labels=['Movies', 'TV Shows'], autopct='%1.1f%%')
plt.title('Movies vs TV Shows')
plt.savefig('output_chart.png')
plt.close()
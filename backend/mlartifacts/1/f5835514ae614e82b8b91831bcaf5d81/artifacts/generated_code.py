import matplotlib.pyplot as plt

churned_avg = df.loc[df['Churn'] == 'Yes', 'MonthlyCharges'].mean()
stayed_avg = df.loc[df['Churn'] == 'No', 'MonthlyCharges'].mean()

plt.pie([churned_avg, stayed_avg], labels=['Churned', 'Stayed'], autopct='%1.1f%%')
plt.title('Average Monthly Charges for Churned and Stayed Customers')
plt.savefig('output_chart.png')
plt.close()
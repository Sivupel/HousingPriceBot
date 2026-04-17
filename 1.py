import pandas as pd


df = pd.read_csv("for_ml_sample_202604170834.csv")

print(df.head())
print()
print(df.columns.tolist())
print()
print(df.shape)
print()
print(df.info())
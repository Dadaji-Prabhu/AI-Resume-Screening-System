import pandas as pd

# Load the dataset
df = pd.read_csv("data/UpdatedResumedataset.csv")

# How many rows and columns
print("Shape:", df.shape)

# What are the column names
print("\nColumns:", df.columns.tolist())

# How many resumes per category
print("\nResumes per category:")
print(df['Category'].value_counts())

# Show one full resume so we can see what it looks like
print("\n--- SAMPLE RESUME ---")
print(df['Resume'][0])
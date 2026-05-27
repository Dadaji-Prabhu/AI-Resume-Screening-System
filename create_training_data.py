import pandas as pd

# Load cleaned data
df = pd.read_csv("data/cleaned_resumes.csv")

training_data = []

for i, row in df.iterrows():
    resume = row['Cleaned_Resume']
    category = row['Category']

    # Positive example
    jd = f"Looking for a {category} with relevant skills"
    training_data.append((resume, jd, 1))

    # Negative example
    for other_cat in df['Category'].unique():
        if other_cat != category:
            jd = f"Looking for a {other_cat} with relevant skills"
            training_data.append((resume, jd, 0))
            break

# Create dataframe
train_df = pd.DataFrame(training_data, columns=['resume', 'jd', 'label'])

# Save
train_df.to_csv("data/training_data.csv", index=False)

print("Training data created successfully!")
import pandas as pd
import re

# Load the dataset
df = pd.read_csv("data/UpdatedResumedataset.csv")

print("Before cleaning:")
print(df['Resume'][0][:200])
print("---")

def clean_resume(text):
    # Remove URLs
    text = re.sub(r'http\S+\s*', ' ', text)
    
    # Remove special characters and symbols
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Convert to lowercase
    text = text.lower().strip()
    
    return text

# Apply cleaning to every resume
df['Cleaned_Resume'] = df['Resume'].apply(clean_resume)

print("After cleaning:")
print(df['Cleaned_Resume'][0][:200])

# Save the cleaned data
df.to_csv("data/cleaned_resumes.csv", index=False)
print("\n Cleaned data saved to data/cleaned_resumes.csv")
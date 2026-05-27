import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#  Step 1: Load the cleaned resumes 
df = pd.read_csv("data/resumes_with_skills.csv")
print(f"Loaded {len(df)} resumes")

#  Step 2: Remove duplicate resumes
df = df.drop_duplicates(subset=['Cleaned_Resume'])
df = df.reset_index(drop=True)
print(f"After removing duplicates: {len(df)} resumes")

# ── Step 3: Define a job description ───────────────────
job_description = """
    Looking for a Data Scientist with experience in python,
    machine learning, deep learning, sql and data analysis.
    Knowledge of tensorflow or keras is a plus.
"""

# ── Step 4: Convert text to numbers using TF-IDF ───────
all_texts = [job_description] + list(df['Cleaned_Resume'])

vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(all_texts)

print(f"\nTF-IDF matrix shape: {tfidf_matrix.shape}")

# ── Step 5: Calculate similarity scores ────────────────
job_vector     = tfidf_matrix[0]
resume_vectors = tfidf_matrix[1:]
scores         = cosine_similarity(job_vector, resume_vectors)[0]

print(f"\nHighest score : {scores.max():.4f}")
print(f"Lowest score  : {scores.min():.4f}")
print(f"Average score : {scores.mean():.4f}")

# ── Step 6: Add scores and rank ─────────────────────────
df['Match_Score'] = scores
df_ranked = df.sort_values('Match_Score', ascending=False)
df_ranked = df_ranked.reset_index(drop=True)

# ── Step 7: Show top 5 results ──────────────────────────
print("\n─── TOP 5 MATCHING RESUMES ───")
for i in range(5):
    row = df_ranked.iloc[i]
    print(f"\nRank #{i+1}")
    print(f"  Category    : {row['Category']}")
    print(f"  Match Score : {row['Match_Score']:.4f}")
    print(f"  Match %     : {round(row['Match_Score'] * 100, 2)}%")
    print(f"  Skills      : {row['Skills']}")

# ── Step 8: Save final results ──────────────────────────
df_ranked.to_csv("data/ranked_resumes.csv", index=False)
print("\n Saved to data/ranked_resumes.csv")
import pandas as pd
import re
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Step 1: Load data ───────────────────────────────────
df = pd.read_csv("data/resumes_with_skills.csv")
df = df.drop_duplicates(subset=['Cleaned_Resume'])
df = df.reset_index(drop=True)
print(f"Loaded {len(df)} resumes")

# ── Step 2: Define job requirements ────────────────────
job_description = """
    Looking for a Data Scientist with experience in python,
    machine learning, deep learning, sql and data analysis.
    Knowledge of tensorflow or keras is a plus.
"""

# Skills the job specifically requires
required_skills = [
    'python', 'machine learning', 'deep learning',
    'sql', 'data analysis', 'tensorflow', 'keras'
]

# ── Step 3: Calculate TF-IDF score ─────────────────────
# Combine job description with all resumes
all_texts = [job_description] + list(df['Cleaned_Resume'])

# Apply TF-IDF — converts text into numbers
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(all_texts)

# Compare job description against all resumes
job_vector = tfidf_matrix[0]
resume_vectors = tfidf_matrix[1:]
tfidf_scores = cosine_similarity(job_vector, resume_vectors)[0]

df['TF_IDF_Score'] = tfidf_scores
print("TF-IDF scores calculated")

# ── Step 4: Calculate skills match score ───────────────
def skills_match_score(candidate_skills_str, required_skills):
    """
    How many required skills does the candidate have?
    Returns a score between 0 and 1

    Example:
    required  = ['python', 'sql', 'machine learning']  → 3 skills
    candidate = ['python', 'sql']                       → 2 matched
    score     = 2/3 = 0.67
    """
    try:
        # Skills are saved as string in CSV, convert back to list
        candidate_skills = ast.literal_eval(candidate_skills_str)
    except:
        return 0.0

    if len(required_skills) == 0:
        return 0.0

    # Count how many required skills candidate has
    matched = sum(1 for skill in required_skills
                  if skill in candidate_skills)

    return matched / len(required_skills)

df['Skills_Score'] = df['Skills'].apply(
    lambda x: skills_match_score(x, required_skills)
)
print("Skills scores calculated")

# ── Step 5: Calculate experience score ─────────────────
def experience_score(resume_text):
    """
    Looks for year mentions in resume to estimate experience.
    Uses original resume text (not cleaned) to preserve years.
    More years mentioned = more experience.
    Returns a score between 0 and 1.
    """
    # Find all 4 digit years between 1990 and 2024
    years = re.findall(r'\b(199\d|200\d|201\d|202\d)\b', str(resume_text))
    count = len(years)

    # Normalize — cap at 10 year mentions = max score
    return min(count / 10, 1.0)

# Use original Resume column to preserve year numbers
df['Experience_Score'] = df['Resume'].apply(experience_score)
print("Experience scores calculated")

# ── Step 6: Calculate final score ──────────────────────
# Weighted combination of all three scores:
# TF-IDF     → 50% (most important — overall match)
# Skills     → 40% (second — specific skill match)
# Experience → 10% (least — just a bonus)

df['Final_Score'] = (
    df['TF_IDF_Score']     * 0.50 +
    df['Skills_Score']     * 0.40 +
    df['Experience_Score'] * 0.10
)

# Convert to percentage out of 100
df['Final_Score_Pct'] = (df['Final_Score'] * 100).round(2)

# ── Step 7: Rank candidates ────────────────────────────
df_ranked = df.sort_values('Final_Score', ascending=False)
df_ranked = df_ranked.reset_index(drop=True)

# ── Step 8: Show top 5 candidates ──────────────────────
print("\n─── TOP 5 CANDIDATES ───")
for i in range(5):
    row = df_ranked.iloc[i]
    print(f"\nRank #{i + 1}")
    print(f"  Category       : {row['Category']}")
    print(f"  TF-IDF Score   : {round(row['TF_IDF_Score'] * 100, 2)}%")
    print(f"  Skills Score   : {round(row['Skills_Score'] * 100, 2)}%")
    print(f"  Experience     : {round(row['Experience_Score'] * 100, 2)}%")
    print(f"  ── FINAL SCORE : {row['Final_Score_Pct']}% ──")

# ── Step 9: Save final ranked results  
df_ranked.to_csv("data/final_ranked_candidates.csv", index=False)
print("\n Final ranking saved to data/final_ranked_candidates.csv")
import pandas as pd

# ── Step 1: Load cleaned data ─────────────────────────
df = pd.read_csv("data/cleaned_resumes.csv")
print(f"Loaded {len(df)} resumes")

# ── Step 2: Define skills list ────────────────────────
SKILLS_LIST = [
    # Programming
    'python', 'java', 'sql', 'javascript', 'html', 'css',
    'r', 'scala', 'c', 'php', 'ruby',

    # Data Science / ML
    'machine learning', 'deep learning', 'natural language processing',
    'tensorflow', 'keras', 'scikit learn', 'pandas', 'numpy',
    'matplotlib', 'tableau', 'power bi', 'data analysis', 'data science',

    # Databases / Big Data
    'mysql', 'oracle', 'mongodb', 'postgresql', 'hadoop',
    'spark', 'hive', 'cassandra',

    # Web / Tools
    'django', 'flask', 'react', 'node', 'git', 'docker',
    'linux', 'windows', 'aws', 'azure',

    # Testing
    'selenium', 'testing', 'automation', 'manual testing',

    # Other
    'network', 'security', 'sap', 'excel', 'ms office'
]

# ── Step 3: Define skill synonyms ─────────────────────
SKILL_SYNONYMS = {
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "natural language processing": ["nlp"],
    "tensorflow": ["tf"],
    "javascript": ["js"],
    "artificial intelligence": ["ai"],
    "power bi": ["powerbi"],
}

# ── Step 4: Skill extraction function ─────────────────
def extract_skills(resume_text):
    found_skills = set()
    resume_lower = resume_text.lower()

    for skill in SKILLS_LIST:
        # Direct match
        if skill in resume_lower:
            found_skills.add(skill)

        # Synonym match
        if skill in SKILL_SYNONYMS:
            for synonym in SKILL_SYNONYMS[skill]:
                if synonym in resume_lower:
                    found_skills.add(skill)

    return list(found_skills)

# ── Step 5: Apply to all resumes ──────────────────────
df['Skills'] = df['Cleaned_Resume'].apply(extract_skills)

# ── Step 6: Show sample results ───────────────────────
print("\n--- SAMPLE OUTPUT ---")

for i in range(3):
    print(f"\nResume #{i+1}")
    print("Category :", df['Category'][i])
    print("Skills   :", df['Skills'][i])

# ── Step 7: Save output ───────────────────────────────
df.to_csv("data/resumes_with_skills.csv", index=False)

print("\n Updated file saved: data/resumes_with_skills.csv")
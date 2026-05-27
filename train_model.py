import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pickle

print("Loading data...")
df = pd.read_csv("data/training_data.csv")
resumes_df = pd.read_csv("data/resumes_with_skills.csv")

print(f"Training data: {df.shape}")
print(f"Resume dataset: {resumes_df.shape}")
print(f"Label distribution:\n{df['label'].value_counts()}")

# ── Simple category JDs matching training data style ──
# Keep same style as original training data
# so model doesnt get confused
CATEGORY_JDS = {
    'Data Science': [
        'looking for a data science with relevant skills',
        'hiring data scientist machine learning python',
        'data science python tensorflow pandas nlp',
        'machine learning engineer data science position',
    ],
    'Python Developer': [
        'looking for a python developer with relevant skills',
        'hiring python developer django flask rest api',
        'python developer backend sql git aws position',
        'senior python developer django postgresql redis',
    ],
    'Java Developer': [
        'looking for a java developer with relevant skills',
        'hiring java developer spring boot hibernate sql',
        'senior java developer spring microservices maven',
        'java backend developer j2ee rest api oracle',
    ],
    'Web Designing': [
        'looking for a web designing with relevant skills',
        'hiring web designer html css javascript react',
        'frontend developer angular vue bootstrap figma',
        'ui ux web designer javascript react nodejs',
    ],
    'DevOps Engineer': [
        'looking for a devops engineer with relevant skills',
        'hiring devops docker kubernetes jenkins aws',
        'cloud devops engineer terraform ansible linux',
        'senior devops engineer ci cd pipeline azure',
    ],
    'Database': [
        'looking for a database with relevant skills',
        'hiring database administrator mysql postgresql',
        'dba oracle sql server mongodb nosql redis',
        'database developer pl sql stored procedures',
    ],
    'Testing': [
        'looking for a testing with relevant skills',
        'hiring qa engineer selenium automation java',
        'test engineer manual testing agile scrum',
        'automation tester selenium pytest robot framework',
    ],
    'HR': [
        'looking for a hr with relevant skills',
        'hiring hr manager recruitment talent acquisition',
        'human resources payroll employee relations',
        'hr executive performance management hiring',
    ],
    'Business Analyst': [
        'looking for a business analyst with relevant skills',
        'hiring business analyst agile scrum jira',
        'senior ba requirements stakeholder management',
        'business analyst sql tableau process improvement',
    ],
    'Network Security Engineer': [
        'looking for a network security engineer with relevant skills',
        'hiring network security firewall vpn cisco',
        'cybersecurity analyst ethical hacking penetration',
        'network engineer ccna routing switching security',
    ],
    'Mechanical Engineer': [
        'looking for a mechanical engineer with relevant skills',
        'hiring mechanical engineer autocad solidworks',
        'design engineer manufacturing production cad',
    ],
    'Civil Engineer': [
        'looking for a civil engineer with relevant skills',
        'hiring civil engineer autocad structural staad',
        'site engineer construction project management',
    ],
    'Electrical Engineering': [
        'looking for a electrical engineering with relevant skills',
        'hiring electrical engineer plc scada power',
        'embedded systems engineer firmware microcontroller',
    ],
    'SAP Developer': [
        'looking for a sap developer with relevant skills',
        'hiring sap developer abap hana fiori modules',
        'sap consultant fi mm sd implementation support',
    ],
    'ETL Developer': [
        'looking for a etl developer with relevant skills',
        'hiring etl developer informatica datastage talend',
        'data warehouse etl developer sql bi reporting',
    ],
    'DotNet Developer': [
        'looking for a dotnet developer with relevant skills',
        'hiring dotnet developer c sharp asp net mvc',
        'net developer azure devops microservices angular',
    ],
    'Blockchain': [
        'looking for a blockchain with relevant skills',
        'hiring blockchain developer ethereum solidity',
        'web3 developer smart contracts nft defi crypto',
    ],
    'Hadoop': [
        'looking for a hadoop with relevant skills',
        'hiring hadoop developer spark hive kafka hdfs',
        'big data engineer spark scala pyspark databricks',
    ],
    'Automation Testing': [
        'looking for a automation testing with relevant skills',
        'hiring automation testing selenium java testng',
        'qa automation bdd cucumber robot framework',
    ],
    'Operations Manager': [
        'looking for a operations manager with relevant skills',
        'hiring operations manager supply chain logistics',
    ],
    'PMO': [
        'looking for a pmo with relevant skills',
        'hiring project manager pmp agile waterfall',
    ],
    'Arts': [
        'looking for a arts with relevant skills',
        'hiring creative designer illustration graphic arts',
    ],
    'Advocate': [
        'looking for a advocate with relevant skills',
        'hiring lawyer advocate legal litigation contract',
    ],
    'Sales': [
        'looking for a sales with relevant skills',
        'hiring sales executive b2b crm lead generation',
    ],
    'Health and fitness': [
        'looking for a health and fitness with relevant skills',
        'hiring fitness trainer nutrition diet wellness',
    ],
}

# ── Build augmented dataset ───────────────────────────
print("\nBuilding augmented training data...")
augmented = []

categories = resumes_df['Category'].unique().tolist()

for _, row in resumes_df.iterrows():
    category = row['Category']
    resume = str(row['Cleaned_Resume']).lower().strip()

    if not resume or category not in CATEGORY_JDS:
        continue

    # Positive: same category JDs — label 1
    for jd in CATEGORY_JDS[category]:
        augmented.append({
            'resume': resume,
            'jd': jd,
            'label': 1
        })

    # Negative: different category JDs — label 0
    # Use ONLY the first JD of each other category
    # (simple format same as training data)
    neg_count = 0
    for other_cat, other_jds in CATEGORY_JDS.items():
        if other_cat != category and neg_count < 3:
            augmented.append({
                'resume': resume,
                'jd': other_jds[0],  # Only simple JD
                'label': 0
            })
            neg_count += 1

aug_df = pd.DataFrame(augmented)
print(f"Augmented samples: {len(aug_df)}")
print(
    f"Augmented labels:\n{aug_df['label'].value_counts()}"
)

# Combine
combined = pd.concat([df, aug_df], ignore_index=True)
combined = combined.drop_duplicates(subset=['resume', 'jd'])
combined = combined.sample(
    frac=1, random_state=42
).reset_index(drop=True)

print(f"\nFinal combined: {len(combined)}")
print(f"Labels:\n{combined['label'].value_counts()}")

# Clean and prepare
combined['resume'] = combined['resume'].fillna('').str.lower()
combined['jd'] = combined['jd'].fillna('').str.lower()
combined['text'] = combined['resume'] + " " + combined['jd']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    combined['text'], combined['label'],
    test_size=0.15,
    random_state=42,
    stratify=combined['label']
)
print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")

# Vectorizer — balanced features
vectorizer = TfidfVectorizer(
    max_features=15000,
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
    strip_accents='unicode',
)
print("Fitting vectorizer...")
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Model — C=1.5 balanced
print("Training model...")
model = LogisticRegression(
    C=1.5,
    max_iter=1000,
    random_state=42,
    class_weight='balanced',
    solver='lbfgs',
)
model.fit(X_train_vec, y_train)

# Evaluate
y_pred = model.predict(X_test_vec)
accuracy = accuracy_score(y_test, y_pred)
print(f"\n✅ Accuracy: {accuracy * 100:.2f}%")
print(classification_report(y_test, y_pred))

# Save
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))
print("✅ Model saved! Restart FastAPI server.")
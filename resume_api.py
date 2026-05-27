import pandas as pd
import re
import ast
import pickle
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Load trained model 
print(" Loading model...")
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
print(" Model loaded!")

# FastAPI app 
app = FastAPI(
    title="HireIQ Resume Screening API",
    description="ML-based Resume Matching System",
    version="6.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#  Load dataset 
print("Loading dataset...")
df = pd.read_csv("data/resumes_with_skills.csv")
df = df.drop_duplicates(subset=['Cleaned_Resume'])
df = df.reset_index(drop=True)
print(f" Loaded {len(df)} resumes, "
      f"{df['Category'].nunique()} categories")

#  Category keywords 
CATEGORY_KEYWORDS = {
    'Data Science': [
        'data science', 'machine learning', 'deep learning',
        'tensorflow', 'pytorch', 'pandas', 'numpy',
        'scikit-learn', 'data analysis', 'statistics',
        'neural network', 'nlp', 'computer vision',
        'data scientist'
    ],
    'Python Developer': [
        'python', 'django', 'flask', 'fastapi',
        'rest api', 'python developer'
    ],
    'Java Developer': [
        'java', 'spring boot', 'spring', 'hibernate',
        'maven', 'j2ee', 'jdbc', 'java developer'
    ],
    'Web Designing': [
        'html', 'css', 'javascript', 'react', 'angular',
        'vue', 'ui', 'ux', 'frontend', 'web design',
        'bootstrap', 'figma', 'web designer'
    ],
    'DevOps Engineer': [
        'devops', 'docker', 'kubernetes', 'jenkins',
        'aws', 'azure', 'gcp', 'terraform', 'ci/cd',
        'linux', 'ansible', 'devops engineer'
    ],
    'Database': [
        'sql', 'mysql', 'postgresql', 'mongodb',
        'oracle', 'database', 'dba', 'nosql', 'redis',
        'database administrator'
    ],
    'Testing': [
        'testing', 'selenium', 'qa', 'quality assurance',
        'test automation', 'manual testing', 'jest',
        'pytest', 'test engineer'
    ],
    'HR': [
        'hr', 'human resources', 'recruitment',
        'payroll', 'hiring', 'talent acquisition',
        'onboarding', 'hr manager'
    ],
    'Business Analyst': [
        'business analyst', 'requirements', 'stakeholder',
        'agile', 'scrum', 'jira', 'process improvement',
        'business analysis'
    ],
    'Network Security Engineer': [
        'network', 'security', 'firewall', 'vpn',
        'cybersecurity', 'ethical hacking', 'penetration',
        'network security'
    ],
    'Mechanical Engineer': [
        'mechanical', 'autocad', 'solidworks',
        'manufacturing', 'production', 'cad', 'cam',
        'mechanical engineer'
    ],
    'Civil Engineer': [
        'civil', 'construction', 'structural', 'autocad',
        'staad', 'site management', 'civil engineer'
    ],
    'Electrical Engineering': [
        'electrical', 'circuit', 'plc', 'scada',
        'power systems', 'embedded', 'electrical engineer'
    ],
    'Blockchain': [
        'blockchain', 'ethereum', 'solidity',
        'smart contract', 'web3', 'cryptocurrency',
        'nft', 'blockchain developer'
    ],
    'Hadoop': [
        'hadoop', 'spark', 'hive', 'pig', 'hdfs',
        'big data', 'kafka', 'hbase', 'hadoop developer'
    ],
    'SAP Developer': [
        'sap', 'abap', 'sap hana', 'sap fi', 'sap mm',
        'sap sd', 'sap developer'
    ],
    'ETL Developer': [
        'etl', 'informatica', 'datastage', 'talend',
        'data warehouse', 'etl developer'
    ],
    'DotNet Developer': [
        '.net', 'dotnet', 'c#', 'asp.net', 'vb.net',
        'dotnet developer', '.net developer'
    ],
    'Automation Testing': [
        'automation', 'selenium', 'appium', 'robot framework',
        'testng', 'cucumber', 'automation testing'
    ],
    'Operations Manager': [
        'operations', 'supply chain', 'logistics',
        'operations manager', 'process management'
    ],
    'PMO': [
        'pmo', 'project management', 'pmp', 'prince2',
        'project manager', 'program manager'
    ],
}

# Skill weights
SKILL_WEIGHTS = {
    "python": 3, "machine learning": 3,
    "deep learning": 3, "data science": 3,
    "tensorflow": 3, "pytorch": 3, "keras": 3,
    "django": 3, "react": 3, "nodejs": 3,
    "java": 3, "spring boot": 3,
    "kubernetes": 3, "docker": 3,
    "sql": 2, "pandas": 2, "numpy": 2,
    "aws": 2, "azure": 2, "gcp": 2,
    "data analysis": 2, "javascript": 2,
    "rest api": 2, "mongodb": 2,
    "html": 1, "css": 1, "excel": 1,
    "git": 1, "linux": 1, "bash": 1,
}

#  Skill synonyms
SKILL_SYNONYMS = {
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "natural language processing": ["nlp"],
    "tensorflow": ["tf"],
    "javascript": ["js"],
    "artificial intelligence": ["ai"],
    "power bi": ["powerbi"],
    "rest api": ["restapi", "rest", "api"],
    "nodejs": ["node.js", "node js"],
    "spring boot": ["springboot"],
    "kubernetes": ["k8s"],
    "c#": ["csharp", "c sharp"],
}


# Helper functions
def normalize_skills(skills):
    normalized = []
    for skill in skills:
        skill_lower = str(skill).lower().strip()
        if not skill_lower:
            continue
        matched = False
        for main_skill, synonyms in SKILL_SYNONYMS.items():
            if (skill_lower == main_skill or
                    skill_lower in synonyms):
                normalized.append(main_skill)
                matched = True
                break
        if not matched:
            normalized.append(skill_lower)
    return list(set(normalized))


def detect_category(text):
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(
            1 for kw in keywords
            if kw in text_lower
        )
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else None


def calculate_skills_match(candidate_skills, required_skills):
    if not required_skills:
        return 0.0
    candidate_set = set(
        s.lower().strip() for s in candidate_skills
    )
    total_weight = 0
    matched_weight = 0
    for skill in required_skills:
        skill_lower = skill.lower().strip()
        weight = SKILL_WEIGHTS.get(skill_lower, 1)
        total_weight += weight
        if skill_lower in candidate_set:
            matched_weight += weight
    return (
        matched_weight / total_weight
        if total_weight > 0 else 0.0
    )


def get_experience_years(text):
    patterns = [
        r'(\d+)\+?\s*years?\s*of\s*experience',
        r'experience\s*of\s*(\d+)\+?\s*years?',
        r'(\d+)\+?\s*years?\s*experience',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            return int(matches[0])
    year_mentions = re.findall(
        r'\b(199\d|200\d|201\d|202\d)\b', text
    )
    return min(len(set(year_mentions)), 10)


def experience_match_score(resume_text, required_exp):
    candidate_years = get_experience_years(resume_text)
    exp_map = {
        '0-1': (0, 1),
        '1-3': (1, 3),
        '3-5': (3, 5),
        '5+':  (5, 99)
    }
    min_req, max_req = exp_map.get(
        required_exp, (0, 99)
    )
    if candidate_years >= min_req:
        return 1.0
    elif candidate_years >= min_req * 0.7:
        return 0.7
    elif candidate_years > 0:
        return 0.4
    else:
        return 0.2


def skills_match_score_csv(
    candidate_skills_str, required_skills
):
    """For CSV dataset scoring"""
    try:
        candidate_skills = ast.literal_eval(
            str(candidate_skills_str)
        )
    except Exception:
        candidate_skills = []
    return calculate_skills_match(
        candidate_skills, required_skills
    )


# ── Request models ────────────────────────────────────

class SingleResumeRequest(BaseModel):
    resume_text: str
    job_description: str
    required_skills: List[str]
    extracted_skills: List[str] = []
    experience_required: str = "any"


class JobRequest(BaseModel):
    job_description: str
    required_skills: list
    top_n: int = 5
    experience_level: str = "any"
    domain: str = "any"


# ── Health check ──────────────────────────────────────

@app.get("/")
def home():
    return {
        "status": "HireIQ API v6.0 ✅ Running",
        "total_resumes": len(df),
        "categories": df['Category'].nunique(),
        "endpoints": {
            "POST /score_resume": (
                "Score actual candidate resume — main endpoint"
            ),
            "POST /match": (
                "Match against CSV dataset"
            ),
            "GET /categories": "Get all categories",
            "GET /domains": "Get all domains",
        }
    }


@app.get("/categories")
def get_categories():
    return {
        "categories": df['Category'].value_counts().to_dict()
    }


@app.get("/domains")
def get_domains():
    return {
        "domains": sorted(df['Category'].unique().tolist())
    }


# ── MAIN: Score actual candidate resume ───────────────

@app.post("/score_resume")
def score_single_resume(request: SingleResumeRequest):
    try:
        resume_text = request.resume_text.lower().strip()
        job_desc = request.job_description.lower().strip()
        required_skills = normalize_skills(request.required_skills)
        extracted_skills = normalize_skills(
            request.extracted_skills
        ) if request.extracted_skills else []

        print(f"\n{'='*55}")
        print("Scoring resume...")
        print(f"Required : {required_skills}")
        print(f"Extracted: {extracted_skills}")

        # ── Step 1: Detect categories first ───────────
        resume_cat = detect_category(resume_text)
        job_cat = detect_category(job_desc)
        print(f"Resume category: {resume_cat}")
        print(f"Job category   : {job_cat}")

        # ── Step 2: Build smart JD for ML scoring ─────
        # Instead of using the raw job description
        # (which may be long and confuse the model),
        # build a simple JD similar to training format
        if job_cat and job_cat in CATEGORY_KEYWORDS:
            # Use category-style JD that model understands
            simple_jd = (
                f"looking for a "
                f"{job_cat.lower()} with relevant skills "
                + " ".join(required_skills[:5])
            )
        else:
            # Fallback to first 50 words of actual JD
            simple_jd = " ".join(
                job_desc.split()[:50]
            )

        print(f"Simple JD used : {simple_jd[:80]}...")

        # ── Step 3: ML Score ───────────────────────────
        combined = resume_text + " " + simple_jd
        vec = vectorizer.transform([combined])
        ml_proba = model.predict_proba(vec)[0]
        ml_score = float(
            ml_proba[1] if len(ml_proba) >= 2
            else ml_proba[0]
        )
        print(f"ML Score       : {ml_score*100:.2f}%")

        # ── Step 4: Skills Score ───────────────────────
        if extracted_skills:
            skills_score = calculate_skills_match(
                extracted_skills, required_skills
            )
        else:
            found = [
                s for s in required_skills
                if s in resume_text
            ]
            skills_score = calculate_skills_match(
                found, required_skills
            )
        print(f"Skills Score   : {skills_score*100:.2f}%")

        # ── Step 5: Experience Score ───────────────────
        exp_years_found = 0

        # Try explicit patterns first
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*(?:work\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*experience',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?exp',
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, resume_text)
            if match:
                exp_years_found = int(match.group(1))
                break

        # Fallback to unique year mentions
        if exp_years_found == 0:
            year_mentions = set(re.findall(
                r'\b(199\d|200\d|201\d|202\d)\b',
                resume_text
            ))
            if len(year_mentions) >= 3:
                exp_years_found = len(year_mentions) - 1
            elif len(year_mentions) == 2:
                exp_years_found = 1

        print(f"Years found    : {exp_years_found}")

        exp_map = {
            '0-1': (0, 1),
            '1-3': (1, 3),
            '3-5': (3, 5),
            '5+':  (5, 99)
        }
        req_exp = request.experience_required
        min_req = exp_map.get(req_exp, (0, 99))[0]

        if req_exp == "any" or req_exp == "0-1":
            exp_score = 1.0
        elif exp_years_found >= min_req:
            exp_score = 1.0
        elif exp_years_found >= max(min_req - 1, 0):
            exp_score = 0.75
        elif exp_years_found > 0:
            exp_score = 0.50
        else:
            # No experience info found — give neutral score
            exp_score = 0.60

        print(
            f"Exp Score      : {exp_score*100:.2f}% "
            f"(req:{req_exp}, found:{exp_years_found}yrs)"
        )

        # ── Step 6: Category Bonus ─────────────────────
        category_bonus = 0.0
        if resume_cat and job_cat and resume_cat == job_cat:
            category_bonus = 0.10
            print(f"Category Bonus : +10% ✅ ({resume_cat})")
        else:
            print(
                f"Category Bonus : 0% ❌ "
                f"({resume_cat} ≠ {job_cat})"
            )

        # ── Step 7: Final Score ────────────────────────
        # Skills 45% + ML 35% + Exp 20%
        base_score = (
            skills_score * 0.45 +
            ml_score     * 0.35 +
            exp_score    * 0.20
        )
        final_score = min(
            base_score + category_bonus, 1.0
        )

        # Safety rules
        # Rule 1: Good skills → minimum 55%
        if skills_score >= 0.6 and final_score < 0.50:
            final_score = 0.55
            print("Rule 1: skills≥60%, bumped to 55%")

        # Rule 2: Zero skills → cap at 30%
        if skills_score == 0.0:
            final_score = min(final_score, 0.30)
            print("Rule 2: 0% skills, capped at 30%")

        # Rule 3: Perfect skills + category match → 80%+
        if (skills_score >= 0.8 and
                category_bonus > 0 and
                final_score < 0.75):
            final_score = max(final_score, 0.75)
            print("Rule 3: excellent match, bumped to 75%+")

        print(f"Base Score     : {base_score*100:.2f}%")
        print(f"FINAL SCORE    : {final_score*100:.2f}%")
        print(f"{'='*55}\n")

        return {
            "ml_score": round(ml_score * 100, 2),
            "skills_score": round(skills_score * 100, 2),
            "experience_score": round(exp_score * 100, 2),
            "category_bonus": round(category_bonus * 100, 2),
            "final_score": round(final_score * 100, 2),
            "resume_category": resume_cat,
            "job_category": job_cat,
            "candidate_experience_years": exp_years_found,
            "status": "success"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "ml_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "category_bonus": 0,
            "final_score": 0,
            "status": f"error: {str(e)}"
        }


    try:
        resume_text = request.resume_text.lower().strip()
        job_desc = request.job_description.lower().strip()
        required_skills = normalize_skills(
            request.required_skills
        )
        extracted_skills = normalize_skills(
            request.extracted_skills
        ) if request.extracted_skills else []

        print(f"\n{'='*55}")
        print("📄 Scoring resume...")
        print(f"Required : {required_skills}")
        print(f"Extracted: {extracted_skills}")

        # ── ML Score ───────────────────────────────────
        combined = f"{resume_text} {job_desc}"
        vec = vectorizer.transform([combined])
        ml_proba = model.predict_proba(vec)[0]
        ml_score = float(
            ml_proba[1] if len(ml_proba) >= 2
            else ml_proba[0]
        )
        print(f"ML Score      : {ml_score*100:.2f}%")

        # ── Skills Score ───────────────────────────────
        if extracted_skills:
            skills_score = calculate_skills_match(
                extracted_skills, required_skills
            )
        else:
            found = [
                s for s in required_skills
                if s in resume_text
            ]
            skills_score = calculate_skills_match(
                found, required_skills
            )
        print(f"Skills Score  : {skills_score*100:.2f}%")

        # ── Experience Score ───────────────────────────
        # Better experience extraction
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*(?:work\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*experience',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?experience',
            r'worked\s*for\s*(\d+)\+?\s*years?',
        ]
        candidate_years = 0
        for pattern in exp_patterns:
            match = re.search(pattern, resume_text)
            if match:
                candidate_years = int(match.group(1))
                break

        # If no explicit mention, use year count as proxy
        if candidate_years == 0:
            year_mentions = re.findall(
                r'\b(199\d|200\d|201\d|202\d)\b',
                resume_text
            )
            unique_years = set(year_mentions)
            if len(unique_years) >= 4:
                candidate_years = len(unique_years) - 1
            elif len(unique_years) >= 2:
                candidate_years = 1
            else:
                candidate_years = 0

        print(f"Candidate exp : {candidate_years} years")

        exp_map = {
            '0-1': (0, 1),
            '1-3': (1, 3),
            '3-5': (3, 5),
            '5+':  (5, 99)
        }
        req_exp = request.experience_required
        min_req, max_req = exp_map.get(req_exp, (0, 99))

        if req_exp == "any" or req_exp == "0-1":
            exp_score = 1.0
        elif candidate_years >= min_req:
            exp_score = 1.0
        elif candidate_years >= min_req * 0.6:
            exp_score = 0.75
        elif candidate_years > 0:
            exp_score = 0.50
        else:
            exp_score = 0.30

        print(
            f"Experience Score: {exp_score*100:.2f}% "
            f"(required: {req_exp}, "
            f"found: {candidate_years}yrs)"
        )

        # ── Category Match ─────────────────────────────
        resume_cat = detect_category(resume_text)
        job_cat = detect_category(job_desc)
        category_bonus = 0.0

        if resume_cat and job_cat:
            if resume_cat == job_cat:
                category_bonus = 0.12
                print(
                    f"Category Bonus  : +12% "
                    f"✅ ({resume_cat} = {job_cat})"
                )
            else:
                print(
                    f"No Category Bonus ❌ "
                    f"({resume_cat} ≠ {job_cat})"
                )
        else:
            print(
                f"Category: resume={resume_cat}, "
                f"job={job_cat}"
            )

        # ── Smart Final Score ──────────────────────────
        # Skills are the most reliable signal
        # ML is good for domain matching
        # Experience adds context

        # Base calculation
        base_score = (
            skills_score * 0.45 +
            ml_score     * 0.40 +
            exp_score    * 0.15
        )

        # Add category bonus
        final_score = min(base_score + category_bonus, 1.0)

        # Minimum floor: if skills match well,
        # ensure decent score
        if skills_score >= 0.7 and final_score < 0.5:
            final_score = max(final_score, 0.55)
            print(
                "Applied skills floor: "
                "good skills match bumped to min 55%"
            )

        # Maximum cap: if no skills match,
        # cap the score
        if skills_score == 0.0 and final_score > 0.4:
            final_score = min(final_score, 0.35)
            print(
                "Applied skills cap: "
                "zero skills match capped at 35%"
            )

        print(f"Base Score    : {base_score*100:.2f}%")
        print(
            f"FINAL SCORE   : {final_score*100:.2f}%"
        )
        print(f"{'='*55}\n")

        return {
            "ml_score": round(ml_score * 100, 2),
            "skills_score": round(skills_score * 100, 2),
            "experience_score": round(exp_score * 100, 2),
            "category_bonus": round(
                category_bonus * 100, 2
            ),
            "final_score": round(final_score * 100, 2),
            "resume_category": resume_cat,
            "job_category": job_cat,
            "candidate_experience_years": candidate_years,
            "status": "success"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "ml_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "category_bonus": 0,
            "final_score": 0,
            "status": f"error: {str(e)}"
        }

    """
    Scores ONE specific candidate resume against a job.
    Uses YOUR trained model.pkl + vectorizer.pkl directly.
    This is called by Django on every resume upload.
    """
    try:
        resume_text = request.resume_text.lower().strip()
        job_desc = request.job_description.lower().strip()
        required_skills = normalize_skills(
            request.required_skills
        )
        extracted_skills = normalize_skills(
            request.extracted_skills
        ) if request.extracted_skills else []

        print(f"\n{'='*50}")
        print("Scoring resume...")
        print(f"Required skills : {required_skills}")
        print(f"Extracted skills: {extracted_skills}")

        # ── Step 1: ML Score ───────────────────────────
        # Same format as training: resume [SEP] jd
        combined = f"{resume_text} [SEP] {job_desc}"
        vec = vectorizer.transform([combined])
        ml_proba = model.predict_proba(vec)[0]

        # Index 1 = probability of label=1 (matched)
        ml_score = float(
            ml_proba[1] if len(ml_proba) >= 2
            else ml_proba[0]
        )
        print(
            f"ML Score        : "
            f"{ml_score:.4f} ({ml_score*100:.2f}%)"
        )

        # ── Step 2: Skills Score ───────────────────────
        if extracted_skills:
            skills_score = calculate_skills_match(
                extracted_skills, required_skills
            )
        else:
            # Fallback: find skills in resume text
            found = [
                skill for skill in required_skills
                if skill in resume_text
            ]
            skills_score = calculate_skills_match(
                found, required_skills
            )
        print(
            f"Skills Score    : "
            f"{skills_score:.4f} ({skills_score*100:.2f}%)"
        )

        # ── Step 3: Experience Score ───────────────────
        if request.experience_required != "any":
            exp_score = experience_match_score(
                resume_text,
                request.experience_required
            )
        else:
            raw_years = get_experience_years(resume_text)
            exp_score = min(raw_years / 5.0, 1.0)
        print(
            f"Experience Score: "
            f"{exp_score:.4f} ({exp_score*100:.2f}%)"
        )

        # ── Step 4: Category Match Bonus ──────────────
        resume_cat = detect_category(resume_text)
        job_cat = detect_category(job_desc)
        category_bonus = 0.0
        if (resume_cat and job_cat and
                resume_cat == job_cat):
            category_bonus = 0.10
        print(
            f"Resume category : {resume_cat}"
        )
        print(
            f"Job category    : {job_cat}"
        )
        if category_bonus > 0:
            print(
                f"Category Bonus  : +10% "
                f"(both are {resume_cat})"
            )

        # ── Step 5: Final Weighted Score ───────────────
        # Give more weight to skills for detailed JDs
        # ML model works better with simple JDs
        jd_word_count = len(job_desc.split())

        if jd_word_count > 30:
            # Detailed JD — trust skills more than ML
            base_score = (
                ml_score     * 0.35 +
                skills_score * 0.50 +
                exp_score    * 0.15
            )
            print(
                f"Detailed JD ({jd_word_count} words) — "
                f"using skills-heavy weighting"
            )
        else:
            # Simple JD — trust ML more
            base_score = (
                ml_score     * 0.55 +
                skills_score * 0.30 +
                exp_score    * 0.15
            )
            print(
                f"Simple JD ({jd_word_count} words) — "
                f"using ML-heavy weighting"
            )

        final_score = min(
            base_score + category_bonus, 1.0
        )

        print(
            f"Base Score      : {base_score:.4f}"
        )
        print(
            f"Final Score     : {final_score:.4f} "
            f"({final_score*100:.2f}%)"
        )
        print(f"{'='*50}\n")

        return {
            "ml_score": round(ml_score * 100, 2),
            "skills_score": round(skills_score * 100, 2),
            "experience_score": round(exp_score * 100, 2),
            "category_bonus": round(
                category_bonus * 100, 2
            ),
            "final_score": round(final_score * 100, 2),
            "resume_category": resume_cat,
            "job_category": job_cat,
            "status": "success"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "ml_score": 0,
            "skills_score": 0,
            "experience_score": 0,
            "category_bonus": 0,
            "final_score": 0,
            "status": f"error: {str(e)}"
        }


# ── Dataset match: score resumes from CSV ─────────────

@app.post("/match")
def match_resumes(request: JobRequest):
    """
    Match job against resumes in your CSV dataset.
    Used for bulk matching / finding similar profiles.
    """
    required_skills = normalize_skills(
        request.required_skills
    )
    filtered_df = df.copy()

    # Experience filter
    if request.experience_level != "any":
        filtered_df['Year_Count'] = filtered_df[
            'Resume'
        ].apply(
            lambda x: len(re.findall(
                r'\b(199\d|200\d|201\d|202\d)\b',
                str(x)
            ))
        )
        if request.experience_level == "fresher":
            filtered_df = filtered_df[
                filtered_df['Year_Count'] <= 2
            ]
        elif request.experience_level == "mid":
            filtered_df = filtered_df[
                (filtered_df['Year_Count'] >= 3) &
                (filtered_df['Year_Count'] <= 6)
            ]
        elif request.experience_level == "senior":
            filtered_df = filtered_df[
                filtered_df['Year_Count'] >= 7
            ]

    # Domain filter
    if request.domain != "any":
        filtered_df = filtered_df[
            filtered_df['Category'].str.lower() ==
            request.domain.lower()
        ]

    filtered_df = filtered_df.reset_index(drop=True)

    if len(filtered_df) == 0:
        return {
            "error": "No resumes found for selected filters",
            "top_candidates": []
        }

    # ML Scoring — same format as training
    job_desc = request.job_description.lower()
    scores = []
    for resume in filtered_df['Cleaned_Resume']:
        combined = (
            str(resume).lower() +
            " [SEP] " +
            job_desc
        )
        vec = vectorizer.transform([combined])
        score = float(
            model.predict_proba(vec)[0][1]
        )
        scores.append(score)

    temp_df = filtered_df.copy()
    temp_df['ML_Score'] = scores
    temp_df['Skills_Score'] = temp_df['Skills'].apply(
        lambda x: skills_match_score_csv(
            x, required_skills
        )
    )
    temp_df['Experience_Score'] = temp_df[
        'Resume'
    ].apply(
        lambda x: min(
            len(re.findall(
                r'\b(199\d|200\d|201\d|202\d)\b',
                str(x)
            )) / 10, 1.0
        )
    )
    temp_df['Final_Score'] = (
        temp_df['ML_Score']         * 0.60 +
        temp_df['Skills_Score']     * 0.30 +
        temp_df['Experience_Score'] * 0.10
    )

    temp_df = temp_df.sort_values(
        'Final_Score', ascending=False
    ).reset_index(drop=True)

    top_candidates = []
    for i in range(min(request.top_n, len(temp_df))):
        row = temp_df.iloc[i]
        try:
            skills = ast.literal_eval(str(row['Skills']))
        except Exception:
            skills = []

        top_candidates.append({
            "rank": i + 1,
            "category": row['Category'],
            "final_score": round(
                row['Final_Score'] * 100, 2
            ),
            "ml_score": round(
                row['ML_Score'] * 100, 2
            ),
            "skills_score": round(
                row['Skills_Score'] * 100, 2
            ),
            "experience_score": round(
                row['Experience_Score'] * 100, 2
            ),
            "skills": skills[:10],
            "resume_snippet": str(row['Resume'])[:300]
        })

    return {
        "total_resumes_scanned": len(filtered_df),
        "top_candidates": top_candidates
    }
import re
import spacy
import numpy as np
import fitz  # PyMuPDF
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nlp = spacy.load('en_core_web_sm')

SKILLS_DATABASE = [
    # Programming Languages — only match as whole words
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#',
    'ruby', 'php', 'swift', 'kotlin', 'scala', 'rust',
    # Removed 'r' and 'go' from general list — too short, cause false matches
    # They will be matched only if explicitly in job skills

    'django', 'flask', 'fastapi', 'react', 'angular', 'vue',
    'nodejs', 'spring', 'laravel', 'express',

    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'opencv',

    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite',
    'oracle', 'cassandra', 'elasticsearch',

    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
    'jenkins', 'git', 'github', 'gitlab', 'ci/cd',

    'html', 'css', 'bootstrap', 'tailwind',

    'data analysis', 'pandas', 'numpy', 'matplotlib', 'seaborn',
    'power bi', 'tableau', 'excel',

    'linux', 'bash', 'rest api', 'graphql', 'microservices',
    'agile', 'scrum', 'jira',

    # HR specific skills
    'recruitment', 'talent acquisition', 'onboarding',
    'payroll', 'performance management', 'hr operations',
    'employee relations', 'training', 'interviewing',
    'communication', 'interview coordination',
    'applicant tracking', 'ats', 'sourcing', 'screening',

    # Business skills
    'project management', 'business analysis', 'stakeholder management',
    'documentation', 'reporting', 'ms office', 'microsoft office',
    'presentation', 'negotiation', 'leadership', 'teamwork',

    # Sales
    'sales', 'crm', 'lead generation', 'b2b', 'marketing',
    'customer service', 'client management',

    # Design
    'figma', 'adobe', 'photoshop', 'illustrator', 'canva',
    'ui design', 'ux design', 'wireframing',
]

# Short skills that need EXACT word boundary matching
SHORT_SKILLS = ['r', 'go', 'c', 'vue', 'sap', 'sql']


def extract_skills(text, job_skills=None):
    text_lower = text.lower()
    found_skills = set()

    # Match job-specific skills first (highest priority)
    if job_skills:
        for skill in job_skills:
            skill_lower = skill.lower().strip()
            if len(skill_lower) <= 2:
                # Short skills need word boundary
                pattern = r'\b' + re.escape(skill_lower) + r'\b'
                if re.search(pattern, text_lower):
                    found_skills.add(skill_lower)
            else:
                if skill_lower in text_lower:
                    found_skills.add(skill_lower)

    # Match from global database
    for skill in SKILLS_DATABASE:
        skill_lower = skill.lower()
        if len(skill_lower) <= 2:
            # Short skills — strict word boundary
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill_lower)
        elif ' ' in skill_lower:
            # Multi-word skills — exact phrase match
            if skill_lower in text_lower:
                found_skills.add(skill_lower)
        else:
            # Normal skills — simple substring
            if skill_lower in text_lower:
                found_skills.add(skill_lower)

    # Remove false positives
    false_positives = set()
    for skill in found_skills:
        if skill == 'r' and 'r programming' not in text_lower and 'language r' not in text_lower:
            false_positives.add(skill)
        if skill == 'go' and 'golang' not in text_lower and 'go programming' not in text_lower:
            false_positives.add(skill)
        if skill == 'c' and 'c programming' not in text_lower and 'language c' not in text_lower:
            false_positives.add(skill)

    found_skills -= false_positives
    return list(found_skills)

EDUCATION_KEYWORDS = [
    # Bachelor degrees
    'btech', 'b.tech', 'b.e', 'be', 'bachelor', 'b.sc', 'bsc',
    'bca', 'b.ca', 'bba', 'b.com', 'bcom', 'ba', 'b.a',

    # Master degrees
    'mtech', 'm.tech', 'm.e', 'me', 'master', 'masters',
    'msc', 'm.sc', 'mca', 'm.ca', 'mba', 'm.b.a',
    'ms', 'm.s', 'ma', 'm.a', 'pgdm', 'post graduate',
    'postgraduate', 'pg diploma', 'post graduation',

    # Other degrees
    'phd', 'ph.d', 'doctorate', 'doctoral',
    'diploma', 'polytechnic',
    '10th', '12th', 'ssc', 'hsc', 'intermediate',

    # Fields
    'computer science', 'information technology',
    'computer engineering', 'software engineering',
    'electronics', 'electrical', 'mechanical',
    'civil engineering', 'data science',
    'artificial intelligence', 'machine learning',
    'information systems', 'it', 'cse', 'ece', 'eee',
]


EDUCATION_LEVELS = {
    # Level 1 — School
    '10th': 1, 'ssc': 1, 'matriculation': 1,

    # Level 2 — Higher Secondary
    '12th': 2, 'hsc': 2, 'intermediate': 2,
    'higher secondary': 2,

    # Level 3 — Diploma
    'diploma': 3, 'polytechnic': 3,

    # Level 4 — Bachelor
    'bachelor': 4, 'bachelors': 4, 'btech': 4, 'b.tech': 4,
    'b.e': 4, 'be': 4, 'bsc': 4, 'b.sc': 4, 'bca': 4,
    'b.ca': 4, 'bba': 4, 'bcom': 4, 'b.com': 4,
    'ba': 4, 'b.a': 4, 'undergraduate': 4, 'ug': 4,
    'graduation': 4, 'graduate': 4,

    # Level 5 — Master
    'master': 5, 'masters': 5, 'mtech': 5, 'm.tech': 5,
    'msc': 5, 'm.sc': 5, 'mca': 5, 'm.ca': 5,
    'mba': 5, 'm.b.a': 5, 'ms': 5, 'm.s': 5,
    'ma': 5, 'm.a': 5, 'me': 5, 'm.e': 5,
    'pgdm': 5, 'post graduate': 5, 'postgraduate': 5,
    'pg': 5,

    # Level 6 — PhD
    'phd': 6, 'ph.d': 6, 'doctorate': 6, 'doctoral': 6,
}

def get_education_level(text):
    """Returns numeric level of education found in text"""
    if not text or text == "Not specified":
        return 0
    text_lower = text.lower()
    highest_level = 0
    for keyword, level in EDUCATION_LEVELS.items():
        if keyword in text_lower:
            if level > highest_level:
                highest_level = level
    return highest_level


def extract_text_from_pdf(file_path):
    try:
        text = ""
        doc = fitz.open(file_path)

        for page in doc:
            text += page.get_text()

        return text
    except:
        return ""

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except:
        return ""

def extract_text_from_resume(file_path):
    file_path = str(file_path)
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    return ""

def extract_name(text):
    skip_words = [
        'java', 'python', 'django', 'react', 'sql',
        'html', 'css', 'aws', 'git', 'linux', 'resume',
        'curriculum', 'vitae', 'objective', 'summary',
        'experience', 'education', 'skills', 'projects',
        'btech', 'mtech', 'mca', 'bca', 'bachelor',
        'master', 'engineer', 'developer', 'profile',
    ]
    lines = text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if (2 <= len(words) <= 4 and
                line.replace(' ', '').isalpha() and
                not any(
                    skip in line.lower()
                    for skip in skip_words
                )):
            return line
    doc = nlp(text[:500])
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            if not any(
                skip in ent.text.lower()
                for skip in skip_words
            ):
                return ent.text
    return "Unknown"

def extract_email(text):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""

def extract_phone(text):
    # Indian + general formats
    patterns = [
        r'\+91[\s\-]?\d{10}',          # +91 9876543210
        r'\b\d{10}\b',                # 9876543210
        r'\(\d{3}\)\s*\d{3}[-\s]?\d{4}',  # (080) 123 4567
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]

    return ""

# def extract_skills(text, job_skills=None):
#     text_lower = text.lower()
#     found_skills = set()
#
#     # job-specific skills
#     if job_skills:
#         for skill in job_skills:
#             if skill.lower() in text_lower:
#                 found_skills.add(skill.lower())
#
#     # global database
#     for skill in SKILLS_DATABASE:
#         if skill.lower() in text_lower:
#             found_skills.add(skill.lower())
#
#     return list(found_skills)

def extract_experience(text):
    text_lower = text.lower()
    # patterns like "3 years"
    patterns = [
        r'(\d+)\+?\s*years?\s*of\s*experience',
        r'(\d+)\+?\s*years?\s*experience',
        r'(\d+)\s*yrs',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            return f"{matches[0]} years"

    # internship / fresher
    if 'intern' in text_lower or 'freelance' in text_lower:
        return "0-1 years"

    # Detect date ranges but ignore year numbers
    date_patterns = re.findall(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', text_lower)
    if date_patterns:
        return "0-1 years"

    return "Not specified"


def extract_education(text):
    lines = text.split('\n')
    education_lines = []

    # Step 1: Find education section
    for i, line in enumerate(lines):
        if 'education' in line.lower():
            education_lines.extend(lines[i:i+5])
            break

    # Step 2: If not found, fallback to keyword search
    if not education_lines:
        for line in lines:
            if any(keyword in line.lower() for keyword in EDUCATION_KEYWORDS):
                education_lines.append(line)

    # Step 3: Clean result
    if education_lines:
        return ' '.join(education_lines[:3])

    return "Not specified"

def parse_resume(file_path, job_skills=None):
    raw_text = extract_text_from_resume(file_path)
    if not raw_text:
        return None
    return {
        'raw_text': raw_text,
        'full_name': extract_name(raw_text),
        'email': extract_email(raw_text),
        'phone': extract_phone(raw_text),
        'extracted_skills': ', '.join(extract_skills(raw_text, job_skills)),
        'extracted_experience': extract_experience(raw_text),
        'extracted_education': extract_education(raw_text),
    }

def calculate_skills_score(candidate_skills, job_skills):
    if not job_skills:
        return 0.0
    candidate_set = set([s.lower().strip() for s in candidate_skills])
    job_set = set([s.lower().strip() for s in job_skills])
    matched = candidate_set.intersection(job_set)
    return round((len(matched) / len(job_set)) * 100, 2)



def calculate_education_score(candidate_edu, required_edu):
    """
    Smart education scoring:
    - If candidate level >= required level → 100%
    - If candidate level is one below required → 60%
    - If candidate level is two below → 30%
    - Keyword matching as fallback
    """
    if not candidate_edu or candidate_edu == "Not specified":
        return 0.0

    candidate_level = get_education_level(candidate_edu)
    required_level = get_education_level(required_edu)

    # If we found levels for both — use level comparison
    if candidate_level > 0 and required_level > 0:
        if candidate_level >= required_level:
            return 100.0
        elif candidate_level == required_level - 1:
            return 60.0
        elif candidate_level == required_level - 2:
            return 30.0
        else:
            return 10.0

    # Fallback — keyword matching
    candidate_lower = candidate_edu.lower()
    required_lower = required_edu.lower()
    keywords = [
        w for w in required_lower.split()
        if len(w) > 2
    ]
    if not keywords:
        return 50.0
    matches = sum(
        1 for kw in keywords if kw in candidate_lower
    )
    score = (matches / len(keywords)) * 100
    return round(min(score, 100), 2)

def calculate_text_similarity(resume_text, job_description):
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(float(similarity[0][0]) * 100, 2)
    except:
        return 0.0

def calculate_experience_score(candidate_exp, required_exp):
    # If entry level required, everyone passes
    if required_exp == '0-1':
        return 80.0  # Give good score for entry level

    exp_map = {'1-3': 2, '3-5': 4, '5+': 6}
    required_years = exp_map.get(required_exp, 2)
    numbers = re.findall(r'\d+', str(candidate_exp))
    if numbers:
        candidate_years = int(numbers[0])
        if candidate_years >= required_years:
            return 100.0
        elif candidate_years >= required_years * 0.7:
            return 70.0
        else:
            return 30.0
    return 30.0


def calculate_overall_score(candidate, job):
    # Skills score
    try:
        skills_score = calculate_skills_score(
            candidate.get_skills_list(),
            job.get_skills_list()
        )
    except Exception as e:
        print(f"Skills score error: {e}")
        skills_score = 0.0

    # Experience score
    try:
        experience_score = calculate_experience_score(
            candidate.extracted_experience or '',
            job.experience_required or '0-1'
        )
        # Safety check — never None
        if experience_score is None:
            experience_score = 50.0
    except Exception as e:
        print(f"Experience score error: {e}")
        experience_score = 50.0

    # Education score
    try:
        education_score = calculate_education_score(
            candidate.extracted_education or '',
            job.education_required or ''
        )
        if education_score is None:
            education_score = 0.0
    except Exception as e:
        print(f"Education score error: {e}")
        education_score = 0.0

    # Text similarity
    try:
        raw_text = candidate.raw_text or ''
        job_desc = job.description or ''
        if raw_text and job_desc:
            text_similarity = calculate_text_similarity(
                raw_text, job_desc
            )
        else:
            text_similarity = 0.0
    except Exception as e:
        print(f"Text similarity error: {e}")
        text_similarity = 0.0

    print(
        f"NLP Breakdown → "
        f"Skills:{skills_score}% "
        f"Exp:{experience_score}% "
        f"Edu:{education_score}% "
        f"Text:{text_similarity}%"
    )

    overall = (
        skills_score     * 0.40 +
        experience_score * 0.25 +
        education_score  * 0.20 +
        text_similarity  * 0.15
    )
    return {
        'skills_score': round(skills_score, 2),
        'experience_score': round(experience_score, 2),
        'education_score': round(education_score, 2),
        'overall_score': round(overall, 2),
    }
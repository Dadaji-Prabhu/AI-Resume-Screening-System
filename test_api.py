import requests

tests = [
    {
        'name': 'Python Dev → Python job',
        'data': {
            'resume_text': 'python developer django rest api sql git machine learning data analysis pandas numpy flask',
            'job_description': 'Looking for a Python Developer with Django REST API and SQL experience',
            'required_skills': ['python', 'django', 'rest api', 'sql', 'git'],
            'extracted_skills': ['python', 'django', 'sql', 'git', 'machine learning'],
            'experience_required': '1-3'
        }
    },
    {
        'name': 'Java Dev → HR job (should be LOW)',
        'data': {
            'resume_text': 'java developer spring boot hibernate maven junit sql java developer',
            'job_description': 'Looking for HR Manager with recruitment payroll hiring experience',
            'required_skills': ['hr', 'recruitment', 'payroll', 'hiring'],
            'extracted_skills': ['java', 'spring boot', 'hibernate', 'sql'],
            'experience_required': '1-3'
        }
    },
    {
        'name': 'Data Scientist → DS job',
        'data': {
            'resume_text': 'data scientist machine learning deep learning tensorflow pytorch pandas numpy scikit learn nlp computer vision neural networks python data science',
            'job_description': 'Looking for Data Science with machine learning and deep learning experience',
            'required_skills': ['machine learning', 'python', 'tensorflow', 'pandas', 'deep learning'],
            'extracted_skills': ['machine learning', 'deep learning', 'tensorflow', 'pandas', 'numpy', 'python'],
            'experience_required': '3-5'
        }
    },
    {
        'name': 'DevOps → DevOps job',
        'data': {
            'resume_text': 'devops engineer docker kubernetes jenkins aws azure terraform ansible linux bash ci cd pipeline',
            'job_description': 'Looking for a DevOps Engineer with Docker Kubernetes and AWS experience',
            'required_skills': ['docker', 'kubernetes', 'aws', 'jenkins', 'terraform'],
            'extracted_skills': ['docker', 'kubernetes', 'aws', 'terraform', 'ansible', 'linux'],
            'experience_required': '3-5'
        }
    },
]

for test in tests:
    r = requests.post(
        'http://127.0.0.1:8001/score_resume',
        json=test['data']
    )
    res = r.json()
    print()
    print(f"Test: {test['name']}")
    print(f"  Final  : {res['final_score']}%")
    print(f"  ML     : {res['ml_score']}%")
    print(f"  Skills : {res['skills_score']}%")
    print(f"  Exp    : {res['experience_score']}%")
    print(f"  Cat    : {res['resume_category']} → {res['job_category']}")
    print(f"  Bonus  : {res['category_bonus']}%")
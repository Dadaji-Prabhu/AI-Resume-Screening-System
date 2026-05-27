import random

# ── Domain Detection ──────────────────────────────────────
DOMAIN_KEYWORDS = {
    'software_engineering': [
        'developer', 'engineer', 'programmer',
        'backend', 'frontend', 'software', 'devops',
        'fullstack', 'full stack', 'web developer',
    ],
    'data_science': [
        'data scientist', 'ml engineer', 'ai engineer',
        'machine learning', 'data analyst', 'data engineer',
        'business analyst',
    ],
    'culinary': [
        'chef', 'cook', 'kitchen', 'baker',
        'culinary', 'sous chef', 'pastry',
    ],
    'healthcare': [
        'doctor', 'nurse', 'healthcare', 'medical',
        'therapist', 'pharmacist', 'surgeon',
    ],
    'sales': [
        'sales', 'business development',
        'account manager', 'marketing',
    ],
    'hr': [
        'hr', 'human resource', 'recruiter',
        'talent acquisition', 'people operations',
    ],
    'finance': [
        'accountant', 'finance', 'analyst',
        'banking', 'auditor', 'ca',
    ],
    'design': [
        'designer', 'ui', 'ux', 'graphic',
        'product designer', 'creative',
    ],
}

# ── Question Banks by Domain ──────────────────────────────
QUESTION_BANKS = {
    'software_engineering': {
        'python': [
            "Explain the difference between a list and tuple in Python and when you would use each.",
            "What are Python generators and when would you use yield instead of return?",
            "Explain *args and **kwargs with an example.",
            "How do you handle exceptions in Python? Explain try, except, else, finally.",
            "What are decorators in Python? Give a real use case.",
            "What is the difference between shallow copy and deep copy?",
        ],
        'django': [
            "Explain Django MTV architecture and how it differs from MVC.",
            "What is the difference between select_related and prefetch_related?",
            "How do you handle database migrations when working in a team?",
            "How have you implemented authentication and authorization in Django?",
            "What is Django middleware and when would you write custom middleware?",
        ],
        'react': [
            "Explain the difference between props and state in React.",
            "What are React hooks? Which ones have you used most?",
            "What is the virtual DOM and how does it improve performance?",
            "How do you manage global state in a React application?",
            "What is the difference between controlled and uncontrolled components?",
        ],
        'sql': [
            "What is the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN?",
            "How would you find duplicate records in a database table?",
            "Explain the difference between WHERE and HAVING clauses.",
            "What are indexes and when should you use them?",
            "Write a query to find the second highest salary from an employee table.",
        ],
        'java': [
            "Explain the four principles of OOP with real examples.",
            "What is the difference between an abstract class and interface in Java?",
            "Explain Java's garbage collection mechanism.",
            "What are Java Streams and how have you used them?",
            "What design patterns have you applied in your Java projects?",
        ],
        'docker': [
            "Explain the difference between a Docker image and a container.",
            "How do you handle environment variables securely in Docker?",
            "What is Docker Compose and when would you use it?",
            "How do you optimize Docker image size?",
        ],
        'aws': [
            "What AWS services have you worked with and for what purpose?",
            "Explain the difference between EC2, Lambda, and ECS.",
            "How do you handle security and IAM in AWS?",
            "What is auto-scaling and how have you implemented it?",
        ],
        'machine learning': [
            "Explain the difference between supervised and unsupervised learning.",
            "How do you handle imbalanced datasets?",
            "What metrics would you use to evaluate a classification model?",
            "Explain overfitting — how do you detect and prevent it?",
            "Walk me through building an ML pipeline end to end.",
        ],
    },
    'data_science': {
        'data analysis': [
            "How do you handle missing data in a dataset?",
            "Explain the difference between correlation and causation.",
            "How do you validate the quality of a dataset?",
            "Walk me through how you would approach analyzing a new dataset.",
        ],
        'python': [
            "How have you used Pandas for data manipulation?",
            "What visualization libraries have you used and why?",
            "How do you handle large datasets that don't fit in memory?",
        ],
        'machine learning': [
            "How do you select the right algorithm for a problem?",
            "Explain cross-validation and why it matters.",
            "What is feature engineering and how have you applied it?",
        ],
    },
    'culinary': {
        'cooking': [
            "How do you manage timing during peak kitchen hours?",
            "Describe your process for maintaining food consistency.",
            "How do you handle menu planning and seasonal ingredients?",
        ],
        'food safety': [
            "Explain HACCP principles and how you apply them.",
            "How do you ensure food hygiene standards are maintained?",
            "What is your process for handling food allergens?",
        ],
        'kitchen management': [
            "How do you handle staff coordination in a busy kitchen?",
            "Describe a situation where you handled a kitchen emergency.",
            "How do you manage food costs and reduce wastage?",
        ],
        'baking': [
            "What factors are most important in successful baking?",
            "How do you troubleshoot failed baked products?",
            "How do you adapt recipes for large scale production?",
        ],
    },
    'healthcare': {
        'patient care': [
            "How do you handle difficult or aggressive patients?",
            "Describe a situation where quick decision-making was critical.",
            "How do you maintain empathy during stressful situations?",
        ],
        'nursing': [
            "How do you prioritize care for multiple patients simultaneously?",
            "How do you handle medication errors?",
            "Describe your experience with emergency response.",
        ],
    },
    'sales': {
        'sales': [
            "How do you handle customer objections?",
            "Describe a successful sales strategy you used and the result.",
            "How do you qualify leads?",
        ],
        'negotiation': [
            "Describe a difficult negotiation you handled successfully.",
            "How do you build long-term client relationships?",
            "How do you handle a client who wants a lower price?",
        ],
        'crm': [
            "What CRM tools have you used and how did you use them?",
            "How do you track and manage your sales pipeline?",
        ],
    },
    'hr': {
        'recruitment': [
            "How do you source candidates for hard-to-fill positions?",
            "How do you ensure a positive candidate experience?",
            "How do you handle unconscious bias in screening?",
        ],
        'communication': [
            "How do you handle conflicts between employees?",
            "Describe your approach to giving difficult feedback.",
        ],
        'hr operations': [
            "How do you manage payroll discrepancies?",
            "What HRMS tools have you worked with?",
            "How do you handle employee grievances?",
        ],
    },
    'finance': {
        'accounting': [
            "Explain the difference between accounts payable and receivable.",
            "How do you handle month-end closing processes?",
            "What accounting software have you worked with?",
        ],
        'analysis': [
            "How do you perform financial forecasting?",
            "What financial ratios do you track and why?",
        ],
    },
    'design': {
        'figma': [
            "Walk me through your design process from brief to final output.",
            "How do you handle design feedback from stakeholders?",
        ],
        'ui design': [
            "How do you ensure accessibility in your designs?",
            "How do you create and maintain a design system?",
        ],
        'ux design': [
            "How do you conduct user research?",
            "Describe a time your UX research changed the product direction.",
        ],
    },
}

# ── Situational Questions by Domain ───────────────────────
SITUATIONAL_QUESTIONS = {
    'software_engineering': [
        "Production crashes at 2 AM. What are your immediate steps?",
        "How would you approach refactoring a legacy codebase with no documentation?",
        "A client wants a feature in 3 days that needs 2 weeks. How do you handle this?",
        "How do you ensure code quality under tight deadlines?",
    ],
    'data_science': [
        "Your model achieves 95% accuracy on test data but fails in production. What do you investigate?",
        "How would you explain a complex ML model to a non-technical stakeholder?",
        "A stakeholder wants insights from a clearly noisy dataset. How do you handle this?",
    ],
    'culinary': [
        "A customer sends back a dish during peak service. What do you do?",
        "How would you manage kitchen delays during a fully booked dinner service?",
        "A key ingredient is unavailable last minute. How do you adapt?",
    ],
    'healthcare': [
        "How would you handle a medical emergency on the ward?",
        "A patient refuses recommended treatment. How do you respond?",
        "Two critical patients need attention simultaneously. How do you prioritize?",
    ],
    'sales': [
        "A major client is threatening to leave. How do you retain them?",
        "How would you hit targets during a slow quarter?",
        "You have a difficult prospect who keeps postponing. What is your approach?",
    ],
    'hr': [
        "Two equally qualified candidates for one position — how do you decide?",
        "A manager keeps rejecting good candidates without clear reason. How do you handle this?",
        "An employee files a complaint against their manager. What is your process?",
    ],
    'finance': [
        "You discover a discrepancy in the accounts during audit. What do you do?",
        "How would you present a financial report to non-finance stakeholders?",
    ],
    'design': [
        "A client rejects your design completely at the last stage. How do you respond?",
        "How do you handle conflicting feedback from multiple stakeholders?",
    ],
    'general': [
        "How do you prioritize when handling multiple responsibilities?",
        "Describe how you handle conflict in the workplace.",
        "Tell me about a time you had to adapt quickly to change.",
    ],
}

# ── Behavioral Questions ──────────────────────────────────
BEHAVIORAL_QUESTIONS = [
    "Tell me about yourself and your career journey.",
    "Describe the most challenging project you have worked on.",
    "Give an example of a time you had to learn something new very quickly.",
    "How do you handle criticism of your work?",
    "Describe a time you showed leadership without a formal title.",
    "Tell me about a time you failed and what you learned.",
    "How do you stay motivated during repetitive or difficult tasks?",
    "Describe a time you went above and beyond your job responsibilities.",
]

# ── Gap Question Templates ─────────────────────────────────
GAP_TEMPLATE = (
    "This role requires {skill} which is not highlighted "
    "in your resume. What exposure do you have to it and "
    "what steps are you taking to develop this skill?"
)

# ── Tips by Category ──────────────────────────────────────
TIPS = {
    'Opening': "Keep it under 2 minutes. Focus on relevant experience and why you want this role.",
    'Technical': "Use specific examples from real projects. Mention the impact of your work.",
    'Skill Gap': "Be honest about your current level but show enthusiasm and a clear learning plan.",
    'Situational': "Use the STAR method — Situation, Task, Action, Result.",
    'Behavioral': "Be specific and use real examples. Quantify results where possible.",
    'Closing': "Always prepare 2-3 thoughtful questions. Ask about team, growth, or challenges.",
}

ICONS = {
    'Opening': '👋',
    'Technical': '💻',
    'Skill Gap': '🎯',
    'Situational': '🎭',
    'Behavioral': '🧠',
    'Closing': '🤝',
}

DIFFICULTY = {
    'Opening': 'Easy',
    'Technical': 'Medium',
    'Skill Gap': 'Hard',
    'Situational': 'Medium',
    'Behavioral': 'Easy',
    'Closing': 'Easy',
}


def normalize_skills(skills_input):
    if isinstance(skills_input, str):
        skills_input = skills_input.split(',')
    return [s.lower().strip() for s in skills_input if s.strip()]


def detect_domain(job_title):
    title = job_title.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                return domain
    return 'general'


def build_question(category, question_text, skill=None):
    cat_key = category.split(' — ')[0]
    icon = ICONS.get(cat_key, '❓')
    tip = TIPS.get(cat_key, 'Think carefully and be specific.')
    difficulty = DIFFICULTY.get(cat_key, 'Medium')
    if skill:
        tip = f"You listed {skill} — back your answer with a specific project example."
    return {
        'category': category,
        'icon': icon,
        'difficulty': difficulty,
        'question': question_text,
        'tip': tip,
    }


def generate_questions(candidate, job):
    """
    Generate personalized interview questions.
    Works for Django model objects.
    candidate: Candidate model instance
    job: Job model instance
    """
    questions = []

    # Extract skills
    candidate_skills = normalize_skills(
        candidate.extracted_skills or ''
    )
    job_skills = job.get_skills_list()
    job_title = job.title

    # Detect domain
    domain = detect_domain(job_title)
    domain_bank = QUESTION_BANKS.get(domain, {})

    matched_skills = [
        s for s in candidate_skills
        if s in domain_bank
    ]
    missing_skills = [
        s for s in job_skills
        if s not in candidate_skills
    ]

    # 1 — Opening
    questions.append(build_question(
        'Opening',
        f"Please introduce yourself and share your background, "
        f"skills, projects, or experience relevant to the "
        f"{job_title} role."
    ))

    # 2 — Technical questions for matched skills
    tech_added = 0
    for skill in matched_skills[:4]:
        if skill in domain_bank and tech_added < 4:
            q = random.choice(domain_bank[skill])
            questions.append(build_question(
                f'Technical — {skill.title()}', q, skill
            ))
            tech_added += 1
# If no matched skills found use job skills
    if tech_added == 0:
        for skill in job_skills[:3]:
            if skill in domain_bank:
                q = random.choice(domain_bank[skill])
                questions.append(build_question(
                    f'Technical — {skill.title()}', q, skill
                ))
                tech_added += 1

    # 3 — Skill gap questions
    for skill in missing_skills[:2]:
        questions.append(build_question(
            'Skill Gap',
            GAP_TEMPLATE.format(skill=skill)
        ))

    # 4 — Situational questions
    sit_pool = SITUATIONAL_QUESTIONS.get(
        domain,
        SITUATIONAL_QUESTIONS['general']
    )
    for q in random.sample(sit_pool, min(2, len(sit_pool))):
        questions.append(build_question('Situational', q))

    # 5 — Behavioral questions
    for q in random.sample(BEHAVIORAL_QUESTIONS, min(2, len(BEHAVIORAL_QUESTIONS))):
        questions.append(build_question('Behavioral', q))

    # 6 — Closing
    questions.append(build_question(
        'Closing',
        f"Do you have any questions for us about the "
        f"{job_title} role or {job.company.company_name}?"
    ))

    return questions
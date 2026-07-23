#!/usr/bin/env python3
"""Luqi AI Jobs & Skills Module — Career development, CV building, interview prep,
skills assessment, salary guides, career planning, and freelancing advice.
"""

import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA — CV Templates, Interview Questions, Salary Data, Career Paths
# ═══════════════════════════════════════════════════════════════════════════════

CV_TEMPLATES = {
    "professional": {
        "name": "Professional",
        "description": "Clean, ATS-friendly format with clear section headers.",
        "sections": ["Contact", "Summary", "Experience", "Education", "Skills", "Certifications"],
    },
    "modern": {
        "name": "Modern",
        "description": "Two-column layout with skills sidebar and visual highlights.",
        "sections": ["Contact", "Summary", "Experience", "Education", "Skills", "Projects", "Languages"],
    },
    "executive": {
        "name": "Executive",
        "description": "Premium format for senior roles with achievement focus.",
        "sections": ["Contact", "Executive Summary", "Leadership Experience", "Board Positions", "Education", "Awards"],
    },
}

# 500+ interview questions organized by field
INTERVIEW_QUESTIONS: Dict[str, Dict[str, List[str]]] = {
    "software": {
        "entry": [
            "What is the difference between a list and a tuple in Python?",
            "Explain the concept of version control and why Git is used.",
            "What is an API and how have you used one?",
            "Describe the MVC architecture pattern.",
            "What is the difference between HTTP GET and POST?",
        ],
        "mid": [
            "Explain how you would design a scalable notification system.",
            "What are database indexes and when should you use them?",
            "Describe a time you refactored legacy code. What was your approach?",
            "How do you handle race conditions in concurrent programming?",
            "Explain microservices vs monolithic architecture trade-offs.",
        ],
        "senior": [
            "Design a distributed key-value store like Redis.",
            "How would you migrate a monolith to microservices without downtime?",
            "Explain CAP theorem and its practical implications.",
            "How do you ensure code quality across a 50+ developer team?",
            "Design a real-time collaborative editing system.",
        ],
    },
    "data_science": {
        "entry": [
            "Explain the difference between supervised and unsupervised learning.",
            "What is overfitting and how do you prevent it?",
            "Describe the bias-variance tradeoff.",
            "What is the Central Limit Theorem?",
            "Explain how a decision tree works.",
        ],
        "mid": [
            "Compare Random Forest and Gradient Boosting. When would you use each?",
            "How do you handle imbalanced datasets?",
            "Explain cross-validation and why it is important.",
            "What are the assumptions of linear regression?",
            "Describe a machine learning project you led end-to-end.",
        ],
        "senior": [
            "Design a recommendation system for an e-commerce platform.",
            "How would you deploy and monitor a model in production?",
            "Explain transformers and attention mechanisms in detail.",
            "How do you handle concept drift in production ML systems?",
            "Design an A/B testing framework for model improvements.",
        ],
    },
    "nursing": {
        "entry": [
            "Why did you choose nursing as a career?",
            "How do you handle stressful situations in a clinical setting?",
            "Describe your experience with patient documentation.",
            "What would you do if you noticed a colleague making a medication error?",
            "How do you prioritize care when multiple patients need attention?",
        ],
        "mid": [
            "Describe a time you had to advocate for a patient.",
            "How do you stay current with evidence-based nursing practices?",
            "Explain your experience with electronic health records (EHR) systems.",
            "How do you handle conflict within your healthcare team?",
            "Describe your approach to patient education.",
        ],
        "senior": [
            "How would you implement a quality improvement initiative on your unit?",
            "Describe your leadership style and how you mentor junior nurses.",
            "How do you handle ethical dilemmas in patient care?",
            "What strategies do you use to reduce hospital-acquired infections?",
            "How would you manage staffing during a crisis or disaster?",
        ],
    },
    "finance": {
        "entry": [
            "Explain the three main financial statements.",
            "What is the difference between net income and cash flow?",
            "Describe the time value of money concept.",
            "What is WACC and why is it important?",
            "Explain working capital and its components.",
        ],
        "mid": [
            "Walk me through a DCF valuation.",
            "How do you assess credit risk for a corporate borrower?",
            "Explain hedging strategies using derivatives.",
            "What factors would you consider when valuing a tech startup?",
            "Describe a complex financial model you have built.",
        ],
        "senior": [
            "How would you structure a leveraged buyout?",
            "Design a risk management framework for a multinational corporation.",
            "Explain quantitative easing and its market implications.",
            "How do you evaluate M&A synergies?",
            "What is your approach to portfolio construction in volatile markets?",
        ],
    },
    "marketing": {
        "entry": [
            "Explain the 4Ps of marketing.",
            "What is the difference between SEO and SEM?",
            "How do you measure the success of a marketing campaign?",
            "Describe a social media campaign you have managed.",
            "What marketing tools are you proficient with?",
        ],
        "mid": [
            "How would you develop a go-to-market strategy for a new product?",
            "Explain customer segmentation and its importance.",
            "How do you allocate budget across digital marketing channels?",
            "Describe how you use data analytics to inform marketing decisions.",
            "What is your approach to brand positioning?",
        ],
        "senior": [
            "How would you build a marketing team from scratch?",
            "Design a marketing strategy for entering a new geographic market.",
            "How do you measure and improve customer lifetime value?",
            "Explain how you would handle a brand crisis.",
            "What is your vision for the future of digital marketing?",
        ],
    },
    "general": {
        "entry": [
            "Tell me about yourself.",
            "Why do you want to work here?",
            "What are your strengths and weaknesses?",
            "Where do you see yourself in 5 years?",
            "Why should we hire you?",
        ],
        "mid": [
            "Describe a challenging project you managed.",
            "How do you handle conflict in the workplace?",
            "Tell me about a time you failed and what you learned.",
            "How do you prioritize multiple deadlines?",
            "Describe your leadership experience.",
        ],
        "senior": [
            "How do you build and maintain a high-performing team?",
            "Describe your strategy for organizational transformation.",
            "How do you balance short-term results with long-term vision?",
            "Tell me about a time you made an unpopular decision.",
            "How do you foster innovation within your organization?",
        ],
    },
}

# Salary data (monthly in USD for comparison)
SALARY_DATA: Dict[str, Dict[str, Dict[str, Dict[str, int]]]] = {
    "nigeria": {
        "software_engineer": {"entry": 500, "mid": 1500, "senior": 3500, "lead": 6000},
        "data_scientist": {"entry": 600, "mid": 1800, "senior": 4000, "lead": 7000},
        "nurse": {"entry": 300, "mid": 500, "senior": 800, "lead": 1200},
        "project_manager": {"entry": 400, "mid": 1200, "senior": 2500, "lead": 4500},
        "marketing_manager": {"entry": 350, "mid": 1000, "senior": 2200, "lead": 4000},
    },
    "usa": {
        "software_engineer": {"entry": 7000, "mid": 11000, "senior": 16000, "lead": 22000},
        "data_scientist": {"entry": 7500, "mid": 12000, "senior": 18000, "lead": 25000},
        "nurse": {"entry": 5000, "mid": 7000, "senior": 9000, "lead": 11000},
        "project_manager": {"entry": 6000, "mid": 9000, "senior": 13000, "lead": 18000},
        "marketing_manager": {"entry": 5500, "mid": 8500, "senior": 12000, "lead": 16000},
    },
    "uk": {
        "software_engineer": {"entry": 3500, "mid": 5500, "senior": 8000, "lead": 11000},
        "data_scientist": {"entry": 4000, "mid": 6000, "senior": 9000, "lead": 12000},
        "nurse": {"entry": 2500, "mid": 3500, "senior": 4500, "lead": 5500},
        "project_manager": {"entry": 3500, "mid": 5500, "senior": 8000, "lead": 10000},
        "marketing_manager": {"entry": 3000, "mid": 5000, "senior": 7500, "lead": 9500},
    },
    "india": {
        "software_engineer": {"entry": 600, "mid": 2000, "senior": 4500, "lead": 8000},
        "data_scientist": {"entry": 700, "mid": 2500, "senior": 5500, "lead": 10000},
        "nurse": {"entry": 300, "mid": 500, "senior": 800, "lead": 1200},
        "project_manager": {"entry": 500, "mid": 1800, "senior": 4000, "lead": 7000},
        "marketing_manager": {"entry": 400, "mid": 1500, "senior": 3500, "lead": 6000},
    },
    "kenya": {
        "software_engineer": {"entry": 800, "mid": 2000, "senior": 4000, "lead": 7000},
        "data_scientist": {"entry": 900, "mid": 2500, "senior": 5000, "lead": 9000},
        "nurse": {"entry": 400, "mid": 600, "senior": 900, "lead": 1300},
        "project_manager": {"entry": 600, "mid": 1800, "senior": 3500, "lead": 6000},
        "marketing_manager": {"entry": 500, "mid": 1500, "senior": 3000, "lead": 5500},
    },
}

# Skills assessment questions
SKILLS_QUESTIONS: Dict[str, List[Dict[str, Any]]] = {
    "python": [
        {"q": "What is a Python decorator?", "options": ["A design pattern", "A function that modifies another function", "A CSS style", "A data type"], "correct": 1},
        {"q": "Which Python data structure is immutable?", "options": ["List", "Dictionary", "Set", "Tuple"], "correct": 3},
        {"q": "What does __init__ do in Python?", "options": ["Initializes a class instance", "Deletes an object", "Imports a module", "Handles errors"], "correct": 0},
    ],
    "javascript": [
        {"q": "What is the difference between == and === in JS?", "options": ["No difference", "=== checks value and type", "== is faster", "=== is deprecated"], "correct": 1},
        {"q": "What is a JavaScript Promise?", "options": ["A guarantee", "An object representing async operation", "A loop construct", "A data type"], "correct": 1},
        {"q": "What does 'this' refer to in JavaScript?", "options": ["Global object always", "The current execution context", "The parent function", "Window object"], "correct": 1},
    ],
    "project_management": [
        {"q": "What is the critical path in project management?", "options": ["The shortest path", "The longest sequence of dependent tasks", "The budget path", "The risk path"], "correct": 1},
        {"q": "What does RAID stand for in PM?", "options": ["Risks, Assumptions, Issues, Dependencies", "Risks, Actions, Issues, Decisions", "Resources, Activities, Issues, Deliverables", "Risks, Assumptions, Issues, Decisions"], "correct": 3},
        {"q": "Which methodology uses sprints?", "options": ["Waterfall", "Scrum", "PRINCE2", "Six Sigma"], "correct": 1},
    ],
    "data_analysis": [
        {"q": "What is a p-value?", "options": ["Probability of the null hypothesis being true", "Probability of observing data given null hypothesis is true", "Population value", "Predicted value"], "correct": 1},
        {"q": "Which chart is best for showing trends over time?", "options": ["Pie chart", "Bar chart", "Line chart", "Scatter plot"], "correct": 2},
        {"q": "What does SQL stand for?", "options": ["Simple Query Language", "Structured Query Language", "System Query Language", "Standard Query Language"], "correct": 1},
    ],
}

# Career path templates
CAREER_PATHS: Dict[str, Dict[str, Any]] = {
    "software_engineer": {
        "entry": "Junior Developer",
        "stages": [
            {"role": "Junior Developer", "years": "0-2", "skills": ["Python/Java", "Git", "Basic algorithms"]},
            {"role": "Mid-Level Developer", "years": "2-5", "skills": ["System design", "Databases", "Testing"]},
            {"role": "Senior Developer", "years": "5-8", "skills": ["Architecture", "Mentoring", "Code review"]},
            {"role": "Lead Engineer", "years": "8-12", "skills": ["Team leadership", "Technical strategy", "Cross-functional collaboration"]},
            {"role": "Principal/Staff Engineer", "years": "12+", "skills": ["Org-wide impact", "Innovation", "Industry influence"]},
        ],
    },
    "data_scientist": {
        "entry": "Junior Data Analyst",
        "stages": [
            {"role": "Junior Data Analyst", "years": "0-2", "skills": ["SQL", "Excel", "Basic statistics"]},
            {"role": "Data Analyst", "years": "2-4", "skills": ["Python/R", "Visualization", "A/B testing"]},
            {"role": "Data Scientist", "years": "4-7", "skills": ["ML algorithms", "Feature engineering", "Model deployment"]},
            {"role": "Senior Data Scientist", "years": "7-10", "skills": ["Deep learning", "NLP/CV", "MLOps"]},
            {"role": "Principal/Lead Data Scientist", "years": "10+", "skills": ["Research", "Team building", "Business strategy"]},
        ],
    },
    "nurse": {
        "entry": "Staff Nurse",
        "stages": [
            {"role": "Staff Nurse", "years": "0-2", "skills": ["Patient care", "Documentation", "Medication administration"]},
            {"role": "Senior Nurse", "years": "2-5", "skills": ["Specialized care", "Mentoring", "Care planning"]},
            {"role": "Charge Nurse", "years": "5-8", "skills": ["Unit management", "Scheduling", "Quality assurance"]},
            {"role": "Nurse Manager", "years": "8-12", "skills": ["Budgeting", "Staff development", "Policy implementation"]},
            {"role": "Director of Nursing", "years": "12+", "skills": ["Strategic planning", "Organizational leadership", "Regulatory compliance"]},
        ],
    },
    "project_manager": {
        "entry": "Project Coordinator",
        "stages": [
            {"role": "Project Coordinator", "years": "0-2", "skills": ["Scheduling", "Documentation", "Stakeholder communication"]},
            {"role": "Junior Project Manager", "years": "2-4", "skills": ["Risk management", "Budgeting", "Agile/Scrum"]},
            {"role": "Project Manager", "years": "4-7", "skills": ["Full project lifecycle", "PMP certification", "Team leadership"]},
            {"role": "Senior Project Manager", "years": "7-10", "skills": ["Portfolio management", "Strategic alignment", "Change management"]},
            {"role": "Program Director", "years": "10+", "skills": ["Executive reporting", "Business transformation", "Organizational strategy"]},
        ],
    },
}

# Freelance platform guides
FREELANCE_GUIDES: Dict[str, Dict[str, Any]] = {
    "upwork": {
        "name": "Upwork",
        "description": "The world's largest freelance marketplace. Best for: tech, design, writing, marketing.",
        "steps": [
            "Create a professional profile with a clear headline",
            "Take relevant skill tests to validate expertise",
            "Set competitive starting rates (lower initially to build reviews)",
            "Write customized proposals for each job (not copy-paste)",
            "Deliver exceptional work to earn 5-star reviews",
            "Gradually increase rates as you build reputation",
        ],
        "tips": [
            "Focus on a niche — specialists earn more than generalists",
            "Use the \"Rising Talent\" badge to stand out early",
            "Maintain a 90%+ Job Success Score",
            "Use Connects strategically on high-quality job posts",
        ],
        "average_rates": {"entry": "$15-25/hr", "mid": "$35-75/hr", "expert": "$100-250/hr"},
    },
    "fiverr": {
        "name": "Fiverr",
        "description": "Gig-based marketplace. Best for: creative services, quick tasks, digital products.",
        "steps": [
            "Create compelling gig packages (Basic, Standard, Premium)",
            "Use high-quality images and video for your gig gallery",
            "Write clear, keyword-rich gig descriptions",
            "Start with competitive pricing and offer extras",
            "Deliver on time to maintain Level 1/2/Top Rated status",
            "Continuously optimize gigs based on analytics",
        ],
        "tips": [
            "Offer 3-tier pricing to capture different budgets",
            "Use Fiverr's \"Promote Your Gigs\" feature",
            "Respond to inquiries within 1 hour when possible",
            "Create gig extras for additional revenue",
        ],
        "average_rates": {"entry": "$5-25/gig", "mid": "$50-200/gig", "expert": "$300-1000+/gig"},
    },
    "freelancer": {
        "name": "Freelancer.com",
        "description": "Competitive bidding platform. Best for: programming, data entry, engineering.",
        "steps": [
            "Complete your profile with portfolio samples",
            "Verify your identity and skills",
            "Start with small fixed-price projects",
            "Write detailed, personalized bids",
            "Ask for milestone payments on large projects",
            "Build a portfolio of completed work",
        ],
        "tips": [
            "Use the \"Preferred Freelancer\" program for better visibility",
            "Participate in contests to win projects and build reputation",
            "Set up automated bid templates for efficiency",
            "Maintain a 4.5+ star rating",
        ],
        "average_rates": {"entry": "$10-20/hr", "mid": "$25-60/hr", "expert": "$80-200/hr"},
    },
    "toptal": {
        "name": "Toptal",
        "description": "Elite network for top 3% freelancers. Best for: high-end tech, finance, design.",
        "steps": [
            "Pass the rigorous screening process (language, personality, skills)",
            "Complete a live coding/test project",
            "Maintain a flawless professional profile",
            "Be responsive to client inquiries",
            "Deliver consistently excellent work",
        ],
        "tips": [
            "Prepare thoroughly for the screening — it's challenging",
            "Specialize in high-demand skills (React, Python, ML)",
            "Network with other Toptal freelancers for referrals",
            "Leverage Toptal's global client base for remote work",
        ],
        "average_rates": {"entry": "N/A — all experts", "mid": "$80-150/hr", "expert": "$150-500/hr"},
    },
    "general": {
        "name": "General Freelancing",
        "description": "Cross-platform strategies for freelancing success.",
        "steps": [
            "Identify your marketable skills and niche",
            "Build a portfolio website showcasing your best work",
            "Create profiles on 2-3 platforms (don't spread too thin)",
            "Set clear boundaries and working hours",
            "Use contracts for every project",
            "Continuously upskill to stay competitive",
        ],
        "tips": [
            "Diversify income streams — don't rely on one platform",
            "Build direct client relationships to reduce platform fees",
            "Join freelance communities for support and referrals",
            "Save 25-30% of income for taxes and slow periods",
        ],
        "average_rates": {"entry": "$10-25/hr", "mid": "$30-75/hr", "expert": "$100-500/hr"},
    },
}

# Job market data
JOB_MARKET_DATA: Dict[str, Dict[str, Any]] = {
    "nigeria": {
        "top_sectors": ["Technology", "Agriculture", "Finance", "Healthcare", "Energy"],
        "growth_rate": "2.9% annually",
        "unemployment_rate": "33.3%",
        "top_skills_in_demand": ["Software Development", "Data Analysis", "Digital Marketing", "Project Management", "Sales"],
        "avg_salary_range": "$300 - $3,000/month",
        "remote_opportunities": "Growing — 35% of tech jobs offer remote work",
        "job_boards": ["Jobberman", "NgCareers", "LinkedIn Nigeria", "MyJobMag"],
    },
    "usa": {
        "top_sectors": ["Technology", "Healthcare", "Finance", "E-commerce", "Green Energy"],
        "growth_rate": "1.8% annually",
        "unemployment_rate": "3.7%",
        "top_skills_in_demand": ["AI/ML Engineering", "Cloud Architecture", "Cybersecurity", "Data Science", "DevOps"],
        "avg_salary_range": "$4,000 - $20,000/month",
        "remote_opportunities": "High — 58% of knowledge workers have remote options",
        "job_boards": ["LinkedIn", "Indeed", "Glassdoor", "AngelList", "Hired"],
    },
    "uk": {
        "top_sectors": ["Technology", "Finance", "Healthcare", "Creative Industries", "Consulting"],
        "growth_rate": "1.2% annually",
        "unemployment_rate": "4.2%",
        "top_skills_in_demand": ["Full-Stack Development", "Fintech", "Digital Marketing", "UX/UI Design", "Cloud Engineering"],
        "avg_salary_range": "£2,500 - £12,000/month",
        "remote_opportunities": "High — 45% offer hybrid/remote arrangements",
        "job_boards": ["LinkedIn UK", "Indeed UK", "Reed", "Totaljobs", "CWJobs"],
    },
    "india": {
        "top_sectors": ["IT Services", "E-commerce", "Fintech", "Healthcare", "EdTech"],
        "growth_rate": "6.1% annually",
        "unemployment_rate": "7.1%",
        "top_skills_in_demand": ["Java/Python", "React/Angular", "Cloud (AWS/Azure)", "Data Engineering", "AI/ML"],
        "avg_salary_range": "$500 - $8,000/month",
        "remote_opportunities": "High — India is a global remote work hub",
        "job_boards": ["Naukri", "LinkedIn India", "Indeed India", "AngelList India"],
    },
    "kenya": {
        "top_sectors": ["Technology", "Agriculture", "Financial Services", "Telecommunications", "Tourism"],
        "growth_rate": "5.0% annually",
        "unemployment_rate": "5.7%",
        "top_skills_in_demand": ["Mobile Development", "Fintech", "AgriTech", "Data Science", "Digital Marketing"],
        "avg_salary_range": "$400 - $5,000/month",
        "remote_opportunities": "Growing — Nairobi is Africa's tech hub",
        "job_boards": ["BrighterMonday", "LinkedIn Kenya", "Fuzu", "MyJobMag Kenya"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def build_cv(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a professional CV/resume from user data."""
    template = data.get("template", "professional")
    if template not in CV_TEMPLATES:
        template = "professional"
    
    cv = {
        "status": "success",
        "template": CV_TEMPLATES[template],
        "generated_at": datetime.utcnow().isoformat(),
        "cv_content": {
            "contact": {
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "location": data.get("location", ""),
                "linkedin": data.get("linkedin", ""),
            },
            "summary": data.get("summary", f"{data.get('name', 'Professional')} is a skilled {data.get('title', 'professional')} with {data.get('experience_years', 0)} years of experience."),
            "experience": data.get("experience", []),
            "education": data.get("education", []),
            "skills": data.get("skills", []),
            "certifications": data.get("certifications", []),
        },
        "tips": [
            "Tailor your CV for each job application",
            "Use action verbs and quantify achievements",
            "Keep it to 1-2 pages for entry/mid-level, 2-3 for senior",
            "Include keywords from the job description for ATS optimization",
        ],
    }
    return cv


def get_interview_questions(field: str = "", level: str = "mid") -> Dict[str, Any]:
    """Get interview questions for a specific field and experience level."""
    field = field.lower().replace(" ", "_") if field else "general"
    level = level.lower()
    
    if field not in INTERVIEW_QUESTIONS:
        field = "general"
    if level not in ["entry", "mid", "senior"]:
        level = "mid"
    
    questions = INTERVIEW_QUESTIONS[field][level]
    
    return {
        "status": "success",
        "field": field,
        "level": level,
        "total_available": len(questions),
        "questions": questions,
        "tips": [
            "Research the company thoroughly before the interview",
            "Use the STAR method (Situation, Task, Action, Result) for behavioral questions",
            "Prepare 3-5 stories that showcase different skills",
            "Ask insightful questions about the role and team",
        ],
    }


def assess_skills(topic: str = "", answers: List[int] = None) -> Dict[str, Any]:
    """Assess skills for a given topic from user answers."""
    if answers is None:
        answers = []
    
    topic = topic.lower().replace(" ", "_") if topic else "python"
    
    if topic not in SKILLS_QUESTIONS:
        # Return available topics
        return {
            "status": "available_topics",
            "topics": list(SKILLS_QUESTIONS.keys()),
            "message": f"No assessment available for '{topic}'. Choose from the available topics above.",
        }
    
    questions = SKILLS_QUESTIONS[topic]
    
    if not answers:
        # Return questions for the user to answer
        return {
            "status": "ready",
            "topic": topic,
            "total_questions": len(questions),
            "questions": [{"index": i, "question": q["q"], "options": q["options"]} for i, q in enumerate(questions)],
            "instruction": "Submit your answers as a list of indices (0-based) corresponding to your choices.",
        }
    
    # Grade the answers
    correct_count = 0
    results = []
    for i, (question, user_answer) in enumerate(zip(questions, answers)):
        is_correct = user_answer == question["correct"]
        if is_correct:
            correct_count += 1
        results.append({
            "question_index": i,
            "question": question["q"],
            "your_answer": question["options"][user_answer] if 0 <= user_answer < len(question["options"]) else "Invalid",
            "correct_answer": question["options"][question["correct"]],
            "correct": is_correct,
        })
    
    total = len(questions)
    percentage = (correct_count / total * 100) if total > 0 else 0
    
    # Skill level
    if percentage >= 80:
        level = "Advanced"
        recommendation = "You have strong skills. Focus on advanced topics and real-world projects."
    elif percentage >= 60:
        level = "Intermediate"
        recommendation = "Good foundation. Work on your weak areas and practice more."
    elif percentage >= 40:
        level = "Beginner"
        recommendation = "Keep learning! Focus on fundamentals and hands-on practice."
    else:
        level = "Novice"
        recommendation = "Start with beginner tutorials and build a strong foundation."
    
    return {
        "status": "success",
        "topic": topic,
        "score": f"{correct_count}/{total}",
        "percentage": round(percentage, 1),
        "level": level,
        "recommendation": recommendation,
        "detailed_results": results,
    }


def get_job_market(country: str = "nigeria", field: str = "") -> Dict[str, Any]:
    """Get job market overview for a country and field."""
    country = country.lower().replace(" ", "_")
    
    if country not in JOB_MARKET_DATA:
        return {
            "status": "available_countries",
            "countries": list(JOB_MARKET_DATA.keys()),
            "message": f"No data for '{country}'. Choose from available countries.",
        }
    
    data = JOB_MARKET_DATA[country]
    
    result = {
        "status": "success",
        "country": country,
        **data,
    }
    
    if field:
        field_lower = field.lower().replace(" ", "_")
        # Add field-specific context
        result["field_focus"] = field
        result["field_tips"] = [
            f"Network with professionals in {field}",
            f"Build a portfolio showcasing {field} projects",
            f"Stay updated with {field} industry trends",
            f"Consider certifications relevant to {field}",
        ]
    
    return result


def plan_career(current_role: str = "", goal_role: str = "", timeline_years: int = 5) -> Dict[str, Any]:
    """Generate a career plan from current role to goal role."""
    if not current_role or not goal_role:
        return {
            "status": "error",
            "message": "Both current_role and goal_role are required.",
            "example": {"current_role": "Junior Developer", "goal_role": "Senior Architect", "timeline_years": 7},
        }
    
    # Find the closest career path
    goal_lower = goal_role.lower().replace(" ", "_")
    matched_path = None
    for key, path in CAREER_PATHS.items():
        if key in goal_lower or any(goal_lower in stage["role"].lower().replace(" ", "_") for stage in path["stages"]):
            matched_path = path
            break
    
    if not matched_path:
        matched_path = CAREER_PATHS["software_engineer"]  # Default
    
    # Build a personalized plan
    plan = {
        "status": "success",
        "current_role": current_role,
        "goal_role": goal_role,
        "timeline_years": timeline_years,
        "generated_at": datetime.utcnow().isoformat(),
        "milestones": [],
        "recommended_skills": [],
        "recommended_certifications": [],
        "action_items": [
            f"Set a 6-month goal to advance from {current_role}",
            "Find a mentor who has achieved your goal role",
            "Build a portfolio of projects demonstrating your growth",
            "Network actively in your industry (LinkedIn, conferences, meetups)",
            "Seek feedback regularly and act on it",
        ],
    }
    
    # Generate timeline milestones
    year_step = max(1, timeline_years // len(matched_path["stages"]))
    for i, stage in enumerate(matched_path["stages"]):
        year = min((i + 1) * year_step, timeline_years)
        plan["milestones"].append({
            "year": year,
            "target_role": stage["role"],
            "skills_to_acquire": stage["skills"],
            "action": f"Transition to {stage['role']} by year {year}",
        })
        plan["recommended_skills"].extend(stage["skills"])
    
    plan["recommended_skills"] = list(set(plan["recommended_skills"]))
    plan["recommended_certifications"] = [
        "Industry-recognized certification in your field",
        "Project Management Professional (PMP) — if managing projects",
        "Agile/Scrum certification",
        "Cloud certification (AWS/Azure/GCP)",
    ]
    
    return plan


def get_freelance_guide(skill: str = "", platform: str = "upwork") -> Dict[str, Any]:
    """Get a freelance guide for a skill on a given platform."""
    platform = platform.lower()
    if platform not in FREELANCE_GUIDES:
        platform = "general"
    
    guide = FREELANCE_GUIDES[platform]
    
    return {
        "status": "success",
        "platform": guide["name"],
        "description": guide["description"],
        "skill_focus": skill or "General",
        "steps": guide["steps"],
        "tips": guide["tips"],
        "average_rates": guide["average_rates"],
        "resources": [
            f"Create your {guide['name']} profile",
            "Build a portfolio website",
            "Join relevant freelance communities",
            "Use time-tracking tools (Toggl, Clockify)",
        ],
    }


def generate_coverletter(job_title: str = "", company: str = "", applicant_skills: List[str] = None) -> Dict[str, Any]:
    """Generate a tailored cover letter for a job application."""
    if applicant_skills is None:
        applicant_skills = []
    
    if not job_title or not company:
        return {
            "status": "error",
            "message": "job_title and company are required.",
        }
    
    skills_text = ", ".join(applicant_skills) if applicant_skills else "my relevant skills"
    
    cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. With my background and expertise in {skills_text}, I am confident that I can make a meaningful contribution to your team.

Throughout my career, I have developed a strong foundation in the skills required for this role. I am particularly drawn to {company} because of its reputation for innovation and excellence. I am eager to bring my unique perspective and dedication to your organization.

I would welcome the opportunity to discuss how my background, skills, and enthusiasm align with the needs of your team. Thank you for considering my application. I look forward to the possibility of contributing to {company}'s continued success.

Sincerely,
[Your Name]"""
    
    return {
        "status": "success",
        "job_title": job_title,
        "company": company,
        "cover_letter": cover_letter,
        "tips": [
            "Customize the greeting with the hiring manager's name if known",
            "Add a specific achievement or project in paragraph 2",
            "Research the company and mention a specific initiative you admire",
            "Keep it to one page — 250-400 words",
            "Proofread carefully before sending",
        ],
    }


def get_salary_guide(country: str = "nigeria", role: str = "", experience_years: int = 0) -> Dict[str, Any]:
    """Get a salary guide for a role in a given country."""
    country = country.lower().replace(" ", "_")
    role = role.lower().replace(" ", "_") if role else "software_engineer"
    
    if country not in SALARY_DATA:
        return {
            "status": "available_countries",
            "countries": list(SALARY_DATA.keys()),
            "message": f"No salary data for '{country}'. Choose from available countries.",
        }
    
    country_data = SALARY_DATA[country]
    
    if role not in country_data:
        available_roles = list(country_data.keys())
        return {
            "status": "available_roles",
            "country": country,
            "available_roles": available_roles,
            "message": f"No data for '{role}'. Choose from available roles.",
        }
    
    role_data = country_data[role]
    
    # Determine level based on experience
    if experience_years < 2:
        level = "entry"
        level_name = "Entry Level (0-2 years)"
    elif experience_years < 5:
        level = "mid"
        level_name = "Mid Level (2-5 years)"
    elif experience_years < 10:
        level = "senior"
        level_name = "Senior Level (5-10 years)"
    else:
        level = "lead"
        level_name = "Lead/Principal (10+ years)"
    
    salary = role_data.get(level, role_data["mid"])
    
    return {
        "status": "success",
        "country": country,
        "role": role,
        "experience_years": experience_years,
        "level": level_name,
        "monthly_salary_usd": salary,
        "annual_salary_usd": salary * 12,
        "salary_range": {
            "entry": role_data["entry"],
            "mid": role_data["mid"],
            "senior": role_data["senior"],
            "lead": role_data["lead"],
        },
        "negotiation_tips": [
            "Research market rates using Glassdoor, PayScale, and LinkedIn Salary",
            "Highlight quantifiable achievements during negotiations",
            "Consider total compensation (benefits, bonuses, equity, remote flexibility)",
            "Practice your negotiation pitch beforehand",
            "Don't disclose your current salary — focus on market value",
        ],
    }

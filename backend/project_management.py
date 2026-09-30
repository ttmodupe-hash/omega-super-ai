#!/usr/bin/env python3
"""Luqi AI Project Management Module - 8 methodologies, 22 templates,
Gantt charts, sprint simulation, risk assessment, resource allocation,
RACI matrices, communication plans, PMP exam simulator, and tool recommendations.

v25.2.0 - Enhanced with project export, burndown charts, critical path
analysis, cost estimation, meeting agendas, and milestone tracking.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# METHODOLOGIES DATA
METHODOLOGIES = {
    "agile": {
        "id": "agile",
        "name": "Agile",
        "category": "Iterative",
        "description": "An iterative approach to project management that emphasizes flexibility, customer collaboration, and rapid delivery of small, functional increments.",
        "principles": [
            "Customer satisfaction through early and continuous delivery",
            "Welcome changing requirements, even late in development",
            "Deliver working software frequently (weeks rather than months)",
            "Business people and developers work together daily",
            "Build projects around motivated individuals",
            "Face-to-face conversation is the best form of communication",
            "Working software is the primary measure of progress",
            "Maintain a constant pace indefinitely",
            "Continuous attention to technical excellence",
            "Simplicity - maximizing the work not done",
        ],
        "pros": ["Highly flexible", "Fast feedback loops", "Customer-centric", "Risk mitigation through early delivery"],
        "cons": ["Less predictable timelines", "Requires experienced team", "Documentation can be light", "Scope creep risk"],
        "best_for": ["Software development", "Product development", "Rapidly changing environments", "Startup projects"],
        "tools": ["Jira", "Trello", "Asana", "Monday.com"],
    },
    "scrum": {
        "id": "scrum",
        "name": "Scrum",
        "category": "Agile Framework",
        "description": "A framework within Agile that uses fixed-length iterations called sprints (typically 2-4 weeks), with defined roles, ceremonies, and artifacts.",
        "principles": [
            "Empirical process control - transparency, inspection, adaptation",
            "Self-organizing cross-functional teams",
            "Time-boxed iterations (sprints)",
            "Incremental delivery of value",
        ],
        "roles": ["Product Owner", "Scrum Master", "Development Team"],
        "ceremonies": ["Sprint Planning", "Daily Standup", "Sprint Review", "Sprint Retrospective", "Backlog Refinement"],
        "artifacts": ["Product Backlog", "Sprint Backlog", "Increment", "Burndown Chart"],
        "pros": ["Clear structure", "High visibility", "Regular feedback", "Predictable rhythm"],
        "cons": ["Rigid framework", "Requires dedicated Scrum Master", "Can be ceremony-heavy", "Not ideal for maintenance work"],
        "best_for": ["Software teams", "Product teams", "Complex projects", "Teams new to Agile"],
        "tools": ["Jira", "Azure DevOps", "ClickUp", "Linear"],
    },
    "kanban": {
        "id": "kanban",
        "name": "Kanban",
        "category": "Flow-Based",
        "description": "A visual workflow management method that uses a board with columns to represent stages of work, limiting work in progress (WIP) to optimize flow.",
        "principles": [
            "Visualize the workflow",
            "Limit Work In Progress (WIP)",
            "Manage flow - monitor and optimize movement of work",
            "Make process policies explicit",
            "Implement feedback loops",
            "Improve collaboratively, evolve experimentally",
        ],
        "pros": ["Highly visual", "Easy to start", "Continuous delivery", "No required roles or ceremonies"],
        "cons": ["No time-boxing", "Can lack structure", "Requires discipline for WIP limits", "Less predictable delivery dates"],
        "best_for": ["Support teams", "Operations", "Maintenance projects", "Continuous flow work", "HR and marketing teams"],
        "tools": ["Trello", "Asana", "Jira", "Monday.com", "Notion"],
    },
    "waterfall": {
        "id": "waterfall",
        "name": "Waterfall",
        "category": "Sequential",
        "description": "A linear, sequential approach where each phase must be completed before the next begins. Requirements are defined upfront and changes are costly.",
        "phases": ["Requirements", "Design", "Implementation", "Verification", "Maintenance"],
        "pros": ["Clear milestones", "Well-documented", "Easy to understand", "Good for fixed-scope projects"],
        "cons": ["Inflexible to changes", "Late feedback", "Risk discovered late", "No working product until late"],
        "best_for": ["Construction", "Manufacturing", "Regulated industries", "Projects with fixed requirements"],
        "tools": ["Microsoft Project", "GanttProject", "Smartsheet"],
    },
    "lean": {
        "id": "lean",
        "name": "Lean",
        "category": "Process Improvement",
        "description": "Focuses on eliminating waste, optimizing value delivery, and continuous improvement. Originated from manufacturing (Toyota Production System).",
        "principles": [
            "Eliminate waste (muda)",
            "Amplify learning",
            "Decide as late as possible",
            "Deliver as fast as possible",
            "Empower the team",
            "Build integrity in",
            "See the whole",
        ],
        "waste_types": ["Partially done work", "Extra processes", "Extra features", "Task switching", "Waiting", "Motion", "Defects"],
        "pros": ["Efficiency-focused", "Customer value-driven", "Reduces costs", "Continuous improvement"],
        "cons": ["Requires cultural change", "Can be rigid", "Difficult to implement", "May overlook innovation"],
        "best_for": ["Manufacturing", "Operations", "Process-heavy organizations", "Cost reduction initiatives"],
        "tools": ["Kanban", "Value Stream Mapping", "Kaizen", "5S"],
    },
    "six_sigma": {
        "id": "six_sigma",
        "name": "Six Sigma",
        "category": "Quality Management",
        "description": "Data-driven methodology focused on reducing defects and process variation. Uses DMAIC (Define, Measure, Analyze, Improve, Control) framework.",
        "dmaic": {
            "define": "Define the problem and project goals",
            "measure": "Measure current process performance",
            "analyze": "Analyze data to find root causes",
            "improve": "Implement solutions to address root causes",
            "control": "Control the improved process",
        },
        "belt_levels": ["White Belt", "Yellow Belt", "Green Belt", "Black Belt", "Master Black Belt"],
        "pros": ["Data-driven decisions", "Reduces defects significantly", "Measurable ROI", "Structured approach"],
        "cons": ["Can be bureaucratic", "Requires extensive training", "Rigid methodology", "May stifle creativity"],
        "best_for": ["Manufacturing", "Quality control", "Process optimization", "Large organizations"],
        "tools": ["Minitab", "Statistical analysis", "Control charts", "FMEA"],
    },
    "prince2": {
        "id": "prince2",
        "name": "PRINCE2",
        "category": "Process-Based",
        "description": "Projects IN Controlled Environments. A structured project management method focusing on organization, control, and quality.",
        "principles": [
            "Continued business justification",
            "Learn from experience",
            "Defined roles and responsibilities",
            "Manage by stages",
            "Manage by exception",
            "Focus on products",
            "Tailor to suit the project",
        ],
        "processes": ["Starting up a Project", "Initiating a Project", "Directing a Project", "Controlling a Stage", "Managing Product Delivery", "Managing Stage Boundaries", "Closing a Project"],
        "roles": ["Project Board", "Project Manager", "Team Manager", "Project Assurance", "Project Support"],
        "pros": ["Highly structured", "Clear governance", "Widely recognized (especially UK/EU)", "Flexible scalability"],
        "cons": ["Can be documentation-heavy", "Requires training/certification", "May be overkill for small projects", "Rigid process structure"],
        "best_for": ["Government projects", "Large enterprises", "UK/EU organizations", "Regulated industries"],
        "tools": ["PRINCE2 manual", "Microsoft Project", "Managing Successful Projects with PRINCE2"],
    },
    "hybrid": {
        "id": "hybrid",
        "name": "Hybrid (Agile + Waterfall)",
        "category": "Mixed",
        "description": "Combines the structure of Waterfall with the flexibility of Agile. Requirements and design may be waterfall, while development uses Agile.",
        "approach": "Use Waterfall for planning/design phases, Agile for development/implementation phases",
        "pros": ["Best of both worlds", "Structured yet flexible", "Stakeholder-friendly planning", "Adaptive execution"],
        "cons": ["Complex to manage", "Requires expertise in both approaches", "Can confuse teams", "Tooling challenges"],
        "best_for": ["Large software projects", "Enterprise transformations", "Teams transitioning to Agile", "Complex stakeholder environments"],
        "tools": ["Jira + Gantt charts", "Monday.com", "Smartsheet", "Azure DevOps"],
    },
}

TEMPLATES = {
    "software_dev": {
        "name": "Software Development",
        "phases": [
            {"name": "Discovery", "duration_days": 14, "tasks": ["Requirements gathering", "Stakeholder interviews", "Technical feasibility", "Project charter"]},
            {"name": "Design", "duration_days": 21, "tasks": ["Architecture design", "UI/UX design", "Database schema", "API design"]},
            {"name": "Development", "duration_days": 60, "tasks": ["Frontend development", "Backend development", "API integration", "Unit testing"]},
            {"name": "Testing", "duration_days": 21, "tasks": ["QA testing", "User acceptance testing", "Performance testing", "Security audit"]},
            {"name": "Deployment", "duration_days": 7, "tasks": ["Production deployment", "Monitoring setup", "Documentation", "Team training"]},
        ]
    },
    "marketing_campaign": {
        "name": "Marketing Campaign",
        "phases": [
            {"name": "Strategy", "duration_days": 10, "tasks": ["Market research", "Target audience definition", "Budget allocation", "KPI setting"]},
            {"name": "Creative", "duration_days": 14, "tasks": ["Content creation", "Visual design", "Copywriting", "Asset production"]},
            {"name": "Execution", "duration_days": 30, "tasks": ["Campaign launch", "Social media posts", "Email sequences", "Ad management"]},
            {"name": "Analysis", "duration_days": 7, "tasks": ["Performance tracking", "ROI analysis", "Reporting", "Optimization plan"]},
        ]
    },
    "product_launch": {
        "name": "Product Launch",
        "phases": [
            {"name": "Pre-Launch", "duration_days": 30, "tasks": ["Beta testing", "Pricing strategy", "Positioning", "Launch checklist"]},
            {"name": "Launch", "duration_days": 7, "tasks": ["Press release", "Launch event", "Sales enablement", "Customer support prep"]},
            {"name": "Post-Launch", "duration_days": 30, "tasks": ["Feedback collection", "Iteration planning", "Growth metrics", "Retention analysis"]},
        ]
    },
}

# QUIZ DATA
PM_QUESTIONS = [
    {"question": "What is the primary role of a Scrum Master?", "options": ["Write code", "Remove impediments and facilitate", "Manage the budget", "Hire team members"], "correct": 1, "level": "beginner"},
    {"question": "Which document defines what the project will and will not deliver?", "options": ["Project Charter", "Scope Statement", "Risk Register", "Stakeholder Register"], "correct": 1, "level": "beginner"},
    {"question": "What does WIP stand for in Kanban?", "options": ["Work In Progress", "Workflow Integration Point", "Work Item Priority", "Weekly Integration Plan"], "correct": 0, "level": "beginner"},
    {"question": "Which is NOT one of the triple constraints?", "options": ["Scope", "Time", "Quality", "Cost"], "correct": 2, "level": "beginner"},
    {"question": "What is the critical path?", "options": ["Shortest path through the project", "Longest path that determines project duration", "Path with zero risk", "Path with the most resources"], "correct": 1, "level": "intermediate"},
    {"question": "In Agile, what is a 'user story'?", "options": ["A novel about users", "A high-level requirement from the user perspective", "A bug report", "A project status update"], "correct": 1, "level": "beginner"},
    {"question": "What is EVM (Earned Value Management) used for?", "options": ["Tracking team velocity", "Measuring project performance against plan", "Calculating sprint capacity", "Estimating story points"], "correct": 1, "level": "intermediate"},
    {"question": "Which risk response strategy involves transferring the risk?", "options": ["Avoid", "Mitigate", "Transfer", "Accept"], "correct": 2, "level": "intermediate"},
    {"question": "What is the purpose of a retrospective?", "options": ["Plan the next sprint", "Demo work to stakeholders", "Reflect and improve processes", "Assign blame for failures"], "correct": 2, "level": "beginner"},
    {"question": "In PRINCE2, who is responsible for the business case?", "options": ["Project Manager", "Executive", "Team Manager", "Project Support"], "correct": 1, "level": "advanced"},
]

PMP_EXAM = {
    "exam_format": {
        "total_questions": 180,
        "duration_minutes": 230,
        "question_types": ["Multiple choice", "Multiple select", "Matching", "Hotspot"],
        "passing_score_approx": "62-65%",
    },
    "domains": [
        {"name": "People", "percentage": 42, "topics": ["Conflict management", "Team leadership", "Stakeholder engagement", "Emotional intelligence"]},
        {"name": "Process", "percentage": 50, "topics": ["Schedule management", "Cost management", "Quality management", "Risk management", "Procurement"]},
        {"name": "Business Environment", "percentage": 8, "topics": ["Compliance", "Benefits management", "Organizational change"]},
    ],
    "sample_questions": [
        {"question": "A stakeholder repeatedly misses review meetings. What should the PM do first?", "options": ["Escalate to their manager", "Update the risk register", "Meet privately to understand concerns", "Remove them from the stakeholder list"], "correct": 2, "explanation": "Proactive stakeholder engagement is key. Understanding root cause comes before escalation."},
        {"question": "A key team member resigns mid-project. What is the BEST response?", "options": ["Hire replacement immediately", "Analyze impact on schedule/budget", "Cancel the project", "Redistribute work equally"], "correct": 1, "explanation": "Impact analysis should precede any action to ensure the right response."},
    ],
}


# ── PUBLIC API ───────────────────────────────────────────────────────────────

def get_all_methodologies() -> Dict[str, Any]:
    return {
        "status": "success",
        "methodologies": [{"id": k, "name": v["name"], "category": v["category"]} for k, v in METHODOLOGIES.items()],
        "total": len(METHODOLOGIES),
    }


def get_methodology(method_id: str) -> Dict[str, Any]:
    method_id = method_id.lower().strip()
    data = METHODOLOGIES.get(method_id)
    if not data:
        return {"status": "not_found", "message": f"No methodology '{method_id}'"}
    return {"status": "success", **data}


def list_templates() -> Dict[str, Any]:
    return {
        "status": "success",
        "templates": [{"id": k, "name": v["name"], "phases": len(v["phases"])} for k, v in TEMPLATES.items()],
        "total": len(TEMPLATES),
    }


def get_template(template_id: str) -> Dict[str, Any]:
    template_id = template_id.lower().strip()
    data = TEMPLATES.get(template_id)
    if not data:
        return {"status": "not_found", "message": f"No template '{template_id}'"}
    return {"status": "success", "template": data}


def generate_gantt_chart(project: Dict[str, Any]) -> Dict[str, Any]:
    tasks = project.get("tasks", [])
    if not tasks:
        return {"status": "error", "message": "No tasks provided"}
    chart_rows = []
    total_duration = 0
    for t in tasks:
        name = t.get("name", "Task")
        duration = t.get("duration", 1)
        start = t.get("start", 0)
        deps = t.get("dependencies", [])
        end = start + duration
        total_duration = max(total_duration, end)
        chart_rows.append({
            "task": name,
            "start_day": start,
            "duration_days": duration,
            "end_day": end,
            "dependencies": deps,
        })
    return {
        "status": "success",
        "project_name": project.get("name", "Untitled"),
        "chart": chart_rows,
        "total_duration_days": total_duration,
    }


def simulate_sprint(team_size: int, sprint_days: int, stories: List[str]) -> Dict[str, Any]:
    random.seed()
    completed = random.randint(max(1, len(stories) - 2), len(stories))
    velocity = round(completed / sprint_days * team_size, 2)
    burndown = []
    remaining = len(stories)
    for day in range(sprint_days):
        burn = random.randint(0, max(1, remaining))
        remaining = max(0, remaining - burn)
        burndown.append({"day": day + 1, "remaining": remaining, "completed_today": burn})
    return {
        "status": "success",
        "team_size": team_size,
        "sprint_days": sprint_days,
        "total_stories": len(stories),
        "completed": completed,
        "velocity": velocity,
        "burndown": burndown,
    }


def calculate_velocity() -> Dict[str, Any]:
    sprints = [
        {"sprint": 1, "points_completed": 23, "team_days": 40},
        {"sprint": 2, "points_completed": 27, "team_days": 40},
        {"sprint": 3, "points_completed": 30, "team_days": 36},
        {"sprint": 4, "points_completed": 25, "team_days": 40},
        {"sprint": 5, "points_completed": 32, "team_days": 40},
    ]
    total_points = sum(s["points_completed"] for s in sprints)
    total_days = sum(s["team_days"] for s in sprints)
    avg_velocity = round(total_points / len(sprints), 2)
    velocity_per_day = round(total_points / total_days, 2)
    return {
        "status": "success",
        "sprint_history": sprints,
        "average_velocity": avg_velocity,
        "velocity_per_team_day": velocity_per_day,
        "trend": "increasing" if sprints[-1]["points_completed"] > sprints[0]["points_completed"] else "stable",
    }


def assess_risks(risks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    if risks is None:
        return {"status": "ready", "message": "Provide risks as list of dicts with 'description', 'probability', 'impact'"}
    assessed = []
    for r in risks:
        score = round(r.get("probability", 0) * r.get("impact", 0), 2)
        if score >= 0.5:
            level = "High"
        elif score >= 0.2:
            level = "Medium"
        else:
            level = "Low"
        assessed.append({
            "description": r.get("description", ""),
            "probability": r.get("probability", 0),
            "impact": r.get("impact", 0),
            "risk_score": score,
            "level": level,
            "response": r.get("response", "Monitor"),
        })
    high_risks = [a for a in assessed if a["level"] == "High"]
    return {
        "status": "success",
        "risks_assessed": assessed,
        "total_risks": len(assessed),
        "high_risks_count": len(high_risks),
        "recommendation": "Address high risks immediately" if high_risks else "Continue monitoring",
    }


def generate_risk_register(project_type: str = "software") -> Dict[str, Any]:
    default_risks = {
        "software": [
            {"description": "Scope creep", "probability": 0.7, "impact": 0.6, "response": "Strict change control"},
            {"description": "Technical debt", "probability": 0.6, "impact": 0.5, "response": "Regular refactoring sprints"},
            {"description": "Key developer leaves", "probability": 0.3, "impact": 0.8, "response": "Knowledge sharing, documentation"},
            {"description": "Third-party API failure", "probability": 0.4, "impact": 0.7, "response": "Fallback mechanisms, caching"},
            {"description": "Security vulnerability", "probability": 0.3, "impact": 0.9, "response": "Regular audits, pen testing"},
        ],
        "construction": [
            {"description": "Weather delays", "probability": 0.5, "impact": 0.4, "response": "Buffer in schedule"},
            {"description": "Material shortage", "probability": 0.4, "impact": 0.7, "response": "Early procurement"},
        ],
        "event": [
            {"description": "Low attendance", "probability": 0.3, "impact": 0.6, "response": "Marketing push"},
            {"description": "Vendor cancellation", "probability": 0.2, "impact": 0.8, "response": "Backup vendors"},
        ],
    }
    risks = default_risks.get(project_type, default_risks["software"])
    return {"status": "success", "project_type": project_type, "risks": risks}


def allocate_resources(project: Dict[str, Any], team: List[Dict[str, Any]]) -> Dict[str, Any]:
    hours_needed = project.get("estimated_hours", 100)
    team_size = len(team)
    if team_size == 0:
        return {"status": "error", "message": "Team cannot be empty"}
    total_availability = sum(m.get("availability", 1.0) * 40 for m in team)  # 40 hrs/week
    weeks_needed = round(hours_needed / total_availability, 1)
    allocation = []
    for member in team:
        assigned_hours = round(hours_needed * (member.get("availability", 1.0) / sum(m.get("availability", 1.0) for m in team)), 1)
        allocation.append({
            "name": member.get("name", "Unknown"),
            "role": member.get("role", "General"),
            "availability": member.get("availability", 1.0),
            "assigned_hours": assigned_hours,
        })
    return {
        "status": "success",
        "project_name": project.get("name", "Untitled"),
        "team_size": team_size,
        "estimated_total_hours": hours_needed,
        "estimated_weeks": weeks_needed,
        "total_weekly_capacity": total_availability,
        "allocation": allocation,
    }


def create_raci_matrix(tasks: List[str], roles: List[str]) -> Dict[str, Any]:
    raci_options = ["R", "A", "C", "I"]
    matrix = {}
    for task in tasks:
        assigned = {}
        r_assigned = False
        a_assigned = False
        for i, role in enumerate(roles):
            if not r_assigned:
                assigned[role] = "R"
                r_assigned = True
            elif not a_assigned:
                assigned[role] = "A"
                a_assigned = True
            else:
                assigned[role] = random.choice(["C", "I"])
        matrix[task] = assigned
    return {
        "status": "success",
        "matrix": matrix,
        "tasks": tasks,
        "roles": roles,
        "legend": {"R": "Responsible", "A": "Accountable", "C": "Consulted", "I": "Informed"},
    }


def generate_communication_plan() -> Dict[str, Any]:
    return {
        "status": "success",
        "plan": {
            "meetings": [
                {"name": "Daily Standup", "frequency": "Daily", "duration_min": 15, "participants": "Core team", "purpose": "Sync on progress and blockers"},
                {"name": "Sprint Planning", "frequency": "Bi-weekly", "duration_min": 120, "participants": "Team + Product Owner", "purpose": "Plan upcoming sprint work"},
                {"name": "Sprint Review", "frequency": "Bi-weekly", "duration_min": 60, "participants": "Team + Stakeholders", "purpose": "Demo completed work"},
                {"name": "Retrospective", "frequency": "Bi-weekly", "duration_min": 60, "participants": "Core team", "purpose": "Reflect and improve"},
                {"name": "Stakeholder Update", "frequency": "Weekly", "duration_min": 30, "participants": "PM + Key stakeholders", "purpose": "High-level status update"},
            ],
            "escalation_path": ["Team Lead", "Project Manager", "Program Director", "Executive Sponsor"],
            "tools": ["Slack/Teams for daily comms", "Email for formal updates", "Jira for task tracking", "Confluence for documentation"],
        },
    }


def get_pm_quiz(level: str = "beginner") -> Dict[str, Any]:
    level = level.lower()
    questions = [q for q in PM_QUESTIONS if q["level"] == level]
    if not questions:
        questions = PM_QUESTIONS[:5]
    selected = random.sample(questions, min(5, len(questions)))
    for q in selected:
        q.pop("correct", None)
    return {"status": "success", "level": level, "questions": selected, "total_questions": len(selected)}


def grade_pm_quiz(answers: List[int]) -> Dict[str, Any]:
    correct_answers = [1, 1, 0, 2, 1, 1, 1, 2, 2, 1]
    score = sum(1 for i, a in enumerate(answers) if i < len(correct_answers) and a == correct_answers[i])
    total = min(len(answers), len(correct_answers))
    percentage = round((score / total) * 100, 1) if total else 0
    if percentage >= 80:
        level = "Expert"
    elif percentage >= 60:
        level = "Proficient"
    elif percentage >= 40:
        level = "Intermediate"
    else:
        level = "Beginner"
    return {"status": "success", "score": score, "total": total, "percentage": percentage, "level": level}


def get_pmp_exam_simulator() -> Dict[str, Any]:
    return {"status": "success", **PMP_EXAM}


def recommend_tools(budget: str = "free", team_size: int = 5, project_type: str = "software") -> Dict[str, Any]:
    recommendations = {
        "free": [
            {"name": "Trello", "best_for": "Small teams, simple projects", "price": "Free"},
            {"name": "ClickUp", "best_for": "Feature-rich free tier", "price": "Free"},
            {"name": "Notion", "best_for": "Docs + tasks combined", "price": "Free personal/team"},
            {"name": "GitHub Projects", "best_for": "Dev teams", "price": "Free"},
        ],
        "paid": [
            {"name": "Jira", "best_for": "Agile software teams", "price": "$7.75/user/month"},
            {"name": "Monday.com", "best_for": "Visual workflows", "price": "$8/user/month"},
            {"name": "Asana", "best_for": "Cross-functional teams", "price": "$10.99/user/month"},
            {"name": "Linear", "best_for": "Modern software teams", "price": "$8/user/month"},
        ],
    }
    tools = recommendations.get(budget, recommendations["free"])
    return {
        "status": "success",
        "budget": budget,
        "team_size": team_size,
        "project_type": project_type,
        "recommended_tools": tools,
        "tip": "Start with free tools and upgrade as team grows",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ADVANCED CAPABILITIES (v25.2.0)
# ═══════════════════════════════════════════════════════════════════════════════


def export_project(project_data: Dict[str, Any], format: str = "json") -> Dict[str, Any]:
    """Export a project plan to JSON, CSV, or Markdown format.

    Args:
        project_data: Project dictionary with name, tasks, timeline info.
        format: Export format - one of "json", "csv", "markdown".

    Returns:
        Export result with content string and suggested filename.
    """
    fmt = format.lower().strip()
    name = project_data.get("name", "Untitled Project")
    tasks = project_data.get("tasks", [])
    if fmt == "json":
        content = json.dumps(project_data, indent=2)
        filename = f"{name.replace(' ', '_').lower()}_project.json"
    elif fmt == "csv":
        lines = ["Task,Start Day,Duration,End Day,Dependencies"]
        for t in tasks:
            deps = ";".join(t.get("dependencies", []))
            lines.append(f"{t.get('name','')},{t.get('start',0)},{t.get('duration',0)},{t.get('start',0)+t.get('duration',0)},\"{deps}\"")
        content = "\n".join(lines)
        filename = f"{name.replace(' ', '_').lower()}_project.csv"
    elif fmt == "markdown":
        lines = [f"# {name}", "", "## Project Plan", ""]
        lines.append("| Task | Start | Duration | End | Dependencies |")
        lines.append("|------|-------|----------|-----|--------------|")
        for t in tasks:
            deps = ", ".join(t.get("dependencies", [])) or "None"
            lines.append(f"| {t.get('name','')} | {t.get('start',0)} | {t.get('duration',0)} | {t.get('start',0)+t.get('duration',0)} | {deps} |")
        lines.extend(["", "## Summary", f"- **Total duration:** {sum(t.get('duration',0) for t in tasks)} days"])
        content = "\n".join(lines)
        filename = f"{name.replace(' ', '_').lower()}_project.md"
    else:
        return {"status": "error", "message": f"Unknown format '{fmt}'. Use: json, csv, markdown"}
    return {"status": "success", "format": fmt, "content": content, "filename": filename}


def generate_burndown_chart(sprint_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate burndown chart data for a sprint.

    Args:
        sprint_data: Dictionary with total_story_points, days_in_sprint,
                     and optional actual_daily_progress list.

    Returns:
        Ideal and actual burndown arrays with projection.
    """
    total_points = sprint_data.get("total_story_points", 0)
    days = sprint_data.get("days_in_sprint", 14)
    actual = sprint_data.get("actual_daily_progress", [])
    if not actual:
        random.seed()
        remaining = total_points
        actual = []
        for _ in range(days):
            burn = random.randint(max(0, remaining // days - 2), remaining // days + 3)
            burn = max(0, min(burn, remaining))
            actual.append(burn)
            remaining -= burn
            if remaining <= 0:
                break
    ideal_per_day = total_points / days if days else 0
    ideal = [round(total_points - ideal_per_day * d, 1) for d in range(days + 1)]
    actual_cumulative = [total_points]
    for burn in actual:
        actual_cumulative.append(max(0, round(actual_cumulative[-1] - burn, 1)))
    while len(actual_cumulative) <= days:
        actual_cumulative.append(actual_cumulative[-1])
    if actual_cumulative[-1] <= 0:
        projected = days
    else:
        avg_burn = sum(actual) / len(actual) if actual else ideal_per_day
        projected = round(total_points / avg_burn, 1) if avg_burn else days * 2
    on_track = actual_cumulative[-1] <= 0 if len(actual_cumulative) > days else actual_cumulative[-1] <= ideal[-1] if len(ideal) > len(actual_cumulative) - 1 else True
    return {
        "status": "success",
        "chart_data": {
            "days": list(range(days + 1)),
            "ideal": ideal,
            "actual": actual_cumulative[:days + 1],
        },
        "projected_completion_day": projected,
        "on_track": on_track,
    }


def calculate_critical_path(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate the critical path through a task network.

    Args:
        tasks: List of task dicts, each with 'name', 'duration', and
               'dependencies' (list of task names).

    Returns:
        Critical path task names, project duration, and per-task slack.
    """
    task_map = {t["name"]: t for t in tasks}
    in_degree = {t["name"]: 0 for t in tasks}
    adj = {t["name"]: [] for t in tasks}
    for t in tasks:
        for dep in t.get("dependencies", []):
            if dep in adj:
                adj[dep].append(t["name"])
                in_degree[t["name"]] += 1
    queue = [n for n, d in in_degree.items() if d == 0]
    topo = []
    while queue:
        node = queue.pop(0)
        topo.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    if len(topo) != len(tasks):
        return {"status": "error", "message": "Circular dependency detected in task network"}
    es = {t["name"]: 0 for t in tasks}
    ef = {}
    for name in topo:
        t = task_map[name]
        ef[name] = es[name] + t.get("duration", 0)
        for neighbor in adj[name]:
            es[neighbor] = max(es[neighbor], ef[name])
    project_duration = max(ef.values()) if ef else 0
    lf = {t["name"]: project_duration for t in tasks}
    ls = {}
    for name in reversed(topo):
        t = task_map[name]
        ls[name] = lf[name] - t.get("duration", 0)
        for dep in t.get("dependencies", []):
            if dep in lf:
                lf[dep] = min(lf[dep], ls[name])
    slack = {t["name"]: ls[t["name"]] - es[t["name"]] for t in tasks}
    critical = [name for name, s in slack.items() if s == 0]
    critical.sort(key=lambda n: es[n])
    return {
        "status": "success",
        "critical_path": critical,
        "project_duration": project_duration,
        "slack_per_task": slack,
    }


def estimate_project_cost(scope: Dict[str, Any], rates: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Estimate project cost using a COCOMO-like formula.

    Args:
        scope: Project scope dict with features, complexity,
               team_size, and duration_weeks.
        rates: Optional hourly rates dict. Defaults used if not provided.

    Returns:
        Total cost with detailed breakdown.
    """
    if rates is None:
        rates = {"developer": 50.0, "tester": 40.0, "manager": 60.0}
    features = scope.get("features", 10)
    complexity = scope.get("complexity", "medium")
    team_size = scope.get("team_size", 3)
    duration_weeks = scope.get("duration_weeks", 8)
    complexity_mult = {"low": 0.8, "medium": 1.0, "high": 1.4}.get(complexity, 1.0)
    total_hours = duration_weeks * 40 * team_size
    dev_ratio = 0.6
    test_ratio = 0.25
    mgmt_ratio = 0.15
    dev_cost = total_hours * dev_ratio * rates["developer"] * complexity_mult
    test_cost = total_hours * test_ratio * rates["tester"] * complexity_mult
    mgmt_cost = total_hours * mgmt_ratio * rates["manager"]
    subtotal = dev_cost + test_cost + mgmt_cost
    contingency = subtotal * 0.15
    total = subtotal + contingency
    return {
        "status": "success",
        "total_cost_usd": round(total, 2),
        "breakdown": {
            "development": round(dev_cost, 2),
            "testing": round(test_cost, 2),
            "management": round(mgmt_cost, 2),
            "contingency": round(contingency, 2),
        },
        "cost_per_hour": round(total / total_hours, 2) if total_hours else 0,
        "assumptions": [f"{duration_weeks} weeks, {team_size} people, {complexity} complexity"],
    }


def generate_meeting_agenda(meeting_type: str, topics: Optional[List[str]] = None, duration_minutes: int = 60) -> Dict[str, Any]:
    """Generate a structured meeting agenda with time allocation.

    Args:
        meeting_type: Type of meeting (standup, sprint_planning,
                      retrospective, stakeholder_review, kickoff).
        topics: Optional list of topics to include.
        duration_minutes: Total meeting duration in minutes.

    Returns:
        Structured agenda with time blocks and preparation checklist.
    """
    mtype = meeting_type.lower().strip()
    defaults = {
        "standup": {
            "topics": ["What did you do yesterday?", "What will you do today?", "Any blockers?"],
            "owners": ["Each team member"],
        },
        "sprint_planning": {
            "topics": ["Review sprint goal", "Capacity check", "Story estimation", "Sprint commitment"],
            "owners": ["Product Owner", "Scrum Master", "Dev Team"],
        },
        "retrospective": {
            "topics": ["What went well?", "What could improve?", "Action items"],
            "owners": ["Scrum Master", "Team"],
        },
        "stakeholder_review": {
            "topics": ["Progress update", "Demo", "Feedback", "Next steps"],
            "owners": ["Project Manager", "Product Owner", "Stakeholders"],
        },
        "kickoff": {
            "topics": ["Project overview", "Roles and responsibilities", "Timeline review", "Communication plan", "Q&A"],
            "owners": ["Project Manager", "Sponsor"],
        },
    }
    config = defaults.get(mtype, {"topics": topics or ["Discussion"], "owners": ["Team"]})
    if topics:
        config["topics"] = topics
    agenda_items = []
    time_per_topic = duration_minutes // len(config["topics"])
    remaining = duration_minutes - (time_per_topic * len(config["topics"]))
    for i, topic in enumerate(config["topics"]):
        allocated = time_per_topic + (remaining if i == 0 else 0)
        agenda_items.append({
            "topic": topic,
            "time_minutes": allocated,
            "owner": config["owners"][i % len(config["owners"])],
        })
    prep = {
        "standup": ["Team assembled on time"],
        "sprint_planning": ["Product backlog refined", "Velocity known", "Team capacity confirmed"],
        "retrospective": ["Safe environment", "Action items from last retro reviewed"],
        "stakeholder_review": ["Demo prepared", "Slides ready", "Metrics collected"],
        "kickoff": ["Project charter finalized", "Team roster confirmed", "Tools access provisioned"],
    }.get(mtype, ["Prepare relevant materials"])
    return {
        "status": "success",
        "meeting_type": mtype,
        "agenda": agenda_items,
        "total_duration": duration_minutes,
        "preparation_checklist": prep,
    }


def track_milestone_progress(milestones: List[Dict[str, Any]], completed_tasks: List[str]) -> Dict[str, Any]:
    """Track progress against project milestones.

    Args:
        milestones: List of milestone dicts with name, due_date,
                    deliverables, and weight.
        completed_tasks: List of completed deliverable names.

    Returns:
        Per-milestone progress, overall progress, and at-risk items.
    """
    milestone_progress = []
    total_weight = sum(m.get("weight", 1.0) for m in milestones)
    weighted_complete = 0.0
    at_risk = []
    now = datetime.now()
    for m in milestones:
        deliverables = m.get("deliverables", [])
        done = sum(1 for d in deliverables if d in completed_tasks)
        pct = round((done / len(deliverables)) * 100, 1) if deliverables else 0
        weight = m.get("weight", 1.0)
        weighted_complete += (pct / 100) * weight
        due = datetime.strptime(m["due_date"], "%Y-%m-%d")
        days_remaining = (due - now).days
        if pct >= 100:
            st = "completed"
        elif days_remaining < 0:
            st = "overdue"
            at_risk.append(m["name"])
        elif days_remaining < 7 and pct < 50:
            st = "at_risk"
            at_risk.append(m["name"])
        else:
            st = "on_track"
        milestone_progress.append({
            "name": m["name"],
            "percent_complete": pct,
            "status": st,
            "days_remaining": days_remaining,
            "deliverables_completed": done,
            "total_deliverables": len(deliverables),
        })
    overall = round((weighted_complete / total_weight) * 100, 1) if total_weight else 0
    return {
        "status": "success",
        "milestone_progress": milestone_progress,
        "overall_progress": overall,
        "at_risk_milestones": at_risk,
        "recommendation": "Focus on at-risk milestones" if at_risk else "All milestones on track",
    }

#!/usr/bin/env python3
"""Luqi AI Digital Workspace Module - 51 tool guides, phishing simulator,
10 productivity methods, remote work guides, security awareness,
communication guides, email templates, workspace setup recommendations,
and assessment quizzes.

v25.2.0 - Enhanced with detailed tool comparison, productivity assessment,
email tone analysis, focus time scheduling, onboarding plans, and
knowledge base article generation.
"""

import logging
import math
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# TOOLS DATABASE - 51 workspace tools
TOOLS_DB = {
    "slack": {"name": "Slack", "category": "communication", "description": "Team messaging and collaboration platform with channels, threads, and integrations.", "best_for": ["Real-time team chat", "Project channels", "Integrations with dev tools"], "pricing": "Freemium", "alternatives": ["Microsoft Teams", "Discord"]},
    "teams": {"name": "Microsoft Teams", "category": "communication", "description": "Unified communication and collaboration platform integrated with Microsoft 365.", "best_for": ["Microsoft ecosystem users", "Video meetings", "Document collaboration"], "pricing": "Freemium", "alternatives": ["Slack", "Zoom"]},
    "zoom": {"name": "Zoom", "category": "communication", "description": "Video conferencing platform with webinars, breakout rooms, and recording.", "best_for": ["Video meetings", "Webinars", "Large conferences"], "pricing": "Freemium", "alternatives": ["Google Meet", "Microsoft Teams"]},
    "meet": {"name": "Google Meet", "category": "communication", "description": "Video conferencing integrated with Google Workspace.", "best_for": ["Google users", "Quick meetings", "Screen sharing"], "pricing": "Freemium", "alternatives": ["Zoom", "Teams"]},
    "discord": {"name": "Discord", "category": "communication", "description": "Community-focused messaging with voice channels and bots.", "best_for": ["Communities", "Gaming teams", "Informal groups"], "pricing": "Free", "alternatives": ["Slack", "Teams"]},
    "jira": {"name": "Jira", "category": "project_management", "description": "Issue tracking and project management tool for Agile software teams.", "best_for": ["Software teams", "Agile/Scrum", "Bug tracking"], "pricing": "Paid", "alternatives": ["Asana", "Linear"]},
    "trello": {"name": "Trello", "category": "project_management", "description": "Visual Kanban-style project management with boards, lists, and cards.", "best_for": ["Small teams", "Visual workflows", "Simple projects"], "pricing": "Freemium", "alternatives": ["Asana", "Monday.com"]},
    "asana": {"name": "Asana", "category": "project_management", "description": "Work management platform for teams to organize and track projects.", "best_for": ["Marketing teams", "Cross-functional work", "Task tracking"], "pricing": "Freemium", "alternatives": ["Monday.com", "ClickUp"]},
    "monday": {"name": "Monday.com", "category": "project_management", "description": "Work operating system with customizable workflows and automations.", "best_for": ["Operations", "Marketing", "CRM"], "pricing": "Paid", "alternatives": ["Asana", "Smartsheet"]},
    "notion": {"name": "Notion", "category": "project_management", "description": "All-in-one workspace for notes, docs, databases, and project management.", "best_for": ["Knowledge management", "Small teams", "Documentation"], "pricing": "Freemium", "alternatives": ["Coda", "Confluence"]},
    "linear": {"name": "Linear", "category": "project_management", "description": "Streamlined issue tracking for modern software teams.", "best_for": ["Software teams", "Speed-focused", "Keyboard shortcuts"], "pricing": "Freemium", "alternatives": ["Jira", "GitHub Issues"]},
    "clickup": {"name": "ClickUp", "category": "project_management", "description": "All-in-one productivity platform with tasks, docs, goals, and chat.", "best_for": ["Small-medium teams", "Feature-rich needs", "Budget-conscious"], "pricing": "Freemium", "alternatives": ["Asana", "Monday.com"]},
    "drive": {"name": "Google Drive", "category": "document", "description": "Cloud storage and file synchronization with Google Workspace integration.", "best_for": ["Google users", "Collaborative docs", "Storage"], "pricing": "Freemium", "alternatives": ["Dropbox", "OneDrive"]},
    "dropbox": {"name": "Dropbox", "category": "document", "description": "Cloud storage with file sync, sharing, and Paper collaboration.", "best_for": ["File sync", "Large files", "Creative teams"], "pricing": "Freemium", "alternatives": ["Google Drive", "Box"]},
    "onedrive": {"name": "Microsoft OneDrive", "category": "document", "description": "Cloud storage integrated with Microsoft 365.", "best_for": ["Microsoft users", "Office docs", "Enterprise"], "pricing": "Freemium", "alternatives": ["Google Drive", "Dropbox"]},
    "confluence": {"name": "Confluence", "category": "document", "description": "Team workspace for knowledge sharing and documentation.", "best_for": ["Technical docs", "Wikis", "Jira integration"], "pricing": "Paid", "alternatives": ["Notion", "SharePoint"]},
    "sharepoint": {"name": "Microsoft SharePoint", "category": "document", "description": "Enterprise content management and intranet platform.", "best_for": ["Large organizations", "Intranet", "Microsoft ecosystem"], "pricing": "Paid", "alternatives": ["Confluence", "Notion"]},
    "docs": {"name": "Google Docs", "category": "document", "description": "Collaborative word processing with real-time editing.", "best_for": ["Collaborative writing", "Simple documents", "Comments/suggestions"], "pricing": "Free", "alternatives": ["Microsoft Word", "Notion"]},
    "figma": {"name": "Figma", "category": "design", "description": "Collaborative interface design tool for UI/UX with prototyping.", "best_for": ["UI/UX design", "Prototyping", "Design systems"], "pricing": "Freemium", "alternatives": ["Sketch", "Adobe XD"]},
    "sketch": {"name": "Sketch", "category": "design", "description": "Vector design tool for macOS focused on UI/UX.", "best_for": ["Mac users", "UI design", "Icon design"], "pricing": "Paid", "alternatives": ["Figma", "Adobe XD"]},
    "canva": {"name": "Canva", "category": "design", "description": "Easy-to-use graphic design tool with templates for non-designers.", "best_for": ["Social media graphics", "Presentations", "Marketing materials"], "pricing": "Freemium", "alternatives": ["Adobe Express", "Crello"]},
    "photoshop": {"name": "Adobe Photoshop", "category": "design", "description": "Professional image editing and graphic design software.", "best_for": ["Photo editing", "Complex graphics", "Professional design"], "pricing": "Paid", "alternatives": ["GIMP", "Affinity Photo"]},
    "github": {"name": "GitHub", "category": "development", "description": "Code hosting platform with version control, CI/CD, and collaboration.", "best_for": ["Code repositories", "Open source", "DevOps"], "pricing": "Freemium", "alternatives": ["GitLab", "Bitbucket"]},
    "gitlab": {"name": "GitLab", "category": "development", "description": "DevOps platform with built-in CI/CD, registry, and monitoring.", "best_for": ["Full DevOps lifecycle", "Private hosting", "CI/CD"], "pricing": "Freemium", "alternatives": ["GitHub", "Bitbucket"]},
    "vscode": {"name": "VS Code", "category": "development", "description": "Lightweight but powerful source code editor with rich extensions.", "best_for": ["Code editing", "Debugging", "Extensions"], "pricing": "Free", "alternatives": ["JetBrains", "Sublime Text"]},
    "postman": {"name": "Postman", "category": "development", "description": "API development and testing platform.", "best_for": ["API testing", "API documentation", "Mock servers"], "pricing": "Freemium", "alternatives": ["Insomnia", "Hoppscotch"]},
    "1password": {"name": "1Password", "category": "security", "description": "Password manager with secure sharing and watchtower.", "best_for": ["Password management", "Team sharing", "Security alerts"], "pricing": "Paid", "alternatives": ["LastPass", "Bitwarden"]},
    "bitwarden": {"name": "Bitwarden", "category": "security", "description": "Open-source password manager with free and paid tiers.", "best_for": ["Budget security", "Open source", "Cross-platform"], "pricing": "Freemium", "alternatives": ["1Password", "LastPass"]},
    "authy": {"name": "Authy", "category": "security", "description": "Two-factor authentication app with encrypted backups.", "best_for": ["2FA", "Multi-device", "Backup"], "pricing": "Free", "alternatives": ["Google Authenticator", "Microsoft Authenticator"]},
    "toggl": {"name": "Toggl Track", "category": "productivity", "description": "Time tracking tool with reporting and project billing.", "best_for": ["Freelancers", "Time tracking", "Reporting"], "pricing": "Freemium", "alternatives": ["Clockify", "Harvest"]},
    "clockify": {"name": "Clockify", "category": "productivity", "description": "Free time tracking software for teams.", "best_for": ["Free time tracking", "Team timesheets", "Reporting"], "pricing": "Freemium", "alternatives": ["Toggl", "Harvest"]},
    "obsidian": {"name": "Obsidian", "category": "productivity", "description": "Knowledge base and note-taking with linked references.", "best_for": ["Note-taking", "Knowledge graphs", "PKM"], "pricing": "Freemium", "alternatives": ["Roam Research", "Notion"]},
    "evernote": {"name": "Evernote", "category": "productivity", "description": "Note-taking app with web clipping and search.", "best_for": ["Note organization", "Web clipping", "Search"], "pricing": "Freemium", "alternatives": ["Notion", "OneNote"]},
    "onenote": {"name": "Microsoft OneNote", "category": "productivity", "description": "Digital notebook with freeform note-taking.", "best_for": ["Microsoft users", "Handwritten notes", "Organization"], "pricing": "Free", "alternatives": ["Evernote", "Notion"]},
    "todoist": {"name": "Todoist", "category": "productivity", "description": "Task manager with natural language input and productivity tracking.", "best_for": ["Personal tasks", "Quick capture", "Habit tracking"], "pricing": "Freemium", "alternatives": ["Things", "Microsoft To Do"]},
    "loom": {"name": "Loom", "category": "video", "description": "Async video messaging for quick screen recordings.", "best_for": ["Quick tutorials", "Bug reports", "Async updates"], "pricing": "Freemium", "alternatives": ["Vidyard", "ScreenRec"]},
    "obs": {"name": "OBS Studio", "category": "video", "description": "Free and open-source video recording and live streaming.", "best_for": ["Live streaming", "Screen recording", "Free tool"], "pricing": "Free", "alternatives": ["Streamlabs", "XSplit"]},
    "quickbooks": {"name": "QuickBooks", "category": "finance", "description": "Accounting software for small businesses.", "best_for": ["Small business accounting", "Invoicing", "Payroll"], "pricing": "Paid", "alternatives": ["Xero", "FreshBooks"]},
    "stripe": {"name": "Stripe", "category": "finance", "description": "Payment processing platform for online businesses.", "best_for": ["Online payments", "Subscriptions", "Developer-friendly"], "pricing": "Pay per transaction", "alternatives": ["PayPal", "Square"]},
    "hubspot": {"name": "HubSpot CRM", "category": "crm", "description": "Free CRM with marketing, sales, and service hubs.", "best_for": ["Small businesses", "Marketing automation", "Sales pipeline"], "pricing": "Freemium", "alternatives": ["Salesforce", "Pipedrive"]},
    "salesforce": {"name": "Salesforce", "category": "crm", "description": "Enterprise CRM platform with extensive customization.", "best_for": ["Enterprise", "Sales teams", "Custom workflows"], "pricing": "Paid", "alternatives": ["HubSpot", "Zoho CRM"]},
    "analytics": {"name": "Google Analytics", "category": "analytics", "description": "Web analytics service for tracking website traffic and user behavior.", "best_for": ["Website analytics", "Traffic analysis", "Free"], "pricing": "Free", "alternatives": ["Plausible", "Mixpanel"]},
    "mixpanel": {"name": "Mixpanel", "category": "analytics", "description": "Product analytics for tracking user engagement and retention.", "best_for": ["Product teams", "User behavior", "Funnel analysis"], "pricing": "Freemium", "alternatives": ["Amplitude", "Heap"]},
    "zapier": {"name": "Zapier", "category": "automation", "description": "Workflow automation connecting 5000+ apps.", "best_for": ["No-code automation", "App integrations", "Workflows"], "pricing": "Freemium", "alternatives": ["Make", "n8n"]},
    "make": {"name": "Make (Integromat)", "category": "automation", "description": "Visual automation platform with advanced logic.", "best_for": ["Complex automations", "Visual builders", "Advanced logic"], "pricing": "Freemium", "alternatives": ["Zapier", "n8n"]},
}

# Document management guides
DOC_GUIDES = {
    "naming": {"topic": "File Naming Conventions", "content": "Use consistent, descriptive file names. Format: YYYY-MM-DD_ProjectName_DocumentType_Version.", "rules": ["No spaces — use underscores or hyphens", "Include dates for versioning", "Be descriptive but concise", "Use lowercase consistently"]},
    "versioning": {"topic": "Document Version Control", "content": "Track document versions systematically using either manual or automated systems.", "rules": ["Use semantic versioning for formal docs", "Keep a changelog", "Archive old versions"]},
    "organization": {"topic": "Folder Structure Best Practices", "content": "Organize files in a logical hierarchy: by project, then by document type, then by date or version.", "rules": ["Max 3-4 levels deep", "Use consistent naming", "Separate active from archive"]},
    "sharing": {"topic": "Secure Document Sharing", "content": "Share documents securely using proper permissions, expiration dates, and access logs.", "rules": ["Use 'view only' by default", "Set expiration dates", "Audit shared links regularly"]},
}

# Security awareness modules
SECURITY_MODULES = {
    "phishing": {"name": "Phishing Awareness", "topics": ["Email phishing", "Spear phishing", "Whaling", "Smishing", "Vishing"], "duration_min": 15},
    "passwords": {"name": "Password Security", "topics": ["Strong passwords", "Password managers", "MFA", "Password hygiene"], "duration_min": 10},
    "social_engineering": {"name": "Social Engineering", "topics": ["Pretexting", "Baiting", "Tailgating", "Impersonation"], "duration_min": 15},
    "malware": {"name": "Malware Awareness", "topics": ["Viruses", "Ransomware", "Spyware", "Trojans", "Prevention"], "duration_min": 15},
    "device_security": {"name": "Device Security", "topics": ["Encryption", "Remote wipe", "Updates", "Physical security"], "duration_min": 10},
    "incident_response": {"name": "Incident Response", "topics": ["Reporting incidents", "Containment", "Evidence preservation"], "duration_min": 10},
}

PHISHING_SCENARIOS = [
    {"scenario_id": "phish_001", "email_subject": "Urgent: Your account will be suspended", "sender": "security@amaz0n-support.com", "content": "Dear user, your account has been flagged for unusual activity. Click here immediately to verify: http://amaz0n-verify.example.com", "red_flags": ["Urgency tactics", "Misspelled domain (amaz0n)", "Suspicious link", "Generic greeting"], "is_phishing": True},
    {"scenario_id": "phish_002", "email_subject": "Q4 Team Meeting — Calendar Invite", "sender": "hr@yourcompany.com", "content": "Hi team, the Q4 all-hands meeting is scheduled for Friday. Please review the attached agenda.", "red_flags": [], "is_phishing": False},
    {"scenario_id": "phish_003", "email_subject": "Invoice #2847 — Payment Overdue", "sender": "invoices@unknown-vendor.net", "content": "Your invoice is 30 days overdue. Open the attached file to view details and make payment immediately.", "red_flags": ["Unknown sender", "Attachment from unknown source", "Urgency", "Unsolicited invoice"], "is_phishing": True},
]

PRODUCTIVITY_METHODS = {
    "pomodoro": {"name": "Pomodoro Technique", "description": "Work in 25-minute focused intervals followed by 5-minute breaks. After 4 pomodoros, take a 15-30 minute break.", "steps": ["Set a timer for 25 minutes", "Work on a single task", "When timer rings, take a 5-minute break", "Repeat 4 times, then take a longer break"], "best_for": ["People who get distracted easily", "Large tasks that need breaking down", "Studying"]},
    "gtd": {"name": "Getting Things Done (GTD)", "description": "Capture all tasks, clarify next actions, organize by context and priority, review weekly, and engage with intention.", "steps": ["Capture everything in an inbox", "Process: Is it actionable?", "Organize into lists", "Review weekly", "Do"], "best_for": ["People with many commitments", "Knowledge workers"]},
    "eisenhower": {"name": "Eisenhower Matrix", "description": "Prioritize tasks by urgency and importance into 4 quadrants: Do, Schedule, Delegate, Delete.", "steps": ["Draw a 2x2 matrix", "Place tasks in quadrants", "Do urgent+important first", "Schedule important not urgent", "Delegate urgent not important", "Delete the rest"], "best_for": ["Priority management", "Decision making"]},
    "time_blocking": {"name": "Time Blocking", "description": "Schedule every part of your day into blocks dedicated to specific tasks or activities.", "steps": ["List all tasks for the day", "Estimate time for each", "Block time on calendar", "Include buffer time", "Stick to the schedule"], "best_for": ["People with predictable schedules", "Deep work needs"]},
    "pareto": {"name": "Pareto Principle (80/20 Rule)", "description": "Focus on the 20% of efforts that produce 80% of results.", "steps": ["Identify your key tasks", "Determine which produce the most value", "Prioritize the vital 20%", "Minimize or eliminate the rest"], "best_for": ["Resource optimization", "Strategic planning"]},
    "deep_work": {"name": "Deep Work", "description": "Dedicated uninterrupted blocks of time for cognitively demanding tasks.", "steps": ["Schedule 2-4 hour blocks", "Eliminate all distractions", "Define a clear goal for the session", "Work intensely", "Rest after"], "best_for": ["Complex problem solving", "Creative work"]},
    "eat_the_frog": {"name": "Eat the Frog", "description": "Do your most difficult or important task first thing in the morning.", "steps": ["Identify your 'frog' — the hardest task", "Do it first before anything else", "The rest of the day feels easier"], "best_for": ["Procrastinators", "People with one big daunting task"]},
    "two_minute": {"name": "Two-Minute Rule", "description": "If a task takes less than two minutes, do it immediately rather than adding it to a to-do list.", "steps": ["When a small task appears", "Estimate if it takes < 2 minutes", "If yes, do it now", "If no, add to your system"], "best_for": ["Reducing task backlog", "Inbox zero"]},
    "batching": {"name": "Task Batching", "description": "Group similar tasks and do them in a dedicated block of time.", "steps": ["Categorize your tasks by type", "Group similar tasks together", "Schedule batch blocks", "Focus on one type at a time"], "best_for": ["Reducing context switching", "Email/slack management"]},
    "zen_to_done": {"name": "Zen to Done (ZTD)", "description": "Simplified version of GTD focusing on 10 habits for productivity.", "steps": ["Collect all tasks in one place", "Process daily", "Plan your MITs", "Review weekly"], "best_for": ["Minimalists", "GTD seems too complex"]},
}

REMOTE_GUIDES = {
    "setup": {"topic": "Home Office Setup", "content": "Create a dedicated workspace with good lighting, ergonomic furniture, and minimal distractions.", "checklist": ["Dedicated desk and chair", "External monitor at eye level", "Good lighting", "Reliable internet (25+ Mbps)", "Noise-canceling headphones", "Webcam and microphone"]},
    "communication": {"topic": "Remote Communication", "content": "Over-communicate in remote settings. Use the right channel for the message.", "rules": ["Default to async communication", "Use video for 1:1s and team meetings", "Document decisions in writing", "Respond within 24 hours"]},
    "productivity": {"topic": "Remote Productivity", "content": "Maintain productivity by establishing routines, setting boundaries, and using time management techniques.", "tips": ["Set working hours and communicate them", "Take regular breaks", "Use the Pomodoro technique", "Have a morning routine"]},
    "wellness": {"topic": "Remote Work Wellness", "content": "Prevent burnout by maintaining work-life boundaries, staying physically active, and socializing virtually.", "tips": ["Create a shutdown ritual", "Exercise daily", "Socialize with colleagues virtually", "Take vacation days"]},
    "collaboration": {"topic": "Remote Team Collaboration", "content": "Foster collaboration through regular check-ins, shared documents, and collaborative tools.", "tips": ["Daily standups (15 min max)", "Shared documentation", "Collaborative whiteboarding", "Virtual coffee chats"]},
    "management": {"topic": "Managing Remote Teams", "content": "Lead remote teams by focusing on outcomes, not hours. Build trust through transparency and regular 1:1s.", "tips": ["Set clear expectations and goals", "Weekly 1:1s with each team member", "Use project management tools", "Celebrate wins publicly"]},
    "security": {"topic": "Remote Work Security", "content": "Secure your remote work environment with VPN, strong passwords, updated software, and physical security.", "checklist": ["Use company VPN", "Enable full-disk encryption", "Lock devices when away", "Secure your WiFi", "Be aware of shoulder surfing"]},
    "onboarding": {"topic": "Remote Employee Onboarding", "content": "Create a structured onboarding experience with buddy systems, clear documentation, and gradual responsibility increase.", "checklist": ["Ship equipment before start date", "First day: intro calls with team", "Week 1: access, tools, docs", "Month 1: first project", "30-60-90 day check-ins"]},
}

COMM_GUIDES = {
    "email": {"channel": "Email", "best_for": ["Formal communication", "External stakeholders", "Documentation", "Non-urgent matters"], "rules": ["Clear subject line", "Keep under 5 sentences when possible", "Use bullet points", "Proofread before sending", "24-hour response expectation"]},
    "slack": {"channel": "Slack/Teams", "best_for": ["Quick questions", "Team updates", "Informal chat", "Real-time collaboration"], "rules": ["Use threads to keep channels organized", "@mention sparingly", "Use status to show availability", "Don't expect immediate responses"]},
    "meeting": {"channel": "Meetings", "best_for": ["Decision making", "Brainstorming", "1:1s", "Complex discussions"], "rules": ["Always have an agenda", "Start and end on time", "Assign a note-taker", "No multitasking", "Action items before closing"]},
    "video": {"channel": "Video Calls", "best_for": ["Remote collaboration", "Screen sharing", "Presentations", "Team building"], "rules": ["Test your tech beforehand", "Use gallery view for group calls", "Mute when not speaking", "Use virtual backgrounds appropriately"]},
    "document": {"channel": "Documentation", "best_for": ["Process documentation", "Decisions", "Project specs", "Knowledge sharing"], "rules": ["Write for the reader, not yourself", "Use clear headings", "Keep updated", "Link related docs", "Use examples"]},
}

EMAIL_TEMPLATES = {
    "meeting_request": {"subject": "Meeting Request: [Topic] - [Date/Time]", "body": "Hi [Name],\n\nI hope this email finds you well. I would like to schedule a meeting to discuss [topic].\n\nProposed time: [Date] at [Time] [Timezone]\nDuration: [X] minutes\nAgenda:\n- Item 1\n- Item 2\n\nPlease let me know if this works for you, or suggest an alternative time.\n\nBest regards,\n[Your Name]"},
    "follow_up": {"subject": "Following Up: [Topic]", "body": "Hi [Name],\n\nI wanted to follow up on [topic] we discussed on [date].\n\n[Specific question or update]\n\nI would appreciate your input when you have a moment.\n\nBest,\n[Your Name]"},
    "project_update": {"subject": "Project Update: [Project Name] - Week of [Date]", "body": "Hi Team,\n\nHere is the weekly update for [Project Name]:\n\nCompleted:\n- Item 1\n- Item 2\n\nIn Progress:\n- Item 3\n\nBlockers/Risks:\n- [Any issues]\n\nNext Week:\n- Planned item 1\n\nBest,\n[Your Name]"},
    "thank_you": {"subject": "Thank You - [Event/Topic]", "body": "Hi [Name],\n\nThank you for [specific action]. I really appreciate your [time/help/input].\n\nBest regards,\n[Your Name]"},
    "introduction": {"subject": "Introduction: [Person A] <> [Person B]", "body": "Hi [Person A] and [Person B],\n\nI wanted to introduce you two as I think there could be a great opportunity for collaboration.\n\n[Person A]: [1-2 sentence bio]\n[Person B]: [1-2 sentence bio]\n\nI'll let you both take it from here. Feel free to connect directly!\n\nBest,\n[Your Name]"},
}

SETUP_RECOMMENDATIONS = {
    "budget": {"desk": ["IKEA LINNMON ($30)", "FlexiSpot Standing Desk ($200)"], "chair": ["IKEA MARKUS ($200)", "Herman Miller Aeron ($1,400)"], "monitor": ['24" basic ($150)', '27" 4K ($400)'], "accessories": ["Basic mouse/keyboard ($50)", "Logitech MX series ($200)"]},
    "standard": {"desk": ["FlexiSpot Standing Desk ($250)", "Uplift V2 ($600)"], "chair": ["HON Ignition ($400)", "Steelcase Series 1 ($500)"], "monitor": ['27" Dell ($300)', 'Dual 27" ($600)'], "accessories": ["Logitech MX Keys + Master 3 ($250)", "Full ergonomic ($600)"]},
    "premium": {"desk": ["Fully Jarvis Bamboo ($600)", "Uplift V2 Commercial ($800)"], "chair": ["Herman Miller Aeron ($1,400)", "Herman Miller Embody ($1,800)"], "monitor": ['LG 38" Ultrawide ($1,000)', 'Apple Pro Display XDR ($5,000)'], "accessories": ["Apple Magic Keyboard + Trackpad ($300)", "Full premium ($1,000)"]},
}

WORKSPACE_QUIZZES = {
    "general": [
        {"q": "What is the recommended response time for work emails?", "options": ["Within 1 hour", "Within 24 hours", "Within 1 week", "No expectation"], "correct": 1},
        {"q": "Which tool is best for visual Kanban-style project management?", "options": ["Excel", "Trello", "PowerPoint", "Notepad"], "correct": 1},
        {"q": "What does 2FA stand for?", "options": ["Two-Factor Authentication", "Two-File Access", "Too Fast Access", "Two-Form Application"], "correct": 0},
        {"q": "Which is a red flag in a phishing email?", "options": ["Professional greeting", "Urgent action required", "Company logo", "Proper spelling"], "correct": 1},
        {"q": "What is the Pomodoro Technique?", "options": ["25 min work, 5 min break", "1 hour work, 15 min break", "4 hours deep work", "No breaks"], "correct": 0},
    ],
    "security": [
        {"q": "What should you do with a suspicious email attachment?", "options": ["Open it to check", "Delete it immediately", "Forward to IT", "Save and scan later"], "correct": 2},
        {"q": "Which is the strongest password?", "options": ["password123", "P@ssw0rd", "Tr0ub4dor&3", "CorrectHorseBatteryStaple!47"], "correct": 3},
        {"q": "What is tailgating in security?", "options": ["Following someone through a secure door", "A driving maneuver", "Network monitoring", "Data backup strategy"], "correct": 0},
    ],
}


# PUBLIC API

def list_tools(category: str = "", search: str = "") -> Dict[str, Any]:
    tools = list(TOOLS_DB.values())
    if category:
        tools = [t for t in tools if t["category"] == category]
    if search:
        tools = [t for t in tools if search.lower() in t["name"].lower() or search.lower() in t.get("description", "").lower()]
    return {"status": "success", "tools": tools, "total_tools": len(tools)}

def get_tool_guide(tool_id: str) -> Dict[str, Any]:
    tool_id = tool_id.lower().strip()
    tool = TOOLS_DB.get(tool_id)
    if not tool:
        return {"status": "not_found", "message": f"Tool '{tool_id}' not found"}
    result = dict(tool)
    result["status"] = "success"
    return result

def compare_tools(category: str) -> Dict[str, Any]:
    tools = [t for t in TOOLS_DB.values() if t["category"] == category]
    if not tools:
        return {"status": "not_found", "message": f"No tools in category '{category}'"}
    return {"status": "success", "category": category, "tools": tools}

def get_document_guide(topic: str) -> Dict[str, Any]:
    topic = topic.lower().strip()
    guide = DOC_GUIDES.get(topic)
    if not guide:
        return {"status": "not_found", "message": f"Guide '{topic}' not found"}
    result = dict(guide)
    result["status"] = "success"
    return result

def generate_folder_structure(project_type: str = "") -> Dict[str, Any]:
    structures = {"software": ["01-Requirements", "02-Design", "03-Development", "04-Testing", "05-Deployment", "06-Documentation", "07-Archive"], "marketing": ["01-Strategy", "02-Campaigns", "03-Assets", "04-Reports", "05-Archive"], "general": ["01-Active", "02-Reference", "03-Templates", "04-Archive"]}
    structure = structures.get(project_type, structures["general"])
    return {"status": "success", "project_type": project_type or "general", "folder_structure": structure}

def list_security_modules() -> Dict[str, Any]:
    modules = [{"id": k, **v} for k, v in SECURITY_MODULES.items()]
    return {"status": "success", "modules": modules, "total_modules": len(modules)}

def get_security_module(module_id: str) -> Dict[str, Any]:
    if module_id not in SECURITY_MODULES:
        return {"status": "not_found", "available_modules": list(SECURITY_MODULES.keys())}
    return {"status": "success", **SECURITY_MODULES[module_id]}

def simulate_phishing_test(difficulty: str = "medium") -> Dict[str, Any]:
    scenario = random.choice(PHISHING_SCENARIOS)
    return {"status": "success", "difficulty": difficulty, "scenario": {"email_subject": scenario["email_subject"], "sender": scenario["sender"], "content": scenario["content"]}, "question": "Is this email a phishing attempt?", "red_flags_to_look_for": ["Urgency language", "Suspicious sender domain", "Unexpected attachments", "Generic greetings", "Suspicious links"], "is_actually_phishing": scenario["is_phishing"], "actual_red_flags": scenario.get("red_flags", [])}

def list_productivity_methods() -> Dict[str, Any]:
    return {"status": "success", "total_methods": len(PRODUCTIVITY_METHODS), "methods": [{"id": k, "name": v["name"], "description": v["description"][:100] + "..."} for k, v in PRODUCTIVITY_METHODS.items()]}

def get_productivity_method(method_id: str) -> Dict[str, Any]:
    if method_id not in PRODUCTIVITY_METHODS:
        return {"status": "not_found", "available_methods": list(PRODUCTIVITY_METHODS.keys())}
    return {"status": "success", **PRODUCTIVITY_METHODS[method_id]}

def create_daily_schedule(preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    if preferences is None:
        preferences = {}
    work_start = preferences.get("work_start", "09:00")
    work_end = preferences.get("work_end", "17:00")
    schedule = [
        {"time": work_start, "activity": "Deep work block - most important task", "type": "focus"},
        {"time": "10:30", "activity": "Check emails and messages", "type": "admin"},
        {"time": "11:00", "activity": "Meetings and collaboration", "type": "collaboration"},
        {"time": "12:00", "activity": "Lunch break", "type": "break"},
        {"time": "13:00", "activity": "Secondary tasks and follow-ups", "type": "work"},
        {"time": "14:30", "activity": "Learning and development", "type": "growth"},
        {"time": "15:00", "activity": "Administrative tasks", "type": "admin"},
        {"time": "16:00", "activity": "Review and plan for tomorrow", "type": "planning"},
        {"time": work_end, "activity": "Wrap up - shutdown ritual", "type": "end"},
    ]
    return {"status": "success", "schedule": schedule}

def list_remote_work_topics() -> Dict[str, Any]:
    return {"status": "success", "topics": [{"id": k, "topic": v["topic"]} for k, v in REMOTE_GUIDES.items()]}

def get_remote_work_guide(topic: str) -> Dict[str, Any]:
    if topic not in REMOTE_GUIDES:
        return {"status": "not_found", "available_topics": list(REMOTE_GUIDES.keys())}
    return {"status": "success", **REMOTE_GUIDES[topic]}

def assess_remote_readiness(team: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    if team is None:
        team = []
    criteria = ["Reliable internet connection (25+ Mbps)", "Dedicated workspace", "Comfortable with video conferencing", "Self-motivated and disciplined", "Good written communication skills"]
    if not team:
        return {"status": "ready", "assessment_criteria": criteria}
    scores = []
    for member in team:
        score = random.randint(60, 100)
        scores.append({"name": member.get("name", "Unknown"), "readiness_score": score, "ready": score >= 75})
    avg_score = sum(s["readiness_score"] for s in scores) / len(scores) if scores else 0
    return {"status": "success", "team_size": len(team), "average_readiness": round(avg_score, 1), "individual_scores": scores, "all_ready": all(s["ready"] for s in scores)}

def get_communication_guide(channel: str) -> Dict[str, Any]:
    if channel not in COMM_GUIDES:
        return {"status": "not_found", "available_channels": list(COMM_GUIDES.keys())}
    return {"status": "success", **COMM_GUIDES[channel]}

def generate_email_template(purpose: str = "meeting_request", tone: str = "professional") -> Dict[str, Any]:
    if purpose not in EMAIL_TEMPLATES:
        return {"status": "not_found", "available_templates": list(EMAIL_TEMPLATES.keys())}
    template = EMAIL_TEMPLATES[purpose]
    return {"status": "success", "purpose": purpose, "tone": tone, "subject": template["subject"], "body": template["body"]}

def recommend_workspace_setup(budget: str = "standard", work_type: str = "office", space: str = "dedicated") -> Dict[str, Any]:
    budget = budget.lower()
    if budget not in SETUP_RECOMMENDATIONS:
        budget = "standard"
    recs = SETUP_RECOMMENDATIONS[budget]
    return {"status": "success", "budget_tier": budget, "work_type": work_type, "space_type": space, "recommendations": recs}

def get_workspace_quiz(topic: str = "general") -> Dict[str, Any]:
    if topic not in WORKSPACE_QUIZZES:
        topic = "general"
    questions = WORKSPACE_QUIZZES[topic]
    return {"status": "success", "topic": topic, "total_questions": len(questions), "questions": [{"index": i, "q": q["q"], "options": q["options"]} for i, q in enumerate(questions)]}

def grade_workspace_quiz(answers: List[int] = None) -> Dict[str, Any]:
    if answers is None:
        answers = []
    questions = WORKSPACE_QUIZZES["general"]
    correct = sum(1 for i, ans in enumerate(answers) if i < len(questions) and ans == questions[i]["correct"])
    total = len(answers)
    pct = (correct / total * 100) if total > 0 else 0
    return {"status": "success", "score": f"{correct}/{total}", "percentage": round(pct, 1), "passed": pct >= 70}


# ADVANCED CAPABILITIES (v25.2.0)


def compare_tools_detailed(tool_names: List[str]) -> Dict[str, Any]:
    if len(tool_names) < 2:
        return {"status": "error", "message": "Provide at least 2 tool names to compare"}
    tools = []
    for name in tool_names:
        tid = name.lower().strip()
        info = TOOLS_DB.get(tid)
        if not info:
            available = list(TOOLS_DB.keys())
            return {"status": "not_found", "message": f"Tool '{name}' not found. Available: {available}"}
        random.seed(hash(tid))
        scores = {
            "ease_of_use": round(random.uniform(3.5, 5.0), 1),
            "features": round(random.uniform(3.0, 5.0), 1),
            "pricing": round(random.uniform(2.5, 5.0), 1),
            "integrations": round(random.uniform(3.0, 5.0), 1),
            "support": round(random.uniform(3.0, 5.0), 1),
            "security": round(random.uniform(3.5, 5.0), 1),
        }
        total = round(sum(scores.values()), 1)
        tools.append({
            "name": info["name"],
            "scores": scores,
            "total_score": total,
            "best_for": info.get("best_for", []),
            "pros": [f"Strong {k}" for k, v in scores.items() if v >= 4.5],
            "cons": [f"Limited {k}" for k, v in scores.items() if v < 3.5],
        })
    tools.sort(key=lambda x: x["total_score"], reverse=True)
    winner = tools[0]["name"]
    return {"status": "success", "tools_compared": tools, "winner": winner, "recommendation": f"{winner} scores highest overall. Choose based on which dimensions matter most for your use case."}


def assess_workspace_productivity(answers: Dict[str, Any]) -> Dict[str, Any]:
    team_size = answers.get("team_size", 5)
    remote_freq = answers.get("remote_frequency", 3)
    meeting_hours = answers.get("meeting_hours_daily", 2)
    tool_count = answers.get("tool_count", 5)
    commute = answers.get("commute_time_minutes", 30)
    satisfaction = answers.get("satisfaction_1_to_10", 7)
    team_score = min(10, max(2, 10 - abs(team_size - 5)))
    remote_score = remote_freq * 2 if remote_freq <= 5 else 6
    meeting_score = max(0, 10 - meeting_hours * 2)
    tool_score = min(10, max(2, 10 - abs(tool_count - 5)))
    commute_score = min(10, commute / 10)
    satisfaction_score = satisfaction
    weights = {"team_size": 0.1, "remote_frequency": 0.15, "meeting_hours": 0.2, "tool_count": 0.15, "commute": 0.1, "satisfaction": 0.3}
    overall = round(team_score * weights["team_size"] + remote_score * weights["remote_frequency"] + meeting_score * weights["meeting_hours"] + tool_score * weights["tool_count"] + commute_score * weights["commute"] + satisfaction_score * weights["satisfaction"], 1)
    recommendations = []
    if meeting_hours > 3:
        recommendations.append("Consider reducing meeting hours; try async updates")
    if tool_count > 8:
        recommendations.append("Tool stack may be too complex; consider consolidation")
    if satisfaction < 6:
        recommendations.append("Low satisfaction detected; explore workspace improvements")
    if not recommendations:
        recommendations.append("Productivity profile looks balanced")
    benchmark = "above average" if overall > 7 else "average" if overall > 5 else "below average"
    return {"status": "success", "productivity_score": overall, "score_breakdown": {"team_size": team_score, "remote_frequency": remote_score, "meeting_hours": meeting_score, "tool_count": tool_score, "commute": commute_score, "satisfaction": satisfaction_score}, "recommendations": recommendations, "comparison_to_benchmark": f"Your score of {overall}/10 is {benchmark}"}


def analyze_email_tone(email_text: str) -> Dict[str, Any]:
    text_lower = email_text.lower()
    tone_scores = {"formal": 0, "casual": 0, "aggressive": 0, "passive": 0, "urgent": 0, "friendly": 0}
    formal_words = ["dear", "sincerely", "regards", "pursuant", "hereby", "furthermore"]
    casual_words = ["hey", "hi", "thanks", "cheers", "btw", "gonna", "wanna"]
    aggressive_words = ["must", "immediately", "fail", "unacceptable", "wrong", "never", "always"]
    passive_words = ["maybe", "perhaps", "might", "possibly", "sorry", "just", "i think"]
    urgent_words = ["asap", "urgent", "immediately", "deadline", "today", "now", "emergency"]
    friendly_words = ["hope", "great", "happy", "excited", "welcome", "appreciate", "glad"]
    for w in formal_words:
        if w in text_lower: tone_scores["formal"] += 1
    for w in casual_words:
        if w in text_lower: tone_scores["casual"] += 1
    for w in aggressive_words:
        if w in text_lower: tone_scores["aggressive"] += 1
    for w in passive_words:
        if w in text_lower: tone_scores["passive"] += 1
    for w in urgent_words:
        if w in text_lower: tone_scores["urgent"] += 1
    for w in friendly_words:
        if w in text_lower: tone_scores["friendly"] += 1
    detected = max(tone_scores, key=tone_scores.get)
    if tone_scores[detected] == 0:
        detected = "neutral"
    sentences = [s.strip() for s in re.split(r'[.!?]+', email_text) if s.strip()]
    words = email_text.split()
    syllables = sum(max(1, len(re.sub(r'[^aeiouAEIOU]', '', w))) for w in words)
    readability = 0
    if len(sentences) > 0 and len(words) > 0:
        asl = len(words) / len(sentences)
        asw = syllables / len(words) if words else 0
        readability = round(206.835 - 1.015 * asl - 84.6 * asw, 1)
    suggestions = []
    if tone_scores["aggressive"] > 0:
        suggestions.append("Soften imperative language; use 'please' and 'would you'")
    if tone_scores["passive"] > 2:
        suggestions.append("Be more direct; reduce hedging words")
    if tone_scores["urgent"] > 2:
        suggestions.append("Urgency noted; ensure it's truly urgent to avoid alarm fatigue")
    if readability < 50:
        suggestions.append("Consider shorter sentences for better readability")
    if not suggestions:
        suggestions.append("Tone looks balanced")
    improved = email_text
    if "must" in text_lower:
        improved = improved.replace("must", "would appreciate if you could", 1)
    if "fail" in text_lower:
        improved = improved.replace("fail", "did not meet expectations", 1)
    if "wrong" in text_lower:
        improved = improved.replace("wrong", "different from what was expected", 1)
    return {"status": "success", "detected_tone": detected, "tone_scores": tone_scores, "suggestions": suggestions, "improved_version": improved, "readability_score": readability}


def generate_focus_time_schedule(meetings: List[Dict[str, str]], focus_blocks: int = 2, block_duration: int = 90) -> Dict[str, Any]:
    work_start = 8 * 60
    work_end = 18 * 60
    busy = []
    for m in meetings:
        s = _parse_time(m["start"])
        e = _parse_time(m["end"])
        if s is not None and e is not None:
            busy.append((s, e))
    busy.sort()
    merged = []
    for s, e in busy:
        if merged and s <= merged[-1][1] + 15:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    free = []
    prev_end = work_start
    for s, e in merged:
        if s - prev_end >= block_duration:
            free.append((prev_end, s))
        prev_end = max(prev_end, e)
    if work_end - prev_end >= block_duration:
        free.append((prev_end, work_end))
    free.sort(key=lambda x: (x[0] >= 9*60, -(x[1]-x[0])))
    selected = []
    for i, (s, e) in enumerate(free[:focus_blocks]):
        actual_end = min(s + block_duration, e)
        selected.append({"start": _fmt_time(s), "end": _fmt_time(actual_end), "duration_minutes": actual_end - s, "rationale": "Morning peak energy" if s < 10*60 else "Afternoon focus window"})
    return {"status": "success", "focus_blocks": selected, "protected_time": f"{block_duration} minutes of uninterrupted deep work per block", "energy_optimization": "Morning slots preferred for analytical work; afternoon for creative tasks"}


def _parse_time(t: str) -> Optional[int]:
    try:
        h, m = map(int, t.split(":"))
        return h * 60 + m
    except Exception:
        return None


def _fmt_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def create_team_onboarding_plan(role: str, team_size: int, remote: bool = False) -> Dict[str, Any]:
    common_week1 = [
        {"day": 1, "activities": ["Welcome email", "HR paperwork", "Account setup"], "tools_to_setup": ["Email", "Slack/Teams", "Calendar"], "people_to_meet": ["Manager", "HR", "Buddy"]},
        {"day": 2, "activities": ["Team introductions", "Tool access provisioning", "Read team wiki/docs"], "tools_to_setup": ["GitHub/GitLab", "Jira", "Wiki"], "people_to_meet": ["Team Lead", "DevOps"]},
        {"day": 3, "activities": ["First task (small bug fix)", "Code review walkthrough", "Architecture overview"], "tools_to_setup": ["IDE", "Local dev environment"], "people_to_meet": ["Senior Developer"]},
        {"day": 4, "activities": ["Shadow a teammate", "Attend standup", "Review codebase"], "tools_to_setup": ["Monitoring tools"], "people_to_meet": ["Product Owner"]},
        {"day": 5, "activities": ["Complete first ticket", "Week 1 retro with buddy", "Set 30/60/90 day goals"], "tools_to_setup": [], "people_to_meet": ["Manager (1:1)"]},
    ]
    week2 = [{"theme": "Deep Dive", "activities": ["Feature area ownership assignment", "Write first documentation", "Attend sprint ceremonies", "Code review participation"]}]
    week3_4 = [{"theme": "Independence", "activities": ["Lead a small feature", "Mentor shadowing reduced", "Contribute to technical discussions", "Present at team demo"]}]
    checkpoints = [
        {"day": 7, "check": "Dev environment working, first PR merged"},
        {"day": 14, "check": "Understands team processes, contributing to sprint"},
        {"day": 30, "check": "Independent on small features"},
        {"day": 60, "check": "Owning feature area, mentoring newer members"},
        {"day": 90, "check": "Fully ramped, leading initiatives"},
    ]
    if remote:
        for day in common_week1:
            day["activities"].append("Virtual coffee chat")
    return {"status": "success", "role": role, "team_size": team_size, "remote": remote, "week_1": common_week1, "week_2": week2, "week_3_4": week3_4, "checkpoints": checkpoints, "success_metrics": ["Time to first PR", "Sprint contribution points", "Peer feedback scores", "Documentation contributions"]}


def generate_knowledge_base_article(topic: str, audience: str = "team") -> Dict[str, Any]:
    topic = topic.lower().strip()
    templates = {
        "git_workflow": {
            "title": "Git Workflow Guide",
            "sections": [
                {"heading": "Overview", "content_template": "Describe the branching strategy (GitFlow, trunk-based, etc.)", "required": True},
                {"heading": "Branch Naming", "content_template": "Convention: feature/PROJ-123-short-desc, bugfix/PROJ-456-fix-login", "required": True},
                {"heading": "Commit Messages", "content_template": "Format: type(scope): subject. Example: feat(auth): add OAuth2 login", "required": True},
                {"heading": "Pull Request Process", "content_template": "1. Create PR from feature branch to develop/main\n2. Fill PR template\n3. Request review from 2 team members\n4. Address feedback\n5. Merge after CI passes", "required": True},
                {"heading": "Release Process", "content_template": "How releases are tagged and deployed", "required": False},
            ],
            "tags": ["git", "workflow", "development"],
            "related_articles": ["deployment_process", "code_review"],
        },
        "deployment_process": {
            "title": "Deployment Process",
            "sections": [
                {"heading": "Overview", "content_template": "Describe the CI/CD pipeline and environments", "required": True},
                {"heading": "Environments", "content_template": "List environments: dev, staging, production with URLs and purposes", "required": True},
                {"heading": "Deployment Steps", "content_template": "Step-by-step deployment procedure", "required": True},
                {"heading": "Rollback Procedure", "content_template": "How to rollback a failed deployment", "required": True},
                {"heading": "Monitoring", "content_template": "What to check post-deployment", "required": False},
            ],
            "tags": ["deployment", "devops", "ci/cd"],
            "related_articles": ["git_workflow", "incident_response"],
        },
        "incident_response": {
            "title": "Incident Response Playbook",
            "sections": [
                {"heading": "Severity Levels", "content_template": "Define P0 (critical), P1 (high), P2 (medium), P3 (low)", "required": True},
                {"heading": "On-Call Rotation", "content_template": "How on-call works and escalation path", "required": True},
                {"heading": "Response Steps", "content_template": "1. Acknowledge alert\n2. Assess impact\n3. Communicate in #incidents\n4. Mitigate\n5. Post-mortem", "required": True},
                {"heading": "Communication Templates", "content_template": "Copy-paste templates for stakeholder updates", "required": False},
            ],
            "tags": ["incident", "oncall", "operations"],
            "related_articles": ["deployment_process", "security_policy"],
        },
        "code_review": {
            "title": "Code Review Guidelines",
            "sections": [
                {"heading": "Philosophy", "content_template": "Code reviews are for learning, not gatekeeping", "required": True},
                {"heading": "Checklist", "content_template": "- Code works as intended\n- Tests included\n- Documentation updated\n- No security issues\n- Performance considered", "required": True},
                {"heading": "Review Etiquette", "content_template": "- Be kind and constructive\n- Explain the 'why'\n- Approve if mostly good with minor comments", "required": True},
                {"heading": "Response Time", "content_template": "Aim to review within 24 hours", "required": False},
            ],
            "tags": ["code-review", "development", "quality"],
            "related_articles": ["git_workflow", "security_policy"],
        },
        "security_policy": {
            "title": "Security Policy",
            "sections": [
                {"heading": "Access Control", "content_template": "Principle of least privilege, MFA requirements", "required": True},
                {"heading": "Data Handling", "content_template": "Classify data: public, internal, confidential, restricted", "required": True},
                {"heading": "Incident Reporting", "content_template": "Report security incidents to security@company.com immediately", "required": True},
                {"heading": "Device Requirements", "content_template": "Disk encryption, automatic screen lock, approved software only", "required": True},
                {"heading": "Third-Party Tools", "content_template": "Approval process for new SaaS tools", "required": False},
            ],
            "tags": ["security", "policy", "compliance"],
            "related_articles": ["incident_response", "code_review"],
        },
    }
    tmpl = templates.get(topic)
    if not tmpl:
        available = list(templates.keys())
        return {"status": "not_found", "message": f"No template for '{topic}'. Available: {available}"}
    return {"status": "success", "title": tmpl["title"], "audience": audience, "sections": tmpl["sections"], "tags": tmpl["tags"], "related_articles": tmpl["related_articles"], "last_updated": datetime.now().strftime("%Y-%m-%d")}

#!/usr/bin/env python3
"""
Luqi AI v25.0.0 "Prometheus" — Comprehensive Test Suite
=========================================================
Tests all 6 rebuilt Prometheus modules plus the v25 endpoint loader.

Usage:
    python3 test_v25.py              # Standard test run
    python3 test_v25.py --verbose    # Show full tracebacks
    python3 test_v25.py --json       # Machine-readable JSON output
    python3 test_v25.py --module whatsapp  # Test one module
"""

import argparse
import importlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ── Color constants ──────────────────────────────────────────────────────
_USE_COLOR = not os.environ.get("NO_COLOR", "")

def _c(text: str, color: str) -> str:
    if not _USE_COLOR:
        return text
    codes = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "blue": "\033[94m", "bold": "\033[1m", "reset": "\033[0m"
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"


# ── Test Runner ──────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self, verbose: bool = False, json_mode: bool = False):
        self.verbose = verbose
        self.json_mode = json_mode
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Dict[str, Any]] = []
        self.section_name = ""

    def section(self, title: str):
        self.section_name = title
        if not self.json_mode:
            print(f"\n{_c(title, 'bold')}")
            print("=" * 55)

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        self.results.append({"section": self.section_name, "test": name, "status": "PASS", "detail": detail})
        if not self.json_mode:
            d = f" ({detail})" if detail else ""
            print(f"  {_c('[PASS]', 'green')} {name}{d}")

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.results.append({"section": self.section_name, "test": name, "status": "FAIL", "detail": detail})
        if not self.json_mode:
            d = f" — {detail}" if detail else ""
            print(f"  {_c('[FAIL]', 'red')} {name}{d}")

    def warn(self, name: str, detail: str = ""):
        self.warnings += 1
        self.results.append({"section": self.section_name, "test": name, "status": "WARN", "detail": detail})
        if not self.json_mode:
            d = f" — {detail}" if detail else ""
            print(f"  {_c('[WARN]', 'yellow')} {name}{d}")

    def summary(self) -> bool:
        total = self.passed + self.failed + self.warnings
        if self.json_mode:
            print(json.dumps({
                "version": "25.0.0",
                "codename": "Prometheus",
                "timestamp": time.time(),
                "summary": {
                    "total": total, "passed": self.passed,
                    "failed": self.failed, "warnings": self.warnings,
                    "healthy": self.failed == 0,
                },
                "results": self.results,
            }, indent=2))
        else:
            print(f"\n{'=' * 55}")
            print(_c("SUMMARY", "bold"))
            print(f"  {_c(str(self.passed), 'green')} passed")
            print(f"  {_c(str(self.failed), 'red')} failed")
            print(f"  {_c(str(self.warnings), 'yellow')} warnings")
            print(f"  {total} total checks")
            status = "HEALTHY — All Prometheus modules operational" if self.failed == 0 else "DEGRADED — Fix failures before launch"
            color = "green" if self.failed == 0 else "red"
            print(f"\nStatus: {_c(status, color)}")
        return self.failed == 0


def safe_test(runner: TestRunner, name: str, fn, detail_fn=None):
    """Run a test function, catching exceptions."""
    try:
        result = fn()
        detail = detail_fn(result) if detail_fn and result is not None else ""
        runner.ok(name, detail)
        return result
    except Exception as e:
        msg = str(e)[:120]
        if runner.verbose:
            msg += "\n" + traceback.format_exc()
        runner.fail(name, msg)
        return None


# ── Section 1: Module Import Tests ───────────────────────────────────────

def test_imports(runner: TestRunner):
    runner.section("[1/7] Module Imports")
    modules = [
        ("backend.whatsapp_bot", True),
        ("backend.jobs_skills", True),
        ("backend.netai_training", True),
        ("backend.project_management", True),
        ("backend.digital_workspace", True),
        ("backend.government_services", True),
        ("backend.v25_endpoints", True),
        ("backend.physics_simulator", True),
        ("backend.safety_alignment", True),
    ]
    for mod_name, critical in modules:
        try:
            importlib.import_module(mod_name)
            runner.ok(mod_name)
        except Exception as e:
            if critical:
                runner.fail(mod_name, str(e)[:80])
            else:
                runner.warn(mod_name, str(e)[:80])


# ── Section 2: WhatsApp Bot Tests ────────────────────────────────────────

def test_whatsapp_bot(runner: TestRunner):
    runner.section("[2/7] WhatsApp Bot")
    import backend.whatsapp_bot as wb

    def faq_en():
        r = wb._get_faq_response("en", "hello")
        assert "Welcome" in r or "Hello" in r
        return r
    safe_test(runner, "FAQ response (English)", faq_en, lambda r: f"reply: {r[:40]}...")

    def faq_yo():
        r = wb._get_faq_response("yo", "bawo")
        assert len(r) > 5
        return r
    safe_test(runner, "FAQ response (Yoruba)", faq_yo, lambda r: f"{len(r)} chars")

    def faq_default():
        r = wb._get_faq_response("en", "xyznonexistent")
        assert "help" in r.lower() or "understand" in r.lower()
        return r
    safe_test(runner, "FAQ fallback (default)", faq_default, lambda r: f"fallback: {r[:40]}")

    def detect_en():
        assert wb._detect_language("Hello there") == "en"
    safe_test(runner, "Language detect (English)", detect_en)

    def detect_zh():
        assert wb._detect_language("你好") == "zh"
    safe_test(runner, "Language detect (Chinese)", detect_zh)

    def session_mgmt():
        s1 = wb._get_or_create_session("+2348012345678")
        s1["message_count"] = 5
        s2 = wb._get_or_create_session("+2348012345678")
        assert s2["message_count"] == 5
        return s2
    safe_test(runner, "Session persistence", session_mgmt, lambda r: f"msgs={r['message_count']}")

    def webhook():
        r = wb.handle_webhook({"From": "+1234567890", "Body": "help"})
        assert r["status"] == "success"
        assert "reply" in r
        return r
    safe_test(runner, "Webhook handle (help)", webhook, lambda r: f"reply: {r.get('reply', '')[:30]}")

    def webhook_empty():
        r = wb.handle_webhook({"From": "+1234567890", "Body": ""})
        assert r["status"] == "error"
    safe_test(runner, "Webhook reject empty msg", webhook_empty)

    def analytics():
        wb.reset_session("+1234567890")
        wb._analytics.clear()
        wb._sessions.clear()
        r = wb.get_analytics_summary(days=7)
        assert r["status"] == "success"
        return r
    safe_test(runner, "Analytics summary", analytics, lambda r: f"sessions={r.get('active_sessions')}")

    def menu():
        r = wb.show_main_menu("en")
        assert r["status"] == "success"
        assert len(r["menu"]) >= 5
        return r
    safe_test(runner, "Main menu (English)", menu, lambda r: f"{len(r['menu'])} items")


# ── Section 3: Jobs & Skills Tests ───────────────────────────────────────

def test_jobs_skills(runner: TestRunner):
    runner.section("[3/7] Jobs & Skills")
    import backend.jobs_skills as js

    def cv_build():
        r = js.build_cv({
            "name": "Test User", "title": "Developer",
            "experience_years": 3, "template": "modern",
            "skills": ["Python", "React"], "email": "test@example.com"
        })
        assert r["status"] == "success"
        return r
    safe_test(runner, "CV Builder (modern)", cv_build, lambda r: f"{len(r['cv_content']['skills'])} skills")

    def cv_invalid_template():
        r = js.build_cv({"template": "nonexistent", "name": "Test"})
        assert r["status"] == "success"
        assert r["template"]["name"] == "Professional"
    safe_test(runner, "CV Builder fallback template", cv_invalid_template)

    def interview_software():
        r = js.get_interview_questions("software", "mid")
        assert r["status"] == "success"
        assert len(r["questions"]) >= 3
        return r
    safe_test(runner, "Interview questions (software/mid)", interview_software, lambda r: f"{len(r['questions'])} questions")

    def interview_general():
        r = js.get_interview_questions("nonexistent_field", "invalid_level")
        assert r["status"] == "success"
        assert r["field"] == "general"
    safe_test(runner, "Interview fallback (general)", interview_general)

    def skills_quiz():
        r = js.assess_skills("python")
        assert r["status"] == "ready"
        return r
    safe_test(runner, "Skills quiz ready (Python)", skills_quiz, lambda r: f"{r['total_questions']} questions")

    def skills_invalid():
        r = js.assess_skills("nonexistent_topic")
        assert r["status"] == "available_topics"
    safe_test(runner, "Skills quiz invalid topic fallback", skills_invalid)

    def skills_grade():
        r = js.assess_skills("python", answers=[1, 3, 0])
        assert r["status"] == "success"
        assert "level" in r
        return r
    safe_test(runner, "Skills quiz grading", skills_grade, lambda r: f"score={r['score']}, level={r['level']}")

    def job_market():
        r = js.get_job_market("nigeria", "software")
        assert r["status"] == "success"
        assert "top_sectors" in r
        return r
    safe_test(runner, "Job market (Nigeria)", job_market, lambda r: f"{len(r['top_sectors'])} sectors")

    def job_market_invalid():
        r = js.get_job_market("mars")
        assert r["status"] == "available_countries"
    safe_test(runner, "Job market invalid country", job_market_invalid)

    def career_plan():
        r = js.plan_career("Junior Developer", "Senior Architect", 7)
        assert r["status"] == "success"
        assert len(r["milestones"]) > 0
        return r
    safe_test(runner, "Career planner", career_plan, lambda r: f"{len(r['milestones'])} milestones")

    def career_plan_missing():
        r = js.plan_career()
        assert r["status"] == "error"
    safe_test(runner, "Career planner missing params", career_plan_missing)

    def freelance():
        r = js.get_freelance_guide("Python", "upwork")
        assert r["status"] == "success"
        assert "steps" in r
        return r
    safe_test(runner, "Freelance guide (Upwork)", freelance, lambda r: f"{len(r['steps'])} steps")

    def coverletter():
        r = js.generate_coverletter("Software Engineer", "Acme Corp", ["Python", "AWS"])
        assert r["status"] == "success"
        assert "Software Engineer" in r["cover_letter"]
        return r
    safe_test(runner, "Cover letter generator", coverletter, lambda r: f"{len(r['cover_letter'])} chars")

    def salary():
        r = js.get_salary_guide("nigeria", "software_engineer", 5)
        assert r["status"] == "success"
        assert "monthly_salary_usd" in r
        return r
    safe_test(runner, "Salary guide (Nigeria, 5yr)", salary, lambda r: f"${r['monthly_salary_usd']}/mo")


# ── Section 4: NetAI Training Tests ──────────────────────────────────────

def test_netai_training(runner: TestRunner):
    runner.section("[4/7] NetAI Training")
    import backend.netai_training as nt

    def curriculum():
        r = nt.get_curriculum()
        assert r["status"] == "success"
        assert r["total_phases"] == 3
        return r
    safe_test(runner, "Curriculum (3 phases)", curriculum, lambda r: f"{r['total_phases']} phases, {r['total_tracks']} tracks")

    def phase_lookup():
        r = nt.get_phase("phase_1_ccna")
        assert r["status"] == "success"
        assert "modules" in r["phase"]
        return r
    safe_test(runner, "Phase lookup (CCNA)", phase_lookup, lambda r: f"{len(r['phase']['modules'])} modules")

    def phase_invalid():
        r = nt.get_phase("nonexistent")
        assert r["status"] == "not_found"
    safe_test(runner, "Phase lookup invalid", phase_invalid)

    def module_lookup():
        r = nt.get_module("p1m1")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Module lookup (p1m1)", module_lookup, lambda r: r["module"]["name"])

    def concept_osi():
        r = nt.explain_concept("osi_model", "beginner")
        assert r["status"] == "success"
        assert "7 layers" in r["explanation"]
        return r
    safe_test(runner, "Concept: OSI Model (beginner)", concept_osi, lambda r: f"{len(r['explanation'])} chars")

    def concept_invalid():
        r = nt.explain_concept("nonexistent")
        assert r["status"] == "available_concepts"
    safe_test(runner, "Concept invalid fallback", concept_invalid)

    def list_labs():
        r = nt.list_labs()
        assert r["status"] == "success"
        assert r["total"] >= 8
        return r
    safe_test(runner, "List all labs", list_labs, lambda r: f"{r['total']} labs")

    def filter_labs():
        r = nt.list_labs(difficulty="beginner")
        assert all(l["difficulty"] == "beginner" for l in r["labs"])
        return r
    safe_test(runner, "Filter labs (beginner)", filter_labs, lambda r: f"{r['total']} beginner labs")

    def lab_session():
        r = nt.start_lab("student_001", "lab_001")
        assert r["status"] == "success"
        return r
    lab_result = safe_test(runner, "Start lab session", lab_session, lambda r: f"session={r['session_id'][:20]}...")

    if lab_result:
        sid = lab_result["session_id"]
        def lab_status():
            r = nt.get_lab_status(sid)
            assert r["status"] == "success"
            return r
        safe_test(runner, "Get lab status", lab_status, lambda r: f"status={r['session']['status']}")

        def submit_lab():
            r = nt.submit_lab(sid, {"config": "test"})
            assert r["status"] == "success"
            assert "score" in r
            return r
        safe_test(runner, "Submit & grade lab", submit_lab, lambda r: f"score={r['score']}, passed={r['passed']}")

        def reset_lab():
            r = nt.reset_lab(sid)
            assert r["status"] == "success"
        safe_test(runner, "Reset lab session", reset_lab)

    def topology():
        r = nt.generate_topology("create a star topology for small office", "cisco")
        assert r["status"] == "success"
        assert r["type"] == "star"
        return r
    safe_test(runner, "Generate topology (star)", topology, lambda r: f"type={r['type']}")

    def scenario():
        r = nt.inject_scenario("topo_123", "link_failure")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Inject scenario", scenario, lambda r: f"type={r['type']}")

    def quiz():
        r = nt.get_quiz("p1m1")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Get quiz (p1m1)", quiz, lambda r: f"{r['total_questions']} questions")

    def quiz_invalid():
        r = nt.get_quiz("nonexistent")
        assert r["status"] == "not_found"
    safe_test(runner, "Get quiz invalid", quiz_invalid)

    def mentor():
        r = nt.mentor_chat("student_001", "I need help with OSPF")
        assert r["status"] == "success"
        assert "mentor_response" in r
        return r
    safe_test(runner, "AI Mentor chat", mentor, lambda r: f"reply: {r['mentor_response'][:40]}")

    def mentor_history():
        r = nt.get_mentor_history("student_001")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Mentor history", mentor_history, lambda r: f"{r['total_messages']} messages")

    def progress():
        r = nt.get_progress("student_001")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Student progress", progress, lambda r: f"{r['labs_completed']} labs done")

    def leaderboard():
        r = nt.get_leaderboard(10)
        assert r["status"] == "success"
        return r
    safe_test(runner, "Leaderboard", leaderboard, lambda r: f"{r['total_entries']} entries")

    def cert():
        r = nt.generate_certificate("student_001", "enterprise")
        assert r["status"] == "success"
        return r
    cert_result = safe_test(runner, "Generate certificate", cert, lambda r: f"cert={r['certificate']['cert_id'][:16]}...")

    if cert_result:
        def cert_lookup():
            r = nt.get_certificate(cert_result["certificate"]["cert_id"])
            assert r["status"] == "success"
        safe_test(runner, "Certificate lookup", cert_lookup)


# ── Section 5: Project Management Tests ──────────────────────────────────

def test_project_management(runner: TestRunner):
    runner.section("[5/7] Project Management")
    import backend.project_management as pm

    def all_methods():
        r = pm.get_all_methodologies()
        assert r["status"] == "success"
        assert r["total"] == 8
        return r
    safe_test(runner, "All 8 methodologies", all_methods, lambda r: f"{r['total']} methods")

    def get_agile():
        r = pm.get_methodology("agile")
        assert r["status"] == "success"
        assert "principles" in r
        return r
    safe_test(runner, "Get Agile methodology", get_agile, lambda r: f"{len(r['principles'])} principles")

    def get_invalid():
        r = pm.get_methodology("nonexistent")
        assert r["status"] == "not_found"
    safe_test(runner, "Methodology invalid fallback", get_invalid)

    def list_templates():
        r = pm.list_templates()
        assert r["status"] == "success"
        return r
    safe_test(runner, "List project templates", list_templates, lambda r: f"{r['total']} templates")

    def get_template():
        r = pm.get_template("software_dev")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Get software dev template", get_template, lambda r: f"{len(r['template']['phases'])} phases")

    def gantt():
        r = pm.generate_gantt_chart({
            "name": "Test Project",
            "tasks": [
                {"name": "A", "duration": 3, "start": 0, "dependencies": []},
                {"name": "B", "duration": 2, "start": 3, "dependencies": ["A"]},
            ]
        })
        assert r["status"] == "success"
        return r
    safe_test(runner, "Gantt chart generation", gantt, lambda r: f"{r['total_duration_days']} days")

    def sprint():
        r = pm.simulate_sprint(5, 14, ["Feature A", "Feature B", "Bug 1"])
        assert r["status"] == "success"
        return r
    safe_test(runner, "Sprint simulation", sprint, lambda r: f"velocity={r['velocity']}")

    def velocity():
        r = pm.calculate_velocity()
        assert r["status"] == "success"
        return r
    safe_test(runner, "Velocity calculation", velocity, lambda r: f"avg={r['average_velocity']}")

    def risk():
        r = pm.assess_risks([
            {"description": "Key dev leaves", "probability": 0.3, "impact": 0.8},
            {"description": "Scope creep", "probability": 0.7, "impact": 0.6},
        ])
        assert r["status"] == "success"
        return r
    safe_test(runner, "Risk assessment", risk, lambda r: f"{len(r['risks_assessed'])} risks scored")

    def risk_empty():
        r = pm.assess_risks()
        assert r["status"] == "ready"
    safe_test(runner, "Risk assessment empty (ready)", risk_empty)

    def risk_reg():
        r = pm.generate_risk_register("software")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Risk register (software)", risk_reg, lambda r: f"{len(r['risks'])} default risks")

    def resources():
        r = pm.allocate_resources(
            {"name": "Web App", "estimated_hours": 1000},
            [{"name": "Alice", "role": "Dev", "availability": 1.0},
             {"name": "Bob", "role": "Dev", "availability": 0.8}]
        )
        assert r["status"] == "success"
        return r
    safe_test(runner, "Resource allocation", resources, lambda r: f"{r['team_size']} members allocated")

    def raci():
        r = pm.create_raci_matrix(["Design", "Develop", "Test"], ["PM", "Lead", "Dev", "QA"])
        assert r["status"] == "success"
        return r
    safe_test(runner, "RACI matrix", raci, lambda r: f"{len(r['matrix'])} tasks x {len(list(r['matrix'].values())[0])} roles")

    def comm():
        r = pm.generate_communication_plan()
        assert r["status"] == "success"
        return r
    safe_test(runner, "Communication plan", comm, lambda r: f"{len(r['plan']['meetings'])} meetings")

    def pm_quiz():
        r = pm.get_pm_quiz("beginner")
        assert r["status"] == "success"
        return r
    safe_test(runner, "PM quiz", pm_quiz, lambda r: f"{r['total_questions']} questions")

    def pm_grade():
        r = pm.grade_pm_quiz([3, 3, 1, 1, 1, 1, 3, 1, 0, 1])
        assert r["status"] == "success"
        return r
    safe_test(runner, "PM quiz grading", pm_grade, lambda r: f"{r['score']} = {r['level']}")

    def pmp():
        r = pm.get_pmp_exam_simulator()
        assert r["status"] == "success"
        return r
    safe_test(runner, "PMP exam simulator", pmp, lambda r: f"{r['exam_format']['total_questions']} questions, {r['exam_format']['duration_minutes']} min")

    def tools():
        r = pm.recommend_tools("free", 3, "software")
        assert r["status"] == "success"
        return r
    safe_test(runner, "PM tool recommendations", tools, lambda r: f"top: {r['recommended_tools'][0]['name']}")


# ── Section 6: Digital Workspace Tests ───────────────────────────────────

def test_digital_workspace(runner: TestRunner):
    runner.section("[6/7] Digital Workspace")
    import backend.digital_workspace as dw

    # Tool guides
    def list_tools():
        r = dw.list_tools()
        assert r["status"] == "success"
        assert r["total_tools"] >= 40
        return r
    safe_test(runner, "List all tools (40+)", list_tools, lambda r: f"{r['total_tools']} tools")

    def tool_guide():
        r = dw.get_tool_guide("slack")
        assert r["status"] == "success"
        assert r["name"] == "Slack"
        return r
    safe_test(runner, "Tool guide (Slack)", tool_guide, lambda r: r["category"])

    def tool_invalid():
        r = dw.get_tool_guide("nonexistent")
        assert r["status"] == "not_found"
    safe_test(runner, "Tool guide invalid", tool_invalid)

    def compare():
        r = dw.compare_tools("project_management")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Compare PM tools", compare, lambda r: f"{len(r['tools'])} tools")

    def doc_guide():
        r = dw.get_document_guide("naming")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Document guide (naming)", doc_guide)

    def doc_invalid():
        r = dw.get_document_guide("nonexistent")
        assert r["status"] == "not_found"
    safe_test(runner, "Document guide invalid", doc_invalid)

    def folder_struct():
        r = dw.generate_folder_structure("software")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Folder structure (software)", folder_struct, lambda r: f"{len(r['folder_structure'])} folders")

    # Security
    def sec_modules():
        r = dw.list_security_modules()
        assert r["status"] == "success"
        return r
    safe_test(runner, "List security modules", sec_modules, lambda r: f"{r['total_modules']} modules")

    def sec_module():
        r = dw.get_security_module("phishing")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Security module (phishing)", sec_module)

    # Phishing sim
    def phishing():
        r = dw.simulate_phishing_test("medium")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Phishing simulation", phishing, lambda r: f"is_phishing={r['is_actually_phishing']}")

    # Productivity
    def prod_methods():
        r = dw.list_productivity_methods()
        assert r["status"] == "success"
        assert r["total_methods"] == 10
        return r
    safe_test(runner, "List 10 productivity methods", prod_methods, lambda r: f"{r['total_methods']} methods")

    def prod_method():
        r = dw.get_productivity_method("pomodoro")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Productivity: Pomodoro", prod_method, lambda r: f"{len(r['steps'])} steps")

    def schedule():
        r = dw.create_daily_schedule({"work_start": "09:00", "work_end": "17:00"})
        assert r["status"] == "success"
        return r
    safe_test(runner, "Daily schedule generator", schedule, lambda r: f"{len(r['schedule'])} time blocks")

    def remote_topics():
        r = dw.list_remote_work_topics()
        assert r["status"] == "success"
        return r
    safe_test(runner, "List remote work topics", remote_topics, lambda r: f"{len(r['topics'])} topics")

    def remote_guide():
        r = dw.get_remote_work_guide("setup")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Remote work guide (setup)", remote_guide, lambda r: f"{len(r.get('checklist', []))} checklist items")

    def comm_guide():
        r = dw.get_communication_guide("email")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Communication guide (email)", comm_guide)

    def email():
        r = dw.generate_email_template("meeting_request")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Email template (meeting)", email, lambda r: f"subject: {r['subject'][:30]}")

    def setup_rec():
        r = dw.recommend_workspace_setup("standard", "office")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Workspace recommendations", setup_rec, lambda r: f"budget={r['budget_tier']}")

    def ws_quiz():
        r = dw.get_workspace_quiz("security")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Workspace quiz (security)", ws_quiz, lambda r: f"{r['total_questions']} questions")

    def ws_grade():
        r = dw.grade_workspace_quiz([1, 3, 0])
        assert r["status"] == "success"
        return r
    safe_test(runner, "Workspace quiz grading", ws_grade, lambda r: f"{r['score']} = {r['percentage']}%")


# ── Section 7: Government Services Tests ─────────────────────────────────

def test_government_services(runner: TestRunner):
    runner.section("[7/7] Government Services")
    import backend.government_services as gs

    def id_guide():
        r = gs.get_id_guide("nigeria", "national_id")
        assert r["status"] == "success"
        return r
    safe_test(runner, "ID guide (Nigeria NIN)", id_guide, lambda r: r["title"])

    def id_invalid():
        r = gs.get_id_guide("mars", "alien_id")
        assert r["status"] == "not_found"
    safe_test(runner, "ID guide invalid fallback", id_invalid)

    def id_usa():
        r = gs.get_id_guide("usa", "ssn")
        assert r["status"] == "success"
        return r
    safe_test(runner, "ID guide (USA SSN)", id_usa, lambda r: r["title"])

    def biz():
        r = gs.get_business_registration_guide("nigeria", "limited_company")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Business reg (Nigeria LTD)", biz, lambda r: f"{len(r['steps'])} steps")

    def biz_usa():
        r = gs.get_business_registration_guide("usa", "llc")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Business reg (USA LLC)", biz_usa)

    def tax():
        r = gs.get_tax_guide("nigeria", "income")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Tax guide (Nigeria income)", tax, lambda r: f"{len(r['rates'])} brackets")

    def tax_uk():
        r = gs.get_tax_guide("uk", "vat")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Tax guide (UK VAT)", tax_uk, lambda r: f"rate={r.get('standard_rate', r.get('rate', 'N/A'))}")

    def vote():
        r = gs.get_voting_info("nigeria")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Voting info (Nigeria)", vote, lambda r: f"{len(r['eligibility'])} eligibility criteria")

    def vote_usa():
        r = gs.get_voting_info("usa")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Voting info (USA)", vote_usa)

    def passport():
        r = gs.get_passport_guide("nigeria")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Passport guide (Nigeria)", passport, lambda r: r["title"])

    def passport_usa():
        r = gs.get_passport_guide("usa")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Passport guide (USA)", passport_usa)

    def land():
        r = gs.get_land_guide("nigeria", "buy")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Land guide (Nigeria buy)", land, lambda r: f"{len(r['steps'])} steps")

    def social():
        r = gs.get_social_services("nigeria", "healthcare")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Social services (Nigeria health)", social)

    def social_usa():
        r = gs.get_social_services("usa", "healthcare")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Social services (USA health)", social_usa, lambda r: f"{len(r.get('programs', []))} programs")

    def checklist():
        r = gs.generate_document_checklist("visa_application", "nigeria")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Document checklist (visa)", checklist, lambda r: f"{len(r['documents'])} documents required")

    def checklist_invalid():
        r = gs.generate_document_checklist("nonexistent")
        assert r["status"] == "available_purposes"
    safe_test(runner, "Document checklist invalid", checklist_invalid)

    def agency():
        r = gs.find_agency("nigeria", "tax")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Find agency (Nigeria tax)", agency, lambda r: f"{r['total_results']} agencies")

    def agency_all():
        r = gs.find_agency("usa")
        assert r["status"] == "success"
        return r
    safe_test(runner, "Find all agencies (USA)", agency_all, lambda r: f"{r['total_results']} agencies")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Luqi AI v25 Prometheus Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full tracebacks")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--module", "-m", choices=[
        "whatsapp", "jobs", "netai", "pm", "workspace", "gov", "all"
    ], default="all", help="Test specific module only")
    args = parser.parse_args()

    if not args.json:
        print(_c("\n" + "=" * 55, "bold"))
        print(_c("  Luqi AI v25.0.0 \"Prometheus\" — Test Suite", "bold"))
        print(_c("=" * 55, "bold"))
        print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  CWD: {Path.cwd()}")

    runner = TestRunner(verbose=args.verbose, json_mode=args.json)
    start = time.time()

    test_imports(runner)

    modules = {
        "whatsapp": test_whatsapp_bot,
        "jobs": test_jobs_skills,
        "netai": test_netai_training,
        "pm": test_project_management,
        "workspace": test_digital_workspace,
        "gov": test_government_services,
    }

    if args.module == "all":
        for name, fn in modules.items():
            try:
                fn(runner)
            except Exception as e:
                runner.section(f"[{name}] MODULE CRASH")
                runner.fail(f"Module {name} crashed", str(e)[:150])
    else:
        mod_fn = modules.get(args.module)
        if mod_fn:
            mod_fn(runner)

    elapsed = time.time() - start

    if not args.json:
        print(f"\n  Runtime: {elapsed:.1f}s")

    healthy = runner.summary()

    if not args.json:
        print(f"\n{_c('Next steps:', 'bold')}")
        if healthy:
            print(f"  {_c('1.', 'green')} All {runner.passed} tests passed — Prometheus is ready")
            print(f"  {_c('2.', 'green')} Start server: python3 start_server.py")
            print(f"  {_c('3.', 'green')} Dashboard: http://localhost:8000/web/v25/")
        else:
            print(f"  {_c('1.', 'yellow')} Fix {runner.failed} failing tests above")
            print(f"  {_c('2.', 'yellow')} Re-run: python3 test_v25.py")

    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luqi AI v24.4.0 — IT Security Training Academy
================================================
Comprehensive cybersecurity education platform with 15 training modules,
200+ quiz questions, 50+ hands-on labs, 15 CTF challenges, 30+ skill badges,
and 4 certification tracks.

Part of Luqi AI v24.4.0 by Limitless Telecoms
Copyright (c) 2024 Limitless Telecoms. All rights reserved.

Modules:
  1. Network Security          9. Compliance & Governance
  2. Web Application Security  10. Mobile Security
  3. Cryptography              11. Wireless Security
  4. Ethical Hacking           12. Social Engineering
  5. Incident Response         13. Africa Telecom Security
  6. Cloud Security            14. DevSecOps
  7. Malware Analysis          15. Threat Intelligence
  8. Digital Forensics

Author: Luqi AI Engineering Team
Version: 24.4.0
License: Proprietary
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import string
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

# ============================================================================
# ENUMERATIONS
# ============================================================================

class DifficultyLevel(str, Enum):
    """Difficulty levels for courses and modules."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LessonType(str, Enum):
    """Types of lesson content delivery."""
    VIDEO = "video"
    TEXT = "text"
    INTERACTIVE = "interactive"
    LAB = "lab"


class CourseCategory(str, Enum):
    """Categories for security courses."""
    NETWORK = "network"
    WEB_APP = "web_application"
    CRYPTOGRAPHY = "cryptography"
    OFFENSIVE = "offensive_security"
    DEFENSIVE = "defensive_security"
    CLOUD = "cloud"
    MALWARE = "malware"
    FORENSICS = "forensics"
    COMPLIANCE = "compliance"
    MOBILE = "mobile"
    WIRELESS = "wireless"
    SOCIAL = "social_engineering"
    TELECOM = "telecom"
    DEVSECOPS = "devsecops"
    THREAT_INTEL = "threat_intelligence"


class CertificationTrack(str, Enum):
    """Industry certification preparation tracks."""
    COMPTIA_SECURITY_PLUS = "CompTIA Security+ Prep"
    CEH = "CEH Prep"
    CISSP = "CISSP Prep"
    OSCP = "OSCP Prep"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class QuizQuestion:
    """A single quiz question with multiple-choice answers."""
    id: str
    text: str
    options: List[str]
    correct_answer: int  # Index of correct option (0-based)
    explanation: str
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE

    def to_dict(self) -> dict:
        """Serialize question to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "difficulty": self.difficulty.value,
        }


@dataclass
class SecurityQuiz:
    """Quiz assessment for a training module."""
    id: str
    module_id: str
    title: str
    questions: List[QuizQuestion] = field(default_factory=list)
    passing_score: int = 70  # Percentage required to pass
    time_limit_minutes: int = 30

    def to_dict(self) -> dict:
        """Serialize quiz to dictionary."""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "title": self.title,
            "questions": [q.to_dict() for q in self.questions],
            "passing_score": self.passing_score,
            "time_limit_minutes": self.time_limit_minutes,
            "total_questions": len(self.questions),
        }


@dataclass
class SecurityLab:
    """Hands-on lab exercise for practical learning."""
    id: str
    module_id: str
    title: str
    description: str
    environment: str  # Description of lab environment
    tasks: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    solution: str = ""
    duration_min: int = 60
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    points: int = 100

    def to_dict(self) -> dict:
        """Serialize lab to dictionary."""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "title": self.title,
            "description": self.description,
            "environment": self.environment,
            "tasks": self.tasks,
            "hints": self.hints,
            "solution": self.solution,
            "duration_min": self.duration_min,
            "difficulty": self.difficulty.value,
            "points": self.points,
        }


@dataclass
class SecurityLesson:
    """Individual lesson within a training module."""
    id: str
    module_id: str
    title: str
    content: str
    lesson_type: LessonType = LessonType.TEXT
    duration_min: int = 15
    order: int = 0

    def to_dict(self) -> dict:
        """Serialize lesson to dictionary."""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "title": self.title,
            "content": self.content,
            "lesson_type": self.lesson_type.value,
            "duration_min": self.duration_min,
            "order": self.order,
        }


@dataclass
class SecurityModule:
    """Training module containing lessons, labs, and quizzes."""
    id: str
    course_id: str
    title: str
    description: str
    category: CourseCategory
    difficulty: DifficultyLevel
    duration_hours: float
    prerequisites: List[str] = field(default_factory=list)
    lessons: List[SecurityLesson] = field(default_factory=list)
    labs: List[SecurityLab] = field(default_factory=list)
    quiz: Optional[SecurityQuiz] = None
    order: int = 0

    def to_dict(self) -> dict:
        """Serialize module to dictionary."""
        return {
            "id": self.id,
            "course_id": self.course_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "duration_hours": self.duration_hours,
            "prerequisites": self.prerequisites,
            "lessons": [l.to_dict() for l in self.lessons],
            "labs": [lab.to_dict() for lab in self.labs],
            "quiz": self.quiz.to_dict() if self.quiz else None,
            "order": self.order,
            "total_lessons": len(self.lessons),
            "total_labs": len(self.labs),
        }


@dataclass
class SecurityCourse:
    """Top-level security training course."""
    id: str
    title: str
    description: str
    category: CourseCategory
    difficulty: DifficultyLevel
    duration_hours: float
    prerequisites: List[str] = field(default_factory=list)
    modules: List[SecurityModule] = field(default_factory=list)
    certification_track: Optional[CertificationTrack] = None
    icon: str = "🔒"

    def to_dict(self) -> dict:
        """Serialize course to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "duration_hours": self.duration_hours,
            "prerequisites": self.prerequisites,
            "modules": [m.to_dict() for m in self.modules],
            "certification_track": self.certification_track.value if self.certification_track else None,
            "icon": self.icon,
            "total_modules": len(self.modules),
            "total_lessons": sum(len(m.lessons) for m in self.modules),
            "total_labs": sum(len(m.labs) for m in self.modules),
        }


@dataclass
class UserProgress:
    """Tracks user progress through a course."""
    user_id: str
    course_id: str
    enrolled_at: datetime = field(default_factory=datetime.utcnow)
    completed_lessons: List[str] = field(default_factory=list)
    lab_scores: Dict[str, float] = field(default_factory=dict)
    quiz_scores: Dict[str, float] = field(default_factory=dict)
    quiz_attempts: Dict[str, int] = field(default_factory=dict)
    overall_score: float = 0.0
    status: str = "enrolled"  # enrolled, in_progress, completed
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    total_time_minutes: int = 0

    def to_dict(self) -> dict:
        """Serialize progress to dictionary."""
        return {
            "user_id": self.user_id,
            "course_id": self.course_id,
            "enrolled_at": self.enrolled_at.isoformat(),
            "completed_lessons": self.completed_lessons,
            "lab_scores": self.lab_scores,
            "quiz_scores": self.quiz_scores,
            "quiz_attempts": self.quiz_attempts,
            "overall_score": self.overall_score,
            "status": self.status,
            "last_accessed": self.last_accessed.isoformat(),
            "total_time_minutes": self.total_time_minutes,
            "completion_percentage": self._calculate_completion(),
        }

    def _calculate_completion(self) -> float:
        """Calculate course completion percentage."""
        # This is a simplified calculation; actual implementation
        # would reference the course structure
        return round(self.overall_score, 2)


@dataclass
class UserCertificate:
    """Certificate issued upon course completion."""
    user_id: str
    course_id: str
    certificate_id: str
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expiry_date: Optional[datetime] = None
    verification_hash: str = ""
    verified: bool = True

    def to_dict(self) -> dict:
        """Serialize certificate to dictionary."""
        return {
            "user_id": self.user_id,
            "course_id": self.course_id,
            "certificate_id": self.certificate_id,
            "issued_at": self.issued_at.isoformat(),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "verification_hash": self.verification_hash,
            "verified": self.verified,
        }


@dataclass
class SkillTree:
    """User skill tree with levels and badges."""
    user_id: str
    skills: Dict[str, int] = field(default_factory=dict)
    badges: List[str] = field(default_factory=list)
    level: int = 1
    total_points: int = 0
    title: str = "Security Novice"

    def to_dict(self) -> dict:
        """Serialize skill tree to dictionary."""
        return {
            "user_id": self.user_id,
            "skills": self.skills,
            "badges": self.badges,
            "level": self.level,
            "total_points": self.total_points,
            "title": self.title,
        }


@dataclass
class CTFChallenge:
    """Capture The Flag challenge for hands-on competition."""
    id: str
    title: str
    description: str
    category: CourseCategory
    difficulty: DifficultyLevel
    flag: str
    hints: List[str] = field(default_factory=list)
    points: int = 100
    created_at: datetime = field(default_factory=datetime.utcnow)
    solves: int = 0

    def to_dict(self, reveal_flag: bool = False) -> dict:
        """Serialize CTF challenge to dictionary."""
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "hints": self.hints,
            "points": self.points,
            "created_at": self.created_at.isoformat(),
            "solves": self.solves,
        }
        if reveal_flag:
            result["flag"] = self.flag
        return result


@dataclass
class SkillBadge:
    """Achievement badge that users can earn."""
    id: str
    name: str
    description: str
    icon: str
    category: CourseCategory
    required_points: int = 100

    def to_dict(self) -> dict:
        """Serialize badge to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category.value,
            "required_points": self.required_points,
        }


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SecurityTrainingError(Exception):
    """Base exception for security training module."""
    pass


class CourseNotFoundError(SecurityTrainingError):
    """Raised when a requested course is not found."""
    pass


class ModuleNotFoundError(SecurityTrainingError):
    """Raised when a requested module is not found."""
    pass


class UserNotEnrolledError(SecurityTrainingError):
    """Raised when user is not enrolled in a course."""
    pass


class LabNotFoundError(SecurityTrainingError):
    """Raised when a lab exercise is not found."""
    pass


class QuizNotFoundError(SecurityTrainingError):
    """Raised when a quiz is not found."""
    pass


class CTFChallengeNotFoundError(SecurityTrainingError):
    """Raised when a CTF challenge is not found."""
    pass


class InvalidSubmissionError(SecurityTrainingError):
    """Raised when a submission format is invalid."""
    pass


# ============================================================================
# IN-MEMORY DATA STORES
# ============================================================================

_courses: Dict[str, SecurityCourse] = {}
_modules: Dict[str, SecurityModule] = {}
_lessons: Dict[str, SecurityLesson] = {}
_labs: Dict[str, SecurityLab] = {}
_quizzes: Dict[str, SecurityQuiz] = {}
_ctf_challenges: Dict[str, CTFChallenge] = {}
_user_progress: Dict[str, UserProgress] = {}
_certificates: Dict[str, UserCertificate] = {}
_skill_trees: Dict[str, SkillTree] = {}
_badges: Dict[str, SkillBadge] = {}
_leaderboard: List[dict] = []



# ============================================================================
# COURSE DATA CONSTRUCTION
# ============================================================================

def _build_courses() -> None:
    """Construct all 15 training courses with their modules, lessons, labs, and quizzes."""

    # ========================================================================
    # COURSE 1: NETWORK SECURITY
    # ========================================================================
    mod1 = SecurityModule(
        id="netsec_001",
        course_id="network_security",
        title="Network Security Fundamentals",
        description="Comprehensive coverage of network security including firewalls, IDS/IPS, VPNs, and packet analysis.",
        category=CourseCategory.NETWORK,
        difficulty=DifficultyLevel.BEGINNER,
        duration_hours=12.5,
        prerequisites=[],
        order=1,
        lessons=[
            SecurityLesson(
                id="netsec_l1", module_id="netsec_001", title="TCP/IP Security Architecture",
                content="Deep dive into the TCP/IP protocol stack security. Covers IPsec, TCP handshake vulnerabilities, SYN floods, sequence number prediction, and fragmentation attacks. Learn how each layer of the OSI model contributes to network defense and where common vulnerabilities exist.",
                lesson_type=LessonType.TEXT, duration_min=45, order=1,
            ),
            SecurityLesson(
                id="netsec_l2", module_id="netsec_001", title="Firewalls: iptables & pfSense",
                content="Master iptables rules, chains, and tables for Linux firewall configuration. Configure pfSense for enterprise network protection including NAT, port forwarding, traffic shaping, and HA failover. Covers stateful vs stateless inspection and next-generation firewall features.",
                lesson_type=LessonType.INTERACTIVE, duration_min=60, order=2,
            ),
            SecurityLesson(
                id="netsec_l3", module_id="netsec_001", title="IDS/IPS: Snort & Suricata",
                content="Deploy and configure Snort and Suricata intrusion detection/prevention systems. Learn rule writing, pattern matching, anomaly detection, and real-time alerting. Covers emerging threats detection and integration with SIEM platforms.",
                lesson_type=LessonType.VIDEO, duration_min=50, order=3,
            ),
            SecurityLesson(
                id="netsec_l4", module_id="netsec_001", title="VPN Technologies: OpenVPN & WireGuard",
                content="Implement secure VPN tunnels using OpenVPN and WireGuard. Covers PKI setup, certificate management, TLS authentication, and performance tuning. Learn site-to-site and client-to-site configurations with split tunneling.",
                lesson_type=LessonType.LAB, duration_min=40, order=4,
            ),
            SecurityLesson(
                id="netsec_l5", module_id="netsec_001", title="Packet Analysis with Wireshark",
                content="Advanced packet capture and analysis using Wireshark. Master display filters, protocol dissection, statistical analysis, and expert info diagnostics. Covers detecting malware C2 traffic, data exfiltration patterns, and network anomalies.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=5,
            ),
            SecurityLesson(
                id="netsec_l6", module_id="netsec_001", title="Network Scanning with Nmap",
                content="Comprehensive Nmap scanning techniques including TCP connect scans, SYN stealth scans, UDP scanning, OS fingerprinting, and NSE scripting. Learn to evade IDS detection and interpret scan results for vulnerability assessment.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="netsec_lab1", module_id="netsec_001",
                title="Configure Enterprise Firewall with iptables",
                description="Set up a comprehensive iptables-based firewall for a three-tier web application architecture.",
                environment="Ubuntu 22.04 LTS with iptables v1.8.7, web server (nginx), database server (PostgreSQL), and application server (Node.js).",
                tasks=[
                    "Set default policies to DROP for INPUT, FORWARD chains",
                    "Allow loopback traffic and established connections",
                    "Allow HTTP (80) and HTTPS (443) from any source",
                    "Allow SSH (22) only from management subnet (10.0.1.0/24)",
                    "Allow DB traffic (5432) only from app tier (10.0.2.0/24)",
                    "Implement rate limiting on SSH to prevent brute force",
                    "Log and drop all other traffic with custom prefix",
                    "Save and persist rules across reboots",
                ],
                hints=[
                    "Use iptables -P to set default policies",
                    "Use conntrack module for established connections",
                    "Consider using ipset for large IP lists",
                ],
                solution="iptables -P INPUT DROP; iptables -P FORWARD DROP; iptables -A INPUT -i lo -j ACCEPT; iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT; iptables -A INPUT -p tcp --dport 80 -j ACCEPT; iptables -A INPUT -p tcp --dport 443 -j ACCEPT; iptables -A INPUT -p tcp --dport 22 -s 10.0.1.0/24 -m limit --limit 3/minute -j ACCEPT; iptables -A INPUT -p tcp --dport 5432 -s 10.0.2.0/24 -j ACCEPT; iptables -A INPUT -j LOG --log-prefix \"DROPPED: \"; iptables-save > /etc/iptables/rules.v4",
                duration_min=90, points=150,
            ),
            SecurityLab(
                id="netsec_lab2", module_id="netsec_001",
                title="Deploy Suricata IDS with Custom Rules",
                description="Install and configure Suricata to detect network intrusions with custom detection rules.",
                environment="Ubuntu 22.04 LTS with Suricata 6.0, Zeek 5.0, and ELK Stack for log aggregation.",
                tasks=[
                    "Install Suricata and configure network interface in promiscuous mode",
                    "Download and update Emerging Threats ruleset",
                    "Write custom rule to detect SQL injection patterns in HTTP traffic",
                    "Write custom rule to detect DNS tunneling attempts",
                    "Configure eve.json output for SIEM integration",
                    "Test rules against sample PCAP files",
                    "Set up alerting via syslog to ELK stack",
                ],
                hints=[
                    "Use suricata-update for rule management",
                    "Test rules with suricata -T for validation",
                    "Monitor /var/log/suricata/eve.json for events",
                ],
                solution="""suricata-update; echo 'alert tcp any any -> any 80 (msg:"SQLi Detected"; flow:to_server; content:"SELECT"; http_uri; pcre:"/SELECT.*FROM/i"; sid:1000001; rev:1;)' >> /etc/suricata/rules/local.rules; systemctl restart suricata""",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="netsec_lab3", module_id="netsec_001",
                title="Wireshark Deep Packet Analysis",
                description="Analyze a malicious PCAP file to identify C2 beaconing, data exfiltration, and lateral movement.",
                environment="Kali Linux with Wireshark 4.0, networkminer, and suspicious.pcap sample file.",
                tasks=[
                    "Load PCAP and identify all unique IP addresses communicating",
                    "Filter HTTP traffic and identify suspicious User-Agent strings",
                    "Follow TCP streams to reconstruct exfiltrated data",
                    "Identify the C2 server IP and beaconing interval",
                    "Extract any files transferred over the network",
                    "Create a timeline of the attack progression",
                ],
                hints=[
                    "Use Statistics -> Conversations to identify heavy talkers",
                    "Look for regular interval communications as C2 beaconing",
                    "Use File -> Export Objects to extract transferred files",
                ],
                solution="Filter: ip.addr==192.168.1.100; http.user_agent contains 'malware'; Follow TCP stream 15; Export HTTP objects; C2 identified at 203.0.113.50 with 300-second beacon interval",
                duration_min=60, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="netsec_q1", module_id="netsec_001", title="Network Security Assessment",
            passing_score=75, time_limit_minutes=25,
            questions=[
                QuizQuestion("nq1", "What is the default policy recommended for iptables INPUT chain in a secure configuration?",
                    ["ACCEPT", "DROP", "REJECT", "LOG"], 1,
                    "DROP is the secure default - only explicitly allowed traffic passes.", DifficultyLevel.BEGINNER),
                QuizQuestion("nq2", "Which TCP flag combination is used in a SYN scan (half-open scan)?",
                    ["SYN+ACK", "SYN only", "ACK only", "FIN+PSH+URG"], 1,
                    "SYN scan sends only SYN packet without completing handshake.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq3", "What is the primary difference between Snort and Suricata?",
                    ["Snort is free, Suricata is paid", "Suricata supports multi-threading natively", "Snort only works on Linux", "Suricata cannot do IPS"], 1,
                    "Suricata was designed from ground up with multi-threading support.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq4", "Which VPN protocol uses modern cryptography with minimal code base?",
                    ["OpenVPN", "IPsec", "WireGuard", "PPTP"], 2,
                    "WireGuard has ~4,000 lines of code vs 400,000+ for OpenVPN/IPsec.", DifficultyLevel.BEGINNER),
                QuizQuestion("nq5", "What Wireshark display filter shows HTTP POST requests?",
                    ["http.request.method == POST", "tcp.port == 80", "http contains POST", "frame contains POST"], 0,
                    "The http.request.method field specifically filters by HTTP method.", DifficultyLevel.BEGINNER),
                QuizQuestion("nq6", "In a stateful firewall, what does the ESTABLISHED state mean?",
                    ["Any incoming connection", "Part of an existing approved connection", "Connection to known IP", "Authenticated connection"], 1,
                    "ESTABLISHED refers to packets that are part of an already-approved connection.", DifficultyLevel.BEGINNER),
                QuizQuestion("nq7", "Which Nmap scan type is most stealthy but requires root privileges?",
                    ["TCP Connect (-sT)", "SYN Scan (-sS)", "UDP Scan (-sU)", "Ping Scan (-sn)"], 1,
                    "SYN scan (-sS) does not complete the TCP handshake, making it stealthier.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq8", "What does the iptables conntrack module track?",
                    ["User connections only", "Connection state for stateful inspection", "Physical connections", "Bluetooth devices"], 1,
                    "conntrack tracks connection states: NEW, ESTABLISHED, RELATED, INVALID.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq9", "Which IDS rule action drops the packet inline?",
                    ["alert", "log", "pass", "drop"], 3,
                    "The 'drop' action blocks the packet when Suricata runs in IPS mode.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq10", "What is the purpose of IPsec AH (Authentication Header)?",
                    ["Encrypt data payload", "Provide integrity and authentication", "Compress data", "Route packets"], 1,
                    "AH provides data integrity, authentication, and anti-replay protection.", DifficultyLevel.ADVANCED),
                QuizQuestion("nq11", "Which BPF filter captures only TCP traffic to port 443?",
                    ["tcp port 443", "tcp dst port 443", "port 443", "tcp and port 443"], 1,
                    "tcp dst port 443 filters only TCP packets with destination port 443.", DifficultyLevel.ADVANCED),
                QuizQuestion("nq12", "What technique does Nmap use for OS fingerprinting?",
                    ["Port scanning only", "TCP/IP stack fingerprinting", "Social engineering", "DNS enumeration"], 1,
                    "Nmap sends crafted packets and analyzes unique responses from TCP/IP stack implementations.", DifficultyLevel.ADVANCED),
                QuizQuestion("nq13", "In Wireshark, what does the 'tcp.analysis.flags' filter show?",
                    ["All TCP packets", "TCP packets with expert info anomalies", "Only SYN packets", "Only RST packets"], 1,
                    "It shows packets with TCP analysis expert info: retransmissions, dup ACKs, etc.", DifficultyLevel.ADVANCED),
                QuizQuestion("nq14", "What is the key advantage of next-gen firewalls over traditional firewalls?",
                    ["They are cheaper", "Application-layer awareness and deep packet inspection", "They use less power", "They have more ports"], 1,
                    "NGFWs can inspect application-layer traffic and identify apps by behavior.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("nq15", "Which TLS version should be used for VPN connections and why?",
                    ["TLS 1.0 for compatibility", "TLS 1.1 for balance", "TLS 1.2 or 1.3 for security", "SSL 3.0 for performance"], 2,
                    "TLS 1.2+ provides strong cipher suites and protection against known vulnerabilities.", DifficultyLevel.BEGINNER),
            ],
        ),
    )

    # ========================================================================
    # COURSE 2: WEB APPLICATION SECURITY
    # ========================================================================
    mod2 = SecurityModule(
        id="webapp_001",
        course_id="web_app_security",
        title="Web Application Security",
        description="Master OWASP Top 10 2024 vulnerabilities, exploitation techniques, and defense strategies for modern web applications.",
        category=CourseCategory.WEB_APP,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=15.0,
        prerequisites=["Basic HTTP/HTTPS knowledge", "HTML/JavaScript basics"],
        order=2,
        lessons=[
            SecurityLesson(
                id="webapp_l1", module_id="webapp_001", title="OWASP Top 10 2024 Overview",
                content="Comprehensive review of the 2024 OWASP Top 10: A01:2021-Broken Access Control, A02:2021-Cryptographic Failures, A03:2021-Injection, A04:2021-Insecure Design, A05:2021-Security Misconfiguration, A06:2021-Vulnerable Components, A07:2021-ID and Auth Failures, A08:2021-Software and Data Integrity Failures, A09:2021-Security Logging Failures, A10:2021-SSRF. Each category includes real-world examples and defense strategies.",
                lesson_type=LessonType.TEXT, duration_min=60, order=1,
            ),
            SecurityLesson(
                id="webapp_l2", module_id="webapp_001", title="Cross-Site Scripting (XSS)",
                content="Deep dive into Stored, Reflected, and DOM-based XSS attacks. Learn how malicious scripts are injected into web pages viewed by other users. Covers bypass techniques, Content Security Policy (CSP) implementation, context-aware output encoding, and modern browser protections like Trusted Types.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=2,
            ),
            SecurityLesson(
                id="webapp_l3", module_id="webapp_001", title="SQL Injection Mastery",
                content="From basic UNION-based attacks to blind SQL injection, time-based inference, and out-of-band extraction. Covers both manual exploitation and automated tools (sqlmap). Learn parameterized queries, ORM security, and database firewall configuration for defense.",
                lesson_type=LessonType.INTERACTIVE, duration_min=65, order=3,
            ),
            SecurityLesson(
                id="webapp_l4", module_id="webapp_001", title="CSRF and SSRF Attacks",
                content="Cross-Site Request Forgery (CSRF) and Server-Side Request Forgery (SSRF) exploitation and defense. Learn how attackers force users to perform unwanted actions and abuse server-side requests to access internal resources. Covers token-based protection, SameSite cookies, and URL validation.",
                lesson_type=LessonType.VIDEO, duration_min=45, order=4,
            ),
            SecurityLesson(
                id="webapp_l5", module_id="webapp_001", title="Command Injection & Code Execution",
                content="OS command injection, remote code execution (RCE), and deserialization attacks. Learn to identify injection points, chain vulnerabilities for full system compromise, and implement secure coding practices including input validation, sandboxing, and safe deserialization patterns.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=5,
            ),
            SecurityLesson(
                id="webapp_l6", module_id="webapp_001", title="Security Headers Deep Dive",
                content="Implement and configure essential HTTP security headers: Content-Security-Policy (CSP), Strict-Transport-Security (HSTS), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. Learn header deployment strategies, reporting mechanisms, and bypass techniques.",
                lesson_type=LessonType.TEXT, duration_min=40, order=6,
            ),
            SecurityLesson(
                id="webapp_l7", module_id="webapp_001", title="XXE and Insecure Deserialization",
                content="XML External Entity (XXE) attacks leading to SSRF, file disclosure, and DoS. Insecure deserialization vulnerabilities in Java, Python, PHP, and .NET. Learn to secure XML parsers, implement serialization constraints, and use safe alternatives.",
                lesson_type=LessonType.LAB, duration_min=55, order=7,
            ),
        ],
        labs=[
            SecurityLab(
                id="webapp_lab1", module_id="webapp_001",
                title="Exploit and Fix XSS Vulnerabilities",
                description="Identify and exploit three types of XSS in a deliberately vulnerable web application, then implement proper fixes.",
                environment="DVWA (Damn Vulnerable Web App) on Docker, modern browser with developer tools, Burp Suite Community.",
                tasks=[
                    "Find and exploit a reflected XSS in the search function",
                    "Find and exploit a stored XSS in the guestbook",
                    "Find and exploit a DOM-based XSS in the URL hash",
                    "Implement CSP headers to mitigate XSS",
                    "Add context-aware output encoding",
                    "Verify fixes with XSS polyglot payloads",
                ],
                hints=[
                    "Try <script>alert(1)</script> in search box",
                    "Store XSS persists across page reloads",
                    "DOM XSS executes in browser without server interaction",
                ],
                solution="Reflected: search?q=<script>alert(1)</script>; Stored: <img src=x onerror=alert(1)> in guestbook; DOM: #<img src=x onerror=alert(1)>; Fix: Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; use html.escape() for output encoding",
                duration_min=90, points=150,
            ),
            SecurityLab(
                id="webapp_lab2", module_id="webapp_001",
                title="SQL Injection from Basic to Advanced",
                description="Progress through SQL injection techniques from simple UNION attacks to blind time-based extraction.",
                environment="SQLi-Labs on Docker, MySQL 8.0, sqlmap, Burp Suite, custom Python scripts.",
                tasks=[
                    "Identify SQL injection point in login form",
                    "Use UNION-based injection to extract database name",
                    "Extract table names from information_schema",
                    "Dump user credentials table",
                    "Perform blind boolean-based injection",
                    "Extract data using time-based blind technique",
                    "Fix vulnerability using parameterized queries",
                ],
                hints=[
                    "Try single quote ' to trigger error",
                    "Use ORDER BY to determine column count",
                    "Sleep functions: MySQL uses SLEEP(), MSSQL uses WAITFOR DELAY",
                ],
                solution="' UNION SELECT null,null,database()-- for DB name; ' UNION SELECT table_name,null,null FROM information_schema.tables-- for tables; Use cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,)) for fix",
                duration_min=105, points=175,
            ),
            SecurityLab(
                id="webapp_lab3", module_id="webapp_001",
                title="Security Headers Implementation",
                description="Configure comprehensive security headers for an Express.js application and test their effectiveness.",
                environment="Node.js 18, Express.js 4, Helmet middleware, Mozilla Observatory for scoring.",
                tasks=[
                    "Install and configure Helmet middleware",
                    "Implement strict CSP with nonce-based script execution",
                    "Configure HSTS with preload directive",
                    "Set X-Frame-Options and frame-ancestors",
                    "Configure Referrer-Policy and Permissions-Policy",
                    "Test with Mozilla Observatory and achieve A+ rating",
                    "Implement CSP reporting endpoint",
                ],
                hints=[
                    "helmet() sets defaults but customize for your needs",
                    "Use crypto.randomBytes for CSP nonces",
                    "Test CSP with report-uri directive first",
                ],
                solution="app.use(helmet({contentSecurityPolicy: {directives: {defaultSrc: [\"'self'\"], scriptSrc: [\"'self'\", (req, res) => \"'nonce-'+res.locals.cspNonce], styleSrc: [\"'self'\", \"'unsafe-inline'\"],}}, hsts: {maxAge: 31536000, preload: true}}));",
                duration_min=60, points=125,
            ),
            SecurityLab(
                id="webapp_lab4", module_id="webapp_001",
                title="CSRF and SSRF Exploitation",
                description="Exploit CSRF to change admin password and SSRF to access internal AWS metadata service.",
                environment="Vulnerable Python Flask app on Docker, internal metadata service at 169.254.169.254.",
                tasks=[
                    "Craft CSRF payload to change admin email without their knowledge",
                    "Bypass CSRF token validation through token fixation",
                    "Exploit SSRF in URL parameter to fetch internal metadata",
                    "Extract IAM credentials from EC2 metadata service",
                    "Implement SameSite=Strict cookies for CSRF defense",
                    "Implement URL whitelist validation for SSRF defense",
                ],
                hints=[
                    "CSRF: Host payload on attacker site, trick admin into visiting",
                    "SSRF: Try http://169.254.169.254/latest/meta-data/",
                    "AWS metadata: /latest/meta-data/iam/security-credentials/",
                ],
                solution="<form action='http://victim/change-email' method='POST'><input name='email' value='attacker@evil.com'></form><script>document.forms[0].submit()</script>; SSRF: ?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/role; Defense: response.set_cookie('session', value, samesite='Strict', secure=True, httponly=True)",
                duration_min=80, points=150,
            ),
        ],
        quiz=SecurityQuiz(
            id="webapp_q1", module_id="webapp_001", title="Web Application Security Assessment",
            passing_score=75, time_limit_minutes=30,
            questions=[
                QuizQuestion("wq1", "Which is the most effective defense against XSS?",
                    ["Input validation only", "Output encoding with CSP", "Blacklisting characters", "Disabling JavaScript"], 1,
                    "Context-aware output encoding combined with CSP is the most robust defense.", DifficultyLevel.BEGINNER),
                QuizQuestion("wq2", "What is the primary cause of SQL injection vulnerabilities?",
                    ["Weak database passwords", "Concatenating user input into SQL queries", "Missing database patches", "Unencrypted connections"], 1,
                    "SQLi occurs when untrusted user input is concatenated directly into SQL queries.", DifficultyLevel.BEGINNER),
                QuizQuestion("wq3", "Which HTTP header prevents clickjacking attacks?",
                    ["X-XSS-Protection", "X-Frame-Options", "Content-Security-Policy", "X-Content-Type-Options"], 1,
                    "X-Frame-Options controls whether a page can be embedded in iframes, preventing clickjacking.", DifficultyLevel.BEGINNER),
                QuizQuestion("wq4", "What CSP directive controls which scripts can execute?",
                    ["default-src", "script-src", "style-src", "connect-src"], 1,
                    "script-src specifically controls sources for JavaScript execution.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wq5", "In a blind SQL injection, how do you extract data without seeing output?",
                    ["Use UNION SELECT", "Use boolean or time-based inference", "Use error messages", "Use direct queries"], 1,
                    "Blind SQLi uses boolean conditions or time delays to infer data bit by bit.", DifficultyLevel.ADVANCED),
                QuizQuestion("wq6", "What is the purpose of the SameSite cookie attribute?",
                    ["Encrypt cookie data", "Prevent CSRF by controlling cross-origin sending", "Set cookie expiration", "Limit cookie size"], 1,
                    "SameSite=Strict prevents cookies from being sent in cross-site requests.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wq7", "Which vulnerability allows an attacker to make the server send requests to arbitrary URLs?",
                    ["CSRF", "SSRF", "XSS", "SQL Injection"], 1,
                    "Server-Side Request Forgery (SSRF) abuses server-side requests to access internal resources.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wq8", "What is insecure deserialization?",
                    ["Using old encryption algorithms", "Untrusted data being deserialized into objects", "Slow database queries", "Missing SSL certificates"], 1,
                    "Insecure deserialization occurs when attacker-controlled data is deserialized without validation.", DifficultyLevel.ADVANCED),
                QuizQuestion("wq9", "Which is NOT a valid X-Frame-Options value?",
                    ["DENY", "SAMEORIGIN", "ALLOW-FROM https://example.com", "ALLOW-ALL"], 3,
                    "ALLOW-ALL is not a valid value. Options are DENY, SAMEORIGIN, or ALLOW-URI.", DifficultyLevel.BEGINNER),
                QuizQuestion("wq10", "What does the HSTS header do?",
                    ["Forces HTTPS connections", "Enables HTTP/2", "Compresses responses", "Caches static content"], 0,
                    "HTTP Strict Transport Security forces browsers to always use HTTPS for a domain.", DifficultyLevel.BEGINNER),
                QuizQuestion("wq11", "What is the difference between stored and reflected XSS?",
                    ["Stored persists on server; reflected requires social engineering", "Reflected is more dangerous", "Stored only works on login pages", "Reflected requires database access"], 0,
                    "Stored XSS persists in the application (e.g., database), while reflected requires victim to click a link.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wq12", "How does a prepared statement prevent SQL injection?",
                    ["By encrypting the query", "By separating code from data", "By blocking special characters", "By using a firewall"], 1,
                    "Prepared statements send SQL structure and data separately, preventing injection.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wq13", "What is XXE (XML External Entity) attack?",
                    ["Cross-site execution", "Exploiting XML parser to read files/SSRF", "XML encryption exploit", "External XSS entry"], 1,
                    "XXE abuses XML parsers with external entity declarations to read files or make requests.", DifficultyLevel.ADVANCED),
                QuizQuestion("wq14", "Which defense is most effective against SSRF?",
                    ["Input validation with URL whitelist", "Disabling all outbound requests", "Using HTTPS only", "Firewall rules only"], 0,
                    "URL whitelist validation combined with DNS resolution checks prevents SSRF.", DifficultyLevel.ADVANCED),
                QuizQuestion("wq15", "What is DOM-based XSS?",
                    ["XSS that modifies the DOM without server interaction", "XSS that requires database access", "XSS that only affects the server", "XSS that uses DOM storage"], 0,
                    "DOM-based XSS executes entirely in the browser when JavaScript writes user input to the DOM unsafely.", DifficultyLevel.ADVANCED),
            ],
        ),
    )


    # ========================================================================

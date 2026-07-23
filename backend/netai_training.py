#!/usr/bin/env python3
"""Luqi AI NetAI Training Module — Network & AI Engineering Training Platform.
3-phase curriculum (CCNA to CCNP to CCIE), virtual device simulation,
packet tracing, topology generation, AI mentoring, quizzes, progress tracking,
leaderboards, and certificate generation.
"""

import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  IN-MEMORY STORES
# ═══════════════════════════════════════════════════════════════════════════════

_lab_sessions: Dict[str, Dict[str, Any]] = {}
_mentor_history: Dict[str, List[Dict[str, Any]]] = {}
_progress: Dict[str, Dict[str, Any]] = {}
_certificates: Dict[str, Dict[str, Any]] = {}
_leaderboard: List[Dict[str, Any]] = []

# ═══════════════════════════════════════════════════════════════════════════════
#  CURRICULUM DATA
# ═══════════════════════════════════════════════════════════════════════════════

CURRICULUM = {
    "phases": [
        {
            "id": "phase_1_ccna",
            "name": "Phase 1: CCNA — Cisco Certified Network Associate",
            "description": "Foundational networking concepts, routing, switching, and basic security.",
            "duration_weeks": 12,
            "modules": [
                {"id": "p1m1", "name": "Network Fundamentals", "topics": ["OSI Model", "TCP/IP", "Ethernet", "IP Addressing", "Subnetting"]},
                {"id": "p1m2", "name": "Network Access", "topics": ["Layer 2 Switching", "VLANs", "Trunking", "STP", "EtherChannel"]},
                {"id": "p1m3", "name": "IP Connectivity", "topics": ["Static Routing", "OSPF", "EIGRP", "BGP Basics", "Route Redistribution"]},
                {"id": "p1m4", "name": "IP Services", "topics": ["DHCP", "DNS", "NAT", "SNMP", "Syslog", "NTP"]},
                {"id": "p1m5", "name": "Security Fundamentals", "topics": ["ACLs", "Port Security", "DHCP Snooping", "DAI", "VPN Concepts"]},
                {"id": "p1m6", "name": "Automation & Programmability", "topics": ["REST API", "Python for Networking", "Ansible", "Netconf/YANG", "SDN"]},
            ],
        },
        {
            "id": "phase_2_ccnp",
            "name": "Phase 2: CCNP — Cisco Certified Network Professional",
            "description": "Advanced routing, switching, troubleshooting, and enterprise network design.",
            "duration_weeks": 16,
            "modules": [
                {"id": "p2m1", "name": "Advanced Routing", "topics": ["OSPFv3", "EIGRPv6", "BGP Path Selection", "MP-BGP", "Policy Routing"]},
                {"id": "p2m2", "name": "Advanced Switching", "topics": ["VTP", "Private VLANs", "MST", "SPAN/RSPAN", "Layer 3 Switching"]},
                {"id": "p2m3", "name": "Troubleshooting", "topics": ["Structured Troubleshooting", "Layer 1-3 Issues", "Routing Problems", "Spanning Tree Issues"]},
                {"id": "p2m4", "name": "Network Design", "topics": ["Hierarchical Design", "Campus Architecture", "WAN Design", "High Availability", "QoS Design"]},
                {"id": "p2m5", "name": "Network Security", "topics": ["Firewall Technologies", "IDS/IPS", "802.1X", "Network Access Control", "Segmentation"]},
                {"id": "p2m6", "name": "VPN Technologies", "topics": ["IPsec", "DMVPN", "GETVPN", "SSL VPN", "MPLS L3VPN"]},
            ],
        },
        {
            "id": "phase_3_ccie",
            "name": "Phase 3: CCIE — Cisco Certified Internetwork Expert",
            "description": "Expert-level network engineering, complex troubleshooting, and architecture.",
            "duration_weeks": 24,
            "modules": [
                {"id": "p3m1", "name": "Advanced BGP", "topics": ["BGP Confederations", "Route Reflectors", "BGP Communities", "Multihoming", "Inter-AS"]},
                {"id": "p3m2", "name": "MPLS & Segment Routing", "topics": ["MPLS Fundamentals", "LDP", "RSVP-TE", "Segment Routing", "SRv6"]},
                {"id": "p3m3", "name": "Network Automation", "topics": ["Python Advanced", "Netmiko", "NAPALM", "Nornir", "Terraform for Network"]},
                {"id": "p3m4", "name": "Cloud Networking", "topics": ["AWS VPC", "Azure VNet", "GCP VPC", "Hybrid Cloud", "Cloud WAN"]},
                {"id": "p3m5", "name": "Advanced Troubleshooting", "topics": ["Complex Scenarios", "Performance Issues", "Security Incidents", "Protocol Analysis"]},
                {"id": "p3m6", "name": "Network Architecture", "topics": ["Enterprise Architecture", "SASE", "Zero Trust", "Intent-Based Networking", "DNA Center"]},
            ],
        },
    ],
    "tracks": [
        {"id": "enterprise", "name": "Enterprise Networking", "description": "Core routing, switching, and network management for large organizations."},
        {"id": "security", "name": "Network Security", "description": "Firewalls, VPNs, IDS/IPS, and zero-trust architectures."},
        {"id": "automation", "name": "Network Automation", "description": "Programmable networks, Python, Ansible, and cloud integration."},
        {"id": "datacenter", "name": "Data Center", "description": "VXLAN, EVPN, spine-leaf architectures, and SDN."},
        {"id": "collaboration", "name": "Collaboration", "description": "Voice, video, and unified communications over IP networks."},
    ],
}

LABS = [
    {"id": "lab_001", "name": "Basic VLAN Configuration", "difficulty": "beginner", "topic": "switching", "duration_min": 30, "description": "Configure VLANs, trunk ports, and inter-VLAN routing."},
    {"id": "lab_002", "name": "OSPF Single Area", "difficulty": "beginner", "topic": "routing", "duration_min": 45, "description": "Set up OSPF in a single area with proper router IDs."},
    {"id": "lab_003", "name": "ACL Configuration", "difficulty": "beginner", "topic": "security", "duration_min": 30, "description": "Implement standard and extended ACLs for traffic filtering."},
    {"id": "lab_004", "name": "BGP Peering", "difficulty": "intermediate", "topic": "routing", "duration_min": 60, "description": "Establish eBGP and iBGP peer sessions with route policies."},
    {"id": "lab_005", "name": "MPLS L3VPN", "difficulty": "advanced", "topic": "mpls", "duration_min": 90, "description": "Configure MPLS core with VRF-based customer VPNs."},
    {"id": "lab_006", "name": "Network Automation with Python", "difficulty": "intermediate", "topic": "automation", "duration_min": 60, "description": "Use Python and Netmiko to automate device configurations."},
    {"id": "lab_007", "name": "DMVPN Deployment", "difficulty": "advanced", "topic": "vpn", "duration_min": 75, "description": "Deploy a Dynamic Multipoint VPN with NHRP and IPsec."},
    {"id": "lab_008", "name": "Troubleshooting OSPF", "difficulty": "intermediate", "topic": "troubleshooting", "duration_min": 45, "description": "Diagnose and resolve common OSPF neighbor and routing issues."},
]

CONCEPT_EXPLANATIONS = {
    "osi_model": {
        "title": "OSI Model",
        "beginner": "The OSI Model has 7 layers: Physical (cables), Data Link (switches), Network (routers), Transport (TCP/UDP), Session, Presentation, and Application (HTTP, email). Think of it like sending a letter through the postal system.",
        "intermediate": "The OSI (Open Systems Interconnection) model is a conceptual framework with 7 layers. Each layer serves the layer above it. Layer 2 uses MAC addresses, Layer 3 uses IP addresses, Layer 4 handles port numbers for process-to-process delivery.",
        "advanced": "The OSI model provides a modular framework for network protocol design. Key implementations: Layer 2 (Ethernet II, 802.1Q), Layer 3 (IPv4/IPv6, ICMP), Layer 4 (TCP with windowing/sequencing, UDP). Understanding encapsulation/de-encapsulation at each layer is critical for protocol analysis and troubleshooting.",
    },
    "ospf": {
        "title": "OSPF (Open Shortest Path First)",
        "beginner": "OSPF is a routing protocol that finds the best path through a network. It uses 'cost' based on bandwidth. It's faster and more efficient than RIP.",
        "intermediate": "OSPF is a link-state IGP using Dijkstra's SPF algorithm. It maintains the LSDB (Link-State Database) and computes the SPT (Shortest Path Tree). Areas reduce LSA flooding: Area 0 is the backbone. Router types: Internal, ABR, ASBR.",
        "advanced": "OSPFv2 (IPv4) and OSPFv3 (IPv6) use hierarchical area design. Key concepts: LSA types (1-7), neighbor states (Down → Init → 2-Way → ExStart → Exchange → Loading → Full), network types (Broadcast, P2P, NBMA), and area types (Stub, Totally Stubby, NSSA). Optimization includes summarization, virtual links, and fast convergence tuning.",
    },
    "bgp": {
        "title": "BGP (Border Gateway Protocol)",
        "beginner": "BGP is the protocol that routes traffic between different organizations on the Internet. It connects autonomous systems (AS) using path attributes.",
        "intermediate": "BGP is a path-vector EGP. Key attributes: AS_PATH, NEXT_HOP, LOCAL_PREF, MED. iBGP requires full mesh or route reflectors. eBGP peers between different ASes. Best path selection follows a 13-step algorithm.",
        "advanced": "BGP is the Internet's routing protocol. Advanced topics: BGP communities for policy, confederations for large ASes, MP-BGP for MPLS VPNs (AFI/SAFI), BGP convergence optimization (prefix-independent convergence), flowspec for DDoS mitigation, and BGP in SD-WAN deployments.",
    },
    "mpls": {
        "title": "MPLS (Multiprotocol Label Switching)",
        "beginner": "MPLS is a technique to speed up network traffic by using short labels instead of long IP lookups. It creates virtual paths through the network.",
        "intermediate": "MPLS operates between Layer 2 and Layer 3 (Layer 2.5). Components: LSR (Label Switch Router), LER (Label Edge Router), LDP (Label Distribution Protocol). Applications: L3VPN (BGP/MPLS IP VPN), L2VPN (VPWS/VPLS), and TE (Traffic Engineering).",
        "advanced": "MPLS architecture includes the control plane (LDP, RSVP-TE, BGP) and data plane (label switching). Advanced: Segment Routing replaces LDP/RSVP with source routing, SR-MPLS and SRv6, EVPN for multi-service VPNs, and MPLS-in-UDP for data center interconnects.",
    },
    "vlan": {
        "title": "VLAN (Virtual LAN)",
        "beginner": "A VLAN splits one physical switch into multiple virtual networks. Devices in the same VLAN can talk to each other, but need a router to talk to other VLANs.",
        "intermediate": "VLANs provide Layer 2 segmentation. 802.1Q tagging adds a 4-byte tag with VLAN ID (1-4094). Trunk ports carry multiple VLANs. Native VLAN is untagged. Inter-VLAN routing requires a Layer 3 device (router-on-a-stick or SVI).",
        "advanced": "Advanced VLAN concepts: Private VLANs (primary, community, isolated ports), VLAN mapping (translation), QinQ (double tagging), MAC-based VLANs, and protocol-based VLANs. Integration with VXLAN for data center overlay networks.",
    },
    "subnetting": {
        "title": "IP Subnetting",
        "beginner": "Subnetting divides a network into smaller parts. Like dividing a building into floors and rooms. It helps organize devices and save IP addresses.",
        "intermediate": "Subnetting borrows bits from the host portion to create subnets. CIDR notation (e.g., /24) indicates the number of network bits. Formula: subnets = 2^n, hosts = 2^h - 2. VLSM allows different subnet sizes within the same network.",
        "advanced": "Advanced subnetting: Variable Length Subnet Masking (VLSM) for efficient allocation, summarization for reduced routing table size, IPv6 subnetting (/64 prefix for LANs), and subnetting in cloud environments (AWS VPC subnets, Azure VNets).",
    },
}

QUIZZES = {
    "p1m1": {
        "title": "Network Fundamentals Quiz",
        "questions": [
            {"q": "Which layer of the OSI model handles IP addressing?", "options": ["Layer 2", "Layer 3", "Layer 4", "Layer 7"], "correct": 1},
            {"q": "What is the default subnet mask for a Class C network?", "options": ["255.0.0.0", "255.255.0.0", "255.255.255.0", "255.255.255.255"], "correct": 2},
            {"q": "Which protocol is connectionless?", "options": ["TCP", "HTTP", "UDP", "FTP"], "correct": 2},
        ],
    },
    "p1m2": {
        "title": "Network Access Quiz",
        "questions": [
            {"q": "What does VLAN stand for?", "options": ["Virtual LAN", "Volume LAN", "Variable LAN", "Virtual Link"], "correct": 0},
            {"q": "Which protocol prevents Layer 2 loops?", "options": ["OSPF", "BGP", "STP", "VTP"], "correct": 2},
            {"q": "What is the purpose of trunking?", "options": ["To connect switches carrying multiple VLANs", "To prevent loops", "To encrypt traffic", "To assign IP addresses"], "correct": 0},
        ],
    },
    "p2m1": {
        "title": "Advanced Routing Quiz",
        "questions": [
            {"q": "Which BGP attribute is used first in best path selection?", "options": ["MED", "LOCAL_PREF", "Weight", "AS_PATH"], "correct": 2},
            {"q": "What is the OSPF router type that connects to Area 0?", "options": ["Internal", "ABR", "ASBR", "Backbone"], "correct": 1},
        ],
    },
}

# Mentor responses
MENTOR_RESPONSES = {
    "encouragement": [
        "You're making great progress! Keep pushing forward.",
        "Networking is a journey, not a destination. Every lab counts!",
        "Don't give up — even CCIEs started with the OSI model.",
        "Your dedication to learning will pay off. Stay consistent!",
    ],
    "study_tips": [
        "Try drawing network diagrams by hand — it helps with retention.",
        "Use packet capture tools like Wireshark to see protocols in action.",
        "Build a home lab with GNS3 or EVE-NG for hands-on practice.",
        "Teach what you learn to someone else — it reinforces your knowledge.",
        "Focus on understanding concepts, not just memorizing commands.",
    ],
    "career": [
        "Network engineers with automation skills are in high demand.",
        "Consider specializing in cloud networking — AWS, Azure, GCP.",
        "Get hands-on experience through internships or volunteer projects.",
        "Join networking communities like Cisco Learning Network.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_curriculum() -> Dict[str, Any]:
    """Retrieve the full Network & AI Engineering training curriculum."""
    return {
        "status": "success",
        "total_phases": len(CURRICULUM["phases"]),
        "total_tracks": len(CURRICULUM["tracks"]),
        **CURRICULUM,
    }


def get_phase(phase_id: str) -> Dict[str, Any]:
    """Retrieve details for a specific training phase by its ID."""
    for phase in CURRICULUM["phases"]:
        if phase["id"] == phase_id:
            return {"status": "success", "phase": phase}
    return {"status": "not_found", "message": f"Phase '{phase_id}' not found. Available: {[p['id'] for p in CURRICULUM['phases']]}."}


def get_module(module_id: str) -> Dict[str, Any]:
    """Retrieve a specific module within a training phase."""
    for phase in CURRICULUM["phases"]:
        for module in phase["modules"]:
            if module["id"] == module_id:
                return {"status": "success", "phase": phase["name"], "module": module}
    return {"status": "not_found", "message": f"Module '{module_id}' not found."}


def explain_concept(concept: str, level: str = "intermediate") -> Dict[str, Any]:
    """Get an AI-generated explanation of a network or AI concept at a given level."""
    concept = concept.lower().replace(" ", "_")
    if concept not in CONCEPT_EXPLANATIONS:
        available = list(CONCEPT_EXPLANATIONS.keys())
        return {"status": "available_concepts", "concepts": available, "message": f"Concept '{concept}' not found."}
    
    explanation = CONCEPT_EXPLANATIONS[concept]
    level = level.lower()
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "intermediate"
    
    return {
        "status": "success",
        "concept": explanation["title"],
        "level": level,
        "explanation": explanation[level],
        "related_concepts": list(CONCEPT_EXPLANATIONS.keys())[:5],
    }


def list_labs(filters: str = "", difficulty: str = "", topic: str = "") -> Dict[str, Any]:
    """List all available hands-on labs, optionally filtered."""
    filtered_labs = LABS.copy()
    
    if difficulty:
        filtered_labs = [l for l in filtered_labs if l["difficulty"] == difficulty.lower()]
    if topic:
        filtered_labs = [l for l in filtered_labs if topic.lower() in l["topic"].lower()]
    
    return {
        "status": "success",
        "total": len(filtered_labs),
        "filters_applied": {"difficulty": difficulty, "topic": topic},
        "labs": filtered_labs,
    }


def start_lab(student_id: str, lab_id: str) -> Dict[str, Any]:
    """Start a new lab session for a student."""
    lab = next((l for l in LABS if l["id"] == lab_id), None)
    if not lab:
        return {"status": "not_found", "message": f"Lab '{lab_id}' not found."}
    
    session_id = f"sess_{student_id}_{lab_id}_{int(time.time())}"
    _lab_sessions[session_id] = {
        "session_id": session_id,
        "student_id": student_id,
        "lab_id": lab_id,
        "lab_name": lab["name"],
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "hints_used": 0,
        "submission": None,
        "score": None,
    }
    
    return {
        "status": "success",
        "session_id": session_id,
        "lab": lab,
        "instructions": f"Complete the '{lab['name']}' lab. Submit your configuration when ready.",
    }


def get_lab_status(session_id: str) -> Dict[str, Any]:
    """Get the current status of an active lab session."""
    if session_id not in _lab_sessions:
        return {"status": "not_found", "message": f"Session '{session_id}' not found."}
    return {"status": "success", "session": _lab_sessions[session_id]}


def submit_lab(session_id: str, submission: Dict[str, Any] = None) -> Dict[str, Any]:
    """Submit a completed lab for grading and feedback."""
    if session_id not in _lab_sessions:
        return {"status": "not_found", "message": f"Session '{session_id}' not found."}
    
    session = _lab_sessions[session_id]
    session["submission"] = submission
    session["completed_at"] = datetime.utcnow().isoformat()
    
    # Auto-grade (simulated)
    score = random.randint(60, 100)
    session["score"] = score
    session["status"] = "completed"
    
    # Update progress
    student_id = session["student_id"]
    if student_id not in _progress:
        _progress[student_id] = {"labs_completed": 0, "total_score": 0, "quizzes_taken": 0}
    _progress[student_id]["labs_completed"] += 1
    _progress[student_id]["total_score"] += score
    
    return {
        "status": "success",
        "session_id": session_id,
        "score": score,
        "passed": score >= 70,
        "feedback": "Good work! Review any missed configurations and try the next lab." if score >= 70 else "Keep practicing. Focus on the configuration details.",
    }


def get_hint(session_id: str, hint_level: int = 1) -> Dict[str, Any]:
    """Request a hint for the current lab session at a specified level."""
    if session_id not in _lab_sessions:
        return {"status": "not_found", "message": f"Session '{session_id}' not found."}
    
    session = _lab_sessions[session_id]
    session["hints_used"] += 1
    
    hints = [
        "Hint 1: Check your interface configurations first.",
        "Hint 2: Verify IP addressing and subnet masks.",
        "Hint 3: Check routing table entries with 'show ip route'.",
        "Hint 4: Use 'ping' and 'traceroute' to test connectivity.",
        "Hint 5: Review ACL direction — inbound vs outbound.",
    ]
    
    hint_index = min(hint_level - 1, len(hints) - 1)
    return {
        "status": "success",
        "hint": hints[hint_index],
        "hints_used": session["hints_used"],
        "penalty": f"-{session['hints_used'] * 5} points from final score",
    }


def reset_lab(session_id: str) -> Dict[str, Any]:
    """Reset a lab session to its initial state."""
    if session_id not in _lab_sessions:
        return {"status": "not_found", "message": f"Session '{session_id}' not found."}
    
    session = _lab_sessions[session_id]
    session["status"] = "active"
    session["started_at"] = datetime.utcnow().isoformat()
    session["completed_at"] = None
    session["hints_used"] = 0
    session["submission"] = None
    session["score"] = None
    
    return {"status": "success", "message": "Lab session reset. Start fresh!"}


def generate_topology(prompt: str, platform: str = "cisco") -> Dict[str, Any]:
    """Generate a network topology from a natural language prompt."""
    topology_types = {
        "star": {"description": "All devices connect to a central hub/switch", "devices": ["Core Switch", "Access Switch x3", "Router"], "use_case": "Small office networks"},
        "mesh": {"description": "Every device connects to every other device", "devices": ["Router x4"], "use_case": "High-availability WANs"},
        "spine_leaf": {"description": "Two-layer topology for data centers", "devices": ["Spine Switch x2", "Leaf Switch x4", "Server x8"], "use_case": "Modern data centers"},
        "bus": {"description": "All devices connect to a single cable", "devices": ["Terminator x2", "T-connector x5"], "use_case": "Legacy networks"},
        "ring": {"description": "Devices form a closed loop", "devices": ["Switch x6"], "use_case": "MAN networks, Resilient networks"},
    }
    
    # Simple keyword matching
    matched_type = "star"
    for t in topology_types:
        if t.replace("_", " ") in prompt.lower() or t in prompt.lower():
            matched_type = t
            break
    
    topo = topology_types[matched_type]
    topology_id = f"topo_{int(time.time())}_{random.randint(1000, 9999)}"
    
    return {
        "status": "success",
        "topology_id": topology_id,
        "prompt": prompt,
        "platform": platform,
        "type": matched_type,
        **topo,
        "generated_config": f"# Auto-generated {platform} config for {matched_type} topology\n# Review before deployment\n",
    }


def inject_scenario(topology_id: str, type: str, difficulty: str = "medium") -> Dict[str, Any]:
    """Inject a fault or attack scenario into an existing topology."""
    scenarios = {
        "link_failure": {"description": "A critical link between two core devices has failed.", "symptoms": ["High latency", "Packet loss", "Routing flaps"]},
        "misconfiguration": {"description": "An incorrect ACL or route map is blocking legitimate traffic.", "symptoms": ["Traffic blocked", "Intermittent connectivity", "Log errors"]},
        "broadcast_storm": {"description": "A layer 2 loop is causing a broadcast storm.", "symptoms": ["High CPU on switches", "Slow network", "Duplicate packets"]},
        "security_breach": {"description": "Unauthorized access detected on the network.", "symptoms": ["Unknown MAC addresses", "Suspicious traffic patterns", "Log alerts"]},
    }
    
    scenario = scenarios.get(type, scenarios["link_failure"])
    scenario_id = f"scen_{int(time.time())}"
    
    return {
        "status": "success",
        "scenario_id": scenario_id,
        "topology_id": topology_id,
        "type": type,
        "difficulty": difficulty,
        **scenario,
        "hint": "Start by checking device logs and interface status. Use 'show' commands systematically.",
    }


def verify_fix(scenario_id: str, student_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Verify a student's fix for an injected scenario."""
    # Simulated verification
    correct = random.choice([True, False])
    return {
        "status": "success",
        "scenario_id": scenario_id,
        "verified": correct,
        "message": "Fix verified successfully! The network is operational." if correct else "Fix incomplete. Check your configuration against the requirements.",
        "checks_passed": random.randint(3, 8) if correct else random.randint(0, 4),
        "total_checks": 8,
    }


def grade_submission(submission: Dict[str, Any] = None) -> Dict[str, Any]:
    """Grade a student submission with detailed AI feedback."""
    score = random.randint(50, 100)
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    
    feedback_points = [
        "Strong understanding of routing protocols demonstrated.",
        "Consider adding more detail to your troubleshooting steps.",
        "Good use of show commands for verification.",
        "Remember to save your configuration with 'write memory'.",
        "Excellent diagram and documentation.",
    ]
    
    return {
        "status": "success",
        "score": score,
        "grade": grade,
        "feedback": random.sample(feedback_points, min(3, len(feedback_points))),
        "recommendations": [
            "Review official Cisco documentation for deeper understanding.",
            "Practice with more advanced lab scenarios.",
            "Join study groups for peer learning.",
        ] if score < 80 else ["Excellent work! Continue to advanced topics."],
    }


def get_telemetry(device_id: str, metric_type: str = "all", duration: int = 3600) -> Dict[str, Any]:
    """Retrieve telemetry data for a device over a specified duration."""
    metrics = {
        "cpu": [random.randint(10, 95) for _ in range(10)],
        "memory": [random.randint(30, 90) for _ in range(10)],
        "interface_stats": {
            "gi0/0": {"tx_packets": random.randint(1000000, 9999999), "rx_packets": random.randint(1000000, 9999999), "errors": random.randint(0, 100)},
            "gi0/1": {"tx_packets": random.randint(1000000, 9999999), "rx_packets": random.randint(1000000, 9999999), "errors": random.randint(0, 100)},
        },
    }
    
    return {
        "status": "success",
        "device_id": device_id,
        "metric_type": metric_type,
        "duration_seconds": duration,
        "metrics": metrics if metric_type == "all" else {metric_type: metrics.get(metric_type, {})},
        "timestamp": datetime.utcnow().isoformat(),
    }


def inject_anomaly(telemetry: Dict[str, Any] = None, anomaly_type: str = "spike") -> Dict[str, Any]:
    """Inject an anomaly into telemetry data for training purposes."""
    return {
        "status": "success",
        "anomaly_type": anomaly_type,
        "injected": True,
        "description": f"Injected a {anomaly_type} anomaly into the telemetry data.",
        "detection_hint": "Look for sudden changes in patterns that deviate from baseline.",
    }


def get_quiz(module_id: str, difficulty: str = "mixed") -> Dict[str, Any]:
    """Retrieve a quiz for a given module at the specified difficulty."""
    if module_id not in QUIZZES:
        return {"status": "not_found", "available_quizzes": list(QUIZZES.keys()), "message": f"Quiz for module '{module_id}' not found."}
    
    quiz = QUIZZES[module_id]
    return {
        "status": "success",
        "module_id": module_id,
        "quiz_title": quiz["title"],
        "difficulty": difficulty,
        "total_questions": len(quiz["questions"]),
        "questions": [{"index": i, "question": q["q"], "options": q["options"]} for i, q in enumerate(quiz["questions"])],
    }


def grade_quiz(quiz_id: str, answers: Dict[str, int] = None) -> Dict[str, Any]:
    """Submit quiz answers for grading and receive results."""
    if answers is None:
        answers = {}
    
    # Find the quiz
    quiz = None
    for q in QUIZZES.values():
        if q["title"].lower().replace(" ", "_") == quiz_id.lower():
            quiz = q
            break
    
    if not quiz:
        return {"status": "not_found", "message": f"Quiz '{quiz_id}' not found."}
    
    correct = 0
    for i, q in enumerate(quiz["questions"]):
        user_ans = answers.get(str(i), -1)
        if user_ans == q["correct"]:
            correct += 1
    
    total = len(quiz["questions"])
    pct = (correct / total * 100) if total > 0 else 0
    
    return {
        "status": "success",
        "quiz_id": quiz_id,
        "score": f"{correct}/{total}",
        "percentage": round(pct, 1),
        "passed": pct >= 70,
    }


def mentor_chat(student_id: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Send a message to the AI mentor and receive guidance."""
    if context is None:
        context = {}
    
    # Simple keyword-based response
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["help", "stuck", "confused"]):
        response = random.choice(MENTOR_RESPONSES["study_tips"])
    elif any(w in msg_lower for w in ["career", "job", "work"]):
        response = random.choice(MENTOR_RESPONSES["career"])
    else:
        response = random.choice(MENTOR_RESPONSES["encouragement"])
    
    # Store history
    if student_id not in _mentor_history:
        _mentor_history[student_id] = []
    _mentor_history[student_id].append({
        "student_message": message,
        "mentor_response": response,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    return {
        "status": "success",
        "student_id": student_id,
        "mentor_response": response,
        "context": context,
    }


def get_mentor_history(student_id: str) -> Dict[str, Any]:
    """Retrieve the AI mentor conversation history for a student."""
    history = _mentor_history.get(student_id, [])
    return {
        "status": "success",
        "student_id": student_id,
        "total_messages": len(history),
        "history": history[-50:],  # Last 50 messages
    }


def get_progress(student_id: str) -> Dict[str, Any]:
    """Get the training progress overview for a student."""
    prog = _progress.get(student_id, {"labs_completed": 0, "total_score": 0, "quizzes_taken": 0})
    avg_score = (prog["total_score"] / prog["labs_completed"]) if prog["labs_completed"] > 0 else 0
    
    return {
        "status": "success",
        "student_id": student_id,
        **prog,
        "average_score": round(avg_score, 1),
        "next_milestone": "Complete 5 labs to earn your first badge!" if prog["labs_completed"] < 5 else "Complete 10 labs for the Bronze certification!",
    }


def get_leaderboard(limit: int = 50, track: str = "all") -> Dict[str, Any]:
    """Retrieve the training leaderboard with optional track filter."""
    # Generate sample leaderboard data
    global _leaderboard
    if not _leaderboard:
        names = ["Alex", "Samira", "Chen", "Jordan", "Priya", "Miguel", "Aisha", "David", "Leila", "Ryan"]
        for i in range(min(limit, len(names))):
            _leaderboard.append({
                "rank": i + 1,
                "student_id": f"student_{i+1}",
                "name": names[i],
                "score": random.randint(60, 100),
                "labs_completed": random.randint(1, 20),
                "track": random.choice(["enterprise", "security", "automation"]),
            })
        _leaderboard.sort(key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(_leaderboard):
            entry["rank"] = i + 1
    
    entries = _leaderboard[:limit] if track == "all" else [e for e in _leaderboard if e["track"] == track][:limit]
    
    return {
        "status": "success",
        "track": track,
        "total_entries": len(entries),
        "leaderboard": entries,
    }


def generate_certificate(student_id: str, track: str = "network_engineering") -> Dict[str, Any]:
    """Generate a completion certificate for a student in a given track."""
    cert_id = f"cert_{hashlib.sha256(f'{student_id}_{track}_{time.time()}'.encode()).hexdigest()[:16]}"
    
    certificate = {
        "cert_id": cert_id,
        "student_id": student_id,
        "track": track,
        "title": f"Certificate of Completion — {track.replace('_', ' ').title()}",
        "issued_at": datetime.utcnow().isoformat(),
        "issuer": "Luqi AI NetAI Training Platform",
        "verify_url": f"/api/netai/certificate/{cert_id}",
    }
    
    _certificates[cert_id] = certificate
    return {"status": "success", "certificate": certificate}


def get_certificate(cert_id: str) -> Dict[str, Any]:
    """Retrieve a previously generated certificate by its ID."""
    if cert_id not in _certificates:
        return {"status": "not_found", "message": f"Certificate '{cert_id}' not found."}
    return {"status": "success", "certificate": _certificates[cert_id]}

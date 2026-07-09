#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luqi AI v24.4.0 — IT Security Training Academy (Part 3)
=======================================================
Courses 9-15: Compliance, Mobile, Wireless, Social Engineering, 
Africa Telecom Security, DevSecOps, and Threat Intelligence.

Part of Luqi AI v24.4.0 by Limitless Telecoms
"""

from it_security_training_part1 import (
    DifficultyLevel, LessonType, CourseCategory, CertificationTrack,
    QuizQuestion, SecurityQuiz, SecurityLab, SecurityLesson,
    SecurityModule, SecurityCourse, UserProgress, UserCertificate,
    SkillTree, CTFChallenge, SkillBadge,
    SecurityTrainingError, CourseNotFoundError, ModuleNotFoundError,
    UserNotEnrolledError, LabNotFoundError, QuizNotFoundError,
    CTFChallengeNotFoundError, InvalidSubmissionError,
    _courses, _modules, _lessons, _labs, _quizzes,
    _ctf_challenges, _user_progress, _certificates, _skill_trees, _badges,
    datetime
)


def _build_courses_part3():
    """Build courses 9-15 for the IT Security Training Academy."""
    
    # ========================================================================
    # COURSE 9: COMPLIANCE & GOVERNANCE
    # ========================================================================
    mod9 = SecurityModule(
        id="compliance_001",
        course_id="compliance_governance",
        title="Security Compliance & Governance",
        description="Master security frameworks, compliance standards, risk management, and audit preparation for enterprise environments.",
        category=CourseCategory.COMPLIANCE,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=11.0,
        prerequisites=["Basic security knowledge"],
        order=9,
        lessons=[
            SecurityLesson(
                id="comp_l1", module_id="compliance_001", title="Introduction to Security Governance",
                content="Security governance frameworks: COBIT, ISO 27001, NIST CSF, ITIL. Roles and responsibilities: CISO, security committee, RACI matrices. Security policies, standards, procedures, and guidelines hierarchy. Governance, Risk Management, and Compliance (GRC) integration.",
                lesson_type=LessonType.TEXT, duration_min=45, order=1,
            ),
            SecurityLesson(
                id="comp_l2", module_id="compliance_001", title="ISO 27001 Implementation",
                content="ISO 27001:2022 standard deep dive: clauses 4-10, Annex A controls (93 controls in 4 categories). ISMS implementation roadmap, risk assessment methodology, Statement of Applicability, internal audits, and certification process.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=2,
            ),
            SecurityLesson(
                id="comp_l3", module_id="compliance_001", title="NIST Cybersecurity Framework",
                content="NIST CSF 2.0: Govern, Identify, Protect, Detect, Respond, Recover functions. Implementation tiers, profiles, and gap analysis. Mapping NIST CSF to other frameworks (ISO 27001, COBIT, CIS Controls).",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=3,
            ),
            SecurityLesson(
                id="comp_l4", module_id="compliance_001", title="Risk Management",
                content="Risk management lifecycle: identification, assessment, treatment, monitoring. Qualitative and quantitative risk analysis. Risk matrices, heat maps, and risk appetite. Treatment options: accept, mitigate, transfer, avoid. FAIR model for quantitative analysis.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=4,
            ),
            SecurityLesson(
                id="comp_l5", module_id="compliance_001", title="SOC 2 Compliance",
                content="SOC 2 Trust Services Criteria: Security, Availability, Processing Integrity, Confidentiality, Privacy. Type I vs Type II audits. Evidence collection, control testing, and auditor engagement. Common criteria (CC) mapping.",
                lesson_type=LessonType.TEXT, duration_min=45, order=5,
            ),
            SecurityLesson(
                id="comp_l6", module_id="compliance_001", title="GDPR & Data Privacy",
                content="GDPR requirements: lawful basis, data subject rights, DPO, DPIA, breach notification. Cross-border data transfers, SCCs, BCRs. Privacy by design and default. Penalties and enforcement cases.",
                lesson_type=LessonType.TEXT, duration_min=50, order=6,
            ),
            SecurityLesson(
                id="comp_l7", module_id="compliance_001", title="PCI DSS & HIPAA",
                content="PCI DSS 4.0: 12 requirements for payment card security. SAQ types, ASV scanning, QSA audits. HIPAA Security Rule: administrative, physical, technical safeguards. Healthcare-specific compliance challenges.",
                lesson_type=LessonType.TEXT, duration_min=45, order=7,
            ),
            SecurityLesson(
                id="comp_l8", module_id="compliance_001", title="Audit Preparation & Management",
                content="Internal and external audit preparation. Evidence collection, documentation standards, and audit trails. Managing auditor relationships, remediation planning, and continuous compliance monitoring.",
                lesson_type=LessonType.LAB, duration_min=55, order=8,
            ),
        ],
        labs=[
            SecurityLab(
                id="comp_lab1", module_id="compliance_001",
                title="Conduct a Risk Assessment",
                description="Perform a comprehensive risk assessment for a fictional organization.",
                environment="Risk assessment template, asset inventory, threat catalog, risk matrix tool.",
                tasks=[
                    "Identify and classify organizational assets",
                    "Identify threats and vulnerabilities for each asset",
                    "Assess likelihood and impact for each risk",
                    "Calculate risk scores and create risk register",
                    "Prioritize risks based on risk appetite",
                    "Propose risk treatment plans",
                    "Present findings to management",
                ],
                hints=[
                    "Use qualitative scales: 1-5 for likelihood and impact",
                    "Consider both technical and business impact",
                    "Involve stakeholders in risk appetite definition",
                ],
                solution="Asset inventory -> Threat modeling -> Vulnerability assessment -> Risk scoring (likelihood x impact) -> Risk register -> Treatment plan (mitigate/accept/transfer/avoid)",
                duration_min=90, points=150,
            ),
            SecurityLab(
                id="comp_lab2", module_id="compliance_001",
                title="ISO 27001 Gap Analysis",
                description="Perform a gap analysis against ISO 27001:2022 requirements.",
                environment="ISO 27001 checklist, organizational documentation, gap analysis template.",
                tasks=[
                    "Review ISO 27001:2022 clauses 4-10",
                    "Assess current state against each requirement",
                    "Identify gaps and assign maturity scores",
                    "Map Annex A controls to organizational controls",
                    "Create remediation roadmap with timelines",
                    "Estimate resource requirements",
                    "Present gap analysis report",
                ],
                hints=[
                    "Use CMMI-style maturity scoring (1-5)",
                    "Focus on mandatory clauses first",
                    "Prioritize high-risk gaps",
                ],
                solution="Clause-by-clause assessment -> Gap identification -> Maturity scoring -> Roadmap creation -> Resource planning -> Executive presentation",
                duration_min=75, points=125,
            ),
            SecurityLab(
                id="comp_lab3", module_id="compliance_001",
                title="GDPR Compliance Check",
                description="Audit an organization against GDPR requirements.",
                environment="GDPR checklist, data flow maps, privacy policy templates, DPIA template.",
                tasks=[
                    "Map all personal data processing activities",
                    "Assess lawful basis for each processing activity",
                    "Review data subject rights procedures",
                    "Evaluate consent mechanisms",
                    "Check cross-border transfer safeguards",
                    "Assess breach notification procedures",
                    "Create compliance action plan",
                ],
                hints=[
                    "Article 30 records of processing are mandatory",
                    "Consent must be freely given, specific, informed, unambiguous",
                    "Breach notification within 72 hours to DPA",
                ],
                solution="Data mapping -> Lawful basis assessment -> Rights procedure review -> Consent audit -> Transfer mechanism check -> Breach procedure test -> Action plan",
                duration_min=75, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="comp_q1", module_id="compliance_001", title="Compliance & Governance Assessment",
            passing_score=70, time_limit_minutes=25,
            questions=[
                QuizQuestion("comp1", "What is the primary goal of security governance?",
                    ["Technical implementation", "Align security with business objectives", "Penetration testing", "Software development"], 1,
                    "Governance ensures security supports and aligns with business goals.", DifficultyLevel.BEGINNER),
                QuizQuestion("comp2", "How many controls are in ISO 27001:2022 Annex A?",
                    ["114", "93", "77", "133"], 1,
                    "ISO 27001:2022 consolidated Annex A to 93 controls in 4 categories.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("comp3", "What are the 6 functions of NIST CSF 2.0?",
                    ["Identify, Protect, Detect, Respond, Recover", "Govern, Identify, Protect, Detect, Respond, Recover", "Plan, Do, Check, Act", "Prevent, Detect, Respond, Recover"], 1,
                    "NIST CSF 2.0 added 'Govern' as a sixth function.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("comp4", "What is a risk appetite?",
                    ["Hunger for risk", "Amount and type of risk an organization is willing to accept", "Risk elimination", "Risk transfer"], 1,
                    "Risk appetite defines the boundaries of acceptable risk.", DifficultyLevel.BEGINNER),
                QuizQuestion("comp5", "What is the difference between SOC 2 Type I and Type II?",
                    ["Type I tests controls at a point in time; Type II over a period", "Type I is better", "No difference", "Type II is cheaper"], 0,
                    "Type I assesses controls at a point in time; Type II over 3-12 months.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("comp6", "How long does an organization have to report a GDPR breach?",
                    ["24 hours", "72 hours", "7 days", "30 days"], 1,
                    "GDPR Article 33 requires breach notification within 72 hours.", DifficultyLevel.BEGINNER),
                QuizQuestion("comp7", "What is DPIA?",
                    ["Data Protection Impact Assessment", "Digital Privacy Information Act", "Data Processing Integration Audit", "Direct Privacy Impact Analysis"], 0,
                    "DPIA assesses privacy risks of processing operations.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("comp8", "How many requirements are in PCI DSS?",
                    ["6", "10", "12", "20"], 2,
                    "PCI DSS has 12 requirements organized into 6 groups.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("comp9", "What is the FAIR model used for?",
                    ["Qualitative risk analysis", "Quantitative risk analysis in financial terms", "Compliance checking", "Penetration testing"], 1,
                    "FAIR (Factor Analysis of Information Risk) provides quantitative risk analysis.", DifficultyLevel.ADVANCED),
                QuizQuestion("comp10", "What is the role of a DPO?",
                    ["Digital Processing Officer", "Data Protection Officer", "Database Performance Optimizer", "Data Privacy Organizer"], 1,
                    "DPO monitors GDPR compliance and advises on data protection.", DifficultyLevel.BEGINNER),
            ],
        ),
    )

    # ========================================================================
    # COURSE 10: MOBILE SECURITY
    # ========================================================================
    mod10 = SecurityModule(
        id="mobile_001",
        course_id="mobile_security",
        title="Mobile Application Security",
        description="Comprehensive mobile security for Android and iOS: reverse engineering, secure coding, and penetration testing.",
        category=CourseCategory.MOBILE,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=12.0,
        prerequisites=["Programming basics", "Web application security"],
        order=10,
        lessons=[
            SecurityLesson(
                id="mob_l1", module_id="mobile_001", title="Mobile Security Landscape",
                content="Mobile threat landscape: malware families, attack vectors, platform-specific vulnerabilities. Android vs iOS security models. OWASP Mobile Top 10 overview. Mobile app ecosystem risks.",
                lesson_type=LessonType.TEXT, duration_min=40, order=1,
            ),
            SecurityLesson(
                id="mob_l2", module_id="mobile_001", title="Android Security Architecture",
                content="Android security model: sandboxing, permissions, SELinux, verified boot. APK structure, Dalvik/ART runtime, inter-component communication (Intents, Content Providers, Broadcast Receivers).",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=2,
            ),
            SecurityLesson(
                id="mob_l3", module_id="mobile_001", title="iOS Security Architecture",
                content="iOS security: code signing, app sandbox, keychain, Secure Enclave, biometric authentication. Jailbreak types and implications. iOS app structure and distribution models.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=3,
            ),
            SecurityLesson(
                id="mob_l4", module_id="mobile_001", title="Mobile App Reverse Engineering",
                content="Android: decompilation with JADX, APKTool, dynamic instrumentation with Frida. iOS: disassembly with Hopper, GDB/LLDB debugging. Anti-reversing techniques and bypass methods.",
                lesson_type=LessonType.LAB, duration_min=65, order=4,
            ),
            SecurityLesson(
                id="mob_l5", module_id="mobile_001", title="Mobile Penetration Testing",
                content="Mobile pentesting methodology: static analysis, dynamic analysis, network testing, server-side testing. Tools: MobSF, objection, Burp Suite Mobile Assistant. API security testing for mobile backends.",
                lesson_type=LessonType.LAB, duration_min=70, order=5,
            ),
            SecurityLesson(
                id="mob_l6", module_id="mobile_001", title="Secure Mobile Development",
                content="OWASP MASVS compliance: storage, cryptography, authentication, network, platform, code quality. Certificate pinning implementation, root/jailbreak detection, obfuscation strategies.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=6,
            ),
            SecurityLesson(
                id="mob_l7", module_id="mobile_001", title="Mobile Malware Analysis",
                content="Android malware families: banking trojans, spyware, ransomware, adware. Static and dynamic analysis techniques. C2 communication patterns and evasion techniques.",
                lesson_type=LessonType.LAB, duration_min=60, order=7,
            ),
        ],
        labs=[
            SecurityLab(
                id="mob_lab1", module_id="mobile_001",
                title="Android App Reverse Engineering",
                description="Reverse engineer an Android APK to find hardcoded secrets and vulnerabilities.",
                environment="Android Studio, JADX, APKTool, Frida, Android emulator.",
                tasks=[
                    "Decompile APK with JADX and APKTool",
                    "Analyze AndroidManifest.xml for misconfigurations",
                    "Find hardcoded API keys and credentials",
                    "Analyze inter-component communication",
                    "Hook functions with Frida to bypass root detection",
                    "Extract and analyze native libraries",
                    "Document all findings",
                ],
                hints=[
                    "Check exported activities and services",
                    "Look for debug flags in manifest",
                    "Native libs often contain logic or secrets",
                ],
                solution="Decompile -> Manifest analysis -> Code review -> Frida hooks -> Native analysis -> Report",
                duration_min=90, points=150,
            ),
            SecurityLab(
                id="mob_lab2", module_id="mobile_001",
                title="iOS App Security Assessment",
                description="Assess iOS app security through static and dynamic analysis.",
                environment="Xcode, Hopper Disassembler, Frida, iOS jailbroken device/simulator, objection.",
                tasks=[
                    "Decrypt and extract IPA file",
                    "Analyze Info.plist for security settings",
                    "Check for jailbreak detection mechanisms",
                    "Intercept network traffic with Burp Suite",
                    "Bypass certificate pinning with Frida",
                    "Analyze Keychain data storage",
                    "Test authentication and session management",
                ],
                hints=[
                    "Use frida-trace to identify anti-debug checks",
                    "Check ATS (App Transport Security) settings",
                    "Keychain items may persist after uninstall",
                ],
                solution="IPA extraction -> Plist analysis -> Jailbreak bypass -> Traffic interception -> Pinning bypass -> Keychain analysis -> Report",
                duration_min=100, points=175,
            ),
            SecurityLab(
                id="mob_lab3", module_id="mobile_001",
                title="Mobile API Penetration Test",
                description="Test the backend API supporting a mobile application.",
                environment="Burp Suite, Postman, mobile app with API backend, OWASP API Top 10 guide.",
                tasks=[
                    "Intercept and analyze all API requests",
                    "Test for broken authentication",
                    "Check for excessive data exposure",
                    "Test rate limiting and brute force protection",
                    "Assess mass assignment vulnerabilities",
                    "Test for injection vulnerabilities",
                    "Verify authorization on all endpoints",
                ],
                hints=[
                    "Check for API versioning issues",
                    "Look for debug endpoints",
                    "Test with different user privilege levels",
                ],
                solution="API mapping -> Authentication testing -> Authorization testing -> Input validation -> Rate limiting -> Business logic -> Report",
                duration_min=90, points=150,
            ),
        ],
        quiz=SecurityQuiz(
            id="mob_q1", module_id="mobile_001", title="Mobile Security Assessment",
            passing_score=75, time_limit_minutes=25,
            questions=[
                QuizQuestion("mob1", "What is Android app sandboxing based on?",
                    ["Virtual machines", "Linux UIDs per app", "Windows permissions", "Hardware isolation"], 1,
                    "Each Android app runs in its own Linux UID sandbox.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("mob2", "What is Frida used for in mobile security?",
                    ["Static analysis", "Dynamic instrumentation", "Network scanning", "Code compilation"], 1,
                    "Frida allows dynamic code injection and function hooking.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("mob3", "What is certificate pinning?",
                    ["Encrypting certificates", "Embedding expected certificate in app", "Certificate generation", "SSL stripping"], 1,
                    "Pinning embeds expected certificate/public key in the app.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("mob4", "What does OWASP MASVS stand for?",
                    ["Mobile Application Security Verification Standard", "Mobile Attack Surface Validation System", "Mobile Authentication Security Verification Standard", "Mobile Application Secure Validation Standard"], 0,
                    "MASVS provides security requirements for mobile apps.", DifficultyLevel.BEGINNER),
                QuizQuestion("mob5", "What is the purpose of ProGuard/R8?",
                    ["Code obfuscation and optimization", "Network protection", "Encryption", "Authentication"], 0,
                    "ProGuard/R8 obfuscates and optimizes Android apps.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("mob6", "What is jailbreaking?",
                    ["Installing apps", "Removing iOS restrictions to gain root access", "Updating iOS", "Backing up data"], 1,
                    "Jailbreaking removes iOS security restrictions.", DifficultyLevel.BEGINNER),
                QuizQuestion("mob7", "What is ADB?",
                    ["Apple Device Bridge", "Android Debug Bridge", "Application Data Bus", "Advanced Debug Browser"], 1,
                    "ADB is the Android Debug Bridge for developer communication.", DifficultyLevel.BEGINNER),
                QuizQuestion("mob8", "What is the Secure Enclave?",
                    ["A secure room", "Hardware security module in Apple processors", "A type of encryption", "A network protocol"], 1,
                    "Secure Enclave is isolated hardware for sensitive operations.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("mob9", "What is an exported Activity in Android?",
                    ["An activity that can be launched by other apps", "A closed activity", "A debug feature", "An error state"], 0,
                    "Exported activities can be launched by other applications.", DifficultyLevel.ADVANCED),
                QuizQuestion("mob10", "What is the purpose of objection?",
                    ["Runtime mobile exploration toolkit", "Code compiler", "Network scanner", "Database manager"], 0,
                    "Objection provides runtime exploration capabilities for mobile apps.", DifficultyLevel.INTERMEDIATE),
            ],
        ),
    )

    # ========================================================================
    # COURSE 11: WIRELESS SECURITY
    # ========================================================================
    mod11 = SecurityModule(
        id="wireless_001",
        course_id="wireless_security",
        title="Wireless Network Security",
        description="Secure WiFi, Bluetooth, and cellular networks. Master wireless encryption, penetration testing, and intrusion detection.",
        category=CourseCategory.WIRELESS,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=10.0,
        prerequisites=["Network security fundamentals"],
        order=11,
        lessons=[
            SecurityLesson(
                id="wl_l1", module_id="wireless_001", title="Wireless Security Fundamentals",
                content="Wireless protocols: 802.11a/b/g/n/ac/ax. Encryption evolution: WEP, WPA, WPA2, WPA3. Authentication methods: Open, WEP, WPA-Personal, WPA-Enterprise (802.1X/EAP). Wireless threat landscape.",
                lesson_type=LessonType.TEXT, duration_min=40, order=1,
            ),
            SecurityLesson(
                id="wl_l2", module_id="wireless_001", title="WiFi Penetration Testing",
                content="WiFi reconnaissance with airodump-ng, packet capture with airodump-ng. WEP cracking, WPA/WPA2 PSK cracking with aircrack-ng. Evil twin attacks, rogue AP detection, and mitigation.",
                lesson_type=LessonType.LAB, duration_min=70, order=2,
            ),
            SecurityLesson(
                id="wl_l3", module_id="wireless_001", title="WPA3 and Modern Security",
                content="WPA3 features: SAE (Simultaneous Authentication of Equals), OWE (Opportunistic Wireless Encryption), 192-bit security mode. Dragonblood vulnerability and mitigations. WiFi 6/6E security enhancements.",
                lesson_type=LessonType.INTERACTIVE, duration_min=45, order=3,
            ),
            SecurityLesson(
                id="wl_l4", module_id="wireless_001", title="Enterprise Wireless Security",
                content="802.1X and RADIUS authentication. EAP methods: PEAP, EAP-TLS, EAP-TTLS. Certificate management for wireless. NAC integration and guest access solutions.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=4,
            ),
            SecurityLesson(
                id="wl_l5", module_id="wireless_001", title="Bluetooth Security",
                content="Bluetooth protocols: BR/EDR, BLE. Pairing methods: Legacy, Secure Connections. BLE attacks: sniffing, MITM, relay attacks. Bluetooth vulnerabilities: BlueBorne, KNOB, KBD.",
                lesson_type=LessonType.LAB, duration_min=55, order=5,
            ),
            SecurityLesson(
                id="wl_l6", module_id="wireless_001", title="Wireless Intrusion Detection",
                content="WIDS/WIPS deployment and configuration. Rogue AP detection, spectrum analysis, and intrusion prevention. Open-source tools: Kismet, Wigle, and custom detection scripts.",
                lesson_type=LessonType.INTERACTIVE, duration_min=45, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="wl_lab1", module_id="wireless_001",
                title="WiFi Penetration Testing with Aircrack-ng",
                description="Perform a complete WiFi security assessment using aircrack-ng suite.",
                environment="Kali Linux, Alfa AWUS036ACH wireless adapter, test access points.",
                tasks=[
                    "Put wireless adapter in monitor mode",
                    "Discover nearby networks with airodump-ng",
                    "Capture WPA handshake from target network",
                    "Perform deauthentication attack",
                    "Crack WPA passphrase with aircrack-ng and wordlist",
                    "Document all findings and recommendations",
                ],
                hints=[
                    "Use airmon-ng to start monitor mode",
                    "Target your own network only",
                    "Better wordlists improve crack success rate",
                ],
                solution="airmon-ng start wlan0; airodump-ng wlan0mon; airodump-ng --bssid <target> -c <ch> -w capture wlan0mon; aireplay-ng -0 10 -a <bssid> wlan0mon; aircrack-ng capture-01.cap -w wordlist.txt",
                duration_min=90, points=150,
            ),
            SecurityLab(
                id="wl_lab2", module_id="wireless_001",
                title="Evil Twin Attack and Defense",
                description="Set up an evil twin access point and implement detection mechanisms.",
                environment="Kali Linux, hostapd, dnsmasq, Wireshark, airgeddon.",
                tasks=[
                    "Configure evil twin AP with hostapd",
                    "Set up DHCP and DNS redirection",
                    "Capture credentials from connected clients",
                    "Implement rogue AP detection with Kismet",
                    "Configure WIPS rules for automatic blocking",
                    "Document attack and defense measures",
                ],
                hints=[
                    "Use airgeddon for automated evil twin setup",
                    "Kismet can detect rogue APs by BSSID comparison",
                    "Enterprise 802.1X prevents most evil twin attacks",
                ],
                solution="hostapd.conf -> hostapd; dnsmasq for DHCP/DNS; Captive portal for credential capture; Defense: Kismet + WIPS + 802.1X authentication",
                duration_min=75, points=125,
            ),
            SecurityLab(
                id="wl_lab3", module_id="wireless_001",
                title="Bluetooth Security Assessment",
                description="Assess Bluetooth device security through scanning and testing.",
                environment="Kali Linux, Bluetooth adapter, Ubertooth One, target Bluetooth devices.",
                tasks=[
                    "Scan for discoverable Bluetooth devices",
                    "Enumerate device services and profiles",
                    "Test pairing vulnerabilities",
                    "Sniff BLE traffic with Ubertooth",
                    "Test for known vulnerabilities (BlueBorne, KNOB)",
                    "Document security posture and recommendations",
                ],
                hints=[
                    "Use hcitool and sdptool for Bluetooth recon",
                    "Ubertooth captures BLE advertising packets",
                    "Many BLE devices lack proper pairing security",
                ],
                solution="hcitool scan -> sdptool browse -> Pairing analysis -> Ubertooth BLE sniff -> Vulnerability assessment -> Report",
                duration_min=75, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="wl_q1", module_id="wireless_001", title="Wireless Security Assessment",
            passing_score=75, time_limit_minutes=20,
            questions=[
                QuizQuestion("wl1", "Why is WEP considered insecure?",
                    ["Uses weak encryption (RC4 with small IV)", "Too slow", "Too complex", "Not supported"], 0,
                    "WEP's RC4 implementation has small IV space enabling rapid key recovery.", DifficultyLevel.BEGINNER),
                QuizQuestion("wl2", "What replaced WPA2's PSK authentication?",
                    ["WPA3 with SAE", "WEP2", "Open authentication", "MAC filtering"], 0,
                    "WPA3 replaces WPA2-PSK with SAE (Simultaneous Authentication of Equals).", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wl3", "What is an evil twin attack?",
                    ["Rogue AP impersonating legitimate network", "Two identical networks", "Router firmware attack", "DNS hijacking"], 0,
                    "Evil twin is a rogue AP with same SSID as legitimate network.", DifficultyLevel.BEGINNER),
                QuizQuestion("wl4", "What is 802.1X?",
                    ["Port-based network access control", "Wireless protocol", "Encryption standard", "Routing protocol"], 0,
                    "802.1X provides port-based authentication for network access.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("wl5", "What tool is used for WiFi reconnaissance?",
                    ["Nmap", "airodump-ng", "Metasploit", "Burp Suite"], 1,
                    "airodump-ng is part of aircrack-ng suite for WiFi recon.", DifficultyLevel.BEGINNER),
                QuizQuestion("wl6", "What is BLE?",
                    ["Bluetooth Low Energy", "Bluetooth Long Energy", "Basic Link Encryption", "Broadband Local Ethernet"], 0,
                    "BLE is Bluetooth Low Energy for power-constrained devices.", DifficultyLevel.BEGINNER),
                QuizQuestion("wl7", "What is the Dragonblood vulnerability?",
                    ["WPA3 SAE side-channel attack", "WPA2 KRACK attack", "WEP weakness", "Bluetooth vulnerability"], 0,
                    "Dragonblood affects WPA3's SAE handshake.", DifficultyLevel.ADVANCED),
                QuizQuestion("wl8", "What is the purpose of WIDS/WIPS?",
                    ["Wireless intrusion detection/prevention", "Wireless internet distribution", "Wireless identity system", "Wireless integration protocol"], 0,
                    "WIDS/WIPS detects and prevents wireless network intrusions.", DifficultyLevel.BEGINNER),
            ],
        ),
    )

    # ========================================================================
    # COURSE 12: SOCIAL ENGINEERING
    # ========================================================================
    mod12 = SecurityModule(
        id="soceng_001",
        course_id="social_engineering",
        title="Social Engineering Defense",
        description="Understand and defend against psychological manipulation techniques used by attackers.",
        category=CourseCategory.SOCIAL,
        difficulty=DifficultyLevel.BEGINNER,
        duration_hours=8.0,
        prerequisites=[],
        order=12,
        lessons=[
            SecurityLesson(
                id="se_l1", module_id="soceng_001", title="Psychology of Social Engineering",
                content="Cognitive biases exploited by attackers: authority, urgency, scarcity, reciprocity, social proof. Attack psychology: pretexting, rapport building, and manipulation techniques.",
                lesson_type=LessonType.TEXT, duration_min=35, order=1,
            ),
            SecurityLesson(
                id="se_l2", module_id="soceng_001", title="Phishing Attacks",
                content="Email phishing, spear phishing, whaling, and clone phishing. Technical indicators: SPF, DKIM, DMARC. Creating and detecting phishing emails. URL analysis and attachment inspection.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=2,
            ),
            SecurityLesson(
                id="se_l3", module_id="soceng_001", title="Pretexting & Impersonation",
                content="Creating convincing pretexts: IT support, executive impersonation, vendor spoofing. Vishing (voice phishing) and smishing (SMS phishing). Physical impersonation and tailgating.",
                lesson_type=LessonType.TEXT, duration_min=40, order=3,
            ),
            SecurityLesson(
                id="se_l4", module_id="soceng_001", title="Advanced Social Engineering",
                content="Watering hole attacks, supply chain social engineering, social media exploitation, and OSINT-based targeting. Red team social engineering engagements.",
                lesson_type=LessonType.TEXT, duration_min=35, order=4,
            ),
            SecurityLesson(
                id="se_l5", module_id="soceng_001", title="Security Awareness Programs",
                content="Building effective security awareness: training design, delivery methods, metrics, and behavior change. Simulated phishing campaigns and just-in-time training.",
                lesson_type=LessonType.INTERACTIVE, duration_min=45, order=5,
            ),
            SecurityLesson(
                id="se_l6", module_id="soceng_001", title="Technical Defenses",
                content="Email security gateways, sandboxing, URL rewriting, attachment scanning. Browser isolation, application whitelisting, and zero-trust architecture for human-layer defense.",
                lesson_type=LessonType.INTERACTIVE, duration_min=40, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="se_lab1", module_id="soceng_001",
                title="Phishing Email Analysis",
                description="Analyze suspicious emails to identify phishing indicators.",
                environment="Sample phishing emails, email header analysis tools, URL inspection tools.",
                tasks=[
                    "Analyze email headers for spoofing indicators",
                    "Inspect URLs for deception techniques",
                    "Check SPF, DKIM, DMARC alignment",
                    "Identify psychological manipulation tactics",
                    "Document all indicators of phishing",
                    "Create detection rules for similar campaigns",
                ],
                hints=[
                    "Check Return-Path vs From domain mismatch",
                    "Look for URL homograph attacks",
                    "Analyze attachment file types carefully",
                ],
                solution="Header analysis -> SPF/DKIM/DMARC check -> URL inspection -> Attachment analysis -> Psychological indicator documentation -> Detection rules",
                duration_min=60, points=100,
            ),
            SecurityLab(
                id="se_lab2", module_id="soceng_001",
                title="Simulated Phishing Campaign",
                description="Design and execute a controlled phishing simulation.",
                environment="GoPhish framework, email templates, landing page templates.",
                tasks=[
                    "Set up GoPhish server",
                    "Create realistic phishing email template",
                    "Design educational landing page",
                    "Configure sending profile",
                    "Launch campaign to test group",
                    "Analyze results and metrics",
                    "Generate awareness report",
                ],
                hints=[
                    "Always get written authorization first",
                    "Use educational landing pages, not credential harvesting",
                    "Focus on metrics: open rate, click rate, report rate",
                ],
                solution="GoPhish setup -> Template creation -> Landing page -> Campaign launch -> Metrics analysis -> Awareness report",
                duration_min=75, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="se_q1", module_id="soceng_001", title="Social Engineering Assessment",
            passing_score=70, time_limit_minutes=15,
            questions=[
                QuizQuestion("se1", "What is pretexting?",
                    ["Creating a fabricated scenario to obtain information", "Encrypting data", "Network scanning", "Password cracking"], 0,
                    "Pretexting creates a fabricated scenario to manipulate targets.", DifficultyLevel.BEGINNER),
                QuizQuestion("se2", "What does SPF verify?",
                    ["Authorized sending mail servers for a domain", "Email content", "Attachment safety", "Encryption strength"], 0,
                    "SPF specifies authorized mail servers for a domain.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("se3", "What is vishing?",
                    ["Voice phishing", "Video phishing", "Virtual phishing", "Virus phishing"], 0,
                    "Vishing uses phone calls for phishing attacks.", DifficultyLevel.BEGINNER),
                QuizQuestion("se4", "What is the most effective defense against social engineering?",
                    ["Security awareness training", "Firewalls", "Antivirus", "Encryption"], 0,
                    "Awareness training empowers users to recognize attacks.", DifficultyLevel.BEGINNER),
                QuizQuestion("se5", "What is tailgating?",
                    ["Following someone through a secure door", "Network scanning", "Email spoofing", "Website cloning"], 0,
                    "Tailgating follows an authorized person through a secure entry.", DifficultyLevel.BEGINNER),
                QuizQuestion("se6", "What does DMARC do?",
                    ["Email authentication and reporting", "Encrypt emails", "Block all spam", "Speed up delivery"], 0,
                    "DMARC uses SPF/DKIM and provides reporting.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("se7", "What is a watering hole attack?",
                    ["Compromising websites visited by target group", "DNS poisoning", "Physical attack", "DDoS attack"], 0,
                    "Watering hole attacks compromise sites the target group visits.", DifficultyLevel.ADVANCED),
                QuizQuestion("se8", "What should you do if you suspect a phishing email?",
                    ["Click links to verify", "Report it to security team, don't click", "Forward to colleagues", "Reply to sender"], 1,
                    "Report suspected phishing without clicking links or opening attachments.", DifficultyLevel.BEGINNER),
            ],
        ),
    )

    # ========================================================================
    # COURSE 13: AFRICA TELECOM SECURITY
    # ========================================================================
    mod13 = SecurityModule(
        id="africatel_001",
        course_id="africa_telecom_security",
        title="Africa Telecom & Mobile Money Security",
        description="Specialized security training for African telecommunications: mobile money, USSD, SIM swap prevention, and telecom regulations.",
        category=CourseCategory.TELECOM,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=10.0,
        prerequisites=["Network security basics"],
        order=13,
        lessons=[
            SecurityLesson(
                id="afr_l1", module_id="africatel_001", title="African Telecom Landscape",
                content="Africa's telecom ecosystem: mobile-first connectivity, GSM/3G/4G/5G rollout, submarine cables, satellite connectivity. Key operators: MTN, Airtel, Orange, Safaricom, Vodacom. Regulatory bodies: NCC, CAK, ICASA, ARCEP.",
                lesson_type=LessonType.TEXT, duration_min=40, order=1,
            ),
            SecurityLesson(
                id="afr_l2", module_id="africatel_001", title="Mobile Money Security",
                content="Mobile money architecture: M-Pesa, MTN Mobile Money, Airtel Money, Orange Money. Security challenges: transaction integrity, agent fraud, account takeover, interoperability risks. KYC/AML compliance.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=2,
            ),
            SecurityLesson(
                id="afr_l3", module_id="africatel_001", title="USSD Security",
                content="USSD protocol security: session-based communication, GSM encryption limitations, USSD injection attacks, menu manipulation, and fraud techniques. USSD vs SMS security comparison.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=3,
            ),
            SecurityLesson(
                id="afr_l4", module_id="africatel_001", title="SIM Swap Fraud Prevention",
                content="SIM swap attack vectors: social engineering at carrier stores, insider threats, online account takeover. Detection methods: IMEI tracking, behavioral analytics, delay mechanisms. Prevention: SIM PINs, notification systems, recovery procedures.",
                lesson_type=LessonType.TEXT, duration_min=45, order=4,
            ),
            SecurityLesson(
                id="afr_l5", module_id="africatel_001", title="SS7 & Signaling Security",
                content="SS7 protocol vulnerabilities: location tracking, SMS interception, call redirection. SIGTRAN and Diameter security. 5G Service-Based Architecture security improvements. STP security and signaling firewalls.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=5,
            ),
            SecurityLesson(
                id="afr_l6", module_id="africatel_001", title="Telecom Regulatory Framework",
                content="African telecom regulations: data protection laws (NDPR in Nigeria, POPIA in South Africa), licensing frameworks, interconnection regimes, universal service obligations, and cybersecurity directives.",
                lesson_type=LessonType.TEXT, duration_min=40, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="afr_lab1", module_id="africatel_001",
                title="USSD Session Analysis",
                description="Analyze USSD traffic to identify security vulnerabilities.",
                environment="Wireshark with USSD dissectors, GSM test network, USSD gateway logs.",
                tasks=[
                    "Capture USSD session traffic",
                    "Analyze session flow and parameters",
                    "Identify encryption gaps",
                    "Test for USSD injection vulnerabilities",
                    "Document security findings",
                    "Propose security improvements",
                ],
                hints=[
                    "USSD uses GSM layer signaling",
                    "Check for plaintext sensitive data",
                    "Session hijacking is a common risk",
                ],
                solution="Traffic capture -> Session analysis -> Encryption assessment -> Injection testing -> Findings report -> Recommendations",
                duration_min=75, points=125,
            ),
            SecurityLab(
                id="afr_lab2", module_id="africatel_001",
                title="SIM Swap Detection System",
                description="Build a detection system for SIM swap attacks.",
                environment="Python 3.11, sample telecom logs, ML libraries, alerting framework.",
                tasks=[
                    "Analyze historical SIM swap patterns",
                    "Build behavioral baseline for subscribers",
                    "Implement anomaly detection rules",
                    "Create alerting thresholds",
                    "Build dashboard for SOC analysts",
                    "Test with simulated SIM swap scenarios",
                ],
                hints=[
                    "Flag unusual SIM changes outside business hours",
                    "Correlate with account changes",
                    "Use velocity checks for swap requests",
                ],
                solution="Pattern analysis -> Baseline creation -> Anomaly detection -> Alerting -> Dashboard -> Testing",
                duration_min=90, points=150,
            ),
        ],
        quiz=SecurityQuiz(
            id="afr_q1", module_id="africatel_001", title="Africa Telecom Security Assessment",
            passing_score=70, time_limit_minutes=20,
            questions=[
                QuizQuestion("afr1", "What is M-Pesa?",
                    ["A mobile money service", "A telecom operator", "A security protocol", "A regulatory body"], 0,
                    "M-Pesa is a mobile money service launched by Safaricom in Kenya.", DifficultyLevel.BEGINNER),
                QuizQuestion("afr2", "What does USSD stand for?",
                    ["Unstructured Supplementary Service Data", "Universal Secure Service Delivery", "Unified Signaling System Data", "User Session Service Data"], 0,
                    "USSD is a GSM protocol for session-based communication.", DifficultyLevel.BEGINNER),
                QuizQuestion("afr3", "What is SIM swap fraud?",
                    ["Transferring phone number to attacker's SIM", "Cloning a SIM card", "Hacking a phone", "Stealing a phone"], 0,
                    "SIM swap transfers a victim's number to an attacker's SIM.", DifficultyLevel.BEGINNER),
                QuizQuestion("afr4", "What is SS7?",
                    ["Signaling System 7", "Security Standard 7", "Service Set 7", "Session 7"], 0,
                    "SS7 is the signaling protocol for telephone networks.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("afr5", "Which Nigerian regulatory body oversees telecom?",
                    ["NCC", "FCC", "ICASA", "ARCEP"], 0,
                    "NCC (Nigerian Communications Commission) regulates Nigerian telecom.", DifficultyLevel.BEGINNER),
                QuizQuestion("afr6", "What is the primary defense against SIM swap?",
                    ["Use app-based 2FA instead of SMS", "Stronger password", "Antivirus", "Firewall"], 0,
                    "App-based 2FA doesn't rely on SMS/SIM.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("afr7", "What is NDPR?",
                    ["Nigeria Data Protection Regulation", "Network Data Processing Rule", "National Digital Privacy Regulation", "New Data Protection Requirement"], 0,
                    "NDPR is Nigeria's data protection regulation.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("afr8", "What is a signaling firewall?",
                    ["Filters SS7/Diameter messages", "Network firewall", "Email filter", "Web application firewall"], 0,
                    "Signaling firewalls filter SS7/Diameter signaling messages.", DifficultyLevel.INTERMEDIATE),
            ],
        ),
    )

    # Store modules 9-13
    _modules[mod9.id] = mod9
    _modules[mod10.id] = mod10
    _modules[mod11.id] = mod11
    _modules[mod12.id] = mod12
    _modules[mod13.id] = mod13

    # Register courses 9-13
    course9 = SecurityCourse(
        id="compliance_governance", title="Security Compliance & Governance",
        description="SOC 2, ISO 27001, NIST CSF, GDPR, PCI-DSS, HIPAA, risk assessment, and audit preparation.",
        category=CourseCategory.COMPLIANCE, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=11.0, modules=[mod9], certification_track=CertificationTrack.CISSP, icon="📋",
    )
    course10 = SecurityCourse(
        id="mobile_security", title="Mobile Application Security",
        description="Android/iOS security, OWASP MASVS, mobile pentesting, API security, and certificate pinning.",
        category=CourseCategory.MOBILE, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=12.0, modules=[mod10], certification_track=CertificationTrack.CEH, icon="📱",
    )
    course11 = SecurityCourse(
        id="wireless_security", title="Wireless Network Security",
        description="WPA2/WPA3, WiFi pentesting with Aircrack-ng, Evil Twin, Bluetooth security, and WIDS.",
        category=CourseCategory.WIRELESS, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=10.0, modules=[mod11], certification_track=CertificationTrack.COMPTIA_SECURITY_PLUS, icon="📡",
    )
    course12 = SecurityCourse(
        id="social_engineering", title="Social Engineering Defense",
        description="Phishing techniques, defense strategies, security awareness programs, and simulated campaigns.",
        category=CourseCategory.SOCIAL, difficulty=DifficultyLevel.BEGINNER,
        duration_hours=8.0, modules=[mod12], certification_track=CertificationTrack.COMPTIA_SECURITY_PLUS, icon="🎭",
    )
    course13 = SecurityCourse(
        id="africa_telecom_security", title="Africa Telecom & Mobile Money Security",
        description="Mobile money security, USSD vulnerabilities, SIM swap fraud, SS7 signaling, and regulatory frameworks.",
        category=CourseCategory.TELECOM, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=10.0, modules=[mod13], certification_track=CertificationTrack.COMPTIA_SECURITY_PLUS, icon="📞",
    )

    _courses["compliance_governance"] = course9
    _courses["mobile_security"] = course10
    _courses["wireless_security"] = course11
    _courses["social_engineering"] = course12
    _courses["africa_telecom_security"] = course13


# Build part 3 courses on import
_build_courses_part3()


# ============================================================================
# CORE FUNCTIONS (shared)
# ============================================================================

def get_all_courses() -> list:
    """Return all security training courses."""
    return [course.to_dict() for course in _courses.values()]


def get_course(course_id: str) -> dict:
    """Get a specific course by ID."""
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")
    return _courses[course_id].to_dict()


def get_all_modules() -> list:
    """Return all training modules."""
    return [module.to_dict() for module in _modules.values()]


def get_module(module_id: str) -> dict:
    """Get a specific module by ID."""
    if module_id not in _modules:
        raise ModuleNotFoundError(f"Module '{module_id}' not found")
    return _modules[module_id].to_dict()


def get_all_labs() -> list:
    """Return all hands-on labs."""
    return [lab.to_dict() for lab in _labs.values()]


def get_lab(lab_id: str) -> dict:
    """Get a specific lab by ID."""
    if lab_id not in _labs:
        raise LabNotFoundError(f"Lab '{lab_id}' not found")
    return _labs[lab_id].to_dict()


def get_all_quizzes() -> list:
    """Return all quizzes."""
    return [quiz.to_dict() for quiz in _quizzes.values()]


def get_quiz(quiz_id: str) -> dict:
    """Get a specific quiz by ID."""
    if quiz_id not in _quizzes:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found")
    return _quizzes[quiz_id].to_dict()


def get_all_ctf_challenges() -> list:
    """Return all CTF challenges (without flags)."""
    return [ctf.to_dict(reveal_flag=False) for ctf in _ctf_challenges.values()]


def get_ctf_challenge(challenge_id: str, reveal_flag: bool = False) -> dict:
    """Get a specific CTF challenge."""
    if challenge_id not in _ctf_challenges:
        raise CTFChallengeNotFoundError(f"CTF challenge '{challenge_id}' not found")
    return _ctf_challenges[challenge_id].to_dict(reveal_flag=reveal_flag)


def get_all_badges() -> list:
    """Return all available skill badges."""
    return [badge.to_dict() for badge in _badges.values()]


def get_badge(badge_id: str) -> dict:
    """Get a specific badge by ID."""
    if badge_id not in _badges:
        raise ValueError(f"Badge '{badge_id}' not found")
    return _badges[badge_id].to_dict()


def get_leaderboard(limit: int = 50) -> list:
    """Return the training leaderboard."""
    return _leaderboard[:limit]


def enroll_user(user_id: str, course_id: str) -> dict:
    """Enroll a user in a course."""
    if not user_id or not course_id:
        raise ValueError("user_id and course_id are required")
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")
    
    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        _user_progress[progress_key] = UserProgress(
            user_id=user_id,
            course_id=course_id,
            enrolled_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
        )
    return {
        "status": "enrolled",
        "user_id": user_id,
        "course_id": course_id,
        "enrolled_at": _user_progress[progress_key].enrolled_at.isoformat(),
    }


def get_user_progress(user_id: str, course_id: str) -> dict:
    """Get user progress for a course."""
    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User '{user_id}' not enrolled in '{course_id}'")
    return _user_progress[progress_key].to_dict()


def update_lesson_progress(user_id: str, course_id: str, lesson_id: str) -> dict:
    """Update lesson completion progress."""
    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User '{user_id}' not enrolled in '{course_id}'")
    
    progress = _user_progress[progress_key]
    if lesson_id not in progress.completed_lessons:
        progress.completed_lessons.append(lesson_id)
    progress.last_accessed = datetime.utcnow()
    return {
        "status": "success",
        "lesson_completed": lesson_id,
        "total_completed": len(progress.completed_lessons),
    }


def submit_quiz(user_id: str, quiz_id: str, answers: dict) -> dict:
    """Submit quiz answers and get graded results."""
    if quiz_id not in _quizzes:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found")
    
    quiz = _quizzes[quiz_id]
    correct = 0
    total = len(quiz.questions)
    feedback = []
    
    for i, question in enumerate(quiz.questions):
        user_answer = answers.get(f"q{i}", -1)
        is_correct = user_answer == question.correct_answer
        if is_correct:
            correct += 1
        feedback.append({
            "question_id": question.id,
            "correct": is_correct,
            "your_answer": user_answer,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation if not is_correct else None,
        })
    
    score = round((correct / total) * 100, 2) if total > 0 else 0
    passed = score >= quiz.passing_score
    
    return {
        "quiz_id": quiz_id,
        "score": score,
        "correct": correct,
        "total": total,
        "passed": passed,
        "passing_score": quiz.passing_score,
        "feedback": feedback,
    }


def submit_lab(user_id: str, lab_id: str, submission: dict) -> dict:
    """Submit a lab exercise for grading."""
    if lab_id not in _labs:
        raise LabNotFoundError(f"Lab '{lab_id}' not found")
    
    lab = _labs[lab_id]
    score = submission.get("score", 0)
    feedback = submission.get("feedback", "")
    
    return {
        "lab_id": lab_id,
        "score": score,
        "max_points": lab.points,
        "feedback": feedback,
        "status": "submitted",
    }


def verify_ctf_flag(user_id: str, challenge_id: str, flag: str) -> dict:
    """Verify a CTF flag submission."""
    if challenge_id not in _ctf_challenges:
        raise CTFChallengeNotFoundError(f"Challenge '{challenge_id}' not found")
    
    challenge = _ctf_challenges[challenge_id]
    correct = challenge.flag == flag
    
    if correct:
        challenge.solves += 1
        return {
            "status": "correct",
            "challenge_id": challenge_id,
            "points_earned": challenge.points,
            "message": "Congratulations! Flag is correct!",
        }
    return {
        "status": "incorrect",
        "challenge_id": challenge_id,
        "message": "Flag is incorrect. Try again!",
    }


def get_user_certificates(user_id: str) -> list:
    """Get all certificates for a user."""
    return [
        cert.to_dict() for cert in _certificates.values()
        if cert.user_id == user_id
    ]


def generate_certificate(user_id: str, course_id: str) -> dict:
    """Generate a certificate for course completion."""
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")
    
    cert_id = f"CERT-{user_id}-{course_id}-{datetime.utcnow().strftime('%Y%m%d')}"
    cert = UserCertificate(
        user_id=user_id,
        course_id=course_id,
        certificate_id=cert_id,
        issued_at=datetime.utcnow(),
        verification_hash=__import__('hashlib').sha256(cert_id.encode()).hexdigest()[:16],
    )
    _certificates[cert_id] = cert
    return cert.to_dict()


def get_skill_tree(user_id: str) -> dict:
    """Get or create a user's skill tree."""
    if user_id not in _skill_trees:
        _skill_trees[user_id] = SkillTree(user_id=user_id)
    return _skill_trees[user_id].to_dict()


def update_skill_tree(user_id: str, points: int, badge_id: str = None) -> dict:
    """Update a user's skill tree with earned points and badges."""
    if user_id not in _skill_trees:
        _skill_trees[user_id] = SkillTree(user_id=user_id)
    
    tree = _skill_trees[user_id]
    tree.total_points += points
    
    # Level up logic
    new_level = min(50, 1 + tree.total_points // 1000)
    if new_level > tree.level:
        tree.level = new_level
    
    # Add badge if provided
    if badge_id and badge_id not in tree.badges:
        tree.badges.append(badge_id)
    
    # Update title based on level
    titles = [
        (1, "Security Novice"), (5, "Security Apprentice"), (10, "Security Analyst"),
        (15, "Security Professional"), (20, "Senior Security Engineer"), (25, "Security Architect"),
        (30, "Lead Security Researcher"), (40, "Chief Security Officer"), (50, "Security Legend"),
    ]
    for level, title in titles:
        if tree.level >= level:
            tree.title = title
    
    return tree.to_dict()


def get_user_stats(user_id: str) -> dict:
    """Get comprehensive user training statistics."""
    user_certs = [c for c in _certificates.values() if c.user_id == user_id]
    user_progress = [p for p in _user_progress.values() if p.user_id == user_id]
    
    tree = get_skill_tree(user_id)
    
    return {
        "user_id": user_id,
        "courses_enrolled": len(user_progress),
        "courses_completed": sum(1 for p in user_progress if p.status == "completed"),
        "total_certificates": len(user_certs),
        "total_points": tree.get("total_points", 0),
        "current_level": tree.get("level", 1),
        "title": tree.get("title", "Security Novice"),
        "badges_earned": len(tree.get("badges", [])),
        "total_time_minutes": sum(p.total_time_minutes for p in user_progress),
    }


def get_course_stats() -> dict:
    """Get overall course statistics."""
    total_enrollments = len(_user_progress)
    total_completions = sum(1 for p in _user_progress.values() if p.status == "completed")
    
    return {
        "total_courses": len(_courses),
        "total_modules": len(_modules),
        "total_labs": len(_labs),
        "total_quizzes": len(_quizzes),
        "total_ctf_challenges": len(_ctf_challenges),
        "total_badges": len(_badges),
        "total_enrollments": total_enrollments,
        "total_completions": total_completions,
        "completion_rate": round((total_completions / max(total_enrollments, 1)) * 100, 2),
    }


def get_recommended_courses(user_id: str) -> list:
    """Get personalized course recommendations for a user."""
    user_progress = {p.course_id: p for p in _user_progress.values() if p.user_id == user_id}
    
    recommendations = []
    for course_id, course in _courses.items():
        if course_id not in user_progress:
            recommendations.append({
                "course_id": course_id,
                "title": course.title,
                "category": course.category.value,
                "difficulty": course.difficulty.value,
                "duration_hours": course.duration_hours,
                "icon": course.icon,
                "reason": "Not yet started",
            })
    
    # Sort by difficulty level
    difficulty_order = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}
    recommendations.sort(key=lambda x: difficulty_order.get(x["difficulty"], 1))
    
    return recommendations[:5]


def search_courses(query: str) -> list:
    """Search courses by title, description, or category."""
    query_lower = query.lower()
    results = []
    
    for course in _courses.values():
        if (query_lower in course.title.lower() or
            query_lower in course.description.lower() or
            query_lower in course.category.value.lower()):
            results.append(course.to_dict())
    
    return results
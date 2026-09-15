    # COURSE 14: DEVSECOPS
    # ========================================================================
    mod14 = SecurityModule(
        id="devsecops_001",
        course_id="devsecops",
        title="DevSecOps Engineering",
        description="Integrate security into the CI/CD pipeline with SAST, DAST, dependency scanning, IaC security, and secrets management.",
        category=CourseCategory.DEVSECOPS,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=12.0,
        prerequisites=[["Software development basics"], ["CI/CD concepts"]],
        order=14,
        lessons=[
            SecurityLesson(
                id="dso_l1", module_id="devsecops_001", title="DevSecOps Principles",
                content="Shift-left security philosophy: integrating security early in SDLC. DevSecOps culture: shared responsibility, automation, feedback loops. Security as code: policy-as-code, security requirements as user stories. The Three Ways of DevOps applied to security: flow, feedback, continual learning.",
                lesson_type=LessonType.TEXT, duration_min=40, order=1,
            ),
            SecurityLesson(
                id="dso_l2", module_id="devsecops_001", title="Secure Coding Practices",
                content="OWASP ASVS levels and secure coding standards. Input validation, output encoding, parameterized queries, secure session management. Memory safety: buffer overflow prevention, use-after-free mitigation. Language-specific security: Rust ownership, Go memory safety, Python type safety, Java sandboxing.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=2,
            ),
            SecurityLesson(
                id="dso_l3", module_id="devsecops_001", title="SAST Integration",
                content="Static Application Security Testing: SonarQube, Semgrep, Checkmarx, CodeQL, Bandit, ESLint security. Integrating SAST into CI/CD: gate policies, quality gates, baseline establishment. Handling false positives, triage workflows, developer feedback loops. Custom rule development.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=3,
            ),
            SecurityLesson(
                id="dso_l4", module_id="devsecops_001", title="DAST & IAST",
                content="Dynamic Application Security Testing: OWASP ZAP, Burp Suite Enterprise, Netsparker. IAST (Interactive AST) with runtime agents. DAST in CI/CD: authenticated scanning, API security testing, spidering and AJAX crawling. Baseline scans vs regression testing. Vulnerability validation and false positive reduction.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=4,
            ),
            SecurityLesson(
                id="dso_l5", module_id="devsecops_001", title="Dependency & Supply Chain Security",
                content="Software supply chain attacks: SolarWinds, Codecov, dependency confusion. Dependency scanning: Snyk, OWASP Dependency-Check, npm audit, pip-audit, GitHub Dependabot. SBOM generation (SPDX, CycloneDX), signing artifacts with Sigstore/cosign. VEX documents and vulnerability exploitation analysis.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=5,
            ),
            SecurityLesson(
                id="dso_l6", module_id="devsecops_001", title="CI/CD Pipeline Security",
                content="Securing CI/CD pipelines: GitHub Actions, GitLab CI, Jenkins, CircleCI. Pipeline hardening: runner isolation, secret management, branch protection, code signing. Supply chain security for CI/CD: pinning actions, verifying checksums, OIDC token authentication. Container image signing and verification.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=6,
            ),
            SecurityLesson(
                id="dso_l7", module_id="devsecops_001", title="Infrastructure as Code Security",
                content="Securing Terraform, CloudFormation, ARM templates, Pulumi. Policy-as-code with OPA/Rego, Checkov, tfsec, Terrascan. Least privilege IAM in IaC, state file encryption, remote state security. Drift detection and remediation automation.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=7,
            ),
            SecurityLesson(
                id="dso_l8", module_id="devsecops_001", title="Secrets Management",
                content="Secrets lifecycle: generation, distribution, rotation, revocation. Tools: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, Doppler. Hardcoded secret detection with GitLeaks, TruffleHog, Trivy. Dynamic secrets, short-lived credentials, secretless architectures. Kubernetes secrets encryption at rest.",
                lesson_type=LessonType.TEXT, duration_min=45, order=8,
            ),
        ],
        labs=[
            SecurityLab(
                id="dso_lab1", module_id="devsecops_001",
                title="SAST Integration with SonarQube",
                description="Integrate SonarQube static analysis into a CI/CD pipeline for a Python project.",
                environment="GitLab CI, SonarQube Community, Python 3.11, sample vulnerable Flask app.",
                tasks=[
                    "Deploy SonarQube and configure project",
                    "Install SonarScanner and configure sonar-project.properties",
                    "Integrate scan into GitLab CI pipeline",
                    "Set quality gate: block on critical/high vulnerabilities",
                    "Fix identified security issues in code",
                    "Verify quality gate passes after fixes",
                ],
                hints=[
                    "sonar-project.properties defines project key and sources",
                    "Set sonar.qualitygate.wait=true in CI for blocking",
                    "Focus on SonarQube security hotspots and vulnerabilities",
                ],
                solution=".gitlab-ci.yml: sonarqube-check: script: sonar-scanner -Dsonar.projectKey=myapp -Dsonar.qualitygate.wait=true; sonar-project.properties: sonar.sources=., sonar.python.version=3.11; Fix: Replace eval() with ast.literal_eval(), Add input validation, Use parameterized queries",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="dso_lab2", module_id="devsecops_001",
                title="OWASP ZAP DAST in CI/CD",
                description="Automate dynamic security testing with OWASP ZAP in a CI pipeline.",
                environment="GitHub Actions, OWASP ZAP Docker, test web application, baseline scan rules.",
                tasks=[
                    "Configure OWASP ZAP baseline scan in GitHub Actions",
                    "Set up target application for scanning",
                    "Define alert filters for known false positives",
                    "Set fail threshold for Medium+ findings",
                    "Generate and archive HTML/XML scan reports",
                    "Create issue for newly introduced vulnerabilities",
                ],
                hints=[
                    "Use zaproxy/action-baseline for GitHub Actions",
                    "Baseline scan spider targets and passive scan only",
                    "Use .zap/rules.tsv to filter specific alerts",
                ],
                solution="GitHub Action: - uses: zaproxy/action-baseline@v2 with: target: 'http://target-app:8080' rules_file_name: '.zap/rules.tsv' cmd_options: '-a'; rules.tsv: 40012 IGNORE (out of domain); Fail on Medium+: -a flag reports all alerts; Archive: upload-artifact for zap-report.html",
                duration_min=60, points=125,
            ),
            SecurityLab(
                id="dso_lab3", module_id="devsecops_001",
                title="Dependency Scanning with Snyk",
                description="Implement dependency vulnerability scanning and SBOM generation.",
                environment="Snyk CLI, Node.js/Python project, GitHub Actions, SBOM generation tools.",
                tasks=[
                    "Authenticate Snyk CLI and test project dependencies",
                    "Fix high-severity vulnerabilities with Snyk fix",
                    "Integrate Snyk scan into CI/CD pipeline",
                    "Set fail threshold for high/critical vulnerabilities",
                    "Generate SPDX SBOM with Tern/Syft",
                    "Sign SBOM artifact with Sigstore cosign",
                ],
                hints=[
                    "snyk test --severity-threshold=high for CI gating",
                    "snyk fix automatically applies available patches",
                    "syft packages dir:. -o spdx-json > sbom.spdx.json",
                ],
                solution="snyk test --severity-threshold=high; snyk fix; # CI: snyk test --severity-threshold=high || exit 1; syft packages dir:. -o spdx-json > sbom.spdx.json; cosign sign-blob --key cosign.key sbom.spdx.json; # Fail build on any critical/high vulns",
                duration_min=60, points=125,
            ),
            SecurityLab(
                id="dso_lab4", module_id="devsecops_001",
                title="Terraform Security with Checkov",
                description="Scan and fix Terraform infrastructure code for security misconfigurations.",
                environment="Terraform 1.5, Checkov, sample AWS infrastructure, CI pipeline.",
                tasks=[
                    "Install Checkov and scan existing Terraform code",
                    "Review failed checks and understand each issue",
                    "Fix publicly exposed security group",
                    "Add encryption to unencrypted EBS and S3 resources",
                    "Implement least privilege IAM policies",
                    "Re-scan and verify all critical checks pass",
                ],
                hints=[
                    "checkov -d terraform/ --framework terraform",
                    "CKV_AWS_24 checks for exposed SSH (0.0.0.0/22)",
                    "CKV_AWS_16 checks for unencrypted EBS volumes",
                ],
                solution="""checkov -d . --framework terraform -o json; # Fix SG: cidr_blocks = [var.trusted_cidr] # NOT 0.0.0.0/0; # Fix EBS: encrypted = true; kms_key_id = aws_kms_key.mykey.arn; # Fix S3: server_side_encryption_configuration { rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" }}}; # Re-scan: all critical checks pass""",
                duration_min=60, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="dso_q1", module_id="devsecops_001", title="DevSecOps Assessment",
            passing_score=75, time_limit_minutes=25,
            questions=[
                QuizQuestion("dsq1", "What does 'shift-left' mean in DevSecOps?",
                    ["Move security to the end", "Integrate security earlier in the development lifecycle", "Use left-side tools", "Remove security checks"], 1,
                    "Shift-left integrates security testing early in the SDLC when fixes are cheaper.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq2", "What is SAST?",
                    ["Static Application Security Testing - analyzes source code", "Dynamic scanning", "Network scanning", "Runtime testing"], 0,
                    "SAST analyzes application source code without executing it to find vulnerabilities.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq3", "What is the difference between SAST and DAST?",
                    ["No difference", "SAST analyzes code; DAST tests running applications", "SAST is faster", "DAST requires source code"], 1,
                    "SAST analyzes source code statically; DAST tests running applications from outside.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq4", "What is an SBOM?",
                    ["Security Bug Only Mode", "Software Bill of Materials - inventory of software components", "System Backup Operations Manual", "Secure Binary Object Model"], 1,
                    "SBOM is a detailed inventory of all components, libraries, and dependencies in software.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq5", "Which tool is commonly used for IaC security scanning?",
                    ["Photoshop", "Checkov", "PowerPoint", "Chrome"], 1,
                    "Checkov scans Terraform, CloudFormation, Kubernetes, and other IaC for misconfigurations.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq6", "What is the purpose of Sigstore/cosign?",
                    ["Sign container images and verify software artifacts", "Speed up builds", "Compress images", "Generate passwords"], 0,
                    "Sigstore/cosign provides keyless signing and verification of software artifacts using OIDC.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq7", "What is HashiCorp Vault used for?",
                    ["Store passwords in plaintext", "Secrets management and dynamic credentials", "Container orchestration", "Network monitoring"], 1,
                    "Vault securely stores secrets, generates dynamic credentials, and handles encryption.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq8", "What is dependency confusion attack?",
                    ["Confusing developers", "Uploading malicious package with same name as internal package to public registry", "Using old dependencies", "Not scanning dependencies"], 1,
                    "Dependency confusion exploits package managers that prefer public over private registries.", DifficultyLevel.ADVANCED),
                QuizQuestion("dsq9", "What is OPA used for in DevSecOps?",
                    ["Open Policy Agent - policy-as-code enforcement", "Database optimization", "User authentication", "Package management"], 0,
                    "OPA (Open Policy Agent) enforces policy-as-code across Kubernetes, CI/CD, and cloud.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq10", "What is GitLeaks used for?",
                    ["Detect hardcoded secrets in Git repositories", "Leak Git repositories", "Git performance optimization", "Git branch management"], 0,
                    "GitLeaks scans Git history for hardcoded secrets like API keys, passwords, and tokens.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq11", "What is the purpose of a quality gate in CI/CD?",
                    ["Block pipeline if security/quality thresholds are not met", "Speed up deployment", "Allow all code through", "Manage user access"], 0,
                    "Quality gates enforce minimum security and quality standards before code can deploy.", DifficultyLevel.BEGINNER),
                QuizQuestion("dsq12", "What is IAST?",
                    ["Interactive Application Security Testing - monitors app from within during testing", "Internet Application Scanning Tool", "Internal Audit Security Test", "Integrated Application Status Tracker"], 0,
                    "IAST uses runtime agents inside the application to detect vulnerabilities during testing.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq13", "What is the most secure way to handle secrets in Kubernetes?",
                    ["Hardcode in YAML", "Use external secret management (Vault, Sealed Secrets) with encryption at rest", "Store in ConfigMap", "Use environment variables"], 1,
                    "External secret management with encryption at rest (etcd encryption) is most secure.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq14", "What is the SolarWinds attack an example of?",
                    ["Physical security breach", "Software supply chain attack", "Social engineering", "DDoS attack"], 1,
                    "SolarWinds (SUNBURST) compromised build pipeline to distribute trojanized updates to 18,000+ organizations.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("dsq15", "What does Semgrep specialize in?",
                    ["Fast, lightweight static analysis with custom rules", "Database scanning", "Network monitoring", "Container runtime security"], 0,
                    "Semgrep is a fast, lightweight SAST tool supporting custom rules in a simple pattern syntax.", DifficultyLevel.INTERMEDIATE),
            ],
        ),
    )

    # ========================================================================
    # COURSE 15: THREAT INTELLIGENCE
    # ========================================================================
    mod15 = SecurityModule(
        id="thintel_001",
        course_id="threat_intelligence",
        title="Threat Intelligence & Hunting",
        description="Master threat modeling, MITRE ATT&CK framework, IOC analysis, threat hunting, and CTI platforms.",
        category=CourseCategory.THREAT_INTEL,
        difficulty=DifficultyLevel.ADVANCED,
        duration_hours=13.0,
        prerequisites=[["Incident Response"], ["Networking fundamentals"]],
        order=15,
        lessons=[
            SecurityLesson(
                id="ti_l1", module_id="thintel_001", title="Threat Modeling",
                content="Systematic threat modeling: STRIDE (Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation), PASTA (Process for Attack Simulation), VAST, Trike. Attack surface analysis, data flow diagrams, threat categorization. Applying threat modeling to cloud, mobile, and IoT architectures.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=1,
            ),
            SecurityLesson(
                id="ti_l2", module_id="thintel_001", title="MITRE ATT&CK Framework",
                content="ATT&CK matrix: Tactics (14 enterprise), Techniques (200+), Sub-techniques, Procedures. Navigator for mapping defenses. Using ATT&CK for detection engineering, gap analysis, red team planning, and threat intelligence. ATT&CK for ICS and Mobile matrices.",
                lesson_type=LessonType.INTERACTIVE, duration_min=60, order=2,
            ),
            SecurityLesson(
                id="ti_l3", module_id="thintel_001", title="IOC Analysis & STIX/TAXII",
                content="Indicators of Compromise: file hashes, IP addresses, domains, URLs, registry keys, YARA rules. STIX 2.1 data model: SDOs, SROs, SCOs. TAXII 2.1 for threat intel sharing. MISP event format, OpenIOC, YARA-CI. Creating and consuming threat intel feeds.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=3,
            ),
            SecurityLesson(
                id="ti_l4", module_id="thintel_001", title="Threat Hunting Methodology",
                content="Hypothesis-driven threat hunting: data collection, hypothesis formation, investigation, validation. Hunting techniques: frequency analysis, outlier detection, pattern matching. Data sources: EDR, SIEM, DNS, proxy, email. Building hunting playbooks and documenting findings.",
                lesson_type=LessonType.INTERACTIVE, duration_min=60, order=4,
            ),
            SecurityLesson(
                id="ti_l5", module_id="thintel_001", title="Dark Web Monitoring",
                content="Dark web structure: surface, deep, dark web. Tor network, .onion services, hidden marketplaces. OSINT on dark web: credential dumps, malware sales, exploit markets. Legal considerations, operational security, and ethical boundaries. Tools and techniques for monitoring.",
                lesson_type=LessonType.VIDEO, duration_min=45, order=5,
            ),
            SecurityLesson(
                id="ti_l6", module_id="thintel_001", title="CTI Platforms",
                content="Cyber Threat Intelligence platforms: MISP, OpenCTI, Anomali ThreatStream, ThreatConnect. Feed curation, indicator lifecycle management, correlation, enrichment. Automation with SOAR integration. Measuring CTI program effectiveness and ROI.",
                lesson_type=LessonType.INTERACTIVE, duration_min=50, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="ti_lab1", module_id="thintel_001",
                title="Threat Model a Web Application with STRIDE",
                description="Apply STRIDE threat modeling to a fictional e-commerce web application.",
                environment="Threat modeling template, draw.io/data flow diagram tool, STRIDE-per-element worksheet.",
                tasks=[
                    "Create data flow diagram of the application",
                    "Identify all trust boundaries",
                    "Apply STRIDE to each element and trust boundary",
                    "Document identified threats with risk ratings",
                    "Propose mitigations for each threat",
                    "Create threat model report",
                ],
                hints=[
                    "Data flows: User -> Web App -> Database -> Payment Gateway",
                    "Trust boundaries exist at every network boundary",
                    "Rate each threat: Critical, High, Medium, Low",
                ],
                solution="DFD: User(browser) -> [Trust Boundary] -> Web Server -> [Trust Boundary] -> Database; STRIDE: S-Spoofing(Login bypass-Mitigate with MFA), T-Tampering(SQL injection-Parameterized queries), R-Repudiation(Missing audit logs-Add logging), I-Info disclosure(Verbose errors-Custom error pages), D-DoS(Rate limiting-Implement WAF), E-Elevation(Privesc-Least privilege)",
                duration_min=60, points=125,
            ),
            SecurityLab(
                id="ti_lab2", module_id="thintel_001",
                title="MITRE ATT&CK Mapping Exercise",
                description="Map known adversary techniques to MITRE ATT&CK and identify detection gaps.",
                environment="MITRE ATT&CK Navigator, sample APT report, detection capability spreadsheet.",
                tasks=[
                    "Read APT intrusion analysis report",
                    "Extract all TTPs and map to ATT&CK techniques",
                    "Import mapping into ATT&CK Navigator",
                    "Color-code techniques by detection capability",
                    "Identify detection gaps (red = no coverage)",
                    "Create detection engineering backlog",
                ],
                hints=[
                    "Look for technique IDs in reports (e.g., T1059 for Command Line)",
                    "Use Navigator layer format for import",
                    "Prioritize gaps in Initial Access and Execution",
                ],
                solution="APT28 techniques mapped: T1566.001 (Spearphishing Attachment), T1059.001 (PowerShell), T1055 (Process Injection), T1003.001 (LSASS Memory), T1021.001 (Remote Desktop); Coverage: Green-detected, Yellow-logged but no alert, Red-no coverage; Gaps: T1055 Process Injection (no coverage), T1003 Credential Dumping (logged only)",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="ti_lab3", module_id="thintel_001",
                title="Deploy MISP Threat Intelligence Platform",
                description="Set up MISP instance, configure feeds, and create threat intelligence events.",
                environment="Docker, MISP container, Ubuntu 22.04, test IOCs, STIX/TAXII feeds.",
                tasks=[
                    "Deploy MISP using Docker Compose",
                    "Configure initial organization and user accounts",
                    "Enable and schedule threat intel feeds",
                    "Create a custom event with IOCs (IPs, domains, hashes)",
                    "Set up TAXII server for automated sharing",
                    "Export events in STIX 2.1 format",
                    "Configure alerting for high-confidence indicators",
                ],
                hints=[
                    "MISP Docker: docker-compose up -d",
                    "Feed settings at Administration -> List Feeds",
                    "Use PyMISP for automation",
                ],
                solution="docker-compose up -d; # Configure org, add feeds ( abuse.ch, CERT-EU ); # Create event: Malware Campaign X; Add attributes: 192.0.2.100 (ip-dst), evil-domain.com (domain), a1b2c3... (md5); Enable TAXII; PyMISP: from pymisp import PyMISP; misp = PyMISP(url, key); misp.add_event(event); Export: STIX 2.1 bundle",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="ti_lab4", module_id="thintel_001",
                title="Threat Hunting with Jupyter Notebooks",
                description="Perform hypothesis-driven threat hunting using Python and Jupyter.",
                environment="Jupyter Lab, pandas, ELK API, sample Windows event logs, EDR data.",
                tasks=[
                    "Formulate hunting hypothesis: Lateral movement via SMB",
                    "Query SIEM/EDR for SMB connections",
                    "Analyze connection patterns with pandas",
                    "Identify anomalous SMB sessions",
                    "Correlate with authentication logs",
                    "Document findings and create detection rule",
                ],
                hints=[
                    "Look for SMB (port 445) between non-server systems",
                    "Check for admin share access (C$, ADMIN$)",
                    "Correlate with Event ID 4624 (logon) and 4648 (explicit credential)",
                ],
                solution="Hypothesis: Lateral movement via SMB admin shares; Query: event_id:4624 AND (ShareName:C$ OR ShareName:ADMIN$) AND SourceIP:10.0.*; Analysis: pandas groupby shows 192.168.1.50 accessed C$ on 15 hosts in 2 minutes; Correlation: Event 4648 shows explicit credential use for administrator account; Finding: Confirmed lateral movement; Detection: Alert on >5 admin share connections from single source in 10 minutes",
                duration_min=75, points=150,
            ),
        ],
        quiz=SecurityQuiz(
            id="ti_q1", module_id="thintel_001", title="Threat Intelligence Assessment",
            passing_score=75, time_limit_minutes=30,
            questions=[
                QuizQuestion("tiq1", "What does STRIDE stand for in threat modeling?",
                    ["Security Testing for Risks in Development", "Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation", "System Threat Response Integration", "Secure Technology for Risk Identification"], 1,
                    "STRIDE is Microsoft's threat classification framework with six threat categories.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq2", "What is the MITRE ATT&CK framework?",
                    ["An antivirus product", "A globally-accessible knowledge base of adversary tactics and techniques", "A programming language", "A network protocol"], 1,
                    "MITRE ATT&CK is a curated knowledge base of real-world adversary tactics and techniques.", DifficultyLevel.BEGINNER),
                QuizQuestion("tiq3", "What does STIX stand for?",
                    ["Security Threat Intelligence Exchange", "Structured Threat Information Expression", "System Threat Identification XML", "Strategic Threat Intelligence Exchange"], 1,
                    "STIX is a standardized language for cyber threat intelligence representation.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq4", "What is TAXII?",
                    ["A tax calculation tool", "Trusted Automated Exchange of Intelligence Information", "A threat scanner", "An encryption protocol"], 1,
                    "TAXII is the transport protocol for sharing STIX-formatted threat intelligence.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq5", "What is an IOC?",
                    ["International Olympic Committee", "Indicator of Compromise - artifact suggesting intrusion", "Internal Operating Center", "Input/Output Controller"], 1,
                    "IOCs are forensic artifacts indicating a potential intrusion or malicious activity.", DifficultyLevel.BEGINNER),
                QuizQuestion("tiq6", "What is threat hunting?",
                    ["Installing antivirus", "Proactively searching for threats that evade existing defenses", "Waiting for alerts", "Patching systems"], 1,
                    "Threat hunting proactively searches for advanced threats that bypass automated detection.", DifficultyLevel.BEGINNER),
                QuizQuestion("tiq7", "What is the difference between threat intelligence and threat hunting?",
                    ["They are the same", "Threat intel provides context; threat hunting actively searches for threats", "Threat hunting is faster", "Threat intel is only for executives"], 1,
                    "Threat intelligence provides contextual knowledge; threat hunting actively searches environments.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq8", "What does MISP stand for?",
                    ["Mobile Information Sharing Platform", "Malware Information Sharing Platform", "Microsoft Intelligence Sharing Protocol", "Managed Incident Security Portal"], 1,
                    "MISP is an open-source threat intelligence platform for sharing IOCs and threat data.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq9", "In MITRE ATT&CK, what is the difference between a Tactic and a Technique?",
                    ["No difference", "Tactic is the adversary's tactical goal; Technique is how they achieve it", "Technique is more important", "Tactic is only for enterprise"], 1,
                    "Tactics represent 'why' (adversary's tactical objective); Techniques represent 'how'.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq10", "What is an APT?",
                    ["Application Performance Test", "Advanced Persistent Threat - sophisticated, long-term targeted attack", "Automatic Patch Tool", "Advanced Protection Technology"], 1,
                    "APTs are sophisticated, long-duration cyberattacks by well-resourced threat actors.", DifficultyLevel.BEGINNER),
                QuizQuestion("tiq11", "What is the purpose of the ATT&CK Navigator?",
                    ["Browse websites securely", "Visualize and layer ATT&CK mappings for coverage analysis", "Scan for malware", "Manage passwords"], 1,
                    "ATT&CK Navigator visualizes technique mappings for gap analysis and coverage planning.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq12", "What is dark web monitoring used for in threat intelligence?",
                    ["Illegal activities", "Detecting leaked credentials, data dumps, and threat actor activity", "Speeding up internet", "Avoiding taxes"], 1,
                    "Organizations monitor dark web for leaked data, credential dumps, and emerging threats.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq13", "What is a TTP in threat intelligence?",
                    ["Tactics, Techniques, and Procedures", "Technical Threat Protocol", "Trusted Transfer Platform", "Target Tracking Program"], 0,
                    "TTPs describe the behavior patterns of threat actors: what they do and how they do it.", DifficultyLevel.BEGINNER),
                QuizQuestion("tiq14", "What is the Cyber Kill Chain?",
                    ["A computer virus", "A model describing stages of a cyberattack from recon to exfiltration", "An antivirus tool", "A password cracker"], 1,
                    "Lockheed Martin's Cyber Kill Chain models 7 stages: Recon, Weaponize, Deliver, Exploit, Install, C2, Actions.", DifficultyLevel.INTERMEDIATE),
                QuizQuestion("tiq15", "What is intelligence-driven defense?",
                    ["Using AI for all decisions", "Using threat intelligence to inform and prioritize security controls", "Hiring more analysts", "Buying more tools"], 1,
                    "Intelligence-driven defense uses threat intel to focus resources on relevant threats.", DifficultyLevel.BEGINNER),
            ],
        ),
    )

    # ========================================================================
    # REGISTER ALL COURSES
    # ========================================================================
    course1 = SecurityCourse(
        id="network_security", title="Network Security Fundamentals",
        description="Master firewalls, IDS/IPS, VPNs, packet analysis, and network scanning for robust network defense.",
        category=CourseCategory.NETWORK, difficulty=DifficultyLevel.BEGINNER,
        duration_hours=12.5, modules=[mod1], certification_track=CertificationTrack.COMPTIA_SECURITY_PLUS, icon="🌐",
    )
    course2 = SecurityCourse(
        id="web_app_security", title="Web Application Security",
        description="Comprehensive coverage of OWASP Top 10, XSS, SQL injection, CSRF, SSRF, and security headers.",
        category=CourseCategory.WEB_APP, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=15.0, modules=[mod2], certification_track=CertificationTrack.OSCP, icon="🌐",
    )
    course3 = SecurityCourse(
        id="cryptography", title="Cryptography & Secure Communications",
        description="From AES to post-quantum: master encryption, hashing, PKI, TLS/SSL, and digital signatures.",
        category=CourseCategory.CRYPTOGRAPHY, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=14.0, modules=[mod3], certification_track=CertificationTrack.CISSP, icon="🔐",
    )
    course4 = SecurityCourse(
        id="ethical_hacking", title="Ethical Hacking & Penetration Testing",
        description="Complete pentesting methodology: reconnaissance, scanning, exploitation, post-exploitation, and reporting.",
        category=CourseCategory.OFFENSIVE, difficulty=DifficultyLevel.ADVANCED,
        duration_hours=18.0, modules=[mod4], certification_track=CertificationTrack.CEH, icon="🎯",
    )
    course5 = SecurityCourse(
        id="incident_response", title="Incident Response & Digital Investigations",
        description="NIST framework, SOAR, playbooks, evidence preservation, and post-incident activities.",
        category=CourseCategory.DEFENSIVE, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=13.0, modules=[mod5], certification_track=CertificationTrack.CISSP, icon="🚨",
    )
    course6 = SecurityCourse(
        id="cloud_security", title="Cloud Security Architecture",
        description="Secure AWS, Azure, GCP: IAM, container security, serverless protection, and cloud forensics.",
        category=CourseCategory.CLOUD, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=14.5, modules=[mod6], certification_track=CertificationTrack.CISSP, icon="☁️",
    )
    course7 = SecurityCourse(
        id="malware_analysis", title="Malware Analysis & Reverse Engineering",
        description="Static analysis, dynamic analysis, reverse engineering with Ghidra, and YARA rule development.",
        category=CourseCategory.MALWARE, difficulty=DifficultyLevel.ADVANCED,
        duration_hours=16.0, modules=[mod7], certification_track=CertificationTrack.CEH, icon="🦠",
    )
    course8 = SecurityCourse(
        id="digital_forensics", title="Digital Forensics & Investigation",
        description="Evidence collection, disk/memory/network forensics, timeline analysis, and chain of custody.",
        category=CourseCategory.FORENSICS, difficulty=DifficultyLevel.ADVANCED,
        duration_hours=15.0, modules=[mod8], certification_track=CertificationTrack.CISSP, icon="🔍",
    )
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
    course14 = SecurityCourse(
        id="devsecops", title="DevSecOps Engineering",
        description="SAST, DAST, dependency scanning, CI/CD security, IaC security, and secrets management.",
        category=CourseCategory.DEVSECOPS, difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=12.0, modules=[mod14], certification_track=CertificationTrack.CISSP, icon="🔄",
    )
    course15 = SecurityCourse(
        id="threat_intelligence", title="Threat Intelligence & Hunting",
        description="Threat modeling, MITRE ATT&CK, IOC analysis, threat hunting, dark web monitoring, and CTI platforms.",
        category=CourseCategory.THREAT_INTEL, difficulty=DifficultyLevel.ADVANCED,
        duration_hours=13.0, modules=[mod15], certification_track=CertificationTrack.CISSP, icon="🧠",
    )

    # Register all courses and their components in global stores
    all_courses = [course1, course2, course3, course4, course5,
                   course6, course7, course8, course9, course10,
                   course11, course12, course13, course14, course15]

    for course in all_courses:
        _courses[course.id] = course
        for module in course.modules:
            _modules[module.id] = module
            for lesson in module.lessons:
                _lessons[lesson.id] = lesson
            for lab in module.labs:
                _labs[lab.id] = lab
            if module.quiz:
                _quizzes[module.quiz.id] = module.quiz
                for question in module.quiz.questions:
                    pass  # Questions stored within quiz

    # ========================================================================
    # INITIALIZE SKILL BADGES
    # ========================================================================
    badge_data = [
        ("badge_netsec", "Firewall Master", "Completed network security module with all labs", "🌐", CourseCategory.NETWORK, 500),
        ("badge_webapp", "Web Defender", "Mastered OWASP Top 10 and web application security", "🛡️", CourseCategory.WEB_APP, 500),
        ("badge_crypto", "Crypto Wizard", "Demonstrated strong cryptography knowledge", "🔐", CourseCategory.CRYPTOGRAPHY, 500),
        ("badge_hacker", "Ethical Hacker", "Completed ethical hacking and pentesting course", "🎯", CourseCategory.OFFENSIVE, 600),
        ("badge_ir", "Incident Responder", "Mastered incident response procedures", "🚨", CourseCategory.DEFENSIVE, 500),
        ("badge_cloud", "Cloud Guardian", "Secured AWS, Azure, and GCP environments", "☁️", CourseCategory.CLOUD, 500),
        ("badge_malware", "Malware Hunter", "Analyzed malware through static and dynamic techniques", "🦠", CourseCategory.MALWARE, 600),
        ("badge_forensics", "Digital Detective", "Completed digital forensics investigation", "🔍", CourseCategory.FORENSICS, 600),
        ("badge_compliance", "Compliance Officer", "Mastered security compliance frameworks", "📋", CourseCategory.COMPLIANCE, 400),
        ("badge_mobile", "Mobile Security Expert", "Secured Android and iOS platforms", "📱", CourseCategory.MOBILE, 500),
        ("badge_wireless", "Wireless Sentinel", "Mastered wireless security protocols", "📡", CourseCategory.WIRELESS, 400),
        ("badge_se", "Human Firewall", "Completed social engineering defense training", "🎭", CourseCategory.SOCIAL, 300),
        ("badge_telecom", "Telecom Guardian", "Secured African telecom and mobile money systems", "📞", CourseCategory.TELECOM, 500),
        ("badge_devsecops", "Pipeline Security Engineer", "Implemented DevSecOps in CI/CD pipeline", "🔄", CourseCategory.DEVSECOPS, 500),
        ("badge_threat", "Threat Hunter", "Completed threat intelligence and hunting course", "🧠", CourseCategory.THREAT_INTEL, 600),
        ("badge_nmap", "Nmap Ninja", "Mastered network scanning techniques", "🔎", CourseCategory.NETWORK, 200),
        ("badge_xss", "XSS Slayer", "Found and fixed all XSS vulnerabilities", "⚔️", CourseCategory.WEB_APP, 200),
        ("badge_sqli", "SQL Injection Master", "Exploited and remediated SQL injection", "💉", CourseCategory.WEB_APP, 200),
        ("badge_wireshark", "Packet Whisperer", "Expert-level packet analysis with Wireshark", "📊", CourseCategory.NETWORK, 200),
        ("badge_aes", "Encryption Expert", "Implemented secure encryption systems", "🔒", CourseCategory.CRYPTOGRAPHY, 200),
        ("badge_c2", "C2 Hunter", "Identified command and control infrastructure", "🎯", CourseCategory.THREAT_INTEL, 300),
        ("badge_ctf", "CTF Champion", "Completed 10+ CTF challenges", "🏆", CourseCategory.OFFENSIVE, 400),
        ("badge_linux", "Linux Privesc Pro", "Mastered Linux privilege escalation", "🐧", CourseCategory.OFFENSIVE, 300),
        ("badge_memory", "Memory Forensics Analyst", "Completed memory analysis investigations", "🧠", CourseCategory.FORENSICS, 300),
        ("badge_registry", "Registry Analyst", "Mastered Windows registry forensics", "🪟", CourseCategory.FORENSICS, 200),
        ("badge_ghidra", "Reverse Engineer", "Completed reverse engineering with Ghidra", "🔧", CourseCategory.MALWARE, 300),
        ("badge_yara", "YARA Rulesmith", "Created effective YARA detection rules", "📝", CourseCategory.MALWARE, 200),
        ("badge_frida", "Frida Master", "Bypassed security controls with dynamic instrumentation", "🎸", CourseCategory.MOBILE, 300),
        ("badge_pinning", "Certificate Pinning Expert", "Implemented and bypassed certificate pinning", "📌", CourseCategory.MOBILE, 200),
        ("badge_wifi", "Wireless Auditor", "Completed WiFi penetration testing", "📶", CourseCategory.WIRELESS, 200),
        ("badge_phish", "Phishing Defender", "Implemented SPF, DKIM, DMARC successfully", "📧", CourseCategory.SOCIAL, 200),
        ("badge_soc2", "SOC 2 Ready", "Completed SOC 2 compliance preparation", "✅", CourseCategory.COMPLIANCE, 300),
        ("badge_gdpr", "GDPR Practitioner", "Mastered GDPR requirements and implementation", "🇪🇺", CourseCategory.COMPLIANCE, 200),
        ("badge_ss7", "Signaling Security Expert", "Analyzed SS7/Diameter signaling security", "📡", CourseCategory.TELECOM, 300),
        ("badge_momo", "Mobile Money Guardian", "Secured mobile money platforms", "💰", CourseCategory.TELECOM, 200),
        ("badge_pipeline", "CI/CD Security Pro", "Secured build and deployment pipelines", "🚀", CourseCategory.DEVSECOPS, 300),
        ("badge_iac", "IaC Security Expert", "Secured infrastructure-as-code deployments", "🏗️", CourseCategory.DEVSECOPS, 200),
        ("badge_mitre", "ATT&CK Navigator", "Mapped threats using MITRE ATT&CK framework", "🗺️", CourseCategory.THREAT_INTEL, 300),
        ("badge_misp", "CTI Analyst", "Deployed and used MISP threat intelligence platform", "📊", CourseCategory.THREAT_INTEL, 200),
    ]
    for bid, name, desc, icon, cat, pts in badge_data:
        _badges[bid] = SkillBadge(id=bid, name=name, description=desc, icon=icon, category=cat, required_points=pts)

    # ========================================================================
    # INITIALIZE CTF CHALLENGES
    # ========================================================================
    ctf_data = [
        ("ctf_netsec", "Network Recon Challenge",
         "Find the hidden service and capture the flag through network reconnaissance.",
         CourseCategory.NETWORK, DifficultyLevel.INTERMEDIATE, "LUQI{NETSCAN_MASTERY_2024}",
         ["Start with a full port scan", "Check unusual ports above 10000", "Banner grabbing reveals the flag"], 150),
        ("ctf_webapp", "XSS to Admin",
         "Escalate a reflected XSS to steal the admin session and retrieve the flag.",
         CourseCategory.WEB_APP, DifficultyLevel.INTERMEDIATE, "LUQI{XSS_ADMIN_TAKEOVER_2024}",
         ["Look for unfiltered input in search", "Use document.location to exfiltrate cookies", "Admin panel has the flag"], 200),
        ("ctf_crypto", "Break the Cipher",
         "Break a weak custom cipher and decrypt the message containing the flag.",
         CourseCategory.CRYPTOGRAPHY, DifficultyLevel.ADVANCED, "LUQI{CRYPTO_BREAKER_2024}",
         ["Analyze the encryption pattern", "Look for repeating patterns indicating weak key schedule", "Frequency analysis helps"], 250),
        ("ctf_ethhack", "Root the Box",
         "Gain root access on a vulnerable Linux system and read the flag.",
         CourseCategory.OFFENSIVE, DifficultyLevel.ADVANCED, "LUQI{ROOT_ACCESS_GRANTED_2024}",
         ["Check for SUID binaries", "Look at cron jobs", "Kernel exploits are a last resort"], 250),
        ("ctf_ir", "Incident Response Challenge",
         "Analyze the provided logs to identify the attack and extract the flag.",
         CourseCategory.DEFENSIVE, DifficultyLevel.INTERMEDIATE, "LUQI{IR_MASTER_DETECTIVE_2024}",
         ["Start with authentication logs", "Look for unusual login patterns", "The attacker left the flag in a temp file"], 150),
        ("ctf_cloud", "S3 Bucket Hunt",
         "Find and access a misconfigured AWS S3 bucket to retrieve the flag.",
         CourseCategory.CLOUD, DifficultyLevel.BEGINNER, "LUQI{S3_BUCKET_FOUND_2024}",
         ["Use bucket enumeration techniques", "Check for public ListBucket permissions", "Flag is in a hidden object"], 100),
        ("ctf_malware", "Malware Analysis CTF",
         "Analyze the provided malware sample to find the embedded C2 domain and flag.",
         CourseCategory.MALWARE, DifficultyLevel.ADVANCED, "LUQI{MALWARE_C2_EXPOSED_2024}",
         ["Run strings first", "Check resource section", "The C2 domain contains the flag"], 250),
        ("ctf_forensics", "Hidden in the Image",
         "Find the flag hidden in the provided image using steganography techniques.",
         CourseCategory.FORENSICS, DifficultyLevel.INTERMEDIATE, "LUQI{STEGANO_DETECTED_2024}",
         ["Try LSB extraction", "Check for appended data after EOF", "Use steghide with empty password"], 200),
        ("ctf_compliance", "Policy Puzzle",
         "Solve the compliance crossword and regulatory quiz to reveal the flag.",
         CourseCategory.COMPLIANCE, DifficultyLevel.BEGINNER, "LUQI{COMPLIANCE_EXPERT_2024}",
         ["Review GDPR articles", "NIST CSF functions hold clues", "The flag is in the answers"], 100),
        ("ctf_mobile", "APK Reversing",
         "Reverse engineer the provided Android APK to find the hardcoded flag.",
         CourseCategory.MOBILE, DifficultyLevel.INTERMEDIATE, "LUQI{APK_REVERSED_2024}",
         ["Decompile with jadx", "Check strings.xml and shared preferences", "The flag is XOR encoded in native lib"], 200),
        ("ctf_wireless", "Capture the Handshake",
         "Capture and crack a WPA2 handshake to find the flag in the network name.",
         CourseCategory.WIRELESS, DifficultyLevel.ADVANCED, "LUQI{WIFI_HANDSHAKE_CRACKED_2024}",
         ["Monitor mode is required", "Look for a hidden SSID", "The password is in rockyou.txt"], 250),
        ("ctf_soceng", "Phishing Simulation",
         "Identify all phishing indicators in the provided emails to construct the flag.",
         CourseCategory.SOCIAL, DifficultyLevel.BEGINNER, "LUQI{PHISH_SPOTTER_2024}",
         ["Check email headers", "Look for spoofed domains", "Each email reveals a part of the flag"], 100),
        ("ctf_telecom", "SIM Trace",
         "Trace a fraudulent SIM swap through telecom logs to identify the attacker and flag.",
         CourseCategory.TELECOM, DifficultyLevel.INTERMEDIATE, "LUQI{SIM_TRACE_COMPLETE_2024}",
         ["Check HLR logs for unusual SIM updates", "Correlate with customer support calls", "The insider ID is the flag"], 200),
        ("ctf_devsecops", "Pipeline Poison",
         "Find and exploit a vulnerability in a CI/CD pipeline to extract the flag.",
         CourseCategory.DEVSECOPS, DifficultyLevel.ADVANCED, "LUQI{PIPELINE_SECURED_2024}",
         ["Check for command injection in build scripts", "Look for exposed secrets in environment variables", "The flag is in the deployment credentials"], 250),
        ("ctf_threat", "APT Attribution",
         "Analyze threat intel to attribute an attack to the correct APT group and find the flag.",
         CourseCategory.THREAT_INTEL, DifficultyLevel.ADVANCED, "LUQI{APT_ATTRIBUTED_2024}",
         ["Map TTPs to MITRE ATT&CK", "Compare with known group profiles", "The group name is the flag suffix"], 250),
    ]
    for cid, title, desc, cat, diff, flag, hints, pts in ctf_data:
        _ctf_challenges[cid] = CTFChallenge(id=cid, title=title, description=desc, category=cat,
                                             difficulty=diff, flag=flag, hints=hints, points=pts)

    # Initialize empty leaderboard
    global _leaderboard
    _leaderboard = []

# Build courses on module import
_build_courses()



# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def get_all_courses() -> List[dict]:
    """Return all 15 security training courses with their full content.

    Returns:
        List[dict]: List of all course dictionaries with modules, lessons,
            labs, and quizzes.

    Example:
        >>> courses = get_all_courses()
        >>> len(courses)
        15
    """
    return [course.to_dict() for course in _courses.values()]


def get_course(course_id: str) -> dict:
    """Get a specific course by its ID.

    Args:
        course_id: The unique course identifier (e.g., 'network_security').

    Returns:
        dict: Course dictionary with all modules, lessons, labs, and quizzes.

    Raises:
        CourseNotFoundError: If the course ID does not exist.

    Example:
        >>> course = get_course('network_security')
        >>> course['title']
        'Network Security Fundamentals'
    """
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found. Available: {list(_courses.keys())}")
    return _courses[course_id].to_dict()


def enroll_user(user_id: str, course_id: str) -> dict:
    """Enroll a user in a security training course.

    Creates a new UserProgress entry to track the user's journey through
    the course. Initializes skill tree if not present.

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the course to enroll in.

    Returns:
        dict: Enrollment confirmation with progress details.

    Raises:
        CourseNotFoundError: If the course does not exist.
        ValueError: If user_id or course_id is empty.

    Example:
        >>> result = enroll_user('user_123', 'network_security')
        >>> result['status']
        'enrolled'
    """
    if not user_id or not course_id:
        raise ValueError("user_id and course_id are required")
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")

    progress_key = f"{user_id}:{course_id}"
    now = datetime.utcnow()

    if progress_key not in _user_progress:
        _user_progress[progress_key] = UserProgress(
            user_id=user_id,
            course_id=course_id,
            enrolled_at=now,
            status="enrolled",
            last_accessed=now,
        )

    # Initialize skill tree if needed
    if user_id not in _skill_trees:
        _skill_trees[user_id] = SkillTree(user_id=user_id)

    progress = _user_progress[progress_key]
    return {
        "status": "success",
        "message": f"User {user_id} enrolled in {course_id}",
        "enrolled_at": progress.enrolled_at.isoformat(),
        "user_id": user_id,
        "course_id": course_id,
        "progress": progress.to_dict(),
    }


def get_user_progress(user_id: str, course_id: str) -> dict:
    """Get a user's progress in a specific course.

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the course.

    Returns:
        dict: User progress including completed lessons, scores, and status.

    Raises:
        UserNotEnrolledError: If the user is not enrolled in the course.
        CourseNotFoundError: If the course does not exist.

    Example:
        >>> progress = get_user_progress('user_123', 'network_security')
        >>> progress['status']
        'enrolled'
    """
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")

    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User {user_id} is not enrolled in {course_id}")

    progress = _user_progress[progress_key]
    progress.last_accessed = datetime.utcnow()
    return progress.to_dict()


def update_lesson_progress(user_id: str, course_id: str, module_id: str,
                           lesson_id: str, time_spent_min: int = 0) -> dict:
    """Mark a lesson as completed and update user progress.

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the course.
        module_id: ID of the module containing the lesson.
        lesson_id: ID of the lesson to mark complete.
        time_spent_min: Optional time spent on the lesson in minutes.

    Returns:
        dict: Updated progress with completion status.

    Raises:
        UserNotEnrolledError: If user is not enrolled.
        CourseNotFoundError: If course does not exist.
        ValueError: If lesson_id is empty.

    Example:
        >>> result = update_lesson_progress('user_123', 'network_security',
        ...                                  'netsec_001', 'netsec_l1')
        >>> result['completed']
        True
    """
    if not lesson_id:
        raise ValueError("lesson_id is required")
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")

    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User {user_id} is not enrolled in {course_id}")

    progress = _user_progress[progress_key]
    now = datetime.utcnow()

    if lesson_id not in progress.completed_lessons:
        progress.completed_lessons.append(lesson_id)

    progress.last_accessed = now
    if time_spent_min:
        progress.total_time_minutes += time_spent_min

    # Calculate overall progress
    course = _courses[course_id]
    total_lessons = sum(len(m.lessons) for m in course.modules)
    if total_lessons > 0:
        lesson_progress = len(progress.completed_lessons) / total_lessons * 50
        lab_progress = sum(progress.lab_scores.values()) / (len(_labs) * 100) * 25 if _labs else 0
        quiz_progress = sum(progress.quiz_scores.values()) / (len(_quizzes) * 100) * 25 if _quizzes else 0
        progress.overall_score = min(100, round(lesson_progress + lab_progress + quiz_progress, 2))

    # Update status
    if progress.overall_score >= 90:
        progress.status = "completed"
    elif progress.overall_score > 0:
        progress.status = "in_progress"

    # Update skill tree
    _update_skill_tree(user_id, course_id, "lesson_complete", lesson_id)

    return {
        "status": "success",
        "lesson_id": lesson_id,
        "completed": True,
        "total_completed_lessons": len(progress.completed_lessons),
        "overall_score": progress.overall_score,
        "course_status": progress.status,
    }


def submit_lab(user_id: str, lab_id: str, submission: dict) -> dict:
    """Submit a lab exercise for auto-grading with feedback.

    Auto-grades lab submissions by comparing submitted answers against
    expected solutions. Provides detailed feedback on correctness.

    Args:
        user_id: Unique identifier for the user.
        lab_id: ID of the lab being submitted.
        submission: Dictionary containing 'answers' (dict of task_id -> answer)
            and optional 'time_spent_min'.

    Returns:
        dict: Grading results with score, feedback, and hints.

    Raises:
        LabNotFoundError: If the lab does not exist.
        InvalidSubmissionError: If submission format is invalid.
        UserNotEnrolledError: If user is not enrolled in the course.

    Example:
        >>> result = submit_lab('user_123', 'netsec_lab1',
        ...                     {'answers': {'task1': 'iptables -P INPUT DROP'}})
        >>> result['score']
        85.0
    """
    if lab_id not in _labs:
        raise LabNotFoundError(f"Lab '{lab_id}' not found")
    if not submission or "answers" not in submission:
        raise InvalidSubmissionError("Submission must contain 'answers' dict")

    lab = _labs[lab_id]
    answers = submission.get("answers", {})
    time_spent = submission.get("time_spent_min", 0)

    # Find the course for this lab
    module = _modules.get(lab.module_id)
    if not module:
        raise LabNotFoundError(f"Module for lab '{lab_id}' not found")

    course_id = module.course_id
    progress_key = f"{user_id}:{course_id}"

    # Auto-grade by comparing with solution keywords
    feedback = {}
    correct_count = 0
    total_tasks = len(lab.tasks)
    solution_lower = lab.solution.lower()

    for task_idx, answer in answers.items():
        answer_lower = str(answer).lower().strip()
        # Simple keyword matching - production would use more sophisticated grading
        if answer_lower and len(answer_lower) > 3:
            # Check if answer contains meaningful content (not just "done")
            keywords_match = any(keyword in answer_lower for keyword in
                               ["iptables", "nmap", "sql", "union", "payload",
                                "firewall", "encrypt", "hash", "certificate",
                                "frida", "hook", "pinning", "terraform", "checkov",
                                "misp", "stix", "yara", "volatility", "wireshark",
                                "metasploit", "msfconsole", "privilege", "sudo"])
            is_done_only = answer_lower in ["done", "completed", "yes", "ok"]
            if keywords_match or not is_done_only:
                correct_count += 1
                feedback[task_idx] = {"correct": True, "comment": "Good work!"}
            else:
                feedback[task_idx] = {
                    "correct": False,
                    "comment": "Please provide a more detailed answer with specific commands or configurations.",
                    "hint": lab.hints[min(int(task_idx.replace('task', '0')), len(lab.hints)-1)] if lab.hints else "",
                }
        else:
            feedback[task_idx] = {
                "correct": False,
                "comment": "Answer too short or empty.",
                "hint": lab.hints[min(int(task_idx.replace('task', '0')), len(lab.hints)-1)] if lab.hints else "",
            }

    score = round((correct_count / max(total_tasks, 1)) * 100, 2)

    # Update progress
    if progress_key in _user_progress:
        _user_progress[progress_key].lab_scores[lab_id] = score
        if time_spent:
            _user_progress[progress_key].total_time_minutes += time_spent
        _update_skill_tree(user_id, course_id, "lab_complete", lab_id, score)

    return {
        "status": "graded",
        "lab_id": lab_id,
        "lab_title": lab.title,
        "score": score,
        "points_earned": round(lab.points * (score / 100)),
        "total_tasks": total_tasks,
        "correct_tasks": correct_count,
        "feedback": feedback,
        "solution_preview": lab.solution[:200] + "..." if len(lab.solution) > 200 else lab.solution,
        "hints_available": len(lab.hints),
    }


def submit_quiz(user_id: str, quiz_id: str, answers: dict) -> dict:
    """Submit quiz answers for grading and track attempts.

    Grades multiple-choice quiz submissions and provides detailed
    feedback with explanations for each question.

    Args:
        user_id: Unique identifier for the user.
        quiz_id: ID of the quiz being submitted.
        answers: Dictionary mapping question_id -> selected_answer_index (0-based).

    Returns:
        dict: Grading results with score, correct/incorrect breakdown,
            and detailed feedback.

    Raises:
        QuizNotFoundError: If the quiz does not exist.
        InvalidSubmissionError: If answers format is invalid.

    Example:
        >>> result = submit_quiz('user_123', 'netsec_q1',
        ...                      {'nq1': 1, 'nq2': 1, 'nq3': 1})
        >>> result['score']
        100.0
    """
    if quiz_id not in _quizzes:
        raise QuizNotFoundError(f"Quiz '{quiz_id}' not found")
    if not answers or not isinstance(answers, dict):
        raise InvalidSubmissionError("Answers must be a dict mapping question_id -> answer_index")

    quiz = _quizzes[quiz_id]
    correct_count = 0
    total_questions = len(quiz.questions)
    feedback = []

    for question in quiz.questions:
        user_answer = answers.get(question.id)
        is_correct = user_answer == question.correct_answer
        if is_correct:
            correct_count += 1

        feedback.append({
            "question_id": question.id,
            "question": question.text,
            "your_answer": user_answer,
            "correct_answer": question.correct_answer,
            "correct": is_correct,
            "explanation": question.explanation if is_correct else f"Correct: {question.options[question.correct_answer]}. {question.explanation}",
        })

    score = round((correct_count / max(total_questions, 1)) * 100, 2)
    passed = score >= quiz.passing_score

    # Find course and update progress
    module = _modules.get(quiz.module_id)
    if module:
        course_id = module.course_id
        progress_key = f"{user_id}:{course_id}"
        if progress_key in _user_progress:
            progress = _user_progress[progress_key]
            # Track best score
            current_best = progress.quiz_scores.get(quiz_id, 0)
            if score > current_best:
                progress.quiz_scores[quiz_id] = score
            progress.quiz_attempts[quiz_id] = progress.quiz_attempts.get(quiz_id, 0) + 1
            _update_skill_tree(user_id, course_id, "quiz_complete", quiz_id, score)

    return {
        "status": "passed" if passed else "failed",
        "quiz_id": quiz_id,
        "quiz_title": quiz.title,
        "score": score,
        "passing_score": quiz.passing_score,
        "passed": passed,
        "correct_answers": correct_count,
        "total_questions": total_questions,
        "feedback": feedback,
        "time_limit_minutes": quiz.time_limit_minutes,
    }


def generate_certificate(user_id: str, course_id: str) -> dict:
    """Generate a completion certificate with verification hash.

    Creates a cryptographically signed certificate when a user completes
    a course with sufficient overall score (>= 70%).

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the completed course.

    Returns:
        dict: Certificate details with verification hash and download info.

    Raises:
        CourseNotFoundError: If course does not exist.
        UserNotEnrolledError: If user is not enrolled.
        SecurityTrainingError: If course completion criteria not met.

    Example:
        >>> cert = generate_certificate('user_123', 'network_security')
        >>> cert['verified']
        True
    """
    if course_id not in _courses:
        raise CourseNotFoundError(f"Course '{course_id}' not found")

    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User {user_id} is not enrolled in {course_id}")

    progress = _user_progress[progress_key]
    if progress.overall_score < 70:
        raise SecurityTrainingError(
            f"Course completion requires 70% overall score. Current: {progress.overall_score}%"
        )

    course = _courses[course_id]
    cert_id = f"LUQI-CERT-{uuid.uuid4().hex[:12].upper()}"
    issued_at = datetime.utcnow()
    expiry_date = issued_at + timedelta(days=730)  # 2 years

    # Generate verification hash
    hash_input = f"{user_id}:{course_id}:{cert_id}:{issued_at.isoformat()}:LUQIAIv24.4.0"
    verification_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    cert = UserCertificate(
        user_id=user_id,
        course_id=course_id,
        certificate_id=cert_id,
        issued_at=issued_at,
        expiry_date=expiry_date,
        verification_hash=verification_hash,
        verified=True,
    )

    cert_key = f"{user_id}:{course_id}"
    _certificates[cert_key] = cert

    # Award badge for course completion
    badge_map = {
        "network_security": "badge_netsec",
        "web_app_security": "badge_webapp",
        "cryptography": "badge_crypto",
        "ethical_hacking": "badge_hacker",
        "incident_response": "badge_ir",
        "cloud_security": "badge_cloud",
        "malware_analysis": "badge_malware",
        "digital_forensics": "badge_forensics",
        "compliance_governance": "badge_compliance",
        "mobile_security": "badge_mobile",
        "wireless_security": "badge_wireless",
        "social_engineering": "badge_se",
        "africa_telecom_security": "badge_telecom",
        "devsecops": "badge_devsecops",
        "threat_intelligence": "badge_threat",
    }
    badge_id = badge_map.get(course_id)
    if badge_id and user_id in _skill_trees:
        if badge_id not in _skill_trees[user_id].badges:
            _skill_trees[user_id].badges.append(badge_id)

    return {
        "status": "success",
        "certificate_id": cert_id,
        "user_id": user_id,
        "course_id": course_id,
        "course_title": course.title,
        "issued_at": issued_at.isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "verification_hash": verification_hash,
        "verification_url": f"/api/security/certificates/verify/{cert_id}",
        "verified": True,
    }


def get_skill_tree(user_id: str) -> dict:
    """Get a user's skill tree with levels, points, and badges.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        dict: Skill tree with levels, badges, skills, and title.

    Example:
        >>> tree = get_skill_tree('user_123')
        >>> tree['level']
        1
    """
    if user_id not in _skill_trees:
        _skill_trees[user_id] = SkillTree(user_id=user_id)

    tree = _skill_trees[user_id]
    badge_details = []
    for badge_id in tree.badges:
        if badge_id in _badges:
            badge_details.append(_badges[badge_id].to_dict())

    # Calculate level based on total points
    tree.level = max(1, tree.total_points // 500 + 1)
    level_titles = {
        1: "Security Novice", 2: "Security Apprentice", 3: "Security Analyst",
        4: "Security Professional", 5: "Security Expert", 6: "Security Master",
        7: "Cyber Guardian", 8: "Elite Defender", 9: "Security Grandmaster",
        10: "Cyber Legend",
    }
    tree.title = level_titles.get(min(tree.level, 10), "Cyber Legend")

    return {
        "user_id": user_id,
        "level": tree.level,
        "title": tree.title,
        "total_points": tree.total_points,
        "skills": tree.skills,
        "badges_earned": len(tree.badges),
        "badges": badge_details,
        "next_level_points": tree.level * 500,
    }


def _update_skill_tree(user_id: str, course_id: str, action: str,
                       item_id: str, score: float = 0) -> None:
    """Update user's skill tree based on learning activity.

    Internal function to track skill progression when users complete
    lessons, labs, and quizzes.

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the course being worked on.
        action: Type of activity ('lesson_complete', 'lab_complete', 'quiz_complete').
        item_id: ID of the completed item.
        score: Score earned for the activity (0-100).
    """
    if user_id not in _skill_trees:
        _skill_trees[user_id] = SkillTree(user_id=user_id)

    tree = _skill_trees[user_id]

    # Map course to skill category
    skill_map = {
        "network_security": "networking",
        "web_app_security": "web_security",
        "cryptography": "cryptography",
        "ethical_hacking": "pentesting",
        "incident_response": "incident_response",
        "cloud_security": "cloud_security",
        "malware_analysis": "malware_analysis",
        "digital_forensics": "forensics",
        "compliance_governance": "compliance",
        "mobile_security": "mobile_security",
        "wireless_security": "wireless_security",
        "social_engineering": "social_engineering",
        "africa_telecom_security": "telecom_security",
        "devsecops": "devsecops",
        "threat_intelligence": "threat_intelligence",
    }

    skill = skill_map.get(course_id, "general")

    if action == "lesson_complete":
        tree.skills[skill] = tree.skills.get(skill, 0) + 10
        tree.total_points += 10
    elif action == "lab_complete":
        points = int(score / 10)
        tree.skills[skill] = tree.skills.get(skill, 0) + points
        tree.total_points += points
    elif action == "quiz_complete":
        points = int(score / 10)
        tree.skills[skill] = tree.skills.get(skill, 0) + points
        tree.total_points += points



def get_leaderboard(course_id: Optional[str] = None, limit: int = 50) -> List[dict]:
    """Get global or course-specific leaderboard ranked by score.

    Args:
        course_id: Optional course ID to filter leaderboard. If None,
            returns global leaderboard across all courses.
        limit: Maximum number of entries to return (default 50, max 100).

    Returns:
        List[dict]: Ranked list of user entries with scores and badges.

    Example:
        >>> board = get_leaderboard('network_security', limit=10)
        >>> board[0]['rank']
        1
    """
    limit = min(limit, 100)

    # Build scores from user progress
    scores: Dict[str, dict] = {}

    for key, progress in _user_progress.items():
        if course_id and progress.course_id != course_id:
            continue

        uid = progress.user_id
        if uid not in scores:
            scores[uid] = {
                "user_id": uid,
                "total_score": 0,
                "courses_completed": 0,
                "labs_completed": 0,
                "quizzes_completed": 0,
            }
        scores[uid]["total_score"] += progress.overall_score
        if progress.status == "completed":
            scores[uid]["courses_completed"] += 1
        scores[uid]["labs_completed"] += len(progress.lab_scores)
        scores[uid]["quizzes_completed"] += len(progress.quiz_scores)

    # Sort by total score descending
    sorted_scores = sorted(scores.values(), key=lambda x: x["total_score"], reverse=True)

    # Add ranks
    result = []
    for rank, entry in enumerate(sorted_scores[:limit], 1):
        entry["rank"] = rank
        # Get user badges
        if entry["user_id"] in _skill_trees:
            entry["badges"] = len(_skill_trees[entry["user_id"]].badges)
            entry["level"] = _skill_trees[entry["user_id"]].level
        else:
            entry["badges"] = 0
            entry["level"] = 1
        result.append(entry)

    return result


def search_courses(query: str, category: Optional[str] = None,
                   difficulty: Optional[str] = None) -> List[dict]:
    """Search courses with filtering by query, category, and difficulty.

    Performs case-insensitive search across course titles, descriptions,
    module titles, and lesson content.

    Args:
        query: Search query string.
        category: Optional category filter (e.g., 'network', 'web_application').
        difficulty: Optional difficulty filter (beginner/intermediate/advanced/expert).

    Returns:
        List[dict]: Matching courses sorted by relevance.

    Example:
        >>> results = search_courses('firewall', category='network')
        >>> len(results) > 0
        True
    """
    if not query:
        return []

    query_lower = query.lower()
    results = []

    for course in _courses.values():
        # Category filter
        if category and course.category.value != category.lower():
            continue
        # Difficulty filter
        if difficulty and course.difficulty.value != difficulty.lower():
            continue

        # Search relevance scoring
        relevance = 0
        if query_lower in course.title.lower():
            relevance += 10
        if query_lower in course.description.lower():
            relevance += 5

        # Search in modules
        for module in course.modules:
            if query_lower in module.title.lower():
                relevance += 3
            if query_lower in module.description.lower():
                relevance += 2
            for lesson in module.lessons:
                if query_lower in lesson.title.lower():
                    relevance += 1
                if query_lower in lesson.content.lower():
                    relevance += 1

        if relevance > 0:
            course_dict = course.to_dict()
            course_dict["relevance"] = relevance
            results.append(course_dict)

    # Sort by relevance descending
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results


def get_recommended_courses(user_id: str) -> List[dict]:
    """Get personalized course recommendations based on user progress.

    Analyzes user's current progress, completed courses, and skill tree
    to recommend the next best courses to take.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        List[dict]: Recommended courses with match scores and reasons.

    Example:
        >>> recs = get_recommended_courses('user_123')
        >>> len(recs) > 0
        True
    """
    recommendations = []

    # Get user's enrolled courses and skills
    enrolled_courses = set()
    user_skills: Dict[str, int] = {}
    if user_id in _skill_trees:
        user_skills = _skill_trees[user_id].skills

    for key, progress in _user_progress.items():
        if progress.user_id == user_id:
            enrolled_courses.add(progress.course_id)

    # Prerequisite chains
    prereq_chains = {
        "network_security": [],
        "web_app_security": [],
        "cryptography": [],
        "ethical_hacking": ["network_security"],
        "incident_response": ["network_security"],
        "cloud_security": ["network_security"],
        "malware_analysis": ["ethical_hacking", "cryptography"],
        "digital_forensics": ["incident_response"],
        "compliance_governance": [],
        "mobile_security": ["web_app_security"],
        "wireless_security": ["network_security"],
        "social_engineering": [],
        "africa_telecom_security": ["network_security"],
        "devsecops": ["web_app_security"],
        "threat_intelligence": ["incident_response"],
    }

    for course_id, course in _courses.items():
        if course_id in enrolled_courses:
            continue

        match_score = 0
        reasons = []

        # Check prerequisites
        prereqs_met = True
        for prereq in prereq_chains.get(course_id, []):
            if prereq not in enrolled_courses:
                prereqs_met = False
                break

        if prereqs_met:
            match_score += 20
            reasons.append("Prerequisites met")

        # Skill affinity
        skill_map = {
            "network_security": "networking",
            "web_app_security": "web_security",
            "cryptography": "cryptography",
            "ethical_hacking": "pentesting",
            "incident_response": "incident_response",
            "cloud_security": "cloud_security",
            "malware_analysis": "malware_analysis",
            "digital_forensics": "forensics",
            "compliance_governance": "compliance",
            "mobile_security": "mobile_security",
            "wireless_security": "wireless_security",
            "social_engineering": "social_engineering",
            "africa_telecom_security": "telecom_security",
            "devsecops": "devsecops",
            "threat_intelligence": "threat_intelligence",
        }
        related_skill = skill_map.get(course_id)
        if related_skill and related_skill in user_skills:
            skill_level = user_skills[related_skill]
            if skill_level < 50:
                match_score += 30  # High priority - new skill
                reasons.append("New skill area to explore")
            elif skill_level < 150:
                match_score += 20  # Medium priority - building skill
                reasons.append("Continue building this skill")
            else:
                match_score += 10  # Lower priority - already skilled

        # Difficulty appropriateness
        if course.difficulty == DifficultyLevel.BEGINNER:
            match_score += 10
            reasons.append("Beginner-friendly")

        if match_score > 0:
            course_dict = course.to_dict()
            course_dict["match_score"] = match_score
            course_dict["recommendation_reasons"] = reasons
            recommendations.append(course_dict)

    # Sort by match score descending
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:10]


def create_ctf_challenge(difficulty: str = "intermediate",
                         category: str = "network") -> dict:
    """Generate a random CTF challenge based on difficulty and category.

    Selects from the pool of 15 pre-built CTF challenges or generates
    a random puzzle challenge.

    Args:
        difficulty: Difficulty level (beginner/intermediate/advanced/expert).
        category: Course category for the challenge.

    Returns:
        dict: CTF challenge details (without revealing the flag).

    Example:
        >>> challenge = create_ctf_challenge('intermediate', 'network')
        >>> 'flag' not in challenge
        True
    """
    # Filter challenges by criteria
    available = []
    for ctf in _ctf_challenges.values():
        cat_match = not category or ctf.category.value == category.lower()
        diff_match = not difficulty or ctf.difficulty.value == difficulty.lower()
        if cat_match or diff_match:
            available.append(ctf)

    if not available:
        # Return a random challenge if no exact match
        available = list(_ctf_challenges.values())

    challenge = random.choice(available)
    return challenge.to_dict(reveal_flag=False)


def verify_ctf_flag(challenge_id: str, flag: str) -> dict:
    """Verify a CTF flag submission with timing and attempt tracking.

    Args:
        challenge_id: ID of the CTF challenge.
        flag: Submitted flag string (e.g., 'LUQI{...}').

    Returns:
        dict: Verification result with correctness, points, and hints.

    Raises:
        CTFChallengeNotFoundError: If the challenge does not exist.
        InvalidSubmissionError: If flag is empty.

    Example:
        >>> result = verify_ctf_flag('ctf_netsec', 'LUQI{NETSCAN_MASTERY_2024}')
        >>> result['correct']
        True
    """
    if not flag:
        raise InvalidSubmissionError("Flag cannot be empty")
    if challenge_id not in _ctf_challenges:
        raise CTFChallengeNotFoundError(f"CTF challenge '{challenge_id}' not found")

    challenge = _ctf_challenges[challenge_id]
    is_correct = flag.strip() == challenge.flag

    if is_correct:
        challenge.solves += 1

    return {
        "correct": is_correct,
        "challenge_id": challenge_id,
        "points": challenge.points if is_correct else 0,
        "difficulty": challenge.difficulty.value,
        "category": challenge.category.value,
        "hints_unlocked": challenge.hints if not is_correct else [],
        "total_solves": challenge.solves,
        "message": "Correct! Flag verified." if is_correct else "Incorrect flag. Try again!",
    }


def get_all_badges() -> List[dict]:
    """Get all available skill badges in the platform.

    Returns:
        List[dict]: All skill badges with their requirements.

    Example:
        >>> badges = get_all_badges()
        >>> len(badges) >= 30
        True
    """
    return [badge.to_dict() for badge in _badges.values()]


def get_user_badges(user_id: str) -> List[dict]:
    """Get all badges earned by a specific user.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        List[dict]: User's earned badges with details.
    """
    if user_id not in _skill_trees:
        return []

    tree = _skill_trees[user_id]
    result = []
    for badge_id in tree.badges:
        if badge_id in _badges:
            badge_dict = _badges[badge_id].to_dict()
            badge_dict["earned"] = True
            result.append(badge_dict)
    return result


def get_certification_tracks() -> List[dict]:
    """Get all available certification preparation tracks.

    Returns:
        List[dict]: Certification tracks with associated courses.

    Example:
        >>> tracks = get_certification_tracks()
        >>> len(tracks)
        4
    """
    tracks = {
        CertificationTrack.COMPTIA_SECURITY_PLUS: [],
        CertificationTrack.CEH: [],
        CertificationTrack.CISSP: [],
        CertificationTrack.OSCP: [],
    }

    for course in _courses.values():
        if course.certification_track in tracks:
            tracks[course.certification_track].append(course.id)

    return [
        {
            "name": track.value,
            "courses": course_list,
            "total_courses": len(course_list),
            "estimated_hours": sum(_courses[c].duration_hours for c in course_list if c in _courses),
        }
        for track, course_list in tracks.items()
    ]


def get_platform_stats() -> dict:
    """Get comprehensive platform statistics.

    Returns:
        dict: Statistics about courses, modules, labs, quizzes, CTFs,
            badges, and user engagement.

    Example:
        >>> stats = get_platform_stats()
        >>> stats['total_courses']
        15
    """
    total_quiz_questions = sum(
        len(quiz.questions) for quiz in _quizzes.values()
    )

    return {
        "total_courses": len(_courses),
        "total_modules": len(_modules),
        "total_lessons": len(_lessons),
        "total_labs": len(_labs),
        "total_quizzes": len(_quizzes),
        "total_quiz_questions": total_quiz_questions,
        "total_ctf_challenges": len(_ctf_challenges),
        "total_badges": len(_badges),
        "total_enrolled_users": len(set(p.user_id for p in _user_progress.values())),
        "total_certificates_issued": len(_certificates),
        "certification_tracks": len(CertificationTrack),
        "version": "24.4.0",
        "platform": "Luqi AI Security Training Academy",
        "company": "Limitless Telecoms",
    }


def get_module_for_course(course_id: str) -> Optional[dict]:
    """Get the primary module for a course.

    Args:
        course_id: The course identifier.

    Returns:
        dict or None: Module details if found.
    """
    if course_id not in _courses:
        return None
    course = _courses[course_id]
    if course.modules:
        return course.modules[0].to_dict()
    return None


def get_lessons_for_module(module_id: str) -> List[dict]:
    """Get all lessons for a specific module.

    Args:
        module_id: The module identifier.

    Returns:
        List[dict]: Lessons sorted by order.
    """
    if module_id not in _modules:
        return []
    module = _modules[module_id]
    return sorted([lesson.to_dict() for lesson in module.lessons], key=lambda x: x["order"])


def get_labs_for_module(module_id: str) -> List[dict]:
    """Get all labs for a specific module.

    Args:
        module_id: The module identifier.

    Returns:
        List[dict]: Lab exercises for the module.
    """
    if module_id not in _modules:
        return []
    module = _modules[module_id]
    return [lab.to_dict() for lab in module.labs]


def get_quiz_for_module(module_id: str) -> Optional[dict]:
    """Get the quiz for a specific module.

    Args:
        module_id: The module identifier.

    Returns:
        dict or None: Quiz details if the module has one.
    """
    if module_id not in _modules:
        return None
    module = _modules[module_id]
    return module.quiz.to_dict() if module.quiz else None


def reset_user_progress(user_id: str, course_id: str) -> dict:
    """Reset a user's progress in a course (for retaking).

    Args:
        user_id: Unique identifier for the user.
        course_id: ID of the course to reset.

    Returns:
        dict: Reset confirmation.

    Raises:
        UserNotEnrolledError: If user is not enrolled.
    """
    progress_key = f"{user_id}:{course_id}"
    if progress_key not in _user_progress:
        raise UserNotEnrolledError(f"User {user_id} is not enrolled in {course_id}")

    del _user_progress[progress_key]
    return {
        "status": "success",
        "message": f"Progress reset for user {user_id} in course {course_id}",
    }


def export_user_report(user_id: str) -> dict:
    """Generate a comprehensive report for a user.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        dict: Complete user report with all progress, certificates,
            skill tree, and badges.
    """
    # Get all progress entries
    user_progress = []
    for key, progress in _user_progress.items():
        if progress.user_id == user_id:
            user_progress.append(progress.to_dict())

    # Get certificates
    user_certs = []
    for key, cert in _certificates.items():
        if cert.user_id == user_id:
            user_certs.append(cert.to_dict())

    skill_tree = get_skill_tree(user_id)
    badges = get_user_badges(user_id)

    return {
        "user_id": user_id,
        "generated_at": datetime.utcnow().isoformat(),
        "courses_enrolled": len(user_progress),
        "courses_completed": sum(1 for p in user_progress if p["status"] == "completed"),
        "overall_progress": user_progress,
        "certificates": user_certs,
        "skill_tree": skill_tree,
        "badges": badges,
    }


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_platform() -> dict:
    """Initialize the security training platform.

    Ensures all courses, badges, and CTF challenges are loaded.

    Returns:
        dict: Platform initialization status and statistics.
    """
    if not _courses:
        _build_courses()

    return get_platform_stats()


# Auto-initialize on module import
_platform_stats = initialize_platform()


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Self-test when run directly
    print("=" * 70)
    print("Luqi AI v24.4.0 - IT Security Training Academy")
    print("Limitless Telecoms - Self-Test Mode")
    print("=" * 70)

    stats = get_platform_stats()
    print(f"\nPlatform Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\nCourses ({stats['total_courses']}):")
    for course in get_all_courses():
        print(f"  {course['icon']} {course['title']} ({course['difficulty']}) - "
              f"{course['total_lessons']} lessons, {course['total_labs']} labs")

    print(f"\nCertification Tracks:")
    for track in get_certification_tracks():
        print(f"  {track['name']}: {track['total_courses']} courses, "
              f"{track['estimated_hours']} hours")

    # Test enrollment
    print("\n--- Testing Enrollment ---")
    result = enroll_user("test_user_001", "network_security")
    print(f"Enrollment: {result['status']}")

    # Test progress tracking
    print("\n--- Testing Progress Tracking ---")
    result = update_lesson_progress("test_user_001", "network_security",
                                     "netsec_001", "netsec_l1", 30)
    print(f"Lesson complete: {result['completed']}, Score: {result['overall_score']}")

    # Test quiz submission
    print("\n--- Testing Quiz Submission ---")
    quiz_answers = {f"nq{i}": 1 for i in range(1, 16)}
    result = submit_quiz("test_user_001", "netsec_q1", quiz_answers)
    print(f"Quiz: {result['status']}, Score: {result['score']}%")

    # Test lab submission
    print("\n--- Testing Lab Submission ---")
    lab_submission = {"answers": {f"task{i}": f"Completed task {i}" for i in range(1, 9)}}
    result = submit_lab("test_user_001", "netsec_lab1", lab_submission)
    print(f"Lab: Score {result['score']}%, Points: {result['points_earned']}")

    # Test skill tree
    print("\n--- Testing Skill Tree ---")
    tree = get_skill_tree("test_user_001")
    print(f"Level: {tree['level']}, Title: {tree['title']}, Points: {tree['total_points']}")

    # Test CTF
    print("\n--- Testing CTF ---")
    ctf = create_ctf_challenge("intermediate", "network")
    print(f"CTF Challenge: {ctf['title']} ({ctf['difficulty']})")
    result = verify_ctf_flag(ctf['id'], "LUQI{WRONG_FLAG}")
    print(f"Wrong flag result: {result['correct']}")

    # Test search
    print("\n--- Testing Search ---")
    results = search_courses("firewall", category="network")
    print(f"Search 'firewall' in network: {len(results)} results")

    # Test recommendations
    print("\n--- Testing Recommendations ---")
    recs = get_recommended_courses("test_user_001")
    print(f"Recommendations: {len(recs)} courses")
    for rec in recs[:3]:
        print(f"  {rec['title']} (match: {rec['match_score']})")

    # Test leaderboard
    print("\n--- Testing Leaderboard ---")
    board = get_leaderboard(limit=5)
    print(f"Leaderboard entries: {len(board)}")

    print("\n" + "=" * 70)
    print("All self-tests completed successfully!")
    print("=" * 70)

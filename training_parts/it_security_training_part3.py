    # COURSE 7: MALWARE ANALYSIS
    # ========================================================================
    mod7 = SecurityModule(
        id="malware_001",
        course_id="malware_analysis",
        title="Malware Analysis & Reverse Engineering",
        description="Analyze malicious software through static and dynamic techniques. Learn to dissect PE files, understand behavior, and identify indicators of compromise.",
        category=CourseCategory.MALWARE,
        difficulty=DifficultyLevel.ADVANCED,
        duration_hours=16.0,
        prerequisites=[["Assembly language basics"], ["Windows internals"], ["Cryptography fundamentals"]],
        order=7,
        lessons=[
            SecurityLesson(
                id="mal_l1", module_id="malware_001", title="Malware Taxonomy & Types",
                content="Classification of malware: viruses, worms, trojans, ransomware, spyware, adware, rootkits, bootkits, fileless malware, wipers. Infection vectors: phishing, drive-by downloads, supply chain, USB drops. Malware delivery mechanisms: droppers, downloaders, stagers. Modern malware families: Emotet, TrickBot, Ryuk, Cobalt Strike.",
                lesson_type=LessonType.TEXT, duration_min=50, order=1,
            ),
            SecurityLesson(
                id="mal_l2", module_id="malware_001", title="Static Analysis Techniques",
                content="Analyzing malware without execution: strings extraction, PE header analysis (DOS/NT headers, sections, imports/exports), resource analysis. Tools: PEStudio, CFF Explorer, Dependency Walker. File hashing (MD5, SHA-256, ssdeep), YARA rule writing, packing detection, entropy analysis for encrypted sections.",
                lesson_type=LessonType.INTERACTIVE, duration_min=65, order=2,
            ),
            SecurityLesson(
                id="mal_l3", module_id="malware_001", title="Dynamic Analysis & Sandboxing",
                content="Safe execution environments: isolated VMs, sandbox tools (Cuckoo, ANY.RUN, Joe Sandbox). Behavior monitoring: API hooking, registry changes, file system modifications, network activity. Memory analysis during execution. Evasive malware techniques: VM detection, timing checks, sandbox awareness.",
                lesson_type=LessonType.INTERACTIVE, duration_min=70, order=3,
            ),
            SecurityLesson(
                id="mal_l4", module_id="malware_001", title="YARA Rule Development",
                content="Writing effective YARA rules for malware detection and hunting. Rule structure: strings, conditions, modifiers. Advanced techniques: byte-level patterns, regular expressions, external variables, modules (PE, ELF, Math). Rule optimization and testing against large datasets.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=4,
            ),
            SecurityLesson(
                id="mal_l5", module_id="malware_001", title="Reverse Engineering Basics",
                content="Introduction to disassembly with IDA Pro Free and Ghidra. Understanding x86/x64 assembly, control flow, function calls, stack frames. Decompilation techniques, cross-references, and annotation. Identifying C2 communication, encryption routines, and obfuscation techniques.",
                lesson_type=LessonType.VIDEO, duration_min=60, order=5,
            ),
            SecurityLesson(
                id="mal_l6", module_id="malware_001", title="Ransomware Analysis",
                content="Deep dive into ransomware behavior: file enumeration, encryption routines, key management, ransom note delivery. Analysis of major ransomware families: WannaCry, NotPetya, Locky, REvil. Decryption possibilities, kill switches, and recovery strategies. Ransom negotiation considerations.",
                lesson_type=LessonType.INTERACTIVE, duration_min=65, order=6,
            ),
        ],
        labs=[
            SecurityLab(
                id="mal_lab1", module_id="malware_001",
                title="Static Analysis of Suspicious PE File",
                description="Perform comprehensive static analysis on a suspicious executable without running it.",
                environment="REMnux VM, PEStudio, CFF Explorer, strings, pestudio, ssdeep.",
                tasks=[
                    "Calculate MD5, SHA-256, and fuzzy hashes",
                    "Extract and analyze all printable strings",
                    "Parse PE headers and analyze section characteristics",
                    "Identify imported DLLs and suspicious API calls",
                    "Check for packing with UPX or custom packers",
                    "Analyze entropy of each section for encryption",
                    "Write a YARA rule for detection",
                ],
                hints=[
                    "High entropy (>7.5) sections may indicate packing/encryption",
                    "APIs like VirtualAlloc, CreateRemoteThread are suspicious",
                    "Check for unusual section names like .vm
p0, .upx",
                ],
                solution="strings -n 6 suspicious.exe | grep -i http; pestudio suspicious.exe; # Check imports: kernel32.dll: VirtualAlloc, WriteProcessMemory, CreateRemoteThread = code injection; # High entropy .text section indicates packing; YARA: rule SuspiciousPE { strings: $a=\"VirtualAlloc\" $b=\"CreateRemoteThread\" condition: uint16(0)==0x5A4D and all of them }",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="mal_lab2", module_id="malware_001",
                title="Dynamic Analysis in Controlled Environment",
                description="Execute and monitor malware behavior in a sandboxed environment.",
                environment="Isolated Windows 10 VM with INetSim, Wireshark, Procmon, Regshot, Cuckoo sandbox.",
                tasks=[
                    "Take system snapshot before execution",
                    "Execute malware and monitor process tree",
                    "Capture all network communications",
                    "Monitor registry modifications",
                    "Track file system changes",
                    "Identify persistence mechanisms",
                    "Extract C2 URLs and indicators",
                ],
                hints=[
                    "INetSim simulates internet services safely",
                    "Procmon filters: ProcessCreate, RegSetValue, WriteFile",
                    "Compare Regshot snapshots for registry changes",
                ],
                solution="Run in Cuckoo sandbox; Monitor with Procmon filter Operation is ProcessCreate or TCP Send; Wireshark filter dns or http; Identify: C2 at evil-domain.com, registry Run key for persistence, encrypted files in Documents folder = ransomware behavior",
                duration_min=90, points=175,
            ),
            SecurityLab(
                id="mal_lab3", module_id="malware_001",
                title="Ghidra Reverse Engineering",
                description="Use Ghidra to reverse engineer a simple crackme program.",
                environment="Ghidra 11.0, simple crackme binary, x86 reference materials.",
                tasks=[
                    "Import binary into Ghidra and run auto-analysis",
                    "Locate the main function in the decompiler",
                    "Identify user input function and comparison logic",
                    "Find the correct password string in the binary",
                    "Patch the binary to accept any password",
                    "Document the reverse engineering process",
                ],
                hints=[
                    "Look for strcmp or memcmp functions",
                    "Check string table for hardcoded values",
                    "Use cross-references to find where strings are used",
                ],
                solution="Import crackme into Ghidra; Find main at entry point; Decompile shows strcmp(user_input, 'SecretPass123'); Password is 'SecretPass123'; Patch: change JNZ to JZ after comparison or NOP the jump",
                duration_min=90, points=175,
            ),
            SecurityLab(
                id="mal_lab4", module_id="malware_001",
                title="YARA Rule Development for Threat Hunting",
                description="Create YARA rules to detect a malware family based on identified indicators.",
                environment="REMnux, YARA, Python 3, sample malware files, VT API for verification.",
                tasks=[
                    "Extract unique strings from malware samples",
                    "Identify PE structure patterns common to the family",
                    "Write YARA rules with multiple string conditions",
                    "Test rules against known malware dataset",
                    "Optimize rules to minimize false positives",
                    "Document rule with metadata and description",
                ],
                hints=[
                    "Combine unique strings with PE structure checks",
                    "Use wide and ascii modifiers for Unicode strings",
                    "Test with yarac for compilation errors",
                ],
                solution="rule APT_Malware_Family { meta: author=\"Analyst\" description=\"Detects XYZ malware family\" strings: $mz={4D5A} $s1=\"C2_SERVER_URL\" wide ascii $s2=\"Mozilla/5.0 Custom\" $s3={68 ?? ?? ?? ?? E8 ?? ?? ?? ??} condition: $mz at 0 and 2 of ($s*) and filesize < 500KB }",
                duration_min=60, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="mal_q1", module_id="malware_001", title="Malware Analysis Assessment",
            passing_score=75, time_limit_minutes=30,
            questions=[
                QuizQuestion("maq1", "What is the difference between static and dynamic analysis?",
                    ["Static is faster", "Static analyzes without execution; dynamic observes behavior during execution", "Dynamic is safer", "Stat
# ___END_OF_FILE___
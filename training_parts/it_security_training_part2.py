    # COURSE 3: CRYPTOGRAPHY
    # ========================================================================
    mod3 = SecurityModule(
        id="crypto_001",
        course_id="cryptography",
        title="Cryptography & Secure Communications",
        description="From ancient ciphers to quantum-resistant algorithms: master modern cryptographic systems, key management, and secure protocols.",
        category=CourseCategory.CRYPTOGRAPHY,
        difficulty=DifficultyLevel.INTERMEDIATE,
        duration_hours=14.0,
        prerequisites=["Basic algebra", "Binary/hexadecimal numbering"],
        order=3,
        lessons=[
            SecurityLesson(
                id="crypto_l1", module_id="crypto_001", title="Cryptographic Foundations",
                content="History of cryptography from Caesar cipher to modern standards. Concepts of confidentiality, integrity, authenticity, non-repudiation. Kerckhoffs' principle, perfect secrecy, and computational security. Understanding entropy, pseudorandom number generators, and their critical role in security.",
                lesson_type=LessonType.TEXT, duration_min=50, order=1,
            ),
            SecurityLesson(
                id="crypto_l2", module_id="crypto_001", title="Symmetric Encryption: AES",
                content="Advanced Encryption Standard (AES) in depth: S-boxes, key expansion, rounds, and modes of operation (ECB, CBC, CTR, GCM). Learn proper IV/nonce handling, padding oracle attacks, and authenticated encryption. Practical implementation using Python cryptography library.",
                lesson_type=LessonType.INTERACTIVE, duration_min=60, order=2,
            ),
            SecurityLesson(
                id="crypto_l3", module_id="crypto_001", title="Asymmetric Encryption: RSA & ECC",
                content="Public-key cryptography fundamentals: RSA key generation, encryption, signing, and common attacks (Bleichenbacher, ROCA). Elliptic Curve Cryptography (ECC) with Curve25519, ECDSA, and Ed25519. Performance comparison and modern recommendations.",
                lesson_type=LessonType.INTERACTIVE, duration_min=65, order=3,
            ),
            SecurityLesson(
                id="crypto_l4", module_id="crypto_001", title="Hashing & Password Storage",
                content="Cryptographic hash functions: SHA-256, SHA-3, BLAKE2, and their properties. Secure password storage with bcrypt, scrypt, and Argon2 (winner of Password Hashing Competition). Learn work factors, memory-hard functions, and why MD5/SHA1 are deprecated for passwords.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=4,
            ),
            SecurityLesson(
                id="crypto_l5", module_id="crypto_001", title="PKI & Digital Certificates",
                content="Public Key Infrastructure: certificate authorities, certificate chains, X.509 format, SAN, key usage extensions. Certificate Transparency, OCSP stapling, and CRL. Self-signed certificates vs commercial vs Let's Encrypt. Common PKI attacks and misconfigurations.",
                lesson_type=LessonType.VIDEO, duration_min=45, order=5,
            ),
            SecurityLesson(
                id="crypto_l6", module_id="crypto_001", title="TLS/SSL Handshake Deep Dive",
                content="TLS 1.2 and TLS 1.3 handshake protocols: ClientHello, ServerHello, key exchange, certificate verification, Finished messages. Cipher suite negotiation, perfect forward secrecy, session resumption (tickets, IDs), and 0-RTT in TLS 1.3. Troubleshooting with OpenSSL s_client.",
                lesson_type=LessonType.INTERACTIVE, duration_min=55, order=6,
            ),
            SecurityLesson(
                id="crypto_l7", module_id="crypto_001", title="Digital Signatures",
                content="RSA-PSS, ECDSA, and Ed25519 signature schemes. PKCS#7/CMS, S/MIME, and code signing. Timestamping and long-term signature validation. Common pitfalls including nonce reuse in ECDSA leading to private key recovery (Sony PS3, Bitcoin wallet hacks).",
                lesson_type=LessonType.TEXT, duration_min=40, order=7,
            ),
            SecurityLesson(
                id="crypto_l8", module_id="crypto_001", title="Key Management & HSMs",
                content="Key lifecycle: generation, distribution, storage, rotation, and destruction. Hardware Security Modules (HSM), AWS KMS, HashiCorp Vault. Key derivation functions (PBKDF2, HKDF), key wrapping, and threshold cryptography. Shamir's Secret Sharing for key backup.",
                lesson_type=LessonType.TEXT, duration_min=50, order=8,
            ),
            SecurityLesson(
                id="crypto_l9", module_id="crypto_001", title="Introduction to Post-Quantum Cryptography",
                content="Quantum computing threats to current cryptography: Shor's algorithm breaking RSA/ECC, Grover's algorithm halving symmetric key security. NIST PQC standardization: CRYSTALS-Kyber (key encapsulation), CRYSTALS-Dilithium (signatures), SPHINCS+, FALCON. Migration strategies and crypto agility.",
                lesson_type=LessonType.TEXT, duration_min=45, order=9,
            ),
        ],
        labs=[
            SecurityLab(
                id="crypto_lab1", module_id="crypto_001",
                title="Implement AES-GCM Encryption in Python",
                description="Build a secure file encryption tool using AES-256-GCM with proper key derivation.",
                environment="Python 3.11 with cryptography library, test files of various sizes.",
                tasks=[
                    "Generate a random 256-bit key using os.urandom",
                    "Derive key from password using PBKDF2-HMAC-SHA256",
                    "Encrypt a file using AES-GCM with unique nonce per file",
                    "Store nonce and tag alongside ciphertext",
                    "Implement secure decryption with authentication verification",
                    "Add support for large files using chunked encryption",
                ],
                hints=[
                    "Never reuse a (key, nonce) pair with GCM",
                    "Use a minimum of 100,000 PBKDF2 iterations",
                    "Authenticate the ciphertext before decryption",
                ],
                solution="from cryptography.hazmat.primitives.ciphers.aead import AESGCM; key = AESGCM.generate_key(bit_length=256); aesgcm = AESGCM(key); nonce = os.urandom(12); ct = aesgcm.encrypt(nonce, plaintext, None); decrypt: aesgcm.decrypt(nonce, ct, None)",
                duration_min=75, points=150,
            ),
            SecurityLab(
                id="crypto_lab2", module_id="crypto_001",
                title="Build a Password Hashing System",
                description="Implement secure password hashing with Argon2id and verify against timing attacks.",
                environment="Python 3.11 with argon2-cffi, bcrypt, hashlib, timing attack simulation tools.",
                tasks=[
                    "Install and configure argon2-cffi library",
                    "Implement hash generation with Argon2id (t=3, m=65536, p=4)",
                    "Implement constant-time password verification",
                    "Compare performance of bcrypt, scrypt, and Argon2",
                    "Test against timing attack using statistical analysis",
                    "Implement secure password reset token generation",
                ],
                hints=[
                    "Use argon2.PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)",
                    "Use hmac.compare_digest() for constant-time comparison",
                    "Generate reset tokens with secrets.token_urlsafe()",
                ],
                solution="from argon2 import PasswordHasher; ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16); hash = ph.hash('user_password'); ph.verify(hash, 'user_password'); ph.check_needs_rehash(hash) for parameter updates",
                duration_min=60, points=125,
            ),
            SecurityLab(
                id="crypto_lab3", module_id="crypto_001",
                title="TLS Certificate Analysis and Validation",
                description="Analyze TLS certificates for security issues and implement certificate pinning.",
                environment="OpenSSL 3.0, Python 3.11 with ssl, socket, cryptography libraries, test server.",
                tasks=[
                    "Use openssl s_client to inspect a server's certificate chain",
                    "Check certificate expiry, SAN, and key usage extensions",
                    "Verify certificate chain against trusted CAs",
                    "Check for weak cipher suites and TLS version",
                    "Implement certificate pinning in Python client",
                    "Test OCSP stapling support on target server",
                ],
                hints=[
                    "openssl s_client -connect example.com:443 -servername example.com",
                    "Use cryptography.x509 to parse certificates in Python",
                    "Pin the SPKI hash, not the full certificate",
                ],
                solution="openssl s_client -connect google.com:443 -showcerts </dev/null 2>/dev/null | openssl x509 -noout -text; Python: ssl.get_server_certificate(('host', 443)); cert = x509.load_pem_x509_certificate(cert_pem); pin = base64.b64encode(hashlib.sha256(cert.public_key().public_bytes(Encoding.DER, SubjectPublicKeyInfo())).digest())",
                duration_min=60, points=125,
            ),
        ],
        quiz=SecurityQuiz(
            id="crypto_q1", module_id="crypto_001", title="Cryptography Assessment",
            passing_score=75, time_limit_minutes=30,
            questions=[
                QuizQuestion("cq1", "What is the key size of AES-256?",
                    ["128 bits", "192 bits", "256 bits", "512 bits"], 2,
                    "AES-256 uses a 25
# ___END_OF_FILE___
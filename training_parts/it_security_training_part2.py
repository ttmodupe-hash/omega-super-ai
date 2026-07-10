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
                content="Quantum computing threats to current cryptography: Shor's algorithm breaking RSA/ECC, Grover's algorithm halving symmetric key security. NIST PQC standardization: CRYSTALS-Kyber (key encapsulation), CRYSTALS-Dil
# ___END_OF_FILE___
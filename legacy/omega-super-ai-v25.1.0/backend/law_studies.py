#!/usr/bin/env python3
"""Luqi AI v19 - Law Studies and Legal AI Assistant
===================================================
Comprehensive legal education and legal AI assistant covering:
- 15 practice areas across multiple jurisdictions
- 50+ landmark cases with full citations and summaries
- Legal document templates (NDA, employment, demand letter, cease and desist)
- Bar exam preparation with MBE-style questions
- IRAC / CREAC / CRAC case briefing
- Court procedures for US, UK, Nigeria, South Africa, EU
- Federal Rules of Evidence (Rules 101-1101)
- Legal citation generator (Bluebook, APA, OSCOLA)
- Cross-jurisdictional comparison engine
- Contract analysis and drafting
- Moot court preparation
- Legal clinic support
"""

import json
import logging
import os
import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────

PRACTICE_AREAS = {
    "corporate": "Corporate and Commercial Law",
    "criminal": "Criminal Law and Procedure",
    "civil": "Civil Litigation",
    "constitutional": "Constitutional Law",
    "international": "International Law",
    "human_rights": "Human Rights Law",
    "ip": "Intellectual Property",
    "family": "Family Law",
    "tort": "Tort Law",
    "property": "Property Law",
    "administrative": "Administrative Law",
    "tax": "Tax Law",
    "labor": "Labor and Employment Law",
    "environmental": "Environmental Law",
    "commercial": "Commercial Law"
}

JURISDICTIONS = {
    "us": "United States Federal Law",
    "uk": "United Kingdom",
    "nigeria": "Federal Republic of Nigeria",
    "south_africa": "Republic of South Africa",
    "eu": "European Union",
    "international": "Public International Law"
}

BAR_EXAM_SUBJECTS = ["constitutional", "contracts", "criminal", "evidence", "property", "torts", "civil_procedure", "professional_responsibility", "corporations", "family", "wills_trusts", "secured_transactions", "conflict_of_laws", "remedies", "sales", "criminal_procedure"]

CITATION_STYLES = ["bluebook", "apa", "oscola", "chicago", "mla"]

BRIEF_METHODS = ["IRAC", "CREAC", "CRAC", "TREAC", "SINAC"]

# ── Landmark Cases Database ────────────────────────────────────────
LANDMARK_CASES = [
    {
        "name": "Marbury v. Madison",
        "citation": "5 U.S. 137 (1803)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Established judicial review.",
        "significance": "Foundation of American constitutional law."
    },
    {
        "name": "Brown v. Board of Education",
        "citation": "347 U.S. 483 (1954)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Racial segregation in public schools is unconstitutional.",
        "significance": "Ended legal segregation."
    },
    {
        "name": "Roe v. Wade",
        "citation": "410 U.S. 113 (1973)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Constitution protects a woman's right to choose abortion.",
        "significance": "Established right to privacy. Overturned by Dobbs (2022)."
    },
    {
        "name": "Miranda v. Arizona",
        "citation": "384 U.S. 436 (1966)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "Police must inform suspects of their rights before interrogation.",
        "significance": "Created Miranda rights warning."
    },
    {
        "name": "Donoghue v. Stevenson",
        "citation": "[1932] AC 562",
        "jurisdiction": "uk",
        "area": "tort",
        "holding": "Established the modern law of negligence.",
        "significance": "Foundation of modern tort law."
    },
    {
        "name": "Mabo v. Queensland (No 2)",
        "citation": "(1992) 175 CLR 1",
        "jurisdiction": "international",
        "area": "constitutional",
        "holding": "Recognized native title in Australia.",
        "significance": "Landmark indigenous land rights case."
    },
    {
        "name": "Obergefell v. Hodges",
        "citation": "576 U.S. 644 (2015)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Same-sex couples have a fundamental right to marry.",
        "significance": "Legalized same-sex marriage nationwide."
    },
    {
        "name": "Gideon v. Wainwright",
        "citation": "372 U.S. 335 (1963)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "States must provide counsel to indigent criminal defendants.",
        "significance": "Established right to appointed counsel."
    },
    {
        "name": "DC v. Heller",
        "citation": "554 U.S. 570 (2008)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Second Amendment protects individual right to possess firearms.",
        "significance": "First ruling on individual Second Amendment rights."
    },
    {
        "name": "New York Times v. Sullivan",
        "citation": "376 U.S. 254 (1964)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Public officials must prove actual malice for defamation.",
        "significance": "Cornerstone of press freedom."
    },
    {
        "name": "Government of RSA v. Grootboom",
        "citation": "2001 (1) SA 46 (CC)",
        "jurisdiction": "south_africa",
        "area": "human_rights",
        "holding": "Government must take reasonable measures to provide housing.",
        "significance": "Established reasonableness test for socio-economic rights."
    },
    {
        "name": "Prosecutor v. Akayesu",
        "citation": "ICTR-96-4-T",
        "jurisdiction": "international",
        "area": "international",
        "holding": "Defined rape as an act of genocide.",
        "significance": "First international conviction for genocide."
    },
    {
        "name": "Brandenburg v. Ohio",
        "citation": "395 U.S. 444 (1969)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Speech must incite imminent lawless action to be punished.",
        "significance": "Established modern incitement standard."
    },
    {
        "name": "McCulloch v. Maryland",
        "citation": "17 U.S. 316 (1819)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Congress has implied powers; states cannot tax federal institutions.",
        "significance": "Established federal supremacy."
    },
    {
        "name": "Chevron v. NRDC",
        "citation": "467 U.S. 837 (1984)",
        "jurisdiction": "us",
        "area": "administrative",
        "holding": "Courts should defer to agency interpretations of ambiguous statutes.",
        "significance": "Established Chevron deference."
    },
    {
        "name": "Katz v. United States",
        "citation": "389 U.S. 347 (1967)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Fourth Amendment protects people not places; electronic surveillance requires warrant.",
        "significance": "Established reasonable expectation of privacy test."
    },
    {
        "name": "Costa v. ENEL",
        "citation": "Case 6/64, [1964] ECR 585",
        "jurisdiction": "eu",
        "area": "constitutional",
        "holding": "EU law takes precedence over conflicting national law.",
        "significance": "Established primacy of EU law."
    },
    {
        "name": "Soering v. United Kingdom",
        "citation": "(1989) 11 EHRR 439",
        "jurisdiction": "international",
        "area": "human_rights",
        "holding": "Extradition to face death penalty may violate Article 3 ECHR.",
        "significance": "Established Soering principle."
    },
    {
        "name": "Hamdi v. Rumsfeld",
        "citation": "542 U.S. 507 (2004)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "US citizens designated enemy combatants have right to challenge detention.",
        "significance": "Established due process for detainees."
    },
    {
        "name": "Tinker v. Des Moines",
        "citation": "393 U.S. 503 (1969)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Students do not shed constitutional rights at schoolhouse gate.",
        "significance": "Landmark student speech case."
    },
    {
        "name": "Daubert v. Merrell Dow",
        "citation": "509 U.S. 579 (1993)",
        "jurisdiction": "us",
        "area": "evidence",
        "holding": "Judges must act as gatekeepers for scientific evidence.",
        "significance": "Established Daubert standard."
    },
    {
        "name": "Dobbs v. Jackson Women's Health",
        "citation": "597 U.S. (2022)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Constitution does not confer a right to abortion.",
        "significance": "Overturned Roe v. Wade."
    },
    {
        "name": "United States v. Nixon",
        "citation": "418 U.S. 683 (1974)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "President is not absolutely immune from judicial process.",
        "significance": "Led to Nixon resignation."
    },
    {
        "name": "Mapp v. Ohio",
        "citation": "367 U.S. 643 (1961)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "Evidence obtained in violation of Fourth Amendment is inadmissible in state courts.",
        "significance": "Applied exclusionary rule to states."
    },
    {
        "name": "Engel v. Vitale",
        "citation": "370 U.S. 421 (1962)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "State-sponsored prayer in public schools violates Establishment Clause.",
        "significance": "Removed formal prayer from public schools."
    },
    {
        "name": "Baker v. Carr",
        "citation": "369 U.S. 186 (1962)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Apportionment questions are justiciable.",
        "significance": "Led to one person one vote."
    },
    {
        "name": "Worcester v. Georgia",
        "citation": "31 U.S. 515 (1832)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Federal government has exclusive authority over Native American affairs.",
        "significance": "Established tribal sovereignty."
    },
    {
        "name": "Fairchild v. Glenhaven",
        "citation": "[2002] UKHL 22",
        "jurisdiction": "uk",
        "area": "tort",
        "holding": "Material increase in risk test for indivisible injuries.",
        "significance": "Key mesothelioma case."
    },
    {
        "name": "Crawford v. Washington",
        "citation": "541 U.S. 36 (2004)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "Confrontation Clause bars testimonial hearsay without cross-examination.",
        "significance": "Transformed confrontation clause jurisprudence."
    },
    {
        "name": "Minister of Health v. TAC",
        "citation": "2002 (5) SA 721 (CC)",
        "jurisdiction": "south_africa",
        "area": "human_rights",
        "holding": "Government must take reasonable measures to prevent mother-to-child HIV transmission.",
        "significance": "Major public health victory."
    },
    {
        "name": "SERAC v. Nigeria",
        "citation": "Comm. 155/96, ACHPR",
        "jurisdiction": "international",
        "area": "human_rights",
        "holding": "African Charter imposes positive obligations to protect social and economic rights.",
        "significance": "First ACHPR case on economic and social rights."
    },
    {
        "name": "Van Gend en Loos",
        "citation": "Case 26/62, [1963] ECR 1",
        "jurisdiction": "eu",
        "area": "constitutional",
        "holding": "EU law creates rights enforceable by individuals in national courts.",
        "significance": "Established direct effect of EU law."
    },
    {
        "name": "Lochner v. New York",
        "citation": "198 U.S. 45 (1905)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "NY law limiting bakers' hours violated Due Process Clause.",
        "significance": "Began Lochner era; later repudiated."
    },
    {
        "name": "Plessy v. Ferguson",
        "citation": "163 U.S. 537 (1896)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Separate but equal facilities do not violate Equal Protection.",
        "significance": "Established separate but equal; later overturned."
    },
    {
        "name": "Korematsu v. United States",
        "citation": "323 U.S. 214 (1944)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Upheld Japanese-American internment as military necessity.",
        "significance": "Universally condemned; repudiated in 2018."
    },
    {
        "name": "Furman v. Georgia",
        "citation": "408 U.S. 238 (1972)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "Death penalty as applied was arbitrary and capricious.",
        "significance": "Temporarily halted death penalty."
    },
    {
        "name": "Citizens United v. FEC",
        "citation": "558 U.S. 310 (2010)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Political spending by corporations is protected speech.",
        "significance": "Major campaign finance ruling."
    },
    {
        "name": "Gregg v. Georgia",
        "citation": "428 U.S. 153 (1976)",
        "jurisdiction": "us",
        "area": "criminal",
        "holding": "Death penalty is not inherently unconstitutional with safeguards.",
        "significance": "Reinstated death penalty with guided discretion."
    },
    {
        "name": "Gibbons v. Ogden",
        "citation": "22 U.S. 1 (1824)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Congress has broad power to regulate interstate commerce.",
        "significance": "Foundation of federal commerce power."
    },
    {
        "name": "Lawrence v. Texas",
        "citation": "539 U.S. 558 (2003)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Criminal prohibitions on consensual same-sex conduct are unconstitutional.",
        "significance": "Established privacy rights."
    },
    {
        "name": "R v. Dudley and Stephens",
        "citation": "14 QBD 273 (1884)",
        "jurisdiction": "uk",
        "area": "criminal",
        "holding": "Necessity is not a defense to murder.",
        "significance": "Established limits on necessity defense."
    },
    {
        "name": "Riverside v. Adams",
        "citation": "Sup. Ct. Nigeria, 1999",
        "jurisdiction": "nigeria",
        "area": "constitutional",
        "holding": "Nigerian Supreme Court has final say on constitutional interpretation.",
        "significance": "Established role of Nigerian Supreme Court."
    },
    {
        "name": "Soobramoney v. Minister of Health",
        "citation": "1998 (1) SA 765 (CC)",
        "jurisdiction": "south_africa",
        "area": "human_rights",
        "holding": "Right to emergency medical treatment has resource limits.",
        "significance": "Established limits on justiciability of socio-economic rights."
    },
    {
        "name": "West Coast Hotel v. Parrish",
        "citation": "300 U.S. 379 (1937)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Minimum wage laws for women are constitutional.",
        "significance": "Ended the Lochner era."
    },
    {
        "name": "Prosecutor v. Tadic",
        "citation": "IT-94-1, ICTY",
        "jurisdiction": "international",
        "area": "international",
        "holding": "Established ICTY jurisdiction and definition of international armed conflict.",
        "significance": "First ICTY case; key international criminal law principles."
    },
    {
        "name": "Lustig-Prean v. UK",
        "citation": "(1999) 29 EHRR 548",
        "jurisdiction": "international",
        "area": "human_rights",
        "holding": "Banning homosexuals from military violates right to private life.",
        "significance": "Struck down UK ban on gay military service."
    },
    {
        "name": "Salduz v. Turkey",
        "citation": "(2008) 49 EHRR 421",
        "jurisdiction": "international",
        "area": "human_rights",
        "holding": "Access to lawyer during police interrogation is a fundamental safeguard.",
        "significance": "Established right to early access to counsel."
    },
    {
        "name": "TLO v. New Jersey",
        "citation": "469 U.S. 325 (1985)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "School officials need only reasonable suspicion to search students.",
        "significance": "Established reasonable suspicion standard for school searches."
    },
    {
        "name": "Airey v. Ireland",
        "citation": "(1979-80) 2 EHRR 305",
        "jurisdiction": "international",
        "area": "human_rights",
        "holding": "Access to court may require state to provide legal aid.",
        "significance": "Established legal aid as access to justice requirement."
    },
    {
        "name": "Francovich v. Italy",
        "citation": "Cases C-6/90 and C-9/90",
        "jurisdiction": "eu",
        "area": "constitutional",
        "holding": "Member States are liable for damages caused by breaches of EU law.",
        "significance": "Established state liability for EU law breaches."
    },
    {
        "name": "Boumediene v. Bush",
        "citation": "553 U.S. 723 (2008)",
        "jurisdiction": "us",
        "area": "constitutional",
        "holding": "Guantanamo detainees have constitutional right to habeas corpus.",
        "significance": "Extended habeas rights to Guantanamo."
    }
]

# ── Federal Rules of Evidence ──────────────────────────────────────
FEDERAL_RULES_OF_EVIDENCE = {
    "101": {
        "title": "Scope; Definitions",
        "article": "I",
        "text": "These rules govern proceedings in United States courts."
    },
    "103": {
        "title": "Rulings on Evidence",
        "article": "I",
        "text": "A party may claim error in a ruling only if the ruling affects a substantial right."
    },
    "104": {
        "title": "Preliminary Questions",
        "article": "I",
        "text": "The court must decide preliminary questions about witness qualification, privilege, and admissibility."
    },
    "105": {
        "title": "Limiting Evidence",
        "article": "I",
        "text": "The court must restrict evidence to its proper scope and instruct the jury accordingly."
    },
    "201": {
        "title": "Judicial Notice",
        "article": "II",
        "text": "The court may judicially notice a fact that is not subject to reasonable dispute."
    },
    "301": {
        "title": "Presumptions in Civil Cases",
        "article": "III",
        "text": "The party against whom a presumption is directed has the burden of producing evidence to rebut it."
    },
    "401": {
        "title": "Test for Relevant Evidence",
        "article": "IV",
        "text": "Evidence is relevant if it has any tendency to make a fact more or less probable than it would be without the evidence."
    },
    "402": {
        "title": "General Admissibility",
        "article": "IV",
        "text": "Relevant evidence is admissible unless otherwise provided. Irrelevant evidence is not admissible."
    },
    "403": {
        "title": "Excluding Relevant Evidence",
        "article": "IV",
        "text": "The court may exclude relevant evidence if its probative value is substantially outweighed by danger of unfair prejudice, confusion, misleading the jury, undue delay, or waste of time."
    },
    "404": {
        "title": "Character Evidence",
        "article": "IV",
        "text": "Evidence of a person's character is not admissible to prove that on a particular occasion the person acted in accordance with the character."
    },
    "405": {
        "title": "Methods of Proving Character",
        "article": "IV",
        "text": "Character evidence may be proved by testimony about reputation or opinion."
    },
    "406": {
        "title": "Habit; Routine Practice",
        "article": "IV",
        "text": "Evidence of a habit or routine practice may be admitted to prove conduct on a particular occasion."
    },
    "407": {
        "title": "Subsequent Remedial Measures",
        "article": "IV",
        "text": "Evidence of subsequent remedial measures is not admissible to prove negligence."
    },
    "408": {
        "title": "Compromise Offers",
        "article": "IV",
        "text": "Evidence of furnishing or accepting a valuable consideration to compromise a claim is not admissible."
    },
    "409": {
        "title": "Offers to Pay Medical Expenses",
        "article": "IV",
        "text": "Evidence of furnishing or offering to pay medical expenses is not admissible to prove liability."
    },
    "410": {
        "title": "Pleas and Plea Discussions",
        "article": "IV",
        "text": "Evidence of a guilty plea later withdrawn or statements made during plea discussions is not admissible."
    },
    "411": {
        "title": "Liability Insurance",
        "article": "IV",
        "text": "Evidence of liability insurance is not admissible to prove negligence."
    },
    "501": {
        "title": "Privilege in General",
        "article": "V",
        "text": "The common law governs a claim of privilege unless otherwise provided."
    },
    "601": {
        "title": "Competency to Testify",
        "article": "VI",
        "text": "Every person is competent to be a witness unless these rules provide otherwise."
    },
    "602": {
        "title": "Need for Personal Knowledge",
        "article": "VI",
        "text": "A witness may testify only if evidence supports a finding that the witness has personal knowledge."
    },
    "603": {
        "title": "Oath or Affirmation",
        "article": "VI",
        "text": "Before testifying, a witness must give an oath or affirmation to testify truthfully."
    },
    "607": {
        "title": "Who May Impeach",
        "article": "VI",
        "text": "Any party may attack a witness's credibility."
    },
    "608": {
        "title": "Character for Truthfulness",
        "article": "VI",
        "text": "A witness's credibility may be attacked by evidence of character for truthfulness or untruthfulness."
    },
    "609": {
        "title": "Impeachment by Criminal Conviction",
        "article": "VI",
        "text": "For a crime punishable by death or imprisonment over one year, evidence must be admitted subject to Rule 403."
    },
    "611": {
        "title": "Mode and Order of Examining",
        "article": "VI",
        "text": "The court should exercise reasonable control over the mode and order of examining witnesses."
    },
    "701": {
        "title": "Opinion Testimony by Lay Witnesses",
        "article": "VII",
        "text": "Lay witness opinion must be rationally based on perception, helpful to understanding testimony, and not based on specialized knowledge."
    },
    "702": {
        "title": "Testimony by Expert Witnesses",
        "article": "VII",
        "text": "An expert may testify if their specialized knowledge will help the trier of fact, based on sufficient facts, reliable principles and methods."
    },
    "703": {
        "title": "Bases of Expert Opinion",
        "article": "VII",
        "text": "An expert may base an opinion on facts or data made aware of or personally observed."
    },
    "704": {
        "title": "Opinion on Ultimate Issue",
        "article": "VII",
        "text": "In a criminal case, an expert must not state an opinion about whether the defendant had a mental state constituting an element of the crime."
    },
    "801": {
        "title": "Definitions; Hearsay Exclusions",
        "article": "VIII",
        "text": "Hearsay means a statement the declarant does not make while testifying, offered to prove the truth of the matter asserted."
    },
    "802": {
        "title": "Rule Against Hearsay",
        "article": "VIII",
        "text": "Hearsay is not admissible unless a federal statute, these rules, or other Supreme Court rules provide otherwise."
    },
    "803": {
        "title": "Exceptions to Hearsay",
        "article": "VIII",
        "text": "Exceptions include: Present Sense Impression, Excited Utterance, Then-Existing Condition, Medical Diagnosis, Recorded Recollection, Business Records, Absence of Entry, Public Records, Learned Treatise, Reputation, Family Records, and others."
    },
    "804": {
        "title": "Hearsay Exceptions; Declarant Unavailable",
        "article": "VIII",
        "text": "Exceptions if declarant unavailable: Former Testimony, Dying Declaration, Statement Against Interest, Personal or Family History."
    },
    "805": {
        "title": "Hearsay Within Hearsay",
        "article": "VIII",
        "text": "Hearsay within hearsay is admissible if each part conforms with an exception."
    },
    "901": {
        "title": "Authenticating Evidence",
        "article": "IX",
        "text": "The proponent must produce evidence sufficient to support a finding that the item is what the proponent claims."
    },
    "1001": {
        "title": "Definitions",
        "article": "X",
        "text": "A writing, recording, or photograph is evidence consisting of letters, words, numbers, or their equivalent."
    },
    "1002": {
        "title": "Requirement of Original",
        "article": "X",
        "text": "An original writing is required to prove its content unless otherwise provided."
    },
    "1003": {
        "title": "Admissibility of Duplicates",
        "article": "X",
        "text": "A duplicate is admissible to the same extent as an original unless authenticity is questioned."
    },
    "1101": {
        "title": "Applicability of Rules",
        "article": "XI",
        "text": "These rules apply to proceedings in United States courts and certain other proceedings."
    }
}

# ── Court Procedures ──────────────────────────────────────────────
COURT_PROCEDURES = {
    "us_federal_civil": {
        "steps": [
            "1. Pleadings: Complaint filed; Answer due in 21 days or Motion to Dismiss",
            "2. Scheduling Conference: Judge sets timeline per Rule 16",
            "3. Discovery: Depositions, interrogatories, requests for production (Rules 26-37)",
            "4. Summary Judgment: Either party may file under Rule 56",
            "5. Pre-Trial Conference: Final issues and jury instructions determined",
            "6. Trial: Jury selection, opening statements, evidence, closing arguments, verdict",
            "7. Post-Trial: Motions for JMOL, new trial, or remittitur",
            "8. Appeal: Notice of appeal to Circuit Court within 30 days"
        ]
    },
    "us_federal_criminal": {
        "steps": [
            "1. Investigation and Charging: Indictment by grand jury or Information filed",
            "2. Initial Appearance: Charges and rights explained; counsel appointed if needed",
            "3. Arraignment: Defendant enters plea (guilty, not guilty, or nolo contendere)",
            "4. Pre-Trial Motions: Suppression, discovery, and severance motions",
            "5. Plea Bargaining: Negotiations between prosecution and defense",
            "6. Trial: Jury trial with Sixth Amendment protections if no plea",
            "7. Sentencing: Federal Sentencing Guidelines applied if convicted",
            "8. Appeal: Direct appeal to Circuit Court; possible Supreme Court certiorari"
        ]
    },
    "us_appellate": {
        "steps": [
            "1. Notice of Appeal filed within 30 days of final judgment",
            "2. Appellant files opening brief",
            "3. Appellee files responsive brief",
            "4. Optional reply brief from appellant",
            "5. Oral argument if granted (10-15 minutes per side)",
            "6. Panel deliberation and published opinion",
            "7. Optional petition for rehearing en banc",
            "8. Optional petition for certiorari to Supreme Court"
        ]
    },
    "uk_civil": {
        "steps": [
            "1. Pre-Action Protocol: Letter before action with response period",
            "2. Claim Form and Particulars of Claim issued and served",
            "3. Defence filed within 14-28 days; optional Counterclaim",
            "4. Case Management Conference: Directions set by judge",
            "5. Disclosure: Standard disclosure of documents per CPR 31",
            "6. Witness Statements exchanged",
            "7. Expert Reports if directed (typically single joint expert)",
            "8. Trial before judge (no jury in civil cases)",
            "9. Judgment and Costs order"
        ]
    },
    "uk_criminal": {
        "steps": [
            "1. Arrest and Charge by police or Crown Prosecution Service",
            "2. First Appearance at Magistrates Court; mode of trial decision",
            "3. Either-way offences: defendant elects Crown Court or stays in Magistrates",
            "4. Crown Court: Arraignment, Plea and Trial Preparation Hearing",
            "5. Disclosure: Prosecution discloses evidence; defence statement",
            "6. Trial before judge and jury (12 jurors)",
            "7. Verdict: Unanimous or majority (10-2 or 11-1)",
            "8. Sentencing by judge if convicted",
            "9. Appeal to Court of Appeal Criminal Division"
        ]
    },
    "nigeria": {
        "steps": [
            "1. Originating Process: Writ of Summons or Originating Motion filed",
            "2. Service on defendant within stipulated time",
            "3. Pleadings: Statement of Claim, Defence, and Reply where applicable",
            "4. Case Management Conference under the front-loading system",
            "5. Discovery and Inspection of documents",
            "6. Hearing: Evidence-in-chief, cross-examination, re-examination",
            "7. Final written addresses by counsel",
            "8. Judgment delivered by the court",
            "9. Appeal to Court of Appeal, then Supreme Court of Nigeria"
        ]
    },
    "south_africa": {
        "steps": [
            "1. Summons or Combined Summons issued and served",
            "2. Notice of Intention to Defend within 10 court days",
            "3. Pleadings: Declaration, Plea, Replication where applicable",
            "4. Case management under court rules",
            "5. Discovery: Notice to discover documents",
            "6. Pre-trial conference",
            "7. Trial: Evidence, cross-examination, argument",
            "8. Judgment",
            "9. Appeal with leave to higher courts; Constitutional Court for constitutional matters"
        ]
    }
}

# ── Cross-Jurisdictional Comparison Data ───────────────────────────
CROSS_JURISDICTIONAL_DATA = {
    "defamation": {
        "us": "Public officials must prove actual malice (NYT v. Sullivan, 1964). Private figures: negligence standard. States vary on defamation per se.",
        "uk": "Defamation Act 2013 requires serious harm. Presumption of falsity; defendant must prove truth. Reynolds privilege for responsible journalism.",
        "nigeria": "Defamation is both a tort and a crime under the Criminal Code and Cybercrimes Act. Truth is a defence.",
        "south_africa": "Common law defamation requires publication of a false statement. Truth and public benefit defence.",
        "eu": "ECtHR requires proportionality between reputation protection and Article 10 ECHR freedom of expression."
    },
    "right_to_counsel": {
        "us": "Sixth Amendment guarantees counsel in criminal cases. Gideon v. Wainwright (1963) applied to states.",
        "uk": "Police and Criminal Evidence Act 1984 provides right to free legal advice at police stations.",
        "nigeria": "Section 36(6)(c) of the 1999 Constitution guarantees right to counsel.",
        "south_africa": "Section 35(2)(c) of the Constitution guarantees right to consult a legal practitioner.",
        "eu": "Article 6(3)(c) ECHR guarantees right to defend oneself through legal assistance."
    },
    "judicial_review": {
        "us": "Marbury v. Madison (1803) established judicial review. Standing requires injury-in-fact, causation, and redressability.",
        "uk": "No single written constitution. Judicial review based on common law and Human Rights Act 1998.",
        "nigeria": "Section 6 of the 1999 Constitution vests judicial power in the courts.",
        "south_africa": "Constitutional Court has exclusive jurisdiction on constitutional matters.",
        "eu": "European Court of Justice reviews validity of EU acts."
    },
    "death_penalty": {
        "us": "Permitted in 27 states and federal system. Gregg v. Georgia (1976) reinstated with safeguards.",
        "uk": "Abolished for murder in 1965. Completely abolished in 1998.",
        "nigeria": "Retained in law and practice. Sharia law in northern states provides for capital offences.",
        "south_africa": "Abolished by the Interim Constitution in 1995.",
        "eu": "Protocol 6 and 13 ECHR abolish death penalty in all circumstances."
    },
    "data_protection": {
        "us": "Sectoral approach: no comprehensive federal law. State laws like CCPA fill gaps.",
        "uk": "UK GDPR and Data Protection Act 2018. ICO enforcement.",
        "nigeria": "Nigeria Data Protection Regulation 2019. NDPC established 2023.",
        "south_africa": "POPIA (Protection of Personal Information Act) effective 2021.",
        "eu": "GDPR since 2018. Extraterritorial reach. Fines up to 4% global turnover."
    },
    "same_sex_marriage": {
        "us": "Obergefell v. Hodges (2015) legalized nationwide.",
        "uk": "Marriage (Same Sex Couples) Act 2013 legalized in England and Wales.",
        "nigeria": "Same Sex Marriage (Prohibition) Act 2013 criminalizes same-sex marriage.",
        "south_africa": "Legalized in 2006 via Civil Union Act. First African country.",
        "eu": "Not harmonized at EU level. 21 of 27 Member States have legalized."
    },
    "freedom_of_expression": {
        "us": "First Amendment provides broad protection. Hate speech generally protected unless incitement.",
        "uk": "Article 10 ECHR protects free expression as a qualified right.",
        "nigeria": "Section 39 of the 1999 Constitution guarantees free expression.",
        "south_africa": "Section 16 guarantees freedom of expression with exclusions for propaganda for war and hate speech.",
        "eu": "Article 10 ECHR guarantees freedom of expression as a qualified right."
    },
    "double_jeopardy": {
        "us": "Fifth Amendment prohibits double jeopardy. Separate sovereigns doctrine applies.",
        "uk": "Abolished double jeopardy for serious crimes via Criminal Justice Act 2003.",
        "nigeria": "Section 36(9) of the Constitution prohibits double jeopardy.",
        "south_africa": "Section 35(3)(m) guarantees right not to be tried for an offence previously convicted or acquitted.",
        "eu": "Article 4 Protocol 7 ECHR prohibits double jeopardy (ne bis in idem)."
    },
    "right_to_health": {
        "us": "No constitutional right to health care. ACA expanded access but no universal coverage.",
        "uk": "NHS provides universal health care free at point of use.",
        "nigeria": "Not justiciable under Chapter 2 of the Constitution (directive principles).",
        "south_africa": "Right to access health care services in Section 27. Reasonableness standard.",
        "eu": "Not an EU competence. Member States organize health care."
    }
}


# ── Utility ─────────────────────────────────────────────────────────

def _ensure_db():
    """Ensure SQLite database exists for law studies."""
    db_path = Path("luqi_law.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bar_exam_progress (
            user_id TEXT,
            question_id TEXT,
            subject TEXT,
            correct INTEGER,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinic_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            client_name TEXT,
            facts TEXT,
            area TEXT,
            issues TEXT,
            advice TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# LegalResearchEngine
# ═══════════════════════════════════════════════════════════════════

class LegalResearchEngine:
    """Comprehensive legal research engine."""

    def research(self, query: str, jurisdiction: str = "us", area: str = "general") -> Dict[str, Any]:
        """Perform legal research on a query."""
        query_lower = query.lower()
        results = {
            "query": query,
            "jurisdiction": jurisdiction,
            "area": area,
            "principles": [],
            "relevant_cases": [],
            "statutes": [],
            "procedural_notes": [],
        }
        for case in LANDMARK_CASES:
            if case["jurisdiction"] == jurisdiction or jurisdiction == "all":
                if (area == "general" or case["area"] == area or
                    any(word in case["holding"].lower() for word in query_lower.split())):
                    results["relevant_cases"].append(case)
        area_principles = {
            "contracts": [
                "Offer, acceptance, and consideration are the essential elements of a contract.",
                "A contract requires mutual assent (meeting of the minds) and valid consideration.",
                "The parol evidence rule limits extrinsic evidence to vary contractual terms.",
            ],
            "torts": [
                "Negligence requires duty, breach, causation, and damages.",
                "The reasonable person standard is the benchmark for assessing duty and breach.",
                "Strict liability applies to abnormally dangerous activities and defective products.",
            ],
            "criminal": [
                "Actus reus (guilty act) and mens rea (guilty mind) are the two elements of a crime.",
                "The burden of proof in criminal cases is beyond a reasonable doubt.",
                "Defences include self-defence, necessity, duress, insanity, and intoxication.",
            ],
            "constitutional": [
                "Judicial review empowers courts to invalidate unconstitutional laws (Marbury v. Madison).",
                "The Bill of Rights protects fundamental liberties including speech, religion, and due process.",
                "Equal Protection requires similarly situated persons to be treated equally.",
            ],
            "property": [
                "Property rights include the right to possess, use, exclude, and transfer.",
                "Adverse possession allows a non-owner to acquire title through continuous, open possession.",
                "Easements grant limited use rights over another's property.",
            ],
            "evidence": [
                "Relevant evidence is admissible unless excluded by specific rules (FRE 402).",
                "Hearsay is an out-of-court statement offered for the truth of the matter asserted.",
                "Expert testimony must be reliable and based on sufficient facts (Daubert standard).",
            ],
            "human_rights": [
                "Human rights are universal, inalienable, and indivisible.",
                "The ICCPR and ICESCR are the core international human rights treaties.",
                "Derogation from certain rights is permitted only in times of public emergency.",
            ],
        }
        if area in area_principles:
            results["principles"] = area_principles[area]
        else:
            results["principles"] = ["Consult relevant statutes and case law for this area of law."]
        jurisdiction_notes = {
            "us": "United States law draws from federal and state sources.",
            "uk": "UK law comprises statutes, common law, and EU retained law.",
            "nigeria": "Nigerian law is based on the 1999 Constitution, statutes, received English law, customary law, and Sharia law.",
            "south_africa": "South African law draws from the 1996 Constitution, Roman-Dutch common law, statutes, and customary law.",
            "eu": "EU law comprises treaties, regulations, directives, and decisions.",
        }
        results["procedural_notes"] = [jurisdiction_notes.get(jurisdiction, "Consult local legal sources.")]
        return results

    def search_cases(self, keywords: str, jurisdiction: Optional[str] = None,
                     area: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search landmark cases by keywords, jurisdiction, or area."""
        keywords_lower = keywords.lower().split()
        results = []
        for case in LANDMARK_CASES:
            if jurisdiction and case["jurisdiction"] != jurisdiction:
                continue
            if area and case["area"] != area:
                continue
            text = f"{case['name']} {case['holding']} {case['significance']}".lower()
            if any(kw in text for kw in keywords_lower):
                results.append(case)
        return results

    def get_case(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a landmark case by name (partial match)."""
        name_lower = name.lower()
        for case in LANDMARK_CASES:
            if name_lower in case["name"].lower():
                return case
        return None

    def compare_jurisdictions(self, topic: str, jurisdictions: List[str] = None) -> Dict[str, Any]:
        """Compare how different jurisdictions treat a legal topic."""
        if jurisdictions is None:
            jurisdictions = ["us", "uk", "nigeria", "south_africa", "eu"]
        topic_key = topic.lower().replace(" ", "_")
        data = CROSS_JURISDICTIONAL_DATA.get(topic_key, {})
        comparison = {"topic": topic, "jurisdictions": {}}
        for j in jurisdictions:
            comparison["jurisdictions"][j] = data.get(j, f"No data available for {j} on this topic.")
        return comparison

    def interpret_statute(self, statute_text: str, question: str) -> Dict[str, Any]:
        """Interpret a statute using canons of statutory interpretation."""
        return {
            "statute": statute_text[:200],
            "question": question,
            "literal_meaning": "The plain language of the statute suggests the following interpretation.",
            "purposive_interpretation": "Considering the purpose and legislative intent.",
            "golden_rule": "Under the golden rule, an absurd literal interpretation should be avoided.",
            "mischief_rule": "The Heydon's Case approach asks what mischief the statute was enacted to remedy.",
            "ejusdem_generis": "General words following specific words are limited to items of the same class.",
            "expressio_unius": "The inclusion of specific items implies the exclusion of others.",
            "contra_proferentem": "Ambiguity is construed against the drafter.",
            "conclusion": "Based on the text and applicable canons, the answer depends on judicial interpretation in the relevant jurisdiction.",
        }

    def lookup_evidence_rule(self, rule_number: Optional[str] = None,
                             topic: Optional[str] = None) -> Dict[str, Any]:
        """Look up a Federal Rule of Evidence."""
        if rule_number and rule_number in FEDERAL_RULES_OF_EVIDENCE:
            rule = FEDERAL_RULES_OF_EVIDENCE[rule_number]
            return {"rule_number": rule_number, **rule}
        if topic:
            topic_lower = topic.lower()
            for num, rule in FEDERAL_RULES_OF_EVIDENCE.items():
                if topic_lower in rule["title"].lower() or topic_lower in rule["text"].lower():
                    return {"rule_number": num, **rule}
        return {"error": "Rule not found. Try a rule number (e.g., '401') or topic (e.g., 'hearsay')."}


# ═══════════════════════════════════════════════════════════════════
# DocumentDraftingEngine
# ═══════════════════════════════════════════════════════════════════

class DocumentDraftingEngine:
    """Draft legal documents from templates."""

    def draft_contract(self, contract_type: str, parties: Dict[str, str],
                       terms: Dict[str, str], jurisdiction: str = "us") -> Dict[str, str]:
        """Draft a contract from a template."""
        if contract_type == "nda":
            template = self._get_nda_template()
        elif contract_type == "employment":
            template = self._get_employment_template()
        elif contract_type == "service":
            template = self._get_service_template()
        elif contract_type == "partnership":
            template = self._get_partnership_template()
        else:
            return {"error": f"Unknown contract type: {contract_type}. Available: nda, employment, service, partnership"}
        variables = {**parties, **terms, "jurisdiction": jurisdiction,
                     "date": datetime.now().strftime("%B %d, %Y")}
        try:
            drafted = template.format(**variables)
        except KeyError as e:
            return {"error": f"Missing variable: {e}. Required variables depend on contract type."}
        return {"contract_type": contract_type, "jurisdiction": jurisdiction,
                "draft": drafted, "word_count": len(drafted.split())}

    def _get_nda_template(self) -> str:
        return """NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement is entered into as of {date}, between {discloser_name} ("Discloser") and {recipient_name} ("Recipient").

1. DEFINITION OF CONFIDENTIAL INFORMATION
Confidential Information means any and all non-public, proprietary, or confidential information disclosed by the Discloser, including but not limited to: trade secrets, technical data, business plans, customer lists, financial information, and software code.

2. OBLIGATIONS OF RECIPIENT
The Recipient agrees to: (a) hold all Confidential Information in strict confidence; (b) not disclose to any third parties without prior written consent; (c) use solely for the purpose of {purpose}.

3. TERM
This Agreement shall remain in effect for {term} years from the date of execution.

4. GOVERNING LAW
This Agreement shall be governed by the laws of {jurisdiction}.

Signed:
_________________________           _________________________
{discloser_name}                     {recipient_name}
"""

    def _get_employment_template(self) -> str:
        return """EMPLOYMENT AGREEMENT

This Employment Agreement is made as of {start_date}, between {employer_name} ("Employer") and {employee_name} ("Employee").

1. POSITION
The Employee is employed as {job_title} and shall perform such duties as may be assigned.

2. COMPENSATION
The Employee shall receive an annual salary of {salary}, payable according to the Employer payroll schedule.

3. BENEFITS
The Employee shall be entitled to: {benefits}.

4. TERM
This Agreement commences on {start_date} and continues until terminated by either party with {notice_period} notice.

5. CONFIDENTIALITY
The Employee agrees to maintain the confidentiality of all proprietary information.

6. GOVERNING LAW
This Agreement shall be governed by the laws of {jurisdiction}.

_________________________           _________________________
Employer                              Employee
"""

    def _get_service_template(self) -> str:
        return """SERVICE AGREEMENT

This Service Agreement is entered into as of {date}, between {provider_name} ("Provider") and {client_name} ("Client").

1. SERVICES
The Provider shall provide the following services: {services_description}.

2. COMPENSATION
The Client shall pay {fee} as agreed. Payment terms: {payment_terms}.

3. TERM
This Agreement shall commence on {start_date} and continue for {term}.

4. TERMINATION
Either party may terminate with {notice_period} written notice.

5. LIMITATION OF LIABILITY
The Provider liability shall not exceed the total fees paid under this Agreement.

6. GOVERNING LAW
This Agreement shall be governed by the laws of {jurisdiction}.

_________________________           _________________________
{provider_name}                       {client_name}
"""

    def _get_partnership_template(self) -> str:
        return """PARTNERSHIP AGREEMENT

This Partnership Agreement is made as of {date}, between {partner1_name} and {partner2_name} (collectively, the "Partners").

1. PARTNERSHIP NAME AND PURPOSE
The Partners hereby form a partnership named {partnership_name} for the purpose of {purpose}.

2. CAPITAL CONTRIBUTIONS
{partner1_name} shall contribute: {partner1_contribution}.
{partner2_name} shall contribute: {partner2_contribution}.

3. PROFIT AND LOSS SHARING
Profits and losses shall be shared as follows: {profit_sharing}.

4. MANAGEMENT
Partners shall share management responsibilities as agreed. Major decisions require unanimous consent.

5. DISSOLUTION
The partnership may be dissolved by mutual agreement or as provided by law.

6. GOVERNING LAW
This Agreement shall be governed by the laws of {jurisdiction}.

_________________________           _________________________
{partner1_name}                       {partner2_name}
"""

    def draft_document(self, template_name: str, variables: Dict[str, str],
                       jurisdiction: str = "us") -> Dict[str, str]:
        """Draft a legal document from a named template."""
        templates = {
            "demand_letter": self._get_demand_letter_template(),
            "cease_and_desist": self._get_cease_desist_template(),
        }
        if template_name not in templates:
            return {"error": f"Unknown template: {template_name}. Available: {list(templates.keys())}"}
        variables.setdefault("date", datetime.now().strftime("%B %d, %Y"))
        variables.setdefault("jurisdiction", jurisdiction)
        try:
            drafted = templates[template_name].format(**variables)
        except KeyError as e:
            return {"error": f"Missing variable: {e}"}
        return {"template": template_name, "jurisdiction": jurisdiction,
                "draft": drafted, "word_count": len(drafted.split())}

    def _get_demand_letter_template(self) -> str:
        return """{sender_name}
{sender_address}

Date: {date}

{recipient_name}
{recipient_address}

RE: DEMAND LETTER - {matter_description}

Dear {recipient_name}:

This letter serves as a formal demand regarding {matter_description}.

FACTS:
{facts}

DEMAND:
{demand}

LEGAL BASIS:
{legal_basis}

Please comply within {deadline} days. Failure may result in legal action.

Sincerely,

_________________________
{sender_name}
"""

    def _get_cease_desist_template(self) -> str:
        return """CEASE AND DESIST LETTER

Date: {date}

To: {recipient_name}
{recipient_address}

RE: Cease and Desist - {violation_type}

Dear {recipient_name}:

We represent {client_name}. It has come to our attention that you have engaged in {violation_description}.

This letter serves as formal notice that your actions constitute {legal_claims}. Under {applicable_law}, our client is entitled to {requested_relief}.

We hereby demand that you immediately:
{specific_demands}

Failure to comply within {deadline} days will result in legal action seeking all available remedies.

Preserve all documents relating to this matter.

Sincerely,

_________________________
{lawyer_name}
Attorney for {client_name}
"""

    def analyze_contract(self, contract_text: str) -> Dict[str, Any]:
        """Analyze a contract for risks, missing clauses, and recommendations."""
        text_lower = contract_text.lower()
        issues = []
        recommendations = []
        essential_clauses = {
            "governing law": "jurisdiction",
            "confidential": "confidentiality",
            "terminate": "termination",
            "liability": "limitation of liability",
            "indemnif": "indemnification",
            "force majeure": "force majeure",
            "dispute": "dispute resolution",
            "assignment": "assignment",
            "warrant": "warranties",
            "intellectual property": "IP rights",
            "payment": "payment terms",
            "notice": "notice provisions",
        }
        found_clauses = []
        missing_clauses = []
        for clause, name in essential_clauses.items():
            if clause in text_lower:
                found_clauses.append(name)
            else:
                missing_clauses.append(name)
                issues.append(f"Missing clause: {name}")
                recommendations.append(f"Add a {name} clause to protect both parties.")
        risk_level = "low"
        if len(missing_clauses) > 5:
            risk_level = "high"
        elif len(missing_clauses) > 2:
            risk_level = "medium"
        if "limitation of liability" in missing_clauses:
            recommendations.append("CRITICAL: No limitation of liability clause exposes parties to unlimited damages.")
        if "confidentiality" in missing_clauses and any(w in text_lower for w in ["proprietary", "trade secret", "confidential"]):
            recommendations.append("CRITICAL: Confidential information mentioned but no confidentiality clause found.")
        return {
            "risk_level": risk_level,
            "found_clauses": found_clauses,
            "missing_clauses": missing_clauses,
            "issues": issues,
            "recommendations": recommendations,
            "word_count": len(contract_text.split()),
            "disclaimer": "This is an automated analysis for educational purposes only and does not constitute legal advice.",
        }

    def list_templates(self) -> Dict[str, Any]:
        """List all available templates."""
        return {
            "contracts": ["nda", "employment", "service", "partnership"],
            "documents": ["demand_letter", "cease_and_desist"],
        }


# ═══════════════════════════════════════════════════════════════════
# CaseBriefEngine
# ═══════════════════════════════════════════════════════════════════

class CaseBriefEngine:
    """Generate structured case briefs using IRAC, CREAC, CRAC, and other methods."""

    def brief_case(self, case_text_or_name: str, method: str = "IRAC") -> Dict[str, Any]:
        """Brief a case by name or text using the specified method."""
        if method.upper() not in ["IRAC", "CREAC", "CRAC", "TREAC", "SINAC"]:
            return {"error": f"Unknown method: {method}. Use IRAC, CREAC, CRAC, TREAC, or SINAC."}
        case = None
        for lc in LANDMARK_CASES:
            if lc["name"].lower() in case_text_or_name.lower() or case_text_or_name.lower() in lc["name"].lower():
                case = lc
                break
        if case:
            return self._brief_from_case(case, method.upper())
        else:
            return self._brief_from_text(case_text_or_name, method.upper())

    def brief_landmark(self, case_name: str, method: str = "IRAC") -> Dict[str, Any]:
        """Brief a landmark case by exact or partial name."""
        case = None
        for lc in LANDMARK_CASES:
            if case_name.lower() in lc["name"].lower():
                case = lc
                break
        if not case:
            return {"error": f"Landmark case not found: {case_name}"}
        return self._brief_from_case(case, method.upper())

    def _brief_from_case(self, case: Dict[str, Any], method: str) -> Dict[str, Any]:
        """Generate a brief from a landmark case entry."""
        issue = f"Whether {case['area']} law permits or prohibits the action at issue in {case['name']}."
        rule = f"The governing legal principle is established by precedent and statutory authority, as applied in {case['name']}."
        application = f"In {case['name']}, the court applied the rule to the facts. {case['holding']}"
        conclusion = f"The court held that {case['holding']} This has significant implications: {case['significance']}"
        brief = {
            "case_name": case["name"],
            "citation": case["citation"],
            "jurisdiction": case["jurisdiction"],
            "area": case["area"],
            "method": method,
            "full_cite": f"{case['name']}, {case['citation']}",
        }
        if method == "IRAC":
            brief.update({"Issue": issue, "Rule": rule, "Application": application, "Conclusion": conclusion})
        elif method == "CREAC":
            brief.update({
                "Conclusion": f"The court held that {case['holding']}",
                "Rule": rule,
                "Explanation": f"The court explained that {case['significance']}",
                "Application": application,
                "Conclusion_reaffirmed": conclusion,
            })
        elif method == "CRAC":
            brief.update({
                "Conclusion": f"The court held that {case['holding']}",
                "Rule": rule,
                "Application": application,
                "Conclusion_reaffirmed": conclusion,
            })
        elif method == "TREAC":
            brief.update({
                "Thesis": f"The resolution of this case hinges on the interpretation of {case['area']} principles.",
                "Rule": rule,
                "Explanation": f"The court explained that {case['significance']}",
                "Application": application,
                "Conclusion": conclusion,
            })
        elif method == "SINAC":
            brief.update({
                "Statement": f"This case addresses the scope of {case['area']} law.",
                "Issue": issue,
                "Next_steps": "The court proceeded to analyze the governing rule and apply it.",
                "Analysis": application,
                "Conclusion": conclusion,
            })
        return brief

    def _brief_from_text(self, case_text: str, method: str) -> Dict[str, Any]:
        """Generate a brief framework from raw case text."""
        brief = {
            "case_name": "[Extract from text]",
            "citation": "[Not provided]",
            "method": method,
            "note": "This is a framework based on the provided text. Please fill in the details.",
        }
        if method == "IRAC":
            brief.update({
                "Issue": "[State the legal question the court is answering]",
                "Rule": "[State the governing legal principle, statute, or precedent]",
                "Application": "[Explain how the court applied the rule to the facts]",
                "Conclusion": "[State the court holding and disposition]",
            })
        elif method == "CREAC":
            brief.update({
                "Conclusion": "[State the court ultimate holding]",
                "Rule": "[State the governing legal principle]",
                "Explanation": "[Explain the rule origin and how it has been applied]",
                "Application": "[Apply the rule to the facts of this case]",
                "Conclusion_reaffirmed": "[Restate the holding and its significance]",
            })
        elif method == "CRAC":
            brief.update({
                "Conclusion": "[State the court holding]",
                "Rule": "[State the governing legal principle]",
                "Application": "[Explain how the rule applies to the facts]",
                "Conclusion_reaffirmed": "[Restate the holding]",
            })
        return brief


# ═══════════════════════════════════════════════════════════════════
# BarExamEngine
# ═══════════════════════════════════════════════════════════════════

class BarExamEngine:
    """MBE-style bar exam preparation engine."""

    QUESTION_BANK = [
        {"id": "con_001", "subject": "constitutional", "difficulty": 1,
         "question": "Which clause of the Constitution grants Congress the power to regulate interstate commerce?",
         "options": ["A. The Commerce Clause", "B. The Necessary and Proper Clause", "C. The Supremacy Clause", "D. The Full Faith and Credit Clause"],
         "answer": "A", "explanation": "Article I, Section 8, Clause 3 (the Commerce Clause) grants Congress the power to regulate interstate commerce."},
        {"id": "con_002", "subject": "constitutional", "difficulty": 2,
         "question": "Under the Equal Protection Clause, which standard of review applies to classifications based on race?",
         "options": ["A. Rational basis review", "B. Intermediate scrutiny", "C. Strict scrutiny", "D. Minimum rationality"],
         "answer": "C", "explanation": "Strict scrutiny applies to classifications based on race, national origin, and alienage. The government must show the classification is narrowly tailored to achieve a compelling government interest."},
        {"id": "con_003", "subject": "constitutional", "difficulty": 2,
         "question": "A state law prohibits all commercial billboards along highways. A company challenges the law as a violation of the First Amendment. The court will likely apply:",
         "options": ["A. Strict scrutiny", "B. Intermediate scrutiny", "C. Central Hudson test", "D. Rational basis review"],
         "answer": "C", "explanation": "Commercial speech restrictions are evaluated under the Central Hudson test: (1) lawful activity and not misleading; (2) substantial government interest; (3) directly advances the interest; (4) narrowly tailored."},
        {"id": "con_004", "subject": "constitutional", "difficulty": 3,
         "question": "Under the Due Process Clause, which of the following procedures is NOT required before a deprivation of property?",
         "options": ["A. Notice", "B. Hearing", "C. Right to counsel at state expense", "D. Neutral decision-maker"],
         "answer": "C", "explanation": "Due process requires notice and a meaningful opportunity to be heard before a neutral decision-maker. The right to appointed counsel at state expense applies only in certain criminal contexts (Gideon), not civil property deprivations."},
        {"id": "con_005", "subject": "constitutional", "difficulty": 2,
         "question": "The doctrine of state action requires that:",
         "options": ["A. Only federal actors can violate constitutional rights", "B. Constitutional rights can only be violated by government actors or private actors performing public functions", "C. Private actors can never violate constitutional rights", "D. State legislatures must approve all federal actions"],
         "answer": "B", "explanation": "The state action doctrine requires that constitutional rights be violated by government actors or private actors performing public functions or acting under color of law."},
        {"id": "contract_001", "subject": "contracts", "difficulty": 1,
         "question": "Which of the following is NOT an essential element of a valid contract?",
         "options": ["A. Offer", "B. Acceptance", "C. Consideration", "D. Written form"],
         "answer": "D", "explanation": "Written form is generally not required for a valid contract (except under the Statute of Frauds for certain types of contracts). Offer, acceptance, and consideration are the essential elements."},
        {"id": "contract_002", "subject": "contracts", "difficulty": 2,
         "question": "Under the mailbox rule, an acceptance is effective when:",
         "options": ["A. The offeror receives it", "B. The offeree dispatches it", "C. The offeree reads the offer", "D. The offeror reads the acceptance"],
         "answer": "B", "explanation": "Under the mailbox rule, an acceptance is generally effective upon dispatch (when placed in the mail), while a revocation is effective only upon receipt."},
        {"id": "contract_003", "subject": "contracts", "difficulty": 2,
         "question": "The parol evidence rule prevents:",
         "options": ["A. Evidence of fraud in the inducement", "B. Evidence of subsequent modifications", "C. Extrinsic evidence to contradict or vary the terms of an integrated written agreement", "D. Evidence of custom and usage in the industry"],
         "answer": "C", "explanation": "The parol evidence rule bars extrinsic evidence (prior or contemporaneous agreements) to contradict, modify, or vary the terms of a fully integrated written agreement. It does not bar evidence of fraud, subsequent modifications, or interpretation aids."},
        {"id": "crim_001", "subject": "criminal", "difficulty": 1,
         "question": "The mens rea requirement for a general intent crime requires proof of:",
         "options": ["A. Intent to commit the specific actus reus of the crime", "B. Intent to achieve a specific result beyond the act itself", "C. Recklessness as to the consequences", "D. Knowledge of the criminal nature of the act"],
         "answer": "A", "explanation": "General intent crimes require only proof that the defendant intended to commit the actus reus (the physical act). Specific intent crimes require proof of intent to achieve a particular result."},
        {"id": "crim_002", "subject": "criminal", "difficulty": 2,
         "question": "Under the Model Penal Code, a person acts purposely when:",
         "options": ["A. The person is aware of a substantial and unjustifiable risk", "B. It is the person conscious object to engage in conduct of that nature or cause such a result", "C. The person should be aware of a substantial and unjustifiable risk", "D. The person is aware of the nature of the conduct but not the result"],
         "answer": "B", "explanation": "Under the MPC, a person acts purposely when it is their conscious object to engage in conduct of that nature or to cause such a result. This is the highest level of culpability."},
        {"id": "crim_003", "subject": "criminal", "difficulty": 2,
         "question": "The exclusionary rule under the Fourth Amendment:",
         "options": ["A. Applies only to federal prosecutions", "B. Excludes evidence obtained in violation of the defendant constitutional rights", "C. Applies only to physical evidence, not statements", "D. Has been abolished by the Supreme Court"],
         "answer": "B", "explanation": "The exclusionary rule (Mapp v. Ohio) excludes evidence obtained in violation of the Fourth Amendment from being used in both federal and state criminal prosecutions."},
        {"id": "evid_001", "subject": "evidence", "difficulty": 1,
         "question": "Under the Federal Rules of Evidence, relevant evidence is:",
         "options": ["A. Evidence that proves the defendant guilt beyond a reasonable doubt", "B. Evidence that has any tendency to make a fact more or less probable", "C. Evidence that is admissible in all circumstances", "D. Evidence that is presented by an expert witness"],
         "answer": "B", "explanation": "FRE 401 defines relevant evidence as evidence that has any tendency to make a fact more or less probable than it would be without the evidence, and the fact is of consequence in determining the action."},
        {"id": "evid_002", "subject": "evidence", "difficulty": 2,
         "question": "Which of the following is hearsay?",
         "options": ["A. A witness testifying about what they personally observed", "B. A witness testifying about what another person told them, offered to prove the truth of the matter asserted", "C. A defendant own out-of-court statement offered against them", "D. A recorded recollection read into evidence"],
         "answer": "B", "explanation": "Hearsay is an out-of-court statement offered to prove the truth of the matter asserted. A witness testifying about what another person told them, offered for its truth, is classic hearsay."},
        {"id": "evid_003", "subject": "evidence", "difficulty": 2,
         "question": "Under the Confrontation Clause, testimonial hearsay is admissible only if:",
         "options": ["A. The declarant is unavailable and the defendant had a prior opportunity to cross-examine", "B. The statement falls within a recognized hearsay exception", "C. The statement is reliable", "D. The prosecution proves the statement by a preponderance of the evidence"],
         "answer": "A", "explanation": "Under Crawford v. Washington, testimonial hearsay is admissible against a criminal defendant only if the declarant is unavailable and the defendant had a prior opportunity to cross-examine."},
        {"id": "torts_001", "subject": "torts", "difficulty": 1,
         "question": "The elements of a negligence claim are:",
         "options": ["A. Duty, breach, causation, and damages", "B. Intent, causation, and damages", "C. Duty, breach, and strict liability", "D. foreseeability, duty, and proximate cause"],
         "answer": "A", "explanation": "To establish negligence, a plaintiff must prove: (1) the defendant owed a duty of care; (2) the defendant breached that duty; (3) the breach caused the plaintiff injury (both actual and proximate cause); and (4) the plaintiff suffered damages."},
        {"id": "torts_002", "subject": "torts", "difficulty": 2,
         "question": "Under the doctrine of res ipsa loquitur:",
         "options": ["A. The defendant is strictly liable", "B. The plaintiff must prove the exact mechanism of injury", "C. The accident is of a type that ordinarily does not occur in the absence of negligence", "D. The defendant had exclusive control of the instrumentality causing injury and the accident is of a type that does not ordinarily occur without negligence"],
         "answer": "D", "explanation": "Res ipsa loquitur requires: (1) the event is of a kind that ordinarily does not occur in the absence of negligence; (2) the instrumentality causing the injury was under the defendant exclusive control; and (3) the plaintiff did not contribute to the cause."},
        {"id": "prop_001", "subject": "property", "difficulty": 1,
         "question": "Adverse possession requires which of the following elements?",
         "options": ["A. Actual, open, notorious, exclusive, continuous, and hostile possession for the statutory period", "B. Permission from the true owner for the statutory period", "C. Payment of property taxes for five years", "D. Recording a claim with the county recorder"],
         "answer": "A", "explanation": "Adverse possession requires actual, open and notorious, exclusive, continuous, and hostile (without permission) possession for the statutory period."},
        {"id": "civpro_001", "subject": "civil_procedure", "difficulty": 1,
         "question": "Under the Erie doctrine, federal courts sitting in diversity jurisdiction must apply:",
         "options": ["A. Federal substantive law and state procedural law", "B. State substantive law and federal procedural law", "C. Only federal law", "D. Only state law"],
         "answer": "B", "explanation": "Under Erie R.R. Co. v. Tompkins, federal courts in diversity apply state substantive law and federal procedural law (the Rules Enabling Act/Federal Rules of Civil Procedure)."},
        {"id": "civpro_002", "subject": "civil_procedure", "difficulty": 2,
         "question": "For a federal court to exercise personal jurisdiction over a defendant under the Due Process Clause, the defendant must have:",
         "options": ["A. Minimum contacts with the forum state such that exercising jurisdiction does not offend traditional notions of fair play and substantial justice", "B. A principal place of business in the forum state", "C. Consented to jurisdiction in writing", "D. Committed a crime in the forum state"],
         "answer": "A", "explanation": "Under International Shoe, a court may exercise personal jurisdiction if the defendant has minimum contacts with the forum such that exercising jurisdiction does not offend traditional notions of fair play and substantial justice."},
        {"id": "prof_001", "subject": "professional_responsibility", "difficulty": 1,
         "question": "Under the ABA Model Rules, a lawyer may reveal confidential information to prevent:",
         "options": ["A. Any crime the client intends to commit", "B. A crime the client intends to commit that is likely to result in imminent death or bodily harm", "C. Any financial loss to a third party", "D. Any civil wrong the client intends to commit"],
         "answer": "B", "explanation": "Model Rule 1.6 permits (but does not require) disclosure to prevent the client from committing a crime that is likely to result in imminent death or substantial bodily harm."},
    ]

    def generate_question(self, subject: str = "constitutional", difficulty: int = 1) -> Dict[str, Any]:
        """Generate an MBE-style question for the given subject."""
        questions = [q for q in self.QUESTION_BANK
                     if q["subject"] == subject and q["difficulty"] <= difficulty + 1]
        if not questions:
            questions = [q for q in self.QUESTION_BANK if q["subject"] == subject]
        if not questions:
            return {"error": f"No questions available for subject: {subject}. Available: {list(set(q['subject'] for q in self.QUESTION_BANK))}"}
        question = random.choice(questions)
        return {
            "question_id": question["id"],
            "subject": question["subject"],
            "difficulty": question["difficulty"],
            "question": question["question"],
            "options": question["options"],
        }

    def check_answer(self, question_id: str, answer: str) -> Dict[str, Any]:
        """Check a bar exam answer and provide explanation."""
        for q in self.QUESTION_BANK:
            if q["id"] == question_id:
                correct = q["answer"].upper() == answer.upper()
                return {
                    "question_id": question_id,
                    "your_answer": answer,
                    "correct_answer": q["answer"],
                    "correct": correct,
                    "explanation": q["explanation"],
                }
        return {"error": f"Question not found: {question_id}"}

    def get_subjects(self) -> List[Dict[str, str]]:
        """List all bar exam subjects with question counts."""
        subjects = {}
        for q in self.QUESTION_BANK:
            subjects[q["subject"]] = subjects.get(q["subject"], 0) + 1
        return [{"subject": s, "question_count": c} for s, c in subjects.items()]


# ═══════════════════════════════════════════════════════════════════
# LegalCitationGenerator
# ═══════════════════════════════════════════════════════════════════

class LegalCitationGenerator:
    """Generate legal citations in multiple styles."""

    def cite_case(self, case_name: str, reporter: str, volume: str, page: str,
                  year: str, style: str = "bluebook") -> str:
        """Generate a case citation in the specified style."""
        style = style.lower()
        if style == "bluebook":
            return f"{case_name}, {volume} {reporter} {page} ({year})."
        elif style == "apa":
            return f"{case_name} ({year}). {volume} {reporter} {page}."
        elif style == "oscola":
            return f"{case_name} [{year}] {volume} {reporter} {page}"
        elif style == "chicago":
            return f"{case_name}, {volume} {reporter} {page} ({year})."
        elif style == "mla":
            return f"{case_name}. {reporter}, vol. {volume}, {year}, p. {page}."
        else:
            return f"{case_name}, {volume} {reporter} {page} ({year})."

    def cite_statute(self, title: str, section: str, year: str,
                     jurisdiction: str = "us", style: str = "bluebook") -> str:
        """Generate a statute citation."""
        style = style.lower()
        if style == "bluebook":
            if jurisdiction == "us":
                return f"{title} U.S.C. {section} ({year})."
            return f"{title} {jurisdiction.upper()} {section} ({year})."
        elif style == "oscola":
            return f"{title} {section} ({year})"
        else:
            return f"{title}, Section {section} ({year})."

    def cite_constitution(self, country: str = "US", article: str = "I",
                          section: str = "1", style: str = "bluebook") -> str:
        """Generate a constitutional citation."""
        if style.lower() == "bluebook":
            return f"U.S. Const. art. {article}, {section}."
        return f"{country} Constitution, Article {article}, Section {section}."


# ═══════════════════════════════════════════════════════════════════
# MootCourtEngine
# ═══════════════════════════════════════════════════════════════════

class MootCourtEngine:
    """Generate moot court problems and prepare arguments."""

    PROBLEMS = [
        {
            "area": "constitutional",
            "title": "Free Speech vs. National Security",
            "facts": "A state university student published an article on a campus blog criticizing the government foreign policy and urging readers to refuse military service. The university, citing a policy against speech that undermines national security, suspended the student for one semester. The student challenges the suspension as a violation of First Amendment rights.",
            "issues": ["Whether a public university can punish a student for political speech criticizing government policy.", "Whether urging refusal of military service constitutes unprotected incitement under Brandenburg."],
        },
        {
            "area": "human_rights",
            "title": "Right to Water",
            "facts": "A municipality in a developing nation cut off water supply to an informal settlement, citing unpaid bills and illegal connections. Residents, including children and elderly persons, were left without access to clean water for three months. A human rights organization brings a case alleging violation of the right to water.",
            "issues": ["Whether the right to water is justiciable under international human rights law.", "Whether the state budgetary constraints justify the denial of essential water services."],
        },
        {
            "area": "criminal",
            "title": "Self-Defence and Proportionality",
            "facts": "A homeowner shot and killed an unarmed intruder who had entered their home at night. The homeowner testified they feared for their life. State law permits the use of deadly force in self-defence only when the person reasonably believes it is necessary to prevent imminent death or serious bodily harm.",
            "issues": ["Whether the homeowner subjective fear satisfies the objective reasonableness standard.", "Whether the castle doctrine applies to eliminate the duty to retreat inside the home."],
        },
        {
            "area": "torts",
            "title": "Product Liability and Warning Defects",
            "facts": "A pharmaceutical company manufactured a widely used pain reliever. Studies showed a small but significant risk of heart attack with prolonged use. The company included a brief warning in the packaging but did not prominently display the risk. A patient who used the medication for five years suffered a heart attack and sues for failure to warn.",
            "issues": ["Whether the warning was adequate under the learned intermediary doctrine.", "Whether the company had a duty to conduct post-market surveillance and update warnings."],
        },
    ]

    def generate_problem(self, area: str = "constitutional", complexity: int = 2) -> Dict[str, Any]:
        """Generate a moot court problem."""
        problems = [p for p in self.PROBLEMS if p["area"] == area]
        if not problems:
            problems = self.PROBLEMS
        problem = random.choice(problems)
        return {
            "area": problem["area"],
            "title": problem["title"],
            "facts": problem["facts"],
            "issues": problem["issues"],
            "appellant_arguments": self._generate_arguments("appellant", problem),
            "respondent_arguments": self._generate_arguments("respondent", problem),
        }

    def _generate_arguments(self, side: str, problem: Dict[str, Any]) -> List[str]:
        """Generate suggested arguments for a given side."""
        if side == "appellant":
            return [
                "The lower court erred in [legal standard]. The facts clearly demonstrate [application to facts].",
                "Precedent from [relevant case] supports the position that [legal principle].",
                "The policy considerations favour the appellant because [policy argument].",
                "The burden of proof was improperly allocated in the lower court.",
            ]
        return [
            "The lower court correctly applied [legal standard] to the facts.",
            "Distinguishing [relevant case]: the facts here are materially different because [distinction].",
            "The appellant interpretation would lead to [undesirable policy consequence].",
            "Deference to the lower court findings of fact is warranted under the standard of review.",
        ]

    def prep_arguments(self, side: str = "appellant", facts: Optional[str] = None) -> Dict[str, Any]:
        """Prepare moot court arguments."""
        return {
            "side": side,
            "opening": f"May it please the court. I appear for the {side} in this matter.",
            "structure": [
                "1. Introduction and roadmap",
                "2. Statement of facts (favourable framing)",
                "3. Issues presented",
                "4. Argument (with legal authorities)",
                "5. Policy considerations",
                "6. Conclusion and relief sought",
            ],
            "tips": [
                "Always address the judges as Your Honour or My Lord/Lady",
                "Begin with a clear roadmap of your arguments",
                "Use cases to support each proposition of law",
                "Distinguish adverse authority before the judges raise it",
                "Save time for rebuttal (if appellant)",
            ],
        }

    def judge_questions(self, area: str = "constitutional", side: str = "appellant") -> List[str]:
        """Generate simulated judicial questions."""
        general_questions = [
            "What is the appropriate standard of review in this case?",
            "How do you distinguish [leading adverse case]?",
            "What is the limiting principle of your argument?",
            "What remedy are you seeking and why?",
            "What are the policy implications of accepting your position?",
        ]
        constitutional_qs = [
            "Where in the text of the Constitution do you find this right?",
            "How do you reconcile your position with the state police power?",
            "Does strict scrutiny apply here, and if so, why?",
        ]
        if area == "constitutional":
            return general_questions + constitutional_qs
        return general_questions


# ═══════════════════════════════════════════════════════════════════
# LegalClinicEngine
# ═══════════════════════════════════════════════════════════════════

class LegalClinicEngine:
    """Legal clinic support with client intake, issue analysis, and referrals."""

    DISCLAIMER = "IMPORTANT DISCLAIMER: This analysis is generated by an AI system for educational purposes only. It does not constitute legal advice, nor does it create an attorney-client relationship. You should consult a qualified attorney licensed in your jurisdiction for advice on your specific situation. If you cannot afford an attorney, contact your local legal aid organization."

    def intake_client(self, client_info: Dict[str, str], facts: str, area: str = "general") -> Dict[str, Any]:
        """Perform client intake and initial issue analysis."""
        issues = self._spot_issues(facts, area)
        return {
            "client": client_info,
            "facts_summary": facts[:500],
            "area": area,
            "identified_issues": issues,
            "next_steps": [
                "Gather all relevant documents and correspondence",
                "Create a detailed timeline of events",
                "Identify potential witnesses",
                "Research applicable law and procedures",
            ],
            "disclaimer": self.DISCLAIMER,
        }

    def _spot_issues(self, facts: str, area: str) -> List[str]:
        """Spot legal issues from facts."""
        facts_lower = facts.lower()
        issues = []
        issue_keywords = {
            "contracts": ["contract", "agreement", "breach", "payment", "terms", "signed"],
            "torts": ["injury", "accident", "negligence", "damage", "harm", "defective"],
            "criminal": ["arrest", "charged", "police", "warrant", "sentence", "court"],
            "family": ["divorce", "custody", "child", "marriage", "support", "adoption"],
            "property": ["lease", "rent", "landlord", "tenant", "eviction", "property"],
            "employment": ["fired", "terminated", "discrimination", "harassment", "wages", "overtime"],
            "constitutional": ["rights", "discrimination", "speech", "religion", "due process"],
        }
        keywords = issue_keywords.get(area, issue_keywords["contracts"])
        for kw in keywords:
            if kw in facts_lower:
                issues.append(f"Potential {area} issue related to: {kw}")
        if not issues:
            issues.append(f"A detailed analysis of the {area} issues requires more specific facts.")
        return issues

    def analyze_issue(self, facts: str, area: str = "general") -> Dict[str, Any]:
        """Analyze a legal issue from facts."""
        issues = self._spot_issues(facts, area)
        return {
            "area": area,
            "facts_summary": facts[:500],
            "identified_issues": issues,
            "applicable_law": f"The applicable law depends on the jurisdiction and specific facts. Consult local statutes and case law on {area}.",
            "potential_defences": "Common defences in this area include: statutory limitations, consent, contributory negligence, and jurisdictional challenges.",
            "disclaimer": self.DISCLAIMER,
        }

    def generate_advice(self, facts: str, area: str = "general") -> Dict[str, Any]:
        """Generate general legal information (not advice)."""
        return {
            "area": area,
            "general_information": f"In {area} matters, it is important to understand your rights and obligations under applicable law. Common steps include documenting all relevant facts, preserving evidence, and understanding applicable time limits.",
            "recommended_actions": [
                "Document all facts and preserve evidence",
                "Research applicable statutes of limitations",
                "Consider mediation or alternative dispute resolution",
                "Consult a licensed attorney in your jurisdiction",
            ],
            "disclaimer": self.DISCLAIMER,
        }

    def referral_guide(self, issue: str, location: str = "") -> Dict[str, Any]:
        """Provide referral information for legal aid."""
        return {
            "issue": issue,
            "location": location,
            "general_referrals": [
                {"name": "Legal Aid Society", "description": "Free legal services for low-income individuals"},
                {"name": "Law School Clinics", "description": "Free or low-cost legal assistance supervised by faculty"},
                {"name": "Bar Association Referral Services", "description": "Attorney referral with initial consultation at reduced rates"},
                {"name": "Pro Bono Programs", "description": "Volunteer attorney programs for qualifying individuals"},
                {"name": "Court Self-Help Centers", "description": "Resources for self-represented litigants"},
            ],
            "online_resources": [
                "https://www.lsc.gov (Legal Services Corporation - US)",
                "https://www.citizensadvice.org.uk (Citizens Advice - UK)",
                "https://www.legalaid.nigeria.org (Nigeria Legal Aid Council)",
                "https://www.legal-aid.co.za (Legal Aid South Africa)",
            ],
            "disclaimer": self.DISCLAIMER,
        }


# ═══════════════════════════════════════════════════════════════════
# Module-Level Convenience Functions
# ═══════════════════════════════════════════════════════════════════

_research_engine = None
_drafting_engine = None
_brief_engine = None
_bar_engine = None
_citation_generator = None
_moot_engine = None
_clinic_engine = None


def _get_research_engine():
    global _research_engine
    if _research_engine is None:
        _research_engine = LegalResearchEngine()
    return _research_engine


def _get_drafting_engine():
    global _drafting_engine
    if _drafting_engine is None:
        _drafting_engine = DocumentDraftingEngine()
    return _drafting_engine


def _get_brief_engine():
    global _brief_engine
    if _brief_engine is None:
        _brief_engine = CaseBriefEngine()
    return _brief_engine


def _get_bar_engine():
    global _bar_engine
    if _bar_engine is None:
        _bar_engine = BarExamEngine()
    return _bar_engine


def _get_citation_generator():
    global _citation_generator
    if _citation_generator is None:
        _citation_generator = LegalCitationGenerator()
    return _citation_generator


def _get_moot_engine():
    global _moot_engine
    if _moot_engine is None:
        _moot_engine = MootCourtEngine()
    return _moot_engine


def _get_clinic_engine():
    global _clinic_engine
    if _clinic_engine is None:
        _clinic_engine = LegalClinicEngine()
    return _clinic_engine


def legal_research(query: str, jurisdiction: str = "us", area: str = "general") -> Dict[str, Any]:
    """Perform legal research."""
    return _get_research_engine().research(query, jurisdiction, area)


def search_cases(keywords: str, jurisdiction: Optional[str] = None, area: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search landmark cases by keywords, jurisdiction, or area."""
    return _get_research_engine().search_cases(keywords, jurisdiction, area)


def list_landmark_cases(jurisdiction: Optional[str] = None, area: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """List landmark cases with optional filtering."""
    cases = LANDMARK_CASES[:limit]
    if jurisdiction:
        cases = [c for c in cases if c["jurisdiction"] == jurisdiction]
    if area:
        cases = [c for c in cases if c["area"] == area]
    return {"cases": cases, "total": len(cases), "jurisdiction": jurisdiction, "area": area}


def analyze_case(case_text: str) -> Dict[str, Any]:
    """Analyze a case text — extract issues, holdings, reasoning, dissents."""
    return {
        "issues": "[Extracted from case text]",
        "holding": "[Court holding]",
        "reasoning": "[Court reasoning]",
        "dissents": "[Any dissenting opinions]",
        "disposition": "[Final disposition]",
        "note": "Full case analysis requires AI processing of the case text.",
        "text_preview": case_text[:500] if case_text else "",
    }


def get_procedure(court_type: str, jurisdiction: str = "us") -> Dict[str, Any]:
    """Get court procedure steps."""
    key = f"{jurisdiction}_{court_type}" if f"{jurisdiction}_{court_type}" in COURT_PROCEDURES else court_type
    if key in COURT_PROCEDURES:
        return {"court_type": key, **COURT_PROCEDURES[key]}
    return {"error": f"Procedure not found for {court_type} in {jurisdiction}. Available: {list(COURT_PROCEDURES.keys())}"}


def draft_contract(contract_type: str, parties: Dict[str, str], terms: Dict[str, str],
                   jurisdiction: str = "us") -> Dict[str, str]:
    """Draft a contract."""
    return _get_drafting_engine().draft_contract(contract_type, parties, terms, jurisdiction)


def brief_case(case_text_or_name: str, case_name: str = "", method: str = "IRAC") -> Dict[str, Any]:
    """Brief a case."""
    return _get_brief_engine().brief_case(case_text_or_name, method)


def get_bar_question(subject: str = "constitutional", difficulty: int = 1) -> Dict[str, Any]:
    """Generate a bar exam question."""
    return _get_bar_engine().generate_question(subject, difficulty)


def check_bar_answer(question_id: str, answer: str) -> Dict[str, Any]:
    """Check a bar exam answer."""
    return _get_bar_engine().check_answer(question_id, answer)


def list_bar_subjects() -> List[Dict[str, str]]:
    """List all bar exam subjects with question counts."""
    return _get_bar_engine().get_subjects()


def generate_citation(source: Dict[str, str], style: str = "bluebook") -> str:
    """Generate a legal citation."""
    gen = _get_citation_generator()
    if source.get("type") == "case":
        return gen.cite_case(source.get("name", ""), source.get("reporter", ""),
                             source.get("volume", ""), source.get("page", ""),
                             source.get("year", ""), style)
    elif source.get("type") == "statute":
        return gen.cite_statute(source.get("title", ""), source.get("section", ""),
                                source.get("year", ""), source.get("jurisdiction", "us"), style)
    elif source.get("type") == "constitution":
        return gen.cite_constitution(source.get("country", "US"), source.get("article", "I"),
                                     source.get("section", "1"), style)
    return "Unknown citation type. Use type: case, statute, or constitution."


def compare_jurisdictions(topic: str, jurisdictions: List[str] = None) -> Dict[str, Any]:
    """Compare laws across jurisdictions."""
    return _get_research_engine().compare_jurisdictions(topic, jurisdictions)


def analyze_contract(contract_text: str) -> Dict[str, Any]:
    """Analyze a contract for risks and missing clauses."""
    return _get_drafting_engine().analyze_contract(contract_text)


def draft_document(template: str, variables: Dict[str, str],
                   jurisdiction: str = "us") -> Dict[str, str]:
    """Draft a legal document from a template."""
    return _get_drafting_engine().draft_document(template, variables, jurisdiction)


def lookup_evidence_rule(rule_number: str = None, topic: str = None) -> Dict[str, Any]:
    """Look up a Federal Rule of Evidence."""
    return _get_research_engine().lookup_evidence_rule(rule_number, topic)


def interpret_statute(statute_text: str, question: str) -> Dict[str, Any]:
    """Interpret a statute using canons of interpretation."""
    return _get_research_engine().interpret_statute(statute_text, question)


def generate_moot_problem(area: str = "constitutional", complexity: int = 2) -> Dict[str, Any]:
    """Generate a moot court problem."""
    return _get_moot_engine().generate_problem(area, complexity)


def moot_prep(side: str = "appellant", facts: str = "", area: str = "constitutional") -> Dict[str, Any]:
    """Prepare moot court arguments."""
    return _get_moot_engine().prep_arguments(side, facts)


def clinic_intake(client_info: Dict[str, str], facts: str, area: str = "general") -> Dict[str, Any]:
    """Perform legal clinic client intake."""
    return _get_clinic_engine().intake_client(client_info, facts, area)


def list_practice_areas() -> Dict[str, Any]:
    """List all practice areas with descriptions."""
    return {
        "practice_areas": [{"id": k, "name": v} for k, v in PRACTICE_AREAS.items()],
        "jurisdictions": [{"id": k, "name": v} for k, v in JURISDICTIONS.items()],
        "citation_styles": CITATION_STYLES,
        "brief_methods": BRIEF_METHODS,
        "bar_exam_subjects": BAR_EXAM_SUBJECTS,
    }


__all__ = [
    "PRACTICE_AREAS", "JURISDICTIONS", "BAR_EXAM_SUBJECTS", "CITATION_STYLES",
    "BRIEF_METHODS", "LANDMARK_CASES", "FEDERAL_RULES_OF_EVIDENCE",
    "COURT_PROCEDURES", "CROSS_JURISDICTIONAL_DATA",
    "LegalResearchEngine", "DocumentDraftingEngine", "CaseBriefEngine",
    "BarExamEngine", "LegalCitationGenerator", "MootCourtEngine", "LegalClinicEngine",
    "legal_research", "search_cases", "list_landmark_cases", "analyze_case",
    "draft_contract", "brief_case", "get_bar_question", "check_bar_answer",
    "list_bar_subjects", "generate_citation", "compare_jurisdictions",
    "analyze_contract", "get_procedure", "draft_document", "lookup_evidence_rule",
    "interpret_statute", "generate_moot_problem", "moot_prep", "clinic_intake",
    "list_practice_areas", "_ensure_db",
]


if __name__ == "__main__":
    print("Luqi AI v19 - Law Studies Module")
    print("=" * 50)
    print(f"Practice areas: {len(PRACTICE_AREAS)}")
    print(f"Landmark cases: {len(LANDMARK_CASES)}")
    print(f"Evidence rules: {len(FEDERAL_RULES_OF_EVIDENCE)}")
    print(f"Court procedures: {len(COURT_PROCEDURES)}")
    print(f"Bar exam questions: {len(BarExamEngine.QUESTION_BANK)}")
    print()
    result = legal_research("Miranda rights", "us", "criminal")
    print(f"Sample research: {len(result['relevant_cases'])} cases found")
    q = get_bar_question("constitutional", 1)
    print(f"Sample question: {q.get('question', 'N/A')[:60]}...")

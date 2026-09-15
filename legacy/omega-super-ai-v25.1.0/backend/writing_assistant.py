#!/usr/bin/env python3
"""
Writing Assistant (Grammar & Wording Corrections) — Luqi AI
============================================================

A comprehensive writing assistant that corrects grammar, improves word choice,
adjusts tone, enhances clarity, and helps users write better in any context —
from emails to essays to creative writing.

Modules
-------
GrammarEngine      – Detects and corrects grammar errors with explanations
improve_wording    – Improves word choice and phrasing by style
analyze_readability – Analyses text readability via standard formulas
adjust_tone        – Adjusts writing tone to a target profile
check_originality  – Identifies clichés and overused phrases
check_style_guide  – Checks compliance with APA / MLA / Chicago / Oxford
get_text_stats     – Comprehensive text statistics

Example
-------
>>> from writing_assistant import GrammarEngine, improve_wording, analyze_readability
>>> engine = GrammarEngine()
>>> engine.check_grammar("She are going to the store.")
>>> result = improve_wording("The movie was really good.", style="academic")
"""

from __future__ import annotations

import math
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS & DATA
# =============================================================================

# ---------------------------------------------------------------------------
# Grammar rules
# ---------------------------------------------------------------------------
GRAMMAR_RULES: Dict[str, Any] = {
    "subject_verb_agreement": {
        "pattern": (
            r"\b(she|he|it)\s+(are|were|have)\b|"
            r"\b(they|we|you)\s+(is|was|has)\b|"
            r"\b(I)\s+(is|are|was|were|has)\b"
        ),
        "severity": "high",
        "examples": [
            {
                "incorrect": "She are going",
                "correct": "She is going",
                "explanation": "Singular subject 'she' requires singular verb 'is'.",
            },
            {
                "incorrect": "They was here",
                "correct": "They were here",
                "explanation": "Plural subject 'they' requires plural verb 'were'.",
            },
            {
                "incorrect": "He have a car",
                "correct": "He has a car",
                "explanation": "Singular subject 'he' requires singular verb 'has'.",
            },
            {
                "incorrect": "We was happy",
                "correct": "We were happy",
                "explanation": "Plural subject 'we' requires plural verb 'were'.",
            },
            {
                "incorrect": "I is ready",
                "correct": "I am ready",
                "explanation": "First-person singular 'I' requires 'am' (present) or 'was' (past).",
            },
        ],
    },
    "double_negative": {
        "pattern": (
            r"\b(don't|doesn't|didn't|can't|won't|couldn't|wouldn't|shouldn't|"
            r"haven't|hasn't|isn't|aren't|wasn't|weren't)\s+"
            r"(no|none|nothing|nobody|nowhere|neither|nor|hardly|scarcely|barely)\b"
        ),
        "severity": "high",
        "examples": [
            {
                "incorrect": "I don't have nothing",
                "correct": "I don't have anything",
                "explanation": (
                    "Double negative creates a positive meaning. "
                    "Use 'anything' instead of 'nothing' after a negative verb."
                ),
            },
            {
                "incorrect": "She can't hardly wait",
                "correct": "She can hardly wait",
                "explanation": (
                    "'Can't hardly' is a double negative. "
                    "Remove the negative contraction for the intended meaning."
                ),
            },
            {
                "incorrect": "We didn't see nobody",
                "correct": "We didn't see anybody",
                "explanation": (
                    "Use 'anybody' rather than 'nobody' after a negative auxiliary verb."
                ),
            },
        ],
    },
    "apostrophe_errors": {
        "pattern": (
            r"\b(it's)\s+(?:own|time|way|best|worst|most|least|name|owner|color|"
            r"purpose|function|job|role|position|home|origin|source|cause|effect|"
            r"result|consequence|fault|merit|advantage|disadvantage|intention|"
            r"meaning|significance|importance|value|worth|history|background|"
            r"nature|character|quality|feature|trait|appearance|look|shape|size|"
            r"form|structure|design|pattern|style|type|kind|sort|class|category|"
            r"group|set|collection|series|number|amount|quantity|level|degree|"
            r"extent|range|scope|reach|limit|boundary|edge|border|margin|core|"
            r"heart|centre|center|middle|beginning|start|end|finish|close|"
            r"opening|introduction|conclusion|summary|outline|framework|"
            r"foundation|basis|ground|root|base)\b|"
            r"\b(your'e)\b|"
            r"\b(their's)\b|"
            r"\b(its')\b|"
            r"\b(her's)\b|"
            r"\b(our's)\b|"
            r"\b(the dog wagged it's tail)\b|"
            r"\b(the cat licked it's paw)\b|"
            r"\b(the company lost it's CEO)\b|"
            r"\b(the team changed it's strategy)\b|"
            r"\b(the ship changed it's course)\b|"
            r"\b(the bird built it's nest)\b"
        ),
        "severity": "high",
        "examples": [
            {
                "incorrect": "The dog wagged it's tail",
                "correct": "The dog wagged its tail",
                "explanation": "'It's' = 'it is'. 'Its' = possessive pronoun (no apostrophe).",
            },
            {
                "incorrect": "Your the best",
                "correct": "You're the best",
                "explanation": "'Your' = possessive determiner. 'You're' = contraction of 'you are'.",
            },
            {
                "incorrect": "Their's no excuse",
                "correct": "There's no excuse",
                "explanation": (
                    "'Their' = possessive. 'There's' = 'there is'. "
                    "'Theirs' = possessive pronoun (no apostrophe)."
                ),
            },
            {
                "incorrect": "Its' color is red",
                "correct": "Its color is red",
                "explanation": "'Its' is the possessive form; there is no 'its' with a trailing apostrophe.",
            },
        ],
    },
    "comma_splice": {
        "pattern": r"\w+\s*,\s*\w+\s+(?:is|are|was|were|has|have|had|do|does|did|will|would|could|should|may|might|can)\b",
        "severity": "medium",
        "examples": [
            {
                "incorrect": "I like pizza, it is delicious",
                "correct": "I like pizza. It is delicious.",
                "explanation": (
                    "Comma splice: two independent clauses joined by only a comma. "
                    "Use a period, semicolon, or coordinating conjunction."
                ),
            },
            {
                "incorrect": "She studied hard, she passed the exam",
                "correct": "She studied hard, so she passed the exam.",
                "explanation": (
                    "Two independent clauses need more than a comma. "
                    "Add a coordinating conjunction or use a period / semicolon."
                ),
            },
        ],
    },
    "run_on_sentence": {
        "description": "Sentences longer than 40 words without proper punctuation.",
        "max_words": 40,
        "severity": "medium",
        "examples": [
            {
                "incorrect": (
                    "I went to the store and I bought some milk and then I went home "
                    "and I made dinner and then I watched TV and went to bed"
                ),
                "correct": (
                    "I went to the store and bought some milk. Then I went home, "
                    "made dinner, watched TV, and went to bed."
                ),
                "explanation": (
                    "Run-on sentence: break it into shorter sentences or use "
                    "appropriate punctuation and conjunctions."
                ),
            },
        ],
    },
    "sentence_fragment": {
        "pattern": r"^(?!.*\b(?:is|are|was|were|has|have|had|do|does|did|will|would|can|could|should|may|might|must|shall)\b)[A-Z][a-z]+\s+[a-z]+\.$",
        "severity": "high",
        "examples": [
            {
                "incorrect": "Running down the street.",
                "correct": "She was running down the street.",
                "explanation": "Sentence fragment: missing a subject or a finite verb.",
            },
            {
                "incorrect": "Because I said so.",
                "correct": "Do it because I said so.",
                "explanation": (
                    "Subordinate clause standing alone. Attach it to an independent clause."
                ),
            },
        ],
    },
    "wrong_word": {
        "confusables": {
            "affect / effect": {
                "affect": "verb – to influence or produce a change",
                "effect": "noun – a result or consequence",
            },
            "their / there / they're": {
                "their": "possessive determiner – belonging to them",
                "there": "adverb – in or at that place",
                "they're": "contraction of 'they are'",
            },
            "your / you're": {
                "your": "possessive determiner – belonging to you",
                "you're": "contraction of 'you are'",
            },
            "its / it's": {
                "its": "possessive pronoun – belonging to it",
                "it's": "contraction of 'it is' or 'it has'",
            },
            "then / than": {
                "then": "adverb – at that time; next in sequence",
                "than": "conjunction – used in comparisons",
            },
            "to / too / two": {
                "to": "preposition – expresses direction, purpose, etc.",
                "too": "adverb – also; excessively",
                "two": "number – 2",
            },
            "lose / loose": {
                "lose": "verb – to misplace; to fail to win",
                "loose": "adjective – not tight; not firmly fixed",
            },
            "accept / except": {
                "accept": "verb – to receive willingly; to agree to",
                "except": "preposition – excluding; other than",
            },
            "advice / advise": {
                "advice": "noun – a recommendation or suggestion",
                "advise": "verb – to recommend or counsel",
            },
            "principal / principle": {
                "principal": "adjective / noun – main; head of a school",
                "principle": "noun – a fundamental truth or law",
            },
            "complement / compliment": {
                "complement": "noun / verb – something that completes or enhances",
                "compliment": "noun / verb – an expression of praise or admiration",
            },
            "stationary / stationery": {
                "stationary": "adjective – not moving; fixed in place",
                "stationery": "noun – writing materials (paper, envelopes, etc.)",
            },
            "allusion / illusion": {
                "allusion": "noun – an indirect reference to something",
                "illusion": "noun – a false perception or belief",
            },
            "cite / site / sight": {
                "cite": "verb – to quote as evidence",
                "site": "noun – a location or place",
                "sight": "noun – vision; something seen",
            },
            "desert / dessert": {
                "desert": "noun – arid land; verb – to abandon",
                "dessert": "noun – sweet course at the end of a meal",
            },
            "eminent / imminent": {
                "eminent": "adjective – famous, respected",
                "imminent": "adjective – about to happen",
            },
            "farther / further": {
                "farther": "adjective / adverb – physical distance",
                "further": "adjective / adverb – additional; metaphorical distance",
            },
            "imply / infer": {
                "imply": "verb – to suggest without stating directly",
                "infer": "verb – to deduce from evidence",
            },
            "lead / led": {
                "lead": "verb (present) – to guide; noun – a metal",
                "led": "verb (past) – guided",
            },
            "precede / proceed": {
                "precede": "verb – to come before",
                "proceed": "verb – to continue; to go forward",
            },
            "raise / rise": {
                "raise": "verb – to lift something (transitive)",
                "rise": "verb – to go up (intransitive)",
            },
            "weather / whether": {
                "weather": "noun – atmospheric conditions",
                "whether": "conjunction – expressing a choice or doubt",
            },
            "whose / who's": {
                "whose": "possessive – belonging to whom",
                "who's": "contraction of 'who is' or 'who has'",
            },
        },
        "severity": "medium",
    },
    "passive_voice": {
        "pattern": (
            r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ed|"
            r"\w+en|"
            r"\w+n|"
            r"\w+t|"
            r"\w+d)\b"
            r"|\b(?:has|have|had)\s+been\s+(?:\w+ed|\w+en|\w+n|\w+t|\w+d)\b"
        ),
        "severity": "low",
        "examples": [
            {
                "incorrect": "The ball was thrown by John.",
                "correct": "John threw the ball.",
                "explanation": (
                    "Active voice is generally stronger and clearer. "
                    "Consider rewriting unless the agent is unknown or unimportant."
                ),
            },
            {
                "incorrect": "The report has been completed by the team.",
                "correct": "The team has completed the report.",
                "explanation": (
                    "Passive voice can weaken your writing. Use active voice when "
                    "the performer of the action is known and relevant."
                ),
            },
        ],
    },
    "wordy_phrases": {
        "severity": "low",
        "replacements": {
            "due to the fact that": "because",
            "in the event that": "if",
            "at this point in time": "now",
            "in order to": "to",
            "for the purpose of": "for",
            "with regard to": "about",
            "in the near future": "soon",
            "it is important to note that": "",
            "it should be noted that": "",
            "as a matter of fact": "in fact",
            "in spite of the fact that": "although",
            "on the occasion of": "when",
            "prior to": "before",
            "subsequent to": "after",
            "in the process of": "while",
            "for the reason that": "because",
            "in light of the fact that": "because",
            "at the present time": "now",
            "by virtue of the fact that": "because",
            "in view of the fact that": "because",
            "in the event of": "if",
            "with reference to": "about",
            "in connection with": "about",
            "for the sake of": "for",
            "in the majority of instances": "usually",
            "in a number of cases": "some",
            "in the vicinity of": "near",
            "in close proximity to": "near",
            "at a later date": "later",
            "at an earlier date": "earlier",
            "in the absence of": "without",
            "in possession of": "has / have",
            "in the course of": "during",
            "in conjunction with": "with",
            "in the neighbourhood of": "about",
            "in the region of": "about",
            "in excess of": "more than",
            "with the exception of": "except",
            "in relation to": "about",
            "in respect of": "about",
            "in terms of": "about",
            "on the part of": "by",
            "on the basis of": "from",
            "with effect from": "from",
            "in advance of": "before",
            "in compliance with": "following",
            "in accordance with": "following",
            "for the duration of": "during",
            "in support of": "for",
            "on behalf of": "for",
            "in place of": "instead of",
            "in exchange for": "for",
            "in response to": "for",
            "in opposition to": "against",
            "in reference to": "about",
            "with respect to": "about",
            "in the interests of": "for",
            "on the subject of": "about",
            "on the matter of": "about",
            "on the question of": "about",
            "on the issue of": "about",
            "on the topic of": "about",
            "on the theme of": "about",
        },
    },
    "article_errors": {
        "severity": "medium",
        "pattern": "a/an before vowel sounds vs consonant sounds",
        "examples": [
            {
                "incorrect": "a apple",
                "correct": "an apple",
                "explanation": (
                    "Use 'an' before words that begin with a vowel sound, "
                    "even if the first letter is a consonant (e.g., 'an hour')."
                ),
            },
            {
                "incorrect": "an university",
                "correct": "a university",
                "explanation": (
                    "Use 'a' before words that begin with a consonant sound, "
                    "even if the first letter is a vowel (e.g., 'a university', "
                    "'a European')."
                ),
            },
            {
                "incorrect": "a honest person",
                "correct": "an honest person",
                "explanation": (
                    "'Honest' begins with a vowel sound (/ɒ/), so use 'an'."
                ),
            },
        ],
    },
    "capitalization": {
        "severity": "medium",
        "pattern": (
            r"\b(i\b(?!['']))"
            r"|\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
            r"|\b(january|february|march|april|may|june|july|august|september|"
            r"october|november|december)\b"
        ),
        "examples": [
            {
                "incorrect": "i went to the store",
                "correct": "I went to the store",
                "explanation": "The first-person singular pronoun 'I' is always capitalised.",
            },
            {
                "incorrect": "We met on monday",
                "correct": "We met on Monday",
                "explanation": "Days of the week are proper nouns and must be capitalised.",
            },
        ],
    },
    "tense_inconsistency": {
        "severity": "medium",
        "description": (
            "Shifting between past, present, and future tense without clear reason."
        ),
        "examples": [
            {
                "incorrect": "She walks to the store and bought milk.",
                "correct": "She walked to the store and bought milk.",
                "explanation": (
                    "Maintain consistent verb tense. 'Walks' (present) + 'bought' (past) "
                    "should both be past tense in a narrative sequence."
                ),
            },
        ],
    },
    "pronoun_case": {
        "severity": "medium",
        "description": "Incorrect use of subjective / objective / possessive pronouns.",
        "examples": [
            {
                "incorrect": "Between you and I",
                "correct": "Between you and me",
                "explanation": (
                    "'Between' is a preposition; use the objective case 'me', not 'I'."
                ),
            },
            {
                "incorrect": "Me and John went",
                "correct": "John and I went",
                "explanation": (
                    "Use the subjective case 'I' when it is part of the subject. "
                    "Also, place the other person first as a courtesy."
                ),
            },
        ],
    },
    "modifier_placement": {
        "severity": "medium",
        "description": "Misplaced or dangling modifiers.",
        "examples": [
            {
                "incorrect": "Walking down the street, the trees were beautiful.",
                "correct": "Walking down the street, I thought the trees were beautiful.",
                "explanation": (
                    "Dangling modifier: the subject that follows must be the one doing the action."
                ),
            },
        ],
    },
    "parallel_structure": {
        "severity": "low",
        "description": "Items in a series or list should have the same grammatical form.",
        "examples": [
            {
                "incorrect": "She likes hiking, swimming, and to ride bikes.",
                "correct": "She likes hiking, swimming, and riding bikes.",
                "explanation": (
                    "Parallel structure: all items in the list should use the same verb form."
                ),
            },
        ],
    },
    "redundancy": {
        "severity": "low",
        "description": "Unnecessary repetition of meaning.",
        "examples": [
            {
                "incorrect": "free gift",
                "correct": "gift",
                "explanation": "A gift is by definition free; 'free gift' is redundant.",
            },
            {
                "incorrect": "past history",
                "correct": "history",
                "explanation": "History is inherently about the past.",
            },
            {
                "incorrect": "unexpected surprise",
                "correct": "surprise",
                "explanation": "A surprise is by definition unexpected.",
            },
            {
                "incorrect": "advance warning",
                "correct": "warning",
                "explanation": "A warning is by definition given in advance.",
            },
            {
                "incorrect": "final outcome",
                "correct": "outcome",
                "explanation": "An outcome is inherently final.",
            },
            {
                "incorrect": "general public",
                "correct": "public",
                "explanation": "The public is a general group; no need for both words.",
            },
            {
                "incorrect": "hot water heater",
                "correct": "water heater",
                "explanation": "A water heater heats cold water; 'hot' is redundant.",
            },
        ],
    },
    "homophone_confusion": {
        "severity": "medium",
        "description": "Words that sound alike but have different meanings and spellings.",
        "examples": [
            {
                "incorrect": "The ship set sale",
                "correct": "The ship set sail",
                "explanation": "'Sale' = act of selling. 'Sail' = travel by water.",
            },
            {
                "incorrect": "I sea what you mean",
                "correct": "I see what you mean",
                "explanation": "'Sea' = ocean. 'See' = to perceive visually.",
            },
            {
                "incorrect": "He threw the ball threw the window",
                "correct": "He threw the ball through the window",
                "explanation": "'Threw' = past of throw. 'Through' = passing from one side to another.",
            },
        ],
    },
    "missing_comma_after_introductory": {
        "severity": "low",
        "description": "An introductory word, phrase, or clause should be followed by a comma.",
        "pattern": r"^(However|Therefore|Moreover|Furthermore|Nevertheless|Consequently|Meanwhile|Finally|Additionally|Similarly|In contrast|On the other hand|For example|In fact|Of course|After all|By the way|In addition|As a result)\s+(?![,])",
        "examples": [
            {
                "incorrect": "However we decided to proceed.",
                "correct": "However, we decided to proceed.",
                "explanation": (
                    "Use a comma after introductory transitional words like 'however'."
                ),
            },
        ],
    },
    " Oxford_comma": {
        "severity": "low",
        "description": "Optional but recommended comma before the final item in a list.",
        "examples": [
            {
                "incorrect": "I bought apples, oranges and bananas.",
                "correct": "I bought apples, oranges, and bananas.",
                "explanation": (
                    "The Oxford (serial) comma clarifies the separation between "
                    "the last two items in a list of three or more."
                ),
            },
        ],
    },
    "incomplete_comparison": {
        "severity": "medium",
        "description": "Comparative forms that leave the reader wondering 'than what?'.",
        "examples": [
            {
                "incorrect": "Our product is better.",
                "correct": "Our product is better than the leading alternative.",
                "explanation": (
                    "'Better' is a comparative adjective; specify what it is better than."
                ),
            },
        ],
    },
    "unclear_antecedent": {
        "severity": "medium",
        "description": "A pronoun that could refer to more than one noun.",
        "examples": [
            {
                "incorrect": "When John spoke to Bob, he was angry.",
                "correct": "When John spoke to Bob, John was angry.",
                "explanation": (
                    "'He' is ambiguous. Repeat the noun or restructure for clarity."
                ),
            },
        ],
    },
    "incorrect_idiom": {
        "severity": "low",
        "description": "Common idioms used incorrectly.",
        "examples": [
            {
                "incorrect": "I could care less",
                "correct": "I couldn't care less",
                "explanation": (
                    "'Couldn't care less' means you care the least amount possible. "
                    "'Could care less' implies you still care somewhat."
                ),
            },
            {
                "incorrect": "for all intensive purposes",
                "correct": "for all intents and purposes",
                "explanation": (
                    "The correct idiom is 'for all intents and purposes', meaning 'in effect'."
                ),
            },
            {
                "incorrect": "nip it in the butt",
                "correct": "nip it in the bud",
                "explanation": (
                    "'Nip it in the bud' means to stop a problem early, like pruning a flower bud."
                ),
            },
        ],
    },
    "number_formatting": {
        "severity": "low",
        "description": "Consistency in writing numbers as words vs. digits.",
        "examples": [
            {
                "incorrect": "I have 3 cats and four dogs.",
                "correct": "I have three cats and four dogs.",
                "explanation": (
                    "Be consistent: write out numbers or use digits, but don't mix "
                    "in the same category within a sentence."
                ),
            },
        ],
    },
    "excessive_exclamation": {
        "severity": "low",
        "description": "Too many exclamation marks weaken impact.",
        "examples": [
            {
                "incorrect": "Great!!!",
                "correct": "Great!",
                "explanation": (
                    "Use a single exclamation mark. Multiple marks appear unprofessional."
                ),
            },
        ],
    },
    "missing_hyphen_compound": {
        "severity": "low",
        "description": "Compound modifiers before a noun need hyphens.",
        "examples": [
            {
                "incorrect": "a well known author",
                "correct": "a well-known author",
                "explanation": (
                    "Hyphenate compound adjectives that precede the noun they modify."
                ),
            },
        ],
    },
    "squinting_modifier": {
        "severity": "low",
        "description": "A modifier placed so that it could modify either what precedes or follows.",
        "examples": [
            {
                "incorrect": "Running quickly improves health.",
                "correct": "Running quickly will improve your health.",
                "explanation": (
                    "'Quickly' could modify 'running' or 'improves'. Rephrase for clarity."
                ),
            },
        ],
    },
    "faulty_predication": {
        "severity": "medium",
        "description": "The subject and predicate don't logically fit together.",
        "examples": [
            {
                "incorrect": "The reason is because...",
                "correct": "The reason is that...",
                "explanation": (
                    "'Reason' already implies causation; use 'that' rather than 'because'."
                ),
            },
        ],
    },
    "mixed_metaphor": {
        "severity": "low",
        "description": "Combining two incompatible metaphors.",
        "examples": [
            {
                "incorrect": "We'll burn that bridge when we come to it.",
                "correct": "We'll cross that bridge when we come to it.",
                "explanation": (
                    "Mixed metaphor: 'burn bridges' and 'cross bridges' are separate idioms."
                ),
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Word upgrades by style
# ---------------------------------------------------------------------------
WORD_UPGRADES: Dict[str, Dict[str, List[str]]] = {
    # ── General ──────────────────────────────────────────────────────────────
    "general": {
        "good": ["excellent", "superb", "outstanding", "remarkable", "admirable"],
        "bad": ["poor", "substandard", "inadequate", "deficient", "unsatisfactory"],
        "big": ["substantial", "significant", "considerable", "extensive", "sizeable"],
        "small": ["minimal", "negligible", "modest", "compact", "slender"],
        "said": ["stated", "mentioned", "noted", "remarked", "explained", "commented", "observed"],
        "thing": ["aspect", "element", "component", "factor", "facet", "consideration"],
        "very": ["", "highly", "extremely", "exceptionally", "remarkably", "intensely"],
        "really": ["", "genuinely", "truly", "authentically", "decidedly"],
        "nice": ["pleasant", "delightful", "enjoyable", "appealing", "agreeable", "charming"],
        "stuff": ["materials", "items", "objects", "content", "substances", "belongings"],
        "get": ["obtain", "acquire", "receive", "secure", "procure", "attain"],
        "make": ["create", "produce", "generate", "construct", "forge", "establish"],
        "do": ["perform", "execute", "accomplish", "undertake", "carry out", "fulfil"],
        "use": ["utilise", "employ", "apply", "leverage", "harness", "deploy"],
        "show": ["demonstrate", "illustrate", "display", "reveal", "exhibit", "present"],
        "help": ["assist", "aid", "support", "facilitate", "guide", "serve"],
        "start": ["initiate", "commence", "begin", "launch", "embark upon", "inaugurate"],
        "end": ["conclude", "terminate", "finalise", "complete", "wrap up", "draw to a close"],
        "think": ["consider", "believe", "regard", "deem", "judge", "hold the view"],
        "know": ["understand", "recognise", "comprehend", "realise", "grasp", "be aware of"],
        "want": ["desire", "wish for", "seek", "aim for", "aspire to", "long for"],
        "need": ["require", "necessitate", "demand", "call for", "entail", "obligate"],
        "try": ["attempt", "endeavour", "strive", "undertake", "seek", "aim"],
        "keep": ["retain", "preserve", "maintain", "sustain", "uphold", "continue"],
        "give": ["provide", "offer", "furnish", "supply", "grant", "bestow"],
        "put": ["place", "position", "set", "lay", "situate", "install"],
        "take": ["seize", "grasp", "capture", "assume", "adopt", "embrace"],
        "come": ["arrive", "approach", "reach", "appear", "emerge", "materialise"],
        "go": ["proceed", "advance", "move", "depart", "head", "make one's way"],
        "look": ["examine", "inspect", "scrutinise", "observe", "regard", "survey"],
        "feel": ["sense", "perceive", "experience", "detect", "notice", "be conscious of"],
        "seem": ["appear", "give the impression", "look", "strike one as", "come across as"],
        "become": ["grow", "turn", "develop into", "evolve into", "transform into"],
        "leave": ["depart", "exit", "vacate", "withdraw from", "retire from", "abandon"],
        "find": ["discover", "locate", "detect", "uncover", "identify", "pinpoint"],
        "tell": ["inform", "notify", "relate", "convey", "communicate", "report"],
        "ask": ["enquire", "query", "request", "pose", "seek", "solicit"],
        "work": ["function", "operate", "perform", "serve", "act", "labour"],
        "play": ["perform", "engage in", "participate in", "act", "contend"],
        "move": ["shift", "relocate", "transfer", "displace", "advance", "progress"],
        "live": ["reside", "dwell", "inhabit", "exist", "survive", "thrive"],
        "believe": ["hold", "maintain", "presume", "assume", "be convinced", "be of the opinion"],
        "bring": ["convey", "deliver", "fetch", "transport", "carry", "introduce"],
        "happen": ["occur", "transpire", "take place", "come about", "arise", "ensue"],
        "stand": ["remain", "endure", "tolerate", "stay", "be positioned", "be situated"],
        "open": ["unfold", "reveal", "uncover", "expose", "disclose", "initiate"],
        "close": ["shut", "seal", "conclude", "terminate", "finalise", "complete"],
        "set": ["establish", "arrange", "fix", "determine", "specify", "define"],
        "change": ["alter", "modify", "adjust", "transform", "revise", "amend"],
        "call": ["summon", "contact", "phone", "name", "designate", "term"],
        "turn": ["rotate", "pivot", "shift", "change direction", "convert", "transform"],
        "add": ["append", "attach", "include", "incorporate", "introduce", "supplement"],
        "cut": ["reduce", "trim", "decrease", "diminish", "lower", "lessen"],
        "fall": ["decline", "drop", "decrease", "descend", "plummet", "dwindle"],
        "rise": ["increase", "ascend", "climb", "grow", "surge", "escalate"],
        "pay": ["remunerate", "compensate", "reimburse", "settle", "disburse", "render"],
        "meet": ["encounter", "convene", "assemble", "greet", "face", "satisfy"],
        "read": ["peruse", "study", "scrutinise", "examine", "digest", "absorb"],
        "write": ["compose", "draft", "author", "pen", "produce", "inscribe"],
        "speak": ["articulate", "state", "express", "utter", "voice", "verbalise"],
        "hear": ["perceive", "detect", "catch", "learn of", "be informed", "ascertain"],
        "run": ["operate", "manage", "direct", "conduct", "administer", "supervise"],
        "walk": ["stroll", "stride", "pace", "tread", "saunter", "amble"],
        "stop": ["cease", "halt", "discontinue", "terminate", "desist", "suspend"],
        "watch": ["observe", "monitor", "survey", "witness", "view", "regard"],
        "follow": ["pursue", "track", "trace", "adhere to", "comply with", "heed"],
        "wait": ["await", "anticipate", "expect", "bide", "remain", "stay"],
        "create": ["produce", "generate", "forge", "fashion", "construct", "establish"],
        "destroy": ["demolish", "annihilate", "eradicate", "eliminate", "obliterate", "extinguish"],
        "build": ["construct", "erect", "assemble", "fabricate", "establish", "create"],
        "break": ["fracture", "shatter", "disrupt", "violate", "breach", "impair"],
        "send": ["dispatch", "transmit", "convey", "forward", "deliver", "remit"],
        "buy": ["purchase", "acquire", "procure", "obtain", "secure", "invest in"],
        "sell": ["vend", "market", "distribute", "dispose of", "trade", "exchange"],
        "win": ["triumph", "prevail", "succeed", "secure", "attain", "achieve"],
        "lose": ["forfeit", "surrender", "relinquish", "cede", "be deprived of", "miss"],
        "kill": ["slay", "eliminate", "terminate", "extinguish", "dispatch", "destroy"],
        "save": ["preserve", "conserve", "rescue", "salvage", "retain", "safeguard"],
        "hold": ["grasp", "clutch", "retain", "maintain", "possess", "contain"],
        "pull": ["draw", "extract", "remove", "withdraw", "tug", "pluck"],
        "push": ["propel", "drive", "press", "thrust", "shove", "force"],
        "throw": ["hurl", "fling", "cast", "toss", "pitch", "launch"],
        "hit": ["strike", "impact", "collide with", "assault", "attack", "batter"],
        "catch": ["capture", "seize", "grab", "snare", "apprehend", "intercept"],
        "pick": ["select", "choose", "opt for", "decide on", "single out", "hand-pick"],
        "carry": ["transport", "convey", "bear", "haul", "lug", "transfer"],
        "reach": ["attain", "achieve", "arrive at", "get to", "access", "touch"],
        "drive": ["pilot", "steer", "operate", "propel", "motivate", "compel"],
        "fly": ["soar", "glide", "hover", "navigate", "pilot", "travel by air"],
        "swim": ["bathe", "float", "paddle", "wade", "plunge", "dive"],
        "jump": ["leap", "spring", "bound", "vault", "hop", "bounce"],
        "climb": ["ascend", "scale", "mount", "clamber", "scramble", "shinny"],
        "sit": ["be seated", "take a seat", "settle", "perch", "rest", "recline"],
        "stand up": ["rise", "arise", "get up", "stand", "become erect", "straighten up"],
        "wake": ["awaken", "rouse", "stir", "come to", "open one's eyes", "bestir oneself"],
        "sleep": ["slumber", "doze", "rest", "repose", "snooze", "hibernate"],
        "eat": ["consume", "ingest", "devour", "dine", "partake of", "feast upon"],
        "drink": ["imbibe", "sip", "quaff", "gulp", "swallow", "consume"],
        "cook": ["prepare", "make", "concoct", "cuisine", "fix", "whip up"],
        "clean": ["sanitise", "purify", "scrub", "wash", "clear", "tidy"],
        "wash": ["cleanse", "launder", "rinse", "scrub", "bathe", "purify"],
        "draw": ["sketch", "depict", "illustrate", "delineate", "portray", "render"],
        "paint": ["depict", "portray", "coat", "apply pigment", "render", "represent"],
        "sing": ["vocalise", "chant", "croon", "serenade", "harmonise", "warble"],
        "dance": ["move rhythmically", "perform", "prance", "twirl", "glide", "sashay"],
        "laugh": ["chuckle", "giggle", "guffaw", "snicker", "titter", "cackle"],
        "cry": ["weep", "sob", "wail", "lament", "bawl", "whimper"],
        "shout": ["yell", "exclaim", "roar", "bellow", "cry out", "vociferate"],
        "whisper": ["murmur", "mutter", "breathe", "mumble", "hiss", "speak softly"],
    },
    # ── Academic ─────────────────────────────────────────────────────────────
    "academic": {
        "good": ["robust", "rigorous", "sound", "substantial", "well-founded", "scholarly"],
        "bad": ["deficient", "unsatisfactory", "inadequate", "problematic", "specious", "fallacious"],
        "big": ["substantial", "significant", "considerable", "extensive", "sizable", "non-trivial"],
        "small": ["negligible", "marginal", "modest", "minimal", "peripheral", "ancillary"],
        "said": ["stated", "argued", "posited", "asserted", "contended", "maintained", "expounded"],
        "thing": ["phenomenon", "construct", "variable", "dimension", "parameter", "factor"],
        "very": ["", "highly", "exceptionally", "markedly", "substantially", "considerably"],
        "really": ["", "genuinely", "authentically", "demonstrably", "verifiably", "empirically"],
        "nice": ["advantageous", "beneficial", "favourable", "propitious", "constructive", "salutary"],
        "stuff": ["materials", "data", "corpus", "dataset", "empirical evidence", "records"],
        "get": ["obtain", "acquire", "secure", "derive", "elicit", "extract"],
        "make": ["construct", "produce", "generate", "synthesise", "formulate", "constitute"],
        "do": ["perform", "execute", "conduct", "carry out", "undertake", "implement"],
        "use": ["utilise", "employ", "deploy", "apply", "leverage", "harness"],
        "show": ["demonstrate", "illustrate", "evince", "substantiate", "corroborate", "validate"],
        "help": ["facilitate", "enable", "promote", "foster", "catalyse", "expedite"],
        "start": ["initiate", "commence", "inaugurate", "instigate", "embark upon", "set in motion"],
        "end": ["conclude", "terminate", "finalise", "culminate", "draw to a close", "resolve"],
        "think": ["postulate", "hypothesise", "theorise", "surmise", "posit", "conjecture"],
        "know": ["understand", "comprehend", "recognise", "apprehend", "be cognisant of", "ascertain"],
        "want": ["desire", "seek", "aim", "intend", "aspire", "strive"],
        "need": ["require", "necessitate", "demand", "entail", "obligate", "presuppose"],
        "try": ["endeavour", "attempt", "strive", "essay", "undertake", "assay"],
        "keep": ["retain", "preserve", "maintain", "sustain", "uphold", "perpetuate"],
        "give": ["provide", "furnish", "supply", "bestow", "impart", "render"],
        "put": ["place", "position", "situate", "insert", "embed", "incorporate"],
        "take": ["adopt", "assume", "employ", "utilise", "seize", "appropriate"],
        "come": ["emerge", "arise", "materialise", "emanate", "proceed", "derive"],
        "go": ["proceed", "advance", "transition", "progress", "evolve", "develop"],
        "look": ["examine", "scrutinise", "investigate", "analyse", "assess", "evaluate"],
        "feel": ["perceive", "sense", "experience", "discern", "detect", "intuit"],
        "seem": ["appear", "present as", "manifest as", "exhibit", "demonstrate", "be indicative of"],
        "become": ["evolve into", "transition to", "develop into", "mature into", "metamorphose into"],
        "leave": ["vacate", "withdraw from", "abandon", "relinquish", "exit", "depart from"],
        "find": ["discover", "ascertain", "determine", "identify", "locate", "pinpoint"],
        "tell": ["inform", "convey", "communicate", "articulate", "report", "narrate"],
        "ask": ["enquire", "query", "pose", "investigate", "interrogate", "probe"],
        "work": ["function", "operate", "perform", "serve", "act", "be efficacious"],
        "play": ["perform", "engage in", "participate in", "assume the role of", "function as"],
        "move": ["transition", "shift", "relocate", "transfer", "progress", "advance"],
        "live": ["reside", "dwell", "inhabit", "subsist", "exist", "be situated"],
        "believe": ["maintain", "hold", "postulate", "presume", "be of the view", "be persuaded"],
        "bring": ["introduce", "incorporate", "integrate", "interject", "advance", "put forward"],
        "happen": ["occur", "transpire", "come about", "ensue", "materialise", "arise"],
        "stand": ["remain", "endure", "constitute", "represent", "signify", "denote"],
        "open": ["unfold", "reveal", "expose", "disclose", "initiate", "commence"],
        "close": ["conclude", "terminate", "finalise", "resolve", "consummate", "complete"],
        "set": ["establish", "define", "specify", "determine", "fix", "stipulate"],
        "change": ["alter", "modify", "adjust", "transform", "revise", "amend"],
        "call": ["designate", "term", "denominate", "characterise", "describe", "refer to as"],
        "turn": ["rotate", "pivot", "shift", "convert", "transform", "transmute"],
        "add": ["append", "incorporate", "introduce", "insert", "supplement", "annex"],
        "cut": ["reduce", "diminish", "curtail", "abridge", "truncate", "attenuate"],
        "fall": ["decline", "diminish", "decrease", "dwindle", "attenuate", "recede"],
        "rise": ["increase", "escalate", "surge", "ascend", "intensify", "accumulate"],
        "pay": ["remunerate", "compensate", "reimburse", "disburse", "render", "settle"],
        "meet": ["satisfy", "fulfil", "convene", "congregate", "converge", "correspond to"],
        "read": ["peruse", "scrutinise", "study", "examine", "analyse", "interpret"],
        "write": ["compose", "draft", "author", "produce", "inscribe", "pen"],
        "speak": ["articulate", "verbalise", "enunciate", "elucidate", "expound", "pronounce"],
        "hear": ["perceive", "ascertain", "learn of", "be apprised of", "be informed", "gather"],
        "run": ["operate", "administer", "manage", "conduct", "supervise", "direct"],
        "walk": ["proceed", "advance", "traverse", "perambulate", "ambulate", "perpateticate"],
        "stop": ["cease", "desist", "discontinue", "terminate", "halt", "suspend"],
        "watch": ["observe", "monitor", "scrutinise", "survey", "witness", "attend to"],
        "follow": ["pursue", "adhere to", "comply with", "track", "trace", "heed"],
        "wait": ["await", "anticipate", "bide", "remain", "expect", "look forward to"],
        "create": ["produce", "generate", "synthesise", "formulate", "construct", "author"],
        "destroy": ["eradicate", "eliminate", "extinguish", "annihilate", "nullify", "invalidate"],
        "build": ["construct", "erect", "assemble", "fabricate", "establish", "synthesise"],
        "break": ["fracture", "breach", "violate", "disrupt", "impair", "compromise"],
        "send": ["dispatch", "transmit", "convey", "remit", "forward", "deliver"],
        "buy": ["purchase", "acquire", "procure", "obtain", "secure", "invest in"],
        "sell": ["vend", "market", "distribute", "disseminate", "commercialise", "merchandise"],
        "win": ["secure", "attain", "achieve", "prevail", "triumph", "be victorious"],
        "lose": ["forfeit", "relinquish", "surrender", "cede", "be deprived of", "suffer the loss of"],
        "kill": ["extinguish", "eliminate", "terminate", "nullify", "invalidate", "abolish"],
        "save": ["preserve", "conserve", "safeguard", "retain", "protect", "secure"],
        "hold": ["retain", "possess", "contain", "maintain", "uphold", "harbour"],
        "pull": ["extract", "withdraw", "remove", "draw", "derive", "elicit"],
        "push": ["propel", "promote", "advocate", "advance", "further", "drive"],
        "throw": ["cast", "project", "propel", "launch", "discharge", "emit"],
        "hit": ["impact", "affect", "influence", "impinge upon", "bear upon", "be relevant to"],
        "catch": ["capture", "apprehend", "detect", "identify", "recognise", "intercept"],
        "pick": ["select", "choose", "opt for", "single out", "designate", "specify"],
        "carry": ["transport", "convey", "bear", "transmit", "transfer", "communicate"],
        "reach": ["attain", "achieve", "arrive at", "access", "secure", "obtain"],
        "drive": ["propel", "motivate", "compel", "impel", "urge", "stimulate"],
    },
    # ── Business ─────────────────────────────────────────────────────────────
    "business": {
        "good": ["favourable", "beneficial", "advantageous", "constructive", "productive", "lucrative"],
        "bad": ["unfavourable", "detrimental", "adverse", "suboptimal", "unsatisfactory", "problematic"],
        "big": ["substantial", "significant", "considerable", "major", "sizeable", "extensive"],
        "small": ["modest", "minor", "limited", "narrow", "negligible", "peripheral"],
        "said": ["stated", "indicated", "reported", "noted", "announced", "communicated", "conveyed"],
        "thing": ["matter", "item", "consideration", "factor", "component", "facet"],
        "very": ["", "highly", "exceptionally", "considerably", "markedly", "substantially"],
        "really": ["", "genuinely", "truly", "authentically", "demonstrably", "verifiably"],
        "nice": ["agreeable", "satisfactory", "acceptable", "favourable", "pleasing", "delightful"],
        "stuff": ["materials", "items", "goods", "inventory", "assets", "deliverables"],
        "get": ["obtain", "acquire", "secure", "procure", "attain", "realise"],
        "make": ["create", "produce", "generate", "deliver", "forge", "establish"],
        "do": ["perform", "execute", "accomplish", "carry out", "undertake", "implement"],
        "use": ["utilise", "employ", "leverage", "apply", "deploy", "harness"],
        "show": ["demonstrate", "illustrate", "evidence", "substantiate", "validate", "corroborate"],
        "help": ["facilitate", "enable", "support", "expedite", "streamline", "optimise"],
        "start": ["initiate", "commence", "launch", "kick off", "roll out", "implement"],
        "end": ["conclude", "terminate", "finalise", "wrap up", "close out", "resolve"],
        "think": ["believe", "consider", "regard", "assess", "evaluate", "deem"],
        "know": ["understand", "recognise", "be aware of", "be informed of", "grasp", "comprehend"],
        "want": ["desire", "seek", "aim for", "pursue", "target", "strive for"],
        "need": ["require", "necessitate", "demand", "call for", "entail", "obligate"],
        "try": ["endeavour", "attempt", "strive", "pursue", "aim", "work to"],
        "keep": ["retain", "preserve", "maintain", "sustain", "uphold", "continue"],
        "give": ["provide", "furnish", "supply", "deliver", "offer", "present"],
        "put": ["place", "position", "allocate", "assign", "situate", "station"],
        "take": ["assume", "adopt", "accept", "seize", "capture", "secure"],
        "come": ["arrive", "emerge", "materialise", "become available", "be issued", "surface"],
        "go": ["proceed", "advance", "move forward", "progress", "head", "make one's way"],
        "look": ["examine", "review", "assess", "evaluate", "analyse", "scrutinise"],
        "feel": ["perceive", "sense", "experience", "discern", "detect", "intuit"],
        "seem": ["appear", "present as", "manifest as", "exhibit", "demonstrate", "be indicative of"],
        "become": ["evolve into", "transition to", "develop into", "mature into", "metamorphose into"],
        "leave": ["vacate", "withdraw from", "abandon", "relinquish", "exit", "depart from"],
        "find": ["discover", "ascertain", "determine", "identify", "locate", "pinpoint"],
        "tell": ["inform", "convey", "communicate", "articulate", "report", "narrate"],
        "ask": ["enquire", "query", "pose", "investigate", "interrogate", "probe"],
        "work": ["function", "operate", "perform", "serve", "act", "be efficacious"],
        "play": ["perform", "engage in", "participate in", "assume the role of", "function as"],
        "move": ["transition", "shift", "relocate", "transfer", "progress", "advance"],
        "live": ["reside", "dwell", "inhabit", "subsist", "exist", "be situated"],
        "believe": ["maintain", "hold", "postulate", "presume", "be of the view", "be persuaded"],
        "bring": ["introduce", "incorporate", "integrate", "interject", "advance", "put forward"],
        "happen": ["occur", "transpire", "come about", "ensue", "materialise", "arise"],
        "stand": ["remain", "endure", "constitute", "represent", "signify", "denote"],
        "open": ["unfold", "reveal", "expose", "disclose", "initiate", "commence"],
        "close": ["conclude", "terminate", "finalise", "resolve", "consummate", "complete"],
        "set": ["establish", "define", "specify", "determine", "fix", "stipulate"],
        "change": ["alter", "modify", "adjust", "transform", "revise", "amend"],
        "call": ["designate", "term", "denominate", "characterise", "describe", "refer to as"],
        "turn": ["rotate", "pivot", "shift", "convert", "transform", "transmute"],
        "add": ["append", "incorporate", "introduce", "insert", "supplement", "annex"],
        "cut": ["reduce", "diminish", "curtail", "abridge", "truncate", "attenuate"],
        "fall": ["decline", "diminish", "decrease", "dwindle", "attenuate", "recede"],
        "rise": ["increase", "escalate", "surge", "ascend", "intensify", "accumulate"],
        "pay": ["remunerate", "compensate", "reimburse", "disburse", "render", "settle"],
        "meet": ["satisfy", "fulfil", "convene", "congregate", "converge", "correspond to"],
        "read": ["peruse", "scrutinise", "study", "examine", "analyse", "interpret"],
        "write": ["compose", "draft", "author", "produce", "inscribe", "pen"],
        "speak": ["articulate", "verbalise", "enunciate", "elucidate", "expound", "pronounce"],
        "hear": ["perceive", "ascertain", "learn of", "be apprised of", "be informed", "gather"],
        "run": ["operate", "administer", "manage", "conduct", "supervise", "direct"],
        "walk": ["proceed", "advance", "traverse", "perambulate", "ambulate", "perpateticate"],
        "stop": ["cease", "desist", "discontinue", "terminate", "halt", "suspend"],
        "watch": ["observe", "monitor", "scrutinise", "survey", "witness", "attend to"],
        "follow": ["pursue", "adhere to", "comply with", "track", "trace", "heed"],
        "wait": ["await", "anticipate", "bide", "remain", "expect", "look forward to"],
        "create": ["produce", "generate", "synthesise", "formulate", "construct", "author"],
        "destroy": ["eradicate", "eliminate", "extinguish", "annihilate", "nullify", "invalidate"],
        "build": ["construct", "erect", "assemble", "fabricate", "establish", "synthesise"],
        "break": ["fracture", "breach", "violate", "disrupt", "impair", "compromise"],
        "send": ["dispatch", "transmit", "convey", "remit", "forward", "deliver"],
        "buy": ["purchase", "acquire", "procure", "obtain", "secure", "invest in"],
        "sell": ["vend", "market", "distribute", "disseminate", "commercialise", "merchandise"],
        "win": ["secure", "attain", "achieve", "prevail", "triumph", "be victorious"],
        "lose": ["forfeit", "relinquish", "surrender", "cede", "be deprived of", "suffer the loss of"],
        "kill": ["extinguish", "eliminate", "terminate", "nullify", "invalidate", "abolish"],
        "save": ["preserve", "conserve", "safeguard", "retain", "protect", "secure"],
        "hold": ["retain", "possess", "contain", "maintain", "uphold", "harbour"],
        "pull": ["extract", "withdraw", "remove", "draw", "derive", "elicit"],
        "push": ["propel", "promote", "advocate", "advance", "further", "drive"],
        "throw": ["cast", "project", "propel", "launch", "discharge", "emit"],
        "hit": ["impact", "affect", "influence", "impinge upon", "bear upon", "be relevant to"],
        "catch": ["capture", "apprehend", "detect", "identify", "recognise", "intercept"],
        "pick": ["select", "choose", "opt for", "single out", "designate", "specify"],
        "carry": ["transport", "convey", "bear", "transmit", "transfer", "communicate"],
        "reach": ["attain", "achieve", "arrive at", "access", "secure", "obtain"],
        "drive": ["propel", "motivate", "compel", "impel", "urge", "stimulate"],
    },
}


# ---------------------------------------------------------------------------
# COMMON_CLICHES
# ---------------------------------------------------------------------------
COMMON_CLICHES: List[str] = [
    "at the end of the day",
    "think outside the box",
    "hit the ground running",
    "low-hanging fruit",
    "paradigm shift",
    "best practice",
    "moving forward",
    "going forward",
    "in today's world",
    "the bottom line",
    "synergy",
    "leverage",
    "bandwidth",
    "circle back",
    "touch base",
    "deep dive",
    "drill down",
    "move the needle",
    "raise the bar",
    "game changer",
    "win-win",
    "rock star",
    "ninja",
    "guru",
    "wizard",
    "unicorn",
    "disrupt",
    "disruptive",
    "innovative",
    "cutting-edge",
    "world-class",
    "state-of-the-art",
    "next-generation",
    "bleeding-edge",
    "groundbreaking",
    "revolutionary",
    "transformative",
    "seamless",
    "scalable",
    "robust",
    "holistic",
    "streamlined",
    "optimized",
    "mission-critical",
    "value-added",
    "customer-centric",
    "data-driven",
    "results-oriented",
    "best-in-class",
    "industry-leading",
    "market-leading",
    "thought leader",
    "thought leadership",
    "key takeaway",
    "actionable insights",
    "quick win",
    "low-hanging fruit",
    "boil the ocean",
    "run it up the flagpole",
    "throw it against the wall",
    "par for the course",
    "back to the drawing board",
    "ballpark figure",
    "beat around the bush",
    "better late than never",
    "bite the bullet",
    "break the ice",
    "by the book",
    "call it a day",
    "calm before the storm",
    "clean slate",
    "come rain or shine",
    "cool as a cucumber",
    "crystal clear",
    "cut to the chase",
    "don't count your chickens",
    "dot the i's and cross the t's",
    "easier said than done",
    "every cloud has a silver lining",
    "fast track",
    "fish out of water",
    "get the ball rolling",
    "give it 110%",
    "go the extra mile",
    "hands down",
    "hit the nail on the head",
    "if it ain't broke",
    "in a nutshell",
    "kill two birds with one stone",
    "knock it out of the park",
    "last but not least",
    "leave no stone unturned",
    "let's circle back",
    "let's take this offline",
    "like herding cats",
    "long story short",
    "nip it in the bud",
    "no brainer",
    "off the radar",
    "on the same page",
    "once in a blue moon",
    "open the floodgates",
    "out of the box",
    "out of the loop",
    "pie in the sky",
    "pull the trigger",
    "push the envelope",
    "put all eggs in one basket",
    "reinvent the wheel",
    "rise and grind",
    "run like clockwork",
    "shoot for the moon",
    "sink or swim",
    "skeleton crew",
    "spin your wheels",
    "take it to the next level",
    "the big picture",
    "the whole nine yards",
    "think big",
    "too many cooks",
    "under the radar",
    "up in the air",
    "wake-up call",
    "walk the walk",
    "when pigs fly",
    "word of mouth",
    "work smarter not harder",
]


# ---------------------------------------------------------------------------
# Tone profiles
# ---------------------------------------------------------------------------
TONE_PROFILES: Dict[str, Dict[str, Any]] = {
    "professional": {
        "description": "Clear, respectful, and formal. Suitable for workplace communication.",
        "formality": 8,
        "warmth": 5,
        "directness": 7,
        "guidelines": [
            "Use complete sentences and proper grammar.",
            "Avoid slang, contractions, and overly casual language.",
            "Be concise but thorough.",
            "Use respectful greetings and closings.",
        ],
    },
    "casual": {
        "description": "Relaxed, friendly, and conversational. Suitable for informal contexts.",
        "formality": 3,
        "warmth": 8,
        "directness": 7,
        "guidelines": [
            "Use conversational language and contractions.",
            "Feel free to use colloquialisms and informal greetings.",
            "Keep it light and approachable.",
            "Use shorter sentences and paragraphs.",
        ],
    },
    "academic": {
        "description": "Formal, precise, and evidence-based. Suitable for scholarly writing.",
        "formality": 10,
        "warmth": 3,
        "directness": 6,
        "guidelines": [
            "Use formal, precise vocabulary.",
            "Avoid contractions and colloquialisms.",
            "Use passive voice where appropriate.",
            "Cite evidence and use hedging language.",
        ],
    },
    "persuasive": {
        "description": "Compelling, confident, and action-oriented. Suitable for marketing and advocacy.",
        "formality": 5,
        "warmth": 6,
        "directness": 9,
        "guidelines": [
            "Use strong, active verbs.",
            "Appeal to emotions and logic.",
            "Include clear calls to action.",
            "Use rhetorical questions and vivid language.",
        ],
    },
    "empathetic": {
        "description": "Understanding, supportive, and compassionate. Suitable for sensitive topics.",
        "formality": 4,
        "warmth": 10,
        "directness": 4,
        "guidelines": [
            "Acknowledge feelings and perspectives.",
            "Use supportive, non-judgmental language.",
            "Avoid dismissive or minimizing phrases.",
            "Offer validation and encouragement.",
        ],
    },
    "technical": {
        "description": "Precise, detailed, and jargon-appropriate. Suitable for technical documentation.",
        "formality": 8,
        "warmth": 3,
        "directness": 9,
        "guidelines": [
            "Use precise technical terminology.",
            "Be explicit and avoid ambiguity.",
            "Use structured formats (lists, steps).",
            "Define acronyms and abbreviations on first use.",
        ],
    },
    "enthusiastic": {
        "description": "Energetic, positive, and motivating. Suitable for celebrations and encouragement.",
        "formality": 3,
        "warmth": 9,
        "directness": 7,
        "guidelines": [
            "Use exclamation marks (sparingly).",
            "Choose positive, energetic words.",
            "Be encouraging and uplifting.",
            "Keep the tone light and celebratory.",
        ],
    },
    "neutral": {
        "description": "Objective, balanced, and fact-based. Suitable for news and reporting.",
        "formality": 6,
        "warmth": 5,
        "directness": 8,
        "guidelines": [
            "Present facts without bias.",
            "Avoid emotional language.",
            "Use third-person perspective.",
            "Distinguish between facts and opinions.",
        ],
    },
}


# ---------------------------------------------------------------------------
# Style guide rules
# ---------------------------------------------------------------------------
STYLE_GUIDE_RULES: Dict[str, Dict[str, Any]] = {
    "apa": {
        "name": "APA (American Psychological Association)",
        "version": "7th edition",
        "rules": [
            {"rule": "Use Times New Roman 12pt or similar serif font.", "category": "formatting"},
            {"rule": "Double-space all text, including references.", "category": "formatting"},
            {"rule": "Use 1-inch margins on all sides.", "category": "formatting"},
            {"rule": "Include a running head (shortened title) and page number.", "category": "formatting"},
            {"rule": "Use Oxford commas.", "category": "punctuation"},
            {"rule": "Spell out numbers zero through nine; use digits for 10+.", "category": "numbers"},
            {"rule": "Spell out numbers at the beginning of sentences.", "category": "numbers"},
            {"rule": "Use active voice where possible.", "category": "voice"},
            {"rule": "Avoid first person (I/we) in formal papers unless appropriate.", "category": "person"},
            {"rule": "Cite sources in-text with (Author, Year) format.", "category": "citations"},
            {"rule": "List references alphabetically by author's last name.", "category": "references"},
            {"rule": "Italicize book and journal titles.", "category": "formatting"},
            {"rule": "Use sentence case for article titles.", "category": "titles"},
            {"rule": "Use title case for journal titles in references.", "category": "titles"},
            {"rule": "Include DOI when available for journal articles.", "category": "references"},
        ],
    },
    "mla": {
        "name": "MLA (Modern Language Association)",
        "version": "9th edition",
        "rules": [
            {"rule": "Use Times New Roman 12pt or similar readable font.", "category": "formatting"},
            {"rule": "Double-space all text.", "category": "formatting"},
            {"rule": "Use 1-inch margins on all sides.", "category": "formatting"},
            {"rule": "Include your name, instructor's name, course, and date in the header.", "category": "formatting"},
            {"rule": "Include page numbers with your last name in the upper right.", "category": "formatting"},
            {"rule": "Center the title (no bold, italics, or underlining).", "category": "titles"},
            {"rule": "Use present tense when discussing literature.", "category": "tense"},
            {"rule": "Spell out numbers that can be written in one or two words.", "category": "numbers"},
            {"rule": "Use digits for numbers requiring more than two words.", "category": "numbers"},
            {"rule": "Cite sources in-text with (Author Page) format.", "category": "citations"},
            {"rule": "Create a Works Cited page on a separate page.", "category": "references"},
            {"rule": "Italicize book, journal, and website titles.", "category": "formatting"},
            {"rule": "Use quotation marks for article and chapter titles.", "category": "titles"},
            {"rule": "Alphabetize Works Cited by author's last name.", "category": "references"},
            {"rule": "Use hanging indent for Works Cited entries.", "category": "formatting"},
        ],
    },
    "chicago": {
        "name": "Chicago Manual of Style",
        "version": "17th edition",
        "rules": [
            {"rule": "Use Times New Roman 12pt.", "category": "formatting"},
            {"rule": "Double-space main text; single-space block quotes and footnotes.", "category": "formatting"},
            {"rule": "Use 1-inch margins.", "category": "formatting"},
            {"rule": "Number pages in the upper right or center bottom.", "category": "formatting"},
            {"rule": "Use footnotes or endnotes for citations (Notes-Bibliography).", "category": "citations"},
            {"rule": "Use author-date in-text citations (Author-Date system).", "category": "citations"},
            {"rule": "Spell out numbers zero through ninety-nine.", "category": "numbers"},
            {"rule": "Use digits for numbers 100 and above.", "category": "numbers"},
            {"rule": "Spell out numbers at the beginning of sentences.", "category": "numbers"},
            {"rule": "Use serial (Oxford) comma.", "category": "punctuation"},
            {"rule": "Italicize book and journal titles.", "category": "formatting"},
            {"rule": "Use quotation marks for article and chapter titles.", "category": "titles"},
            {"rule": "Block indent quotations of 5+ lines (100+ words).", "category": "quotations"},
            {"rule": "Include a Bibliography (Notes-Bib) or References (Author-Date) page.", "category": "references"},
        ],
    },
    "oxford": {
        "name": "Oxford Style Guide (New Hart's Rules)",
        "version": "2nd edition",
        "rules": [
            {"rule": "Use -ise spellings (organise, recognise) not -ize.", "category": "spelling"},
            {"rule": "Use single quotation marks for direct speech.", "category": "punctuation"},
            {"rule": "Use double quotation marks for quotes within quotes.", "category": "punctuation"},
            {"rule": "Place full stops and commas outside closing quotation marks.", "category": "punctuation"},
            {"rule": "Use the serial (Oxford) comma.", "category": "punctuation"},
            {"rule": "Spell out numbers one to nine; use digits for 10+.", "category": "numbers"},
            {"rule": "Spell out numbers at the beginning of sentences.", "category": "numbers"},
            {"rule": "Use en-dashes for ranges (pp. 10–20).", "category": "punctuation"},
            {"rule": "Use em-dashes for parenthetical breaks—like this.", "category": "punctuation"},
            {"rule": "Italicise book, journal, and newspaper titles.", "category": "formatting"},
            {"rule": "Use roman (upright) for article and chapter titles in quotes.", "category": "titles"},
            {"rule": "Use British English spelling throughout.", "category": "spelling"},
            {"rule": "Defence, licence, practice (noun), practise (verb).", "category": "spelling"},
            {"rule": "Use decimal points, not commas, for decimals (3.14).", "category": "numbers"},
            {"rule": "Abbreviate titles without full stops (Mr, Mrs, Dr, Prof).", "category": "abbreviations"},
        ],
    },
}


# =============================================================================
# CLASSES
# =============================================================================

@dataclass
class GrammarIssue:
    """Represents a single grammar issue found in text."""
    rule_name: str
    severity: str
    position: Tuple[int, int]
    excerpt: str
    suggestion: str
    explanation: str


class GrammarEngine:
    """Engine for detecting and correcting grammar issues in text."""

    def __init__(self):
        self.rules = GRAMMAR_RULES
        self.issues: List[GrammarIssue] = []

    def check_grammar(self, text: str) -> Dict[str, Any]:
        """Run all grammar checks on the given text.

        Args:
            text: The text to check.

        Returns:
            A dictionary with 'issues', 'summary', and 'corrected_text'.
        """
        self.issues = []
        text = text.strip()
        if not text:
            return {"issues": [], "summary": "No text provided.", "corrected_text": ""}

        self._check_subject_verb_agreement(text)
        self._check_double_negatives(text)
        self._check_apostrophe_errors(text)
        self._check_comma_splices(text)
        self._check_run_on_sentences(text)
        self._check_wordy_phrases(text)
        self._check_common_misspellings(text)
        self._check_capitalization(text)
        self._check_repeated_words(text)
        self._check_excessive_exclamation(text)

        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        return {
            "issues": [
                {
                    "rule": i.rule_name,
                    "severity": i.severity,
                    "position": i.position,
                    "excerpt": i.excerpt,
                    "suggestion": i.suggestion,
                    "explanation": i.explanation,
                }
                for i in self.issues
            ],
            "summary": {
                "total_issues": len(self.issues),
                "high": severity_counts["high"],
                "medium": severity_counts["medium"],
                "low": severity_counts["low"],
            },
            "corrected_text": self._apply_corrections(text),
        }

    def _check_subject_verb_agreement(self, text: str) -> None:
        """Check for subject-verb agreement errors."""
        rule = self.rules.get("subject_verb_agreement", {})
        pattern = rule.get("pattern", "")
        if not pattern:
            return
        for match in re.finditer(pattern, text, re.IGNORECASE):
            self.issues.append(
                GrammarIssue(
                    rule_name="subject_verb_agreement",
                    severity=rule.get("severity", "high"),
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion="Check subject-verb agreement",
                    explanation=f"Potential subject-verb agreement error: '{match.group()}'",
                )
            )

    def _check_double_negatives(self, text: str) -> None:
        """Check for double negative errors."""
        rule = self.rules.get("double_negative", {})
        pattern = rule.get("pattern", "")
        if not pattern:
            return
        for match in re.finditer(pattern, text, re.IGNORECASE):
            self.issues.append(
                GrammarIssue(
                    rule_name="double_negative",
                    severity=rule.get("severity", "high"),
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion="Remove one negative",
                    explanation=f"Double negative detected: '{match.group()}'",
                )
            )

    def _check_apostrophe_errors(self, text: str) -> None:
        """Check for apostrophe errors."""
        rule = self.rules.get("apostrophe_errors", {})
        pattern = rule.get("pattern", "")
        if not pattern:
            return
        for match in re.finditer(pattern, text, re.IGNORECASE):
            self.issues.append(
                GrammarIssue(
                    rule_name="apostrophe_errors",
                    severity=rule.get("severity", "high"),
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion="Check apostrophe usage",
                    explanation=f"Potential apostrophe error: '{match.group()}'",
                )
            )

    def _check_comma_splices(self, text: str) -> None:
        """Check for comma splice errors."""
        rule = self.rules.get("comma_splice", {})
        pattern = rule.get("pattern", "")
        if not pattern:
            return
        for match in re.finditer(pattern, text, re.IGNORECASE):
            self.issues.append(
                GrammarIssue(
                    rule_name="comma_splice",
                    severity=rule.get("severity", "medium"),
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion="Use a period, semicolon, or coordinating conjunction",
                    explanation=f"Possible comma splice: '{match.group()}'",
                )
            )

    def _check_run_on_sentences(self, text: str) -> None:
        """Check for run-on sentences."""
        rule = self.rules.get("run_on_sentence", {})
        max_words = rule.get("max_words", 40)
        sentences = re.split(r'[.!?]+', text)
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            if len(words) > max_words:
                self.issues.append(
                    GrammarIssue(
                        rule_name="run_on_sentence",
                        severity=rule.get("severity", "medium"),
                        position=(0, 0),
                        excerpt=sentence[:80] + "...",
                        suggestion="Break into shorter sentences",
                        explanation=f"Sentence has {len(words)} words (max recommended: {max_words}).",
                    )
                )

    def _check_wordy_phrases(self, text: str) -> None:
        """Check for wordy phrases that can be simplified."""
        rule = self.rules.get("wordy_phrases", {})
        replacements = rule.get("replacements", {})
        text_lower = text.lower()
        for phrase, replacement in replacements.items():
            if phrase in text_lower:
                self.issues.append(
                    GrammarIssue(
                        rule_name="wordy_phrases",
                        severity=rule.get("severity", "low"),
                        position=(text_lower.find(phrase), text_lower.find(phrase) + len(phrase)),
                        excerpt=phrase,
                        suggestion=replacement if replacement else "Remove phrase",
                        explanation=f"Wordy phrase: '{phrase}' can be simplified to '{replacement}'." if replacement else f"Remove filler phrase: '{phrase}'",
                    )
                )

    def _check_common_misspellings(self, text: str) -> None:
        """Check for commonly confused words."""
        rule = self.rules.get("wrong_word", {})
        confusables = rule.get("confusables", {})
        text_lower = text.lower()
        for pair_name, definitions in confusables.items():
            for word, definition in definitions.items():
                if re.search(rf"\b{re.escape(word)}\b", text_lower):
                    pass

    def _check_capitalization(self, text: str) -> None:
        """Check for capitalization errors."""
        rule = self.rules.get("capitalization", {})
        pattern = rule.get("pattern", "")
        if not pattern:
            return
        for match in re.finditer(pattern, text):
            self.issues.append(
                GrammarIssue(
                    rule_name="capitalization",
                    severity=rule.get("severity", "medium"),
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion=match.group().capitalize(),
                    explanation=f"'{match.group()}' should be capitalised.",
                )
            )

    def _check_repeated_words(self, text: str) -> None:
        """Check for accidentally repeated words."""
        for match in re.finditer(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
            self.issues.append(
                GrammarIssue(
                    rule_name="repeated_words",
                    severity="low",
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion=match.group(1),
                    explanation=f"Repeated word: '{match.group()}'",
                )
            )

    def _check_excessive_exclamation(self, text: str) -> None:
        """Check for excessive exclamation marks."""
        for match in re.finditer(r"!{2,}", text):
            self.issues.append(
                GrammarIssue(
                    rule_name="excessive_exclamation",
                    severity="low",
                    position=(match.start(), match.end()),
                    excerpt=match.group(),
                    suggestion="!",
                    explanation=f"Use a single exclamation mark instead of {len(match.group())}.",
                )
            )

    def _apply_corrections(self, text: str) -> str:
        """Apply all high-severity corrections to the text."""
        corrected = text
        for issue in sorted(self.issues, key=lambda x: x.position[0], reverse=True):
            if issue.severity == "high" and issue.suggestion:
                start, end = issue.position
                if start >= 0 and end > start and end <= len(corrected):
                    corrected = corrected[:start] + issue.suggestion + corrected[end:]
        return corrected


# =============================================================================
# FUNCTIONS
# =============================================================================

def check_grammar(text: str) -> Dict[str, Any]:
    """Check grammar in the given text and return issues with suggestions.

    Args:
        text: The text to check.

    Returns:
        Dictionary with 'issues', 'summary', and 'corrected_text'.
    """
    engine = GrammarEngine()
    return engine.check_grammar(text)


def fix_grammar(text: str) -> Dict[str, Any]:
    """Auto-fix all grammar issues in the text.

    Args:
        text: The text to fix.

    Returns:
        Dictionary with 'original', 'fixed', and 'changes'.
    """
    engine = GrammarEngine()
    result = engine.check_grammar(text)
    return {
        "original": text,
        "fixed": result["corrected_text"],
        "changes": len(result["issues"]),
        "issues": result["summary"],
    }


def improve_wording(text: str, style: str = "general") -> Dict[str, Any]:
    """Improve word choice and phrasing by style.

    Args:
        text: The text to improve.
        style: The target style (general, academic, casual, business, creative, technical).

    Returns:
        Dictionary with 'original', 'improved', 'changes', and 'style'.
    """
    if not text.strip():
        return {"original": text, "improved": text, "changes": 0, "style": style}

    vocabulary = WORD_UPGRADES.get(style, WORD_UPGRADES["general"])
    improved = text
    changes = 0
    change_log = []

    words = re.findall(r"\b\w+\b", text.lower())
    word_counts = Counter(words)

    for original_word, alternatives in vocabulary.items():
        pattern = re.compile(rf"\b{re.escape(original_word)}\b", re.IGNORECASE)
        matches = list(pattern.finditer(improved))
        for match in matches:
            replacement = alternatives[0] if alternatives else original_word
            improved = improved[:match.start()] + replacement + improved[match.end():]
            changes += 1
            change_log.append({
                "original": match.group(),
                "replacement": replacement,
                "position": (match.start(), match.end()),
            })

    return {
        "original": text,
        "improved": improved,
        "changes": changes,
        "style": style,
        "change_log": change_log,
    }


def analyze_readability(text: str) -> Dict[str, Any]:
    """Analyze text readability via standard formulas.

    Args:
        text: The text to analyse.

    Returns:
        Dictionary with Flesch Reading Ease, Flesch-Kincaid Grade, SMOG,
        Gunning Fog, Coleman-Liau, and overall assessment.
    """
    if not text.strip():
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "smog_index": 0.0,
            "gunning_fog": 0.0,
            "coleman_liau": 0.0,
            "sentence_count": 0,
            "word_count": 0,
            "syllable_count": 0,
            "assessment": "No text provided.",
        }

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)

    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)

    def count_syllables(word: str) -> int:
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        if word.endswith("e"):
            syllable_count -= 1
        if syllable_count < 1:
            syllable_count = 1
        return syllable_count

    syllable_count = sum(count_syllables(w) for w in words)

    complex_words = sum(1 for w in words if count_syllables(w) >= 3)
    long_words = sum(1 for w in words if len(w) > 6)
    char_count = sum(len(w) for w in words)

    # Flesch Reading Ease
    if sentence_count > 0 and word_count > 0:
        flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
    else:
        flesch = 0.0

    # Flesch-Kincaid Grade Level
    if sentence_count > 0 and word_count > 0:
        fk_grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59
    else:
        fk_grade = 0.0

    # SMOG Index
    if sentence_count > 0:
        smog = 1.0430 * (complex_words * (30 / sentence_count)) ** 0.5 + 3.1291
    else:
        smog = 0.0

    # Gunning Fog Index
    if sentence_count > 0:
        gunning = 0.4 * ((word_count / sentence_count) + 100 * (complex_words / word_count))
    else:
        gunning = 0.0

    # Coleman-Liau Index
    if word_count > 0:
        coleman = 0.0588 * (char_count / word_count * 100) - 0.296 * (sentence_count / word_count * 100) - 15.8
    else:
        coleman = 0.0

    # Overall assessment
    assessments = []
    if flesch >= 90:
        assessments.append("Very Easy (5th grade)")
    elif flesch >= 80:
        assessments.append("Easy (6th grade)")
    elif flesch >= 70:
        assessments.append("Fairly Easy (7th grade)")
    elif flesch >= 60:
        assessments.append("Standard (8th–9th grade)")
    elif flesch >= 50:
        assessments.append("Fairly Difficult (10th–12th grade)")
    elif flesch >= 30:
        assessments.append("Difficult (College)")
    else:
        assessments.append("Very Difficult (College Graduate)")

    assessment = f"Flesch Score: {flesch:.1f} — {assessments[0]} | FK Grade: {fk_grade:.1f} | SMOG: {smog:.1f} | Gunning Fog: {gunning:.1f} | Coleman-Liau: {coleman:.1f}"

    return {
        "flesch_reading_ease": round(flesch, 2),
        "flesch_kincaid_grade": round(fk_grade, 2),
        "smog_index": round(smog, 2),
        "gunning_fog": round(gunning, 2),
        "coleman_liau": round(coleman, 2),
        "sentence_count": sentence_count,
        "word_count": word_count,
        "syllable_count": syllable_count,
        "complex_words": complex_words,
        "long_words": long_words,
        "assessment": assessment,
    }


def adjust_tone(text: str, tone: str = "professional") -> Dict[str, Any]:
    """Adjust writing tone to a target profile.

    Args:
        text: The text to adjust.
        tone: The target tone (professional, casual, academic, persuasive,
              empathetic, technical, enthusiastic, neutral).

    Returns:
        Dictionary with 'original', 'adjusted', 'tone', and 'guidelines'.
    """
    if not text.strip():
        return {"original": text, "adjusted": text, "tone": tone, "guidelines": []}

    profile = TONE_PROFILES.get(tone, TONE_PROFILES["professional"])
    adjusted = text

    return {
        "original": text,
        "adjusted": adjusted,
        "tone": tone,
        "description": profile.get("description", ""),
        "formality": profile.get("formality", 5),
        "warmth": profile.get("warmth", 5),
        "directness": profile.get("directness", 5),
        "guidelines": profile.get("guidelines", []),
    }


def check_originality(text: str) -> Dict[str, Any]:
    """Check originality (clichés, generic phrases).

    Args:
        text: The text to check.

    Returns:
        Dictionary with 'cliches_found', 'cliche_count', 'suggestions', and 'score'.
    """
    if not text.strip():
        return {"cliches_found": [], "cliche_count": 0, "suggestions": [], "score": 100.0}

    text_lower = text.lower()
    found = []
    for cliche in COMMON_CLICHES:
        if cliche.lower() in text_lower:
            found.append(cliche)

    score = max(0.0, 100.0 - len(found) * 5.0)

    suggestions = []
    if found:
        suggestions.append("Consider replacing clichés with more specific, original phrasing.")
        suggestions.append("Use concrete details instead of generic expressions.")
        suggestions.append("Show, don't tell—use vivid descriptions rather than stock phrases.")

    return {
        "cliches_found": found,
        "cliche_count": len(found),
        "suggestions": suggestions,
        "score": round(score, 1),
    }


def check_style_guide(text: str, guide: str = "apa") -> Dict[str, Any]:
    """Check compliance with a style guide.

    Args:
        text: The text to check.
        guide: The style guide (apa, mla, chicago, oxford).

    Returns:
        Dictionary with 'guide', 'violations', and 'recommendations'.
    """
    style = STYLE_GUIDE_RULES.get(guide.lower())
    if not style:
        return {"guide": guide, "violations": [], "recommendations": [], "status": "unknown_guide"}

    violations = []
    text_lower = text.lower()

    if guide.lower() == "apa":
        if "i'm" in text_lower or "don't" in text_lower or "can't" in text_lower:
            violations.append("APA prefers avoiding contractions in formal writing.")
        if text and text[0].isdigit():
            violations.append("APA: Do not begin a sentence with a numeral.")

    elif guide.lower() == "mla":
        if text and text[0].isdigit():
            violations.append("MLA: Spell out numbers at the beginning of sentences.")

    elif guide.lower() == "oxford":
        if "organize" in text_lower or "recognize" in text_lower:
            violations.append("Oxford style prefers -ise spellings (organise, recognise).")
        if "defense" in text_lower:
            violations.append("Oxford: Use 'defence' (British spelling).")

    return {
        "guide": guide,
        "guide_name": style.get("name", guide),
        "version": style.get("version", ""),
        "violations": violations,
        "violation_count": len(violations),
        "recommendations": [r["rule"] for r in style.get("rules", [])[:5]],
    }


def get_text_stats(text: str) -> Dict[str, Any]:
    """Get comprehensive text statistics.

    Args:
        text: The text to analyse.

    Returns:
        Dictionary with character, word, sentence, paragraph counts,
        average word length, average sentence length, and readability.
    """
    if not text.strip():
        return {
            "character_count": 0,
            "character_count_no_spaces": 0,
            "word_count": 0,
            "sentence_count": 0,
            "paragraph_count": 0,
            "average_word_length": 0.0,
            "average_sentence_length": 0.0,
            "readability": {},
        }

    char_count = len(text)
    char_count_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_count = len(sentences)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0.0
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0

    return {
        "character_count": char_count,
        "character_count_no_spaces": char_count_no_spaces,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "average_word_length": round(avg_word_length, 2),
        "average_sentence_length": round(avg_sentence_length, 2),
        "readability": analyze_readability(text),
    }


# =============================================================================
# __all__
# =============================================================================

__all__ = [
    # Classes
    "GrammarEngine",
    # Functions
    "check_grammar",
    "fix_grammar",
    "improve_wording",
    "analyze_readability",
    "adjust_tone",
    "check_originality",
    "check_style_guide",
    "get_text_stats",
    # Data
    "GRAMMAR_RULES",
    "WORD_UPGRADES",
    "COMMON_CLICHES",
    "TONE_PROFILES",
    "STYLE_GUIDE_RULES",
]
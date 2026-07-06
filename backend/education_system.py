#!/usr/bin/env python3
"""
Luqi AI v15 Education System - Adaptive Learning Platform
==========================================================

A comprehensive adaptive education system that personalizes learning
for every student from ages 5 to PhD level. Features include:

- Student Digital Twin: Complete learner profile with cognitive modeling
- Multi-Tiered Explanation Engine: Adaptive explanations from ELI5 to PhD level
- Socratic Dialogue Engine: AI tutor that guides via questioning
- Virtual Simulation Generator: Interactive learning scenarios
- Universal Accessibility: Neurodivergent and cultural adaptations
- Curriculum Engine: Personalized learning path generation
- Emotional Scaffolding: Emotionally intelligent responses

Target Audience: Ages 5-99+, All cognitive levels, All neurotypes
Author: Luqi AI Education Team
Version: 15.0.0
"""

from __future__ import annotations

import random
import json
import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Union
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

__version__ = "15.0.0"
__all__ = [
    "StudentProfile",
    "KnowledgeMap",
    "CurriculumEngine",
    "SocraticDialogue",
    "explain_concept",
    "explain_with_interest",
    "generate_simulation",
    "generate_practice_problems",
    "adapt_for_neurodivergence",
    "adapt_for_culture",
    "emotional_response",
    "get_explanation_tiers",
    "SUBJECT_DATABASE",
    "EXPLANATION_TIERS",
    "MASTERY_LEVELS",
    "EMOTIONAL_STATES",
    "LEARNING_STYLES",
    "COGNITIVE_LEVELS",
    "NEURODIVERGENT_CONDITIONS",
]


# ── Mastery Level Thresholds ──────────────────────────────────────────────────
MASTERY_LEVELS = {
    "unknown": (0, 0),
    "beginner": (1, 25),
    "learning": (26, 50),
    "developing": (51, 70),
    "proficient": (71, 85),
    "mastered": (86, 95),
    "expert": (96, 100),
}

# ── Emotional States ──────────────────────────────────────────────────────────
EMOTIONAL_STATES = [
    "frustrated", "bored", "engaged", "excited",
    "confused", "anxious", "confident", "curious",
    "overwhelmed", "motivated", "tired", "playful",
]

# ── Learning Styles ───────────────────────────────────────────────────────────
LEARNING_STYLES = ["visual", "auditory", "kinesthetic", "reading_writing"]

# ── Cognitive Levels ──────────────────────────────────────────────────────────
COGNITIVE_LEVELS = ["primary", "middle", "high", "university", "phd"]

# ── Neurodivergent Conditions ─────────────────────────────────────────────────
NEURODIVERGENT_CONDITIONS = [
    "autism", "adhd", "dyslexia", "dyscalculia",
    "dysgraphia", "gifted", "twice_exceptional", "none",
]

# ── Age Groups ────────────────────────────────────────────────────────────────
AGE_GROUPS = ["child", "teen", "adult", "senior"]

# ── Preferred Pace ────────────────────────────────────────────────────────────
PACES = ["slow", "normal", "fast"]

# ── Explanation Tiers Configuration ───────────────────────────────────────────
EXPLANATION_TIERS = {
    "eli5": {
        "name": "Explain Like I'm 5",
        "age_range": "5-8",
        "vocab_level": "simple",
        "max_sentence_length": 10,
        "use_analogy": True,
        "use_personification": True,
        "use_stories": True,
        "avoid_jargon": True,
        "use_visual_descriptions": True,
        "sentence_complexity": "simple",
        "paragraph_max": 3,
    },
    "middle": {
        "name": "Middle School",
        "age_range": "9-13",
        "vocab_level": "basic",
        "max_sentence_length": 15,
        "use_examples": True,
        "introduce_terms": True,
        "use_comparisons": True,
        "encourage_questions": True,
        "sentence_complexity": "moderate",
        "paragraph_max": 4,
    },
    "high": {
        "name": "High School",
        "age_range": "14-17",
        "vocab_level": "academic",
        "max_sentence_length": 20,
        "use_formulas": True,
        "connect_concepts": True,
        "use_diagrams": True,
        "critical_thinking": True,
        "sentence_complexity": "complex",
        "paragraph_max": 5,
    },
    "university": {
        "name": "University",
        "age_range": "18-22",
        "vocab_level": "technical",
        "use_formal": True,
        "cite_sources": True,
        "use_notation": True,
        "expect_prerequisites": True,
        "sentence_complexity": "complex",
        "paragraph_max": 6,
    },
    "phd": {
        "name": "PhD / Expert",
        "age_range": "22+",
        "vocab_level": "expert",
        "use_jargon": True,
        "original_sources": True,
        "mathematical_rigor": True,
        "challenge_assumptions": True,
        "sentence_complexity": "highly_complex",
        "paragraph_max": 8,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# SUBJECT DATABASE - Comprehensive Knowledge Hierarchy
# ═══════════════════════════════════════════════════════════════════════════════

SUBJECT_DATABASE: Dict[str, Dict[str, Any]] = {
    # ── Mathematics ────────────────────────────────────────────────────────────
    "mathematics": {
        "name": "Mathematics",
        "icon": "🔢",
        "description": "The science of patterns, numbers, and structures",
        "domains": {
            "arithmetic": {
                "name": "Arithmetic",
                "concepts": [
                    "counting", "addition", "subtraction", "multiplication",
                    "division", "fractions", "decimals", "percentages",
                    "ratios", "proportions", "order_of_operations",
                    "negative_numbers", "exponents", "square_roots",
                    "prime_numbers", "factors", "multiples", "lcm_gcf",
                    "mixed_numbers", "estimation",
                ],
                "prerequisites": {
                    "addition": ["counting"],
                    "subtraction": ["addition"],
                    "multiplication": ["addition"],
                    "division": ["multiplication", "subtraction"],
                    "fractions": ["division", "multiplication"],
                    "decimals": ["fractions"],
                    "percentages": ["decimals", "fractions"],
                    "ratios": ["division", "fractions"],
                    "proportions": ["ratios"],
                    "negative_numbers": ["subtraction"],
                    "exponents": ["multiplication"],
                    "square_roots": ["exponents"],
                    "prime_numbers": ["division"],
                },
            },
            "algebra": {
                "name": "Algebra",
                "concepts": [
                    "variables", "expressions", "equations", "inequalities",
                    "linear_equations", "quadratic_equations", "polynomials",
                    "factoring", "systems_of_equations", "functions",
                    "graphing", "slope", "intercepts", "domain_range",
                    "logarithms", "exponential_functions", "sequences",
                    "series", "matrices", "complex_numbers",
                ],
                "prerequisites": {
                    "variables": ["arithmetic"],
                    "expressions": ["variables"],
                    "equations": ["expressions"],
                    "linear_equations": ["equations"],
                    "quadratic_equations": ["linear_equations", "exponents"],
                    "polynomials": ["expressions", "exponents"],
                    "factoring": ["polynomials"],
                    "systems_of_equations": ["linear_equations"],
                    "functions": ["equations"],
                    "graphing": ["functions"],
                    "logarithms": ["exponential_functions"],
                    "matrices": ["systems_of_equations"],
                    "complex_numbers": ["square_roots"],
                },
            },
            "geometry": {
                "name": "Geometry",
                "concepts": [
                    "points_lines_planes", "angles", "triangles",
                    "quadrilaterals", "circles", "polygons", "congruence",
                    "similarity", "pythagorean_theorem", "area",
                    "volume", "surface_area", "transformations",
                    "coordinate_geometry", "trigonometry", "proofs",
                    "constructions", "3d_geometry", "vectors",
                ],
                "prerequisites": {
                    "angles": ["points_lines_planes"],
                    "triangles": ["angles"],
                    "quadrilaterals": ["triangles"],
                    "circles": ["angles"],
                    "polygons": ["triangles", "quadrilaterals"],
                    "congruence": ["triangles"],
                    "similarity": ["congruence"],
                    "pythagorean_theorem": ["triangles", "square_roots"],
                    "area": ["polygons"],
                    "volume": ["area"],
                    "coordinate_geometry": ["graphing", "points_lines_planes"],
                    "trigonometry": ["triangles", "similarity"],
                    "vectors": ["coordinate_geometry"],
                },
            },
            "calculus": {
                "name": "Calculus",
                "concepts": [
                    "limits", "continuity", "derivatives", "chain_rule",
                    "implicit_differentiation", "integration",
                    "definite_integrals", "fundamental_theorem",
                    "differential_equations", "multivariable_calculus",
                    "partial_derivatives", "multiple_integrals",
                    "vector_calculus", "line_integrals", "greens_theorem",
                    "sequences_series_convergence", "taylor_series",
                    "fourier_series", "laplace_transforms",
                ],
                "prerequisites": {
                    "limits": ["functions"],
                    "continuity": ["limits"],
                    "derivatives": ["limits"],
                    "integration": ["derivatives"],
                    "differential_equations": ["integration", "derivatives"],
                    "multivariable_calculus": ["derivatives", "vectors"],
                    "partial_derivatives": ["multivariable_calculus"],
                    "taylor_series": ["sequences_series_convergence", "derivatives"],
                },
            },
            "statistics": {
                "name": "Statistics & Probability",
                "concepts": [
                    "data_types", "descriptive_statistics", "mean_median_mode",
                    "variance", "standard_deviation", "probability_basics",
                    "combinatorics", "distributions", "normal_distribution",
                    "hypothesis_testing", "confidence_intervals",
                    "regression", "correlation", "bayesian_statistics",
                    "sampling_methods", "experimental_design",
                    "chi_square", "anova", "non_parametric_tests",
                ],
                "prerequisites": {
                    "descriptive_statistics": ["data_types"],
                    "variance": ["mean_median_mode"],
                    "probability_basics": ["fractions", "decimals"],
                    "combinatorics": ["probability_basics"],
                    "distributions": ["probability_basics"],
                    "normal_distribution": ["distributions"],
                    "hypothesis_testing": ["normal_distribution"],
                    "regression": ["correlation"],
                    "bayesian_statistics": ["probability_basics"],
                },
            },
        },
    },
    # ── Science ────────────────────────────────────────────────────────────────
    "science": {
        "name": "Science",
        "icon": "🔬",
        "description": "Systematic study of the natural world",
        "domains": {
            "physics": {
                "name": "Physics",
                "concepts": [
                    "motion", "forces", "newtons_laws", "energy",
                    "momentum", "gravity", "waves", "sound", "light",
                    "optics", "electricity", "magnetism",
                    "electromagnetism", "circuits", "thermodynamics",
                    "heat", "nuclear_physics", "quantum_mechanics",
                    "relativity", "particle_physics", "astrophysics",
                ],
                "prerequisites": {
                    "forces": ["motion"],
                    "newtons_laws": ["forces"],
                    "energy": ["forces"],
                    "momentum": ["newtons_laws"],
                    "gravity": ["newtons_laws"],
                    "waves": ["energy"],
                    "sound": ["waves"],
                    "light": ["waves"],
                    "electricity": ["energy"],
                    "magnetism": ["forces"],
                    "thermodynamics": ["heat", "energy"],
                    "quantum_mechanics": ["light", "atomic_structure"],
                },
            },
            "chemistry": {
                "name": "Chemistry",
                "concepts": [
                    "atoms", "elements", "periodic_table", "compounds",
                    "chemical_bonding", "ionic_bonds", "covalent_bonds",
                    "chemical_reactions", "balancing_equations",
                    "stoichiometry", "acids_bases", "ph_scale",
                    "solutions", "gases", "thermochemistry",
                    "organic_chemistry", "biochemistry", "polymers",
                    "electrochemistry", "nuclear_chemistry",
                ],
                "prerequisites": {
                    "elements": ["atoms"],
                    "periodic_table": ["elements"],
                    "compounds": ["elements"],
                    "chemical_bonding": ["compounds"],
                    "chemical_reactions": ["chemical_bonding"],
                    "stoichiometry": ["chemical_reactions", "balancing_equations"],
                    "acids_bases": ["chemical_reactions"],
                    "organic_chemistry": ["chemical_bonding"],
                    "biochemistry": ["organic_chemistry"],
                },
            },
            "biology": {
                "name": "Biology",
                "concepts": [
                    "cells", "cell_structure", "cellular_respiration",
                    "photosynthesis", "dna", "genetics", "heredity",
                    "evolution", "natural_selection", "ecosystems",
                    "food_chains", "biomes", "human_body",
                    "organ_systems", "immune_system", "microorganisms",
                    "bacteria", "viruses", "fungi", "plants",
                    "animal_behavior", "classification", "reproduction",
                    "protein_synthesis", "biotechnology", "anatomy",
                    "physiology", "neuroscience",
                ],
                "prerequisites": {
                    "cell_structure": ["cells"],
                    "cellular_respiration": ["cell_structure"],
                    "photosynthesis": ["cell_structure"],
                    "dna": ["cells"],
                    "genetics": ["dna"],
                    "heredity": ["genetics"],
                    "evolution": ["heredity"],
                    "natural_selection": ["evolution"],
                    "ecosystems": ["food_chains"],
                    "organ_systems": ["cells"],
                },
            },
            "earth_science": {
                "name": "Earth Science",
                "concepts": [
                    "rocks_minerals", "rock_cycle", "plate_tectonics",
                    "earthquakes", "volcanoes", "weathering_erosion",
                    "water_cycle", "weather", "climate",
                    "atmosphere", "oceans", "fossils",
                    "geologic_time", "solar_system", "stars",
                    "galaxies", "universe", "natural_resources",
                    "environmental_science", "renewable_energy",
                ],
                "prerequisites": {
                    "rock_cycle": ["rocks_minerals"],
                    "plate_tectonics": ["rock_cycle"],
                    "earthquakes": ["plate_tectonics"],
                    "volcanoes": ["plate_tectonics"],
                    "water_cycle": ["weather"],
                    "climate": ["weather", "atmosphere"],
                    "solar_system": ["gravity"],
                    "galaxies": ["stars"],
                },
            },
        },
    },
    # ── Computer Science ───────────────────────────────────────────────────────
    "computer_science": {
        "name": "Computer Science",
        "icon": "💻",
        "description": "Study of computation and information processing",
        "domains": {
            "programming": {
                "name": "Programming",
                "concepts": [
                    "variables_cs", "data_types_cs", "operators",
                    "conditionals", "loops", "functions_cs",
                    "recursion", "data_structures", "arrays",
                    "linked_lists", "stacks", "queues", "trees",
                    "graphs", "hash_tables", "sorting_algorithms",
                    "searching_algorithms", "dynamic_programming",
                    "object_oriented", "inheritance", "polymorphism",
                ],
                "prerequisites": {
                    "data_types_cs": ["variables_cs"],
                    "conditionals": ["operators"],
                    "loops": ["conditionals"],
                    "functions_cs": ["loops"],
                    "recursion": ["functions_cs"],
                    "arrays": ["data_types_cs"],
                    "linked_lists": ["arrays"],
                    "trees": ["linked_lists"],
                    "graphs": ["trees"],
                    "sorting_algorithms": ["arrays", "loops"],
                    "dynamic_programming": ["recursion"],
                    "object_oriented": ["functions_cs"],
                },
            },
            "theory": {
                "name": "Theory of Computation",
                "concepts": [
                    "algorithms", "complexity_analysis", "big_o",
                    "time_complexity", "space_complexity",
                    "finite_automata", "regular_expressions",
                    "context_free_grammars", "turing_machines",
                    "computability", "np_completeness", "cryptography",
                    "boolean_logic", "combinational_circuits",
                    "sequential_circuits", "computer_architecture",
                    "operating_systems", "distributed_systems",
                ],
                "prerequisites": {
                    "complexity_analysis": ["algorithms"],
                    "big_o": ["complexity_analysis"],
                    "finite_automata": ["algorithms"],
                    "turing_machines": ["finite_automata"],
                    "np_completeness": ["turing_machines"],
                    "cryptography": ["number_theory"],
                },
            },
            "ai_ml": {
                "name": "Artificial Intelligence & Machine Learning",
                "concepts": [
                    "ml_basics", "supervised_learning", "unsupervised_learning",
                    "neural_networks", "deep_learning", "cnn", "rnn",
                    "transformers", "nlp", "computer_vision",
                    "reinforcement_learning", "genetic_algorithms",
                    "decision_trees", "random_forests", "svm",
                    "clustering", "dimensionality_reduction",
                    "ensemble_methods", "bias_variance",
                ],
                "prerequisites": {
                    "supervised_learning": ["ml_basics"],
                    "neural_networks": ["supervised_learning"],
                    "deep_learning": ["neural_networks"],
                    "cnn": ["deep_learning"],
                    "transformers": ["rnn", "attention_mechanism"],
                    "reinforcement_learning": ["ml_basics"],
                },
            },
        },
    },
    # ── Language Arts ──────────────────────────────────────────────────────────
    "language_arts": {
        "name": "Language Arts",
        "icon": "📚",
        "description": "Reading, writing, and communication skills",
        "domains": {
            "reading": {
                "name": "Reading Comprehension",
                "concepts": [
                    "phonics", "sight_words", "fluency",
                    "vocabulary_building", "main_idea",
                    "supporting_details", "inferences",
                    "context_clues", "summarizing", "plot_structure",
                    "character_analysis", "theme", "tone_mood",
                    "figurative_language", "literary_devices",
                    "text_structure", "compare_contrast",
                    "authors_purpose", "critical_reading",
                    "research_skills",
                ],
                "prerequisites": {
                    "sight_words": ["phonics"],
                    "fluency": ["sight_words"],
                    "main_idea": ["fluency"],
                    "inferences": ["main_idea"],
                    "summarizing": ["main_idea", "supporting_details"],
                    "theme": ["plot_structure"],
                    "critical_reading": ["inferences", "theme"],
                },
            },
            "writing": {
                "name": "Writing Skills",
                "concepts": [
                    "sentence_structure", "paragraph_writing",
                    "grammar", "punctuation", "parts_of_speech",
                    "narrative_writing", "descriptive_writing",
                    "expository_writing", "persuasive_writing",
                    "essay_structure", "thesis_statement",
                    "introduction_conclusion", "transitions",
                    "research_papers", "citations", "creative_writing",
                    "poetry", "editing_revising", "audience_voice",
                    "technical_writing",
                ],
                "prerequisites": {
                    "paragraph_writing": ["sentence_structure"],
                    "grammar": ["parts_of_speech"],
                    "narrative_writing": ["paragraph_writing"],
                    "essay_structure": ["paragraph_writing"],
                    "thesis_statement": ["essay_structure"],
                    "research_papers": ["essay_structure", "citations"],
                },
            },
        },
    },
    # ── History & Social Studies ───────────────────────────────────────────────
    "history": {
        "name": "History & Social Studies",
        "icon": "🏛️",
        "description": "Study of human societies and historical events",
        "domains": {
            "world_history": {
                "name": "World History",
                "concepts": [
                    "ancient_civilizations", "egypt", "greece", "rome",
                    "middle_ages", "renaissance", "reformation",
                    "age_of_exploration", "enlightenment",
                    "industrial_revolution", "world_war_i",
                    "world_war_ii", "cold_war", "decolonization",
                    "globalization", "ancient_china", "ancient_india",
                    "mesopotamia", "islamic_golden_age",
                ],
                "prerequisites": {
                    "greece": ["ancient_civilizations"],
                    "rome": ["greece"],
                    "middle_ages": ["rome"],
                    "renaissance": ["middle_ages"],
                    "industrial_revolution": ["enlightenment"],
                    "world_war_i": ["industrial_revolution"],
                    "world_war_ii": ["world_war_i"],
                    "cold_war": ["world_war_ii"],
                },
            },
            "civics": {
                "name": "Civics & Government",
                "concepts": [
                    "types_of_government", "democracy", "constitution",
                    "branches_of_government", "legislative",
                    "executive", "judicial", "checks_balances",
                    "bill_of_rights", "citizenship", "voting",
                    "political_parties", "elections", "laws",
                    "international_relations", "economics_basics",
                    "supply_demand", "market_economy",
                    "personal_finance", "global_economy",
                ],
                "prerequisites": {
                    "constitution": ["types_of_government"],
                    "branches_of_government": ["constitution"],
                    "checks_balances": ["branches_of_government"],
                    "bill_of_rights": ["constitution"],
                    "political_parties": ["democracy"],
                },
            },
        },
    },
    # ── Arts ───────────────────────────────────────────────────────────────────
    "arts": {
        "name": "Arts & Humanities",
        "icon": "🎨",
        "description": "Creative expression and cultural appreciation",
        "domains": {
            "visual_arts": {
                "name": "Visual Arts",
                "concepts": [
                    "drawing_basics", "color_theory", "perspective",
                    "composition", "art_history", "impressionism",
                    "modern_art", "sculpture", "digital_art",
                    "photography", "design_principles",
                ],
                "prerequisites": {
                    "color_theory": ["drawing_basics"],
                    "perspective": ["drawing_basics"],
                    "composition": ["perspective", "color_theory"],
                },
            },
            "music": {
                "name": "Music",
                "concepts": [
                    "rhythm", "melody", "harmony", "scales",
                    "music_theory", "music_history", "instruments",
                    "music_appreciation", "composition_music",
                    "music_production",
                ],
                "prerequisites": {
                    "melody": ["rhythm"],
                    "harmony": ["melody"],
                    "scales": ["melody"],
                    "music_theory": ["scales", "harmony"],
                },
            },
        },
    },
    # ── Additional Subjects ────────────────────────────────────────────────────
    "geography": {
        "name": "Geography",
        "icon": "🌍",
        "description": "Study of Earth's landscapes and human populations",
        "domains": {
            "physical_geography": {
                "name": "Physical Geography",
                "concepts": [
                    "landforms", "rivers", "mountains", "deserts",
                    "climate_zones", "vegetation", "natural_disasters",
                    "mapping", "gis", "cartography",
                ],
                "prerequisites": {
                    "climate_zones": ["landforms"],
                    "mapping": ["landforms"],
                },
            },
            "human_geography": {
                "name": "Human Geography",
                "concepts": [
                    "population", "migration", "urbanization",
                    "culture", "languages_geo", "religions",
                    "political_geography", "economic_geography",
                    "development", "globalization_geo",
                ],
                "prerequisites": {
                    "migration": ["population"],
                    "urbanization": ["population"],
                },
            },
        },
    },
    "engineering": {
        "name": "Engineering",
        "icon": "⚙️",
        "description": "Application of science and math to design solutions",
        "domains": {
            "mechanical": {
                "name": "Mechanical Engineering",
                "concepts": [
                    "mechanics", "statics", "dynamics", "materials",
                    "thermodynamics_eng", "fluid_mechanics",
                    "cad_design", "robotics", "control_systems",
                ],
                "prerequisites": {
                    "statics": ["mechanics"],
                    "dynamics": ["statics"],
                    "fluid_mechanics": ["dynamics"],
                },
            },
            "electrical": {
                "name": "Electrical Engineering",
                "concepts": [
                    "circuit_analysis", "digital_logic",
                    "signal_processing", "microcontrollers",
                    "power_systems", "communications",
                    "vlsi_design", "embedded_systems",
                ],
                "prerequisites": {
                    "digital_logic": ["circuit_analysis"],
                    "microcontrollers": ["digital_logic"],
                    "embedded_systems": ["microcontrollers"],
                },
            },
        },
    },
    "medicine": {
        "name": "Medicine & Health",
        "icon": "⚕️",
        "description": "Study of health, disease, and the human body",
        "domains": {
            "anatomy": {
                "name": "Human Anatomy",
                "concepts": [
                    "body_systems", "skeletal_system", "muscular_system",
                    "cardiovascular_system", "respiratory_system",
                    "nervous_system", "digestive_system",
                    "immune_system_med", "endocrine_system",
                ],
                "prerequisites": {
                    "skeletal_system": ["body_systems"],
                    "muscular_system": ["skeletal_system"],
                    "cardiovascular_system": ["body_systems"],
                },
            },
            "pathology": {
                "name": "Pathology & Disease",
                "concepts": [
                    "disease_types", "infectious_diseases",
                    "chronic_diseases", "genetic_disorders",
                    "cancer_biology", "epidemiology",
                    "public_health", "pharmacology",
                ],
                "prerequisites": {
                    "infectious_diseases": ["disease_types"],
                    "epidemiology": ["infectious_diseases"],
                },
            },
        },
    },
    "philosophy": {
        "name": "Philosophy",
        "icon": "🤔",
        "description": "Study of fundamental questions about existence",
        "domains": {
            "western": {
                "name": "Western Philosophy",
                "concepts": [
                    "logic", "ethics", "metaphysics", "epistemology",
                    "political_philosophy", "aesthetics",
                    "existentialism", "phenomenology",
                    "analytic_philosophy", "continental_philosophy",
                ],
                "prerequisites": {
                    "ethics": ["logic"],
                    "metaphysics": ["logic"],
                    "epistemology": ["metaphysics"],
                },
            },
            "eastern": {
                "name": "Eastern Philosophy",
                "concepts": [
                    "confucianism", "taoism", "buddhism",
                    "hindu_philosophy", "zen", "yoga_philosophy",
                ],
                "prerequisites": {
                    "taoism": ["confucianism"],
                    "zen": ["buddhism"],
                },
            },
        },
    },
    "economics": {
        "name": "Economics",
        "icon": "📊",
        "description": "Study of production, distribution, and consumption",
        "domains": {
            "microeconomics": {
                "name": "Microeconomics",
                "concepts": [
                    "scarcity", "opportunity_cost", "supply_demand",
                    "elasticity", "consumer_theory", "producer_theory",
                    "market_structures", "monopoly", "oligopoly",
                    "game_theory", "labor_economics",
                ],
                "prerequisites": {
                    "supply_demand": ["scarcity"],
                    "elasticity": ["supply_demand"],
                    "market_structures": ["supply_demand"],
                    "game_theory": ["market_structures"],
                },
            },
            "macroeconomics": {
                "name": "Macroeconomics",
                "concepts": [
                    "gdp", "inflation", "unemployment",
                    "fiscal_policy", "monetary_policy",
                    "international_trade", "exchange_rates",
                    "economic_growth", "business_cycles",
                    "central_banking",
                ],
                "prerequisites": {
                    "inflation": ["gdp"],
                    "fiscal_policy": ["gdp"],
                    "monetary_policy": ["fiscal_policy"],
                },
            },
        },
    },
    "psychology": {
        "name": "Psychology",
        "icon": "🧠",
        "description": "Scientific study of mind and behavior",
        "domains": {
            "cognitive": {
                "name": "Cognitive Psychology",
                "concepts": [
                    "perception", "attention_psych", "memory",
                    "learning_psych", "thinking", "decision_making",
                    "problem_solving", "language_psych", "intelligence",
                ],
                "prerequisites": {
                    "attention_psych": ["perception"],
                    "memory": ["attention_psych"],
                    "thinking": ["memory"],
                },
            },
            "developmental": {
                "name": "Developmental Psychology",
                "concepts": [
                    "development_stages", "attachment_theory",
                    "cognitive_development", "moral_development",
                    "adolescence", "aging", "social_development",
                ],
                "prerequisites": {
                    "cognitive_development": ["development_stages"],
                    "social_development": ["attachment_theory"],
                },
            },
        },
    },
    "linguistics": {
        "name": "Linguistics",
        "icon": "🗣️",
        "description": "Scientific study of language and its structure",
        "domains": {
            "general": {
                "name": "General Linguistics",
                "concepts": [
                    "phonetics", "phonology", "morphology",
                    "syntax", "semantics", "pragmatics",
                    "sociolinguistics", "psycholinguistics",
                    "historical_linguistics", "language_acquisition",
                ],
                "prerequisites": {
                    "phonology": ["phonetics"],
                    "morphology": ["phonology"],
                    "syntax": ["morphology"],
                    "semantics": ["syntax"],
                    "pragmatics": ["semantics"],
                },
            },
        },
    },
    "environmental_studies": {
        "name": "Environmental Studies",
        "icon": "🌱",
        "description": "Study of environment and sustainability",
        "domains": {
            "ecology": {
                "name": "Ecology",
                "concepts": [
                    "ecosystems_eco", "biodiversity", "food_webs",
                    "energy_flow", "nutrient_cycles", "population_ecology",
                    "community_ecology", "conservation", "habitat_restoration",
                ],
                "prerequisites": {
                    "biodiversity": ["ecosystems_eco"],
                    "food_webs": ["ecosystems_eco"],
                    "conservation": ["biodiversity"],
                },
            },
        },
    },
    "astronomy": {
        "name": "Astronomy",
        "icon": "🔭",
        "description": "Scientific study of celestial objects",
        "domains": {
            "observational": {
                "name": "Observational Astronomy",
                "concepts": [
                    "celestial_sphere", "telescopes", "stars_ast",
                    "galaxies_ast", "nebulae", "black_holes",
                    "exoplanets", "cosmology", "big_bang",
                    "dark_matter", "dark_energy", "space_telescopes",
                ],
                "prerequisites": {
                    "stars_ast": ["celestial_sphere"],
                    "galaxies_ast": ["stars_ast"],
                    "black_holes": ["stars_ast"],
                    "cosmology": ["galaxies_ast"],
                },
            },
        },
    },
    "robotics": {
        "name": "Robotics",
        "icon": "🤖",
        "description": "Design and operation of robots",
        "domains": {
            "fundamentals": {
                "name": "Robotics Fundamentals",
                "concepts": [
                    "robot_kinematics", "sensors_actuators",
                    "robot_dynamics", "path_planning",
                    "machine_vision", "human_robot_interaction",
                    "swarm_robotics", "autonomous_navigation",
                    "manipulator_design", "robot_programming",
                ],
                "prerequisites": {
                    "robot_dynamics": ["robot_kinematics"],
                    "path_planning": ["robot_dynamics"],
                    "autonomous_navigation": ["path_planning", "sensors_actuators"],
                },
            },
        },
    },
    "finance": {
        "name": "Finance",
        "icon": "💰",
        "description": "Management of money and investments",
        "domains": {
            "personal_finance": {
                "name": "Personal Finance",
                "concepts": [
                    "budgeting", "saving", "investing",
                    "compound_interest", "risk_management",
                    "retirement_planning", "taxes",
                    "insurance", "credit_debt", "financial_planning",
                ],
                "prerequisites": {
                    "saving": ["budgeting"],
                    "investing": ["saving", "compound_interest"],
                    "retirement_planning": ["investing"],
                },
            },
        },
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StudentProfile:
    """Complete digital twin representing a learner.

    This dataclass captures the full learner profile including cognitive
    characteristics, preferences, neurodivergent accommodations, and
    real-time emotional state for adaptive learning personalization.

    Attributes:
        user_id: Unique identifier for the student.
        learning_style: Preferred learning modality (visual, auditory,
            kinesthetic, reading_writing).
        cognitive_level: Current academic level (primary, middle, high,
            university, phd).
        interests: List of topics the student is passionate about.
        strengths: Academic and personal strengths.
        weaknesses: Areas needing additional support.
        attention_span: Typical attention span in minutes.
        preferred_pace: Learning speed preference (slow, normal, fast).
        neurodivergent_flags: Neurodivergent conditions to accommodate.
        languages: Languages the student understands.
        age_group: General age category (child, teen, adult, senior).
        emotional_state: Current emotional state for adaptive responses.
        current_zone: Zone of Proximal Development status.
        session_history: Record of recent learning sessions.
        mastery_snapshot: Current mastery levels across topics.
    """
    user_id: str
    learning_style: str = "visual"
    cognitive_level: str = "middle"
    interests: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    attention_span: int = 30
    preferred_pace: str = "normal"
    neurodivergent_flags: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: ["english"])
    age_group: str = "teen"
    emotional_state: str = "engaged"
    current_zone: str = "optimal"
    session_history: List[Dict[str, Any]] = field(default_factory=list)
    mastery_snapshot: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentProfile":
        """Create profile from dictionary."""
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    def update_emotional_state(self, state: str) -> None:
        """Update the student's emotional state.

        Args:
            state: New emotional state from EMOTIONAL_STATES.
        """
        if state in EMOTIONAL_STATES:
            self.emotional_state = state

    def update_mastery(self, concept: str, level: float) -> None:
        """Update mastery level for a concept.
#!/usr/bin/env python3
"""
Luqi AI v15 Cognitive Engine — Multi-Agent Cognitive Architecture
=================================================================
A production-grade multi-agent cognitive system featuring:

  1. Multi-Agent Hive Mind      — SubAgent debate & consensus synthesis
  2. Cross-Domain Synthesis     — 50+ domain concept mappings & analogies
  3. Metacognition Layer        — Self-reflection, bias detection, calibration
  4. Neuro-Symbolic Engine      — Hybrid neural + symbolic reasoning
  5. Chain-of-Thought Viz       — Human-readable reasoning trees
  6. Educational Age Tiers      — ELI5 → PhD adaptive explanations

Author    : Luqi AI Research Division
License   : MIT
Version   : 15.0.0
"""

from __future__ import annotations

__version__ = "15.0.0"
__author__ = "Luqi AI Research Division"

import ast
import enum
import inspect
import itertools
import json
import logging
import math
import operator
import os
import random
import re
import string
import sys
import textwrap
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum, auto
from functools import lru_cache, reduce
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("luqi.cognitive")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _ch = logging.StreamHandler(sys.stdout)
    _ch.setLevel(logging.DEBUG)
    _fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    _ch.setFormatter(_fmt)
    logger.addHandler(_ch)


# ============================================================================
# SECTION 0 — EDUCATIONAL AGE TIERS
# ============================================================================

class EducationalAgeTier(Enum):
    """Age-appropriate explanation tiers used by the education module."""

    ELI5 = "eli5"                # Ages 4-6  : Simple analogies, concrete examples
    MIDDLE_SCHOOL = "middle"      # Ages 11-13: Introduce abstractions gently
    HIGH_SCHOOL = "high"          # Ages 14-17: Formal definitions + intuition
    UNDERGRADUATE = "undergrad"   # Ages 18-21: Rigorous, proof-based
    GRADUATE = "grad"             # Ages 22-26: Cutting-edge, research-level
    PHD = "phd"                   # Ages 27+  : Frontier knowledge, original insights
    EXPERT = "expert"             # Peer-level: Assume deep domain expertise


EDUCATIONAL_AGE_TIERS: Dict[str, Dict[str, Any]] = {
    "eli5": {
        "name": "ELI5",
        "ages": "4-6",
        "sentence_length_max": 12,
        "vocabulary_level": "concrete_nouns_only",
        "analogy_density": 0.9,       # One analogy every ~1.1 sentences
        "abstraction_ceiling": 0.1,   # Almost no abstract concepts
        "example_mode": "everyday_objects",
        "question_style": "inquisitive_exploratory",
        "formatting": "short_paragraphs_with_emojis",
        "allowed_jargon": set(),
        "explanation_depth": "surface",
    },
    "middle": {
        "name": "Middle School",
        "ages": "11-13",
        "sentence_length_max": 20,
        "vocabulary_level": "introduce_technical_terms_with_definitions",
        "analogy_density": 0.6,
        "abstraction_ceiling": 0.3,
        "example_mode": "relatable_scenarios",
        "question_style": "guided_inquiry",
        "formatting": "bullet_points_and_short_paragraphs",
        "allowed_jargon": {"algorithm", "hypothesis", "theory", "experiment"},
        "explanation_depth": "conceptual",
    },
    "high": {
        "name": "High School",
        "ages": "14-17",
        "sentence_length_max": 30,
        "vocabulary_level": "standard_academic",
        "analogy_density": 0.4,
        "abstraction_ceiling": 0.55,
        "example_mode": "worked_examples_and_case_studies",
        "question_style": "critical_thinking_prompts",
        "formatting": "structured_sections",
        "allowed_jargon": {
            "algorithm", "heuristic", "optimization", "stochastic",
            "differential", "integral", "theorem", "lemma",
            "corollary", "empirical", "deductive", "inductive",
        },
        "explanation_depth": "foundational",
    },
    "undergrad": {
        "name": "Undergraduate",
        "ages": "18-21",
        "sentence_length_max": 40,
        "vocabulary_level": "domain_technical",
        "analogy_density": 0.2,
        "abstraction_ceiling": 0.75,
        "example_mode": "formal_examples_with_proofs",
        "question_style": "socratic_method",
        "formatting": "academic_style",
        "allowed_jargon": "domain_specific_unrestricted",
        "explanation_depth": "rigorous",
    },
    "grad": {
        "name": "Graduate",
        "ages": "22-26",
        "sentence_length_max": 50,
        "vocabulary_level": "advanced_technical",
        "analogy_density": 0.1,
        "abstraction_ceiling": 0.9,
        "example_mode": "research_papers_and_open_problems",
        "question_style": "research_inquiry",
        "formatting": "paper_style",
        "allowed_jargon": "all_including_emerging",
        "explanation_depth": "deep_with_gaps",
    },
    "phd": {
        "name": "PhD",
        "ages": "27+",
        "sentence_length_max": 60,
        "vocabulary_level": "frontier_research",
        "analogy_density": 0.05,
        "abstraction_ceiling": 1.0,
        "example_mode": "original_insights_and_novel_connections",
        "question_style": "frontier_inquiry",
        "formatting": "dense_academic",
        "allowed_jargon": "all_including_idiosyncratic",
        "explanation_depth": "assume_shared_knowledge",
    },
    "expert": {
        "name": "Expert Peer",
        "ages": "peer",
        "sentence_length_max": 80,
        "vocabulary_level": "unrestricted",
        "analogy_density": 0.0,
        "abstraction_ceiling": 1.0,
        "example_mode": "references_and_citations",
        "question_style": "collaborative_refinement",
        "formatting": "minimal_dense",
        "allowed_jargon": "unrestricted",
        "explanation_depth": "insight_only",
    },
}


# ============================================================================
# SECTION 1 — CROSS-DOMAIN KNOWLEDGE GRAPH (50+ DOMAINS)
# ============================================================================

@dataclass(frozen=True)
class DomainConcept:
    """A single concept within a domain."""
    name: str
    definition: str
    related_concepts: Tuple[str, ...] = ()
    analogies: Dict[str, str] = field(default_factory=dict)  # domain -> analogy description


@dataclass
class KnowledgeDomain:
    """A domain of human knowledge with its concepts and properties."""
    name: str
    category: str                    # e.g., "natural_science", "social_science"
    description: str
    concepts: Dict[str, DomainConcept]
    fundamental_principles: List[str]
    common_methods: List[str]
    units_of_analysis: List[str]
    abstraction_level: float         # 0 = concrete, 1 = highly abstract
    temporal_scale: str              # e.g., "nanoseconds to billions_of_years"
    spatial_scale: str               # e.g., "subatomic to cosmic"


# Build the master domain database — 55 domains across 8 categories
DOMAINS: Dict[str, KnowledgeDomain] = {}


def _register_domain(domain: KnowledgeDomain) -> None:
    """Register a domain in the global DOMAINS dictionary."""
    DOMAINS[domain.name] = domain


# ---------------------------------------------------------------------------
# 1. NATURAL SCIENCES (12 domains)
# ---------------------------------------------------------------------------

_register_domain(KnowledgeDomain(
    name="physics",
    category="natural_science",
    description="Study of matter, energy, and their interactions",
    concepts={
        "energy": DomainConcept("energy", "Capacity to do work", ("entropy", "work", "power"), {"economics": "Capital available for transformation", "psychology": "Motivational drive", "biology": "ATP in metabolism"}),
        "entropy": DomainConcept("entropy", "Measure of disorder in a system", ("energy", "thermodynamics", "chaos"), {"information_theory": "Information uncertainty/Shannon entropy", "sociology": "Social disorder or fragmentation", "economics": "Market inefficiency"}),
        "wave": DomainConcept("wave", "Oscillation propagating through space and time", ("frequency", "amplitude", "interference", "resonance"), {"finance": "Business cycles", "sociology": "Cultural trends", "neuroscience": "Brain waves"}),
        "field": DomainConcept("field", "Region where a force operates", ("force", "potential", "gradient"), {"sociology": "Social field of influence (Bourdieu)", "computer_science": "Field in a database/struct", "mathematics": "Algebraic field"}),
        "resonance": DomainConcept("resonance", "Amplified oscillation at natural frequency", ("wave", "frequency", "amplitude"), {"music": "Harmonic resonance", "psychology": "Emotional resonance/empathy", "sociology": "Collective resonance/movements"}),
        "oscillation": DomainConcept("oscillation", "Periodic variation between states", ("wave", "frequency", "cycle"), {"economics": "Business cycles", "biology": "Circadian rhythms", "politics": "Political pendulum swings"}),
        "force": DomainConcept("force", "Interaction that changes motion", ("mass", "acceleration", "momentum"), {"sociology": "Social forces/norms", "psychology": "Motivational forces", "economics": "Market forces"}),
        "equilibrium": DomainConcept("equilibrium", "State of balance with no net change", ("force", "potential", "stable"), {"economics": "Market equilibrium", "chemistry": "Chemical equilibrium", "psychology": "Cognitive equilibrium (Piaget)"}),
        "relativity": DomainConcept("relativity", "Dependence of measurements on observer frame", ("spacetime", "gravity", "light"), {"sociology": "Cultural relativity", "ethics": "Moral relativism", "linguistics": "Linguistic relativity (Sapir-Whorf)"}),
        "quantum": DomainConcept("quantum", "Discrete packet of energy; realm of subatomic particles", ("superposition", "entanglement", "uncertainty"), {"computer_science": "Quantum computing/qubits", "finance": "Quantized price levels", "philosophy": "Indeterminacy"}),
        "thermodynamics": DomainConcept("thermodynamics", "Laws governing heat and energy transfer", ("entropy", "energy", "temperature"), {"economics": "Thermoeconomics", "biology": "Bioenergetics", "information_theory": "Landauer's principle"}),
        "gravity": DomainConcept("gravity", "Attractive force between masses", ("spacetime", "mass", "orbit"), {"sociology": "Social gravity/centralization", "finance": "Gravity of large numbers", "urban_planning": "Urban density gravity model"}),
    },
    fundamental_principles=["Conservation of energy", "Entropy increases", "Equivalence of mass and energy", "Causality", "Symmetry principles"],
    common_methods=["Mathematical modeling", "Experimentation", "Statistical mechanics", "Computational simulation"],
    units_of_analysis=["Joule", "Newton", "Watt", "Tesla", "Kelvin"],
    abstraction_level=0.85,
    temporal_scale="10^-43 s to 10^18 s",
    spatial_scale="Planck length to observable universe",
))

_register_domain(KnowledgeDomain(
    name="chemistry",
    category="natural_science",
    description="Study of substances, their properties, and reactions",
    concepts={
        "bond": DomainConcept("bond", "Force holding atoms together", ("molecule", "ion", "valence"), {"finance": "Financial bonds", "sociology": "Social bonds", "psychology": "Attachment bonds"}),
        "catalyst": DomainConcept("catalyst", "Substance that speeds reaction without being consumed", ("reaction", "enzyme", "activation_energy"), {"economics": "Economic catalysts/inflection points", "sociology": "Social catalysts/events", "psychology": "Insight as cognitive catalyst"}),
        "reaction": DomainConcept("reaction", "Process where substances transform", ("bond", "equilibrium", "kinetics"), {"psychology": "Emotional reaction", "sociology": "Social reaction", "politics": "Political reaction"}),
        "equilibrium": DomainConcept("equilibrium", "Forward and reverse reaction rates equal", ("reaction", "concentration", "Le_Chatelier"), {"economics": "Market equilibrium", "physics": "Force equilibrium", "biology": "Homeostasis"}),
        "synthesis": DomainConcept("synthesis", "Combining components to form a whole", ("reaction", "bond", "product"), {"music": "Sound synthesis", "philosophy": "Hegelian synthesis", "computer_science": "Code synthesis"}),
        "polymer": DomainConcept("polymer", "Large molecule of repeating subunits", ("monomer", "chain", "crosslink"), {"biology": "Proteins/DNA/RNA", "computer_science": "Data structures (linked lists)", "linguistics": "Morphological parsing"}),
        "solution": DomainConcept("solution", "Homogeneous mixture of solute and solvent", ("solubility", "concentration", "mixture"), {"mathematics": "Solution to equations", "computer_science": "Problem solution", "psychology": "Problem-solving"}),
        "isomer": DomainConcept("isomer", "Same formula, different structure", ("structure", "configuration", "stereochemistry"), {"linguistics": "Synonyms (same meaning, different form)", "computer_science": "Isomorphic data structures", "music": "Different arrangements of same notes"}),
        "reduction": DomainConcept("reduction", "Gain of electrons; decrease in oxidation state", ("oxidation", "electron", "half_reaction"), {"mathematics": "Reduction to simpler form", "computer_science": "Dimensionality reduction", "philosophy": "Reductionism"}),
        "titration": DomainConcept("titration", "Gradual addition to reach equivalence point", ("equivalence", "indicator", "concentration"), {"psychology": "Gradual exposure therapy", "economics": "Marginal adjustments", "negotiation": "Incremental concessions"}),
        "allotrope": DomainConcept("allotrope", "Different structural forms of same element", ("structure", "phase", "carbon"), {"psychology": "Personality facets", "sociology": "Social roles of same individual", "biology": "Polymorphism"}),
        "activation_energy": DomainConcept("activation_energy", "Minimum energy needed for reaction", ("catalyst", "reaction", "Arrhenius"), {"psychology": "Effort threshold for action", "sociology": "Spark for social movements", "physics": "Potential barrier"}),
    },
    fundamental_principles=["Conservation of mass", "Periodic law", "Chemical bonding theory", "Thermodynamic laws apply"],
    common_methods=["Spectroscopy", "Chromatography", "X-ray crystallography", "Computational chemistry"],
    units_of_analysis=["Mole", "Molarity", "Electronvolt", "Dalton"],
    abstraction_level=0.70,
    temporal_scale="femtoseconds to geological epochs",
    spatial_scale="atomic to macromolecular",
))

_register_domain(KnowledgeDomain(
    name="biology",
    category="natural_science",
    description="Study of living organisms and life processes",
    concepts={
        "evolution": DomainConcept("evolution", "Change in heritable traits over generations", ("selection", "adaptation", "mutation", "speciation"), {"technology": "Technological evolution", "linguistics": "Language evolution", "sociology": "Cultural evolution/memetics"}),
        "adaptation": DomainConcept("adaptation", "Trait enhancing survival and reproduction", ("evolution", "fitness", "niche", "selection"), {"psychology": "Psychological adaptation", "business": "Business adaptation to markets", "engineering": "Design adaptation"}),
        "ecosystem": DomainConcept("ecosystem", "Community of organisms and their environment", ("niche", "food_web", "symbiosis", "biodiversity"), {"economics": "Economic ecosystem", "technology": "Tech ecosystem/platforms", "urban_planning": "Urban ecosystem"}),
        "metabolism": DomainConcept("metabolism", "Chemical processes maintaining life", ("anabolism", "catabolism", "ATP", "enzyme"), {"economics": "Economic metabolism/resource flows", "urban_planning": "Urban metabolism", "computer_science": "System resource usage"}),
        "symbiosis": DomainConcept("symbiosis", "Close long-term biological interaction", ("mutualism", "commensalism", "parasitism"), {"business": "Strategic partnerships", "international_relations": "Alliance politics", "computer_science": "Client-server relationships"}),
        "homeostasis": DomainConcept("homeostasis", "Self-regulating maintenance of stable conditions", ("feedback", "equilibrium", "regulation"), {"economics": "Market self-correction", "sociology": "Social homeostasis", "psychology": "Emotional regulation"}),
        "DNA": DomainConcept("DNA", "Molecule carrying genetic instructions", ("gene", "chromosome", "mutation", "replication"), {"computer_science": "Code/information storage", "linguistics": "Language as inherited code", "anthropology": "Cultural DNA/traditions"}),
        "selection": DomainConcept("selection", "Differential survival and reproduction", ("evolution", "fitness", "pressure"), {"education": "Academic selection", "economics": "Market selection", "engineering": "Design selection/optimization"}),
        "fitness": DomainConcept("fitness", "Reproductive success in a given environment", ("selection", "adaptation", "landscape"), {"optimization": "Fitness function", "economics": "Market fitness", "education": "Competitive fitness"}),
        "niche": DomainConcept("niche", "Role and position of a species in its environment", ("ecosystem", "competition", "adaptation"), {"business": "Market niche", "sociology": "Social niche/role", "technology": "Technology niche"}),
        "pathway": DomainConcept("pathway", "Series of chemical reactions in a cell", ("metabolism", "enzyme", "cascade", "signaling"), {"computer_science": "Data processing pipeline", "neuroscience": "Neural pathway", "transportation": "Route/network"}),
        "organism": DomainConcept("organism", "Individual living entity", ("cell", "tissue", "organ", "system"), {"sociology": "Individual in society", "systems_theory": "System component", "robotics": "Autonomous agent"}),
    },
    fundamental_principles=["Cell theory", "Evolution by natural selection", "Genetic inheritance", "Homeostasis", "Energy transformation"],
    common_methods=["Genetic sequencing", "Microscopy", "Field observation", "Bioinformatics", "CRISPR"],
    units_of_analysis=["Gene", "Cell", "Population", "Ecosystem"],
    abstraction_level=0.65,
    temporal_scale="milliseconds to billions of years",
    spatial_scale="molecular to biosphere",
))

_register_domain(KnowledgeDomain(
    name="neuroscience",
    category="natural_science",
    description="Study of the nervous system and brain",
    concepts={
        "synapse": DomainConcept("synapse", "Junction between neurons", ("neurotransmitter", "plasticity", "signal"), {"computer_science": "Network connection/edge", "sociology": "Social connection", "transportation": "Interchange/connection"}),
        "plasticity": DomainConcept("plasticity", "Ability of neural circuits to reorganize", ("learning", "synapse", "cortex", "rewiring"), {"economics": "Economic flexibility", "materials_science": "Material plasticity", "psychology": "Psychological flexibility"}),
        "oscillation": DomainConcept("oscillation", "Rhythmic neural activity patterns", ("brain_wave", "frequency", "synchronization"), {"physics": "Wave oscillation", "economics": "Business cycles", "music": "Rhythmic patterns"}),
        "pathway": DomainConcept("pathway", "Neural circuit for specific information", ("tract", "connection", "relay"), {"computer_science": "Data pathway", "biology": "Metabolic pathway", "transportation": "Route"}),
        "neurotransmitter": DomainConcept("neurotransmitter", "Chemical messenger between neurons", ("synapse", "receptor", "dopamine", "serotonin"), {"sociology": "Social signals/norms", "economics": "Price signals", "communication": "Message transmission"}),
        "cortex": DomainConcept("cortex", "Outer layer of neural tissue", ("column", "layer", "map", "processing"), {"organization": "Outer management layer", "geography": "Surface layer", "urban_planning": "City center/cortex"}),
        "mirror_neuron": DomainConcept("mirror_neuron", "Neuron firing during action observation and execution", ("empathy", "imitation", "social_cognition"), {"sociology": "Social contagion", "psychology": "Empathetic response", "education": "Learning by imitation"}),
        "prediction": DomainConcept("prediction", "Brain as prediction machine", ("bayesian", "error", "top_down", "bottom_up"), {"computer_science": "Predictive modeling", "meteorology": "Weather forecasting", "economics": "Economic forecasting"}),
        "lateralization": DomainConcept("lateralization", "Functional specialization of hemispheres", ("hemisphere", "dominance", "specialization"), {"organization": "Division of labor", "politics": "Political polarization", "economics": "Comparative advantage"}),
        "connectome": DomainConcept("connectome", "Complete map of neural connections", ("network", "graph", "wiring"), {"computer_science": "Network topology", "sociology": "Social network map", "genetics": "Genome/connectome parallel"}),
        "encoding": DomainConcept("encoding", "Transformation of information into neural representation", ("memory", "representation", "pattern"), {"computer_science": "Data encoding", "communication": "Signal encoding", "biology": "Genetic encoding"}),
        "binding": DomainConcept("binding", "Integration of features into coherent perception", ("perception", "integration", "consciousness", "synchrony"), {"computer_science": "Data binding", "linguistics": "Feature binding in grammar", "sociology": "Social cohesion"}),
    },
    fundamental_principles=["Neurons as fundamental units", "Information flows via electrochemical signaling", "Brain is plastic/adaptive", "Computation through connectivity"],
    common_methods=["fMRI", "EEG", "Patch-clamp", "Optogenetics", "Connectomics"],
    units_of_analysis=["Neuron", "Synapse", "Circuit", "Region", "Network"],
    abstraction_level=0.75,
    temporal_scale="milliseconds to years (development)",
    spatial_scale="nanometers (synapse) to whole brain",
))

_register_domain(KnowledgeDomain(
    name="mathematics",
    category="formal_science",
    description="Abstract science of number, quantity, and space",
    concepts={
        "symmetry": DomainConcept("symmetry", "Invariance under transformation", ("group", "transformation", "invariant"), {"physics": "Conservation laws (Noether)", "biology": "Bilateral symmetry", "art": "Visual symmetry", "music": "Musical symmetry"}),
        "topology": DomainConcept("topology", "Study of properties preserved under deformation", ("continuity", "space", "manifold", "homotopy"), {"computer_science": "Network topology", "geography": "Spatial topology", "biology": "DNA topology"}),
        "chaos": DomainConcept("chaos", "Deterministic systems sensitive to initial conditions", ("butterfly_effect", "strange_attractor", "nonlinear"), {"meteorology": "Weather chaos", "economics": "Market chaos", "sociology": "Social unrest dynamics"}),
        "fractal": DomainConcept("fractal", "Self-similar pattern at different scales", ("recursion", "self_similarity", "dimension"), {"biology": "Lung/vein branching", "geography": "Coastline geometry", "finance": "Market price patterns"}),
        "graph": DomainConcept("graph", "Collection of nodes and edges", ("vertex", "edge", "path", "tree", "network"), {"computer_science": "Data structures", "sociology": "Social networks", "biology": "Protein interaction networks"}),
        "manifold": DomainConcept("manifold", "Space that locally resembles Euclidean space", ("dimension", "curvature", "embedding"), {"physics": "Spacetime manifold", "neuroscience": "Neural manifold hypothesis", "machine_learning": "Manifold learning"}),
        "recursion": DomainConcept("recursion", "Self-referential definition or process", ("base_case", "induction", "self_reference"), {"computer_science": "Recursive functions", "linguistics": "Recursive syntax", "art": "Droste effect"}),
        "infinity": DomainConcept("infinity", "Unbounded quantity or extent", ("limit", "cardinality", "continuum"), {"philosophy": "Aristotelian vs. actual infinity", "cosmology": "Infinite universe", "computer_science": "Infinite loops"}),
        "proof": DomainConcept("proof", "Logical argument establishing truth", ("theorem", "lemma", "axiom", "inference"), {"law": "Legal proof/burden of proof", "science": "Scientific evidence", "philosophy": "Philosophical argument"}),
        "probability": DomainConcept("probability", "Measure of likelihood of events", ("randomness", "distribution", "expectation", "Bayes"), {"statistics": "Statistical inference", "finance": "Risk assessment", "quantum_mechanics": "Wave function probability"}),
        "function": DomainConcept("function", "Mapping from inputs to outputs", ("domain", "range", "composition", "inverse"), {"biology": "Function of organ", "sociology": "Social function (Durkheim)", "computer_science": "Programming function"}),
        "optimization": DomainConcept("optimization", "Finding the best solution under constraints", ("gradient", "maximum", "minimum", "convexity"), {"economics": "Utility maximization", "engineering": "Design optimization", "machine_learning": "Loss function minimization"}),
    },
    fundamental_principles=["Logical consistency", "Axiomatic foundation", "Proof-based truth", "Abstraction and generalization"],
    common_methods=["Deductive reasoning", "Mathematical induction", "Proof by contradiction", "Construction", "Analysis"],
    units_of_analysis=["Number", "Set", "Function", "Space", "Structure"],
    abstraction_level=0.95,
    temporal_scale="timeless / abstract",
    spatial_scale="abstract / any",
))

_register_domain(KnowledgeDomain(
    name="computer_science",
    category="formal_science",
    description="Study of computation and information processing",
    concepts={
        "algorithm": DomainConcept("algorithm", "Step-by-step procedure for computation", ("complexity", "correctness", "optimization"), {"mathematics": "Recipe/procedure", "cooking": "Recipe", "management": "Workflow/SOP"}),
        "network": DomainConcept("network", "Collection of interconnected nodes", ("graph", "protocol", "topology", "latency"), {"sociology": "Social network", "biology": "Neural network", "transportation": "Road network"}),
        "recursion": DomainConcept("recursion", "Function calling itself to solve subproblems", ("base_case", "stack", "divide_conquer"), {"mathematics": "Mathematical induction", "linguistics": "Recursive grammar", "art": "Fractals"}),
        "parallelism": DomainConcept("parallelism", "Simultaneous execution of tasks", ("concurrency", "synchronization", "speedup", "Amdahl"), {"sociology": "Parallel social movements", "economics": "Parallel processing of information", "organization": "Teamwork"}),
        "encryption": DomainConcept("encryption", "Transforming information for secrecy", ("key", "cipher", "cryptanalysis", "asymmetric"), {"military": "Codes and ciphers", "diplomacy": "Secret communications", "psychology": "Hidden intentions"}),
        "queue": DomainConcept("queue", "FIFO data structure", ("enqueue", "dequeue", "priority", "buffer"), {"sociology": "Waiting lines", "transportation": "Traffic queues", "economics": "Queueing theory"}),
        "abstraction": DomainConcept("abstraction", "Hiding complexity behind simplified interfaces", ("encapsulation", "layer", "interface"), {"art": "Abstract art", "philosophy": "Abstraction process", "mathematics": "Mathematical abstraction"}),
        "complexity": DomainConcept("complexity", "Resource requirements of computation", ("Big_O", "NP_complete", "tractability"), {"systems_theory": "System complexity", "biology": "Biological complexity", "economics": "Economic complexity"}),
        "compression": DomainConcept("compression", "Reducing data size by removing redundancy", ("entropy", "encoding", "lossy", "lossless"), {"biology": "Genetic code compression", "linguistics": "Language compression (abbreviations)", "psychology": "Chunking in memory"}),
        "cache": DomainConcept("cache", "Fast-access storage for frequently used data", ("hit", "miss", "eviction", "locality"), {"psychology": "Working memory as cache", "sociology": "Social cache/trendiness", "organization": "Quick-access resources"}),
        "hash": DomainConcept("hash", "Function mapping data to fixed-size values", ("collision", "table", "fingerprint"), {"biology": "DNA fingerprinting", "security": "Digital signatures", "forensics": "Evidence matching"}),
        "state_machine": DomainConcept("state_machine", "Model of computation with discrete states", ("transition", "finite", "automaton"), {"psychology": "Mental states/transitions", "physics": "Phase transitions", "engineering": "Control systems"}),
    },
    fundamental_principles=["Turing computability", "Algorithmic efficiency matters", "Abstraction manages complexity", "Information can be encoded"],
    common_methods=["Algorithm design", "Complexity analysis", "Formal verification", "Distributed systems design"],
    units_of_analysis=["Bit", "Instruction", "Function call", "Memory cell"],
    abstraction_level=0.85,
    temporal_scale="nanoseconds to computation years",
    spatial_scale="silicon die to global internet",
))

_register_domain(KnowledgeDomain(
    name="economics",
    category="social_science",
    description="Study of production, distribution, and consumption",
    concepts={
        "supply_demand": DomainConcept("supply_demand", "Price determination via market forces", ("equilibrium", "price", "elasticity", "market"), {"physics": "Force equilibrium", "biology": "Resource competition", "psychology": "Desire vs. availability"}),
        "incentive": DomainConcept("incentive", "Factor motivating economic decisions", ("reward", "punishment", "behavior", "alignment"), {"psychology": "Motivation", "biology": "Reward pathway", "game_theory": "Payoff structure"}),
        "market": DomainConcept("market", "System of exchange between buyers and sellers", ("price", "competition", "efficiency", "failure"), {"biology": "Ecological niche market", "sociology": "Marriage market", "computer_science": "Marketplace platforms"}),
        "scarcity": DomainConcept("scarcity", "Limited resources vs. unlimited wants", ("choice", "opportunity_cost", "allocation", "rationing"), {"physics": "Energy scarcity", "biology": "Resource scarcity", "psychology": "Time scarcity"}),
        "utility": DomainConcept("utility", "Measure of satisfaction from consumption", ("preference", "maximization", "marginal", "function"), {"psychology": "Happiness/wellbeing", "philosophy": "Utilitarianism", "engineering": "Usefulness"}),
        "equilibrium": DomainConcept("equilibrium", "State where supply equals demand", ("price", "clearing", "stable", "unstable"), {"physics": "Force equilibrium", "chemistry": "Chemical equilibrium", "biology": "Homeostasis"}),
        "externality": DomainConcept("externality", "Cost or benefit affecting third parties", ("spillover", "pollution", "network_effect"), {"sociology": "Social externalities", "environment": "Environmental impact", "network_science": "Network effects"}),
        "moral_hazard": DomainConcept("moral_hazard", "Risk-taking when protected from consequences", ("information_asymmetry", "insurance", "principal_agent"), {"psychology": "Reduced vigilance", "sociology": "Dependency culture", "finance": "Too big to fail"}),
        "network_effect": DomainConcept("network_effect", "Value increases with more users", ("metcalfe", "platform", "critical_mass"), {"sociology": "Social networks", "telecommunications": "Phone networks", "transportation": "Transit networks"}),
        "comparative_advantage": DomainConcept("comparative_advantage", "Benefit from specializing in lower opportunity cost", ("trade", "specialization", "efficiency"), {"biology": "Ecological specialization", "sociology": "Division of labor", "psychology": "Personal strengths"}),
        "inflation": DomainConcept("inflation", "General increase in prices over time", ("deflation", "monetary_policy", "purchasing_power"), {"physics": "Expansion/inflation of universe", "biology": "Inflammation (swelling)", "meteorology": "Atmospheric inflation"}),
        "liquidity": DomainConcept("liquidity", "Ease of converting assets to cash", ("cash", "market_depth", "frozen"), {"chemistry": "Liquid state/flow", "physics": "Fluid dynamics", "psychology": "Cognitive fluidity"}),
    },
    fundamental_principles=["People face trade-offs", "Cost of something is what you give up", "Rational people think at the margin", "People respond to incentives"],
    common_methods=["Econometric analysis", "Game theory", "Behavioral experiments", "Macroeconomic modeling"],
    units_of_analysis=["Dollar/Euro/Yen", "GDP", "Utility (utils)", "Employment rate"],
    abstraction_level=0.80,
    temporal_scale="transactions (seconds) to economic epochs (centuries)",
    spatial_scale="individual to global economy",
))

_register_domain(KnowledgeDomain(
    name="psychology",
    category="social_science",
    description="Scientific study of mind and behavior",
    concepts={
        "cognition": DomainConcept("cognition", "Mental processes of knowing and reasoning", ("perception", "memory", "thinking", "decision"), {"computer_science": "Information processing", "neuroscience": "Neural computation", "AI": "Cognitive architectures"}),
        "bias": DomainConcept("bias", "Systematic deviation from rational judgment", ("heuristic", "prejudice", "confirmation", "anchoring"), {"statistics": "Statistical bias", "machine_learning": "Algorithmic bias", "journalism": "Media bias"}),
        "motivation": DomainConcept("motivation", "Factors initiating and directing behavior", ("drive", "intrinsic", "extrinsic", "goal"), {"economics": "Incentives", "biology": "Survival drive", "physics": "Force/drive"}),
        "perception": DomainConcept("perception", "Organization and interpretation of sensory input", ("sensation", "attention", "illusion", "schema"), {"physics": "Measurement/observation", "philosophy": "Phenomenology", "computer_vision": "Visual processing"}),
        "memory": DomainConcept("memory", "Encoding, storage, and retrieval of information", ("short_term", "long_term", "encoding", "recall"), {"computer_science": "RAM/storage", "history": "Collective memory", "neuroscience": "Synaptic plasticity"}),
        "habit": DomainConcept("habit", "Automated behavior triggered by context", ("routine", "cue", "reward", "automaticity"), {"biology": "Conditioned reflex", "sociology": "Social habits/customs", "computer_science": "Cached routines"}),
        "attribution": DomainConcept("attribution", "How people explain causes of behavior", ("internal", "external", "fundamental_error", "self_serving"), {"sociology": "Social attribution", "journalism": "Cause attribution", "law": "Legal causation"}),
        "schema": DomainConcept("schema", "Cognitive framework for organizing knowledge", ("script", "frame", "prototype", "stereotype"), {"computer_science": "Database schema", "linguistics": "Grammatical schemas", "art": "Visual schemas"}),
        "flow": DomainConcept("flow", "Mental state of complete absorption in activity", ("engagement", "optimal_experience", "mastery", "immersion"), {"physics": "Fluid flow", "sociology": "Social flow", "music": "Musical flow/groove"}),
        "resilience": DomainConcept("resilience", "Capacity to recover from adversity", ("coping", "adaptation", "grit", "post_traumatic_growth"), {"materials_science": "Material resilience", "ecology": "Ecosystem resilience", "engineering": "System resilience"}),
        "conditioning": DomainConcept("conditioning", "Learning through association or consequences", ("classical", "operant", "reinforcement", "punishment"), {"computer_science": "Reinforcement learning", "education": "Teaching methods", "biology": "Conditioned reflexes"}),
        "theory_of_mind": DomainConcept("theory_of_mind", "Ability to attribute mental states to others", ("empathy", "perspective_taking", "intentionality"), {"AI": "Theory of mind in agents", "literature": "Character perspective", "sociology": "Social understanding"}),
    },
    fundamental_principles=["Behavior has multiple causes", "Nature and nurture interact", "Mind and body are connected", "People are active information processors"],
    common_methods=["Experimentation", "Observation", "Survey", "Neuroimaging", "Longitudinal studies"],
    units_of_analysis=["Individual", "Dyad", "Group", "Culture"],
    abstraction_level=0.70,
    temporal_scale="milliseconds (reaction) to lifespan (development)",
    spatial_scale="neural circuit to cultural level",
))


# ---- Continue registering more domains ----

_register_domain(KnowledgeDomain(
    name="sociology",
    category="social_science",
    description="Study of society and social relationships",
    concepts={
        "network": DomainConcept("network", "Pattern of social relationships", ("tie", "node", "centrality", "clustering"), {"computer_science": "Computer network", "biology": "Neural network", "mathematics": "Graph theory"}),
        "culture": DomainConcept("culture", "Shared beliefs, values, and practices", ("norm", "symbol", "ritual", "tradition"), {"biology": "Cell culture", "anthropology": "Cultural anthropology", "business": "Corporate culture"}),
        "institution": DomainConcept("institution", "Established social structures and norms", ("organization", "norm", "legitimacy", "path_dependence"), {"economics": "Economic institutions", "politics": "Political institutions", "law": "Legal institutions"}),
        "norm": DomainConcept("norm", "Shared expectation about appropriate behavior", ("conformity", "deviance", "sanction", "socialization"), {"mathematics": "Mathematical norm", "physics": "Normal vector", "linguistics": "Language norms"}),
        "hierarchy": DomainConcept("hierarchy", "Ranked system of statuses or roles", ("power", "stratification", "authority", "dominance"), {"computer_science": "Class hierarchy", "biology": "Taxonomic hierarchy", "mathematics": "Hierarchical sets"}),
        "collective_behavior": DomainConcept("collective_behavior", "Action taken by large numbers of people", ("crowd", "social_movement", "fad", "panic"), {"physics": "Collective motion", "biology": "Swarm behavior", "economics": "Herd behavior in markets"}),
        "social_capital": DomainConcept("social_capital", "Value derived from social networks and trust", ("trust", "reciprocity", "network", "bonding", "bridging"), {"economics": "Human capital", "finance": "Financial capital", "political_science": "Political capital"}),
        "anomie": DomainConcept("anomie", "Breakdown of social norms leading to confusion", ("normlessness", "alienation", "deviance", "Durkheim"), {"psychology": "Existential confusion", "ethics": "Moral confusion", "politics": "Political instability"}),
        "stratification": DomainConcept("stratification", "Layering of society into hierarchical classes", ("class", "caste", "mobility", "inequality"), {"geology": "Geological strata", "biology": "Tissue layers", "computer_science": "Protocol layers"}),
        "socialization": DomainConcept("socialization", "Process of learning social norms and roles", ("agent", "primary", "secondary", "anticipatory"), {"education": "Schooling", "psychology": "Developmental learning", "anthropology": "Enculturation"}),
        "bureaucracy": DomainConcept("bureaucracy", "Organizational structure with formal rules", ("hierarchy", "rationality", "Weber", "red_tape"), {"computer_science": "Algorithmic processes", "government": "Administrative systems", "organization": "Corporate structure"}),
        "deviance": DomainConcept("deviance", "Violation of social norms", ("crime", "stigma", "labeling", "social_control"), {"statistics": "Statistical deviation", "engineering": "Device deviation from spec", "biology": "Genetic deviation"}),
    },
    fundamental_principles=["Social structure influences individual behavior", "Power is unevenly distributed", "Social facts have objective reality", "Change is constant"],
    common_methods=["Survey research", "Ethnography", "Social network analysis", "Comparative historical analysis"],
    units_of_analysis=["Individual", "Group", "Organization", "Society", "World system"],
    abstraction_level=0.75,
    temporal_scale="interaction moments to centuries",
    spatial_scale="dyad to global system",
))

_register_domain(KnowledgeDomain(
    name="philosophy",
    category="humanities",
    description="Systematic study of fundamental questions about existence, knowledge, and ethics",
    concepts={
        "ontology": DomainConcept("ontology", "Study of what exists and the nature of being", ("being", "existence", "category", "substance"), {"computer_science": "Ontologies in knowledge representation", "physics": "What fundamental entities exist", "mathematics": "Mathematical existence"}),
        "epistemology": DomainConcept("epistemology", "Study of knowledge and justified belief", ("belief", "justification", "truth", "skepticism"), {"science": "Scientific method", "AI": "Machine knowledge", "psychology": "How humans know"}),
        "ethics": DomainConcept("ethics", "Study of moral principles and values", ("morality", "virtue", "duty", "consequentialism", "deontology"), {"economics": "Welfare economics", "law": "Legal ethics", "AI": "AI alignment/AI ethics"}),
        "logic": DomainConcept("logic", "Study of valid reasoning and argumentation", ("deduction", "induction", "fallacy", "validity"), {"computer_science": "Logic programming", "mathematics": "Formal logic", "law": "Legal reasoning"}),
        "metaphysics": DomainConcept("metaphysics", "Study of the fundamental nature of reality", ("causation", "time", "space", "free_will", "determinism"), {"physics": "Foundations of physics", "cosmology": "Nature of the universe", "neuroscience": "Nature of mind"}),
        "consciousness": DomainConcept("consciousness", "Subjective experience and awareness", ("qualia", "intentionality", "phenomenology", "hard_problem"), {"neuroscience": "Neural correlates", "AI": "Machine consciousness", "psychology": "States of consciousness"}),
        "free_will": DomainConcept("free_will", "Capacity to choose between alternatives", ("determinism", "compatibilism", "libertarianism", "autonomy"), {"physics": "Physical determinism", "law": "Legal responsibility", "AI": "Agent autonomy"}),
        "aesthetics": DomainConcept("aesthetics", "Study of beauty and artistic value", ("beauty", "sublime", "taste", "criticism"), {"art": "Art theory", "psychology": "Psychology of beauty", "economics": "Value of art"}),
        "dialectic": DomainConcept("dialectic", "Method of argument through contradiction and synthesis", ("thesis", "antithesis", "synthesis", "Hegel"), {"politics": "Political dialectics", "science": "Scientific progress (Kuhn)", "psychology": "Cognitive dissonance resolution"}),
        "nihilism": DomainConcept("nihilism", "Rejection of meaning, purpose, or objective truth", ("existentialism", "absurdism", "meaning"), {"culture": "Postmodern nihilism", "physics": "Heat death of universe", "psychology": "Existential depression"}),
        "phenomenology": DomainConcept("phenomenology", "Study of structures of conscious experience", ("intentionality", "lived_experience", " bracketing", "essence"), {"psychology": "Subjective experience", "neuroscience": "Neural correlates of experience", "design": "User experience research"}),
        "utilitarianism": DomainConcept("utilitarianism", "Greatest good for greatest number", ("consequentialism", "happiness", "welfare", "aggregation"), {"economics": "Welfare economics", "public_policy": "Cost-benefit analysis", "AI": "Alignment/utilitarian AI"}),
    },
    fundamental_principles=["Question everything", "Arguments need justification", "Clarity in concepts", "Reason as a tool"],
    common_methods=["Conceptual analysis", "Thought experiments", "Phenomenological description", "Dialectical reasoning"],
    units_of_analysis=["Concept", "Argument", "Worldview", "Tradition"],
    abstraction_level=0.95,
    temporal_scale="timeless",
    spatial_scale="conceptual / universal",
))


# ---- Registering additional domains (batch 2) ----

_register_domain(KnowledgeDomain(
    name="linguistics",
    category="humanities",
    description="Scientific study of language",
    concepts={
        "syntax": DomainConcept("syntax", "Rules for sentence structure", ("grammar", "phrase", "clause", "constituent"), {"computer_science": "Programming language syntax", "music": "Musical syntax/harmonic progression", "mathematics": "Formal syntax"}),
        "semantics": DomainConcept("semantics", "Study of meaning in language", ("meaning", "reference", "truth", "pragmatics"), {"computer_science": "Semantic web", "psychology": "Semantic memory", "logic": "Model-theoretic semantics"}),
        "phonology": DomainConcept("phonology", "System of sounds in a language", ("phoneme", "allophone", "prosody", "syllable"), {"music": "Phonology as musical system", "biology": "Vocal production", "physics": "Acoustic phonetics"}),
        "pragmatics": DomainConcept("pragmatics", "Language use in context", ("implicature", "speech_act", "context", "deixis"), {"sociology": "Social context", "AI": "Conversational AI", "psychology": "Social cognition"}),
        "morphology": DomainConcept("morphology", "Study of word formation", ("morpheme", "inflection", "derivation", "affix"), {"biology": "Morphology of organisms", "chemistry": "Molecular morphology", "computer_science": "File format morphology"}),
        "evolution": DomainConcept("evolution", "Change in languages over time", ("language_change", "speciation", "creole", "dialect"), {"biology": "Biological evolution", "sociology": "Social evolution", "technology": "Technology evolution"}),
        "universal_grammar": DomainConcept("universal_grammar", "Innate linguistic capacity", ("Chomsky", "principles", "parameters", "language_acquisition"), {"biology": "Genetic programming", "computer_science": "Hardcoded algorithms", "psychology": "Innate cognitive structures"}),
        "metaphor": DomainConcept("metaphor", "Understanding one concept in terms of another", ("mapping", "conceptual", "source", "target", "Lakoff"), {"mathematics": "Mathematical metaphor", "art": "Visual metaphor", "science": "Scientific models as metaphors"}),
        "discourse": DomainConcept("discourse", "Connected sequences of language use", ("coherence", "cohesion", "genre", "register"), {"sociology": "Social discourse", "politics": "Political discourse", "psychology": "Narrative psychology"}),
        "code_switching": DomainConcept("code_switching", "Alternating between languages/varieties", ("bilingualism", "register", "identity", "context"), {"computer_science": "Context switching", "psychology": "Cognitive switching", "sociology": "Identity negotiation"}),
        "lexicon": DomainConcept("lexicon", "Vocabulary of a language or speaker", ("vocabulary", "word", "lemma", "dictionary"), {"computer_science": "Database schema", "anthropology": "Cultural knowledge store", "psychology": "Mental lexicon"}),
        "pidgin": DomainConcept("pidgin", "Simplified contact language", ("creole", "contact", "simplification", " lingua_franca"), {"business": "Business jargon/lingo", "technology": "API interfaces as pidgins", "diplomacy": "Diplomatic language"}),
    },
    fundamental_principles=["Language is systematic", "Language is creative/generative", "Language varies and changes", "Form and meaning interact"],
    common_methods=["Corpus analysis", "Elicitation", "Experimental syntax", "Historical comparison", "Fieldwork"],
    units_of_analysis=["Phoneme", "Morpheme", "Word", "Sentence", "Discourse"],
    abstraction_level=0.80,
    temporal_scale="real-time processing to millennia of change",
    spatial_scale="individual speaker to global language family",
))

_register_domain(KnowledgeDomain(
    name="music",
    category="arts",
    description="Art of organizing sound in time",
    concepts={
        "harmony": DomainConcept("harmony", "Simultaneous combination of notes", ("chord", "progression", "consonance", "tonality"), {"mathematics": "Frequency ratios", "sociology": "Social harmony", "color_theory": "Color harmony", "psychology": "Emotional harmony"}),
        "rhythm": DomainConcept("rhythm", "Pattern of durations and accents in time", ("beat", "meter", "tempo", "syncopation"), {"poetry": "Poetic meter", "biology": "Circadian rhythm", "dance": "Choreographic rhythm", "physics": "Periodic motion"}),
        "frequency": DomainConcept("frequency", "Rate of vibration determining pitch", ("pitch", "Hertz", "spectrum", "overtone"), {"physics": "Wave frequency", "statistics": "Frequency distribution", "biology": "Population frequency"}),
        "resonance": DomainConcept("resonance", "Reinforcement of sound through sympathetic vibration", ("harmonic", "acoustics", "body", "sustain"), {"physics": "Physical resonance", "sociology": "Emotional resonance", "neuroscience": "Neural resonance"}),
        "composition": DomainConcept("composition", "Creation of musical works", ("form", "structure", "theme", "variation"), {"art": "Visual composition", "literature": "Literary composition", "chemistry": "Chemical composition"}),
        "dissonance": DomainConcept("dissonance", "Tension from conflicting sounds", ("consonance", "resolution", "tension", "cluster"), {"psychology": "Cognitive dissonance", "sociology": "Social conflict", "drama": "Narrative tension"}),
        "timbre": DomainConcept("timbre", "Quality distinguishing different sounds", ("spectrum", "envelope", "timbre_space", "instrument"), {"psychology": "Perceptual quality", "linguistics": "Voice quality", "materials_science": "Material acoustic signature"}),
        "polyphony": DomainConcept("polyphony", "Multiple independent melodic lines", ("counterpoint", "voice", "texture", "imitation"), {"sociology": "Multiple voices/perspectives", "biology": "Parallel evolution", "literature": "Multi-threaded narrative"}),
        "modulation": DomainConcept("modulation", "Change from one key to another", ("key", "pivot", "transition", "tonic"), {"communication": "Signal modulation", "psychology": "Emotional modulation", "chemistry": "State modulation"}),
        "improvisation": DomainConcept("improvisation", "Spontaneous musical creation", ("spontaneity", "creativity", "jazz", "extemporization"), {"theater": "Improvisational theater", "business": "Adaptive strategy", "AI": "Generative AI"}),
        "dynamics": DomainConcept("dynamics", "Variations in loudness", ("forte", "piano", "crescendo", "expression"), {"physics": "Fluid dynamics", "economics": "Market dynamics", "sociology": "Group dynamics"}),
        "counterpoint": DomainConcept("counterpoint", "Art of combining independent melodies", ("voice_leading", "fugue", "canon", "imitation"), {"mathematics": "Independent variables", "architecture": "Spatial counterpoint", "dance": "Choreographic counterpoint"}),
    },
    fundamental_principles=["Sound is organized vibration", "Time is the canvas", "Tension and resolution create meaning", "Pattern recognition is fundamental to listening"],
    common_methods=["Composition", "Analysis", "Performance", "Acoustic measurement", "Psychophysics"],
    units_of_analysis=["Note", "Chord", "Measure", "Phrase", "Movement"],
    abstraction_level=0.70,
    temporal_scale="milliseconds to hours",
    spatial_scale="individual ear to concert hall",
))

_register_domain(KnowledgeDomain(
    name="architecture",
    category="arts",
    description="Art and science of designing buildings and structures",
    concepts={
        "structure": DomainConcept("structure", "Arrangement of elements resisting forces", ("load", "frame", "shell", "truss"), {"biology": "Anatomical structure", "sociology": "Social structure", "linguistics": "Syntactic structure", "computer_science": "Data structure"}),
        "load": DomainConcept("load", "Force applied to a structure", ("dead_load", "live_load", "wind", "seismic", "tension"), {"computer_science": "System load", "economics": "Debt load", "psychology": "Cognitive load"}),
        "tension": DomainConcept("tension", "Pulling force stretching a material", ("compression", "stress", "strain", "cable"), {"psychology": "Emotional tension", "drama": "Narrative tension", "physics": "Tension force", "politics": "Political tension"}),
        "compression": DomainConcept("compression", "Squeezing force shortening a material", ("tension", "buckling", "column", "arch"), {"computer_science": "Data compression", "biology": "Vascular compression", "economics": "Market compression/consolidation"}),
        "form": DomainConcept("form", "Three-dimensional shape and mass", ("space", "mass", "geometry", "proportion"), {"art": "Artistic form", "philosophy": "Platonic form", "biology": "Morphological form", "literature": "Literary form"}),
        "space": DomainConcept("space", "Three-dimensional extent defined by enclosure", ("volume", "void", "proportion", "scale"), {"mathematics": "Geometric space", "physics": "Spacetime", "sociology": "Social space (Lefebvre)", "psychology": "Personal space"}),
        "symmetry": DomainConcept("symmetry", "Balanced proportion of elements", ("axis", "reflection", "rotation", "proportion"), {"mathematics": "Geometric symmetry", "biology": "Bilateral symmetry", "physics": "Symmetry laws"}),
        "scale": DomainConcept("scale", "Relative size proportion", ("proportion", "human_scale", "monumental", "intimate"), {"mathematics": "Numerical scale", "geography": "Map scale", "music": "Musical scale", "economics": "Economies of scale"}),
        "tectonics": DomainConcept("tectonics", "Art of construction and joining", ("joint", "connection", "material", "assembly"), {"geology": "Plate tectonics", "biology": "Cellular tectonics", "linguistics": "Syntactic tectonics"}),
        "program": DomainConcept("program", "Functional requirements of a building", ("function", "use", "activity", "flow"), {"computer_science": "Computer program", "management": "Business program", "education": "Educational program"}),
        "context": DomainConcept("context", "Environmental and cultural setting", ("site", "climate", "culture", "vernacular"), {"psychology": "Social context", "linguistics": "Linguistic context", "computer_science": "Execution context"}),
        "fenestration": DomainConcept("fenestration", "Design and placement of openings", ("window", "light", "aperture", "view"), {"optics": "Aperture", "astronomy": "Observational window", "geology": "Veins/dikes as Earth windows"}),
    },
    fundamental_principles=["Form follows function", "Structure expresses force", "Space is the essence", "Architecture serves human needs"],
    common_methods=["Design studio", "Structural analysis", "Model making", "Environmental simulation"],
    units_of_analysis=["Module", "Bay", "Room", "Floor", "Building", "Urban block"],
    abstraction_level=0.65,
    temporal_scale="construction months to centuries of use",
    spatial_scale="detail to urban fabric",
))


# ---- Registering remaining domains in batches ----

_register_domain(KnowledgeDomain(
    name="oceanography",
    category="natural_science",
    description="Study of the physical and biological aspects of the ocean",
    concepts={
        "current": DomainConcept("current", "Continuous directed movement of ocean water", ("gyre", "thermohaline", "tide", "upwelling"), {"physics": "Electrical current", "sociology": "Cultural currents", "economics": "Economic currents/trends", "electricity": "Electric current"}),
        "pressure": DomainConcept("pressure", "Force per unit area exerted by water column", ("depth", "bar", "isobar", "gradient"), {"physics": "Pressure in gases", "psychology": "Social pressure", "meteorology": "Atmospheric pressure"}),
        "salinity": DomainConcept("salinity", "Salt concentration in seawater", ("psu", "halocline", "evaporation", "freshwater"), {"chemistry": "Solution concentration", "biology": "Osmotic balance", "meteorology": "Precipitation/evaporation balance"}),
        "thermocline": DomainConcept("thermocline", "Transition layer between warm and cold water", ("stratification", "mixed_layer", "deep_water", "temperature"), {"atmosphere": "Tropopause", "sociology": "Social stratification", "physics": "Thermal boundary layer"}),
        "upwelling": DomainConcept("upwelling", "Deep nutrient-rich water rising to surface", ("nutrient", "productivity", "Ekman", "downwelling"), {"economics": "Resource upwelling/new discoveries", "sociology": "Social upwelling/emergence", "geology": "Mantle upwelling"}),
        "tide": DomainConcept("tide", "Periodic rise and fall of sea level", ("lunar", "solar", "spring", "neap", "amplitude"), {"politics": "Political tides", "sociology": "Social tides/trends", "metaphor": "Tide of history"}),
        "plankton": DomainConcept("plankton", "Drifting organisms in water column", ("phytoplankton", "zooplankton", "bloom", "food_web"), {"economics": "Economic plankton/small businesses", "sociology": "Social drift", "meteorology": "Atmospheric plankton/aerosols"}),
        "benthic": DomainConcept("benthic", "Bottom-dwelling organisms and zone", ("sediment", "abyssal", "vent", "ecosystem"), {"geology": "Bedrock layer", "sociology": "Bottom of social hierarchy", "economics": "Base of economic pyramid"}),
        "acidification": DomainConcept("acidification", "Decrease in ocean pH from CO2 absorption", ("pH", "carbonate", "shell", "bleaching"), {"chemistry": "Acid-base chemistry", "medicine": "Metabolic acidosis", "environmental_science": "Soil acidification"}),
        "gyre": DomainConcept("gyre", "Large circular ocean current system", ("vortex", "circulation", "garbage_patch", "Coriolis"), {"meteorology": "Atmospheric gyres", "physics": "Rotational dynamics", "sociology": "Cultural gyres/cycles"}),
        "tsunami": DomainConcept("tsunami", "Large ocean wave from seismic displacement", ("seismic", "wave", "runup", "warning"), {"sociology": "Social tsunami/mass movements", "economics": "Financial tsunami", "metaphor": "Tsunami of change"}),
        "brine": DomainConcept("brine", "Concentrated salt solution", ("salinity", "desalination", "pickling", "pool"), {"chemistry": "Salt solution", "food_science": "Brining", "geology": "Brine pools"}),
    },
    fundamental_principles=["Oceans regulate climate", "Water density drives circulation", "Marine ecosystems are interconnected", "Oceans are under pressure from human activity"],
    common_methods=["Oceanographic surveys", "Remote sensing", "Buoy measurements", "Submersible exploration", "Modeling"],
    units_of_analysis=["Water parcel", "Plankton community", "Current system", "Basin"],
    abstraction_level=0.60,
    temporal_scale="seconds (waves) to millennia (circulation)",
    spatial_scale="molecular to ocean basin",
))

_register_domain(KnowledgeDomain(
    name="astronomy",
    category="natural_science",
    description="Study of celestial objects and the universe",
    concepts={
        "orbit": DomainConcept("orbit", "Path of one body around another", ("ellipse", "Kepler", "period", "eccentricity"), {"physics": "Orbital mechanics", "chemistry": "Electron orbitals", "metaphor": "Social orbit"}),
        "redshift": DomainConcept("redshift", "Increase in wavelength from moving source", ("Doppler", "Hubble", "expansion", "blueshift"), {"acoustics": "Doppler shift in sound", "metaphor": "Cosmic retreat", "technology": "Radar speed detection"}),
        "black_hole": DomainConcept("black_hole", "Region where gravity prevents escape", ("event_horizon", "singularity", "accretion", "spaghettification"), {"finance": "Debt black hole", "metaphor": "Information black hole", "sociology": "Bureaucratic black hole"}),
        "nebula": DomainConcept("nebula", "Cloud of gas and dust in space", ("emission", "reflection", "planetary", "star_formation"), {"meteorology": "Cloud formations", "chemistry": "Aerosol clouds", "art": "Nebulous art forms"}),
        "dark_matter": DomainConcept("dark_matter", "Invisible mass affecting gravity", ("rotation_curve", "WIMP", "halos", "gravitational_lensing"), {"economics": "Shadow economy", "sociology": "Invisible social forces", "psychology": "Unconscious drives"}),
        "exoplanet": DomainConcept("exoplanet", "Planet outside our solar system", ("transit", "habitable_zone", "atmosphere", "biosignature"), {"exploration": "New territories", "sociology": "Alien societies (speculative)", "biology": "Alternative biochemistries"}),
        "supernova": DomainConcept("supernova", "Stellar explosion at end of life", ("nucleosynthesis", "remnant", " Type_Ia", "neutron_star"), {"metaphor": "Explosive breakthrough", "chemistry": "Element creation", "history": "Sudden historical change"}),
        "galaxy": DomainConcept("galaxy", "Gravitationally bound system of stars", ("spiral", "elliptical", "barred", "merger"), {"sociology": "Social galaxies/communities", "biology": "Cellular galaxies", "metaphor": "Galaxy of ideas"}),
        "cosmic_microwave_background": DomainConcept("cosmic_microwave_background", "Relic radiation from Big Bang", ("anisotropy", "Big_Bang", "recombination", "WMAP"), {"archaeology": "Cultural fossils", "history": "Historical records", "geology": "Rock strata"}),
        "gravitational_wave": DomainConcept("gravitational_wave", "Ripple in spacetime from massive acceleration", ("LIGO", "spacetime", "merger", "detector"), {"sociology": "Ripple effects", "meteorology": "Atmospheric waves", "oceanography": "Ocean waves"}),
        "habitable_zone": DomainConcept("habitable_zone", "Region where liquid water could exist", ("Goldilocks", "temperature", "atmosphere", "liquid_water"), {"economics": "Viable market zone", "ecology": "Ecological niche", "urban_planning": "Livable zone"}),
        "spacetime": DomainConcept("spacetime", "Four-dimensional fabric of the universe", ("curvature", "metric", "interval", "manifold"), {"philosophy": "Nature of reality", "computer_science": "4D data structures", "mathematics": "Riemannian manifold"}),
    },
    fundamental_principles=["Laws of physics are universal", "Universe is expanding", "Gravity shapes structure", "Light carries information across space and time"],
    common_methods=["Telescopic observation", "Spectroscopy", "Computational astrophysics", "Gravitational wave detection"],
    units_of_analysis=["Light-year", "Parsec", "Solar mass", "Magnitude"],
    abstraction_level=0.90,
    temporal_scale="billions of years",
    spatial_scale="subatomic to observable universe (93 Gly)",
))

_register_domain(KnowledgeDomain(
    name="geology",
    category="natural_science",
    description="Study of Earth's physical structure and history",
    concepts={
        "plate_tectonics": DomainConcept("plate_tectonics", "Theory of moving lithospheric plates", ("subduction", "ridge", "fault", "mantle"), {"sociology": "Social tectonics/collisions", "politics": "Political fault lines", "economics": "Structural shifts"}),
        "sedimentation": DomainConcept("sedimentation", "Deposition and accumulation of particles", ("stratification", "erosion", "compaction", "lithification"), {"history": "Layered history", "information_science": "Data sedimentation", "sociology": "Cultural layers"}),
        "mineral": DomainConcept("mineral", "Naturally occurring inorganic solid with crystal structure", ("crystal", "hardness", " Mohs", "ore"), {"biology": "Essential nutrients", "economics": "Mineral resources", "materials_science": "Material properties"}),
        "volcano": DomainConcept("volcano", "Opening where magma erupts", ("magma", "lava", "caldera", "eruption"), {"psychology": "Emotional eruption", "politics": "Political eruption", "metaphor": "Volcano of creativity"}),
        "metamorphism": DomainConcept("metamorphism", "Change in rock from heat and pressure", ("foliation", "grade", "facies", "recrystallization"), {"psychology": "Personal transformation", "sociology": "Social transformation", "biology": "Metamorphosis"}),
        "fossil": DomainConcept("fossil", "Preserved remains of ancient organisms", ("trace", "index", "preservation", "excavation"), {"technology": "Technological fossils", "culture": "Cultural fossils", "linguistics": "Linguistic fossils"}),
        "earthquake": DomainConcept("earthquake", "Sudden release of energy in Earth's crust", ("seismic", "magnitude", "Richter", "fault", "tsunami"), {"finance": "Market earthquake", "politics": "Political earthquake", "sociology": "Social upheaval"}),
        "erosion": DomainConcept("erosion", "Wearing away of Earth materials", ("weathering", "transport", "deposition", "landform"), {"economics": "Wealth erosion", "sociology": "Social erosion", "psychology": "Memory erosion"}),
        "geologic_time": DomainConcept("geologic_time", "Chronology of Earth's history", ("eon", "era", "period", "epoch", "stratigraphy"), {"history": "Deep history", "biology": "Evolutionary time", "cosmology": "Cosmic time"}),
        "magma": DomainConcept("magma", "Molten rock beneath Earth's surface", ("igneous", "chamber", "viscosity", "pluton"), {"psychology": "Subconscious magma", "metaphor": "Creative magma", "politics": "Political magma/brewing change"}),
        "mineralogy": DomainConcept("mineralogy", "Study of minerals", ("crystallography", "optical", "XRD", "chemistry"), {"biology": "Taxonomy of organisms", "computer_science": "Classification systems", "library_science": "Cataloging"}),
        "seismic": DomainConcept("seismic", "Relating to earthquakes or vibrations", ("wave", "P_wave", "S_wave", "tomography"), {"acoustics": "Sound waves", "medicine": "Seismic tremors (Parkinsons)", "engineering": "Vibration analysis"}),
    },
    fundamental_principles=["Uniformitarianism", "Plate tectonics", "Rock cycle", "Deep time"],
    common_methods=["Field mapping", "Radiometric dating", "Seismic analysis", "Microscopy", "Remote sensing"],
    units_of_analysis=["Rock unit", "Stratum", "Formation", "Plate"],
    abstraction_level=0.55,
    temporal_scale="seconds (earthquakes) to billions of years",
    spatial_scale="mineral grain to planetary",
))

_register_domain(KnowledgeDomain(
    name="meteorology",
    category="natural_science",
    description="Study of the atmosphere and weather",
    concepts={
        "front": DomainConcept("front", "Boundary between air masses", ("cold_front", "warm_front", "occluded", "stationary"), {"military": "Battle front", "sociology": "Cultural frontiers", "politics": "Political fronts"}),
        "pressure_system": DomainConcept("pressure_system", "Region with relatively high or low pressure", ("high", "low", "anticyclone", "cyclone"), {"psychology": "Social pressure", "economics": "Market pressure", "engineering": "Pressure vessels"}),
        "humidity": DomainConcept("humidity", "Amount of water vapor in air", ("relative", "dew_point", "saturation", "mixing_ratio"), {"psychology": "Emotional humidity/tension", "sociology": "Social humidity/density", "materials_science": "Material humidity"}),
        "jet_stream": DomainConcept("jet_stream", "Narrow band of strong winds in upper atmosphere", ("Rossby", "polar", "subtropical", "meander"), {"oceanography": "Ocean currents", "economics": "Economic jet streams/trends", "sociology": "Social currents"}),
        "coriolis_effect": DomainConcept("coriolis_effect", "Apparent deflection due to Earth's rotation", ("rotation", "deflection", "cyclone", "geostrophic"), {"sociology": "Institutional inertia", "psychology": "Cognitive inertia", "physics": "Inertial frames"}),
        "greenhouse_effect": DomainConcept("greenhouse_effect", "Warming from trapped infrared radiation", ("CO2", "warming", "feedback", "radiative_forcing"), {"economics": "Greenhouse economy", "agriculture": "Greenhouse farming", "sociology": "Enclosed systems"}),
        "barometric_pressure": DomainConcept("barometric_pressure", "Atmospheric pressure measured by barometer", ("millibar", "high_pressure", "low_pressure", "isobar"), {"medicine": "Blood pressure", "physics": "Fluid pressure", "psychology": "Performance pressure"}),
        "cyclogenesis": DomainConcept("cyclogenesis", "Development of cyclonic systems", ("frontogenesis", "occlusion", "intensification", "extratropical"), {"sociology": "Formation of social movements", "politics": "Political cyclogenesis", "biology": "Morphogenesis"}),
        "dew_point": DomainConcept("dew_point", "Temperature at which air becomes saturated", ("condensation", "humidity", "saturation", "frost"), {"chemistry": "Saturation point", "psychology": "Breaking point", "metaphor": "Tipping point"}),
        "monsoon": DomainConcept("monsoon", "Seasonal reversal of winds bringing rain", ("seasonal", "precipitation", "ITCZ", "orographic"), {"economics": "Monsoon economy", "finance": "Seasonal markets", "sociology": "Seasonal social patterns"}),
        "tornado": DomainConcept("tornado", "Violently rotating column of air", ("vortex", "funnel", " Fujita", "supercell"), {"finance": "Financial tornado", "sociology": "Social vortex", "metaphor": "Tornado of activity"}),
        "albedo": DomainConcept("albedo", "Fraction of light reflected by a surface", ("reflectivity", "ice", "dark_surface", "forcing"), {"psychology": "Surface impression", "sociology": "Social reflectivity", "computer_graphics": "Surface reflectance"}),
    },
    fundamental_principles=["Energy from Sun drives weather", "Water cycle connects systems", "Pressure gradients create wind", "Conservation of angular momentum"],
    common_methods=["Remote sensing", "Numerical weather prediction", "Radar", "Radiosonde"],
    units_of_analysis=["Millibar", "Knot", "Celsius", "Percent humidity"],
    abstraction_level=0.60,
    temporal_scale="minutes (tornado) to climate epochs",
    spatial_scale="local to global",
))


# ============================================================================
# SECTION 1b — ADDITIONAL DOMAINS (25 more to reach 50+)
# ============================================================================

_register_domain(KnowledgeDomain(
    name="anthropology",
    category="social_science",
    description="Study of humans, past and present",
    concepts={
        "culture": DomainConcept("culture", "Learned and shared behaviors and beliefs", ("norm", "symbol", "ritual", "value", "practice"), {"biology": "Cell culture", "sociology": "Cultural sociology", "business": "Corporate culture"}),
        "kinship": DomainConcept("kinship", "System of social relationships based on family", ("descent", "marriage", "clan", "lineage"), {"graph_theory": "Family trees as graphs", "sociology": "Social bonds", "biology": "Genetic relatedness"}),
        "ethnography": DomainConcept("ethnography", "Qualitative study of people in their natural setting", ("participant_observation", "fieldwork", "thick_description", "emic"), {"journalism": "Immersion journalism", "sociology": "Qualitative research", "psychology": "Case study"}),
        "evolution": DomainConcept("evolution", "Change in human biology and culture over time", ("adaptation", "selection", "hominin", "bipedalism"), {"biology": "Biological evolution", "sociology": "Social evolution", "technology": "Technological evolution"}),
        "myth": DomainConcept("myth", "Traditional story embodying cultural beliefs", ("ritual", "symbol", "archetype", "cosmology"), {"literature": "Narrative archetypes", "psychology": "Collective unconscious (Jung)", "politics": "National myths"}),
        "taboo": DomainConcept("taboo", "Social prohibition on certain actions or topics", ("prohibition", "pollution", "sacred", "transgression"), {"sociology": "Social norms", "law": "Legal prohibitions", "psychology": "Moral disgust"}),
        "exchange": DomainConcept("exchange", "Transfer of goods, services, or symbols", ("reciprocity", "gift", "market", "Mauss"), {"economics": "Economic exchange", "sociology": "Social exchange theory", "communication": "Information exchange"}),
        "liminality": DomainConcept("liminality", "Transitional phase in rituals or social states", ("threshold", "rite_of_passage", "betwixt", "Turner"), {"psychology": "Life transitions", "sociology": "Social margins", "architecture": "Threshold spaces"}),
        "symbol": DomainConcept("symbol", "Object or action representing abstract meaning", ("sign", "meaning", "representation", "Saussure"), {"mathematics": "Mathematical symbols", "computer_science": "Symbolic computation", "psychology": "Symbolic thinking"}),
        "diffusion": DomainConcept("diffusion", "Spread of cultural traits between groups", ("borrowing", "innovation", "adoption", "wave"), {"physics": "Diffusion of particles", "sociology": "Idea diffusion", "epidemiology": "Disease diffusion"}),
        "totem": DomainConcept("totem", "Natural object or animal symbolizing a group", ("clan", "symbol", "Durkheim", "identity"), {"politics": "National symbols", "sociology": "Group identity markers", "psychology": "Identity anchors"}),
        "holism": DomainConcept("holism", "Study of whole systems rather than parts", ("system", "interconnected", "context", "functionalism"), {"medicine": "Holistic medicine", "ecology": "Ecosystem approach", "philosophy": "Holistic philosophy"}),
    },
    fundamental_principles=["Culture is learned", "Biology and culture interact", "Context matters", "Comparative approach illuminates universals"],
    common_methods=["Ethnography", "Archaeological excavation", "Linguistic analysis", "Physical anthropology"],
    units_of_analysis=["Individual", "Household", "Community", "Society", "Species"],
    abstraction_level=0.75,
    temporal_scale="ethnographic present to millions of years",
    spatial_scale="local community to global species",
))

_register_domain(KnowledgeDomain(
    name="political_science",
    category="social_science",
    description="Study of government, politics, and political behavior",
    concepts={
        "power": DomainConcept("power", "Ability to influence or control behavior", ("authority", "coercion", "legitimacy", "Weber"), {"physics": "Mechanical power", "sociology": "Social power", "psychology": "Personal power"}),
        "sovereignty": DomainConcept("sovereignty", "Supreme authority within a territory", ("state", "self_determination", "Westphalia", "supremacy"), {"law": "Legal sovereignty", "philosophy": "Personal sovereignty", "economics": "Monetary sovereignty"}),
        "democracy": DomainConcept("democracy", "Rule by the people", ("representation", "voting", "participation", "majority"), {"organization": "Democratic management", "education": "Student democracy", "technology": "Open-source governance"}),
        "ideology": DomainConcept("ideology", "System of political beliefs and values", ("liberalism", "conservatism", "socialism", "fascism"), {"psychology": "Belief systems", "sociology": "Worldview frameworks", "religion": "Religious ideology"}),
        "bureaucracy": DomainConcept("bureaucracy", "Administrative system with formal rules", ("administration", "red_tape", "hierarchy", "Weber"), {"business": "Corporate bureaucracy", "sociology": "Organizational structure", "computer_science": "Algorithmic procedures"}),
        "diplomacy": DomainConcept("diplomacy", "Practice of conducting negotiations between states", ("negotiation", "treaty", "embassy", "soft_power"), {"psychology": "Interpersonal diplomacy", "business": "Corporate diplomacy", "communication": "Strategic communication"}),
        "constitution": DomainConcept("constitution", "Fundamental principles governing a state", ("amendment", "rights", "separation_of_powers", "rule_of_law"), {"organization": "Organizational charter", "computer_science": "System constitution/configuration", "biology": "Genetic constitution"}),
        "federalism": DomainConcept("federalism", "Division of power between central and regional governments", ("devolution", "unitary", "confederation", "subsidiarity"), {"computer_science": "Distributed systems", "organization": "Decentralized management", "biology": "Modular organisms"}),
        "public_goods": DomainConcept("public_goods", "Goods non-excludable and non-rivalrous", ("free_rider", "externality", "provision", "collective_action"), {"economics": "Public economics", "sociology": "Common resources", "environment": "Environmental commons"}),
        "polarization": DomainConcept("polarization", "Divergence of political attitudes to extremes", ("partisanship", "gridlock", "ideology", "echo_chamber"), {"physics": "Wave polarization", "sociology": "Social polarization", "psychology": "Cognitive polarization"}),
        "regime": DomainConcept("regime", "Form of government or rules of a system", ("authoritarian", "democratic", "hybrid", "transition"), {"medicine": "Medical regime/treatment", "environment": "Environmental regime", "sociology": "Social regime"}),
        "geopolitics": DomainConcept("geopolitics", "Politics influenced by geographic factors", ("territory", "resources", "strategic", "Mackinder"), {"economics": "Economic geography", "military": "Military strategy", "environment": "Environmental determinism"}),
    },
    fundamental_principles=["Power is central to politics", "Institutions shape behavior", "Interests drive conflict and cooperation", "Ideas matter"],
    common_methods=["Statistical analysis", "Case studies", "Game theory", "Survey research", "Content analysis"],
    units_of_analysis=["Individual voter", "Interest group", "Party", "State", "International system"],
    abstraction_level=0.80,
    temporal_scale="election cycles to regime centuries",
    spatial_scale="local ward to international system",
))

_register_domain(KnowledgeDomain(
    name="history",
    category="humanities",
    description="Study and interpretation of past events",
    concepts={
        "causation": DomainConcept("causation", "Relationship between events where one produces another", ("cause", "effect", "contingency", "determinism"), {"physics": "Physical causation", "law": "Legal causation", "philosophy": "Causal metaphysics"}),
        "periodization": DomainConcept("periodization", "Division of history into named eras", ("epoch", "era", "age", "turning_point"), {"geology": "Geological periods", "biology": "Life history stages", "literature": "Literary periods"}),
        "primary_source": DomainConcept("primary_source", "Direct evidence from the time under study", ("document", "artifact", "testimony", "archive"), {"science": "Raw data", "journalism": "First-hand reporting", "law": "Direct evidence"}),
        "revisionism": DomainConcept("revisionism", "Reinterpretation of historical accounts", ("orthodox", "interpretation", "narrative", "source"), {"science": "Scientific revision", "politics": "Political revisionism", "psychology": "Memory revision"}),
        "empire": DomainConcept("empire", "State extending dominion over multiple territories", ("imperialism", "colonialism", "hegemony", "metropole"), {"business": "Corporate empire", "computer_science": "Software empires", "biology": "Ecological empire/invasive species"}),
        "revolution": DomainConcept("revolution", "Fundamental and rapid change in a society", ("upheaval", "transformation", "rebellion", "regime_change"), {"physics": "Circular revolution", "astronomy": "Orbital revolution", "technology": "Technological revolution"}),
        "continuity": DomainConcept("continuity", "Persistence of institutions or patterns over time", ("change", "tradition", "institution", "longue_duree"), {"mathematics": "Mathematical continuity", "physics": "Continuous functions", "psychology": "Psychological continuity"}),
        "narrative": DomainConcept("narrative", "Story organizing historical events", ("chronicle", "interpretation", "source", "plot"), {"literature": "Literary narrative", "psychology": "Personal narrative", "sociology": "Social narrative"}),
        "archive": DomainConcept("archive", "Repository of historical documents", ("preservation", "access", "memory", "record"), {"computer_science": "Data archives", "biology": "Genetic archives", "psychology": "Memory as archive"}),
        "historiography": DomainConcept("historiography", "Study of how history is written", ("method", "school", "paradigm", "source"), {"science": "Study of scientific methods", "literature": "Literary criticism", "philosophy": "Epistemology"}),
        "legacy": DomainConcept("legacy", "Long-lasting impact of past events or people", ("inheritance", "heritage", "consequence", "memory"), {"law": "Legal legacy", "technology": "Technical debt/legacy systems", "psychology": "Psychological legacy"}),
        "diaspora": DomainConcept("diaspora", "Dispersion of people from their homeland", ("migration", "identity", "homeland", "community"), {"biology": "Species dispersal", "physics": "Diaspora of particles", "metaphor": "Diaspora of ideas"}),
    },
    fundamental_principles=["Context is essential", "Multiple perspectives exist", "Sources must be critically evaluated", "Past and present interact"],
    common_methods=["Archival research", "Oral history", "Quantitative analysis", "Comparative history"],
    units_of_analysis=["Event", "Individual", "Institution", "Civilization", "Era"],
    abstraction_level=0.75,
    temporal_scale="moments to deep time",
    spatial_scale="local to global",
))

_register_domain(KnowledgeDomain(
    name="law",
    category="social_science",
    description="System of rules enforced by institutions",
    concepts={
        "jurisdiction": DomainConcept("jurisdiction", "Authority to make legal decisions", ("territory", "competence", "sovereign", "conflict"), {"sociology": "Social jurisdiction", "computer_science": "Scope of authority", "politics": "Political jurisdiction"}),
        "precedent": DomainConcept("precedent", "Prior legal case guiding future decisions", ("stare_decisis", "binding", "distinguishing", "overruling"), {"science": "Scientific precedent", "sociology": "Social precedents", "psychology": "Behavioral precedent"}),
        "liability": DomainConcept("liability", "Legal responsibility for acts or omissions", ("negligence", "strict", "fault", "tort"), {"finance": "Financial liability", "insurance": "Insurance liability", "engineering": "Product liability"}),
        "contract": DomainConcept("contract", "Legally enforceable agreement", ("offer", "acceptance", "consideration", "breach"), {"biology": "Social contract in animals", "economics": "Economic contracts", "sociology": "Social contract theory"}),
        "due_process": DomainConcept("due_process", "Fair treatment through judicial system", ("hearing", "notice", "fairness", "procedure"), {"ethics": "Procedural justice", "organization": "Fair process", "psychology": "Procedural fairness"}),
        "tort": DomainConcept("tort", "Civil wrong causing harm", ("negligence", "intentional", "strict", "damages"), {"ethics": "Moral wrong", "sociology": "Social harm", "economics": "Economic damage"}),
        "constitutionalism": DomainConcept("constitutionalism", "Government limited by fundamental law", ("limitation", "rights", "separation", "review"), {"politics": "Constitutional democracy", "philosophy": "Rule of law", "organization": "Governance charters"}),
        "evidence": DomainConcept("evidence", "Information used to prove facts", ("testimony", "documentary", "physical", "burden"), {"science": "Scientific evidence", "philosophy": "Epistemic evidence", "psychology": "Evidence-based reasoning"}),
        "intellectual_property": DomainConcept("intellectual_property", "Legal rights over creations of the mind", ("patent", "copyright", "trademark", "trade_secret"), {"economics": "Knowledge economy", "ethics": "Ownership of ideas", "technology": "Tech IP strategy"}),
        "adversarial_system": DomainConcept("adversarial_system", "Legal process with opposing parties", ("prosecution", "defense", "judge", "jury"), {"debate": "Formal debate", "sports": "Competition", "science": "Adversarial collaboration"}),
        "regulation": DomainConcept("regulation", "Rule-making and enforcement by government", ("deregulation", "compliance", "oversight", "agency"), {"biology": "Homeostatic regulation", "engineering": "Control systems", "economics": "Market regulation"}),
        "restitution": DomainConcept("restitution", "Restoration of something lost or stolen", ("compensation", "remedy", "unjust_enrichment", "return"), {"ethics": "Moral restitution", "history": "Historical restitution", "economics": "Economic compensation"}),
    },
    fundamental_principles=["Rule of law", "Equality before the law", "Presumption of innocence", "Due process"],
    common_methods=["Statutory interpretation", "Case analysis", "Comparative law", "Legal reasoning"],
    units_of_analysis=["Case", "Statute", "Doctrine", "Jurisdiction"],
    abstraction_level=0.80,
    temporal_scale="case duration to legal tradition centuries",
    spatial_scale="local ordinance to international law",
))

_register_domain(KnowledgeDomain(
    name="medicine",
    category="applied_science",
    description="Science and practice of diagnosing, treating, and preventing disease",
    concepts={
        "pathology": DomainConcept("pathology", "Study of disease causes and effects", ("etiology", "morbidity", "mortality", "histology"), {"psychology": "Mental pathology", "sociology": "Social pathology", "computer_science": "System pathology"}),
        "diagnosis": DomainConcept("diagnosis", "Identification of disease from symptoms", ("differential", "prognosis", "symptom", "biomarker"), {"engineering": "Fault diagnosis", "computer_science": "Troubleshooting", "psychology": "Psychological assessment"}),
        "treatment": DomainConcept("treatment", "Medical care to cure or manage disease", ("therapy", "pharmacology", "surgery", "protocol"), {"psychology": "Psychotherapy", "education": "Educational intervention", "engineering": "Repair/treatment"}),
        "immunity": DomainConcept("immunity", "Body's defense against disease", ("antibody", "vaccine", "autoimmune", "herd"), {"law": "Legal immunity", "computer_science": "System immunity/resilience", "sociology": "Social immunity to misinformation"}),
        "homeostasis": DomainConcept("homeostasis", "Maintenance of stable internal environment", ("feedback", "equilibrium", "regulation", "balance"), {"economics": "Market homeostasis", "sociology": "Social stability", "engineering": "Control systems"}),
        "epidemiology": DomainConcept("epidemiology", "Study of disease patterns in populations", ("incidence", "prevalence", "outbreak", "transmission", "R0"), {"sociology": "Social epidemiology", "computer_science": "Virus propagation", "marketing": "Trend propagation"}),
        "etiology": DomainConcept("etiology", "Study of disease causation", ("cause", "risk_factor", "pathogen", "genetic"), {"history": "Historical causation", "philosophy": "Causality", "law": "Legal causation"}),
        "prognosis": DomainConcept("prognosis", "Predicted course of disease", ("outcome", "survival", "prediction", "forecast"), {"economics": "Economic prognosis", "meteorology": "Weather prognosis", "finance": "Financial forecast"}),
        "pharmacokinetics": DomainConcept("pharmacokinetics", "How body processes drugs", ("absorption", "distribution", "metabolism", "excretion"), {"environment": "Pollutant fate", "chemistry": "Reaction kinetics", "economics": "Resource distribution"}),
        "placebo": DomainConcept("placebo", "Inert substance producing real effects", ("nocebo", "expectation", "effect", "control"), {"psychology": "Expectation effects", "sociology": "Social placebo", "marketing": "Brand placebo effects"}),
        "syndrome": DomainConcept("syndrome", "Collection of symptoms characterizing a condition", ("symptom", "complex", "pattern", "cluster"), {"sociology": "Social syndrome", "psychology": "Behavioral syndrome", "meteorology": "Weather syndrome/pattern"}),
        "comorbidity": DomainConcept("comorbidity", "Presence of multiple simultaneous conditions", ("multimorbidity", "interaction", "polypharmacy", "overlap"), {"sociology": "Overlapping social problems", "economics": "Compound crises", "psychology": "Dual diagnosis"}),
    },
    fundamental_principles=["Primum non nocere (First do no harm)", "Evidence-based practice", "Holistic patient care", "Prevention is preferable to cure"],
    common_methods=["Clinical trials", "Diagnostic imaging", "Laboratory tests", "Epidemiological studies"],
    units_of_analysis=["Cell", "Organ", "Patient", "Population"],
    abstraction_level=0.70,
    temporal_scale="acute (hours) to chronic (decades)",
    spatial_scale="molecular to public health",
))

_register_domain(KnowledgeDomain(
    name="education",
    category="applied_science",
    description="Theory and practice of teaching and learning",
    concepts={
        "pedagogy": DomainConcept("pedagogy", "Method and practice of teaching", ("instruction", "andragogy", "curriculum", "assessment"), {"psychology": "Learning theory", "theater": "Directing/performance", "engineering": "System design"}),
        "curriculum": DomainConcept("curriculum", "Planned educational content and experiences", ("syllabus", "standards", "scope", "sequence"), {"architecture": "Blueprint", "computer_science": "Program structure", "music": "Musical program"}),
        "assessment": DomainConcept("assessment", "Evaluation of student learning", ("formative", "summative", "rubric", "feedback"), {"medicine": "Patient assessment", "business": "Performance review", "psychology": "Psychological testing"}),
        "scaffolding": DomainConcept("scaffolding", "Temporary support for learning new skills", ("Vygotsky", "ZPD", "support", "fade"), {"construction": "Building scaffolding", "psychology": "Cognitive support", "software": "Code scaffolding"}),
        "metacognition": DomainConcept("metacognition", "Thinking about one's own thinking", ("reflection", "self_regulation", "awareness", "monitoring"), {"AI": "Metacognitive AI", "psychology": "Self-awareness", "philosophy": "Self-reflection"}),
        "differentiation": DomainConcept("differentiation", "Tailoring instruction to individual needs", ("personalization", "adaptation", "diverse", "UDL"), {"mathematics": "Calculus differentiation", "biology": "Cellular differentiation", "business": "Market differentiation"}),
        "transfer": DomainConcept("transfer", "Applying learning to new contexts", ("near", "far", "positive", "negative"), {"physics": "Heat transfer", "economics": "Wealth transfer", "psychology": "Skill transfer"}),
        "motivation": DomainConcept("motivation", "Factors driving learning engagement", ("intrinsic", "extrinsic", "self_determination", "growth_mindset"), {"psychology": "Motivation theory", "economics": "Incentives", "biology": "Drives"}),
        "cognition": DomainConcept("cognition", "Mental processes involved in learning", ("memory", "attention", "perception", "reasoning"), {"computer_science": "Cognitive computing", "neuroscience": "Neural basis", "philosophy": "Philosophy of mind"}),
        "feedback": DomainConcept("feedback", "Information about performance to guide improvement", ("formative", "timely", "specific", "actionable"), {"engineering": "Control feedback", "biology": "Feedback loops", "communication": "Communication feedback"}),
        "inquiry": DomainConcept("inquiry", "Learning through questioning and investigation", ("discovery", "problem_based", "scientific_method", "curiosity"), {"science": "Scientific inquiry", "philosophy": "Philosophical inquiry", "journalism": "Investigative inquiry"}),
        "literacy": DomainConcept("literacy", "Ability to read, write, and comprehend", ("numeracy", "digital", "critical", "media"), {"computer_science": "Computer literacy", "sociology": "Cultural literacy", "economics": "Financial literacy"}),
    },
    fundamental_principles=["Learning is active construction", "Prior knowledge matters", "Social context shapes learning", "Assessment drives learning"],
    common_methods=["Direct instruction", "Inquiry-based learning", "Collaborative learning", "Formative assessment"],
    units_of_analysis=["Concept", "Skill", "Lesson", "Course", "Program"],
    abstraction_level=0.65,
    temporal_scale="lesson (minutes) to lifelong learning",
    spatial_scale="individual mind to education system",
))

_register_domain(KnowledgeDomain(
    name="engineering",
    category="applied_science",
    description="Application of scientific principles to design and build",
    concepts={
        "design": DomainConcept("design", "Process of creating specifications for systems", ("requirements", "iteration", "prototype", "optimization"), {"art": "Artistic design", "business": "Business design", "nature": "Evolutionary design"}),
        "feedback": DomainConcept("feedback", "Using output information to adjust input", ("control", "loop", "negative", "positive"), {"psychology": "Performance feedback", "biology": "Feedback inhibition", "communication": "Communication feedback"}),
        "efficiency": DomainConcept("efficiency", "Ratio of useful output to total input", ("optimization", "waste", "energy", "conversion"), {"economics": "Economic efficiency", "biology": "Metabolic efficiency", "physics": "Thermodynamic efficiency"}),
        "redundancy": DomainConcept("redundancy", "Duplication of critical components", ("fail_safe", "backup", "reliability", "N+1"), {"linguistics": "Informational redundancy", "biology": "Genetic redundancy", "communication": "Error correction"}),
        "scalability": DomainConcept("scalability", "Ability to handle growing workloads", ("scaling", "bottleneck", "performance", "load"), {"business": "Business scalability", "biology": "Scalable organisms", "architecture": "Scalable design"}),
        "modularity": DomainConcept("modularity", "Design with interchangeable components", ("interface", "module", "coupling", "cohesion"), {"biology": "Modular organisms", "sociology": "Modular society", "organization": "Team modules"}),
        "tolerance": DomainConcept("tolerance", "Permissible variation in dimensions", ("fit", "clearance", "precision", "stack_up"), {"sociology": "Social tolerance", "psychology": "Stress tolerance", "biology": "Environmental tolerance"}),
        "prototype": DomainConcept("prototype", "Early model for testing and learning", ("MVP", "iteration", "pilot", "mockup"), {"biology": "Evolutionary prototype", "software": "Software prototype", "psychology": "Cognitive prototype"}),
        "constraint": DomainConcept("constraint", "Limitation on design freedom", ("budget", "material", "regulatory", "performance"), {"mathematics": "Mathematical constraints", "optimization": "Constraint optimization", "physics": "Physical constraints"}),
        "safety_factor": DomainConcept("safety_factor", "Margin of strength above expected load", ("redundancy", "reliability", "risk", "margin"), {"finance": "Safety margin", "medicine": "Safety margin in dosing", "planning": "Buffer time"}),
        "signal": DomainConcept("signal", "Information-carrying quantity", ("noise", "processing", "filtering", "amplification"), {"biology": "Cell signaling", "economics": "Market signals", "communication": "Communication signals"}),
        "system": DomainConcept("system", "Set of interacting components forming whole", ("emergence", "boundary", "input", "output", "feedback"), {"biology": "Biological system", "sociology": "Social system", "ecology": "Ecosystem"}),
    },
    fundamental_principles=["Engineering is problem-solving", "Constraints define design", "Safety is paramount", "Iteration improves solutions"],
    common_methods=["Systems engineering", "FEA", "Prototyping", "Risk analysis", "Optimization"],
    units_of_analysis=["Component", "Subsystem", "System", "System of systems"],
    abstraction_level=0.60,
    temporal_scale="design hours to infrastructure decades",
    spatial_scale="microelectronic to civil engineering",
))


# ============================================================================
# Helper functions for cross-domain operations
# ============================================================================

def get_domains() -> Dict[str, KnowledgeDomain]:
    """Return all registered knowledge domains."""
    return dict(DOMAINS)


def _concept_to_vector(concept: DomainConcept) -> Dict[str, float]:
    """Convert a concept to a sparse feature vector for similarity."""
    features: Dict[str, float] = {}
    words = set(
        concept.name.lower().split("_")
        + concept.definition.lower().split()
        + [w for rc in concept.related_concepts for w in rc.lower().split("_")]
    )
    for w in words:
        features[w] = features.get(w, 0) + 1.0
    return features


def _cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    keys = set(v1.keys()) & set(v2.keys())
    if not keys:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in keys)
    norm1 = math.sqrt(sum(x * x for x in v1.values()))
    norm2 = math.sqrt(sum(x * x for x in v2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _find_concept_in_domain(concept_name: str, domain: KnowledgeDomain) -> Optional[DomainConcept]:
    """Find a concept by name (case-insensitive, partial match) in a domain."""
    concept_lower = concept_name.lower().replace(" ", "_")
    # Exact match
    if concept_lower in domain.concepts:
        return domain.concepts[concept_lower]
    # Partial match
    for key, concept in domain.concepts.items():
        if concept_lower in key or key in concept_lower:
            return concept
    return None



# ============================================================================
# SECTION 1c — ADDITIONAL DOMAINS BATCH 3 (remaining to reach 55+)
# ============================================================================

_register_domain(KnowledgeDomain(
    name="ecology",
    category="natural_science",
    description="Study of organisms and their environments",
    concepts={
        "niche": DomainConcept("niche", "Role and position of a species in an ecosystem", ("habitat", "resource", "competition", "partitioning"), {"economics": "Market niche", "sociology": "Social niche", "business": "Business niche"}),
        "succession": DomainConcept("succession", "Gradual change in ecosystem structure", ("pioneer", "climax", "disturbance", "recovery"), {"politics": "Political succession", "history": "Dynastic succession", "psychology": "Succession planning"}),
        "biodiversity": DomainConcept("biodiversity", "Variety of life at all levels", ("species", "genetic", "ecosystem", "hotspot"), {"economics": "Economic diversity", "sociology": "Cultural diversity", "technology": "Tech biodiversity"}),
        "food_web": DomainConcept("food_web", "Network of feeding relationships", ("trophic", "producer", "consumer", "decomposer"), {"economics": "Supply chain web", "sociology": "Social dependency web", "computer_science": "Dependency graph"}),
        "carrying_capacity": DomainConcept("carrying_capacity", "Maximum population an environment supports", ("limit", "population", "resources", "overshoot"), {"economics": "Market capacity", "infrastructure": "System capacity", "sociology": "Social carrying capacity"}),
        "keystone_species": DomainConcept("keystone_species", "Species with disproportionate ecosystem impact", ("engineer", "disproportionate", "removal", "collapse"), {"sociology": "Key influencers", "economics": "Systemically important firms", "technology": "Platform companies"}),
        "resilience": DomainConcept("resilience", "Ability to absorb disturbance and reorganize", ("stability", "adaptation", "recovery", "robustness"), {"psychology": "Psychological resilience", "engineering": "System resilience", "materials_science": "Material resilience"}),
        "biome": DomainConcept("biome", "Large ecological community type", ("climate", "vegetation", "tundra", "rainforest"), {"geography": "Geographic regions", "sociology": "Cultural biomes", "urban_planning": "Urban biomes"}),
        "invasive_species": DomainConcept("invasive_species", "Non-native species causing ecological harm", ("native", "competition", "predation", "spread"), {"economics": "Market invaders/disruptors", "sociology": "Cultural imperialism", "technology": "Disruptive technology"}),
    },
    fundamental_principles=["Ecosystems are interconnected", "Biodiversity matters", "Energy flows, matter cycles", "Humans are part of nature"],
    common_methods=["Field observation", "Modeling", "Remote sensing", "Experiments"],
    units_of_analysis=["Species", "Population", "Community", "Ecosystem", "Biome"],
    abstraction_level=0.60,
    temporal_scale="seasonal to evolutionary",
    spatial_scale="local patch to biosphere",
))
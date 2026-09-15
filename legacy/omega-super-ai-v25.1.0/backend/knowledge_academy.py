#!/usr/bin/env python3
"""
Omega Super AI -- Global Knowledge Academy
===========================================
A universal learning platform that ingests ALL global schools of thought into a
structured Knowledge Graph. Trains anyone from complete beginner to expert at
their own pace.

Features:
  1. Knowledge Graph        -- 11 disciplines, 55+ schools of thought
  2. Adaptive Learning      -- Personalized paths for any level
  3. Debate Simulator       -- Structured debates between schools
  4. Cross-Disciplinary     -- Bridges between fields
  5. Mastery Tracker        -- Progress tracking & quizzes
  6. Beginner-Friendly      -- ELI5, starter packs, study plans

Author    : Omega Super AI Research Division
License   : MIT
Version   : 1.0.0
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Omega Super AI Research Division"
__all__ = [
    "KNOWLEDGE_GRAPH", "get_discipline", "get_school", "search_schools",
    "list_disciplines", "get_knowledge_graph_stats", "search_across_all",
    "get_figure_profile", "assess_level", "generate_learning_path",
    "explain_concept", "get_lesson", "simulate_debate", "get_debate_topics",
    "compare_schools", "get_recommended_debate", "find_connections",
    "get_interdisciplinary_fields", "track_progress", "quiz_concept",
    "grade_quiz", "get_learning_analytics", "generate_revision_cards",
    "explain_like_im_five", "get_starter_pack", "generate_study_plan",
    "get_discipline_overview", "get_daily_challenge", "get_random_discovery",
    "get_curriculum_pathway", "export_student_report", "get_search_index",
    "register_student", "log_activity", "update_progress", "init_db", "get_db",
]

import json
import logging
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge_academy.db")

LEVELS = ["beginner", "intermediate", "advanced", "expert"]

PACE_LESSONS_PER_DAY = {"slow": 1, "medium": 3, "fast": 5}

# ═══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH -- 11 Disciplines, 55+ Schools of Thought
# ═══════════════════════════════════════════════════════════════════════════

KNOWLEDGE_GRAPH = {
    "epistemology": {
        "name": "Epistemology & Philosophy of Science",
        "icon": "🔍",
        "description": "The study of knowledge, belief, and justification -- how we know what we know.",
        "schools": [
            {
                "id": "empiricism",
                "name": "Empiricism",
                "founder": "John Locke",
                "core_axioms": [
                    "All knowledge originates from sensory experience",
                    "The mind at birth is a tabula rasa (blank slate)",
                    "Ideas come from impressions received through the senses",
                    "Scientific observation is the most reliable path to knowledge",
                    "Abstract concepts are built from accumulated experiences"
                ],
                "key_figures": ["John Locke", "David Hume", "George Berkeley", "Francis Bacon"],
                "opposing_schools": ["rationalism", "idealism"],
                "simulation_variables": {"evidence_weight": 0.9, "rational_weight": 0.1, "skepticism": 0.3},
                "historical_period": "17th-18th Century",
                "beginner_explanation": "Imagine a baby born knowing nothing. Everything the baby learns comes from seeing, hearing, touching, tasting, and smelling. Empiricists believe ALL human knowledge works this way -- we start as blank slates and fill them through experience.",
                "real_world_analogy": "Learning to cook by actually cooking (not just reading recipes). You learn what 'hot' means by touching something hot."
            },
            {
                "id": "rationalism",
                "name": "Rationalism",
                "founder": "René Descartes",
                "core_axioms": [
                    "Reason is the primary source of knowledge",
                    "Some ideas are innate -- present in the mind from birth",
                    "Mathematical and logical truths exist independently of experience",
                    "The senses can be deceived; reason provides certainty",
                    "Deductive reasoning from first principles reveals truth"
                ],
                "key_figures": ["René Descartes", "Gottfried Leibniz", "Baruch Spinoza"],
                "opposing_schools": ["empiricism", "skepticism"],
                "simulation_variables": {"evidence_weight": 0.1, "rational_weight": 0.9, "skepticism": 0.2},
                "historical_period": "17th Century",
                "beginner_explanation": "Have you ever just KNOWN something was true without needing to test it? Like 2+2=4 -- you don't need to count apples to know that. Rationalists believe our minds have built-in knowledge and the ability to reason things out through thinking alone.",
                "real_world_analogy": "Solving a puzzle in your head before trying the pieces. You can figure out the solution through pure reasoning."
            },
            {
                "id": "skepticism",
                "name": "Skepticism",
                "founder": "Pyrrho of Elis",
                "core_axioms": [
                    "Certain knowledge is impossible to attain",
                    "All claims should be questioned and examined",
                    "Suspension of judgment leads to tranquility",
                    "The senses and reason are both fallible",
                    "Dogmatic beliefs are the root of mental disturbance"
                ],
                "key_figures": ["Pyrrho of Elis", "David Hume", "Sextus Empiricus"],
                "opposing_schools": ["rationalism", "positivism"],
                "simulation_variables": {"evidence_weight": 0.5, "rational_weight": 0.5, "skepticism": 1.0},
                "historical_period": "4th Century BCE - Present",
                "beginner_explanation": "Have you ever been fooled by an optical illusion? Or believed something that turned out to be false? Skeptics say we should ALWAYS question everything because our senses and even our thinking can trick us.",
                "real_world_analogy": "A detective who questions every witness's story. Even if someone seems trustworthy, the detective checks the facts independently."
            },
            {
                "id": "positivism",
                "name": "Positivism",
                "founder": "Auguste Comte",
                "core_axioms": [
                    "Only scientifically verified facts constitute valid knowledge",
                    "Society progresses through three stages: theological, metaphysical, scientific",
                    "Social phenomena can be studied with scientific methods",
                    "Observation and experimentation are the only valid sources of knowledge",
                    "Value judgments have no place in scientific inquiry"
                ],
                "key_figures": ["Auguste Comte", "Ernst Mach", "Vienna Circle"],
                "opposing_schools": ["skepticism", "post_structuralism"],
                "simulation_variables": {"evidence_weight": 1.0, "rational_weight": 0.3, "skepticism": 0.1},
                "historical_period": "19th-20th Century",
                "beginner_explanation": "Positivists are like super-scientists. They believe that if you can't measure it, test it, or observe it, it's not real knowledge. If it can't be proven scientifically, it's just opinion.",
                "real_world_analogy": "A doctor who only trusts blood tests and X-rays, not a patient's feelings. The hard data is what matters."
            },
            {
                "id": "pragmatism",
                "name": "Pragmatism",
                "founder": "William James",
                "core_axioms": [
                    "The truth of an idea is measured by its practical consequences",
                    "Knowledge is a tool for solving problems and adapting to the environment",
                    "Reality is not fixed but shaped by our interactions with it",
                    "Beliefs are habits of action -- judge them by their results",
                    "There is no absolute truth; truth is what works in practice"
                ],
                "key_figures": ["William James", "John Dewey", "Charles Sanders Peirce", "Richard Rorty"],
                "opposing_schools": ["rationalism", "positivism"],
                "simulation_variables": {"evidence_weight": 0.7, "rational_weight": 0.4, "skepticism": 0.3},
                "historical_period": "Late 19th-20th Century",
                "beginner_explanation": "Does it WORK? That's what pragmatists care about most. They believe an idea is 'true' if it helps you navigate life better. It's not about perfect theories -- it's about what gets results.",
                "real_world_analogy": "Trying different routes to work. The 'true' best route is the one that gets you there fastest -- not the one that looks best on a map."
            }
        ]
    },
    "ethics": {
        "name": "Ethics & Moral Philosophy",
        "icon": "⚖️",
        "description": "The study of right and wrong -- how should we live and treat each other?",
        "schools": [
            {
                "id": "deontology",
                "name": "Deontology",
                "founder": "Immanuel Kant",
                "core_axioms": [
                    "Morality is based on absolute duties and rules",
                    "The ends never justify the means",
                    "Act only according to maxims you can will as universal law",
                    "Never treat people merely as means, always as ends",
                    "Moral worth comes from doing duty for duty's sake"
                ],
                "key_figures": ["Immanuel Kant", "W.D. Ross"],
                "opposing_schools": ["utilitarianism", "nihilism"],
                "simulation_variables": {"rule_flexibility": 0.0, "consequence_weight": 0.0, "individual_rights": 1.0},
                "historical_period": "18th Century",
                "beginner_explanation": "Some things are just WRONG, period. It doesn't matter if lying would help someone. Deontologists believe in absolute rules: never lie, never steal, never kill -- no matter the situation.",
                "real_world_analogy": "A parent who says 'no hitting' and sticks to it even if another kid started it. The rule is absolute."
            },
            {
                "id": "utilitarianism",
                "name": "Utilitarianism",
                "founder": "Jeremy Bentham",
                "core_axioms": [
                    "The morally right action maximizes overall happiness",
                    "All affected individuals' well-being counts equally",
                    "Consequences determine the moral value of actions",
                    "The principle of utility: greatest good for the greatest number",
                    "Pleasure and pain are the fundamental measures of value"
                ],
                "key_figures": ["Jeremy Bentham", "John Stuart Mill", "Peter Singer"],
                "opposing_schools": ["deontology", "virtue_ethics"],
                "simulation_variables": {"rule_flexibility": 0.9, "consequence_weight": 1.0, "individual_rights": 0.3},
                "historical_period": "18th-19th Century",
                "beginner_explanation": "What makes the most people happiest? That's what utilitarians ask. If lying would save 100 lives, they say lie! The outcome matters more than the rule.",
                "real_world_analogy": "A captain who sacrifices one lifeboat to save the whole ship. The greater good justifies the hard choice."
            },
            {
                "id": "virtue_ethics",
                "name": "Virtue Ethics",
                "founder": "Aristotle",
                "core_axioms": [
                    "Morality is about cultivating good character",
                    "Virtue is a habit disposed toward the good",
                    "The golden mean: virtue lies between excess and deficiency",
                    "Moral education develops practical wisdom (phronesis)",
                    "Eudaimonia (flourishing) is the ultimate goal of human life"
                ],
                "key_figures": ["Aristotle", "Thomas Aquinas", "Alasdair MacIntyre"],
                "opposing_schools": ["utilitarianism", "nihilism"],
                "simulation_variables": {"rule_flexibility": 0.5, "consequence_weight": 0.4, "individual_rights": 0.7},
                "historical_period": "4th Century BCE",
                "beginner_explanation": "Don't ask 'what's the right rule?' Ask 'what would a good person do?' Virtue ethics is about BECOMING a better person -- honest, brave, kind -- rather than following a checklist of rules.",
                "real_world_analogy": "A musician who practices daily not for a single concert, but to become a great musician. Character is built through habits over time."
            },
            {
                "id": "nihilism",
                "name": "Nihilism",
                "founder": "Friedrich Nietzsche",
                "core_axioms": [
                    "Objective moral values do not exist",
                    "Life has no inherent meaning or purpose",
                    "All religious, moral, and metaphysical beliefs are human constructions",
                    "Traditional values are obstacles to human potential",
                    "The individual must create their own values and meaning"
                ],
                "key_figures": ["Friedrich Nietzsche", "Ivan Turgenev"],
                "opposing_schools": ["deontology", "virtue_ethics", "stoicism"],
                "simulation_variables": {"rule_flexibility": 1.0, "consequence_weight": 0.5, "individual_rights": 1.0},
                "historical_period": "19th Century",
                "beginner_explanation": "Nihilists say nothing has built-in meaning. Not morality, not life, not the universe. It's not necessarily sad though -- it means YOU get to decide what matters.",
                "real_world_analogy": "A blank canvas. There's no picture already there -- you get to paint whatever you want. The meaning is what you create."
            },
            {
                "id": "stoicism",
                "name": "Stoicism",
                "founder": "Zeno of Citium",
                "core_axioms": [
                    "Virtue is the only true good",
                    "We cannot control external events, only our responses",
                    "Emotions stem from false judgments -- correct them",
                    "Live in accordance with nature and reason",
                    "Amor fati -- love of fate, embrace what happens"
                ],
                "key_figures": ["Marcus Aurelius", "Seneca", "Epictetus"],
                "opposing_schools": ["nihilism", "epicureanism"],
                "simulation_variables": {"rule_flexibility": 0.2, "consequence_weight": 0.3, "individual_rights": 0.8},
                "historical_period": "3rd Century BCE",
                "beginner_explanation": "You can't control the weather, traffic, or other people's actions. But you CAN control how you react. Stoics focus on their own responses and accept what they cannot change.",
                "real_world_analogy": "A surfer who can't control the waves but can control how they ride them. They don't get angry at the ocean -- they adapt."
            }
        ]
    },
    "political_theory": {
        "name": "Political & Social Theory",
        "icon": "🏛️",
        "description": "How should society be organized? What is the ideal form of government?",
        "schools": [
            {
                "id": "liberalism",
                "name": "Liberalism",
                "founder": "John Locke",
                "core_axioms": [
                    "Individual liberty is the highest political value",
                    "Government legitimacy derives from the consent of the governed",
                    "All people are equal before the law",
                    "Free markets and private property rights promote prosperity",
                    "Separation of powers prevents tyranny"
                ],
                "key_figures": ["John Locke", "John Stuart Mill", "John Rawls"],
                "opposing_schools": ["marxism", "fascism"],
                "simulation_variables": {"individual_freedom": 0.9, "state_power": 0.2, "economic_control": 0.1},
                "historical_period": "17th Century - Present",
                "beginner_explanation": "Everyone should be free to live their life as they choose, as long as they don't hurt others. Government should protect your rights but stay out of your personal business.",
                "real_world_analogy": "A neighborhood where each family decorates their house however they want, but there's a small police force to stop theft and violence."
            },
            {
                "id": "marxism",
                "name": "Marxism",
                "founder": "Karl Marx",
                "core_axioms": [
                    "History is driven by class struggle over the means of production",
                    "Capitalism inherently exploits workers by extracting surplus value",
                    "Private property of the means of production should be abolished",
                    "The proletariat must overthrow the bourgeoisie",
                    "Ultimate goal: a classless, stateless communist society"
                ],
                "key_figures": ["Karl Marx", "Friedrich Engels", "Vladimir Lenin"],
                "opposing_schools": ["liberalism", "anarchism"],
                "simulation_variables": {"individual_freedom": 0.3, "state_power": 0.9, "economic_control": 1.0},
                "historical_period": "19th Century",
                "beginner_explanation": "Workers create all the value but bosses keep most of the profit. Marxists believe this is unfair and want workers to own and control the businesses they work in.",
                "real_world_analogy": "A bakery where all bakers equally own the bakery and share all profits, instead of one owner keeping most while paying workers minimum wage."
            },
            {
                "id": "fascism",
                "name": "Fascism",
                "founder": "Giovanni Gentile",
                "core_axioms": [
                    "The nation or race is the supreme collective entity",
                    "Totalitarian state control over all aspects of society",
                    "Rejection of individualism and liberal democracy",
                    "Cult of the leader (Führerprinzip)",
                    "Glorification of violence, war, and military strength"
                ],
                "key_figures": ["Giovanni Gentile", "Benito Mussolini"],
                "opposing_schools": ["liberalism", "anarchism", "marxism"],
                "simulation_variables": {"individual_freedom": 0.0, "state_power": 1.0, "economic_control": 0.8},
                "historical_period": "20th Century",
                "beginner_explanation": "The nation comes first, individuals come second. Fascists believe a strong leader and a unified national identity are more important than personal freedoms.",
                "real_world_analogy": "A sports team where the coach makes every decision and players must obey without question -- team loyalty above all."
            },
            {
                "id": "anarchism",
                "name": "Anarchism",
                "founder": "Mikhail Bakunin",
                "core_axioms": [
                    "All involuntary hierarchy should be abolished",
                    "The state is inherently oppressive and should be eliminated",
                    "Voluntary cooperation and mutual aid can replace government",
                    "Individuals should be free from all forms of domination",
                    "Direct action and self-organization are preferred methods"
                ],
                "key_figures": ["Mikhail Bakunin", "Pierre-Joseph Proudhon", "Peter Kropotkin"],
                "opposing_schools": ["liberalism", "fascism", "marxism"],
                "simulation_variables": {"individual_freedom": 1.0, "state_power": 0.0, "economic_control": 0.0},
                "historical_period": "19th Century",
                "beginner_explanation": "No government at all! Anarchists believe people can organize themselves through voluntary cooperation without any rulers or laws.",
                "real_world_analogy": "A potluck dinner where everyone brings food to share voluntarily. No one is forced, but everyone benefits."
            },
            {
                "id": "realism",
                "name": "Realism",
                "founder": "Niccolò Machiavelli",
                "core_axioms": [
                    "States operate based on rational self-interest and power",
                    "The international system is anarchic -- no overarching authority",
                    "Moral principles do not guide state behavior",
                    "States seek power and security above all else",
                    "Conflict is inherent in international relations"
                ],
                "key_figures": ["Niccolò Machiavelli", "Hans Morgenthau", "Kenneth Waltz"],
                "opposing_schools": ["liberalism", "idealism"],
                "simulation_variables": {"individual_freedom": 0.4, "state_power": 0.9, "economic_control": 0.3},
                "historical_period": "16th Century - Present",
                "beginner_explanation": "Countries are like players in a game with no referee. Each country looks out for itself. Trust and friendship don't matter as much as power and survival.",
                "real_world_analogy": "A poker game where every player bluffs and strategizes to win. There's no 'fair' -- only what advances your position."
            }
        ]
    },
    "economics": {
        "name": "Macroeconomics & Economic Theory",
        "icon": "💰",
        "description": "How do markets, money, and economies work at the national and global scale?",
        "schools": [
            {
                "id": "classical_economics",
                "name": "Classical Economics",
                "founder": "Adam Smith",
                "core_axioms": [
                    "Markets self-correct through supply and demand",
                    "The 'invisible hand' guides individuals to promote public good",
                    "Free trade benefits all participating nations",
                    "Say's Law: supply creates its own demand",
                    "Government intervention should be minimal"
                ],
                "key_figures": ["Adam Smith", "David Ricardo", "Jean-Baptiste Say"],
                "opposing_schools": ["keynesianism", "marxism"],
                "simulation_variables": {"government_intervention": 0.1, "market_freedom": 1.0, "trade_barriers": 0.0},
                "historical_period": "18th-19th Century",
                "beginner_explanation": "If you leave people alone to buy and sell freely, everything works out. Like magic! Prices adjust naturally. Government should just stay out of the way.",
                "real_world_analogy": "A farmers market with no rules. Sellers set their own prices, buyers choose freely, and somehow everyone gets what they need."
            },
            {
                "id": "keynesianism",
                "name": "Keynesian Economics",
                "founder": "John Maynard Keynes",
                "core_axioms": [
                    "Aggregate demand drives economic output",
                    "Wages and prices are sticky in the short run",
                    "Government intervention can stabilize the business cycle",
                    "During recessions, governments should spend to boost demand",
                    "Deficit spending in bad times; surplus in good times"
                ],
                "key_figures": ["John Maynard Keynes", "Paul Samuelson", "Joan Robinson"],
                "opposing_schools": ["austrian_school", "monetarism"],
                "simulation_variables": {"government_intervention": 0.8, "market_freedom": 0.5, "trade_barriers": 0.2},
                "historical_period": "20th Century (Post-1936)",
                "beginner_explanation": "When the economy is in a recession, the government should step in and spend money to create jobs. It's like pushing a stalled car to get it moving again.",
                "real_world_analogy": "When a restaurant is empty, the owner offers a discount to attract customers. The government does the same for the whole economy."
            },
            {
                "id": "monetarism",
                "name": "Monetarism",
                "founder": "Milton Friedman",
                "core_axioms": [
                    "The money supply is the primary driver of economic activity",
                    "Inflation is always and everywhere a monetary phenomenon",
                    "Central banks should target stable money supply growth",
                    "Government spending is less effective than monetary policy",
                    "Free markets work; government intervention usually fails"
                ],
                "key_figures": ["Milton Friedman", "Anna Schwartz"],
                "opposing_schools": ["keynesianism", "austrian_school"],
                "simulation_variables": {"government_intervention": 0.2, "market_freedom": 0.8, "trade_barriers": 0.1},
                "historical_period": "20th Century",
                "beginner_explanation": "Money matters! If there's too much money floating around, prices go up (inflation). If there's too little, the economy slows down. Central banks should carefully control the money supply.",
                "real_world_analogy": "Like controlling water pressure in a building. Too much pressure = burst pipes (inflation). Too little = weak flow (recession)."
            },
            {
                "id": "austrian_school",
                "name": "Austrian School",
                "founder": "Carl Menger",
                "core_axioms": [
                    "Individual choices and subjective value drive economies",
                    "Rejects mathematical modeling of human behavior",
                    "Free markets allocate resources most efficiently",
                    "Business cycles are caused by central bank manipulation",
                    "Government intervention causes malinvestment"
                ],
                "key_figures": ["Carl Menger", "Ludwig von Mises", "Friedrich Hayek"],
                "opposing_schools": ["keynesianism", "monetarism"],
                "simulation_variables": {"government_intervention": 0.0, "market_freedom": 1.0, "trade_barriers": 0.0},
                "historical_period": "Late 19th Century - Present",
                "beginner_explanation": "Only individuals know what's best for themselves. Government planners can't possibly know enough to make good economic decisions. Let everyone choose freely.",
                "real_world_analogy": "A crowd-sourced navigation app. Millions of individual decisions create the best traffic flow -- no central planner needed."
            },
            {
                "id": "institutional_economics",
                "name": "Institutional Economics",
                "founder": "Thorstein Veblen",
                "core_axioms": [
                    "Economic behavior is embedded in social and cultural institutions",
                    "Evolutionary social frameworks shape economic outcomes",
                    "Power dynamics and vested interests influence policy",
                    "Technological change drives institutional evolution",
                    "Economic analysis must include sociological factors"
                ],
                "key_figures": ["Thorstein Veblen", "John Commons", "Douglass North"],
                "opposing_schools": ["classical_economics", "austrian_school"],
                "simulation_variables": {"government_intervention": 0.5, "market_freedom": 0.4, "trade_barriers": 0.3},
                "historical_period": "Early 20th Century",
                "beginner_explanation": "Economies don't exist in a vacuum. Laws, culture, habits, and institutions all shape how economies work. Understanding economics means understanding society.",
                "real_world_analogy": "Like understanding traffic by looking at road design, driving culture, and law enforcement -- not just counting cars."
            }
        ]
    },
    "psychology": {
        "name": "Psychology & Cognitive Science",
        "icon": "🧠",
        "description": "How does the mind work? What drives human behavior and thought?",
        "schools": [
            {
                "id": "psychoanalysis",
                "name": "Psychoanalysis",
                "founder": "Sigmund Freud",
                "core_axioms": [
                    "Unconscious desires drive most human behavior",
                    "Childhood experiences shape adult personality",
                    "The psyche consists of id, ego, and superego",
                    "Defense mechanisms protect the ego from anxiety",
                    "Free association and dream analysis reveal the unconscious"
                ],
                "key_figures": ["Sigmund Freud", "Carl Jung", "Jacques Lacan"],
                "opposing_schools": ["behaviorism", "cognitive_psychology"],
                "simulation_variables": {"conscious_control": 0.1, "environmental_influence": 0.3, "biology_weight": 0.2},
                "historical_period": "Late 19th Century",
                "beginner_explanation": "Most of what drives your behavior is hidden from you -- buried deep in your unconscious mind. Your childhood, secret desires, and repressed memories control you more than you realize.",
                "real_world_analogy": "An iceberg. The small tip above water is your conscious mind. The massive underwater part is your unconscious -- where the real action happens."
            },
            {
                "id": "behaviorism",
                "name": "Behaviorism",
                "founder": "John B. Watson",
                "core_axioms": [
                    "Psychology should study only observable behavior",
                    "All behavior is learned through conditioning",
                    "Classical conditioning: stimulus-response associations",
                    "Operant conditioning: reinforcement and punishment shape behavior",
                    "Internal mental states are irrelevant to scientific study"
                ],
                "key_figures": ["John B. Watson", "B.F. Skinner", "Ivan Pavlov"],
                "opposing_schools": ["psychoanalysis", "humanistic_psychology"],
                "simulation_variables": {"conscious_control": 0.0, "environmental_influence": 1.0, "biology_weight": 0.0},
                "historical_period": "Early 20th Century",
                "beginner_explanation": "Don't worry about thoughts and feelings -- just look at behavior. If you can see it and measure it, you can change it through rewards and punishments.",
                "real_world_analogy": "Training a dog. Give a treat when they sit, they sit more. Ignore bad behavior, it goes away. Same principle works on humans."
            },
            {
                "id": "cognitive_psychology",
                "name": "Cognitive Psychology",
                "founder": "Ulric Neisser",
                "core_axioms": [
                    "The mind is an information-processing system",
                    "Mental processes (attention, memory, perception) can be studied scientifically",
                    "The brain is like a computer -- input, process, output",
                    "Cognitive schemas organize knowledge and guide behavior",
                    "Mental representations mediate between stimulus and response"
                ],
                "key_figures": ["Ulric Neisser", "Jean Piaget", "Noam Chomsky"],
                "opposing_schools": ["behaviorism", "psychoanalysis"],
                "simulation_variables": {"conscious_control": 0.7, "environmental_influence": 0.4, "biology_weight": 0.5},
                "historical_period": "1950s - Present",
                "beginner_explanation": "Your brain is like a computer. It takes in information, processes it, stores it, and outputs decisions. Understanding these mental programs helps us understand behavior.",
                "real_world_analogy": "Like a smartphone: camera captures input, apps process it, memory stores it, and you get an output. Same idea for your brain."
            },
            {
                "id": "humanistic_psychology",
                "name": "Humanistic Psychology",
                "founder": "Carl Rogers",
                "core_axioms": [
                    "Humans have an innate drive toward self-actualization",
                    "Free will and personal agency are central to human nature",
                    "Psychology should focus on the whole person, not disorders",
                    "Unconditional positive regard fosters growth",
                    "Subjective experience is the most important data"
                ],
                "key_figures": ["Carl Rogers", "Abraham Maslow", "Rollo May"],
                "opposing_schools": ["behaviorism", "psychoanalysis"],
                "simulation_variables": {"conscious_control": 0.9, "environmental_influence": 0.3, "biology_weight": 0.2},
                "historical_period": "1950s - Present",
                "beginner_explanation": "People are basically good and want to become the best version of themselves. Psychology should help you grow, not just fix problems. You have the power to choose your own path.",
                "real_world_analogy": "A gardener who tends a plant with water, sunlight, and good soil. The plant naturally grows toward the sun -- the gardener just creates the right conditions."
            },
            {
                "id": "evolutionary_psychology",
                "name": "Evolutionary Psychology",
                "founder": "Leda Cosmides",
                "core_axioms": [
                    "Mental traits are adaptations shaped by natural selection",
                    "The mind consists of domain-specific modules evolved to solve problems",
                    "Human behavior reflects ancestral adaptive challenges",
                    "Sexual selection explains mating strategies",
                    "Evolutionary pressures shaped social behavior and cooperation"
                ],
                "key_figures": ["Leda Cosmides", "David Buss", "Steven Pinker"],
                "opposing_schools": ["behaviorism", "humanistic_psychology"],
                "simulation_variables": {"conscious_control": 0.3, "environmental_influence": 0.2, "biology_weight": 1.0},
                "historical_period": "1980s - Present",
                "beginner_explanation": "Why do we think and act the way we do? Because our ancestors who thought that way survived and had babies. Evolution shaped our minds over millions of years.",
                "real_world_analogy": "Like a shark's streamlined body evolved for hunting in water. Our minds evolved tools for surviving in social groups, finding food, and attracting mates."
            }
        ]
    },
    "eastern_philosophy": {
        "name": "Eastern Philosophy & Spirituality",
        "icon": "☯️",
        "description": "Ancient wisdom traditions from Asia -- harmony, balance, and inner peace.",
        "schools": [
            {
                "id": "confucianism",
                "name": "Confucianism",
                "founder": "Confucius (Kong Fuzi)",
                "core_axioms": [
                    "Social harmony through proper relationships and rituals (li)",
                    "Filial piety and respect for elders is the foundation of morality",
                    "The junzi (gentleman/person of virtue) leads by moral example",
                    "Education and self-cultivation transform both individual and society",
                    "Ren (benevolence/humaneness) is the highest virtue"
                ],
                "key_figures": ["Confucius", "Mencius", "Xunzi"],
                "opposing_schools": ["legalism", "mohism"],
                "simulation_variables": {"individual_focus": 0.2, "social_harmony": 1.0, "spirituality": 0.3},
                "historical_period": "6th Century BCE",
                "beginner_explanation": "Be good to your family, respect your elders, learn constantly, and treat others well. Confucius believed that if everyone did their role properly, society would be peaceful.",
                "real_world_analogy": "A family dinner where everyone has a role: parents cook, children set the table, grandparents share wisdom. Respect and harmony make it work."
            },
            {
                "id": "taoism",
                "name": "Taoism",
                "founder": "Lao Tzu",
                "core_axioms": [
                    "The Tao (Way) is the natural order of the universe",
                    "Wu wei -- effortless action in harmony with the Tao",
                    "Simplicity, humility, and non-interference lead to harmony",
                    "Yin and yang represent complementary opposites in balance",
                    "The soft overcomes the hard; the flexible overcomes the rigid"
                ],
                "key_figures": ["Lao Tzu", "Zhuangzi"],
                "opposing_schools": ["legalism", "confucianism"],
                "simulation_variables": {"individual_focus": 0.8, "social_harmony": 0.5, "spirituality": 1.0},
                "historical_period": "6th Century BCE",
                "beginner_explanation": "Go with the flow! Taoism teaches that forcing things creates problems. Instead, align yourself with the natural way of the universe. Be like water -- soft but unstoppable.",
                "real_world_analogy": "A river flowing around rocks. It doesn't fight or force -- it finds the easiest path. Over time, it carves canyons through the hardest stone."
            },
            {
                "id": "buddhism",
                "name": "Buddhism",
                "founder": "Siddhartha Gautama (The Buddha)",
                "core_axioms": [
                    "Life is suffering (dukkha); suffering is caused by attachment",
                    "The Four Noble Truths diagnose and prescribe the end of suffering",
                    "The Eightfold Path leads to liberation (nirvana)",
                    "Anatta (no-self): there is no permanent, unchanging self",
                    "Impermanence: all things arise and pass away"
                ],
                "key_figures": ["Siddhartha Gautama", "Nagarjuna", "Thich Nhat Hanh"],
                "opposing_schools": ["hinduism", "materialism"],
                "simulation_variables": {"individual_focus": 0.7, "social_harmony": 0.6, "spirituality": 1.0},
                "historical_period": "6th Century BCE",
                "beginner_explanation": "Suffering comes from wanting things to be different than they are. Buddhism teaches meditation and mindfulness to let go of attachments and find inner peace.",
                "real_world_analogy": "Holding a burning coal. The longer you grip it, the more it hurts. Letting go is the relief. Buddhism teaches you how to let go."
            },
            {
                "id": "legalism",
                "name": "Legalism",
                "founder": "Han Feizi",
                "core_axioms": [
                    "Human nature is inherently selfish and must be controlled",
                    "Strict laws and harsh punishments maintain social order",
                    "The ruler must use power, not virtue, to govern",
                    "State strength is the supreme value; individual welfare is secondary",
                    "Two handles of state: reward and punishment"
                ],
                "key_figures": ["Han Feizi", "Shang Yang", "Li Si"],
                "opposing_schools": ["confucianism", "taoism"],
                "simulation_variables": {"individual_focus": 0.0, "social_harmony": 0.3, "spirituality": 0.0},
                "historical_period": "3rd Century BCE",
                "beginner_explanation": "People are naturally selfish and will break rules if they can get away with it. Legalists believe only strict laws and harsh punishments can keep order.",
                "real_world_analogy": "A strict teacher who gives detention for every rule broken. Fear of punishment keeps the classroom orderly."
            },
            {
                "id": "mohism",
                "name": "Mohism",
                "founder": "Mozi",
                "core_axioms": [
                    "Universal, impartial love (jian ai) should replace favoritism",
                    "State action should be evaluated by its consequences for all",
                    "Opposition to aggressive warfare; promotion of defensive peace",
                    "Frugality and simplicity in rituals and government",
                    "Meritocracy: promote based on ability, not birth"
                ],
                "key_figures": ["Mozi"],
                "opposing_schools": ["confucianism", "legalism"],
                "simulation_variables": {"individual_focus": 0.5, "social_harmony": 0.9, "spirituality": 0.4},
                "historical_period": "5th Century BCE",
                "beginner_explanation": "Love everyone equally -- not just your family but strangers too. Mozi believed that favoring your own family over others causes conflict. Treat everyone with equal care.",
                "real_world_analogy": "A firefighter who saves lives without asking whose family the person belongs to. Every life matters equally."
            }
        ]
    },
    "sociology": {
        "name": "Sociology & Social Theory",
        "icon": "🌍",
        "description": "How do societies function? What binds people together or tears them apart?",
        "schools": [
            {
                "id": "structural_functionalism",
                "name": "Structural Functionalism",
                "founder": "Émile Durkheim",
                "core_axioms": [
                    "Society is a complex system whose parts work together",
                    "Each social institution serves a function for the whole",
                    "Social cohesion and shared values maintain order",
                    "Dysfunction in one part affects the entire system",
                    "Social facts exist independently of individuals"
                ],
                "key_figures": ["Émile Durkheim", "Talcott Parsons", "Robert Merton"],
                "opposing_schools": ["conflict_theory", "symbolic_interactionism"],
                "simulation_variables": {"social_order": 0.9, "individual_agency": 0.2, "power_focus": 0.1},
                "historical_period": "Late 19th Century",
                "beginner_explanation": "Society is like a human body. The heart, lungs, brain all work together. Schools, families, government, religion -- each plays a role in keeping society healthy.",
                "real_world_analogy": "A watch with many gears. Each gear has a job. If one breaks, the whole watch stops working properly."
            },
            {
                "id": "conflict_theory",
                "name": "Conflict Theory",
                "founder": "Karl Marx",
                "core_axioms": [
                    "Society is structured by competition over limited resources",
                    "Dominant groups maintain power through ideology and institutions",
                    "Social change arises from conflict between groups",
                    "Power imbalances are inherent in all social structures",
                    "Class, race, and gender are primary axes of inequality"
                ],
                "key_figures": ["Karl Marx", "Max Weber", "C. Wright Mills"],
                "opposing_schools": ["structural_functionalism", "symbolic_interactionism"],
                "simulation_variables": {"social_order": 0.2, "individual_agency": 0.4, "power_focus": 1.0},
                "historical_period": "19th Century",
                "beginner_explanation": "Society is a battlefield where powerful groups exploit weaker ones. Rich vs poor, men vs women, dominant race vs minorities. Change only happens when the oppressed fight back.",
                "real_world_analogy": "A game of Monopoly where some players start with hotels already built. The game is rigged from the start."
            },
            {
                "id": "symbolic_interactionism",
                "name": "Symbolic Interactionism",
                "founder": "George Herbert Mead",
                "core_axioms": [
                    "Reality is socially constructed through everyday interactions",
                    "Symbols and language create shared meaning",
                    "The self emerges through social interaction",
                    "Micro-level interactions shape macro-level society",
                    "Subjective interpretation matters more than objective structure"
                ],
                "key_figures": ["George Herbert Mead", "Herbert Blumer", "Erving Goffman"],
                "opposing_schools": ["structural_functionalism", "conflict_theory"],
                "simulation_variables": {"social_order": 0.4, "individual_agency": 1.0, "power_focus": 0.2},
                "historical_period": "Early 20th Century",
                "beginner_explanation": "Society is built from countless tiny interactions every day. A smile, a handshake, a text message -- these create the social world. Meaning comes from how we interpret things together.",
                "real_world_analogy": "A dance where partners constantly adjust to each other. The dance emerges from each small step -- no single person controls it."
            },
            {
                "id": "post_structuralism",
                "name": "Post-Structuralism",
                "founder": "Michel Foucault",
                "core_axioms": [
                    "Language and discourse construct reality; nothing is objective",
                    "Power operates through knowledge and discourse",
                    "There is no fixed human nature or universal truth",
                    "Identity is fluid and performed, not essential",
                    "Binary oppositions (male/female, rational/emotional) are artificial"
                ],
                "key_figures": ["Michel Foucault", "Jacques Derrida", "Judith Butler"],
                "opposing_schools": ["structural_functionalism", "positivism"],
                "simulation_variables": {"social_order": 0.1, "individual_agency": 0.9, "power_focus": 1.0},
                "historical_period": "Late 20th Century",
                "beginner_explanation": "Nothing is 'natural' or 'just the way things are.' Everything we believe is shaped by language, culture, and power. Categories like 'man' and 'woman' are constructed, not given.",
                "real_world_analogy": "A movie set. The buildings look real but they're just facades. The 'reality' you see is constructed -- behind it is scaffolding and wires."
            },
            {
                "id": "functionalism_anthropology",
                "name": "Functionalism (Anthropology)",
                "founder": "Bronisław Malinowski",
                "core_axioms": [
                    "Cultural practices exist to satisfy biological or psychological needs",
                    "Every custom, belief, and institution serves a function",
                    "Cultural traits should be understood in their social context",
                    "Fieldwork and participant observation are essential methods",
                    "Universal human needs create similar cultural patterns"
                ],
                "key_figures": ["Bronisław Malinowski", "A.R. Radcliffe-Brown"],
                "opposing_schools": ["post_structuralism", "conflict_theory"],
                "simulation_variables": {"social_order": 0.7, "individual_agency": 0.3, "power_focus": 0.2},
                "historical_period": "Early 20th Century",
                "beginner_explanation": "Why do different cultures do things differently? Functionalists say every practice -- even ones that seem strange -- exists for a reason. It fulfills a human need.",
                "real_world_analogy": "Like finding out a 'weird' family tradition exists because it brings everyone together once a year. There's always a purpose behind the practice."
            }
        ]
    },
    "physics": {
        "name": "Physics & Cosmology",
        "icon": "⚛️",
        "description": "How does the universe work? From atoms to galaxies.",
        "schools": [
            {
                "id": "classical_mechanics",
                "name": "Classical Mechanics",
                "founder": "Isaac Newton",
                "core_axioms": [
                    "The universe is deterministic and governed by absolute laws",
                    "Newton's three laws of motion describe all mechanical phenomena",
                    "Gravity is a force acting at a distance between masses",
                    "Space and time are absolute and independent",
                    "Energy is conserved; momentum is conserved"
                ],
                "key_figures": ["Isaac Newton", "Galileo Galilei", "Johannes Kepler"],
                "opposing_schools": ["quantum_mechanics", "relativity"],
                "simulation_variables": {"determinism": 1.0, "scale": "macroscopic", "certainty": 1.0},
                "historical_period": "17th Century",
                "beginner_explanation": "Everything in the universe moves according to predictable rules. If you know where something is and how fast it's going, you can predict exactly where it'll be tomorrow. Like clockwork.",
                "real_world_analogy": "A pool table. If you know the exact angle and force of your shot, you can predict where every ball will end up."
            },
            {
                "id": "relativity",
                "name": "Relativity (Einsteinian)",
                "founder": "Albert Einstein",
                "core_axioms": [
                    "Space and time are a single fabric (spacetime)",
                    "Mass and energy warp spacetime, causing gravity",
                    "The speed of light is constant for all observers",
                    "Time slows and space contracts at high velocities",
                    "E=mc²: mass and energy are equivalent"
                ],
                "key_figures": ["Albert Einstein", "Hermann Minkowski"],
                "opposing_schools": ["classical_mechanics"],
                "simulation_variables": {"determinism": 0.8, "scale": "cosmic", "certainty": 0.9},
                "historical_period": "20th Century",
                "beginner_explanation": "Time is not the same for everyone! If you travel near the speed of light, time slows down for you. And gravity isn't a force -- it's the bending of space itself.",
                "real_world_analogy": "A bowling ball on a trampoline. The ball makes a dent. Roll a marble nearby and it curves toward the ball. That's gravity -- space itself is curved."
            },
            {
                "id": "quantum_mechanics",
                "name": "Quantum Mechanics",
                "founder": "Niels Bohr",
                "core_axioms": [
                    "The universe is probabilistic at the subatomic level",
                    "Wave-particle duality: matter behaves as both wave and particle",
                    "Heisenberg Uncertainty Principle: you can't know everything precisely",
                    "Quantum superposition: particles exist in multiple states simultaneously",
                    "Quantum entanglement: particles can be connected across any distance"
                ],
                "key_figures": ["Niels Bohr", "Werner Heisenberg", "Erwin Schrödinger", "Max Planck"],
                "opposing_schools": ["classical_mechanics"],
                "simulation_variables": {"determinism": 0.0, "scale": "subatomic", "certainty": 0.0},
                "historical_period": "20th Century",
                "beginner_explanation": "At the tiny scale of atoms, reality gets weird. Particles can be in two places at once. You can never be 100% certain about anything. The universe is fundamentally fuzzy.",
                "real_world_analogy": "A coin spinning in the air. While spinning, it's neither heads nor tails -- it's both. Only when it lands (is measured) does it 'choose' a side."
            },
            {
                "id": "string_theory",
                "name": "String Theory",
                "founder": "Edward Witten",
                "core_axioms": [
                    "Subatomic particles are tiny vibrating strings, not points",
                    "Different vibrations produce different particles",
                    "Requires 10 or 11 dimensions of spacetime",
                    "Unifies general relativity with quantum mechanics",
                    "Supersymmetry connects bosons and fermions"
                ],
                "key_figures": ["Edward Witten", "Leonard Susskind"],
                "opposing_schools": ["loop_quantum_gravity"],
                "simulation_variables": {"determinism": 0.5, "scale": "planck", "certainty": 0.3},
                "historical_period": "1980s - Present",
                "beginner_explanation": "Everything in the universe -- every particle, every force -- is made of tiny vibrating strings. Like different notes on a violin string creating different sounds, different vibrations create different particles.",
                "real_world_analogy": "A violin. One string can play many notes depending on how it vibrates. Similarly, one tiny string can be an electron, a photon, or a quark depending on its vibration."
            },
            {
                "id": "loop_quantum_gravity",
                "name": "Loop Quantum Gravity",
                "founder": "Carlo Rovelli",
                "core_axioms": [
                    "Spacetime is not continuous but quantized into discrete loops",
                    "Space is made of tiny, interwoven loops at the Planck scale",
                    "No need for extra dimensions beyond the four we observe",
                    "Background-independent: space itself is dynamical",
                    "Black holes have entropy proportional to their surface area"
                ],
                "key_figures": ["Carlo Rovelli", "Lee Smolin"],
                "opposing_schools": ["string_theory"],
                "simulation_variables": {"determinism": 0.6, "scale": "planck", "certainty": 0.4},
                "historical_period": "1980s - Present",
                "beginner_explanation": "Space itself is made of tiny loops woven together like a fabric. It looks smooth to us, but if you zoom in enough, you'd see individual threads. No extra dimensions needed.",
                "real_world_analogy": "A woven basket. From far away it looks smooth. Up close you see individual loops of fiber woven together. Space is the same."
            }
        ]
    },
    "biology": {
        "name": "Biology & Evolutionary Science",
        "icon": "🧬",
        "description": "How does life work and evolve? From genes to ecosystems.",
        "schools": [
            {
                "id": "darwinism",
                "name": "Darwinism",
                "founder": "Charles Darwin",
                "core_axioms": [
                    "Species evolve over generations through natural selection",
                    "Variation exists within populations; some traits aid survival",
                    "Those with advantageous traits survive and reproduce more",
                    "Over time, populations adapt to their environments",
                    "All life on Earth shares common ancestry"
                ],
                "key_figures": ["Charles Darwin", "Alfred Russel Wallace"],
                "opposing_schools": ["lamarckism", "creationism"],
                "simulation_variables": {"selection_pressure": 0.8, "mutation_rate": 0.1, "adaptation_speed": "slow"},
                "historical_period": "19th Century",
                "beginner_explanation": "Over many generations, animals and plants that have helpful traits survive better and have more babies. Slowly, the whole group changes. That's how new species are formed.",
                "real_world_analogy": "A dog breeder who only breeds the fastest dogs. Over generations, the whole line becomes faster. Nature does the same, but without a plan."
            },
            {
                "id": "modern_synthesis",
                "name": "Modern Synthesis",
                "founder": "Ernst Mayr",
                "core_axioms": [
                    "Natural selection + Mendelian genetics + molecular biology",
                    "Mutations in DNA create genetic variation",
                    "Genetic drift causes random changes in small populations",
                    "Gene flow between populations maintains genetic similarity",
                    "Speciation occurs through reproductive isolation"
                ],
                "key_figures": ["Ernst Mayr", "Theodosius Dobzhansky", "J.B.S. Haldane"],
                "opposing_schools": ["darwinism (as incomplete)"],
                "simulation_variables": {"selection_pressure": 0.7, "mutation_rate": 0.3, "adaptation_speed": "moderate"},
                "historical_period": "1940s",
                "beginner_explanation": "Darwin was right about natural selection, but he didn't know about genes. The Modern Synthesis combines Darwin's ideas with genetics -- showing exactly HOW traits are passed on through DNA.",
                "real_world_analogy": "Like combining a recipe book (genes) with a cooking competition (natural selection). The recipes mutate slightly, and the best dishes win."
            },
            {
                "id": "epigenetics",
                "name": "Epigenetics",
                "founder": "Conrad Waddington",
                "core_axioms": [
                    "Environmental factors can change gene expression without altering DNA",
                    "Methylation and histone modification regulate gene activity",
                    "Epigenetic changes can be inherited across generations",
                    "Nature AND nurture interact to shape organisms",
                    "Lifestyle and environment directly affect genetic expression"
                ],
                "key_figures": ["Conrad Waddington", "Michael Meaney"],
                "opposing_schools": ["genetic_determinism"],
                "simulation_variables": {"selection_pressure": 0.3, "mutation_rate": 0.1, "adaptation_speed": "fast"},
                "historical_period": "1940s - Present",
                "beginner_explanation": "Your DNA is like a piano keyboard. Epigenetics is about WHICH keys are played and HOW LOUD. Your environment determines which genes get turned on or off -- without changing the DNA sequence itself.",
                "real_world_analogy": "A light switch. The wiring (DNA) doesn't change, but the switch can be turned on or off. Your diet, stress, and environment flip these switches."
            },
            {
                "id": "evo_devo",
                "name": "Evolutionary Developmental Biology",
                "founder": "Stephen Jay Gould",
                "core_axioms": [
                    "Developmental processes shape evolutionary outcomes",
                    "Hox genes control body plans across species",
                    "Small genetic changes can produce large morphological effects",
                    "Developmental constraints limit possible evolutionary paths",
                    "Ontogeny recapitulates phylogeny (with modifications)"
                ],
                "key_figures": ["Stephen Jay Gould", "Sean B. Carroll"],
                "opposing_schools": ["strict_selectionism"],
                "simulation_variables": {"selection_pressure": 0.5, "mutation_rate": 0.2, "adaptation_speed": "variable"},
                "historical_period": "1970s - Present",
                "beginner_explanation": "How an embryo develops shapes how a species evolves. Tiny tweaks in development can create huge differences -- like the difference between a human arm and a whale flipper.",
                "real_world_analogy": "Like baking: small changes in the recipe (genes) or the baking process (development) can produce very different cakes. Same ingredients, different outcomes."
            },
            {
                "id": "gaia_hypothesis",
                "name": "Gaia Hypothesis",
                "founder": "James Lovelock",
                "core_axioms": [
                    "Earth functions as a single, self-regulating complex system",
                    "Living organisms interact with the inorganic surroundings",
                    "The planet maintains conditions favorable for life",
                    "Biological processes regulate global temperature and chemistry",
                    "Life and environment co-evolve as a coupled system"
                ],
                "key_figures": ["James Lovelock", "Lynn Margulis"],
                "opposing_schools": ["neo-darwinism"],
                "simulation_variables": {"selection_pressure": 0.2, "mutation_rate": 0.1, "adaptation_speed": "geological"},
                "historical_period": "1970s",
                "beginner_explanation": "Earth itself is like a living organism. The air, oceans, and life all work together to keep the planet habitable. Life doesn't just adapt to Earth -- it actively controls Earth's conditions.",
                "real_world_analogy": "Your body regulates its own temperature at 98.6°F. Similarly, Earth regulates its own temperature through interactions between life, oceans, and atmosphere."
            }
        ]
    },
    "art": {
        "name": "Art, Aesthetics & Creative Philosophy",
        "icon": "🎨",
        "description": "What is beauty? How do art and creativity shape human experience?",
        "schools": [
            {
                "id": "classicism",
                "name": "Classicism",
                "founder": "Ancient Greeks",
                "core_axioms": [
                    "Art should reflect ideal forms and universal beauty",
                    "Symmetry, proportion, and harmony are essential",
                    "Reason and order triumph over emotion and chaos",
                    "The ancient Greeks and Romans achieved artistic perfection",
                    "Art should educate and elevate moral character"
                ],
                "key_figures": ["Phidias", "Vitruvius", "Johann Winckelmann"],
                "opposing_schools": ["romanticism", "postmodernism"],
                "simulation_variables": {"emotion": 0.2, "structure": 1.0, "innovation": 0.1},
                "historical_period": "Ancient Greece - 18th Century",
                "beginner_explanation": "Art should be perfect, balanced, and beautiful. Think of Greek statues with perfect proportions, or buildings with perfect symmetry. Rules and order create the best art.",
                "real_world_analogy": "A perfectly arranged garden with geometric hedges and symmetrical flower beds. Every element is in its proper place."
            },
            {
                "id": "romanticism",
                "name": "Romanticism",
                "founder": "Caspar David Friedrich",
                "core_axioms": [
                    "Emotion, imagination, and individualism are supreme",
                    "Nature is a source of spiritual truth and the sublime",
                    "The artist is a genius channeling inner inspiration",
                    "Rebellion against rationalism, industrialization, and rules",
                    "The pursuit of the sublime -- awe mixed with terror"
                ],
                "key_figures": ["Caspar David Friedrich", "William Wordsworth", "Ludwig van Beethoven"],
                "opposing_schools": ["classicism", "modernism"],
                "simulation_variables": {"emotion": 1.0, "structure": 0.1, "innovation": 0.7},
                "historical_period": "Late 18th - 19th Century",
                "beginner_explanation": "Feel your feelings! Romantic art celebrates raw emotion, the power of nature, and the unique genius of the individual artist. Don't follow rules -- follow your heart.",
                "real_world_analogy": "A wild, untamed mountain landscape with storm clouds. Powerful, emotional, overwhelming -- that's the romantic ideal."
            },
            {
                "id": "modernism",
                "name": "Modernism",
                "founder": "Various",
                "core_axioms": [
                    "Reject historical styles; embrace innovation and progress",
                    "Form follows function -- design serves purpose",
                    "Industrial materials and technology enable new aesthetics",
                    "Art should reflect modern life and urban experience",
                    "Break with tradition; experiment with new forms"
                ],
                "key_figures": ["Le Corbusier", "Pablo Picasso", "Walter Gropius"],
                "opposing_schools": ["classicism", "romanticism"],
                "simulation_variables": {"emotion": 0.3, "structure": 0.8, "innovation": 1.0},
                "historical_period": "Late 19th - Mid 20th Century",
                "beginner_explanation": "The old ways are outdated. Modern art embraces factories, cities, machines, and new materials. Less decoration, more function. Art should reflect the modern world.",
                "real_world_analogy": "A sleek skyscraper made of steel and glass. Clean lines, no ornaments, purely functional -- but beautiful in its efficiency."
            },
            {
                "id": "postmodernism",
                "name": "Postmodernism",
                "founder": "Various",
                "core_axioms": [
                    "Irony, playfulness, and self-reference replace sincerity",
                    "Eclectic mixing of styles and cultural references",
                    "Questioning of grand narratives and universal truths",
                    "High and low culture are equally valid",
                    "Subversion and deconstruction of established forms"
                ],
                "key_figures": ["Andy Warhol", "Jean-François Lyotard", "Jacques Derrida"],
                "opposing_schools": ["modernism", "classicism"],
                "simulation_variables": {"emotion": 0.5, "structure": 0.2, "innovation": 0.9},
                "historical_period": "Late 20th Century",
                "beginner_explanation": "Nothing is serious. Everything is a remix. Postmodern art combines high culture with pop culture, uses irony, and questions whether any art is 'better' than any other.",
                "real_world_analogy": "A collage made of magazine cutouts, comic strips, and famous paintings mixed together. Nothing is original; everything is a reference to something else."
            },
            {
                "id": "minimalism",
                "name": "Minimalism",
                "founder": "Donald Judd",
                "core_axioms": [
                    "Reduce art to its essential forms",
                    "Eliminate expression, narrative, and metaphor",
                    "The object itself is the art -- not a representation",
                    "Industrial fabrication removes the artist's hand",
                    "Less is more -- reduction reveals truth"
                ],
                "key_figures": ["Donald Judd", "Agnes Martin", "Frank Stella"],
                "opposing_schools": ["romanticism", "postmodernism"],
                "simulation_variables": {"emotion": 0.0, "structure": 1.0, "innovation": 0.6},
                "historical_period": "1960s - Present",
                "beginner_explanation": "Strip away everything unnecessary. What's left? That IS the art. A single color on a canvas. A plain box. The art is the experience of seeing the pure, simple object.",
                "real_world_analogy": "An empty white room with a single chair. No decoration, no clutter. Just the essential experience of sitting in a chair."
            }
        ]
    },
    "mathematics": {
        "name": "Mathematics & Logic",
        "icon": "🔢",
        "description": "The language of patterns, structure, and logical reasoning.",
        "schools": [
            {
                "id": "formalism",
                "name": "Formalism",
                "founder": "David Hilbert",
                "core_axioms": [
                    "Mathematics is manipulation of abstract symbols per formal rules",
                    "Mathematical truth means derivability from axioms",
                    "Mathematics has no intrinsic meaning beyond its formal structure",
                    "A consistent set of axioms guarantees meaningful mathematics",
                    "All mathematics can be reduced to formal systems"
                ],
                "key_figures": ["David Hilbert", "Bertrand Russell", "Alfred North Whitehead"],
                "opposing_schools": ["intuitionism", "platonism"],
                "simulation_variables": {"abstract": 1.0, "constructive": 0.0, "realist": 0.0},
                "historical_period": "Late 19th - Early 20th Century",
                "beginner_explanation": "Math is like a game with rules. You have symbols and rules for moving them around. The game doesn't need to 'mean' anything in the real world -- it's about following the rules perfectly.",
                "real_world_analogy": "Chess. The rules define how pieces move. The game has no connection to real battles, but it's perfectly logical and consistent within its own rules."
            },
            {
                "id": "intuitionism",
                "name": "Intuitionism",
                "founder": "L.E.J. Brouwer",
                "core_axioms": [
                    "Mathematics is a mental construction",
                    "A mathematical object exists only if it can be constructed",
                    "The law of excluded middle does not always hold",
                    "Infinite sets cannot be treated as completed objects",
                    "Mathematical truth is discovered through intuition"
                ],
                "key_figures": ["L.E.J. Brouwer", "Arend Heyting"],
                "opposing_schools": ["formalism", "platonism"],
                "simulation_variables": {"abstract": 0.3, "constructive": 1.0, "realist": 0.0},
                "historical_period": "Early 20th Century",
                "beginner_explanation": "Math only exists if you can actually build it. Saying 'there exists a number with property X' doesn't count unless you can actually find or construct that number. Proof by contradiction isn't enough.",
                "real_world_analogy": "Building a house. Saying 'a house could exist here' is different from actually building it. Intuitionists only count things you can actually build."
            },
            {
                "id": "platonism",
                "name": "Platonism",
                "founder": "Plato",
                "core_axioms": [
                    "Mathematical entities exist objectively in an abstract realm",
                    "Mathematical truths are discovered, not invented",
                    "The physical world is an imperfect shadow of mathematical forms",
                    "Numbers, sets, and functions exist independently of human minds",
                    "Mathematicians explore an objective, eternal reality"
                ],
                "key_figures": ["Plato", "Kurt Gödel", "Roger Penrose"],
                "opposing_schools": ["formalism", "intuitionism"],
                "simulation_variables": {"abstract": 0.8, "constructive": 0.0, "realist": 1.0},
                "historical_period": "Ancient Greece - Present",
                "beginner_explanation": "Math is real -- more real than the physical world. Numbers don't need humans to exist. Just like dinosaurs existed before we found their bones, mathematical truths exist waiting to be discovered.",
                "real_world_analogy": "An unexplored island. The island exists whether anyone visits or not. Mathematicians are explorers discovering what was always there."
            },
            {
                "id": "logicism",
                "name": "Logicism",
                "founder": "Gottlob Frege",
                "core_axioms": [
                    "All mathematics is reducible to logic",
                    "Mathematical concepts are definable in purely logical terms",
                    "Mathematical theorems are derivable from logical axioms",
                    "Numbers are classes of equinumerous classes",
                    "Logic is the foundation of all mathematical knowledge"
                ],
                "key_figures": ["Gottlob Frege", "Bertrand Russell", "Alfred North Whitehead"],
                "opposing_schools": ["formalism", "intuitionism"],
                "simulation_variables": {"abstract": 0.9, "constructive": 0.2, "realist": 0.5},
                "historical_period": "Late 19th - Early 20th Century",
                "beginner_explanation": "All math is really just logic in disguise. Numbers, addition, calculus -- if you break them down far enough, they're all just logical reasoning. Math IS logic.",
                "real_world_analogy": "All cooking is really just chemistry. Different ingredients and techniques, but at the bottom it's all chemical reactions. Logicism says math is the same -- it's all logic underneath."
            },
            {
                "id": "structuralism_math",
                "name": "Structuralism",
                "founder": "Nicolas Bourbaki",
                "core_axioms": [
                    "Mathematics studies structures and their relationships",
                    "Individual objects matter less than the structures they inhabit",
                    "Isomorphic structures are mathematically identical",
                    "Category theory provides the unifying framework",
                    "Mathematical progress comes from abstracting common patterns"
                ],
                "key_figures": ["Nicolas Bourbaki", "Saunders Mac Lane"],
                "opposing_schools": ["platonism", "formalism"],
                "simulation_variables": {"abstract": 0.9, "constructive": 0.4, "realist": 0.3},
                "historical_period": "Mid 20th Century",
                "beginner_explanation": "It's not about the numbers themselves -- it's about how they're arranged and relate to each other. The PATTERN is what matters, not the individual pieces.",
                "real_world_analogy": "Architecture. It's not about individual bricks -- it's about the structure they create together. Different buildings can have the same underlying structure."
            }
        ]
    }
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_db = None

def get_db():
    """Lazy-loaded database connection with auto-initialization."""
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _db = sqlite3.connect(DB_PATH)
        _db.row_factory = sqlite3.Row
        init_db(_db)
    return _db


def init_db(db=None):
    """Initialize database tables."""
    if db is None:
        db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            level TEXT DEFAULT 'beginner',
            pace TEXT DEFAULT 'medium',
            interests TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            school_id TEXT,
            discipline_id TEXT,
            completion REAL DEFAULT 0.0,
            quiz_score REAL DEFAULT 0.0,
            time_spent INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            concept_id TEXT,
            score REAL,
            answers TEXT,
            feedback TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()


# ---------------------------------------------------------------------------
# Knowledge Graph Accessors
# ---------------------------------------------------------------------------

def list_disciplines() -> Dict[str, Any]:
    """Return all disciplines with basic info."""
    disciplines = []
    for did, disc in KNOWLEDGE_GRAPH.items():
        disciplines.append({
            "id": did,
            "name": disc["name"],
            "icon": disc.get("icon", ""),
            "description": disc["description"],
            "school_count": len(disc["schools"])
        })
    return {"disciplines": disciplines, "total": len(disciplines)}


def get_discipline(discipline_id: str) -> Dict[str, Any]:
    """Get a discipline with all schools."""
    disc = KNOWLEDGE_GRAPH.get(discipline_id)
    if not disc:
        return {"success": False, "error": f"Discipline '{discipline_id}' not found"}
    return {"success": True, "discipline": disc}


def get_school(school_id: str) -> Dict[str, Any]:
    """Get a specific school across all disciplines."""
    for did, disc in KNOWLEDGE_GRAPH.items():
        for school in disc["schools"]:
            if school["id"] == school_id:
                return {"success": True, "school": school, "discipline_id": did}
    return {"success": False, "error": f"School '{school_id}' not found"}


def search_schools(query: str) -> Dict[str, Any]:
    """Search schools by name or figure."""
    results = []
    q = query.lower()
    for did, disc in KNOWLEDGE_GRAPH.items():
        for school in disc["schools"]:
            if q in school["name"].lower() or any(q in f.lower() for f in school["key_figures"]):
                results.append({"school": school, "discipline_id": did, "discipline_name": disc["name"]})
    return {"results": results, "count": len(results)}


def get_knowledge_graph_stats() -> Dict[str, Any]:
    """Get statistics about the knowledge graph."""
    total_schools = 0
    total_figures = set()
    total_axioms = 0
    for disc in KNOWLEDGE_GRAPH.values():
        total_schools += len(disc["schools"])
        for school in disc["schools"]:
            total_figures.update(school["key_figures"])
            total_axioms += len(school["core_axioms"])
    return {
        "disciplines": len(KNOWLEDGE_GRAPH),
        "schools": total_schools,
        "unique_figures": len(total_figures),
        "total_axioms": total_axioms,
        "interdisciplinary_fields": len(INTERDISCIPLINARY_FIELDS),
        "debate_topics": len(DEBATE_TOPICS)
    }


# ---------------------------------------------------------------------------
# Adaptive Learning
# ---------------------------------------------------------------------------

def assess_level(student_id: str, answers: List[Dict]) -> Dict[str, Any]:
    """Assess student's knowledge level based on quiz answers."""
    if not answers:
        return {"level": "beginner", "confidence": 0.0}
    
    correct = sum(1 for a in answers if a.get("correct", False))
    score = correct / len(answers)
    
    if score >= 0.9:
        level = "expert"
    elif score >= 0.7:
        level = "advanced"
    elif score >= 0.4:
        level = "intermediate"
    else:
        level = "beginner"
    
    return {"level": level, "score": round(score, 2), "confidence": min(score + 0.2, 1.0)}


def generate_learning_path(student_id: str, interests: List[str], pace: str = "medium") -> Dict[str, Any]:
    """Generate a personalized learning path."""
    path = []
    lessons_per_day = PACE_LESSONS_PER_DAY.get(pace, 3)
    
    for interest in interests:
        disc = KNOWLEDGE_GRAPH.get(interest)
        if not disc:
            continue
        for i, school in enumerate(disc["schools"]):
            path.append({
                "discipline": disc["name"],
                "school_of_thought": school["name"],
                "lesson_title": f"Introduction to {school['name']}",
                "estimated_minutes": 20,
                "difficulty": LEVELS[min(i // 2, len(LEVELS) - 1)],
                "prerequisites_met": True,
                "why_relevant": f"Foundational school in {disc['name']}"
            })
    
    total_hours = sum(p["estimated_minutes"] for p in path) / 60
    days = len(path) / lessons_per_day
    
    return {
        "path_id": str(uuid.uuid4()),
        "modules": path,
        "total_hours": round(total_hours, 1),
        "estimated_completion_days": round(days),
        "pace": pace,
        "lessons_per_day": lessons_per_day
    }


def explain_concept(concept_id: str, level: str = "intermediate") -> Dict[str, Any]:
    """Explain a concept at the appropriate level."""
    school_data = get_school(concept_id)
    if not school_data["success"]:
        return {"error": school_data.get("error", "Concept not found")}
    
    school = school_data["school"]
    
    if level == "beginner":
        explanation = school["beginner_explanation"]
        analogy = school["real_world_analogy"]
    elif level == "intermediate":
        explanation = " ".join(school["core_axioms"][:3])
        analogy = school["real_world_analogy"]
    elif level == "advanced":
        explanation = " ".join(school["core_axioms"])
        analogy = f"Compare with: {', '.join(school['opposing_schools'])}"
    else:  # expert
        explanation = f"Deep analysis of {school['name']}: " + " ".join(school["core_axioms"])
        analogy = f"Critique: Examine contradictions between {school['name']} and {', '.join(school['opposing_schools'])}"
    
    return {
        "concept": school["name"],
        "level": level,
        "explanation": explanation,
        "analogy": analogy,
        "key_figures": school["key_figures"],
        "common_misconceptions": get_misconceptions(school["name"]),
        "related_concepts": school["opposing_schools"],
        "suggested_reading": [f"{f} - Selected Works" for f in school["key_figures"][:2]],
        "discussion_questions": generate_discussion_questions(school["name"])
    }


def get_lesson(school_id: str, lesson_number: int, student_level: str = "intermediate") -> Dict[str, Any]:
    """Get a complete lesson for a school of thought."""
    school_data = get_school(school_id)
    if not school_data["success"]:
        return {"error": "School not found"}
    
    school = school_data["school"]
    disc_name = school_data.get("discipline_id", "")
    
    # Generate lesson sections based on level
    if student_level == "beginner":
        sections = [
            {"title": "What is this?", "content": school["beginner_explanation"]},
            {"title": "Simple Analogy", "content": school["real_world_analogy"]},
            {"title": "Key People", "content": ", ".join(school["key_figures"][:2])},
            {"title": "Main Idea", "content": school["core_axioms"][0]}
        ]
    elif student_level == "intermediate":
        sections = [
            {"title": "Core Principles", "content": " ".join(school["core_axioms"][:3])},
            {"title": "Key Thinkers", "content": ", ".join(school["key_figures"])},
            {"title": "Historical Context", "content": f"Developed during {school['historical_period']}"},
            {"title": "Opposing Views", "content": f"Critics include: {', '.join(school['opposing_schools'])}"}
        ]
    else:
        sections = [
            {"title": "Complete Axioms", "content": " ".join(school["core_axioms"])},
            {"title": "Full Analysis", "content": f"Founded by {school['founder']} in {school['historical_period']}"},
            {"title": "Critical Debates", "content": f"Primary opposition from: {', '.join(school['opposing_schools'])}"},
            {"title": "Simulation Variables", "content": str(school.get("simulation_variables", {}))}
        ]
    
    return {
        "title": f"Lesson {lesson_number}: {school['name']}",
        "content_sections": sections,
        "quiz_questions": generate_quiz_questions(school, 3),
        "discussion_prompts": generate_discussion_questions(school["name"]),
        "estimated_minutes": 15 + (5 if student_level == "advanced" else 0),
        "next_lesson": lesson_number + 1
    }


# ---------------------------------------------------------------------------
# Debate Simulator
# ---------------------------------------------------------------------------

DEBATE_TOPICS = [
    "Is free will compatible with determinism?",
    "Should governments intervene in free markets?",
    "Is morality objective or subjective?",
    "Does God exist?",
    "Is consciousness purely physical?",
    "Should art be publicly funded?",
    "Is democracy the best form of government?",
    "Can war ever be justified?",
    "Is inequality necessary for progress?",
    "Should we colonize other planets?",
    "Is artificial intelligence a threat to humanity?",
    "Do animals have rights?",
    "Is censorship ever justified?",
    "Should education be free for everyone?",
    "Is the death penalty morally acceptable?",
    "Can we trust our senses?",
    "Is the universe infinite?",
    "Does history repeat itself?",
    "Is nationalism beneficial or harmful?",
    "Should genetic engineering be allowed?"
]


def get_debate_topics() -> Dict[str, Any]:
    """Return curated debate topics."""
    return {"topics": DEBATE_TOPICS, "count": len(DEBATE_TOPICS)}


def simulate_debate(school_a_id: str, school_b_id: str, topic: str, format: str = "structured") -> Dict[str, Any]:
    """Simulate a debate between two schools of thought."""
    a_data = get_school(school_a_id)
    b_data = get_school(school_b_id)
    
    if not a_data["success"] or not b_data["success"]:
        return {"error": "One or both schools not found"}
    
    school_a = a_data["school"]
    school_b = b_data["school"]
    
    # Generate arguments from axioms
    a_args = school_a["core_axioms"]
    b_args = school_b["core_axioms"]
    
    # Find logical conflicts
    clashes = find_axiom_conflicts(school_a, school_b)
    
    # Generate transcript
    transcript = []
    if format == "structured":
        transcript.append({"speaker": school_a["name"], "argument": f"On the topic of '{topic}', we argue based on our foundational principles: {a_args[0]}", "rebuttal_to": None, "strength": 0.8})
        transcript.append({"speaker": school_b["name"], "argument": f"We fundamentally disagree. Our position rests on: {b_args[0]}", "rebuttal_to": school_a["name"], "strength": 0.8})
        for i, clash in enumerate(clashes[:3]):
            transcript.append({"speaker": school_a["name"], "argument": f"Point {i+1}: {clash['a_position']}", "rebuttal_to": school_b["name"], "strength": 0.7})
            transcript.append({"speaker": school_b["name"], "argument": f"Counter-point: {clash['b_position']}", "rebuttal_to": school_a["name"], "strength": 0.7})
    elif format == "socratic":
        transcript.append({"speaker": "Socratic Moderator", "argument": f"Let us examine '{topic}' through questioning. {school_a['name']}, what is your fundamental premise?", "rebuttal_to": None, "strength": 1.0})
        transcript.append({"speaker": school_a["name"], "argument": f"Our premise: {a_args[0]}", "rebuttal_to": "Socratic Moderator", "strength": 0.8})
        transcript.append({"speaker": "Socratic Moderator", "argument": f"And {school_b['name']}, how do you challenge this?", "rebuttal_to": school_a["name"], "strength": 1.0})
        transcript.append({"speaker": school_b["name"], "argument": f"We challenge this because: {b_args[0]}", "rebuttal_to": "Socratic Moderator", "strength": 0.8})
    else:  # battle
        transcript.append({"speaker": school_a["name"], "argument": f"Your position on '{topic}' is fundamentally flawed! {a_args[0]}", "rebuttal_to": school_b["name"], "strength": 0.9})
        transcript.append({"speaker": school_b["name"], "argument": f"Absurd! You ignore reality. {b_args[0]}", "rebuttal_to": school_a["name"], "strength": 0.9})
        transcript.append({"speaker": school_a["name"], "argument": f"Your ignorance is showing: {a_args[1] if len(a_args) > 1 else a_args[0]}", "rebuttal_to": school_b["name"], "strength": 0.85})
        transcript.append({"speaker": school_b["name"], "argument": f"Pathetic! Consider: {b_args[1] if len(b_args) > 1 else b_args[0]}", "rebuttal_to": school_a["name"], "strength": 0.85})
    
    # Generate synthesis
    synthesis = f"While {school_a['name']} emphasizes {a_args[0].lower()}, and {school_b['name']} prioritizes {b_args[0].lower()}, both schools contribute valuable perspectives on '{topic}'. The tension between these viewpoints drives deeper understanding."
    
    return {
        "topic": topic,
        "format": format,
        "debaters": [
            {"school": school_a["name"], "axioms": school_a["core_axioms"][:3], "stance": "affirmative"},
            {"school": school_b["name"], "axioms": school_b["core_axioms"][:3], "stance": "opposition"}
        ],
        "transcript": transcript,
        "key_clashes": clashes,
        "synthesis": synthesis,
        "student_questions": generate_discussion_questions(topic),
        "further_reading": [f"{f}: Selected Works" for f in set(school_a["key_figures"] + school_b["key_figures"])]
    }


def compare_schools(school_a_id: str, school_b_id: str) -> Dict[str, Any]:
    """Side-by-side comparison of two schools."""
    a_data = get_school(school_a_id)
    b_data = get_school(school_b_id)
    
    if not a_data["success"] or not b_data["success"]:
        return {"error": "School not found"}
    
    a, b = a_data["school"], b_data["school"]
    
    similarities = []
    differences = []
    
    # Find similarities
    a_figures = set(f.lower() for f in a["key_figures"])
    b_figures = set(f.lower() for f in b["key_figures"])
    shared = a_figures & b_figures
    if shared:
        similarities.append(f"Shared figures: {', '.join(shared)}")
    
    # Check historical overlap
    if a["historical_period"] == b["historical_period"]:
        similarities.append(f"Both emerged during {a['historical_period']}")
    
    # Find differences
    differences.append(f"{a['name']} focuses on: {a['core_axioms'][0]}")
    differences.append(f"{b['name']} focuses on: {b['core_axioms'][0]}")
    
    # Agreement areas
    agreement = []
    if any(o not in [s["id"] for s in [b]] for o in a["opposing_schools"]):
        agreement.append("Both oppose different schools of thought")
    
    return {
        "similarities": similarities,
        "differences": differences,
        "agreement_areas": agreement,
        "conflict_areas": find_axiom_conflicts(a, b),
        "historical_interactions": f"{a['name']} ({a['historical_period']}) vs {b['name']} ({b['historical_period']})"
    }


# ---------------------------------------------------------------------------
# Cross-Disciplinary
# ---------------------------------------------------------------------------

INTERDISCIPLINARY_FIELDS = [
    {"name": "Behavioral Economics", "bridges": ["economics", "psychology"], "description": "How psychological factors influence economic decisions"},
    {"name": "Neurophilosophy", "bridges": ["epistemology", "psychology"], "description": "The intersection of neuroscience and philosophy of mind"},
    {"name": "Biopolitics", "bridges": ["political_theory", "biology"], "description": "How biological concepts shape political thought"},
    {"name": "Evolutionary Psychology", "bridges": ["psychology", "biology"], "description": "Psychological traits as evolutionary adaptations"},
    {"name": "Econophysics", "bridges": ["economics", "physics"], "description": "Applying physics methods to economic systems"},
    {"name": "Neuroeconomics", "bridges": ["economics", "psychology", "biology"], "description": "Brain mechanisms underlying economic choice"},
    {"name": "Moral Psychology", "bridges": ["ethics", "psychology"], "description": "Psychological foundations of moral judgment"},
    {"name": "Philosophy of Economics", "bridges": ["epistemology", "economics"], "description": "Epistemological foundations of economic knowledge"},
    {"name": "Social Epistemology", "bridges": ["epistemology", "sociology"], "description": "How social processes affect knowledge"},
    {"name": "Environmental Ethics", "bridges": ["ethics", "biology"], "description": "Moral responsibilities toward the environment"},
    {"name": "Philosophy of Science", "bridges": ["epistemology", "physics", "biology"], "description": "Philosophical foundations of scientific knowledge"},
    {"name": "Cognitive Science", "bridges": ["psychology", "biology", "mathematics"], "description": "Interdisciplinary study of mind and intelligence"},
    {"name": "Computational Social Science", "bridges": ["sociology", "mathematics", "psychology"], "description": "Using computational methods to study society"},
    {"name": "Network Science", "bridges": ["mathematics", "sociology", "physics"], "description": "Study of complex networks across disciplines"},
    {"name": "Decision Theory", "bridges": ["mathematics", "economics", "psychology"], "description": "Mathematical analysis of decision making"},
    {"name": "Game Theory", "bridges": ["mathematics", "economics", "political_theory"], "description": "Mathematical models of strategic interaction"},
    {"name": "Complexity Theory", "bridges": ["mathematics", "physics", "biology"], "description": "Study of complex adaptive systems"},
    {"name": "Sociobiology", "bridges": ["biology", "sociology"], "description": "Biological basis of social behavior"},
    {"name": "Political Economy", "bridges": ["political_theory", "economics"], "description": "Interaction of politics and economics"},
    {"name": "Aesthetics of Science", "bridges": ["art", "epistemology", "physics"], "description": "Beauty and elegance in scientific theories"},
    {"name": "Psychohistory", "bridges": ["psychology", "sociology", "political_theory"], "description": "Psychological analysis of historical events"},
    {"name": "Quantum Cognition", "bridges": ["psychology", "physics", "mathematics"], "description": "Applying quantum probability to cognition"},
    {"name": "Digital Humanities", "bridges": ["art", "sociology", "mathematics"], "description": "Computational approaches to humanistic study"},
    {"name": "Science and Technology Studies", "bridges": ["sociology", "epistemology", "physics"], "description": "Social study of science and technology"},
    {"name": "Evolutionary Ethics", "bridges": ["ethics", "biology"], "description": "Evolutionary origins of moral behavior"},
    {"name": "Mathematical Biology", "bridges": ["mathematics", "biology"], "description": "Mathematical modeling of biological systems"},
    {"name": "Philosophy of Mathematics", "bridges": ["epistemology", "mathematics"], "description": "Nature and foundations of mathematics"},
    {"name": "Systems Biology", "bridges": ["biology", "mathematics", "physics"], "description": "Holistic study of biological systems"},
    {"name": "Political Psychology", "bridges": ["political_theory", "psychology"], "description": "Psychological factors in political behavior"},
    {"name": "Media Studies", "bridges": ["sociology", "art", "psychology"], "description": "Critical analysis of media and communication"},
    {"name": "Quantum Gravity Research", "bridges": ["physics", "mathematics"], "description": "Unification of quantum mechanics and gravity"}
]


def get_interdisciplinary_fields() -> Dict[str, Any]:
    """Return all interdisciplinary fields."""
    return {"fields": INTERDISCIPLINARY_FIELDS, "count": len(INTERDISCIPLINARY_FIELDS)}


def find_connections(discipline_a: str, discipline_b: str) -> Dict[str, Any]:
    """Find connections between two disciplines."""
    bridges = []
    for field in INTERDISCIPLINARY_FIELDS:
        if discipline_a in field["bridges"] and discipline_b in field["bridges"]:
            bridges.append({"field": field["name"], "description": field["description"]})
    
    # Find shared figures
    disc_a = KNOWLEDGE_GRAPH.get(discipline_a, {})
    disc_b = KNOWLEDGE_GRAPH.get(discipline_b, {})
    a_figures = set()
    b_figures = set()
    for s in disc_a.get("schools", []):
        a_figures.update(s["key_figures"])
    for s in disc_b.get("schools", []):
        b_figures.update(s["key_figures"])
    shared = list(a_figures & b_figures)
    
    return {
        "bridges": bridges,
        "interdisciplinary_fields": [b["field"] for b in bridges],
        "shared_figures": shared
    }


# ---------------------------------------------------------------------------
# Mastery Tracker
# ---------------------------------------------------------------------------

def track_progress(student_id: str) -> Dict[str, Any]:
    """Get comprehensive learning progress."""
    db = get_db()
    cursor = db.execute("SELECT * FROM progress WHERE student_id = ?", (student_id,))
    rows = cursor.fetchall()
    
    disciplines_progress = {}
    schools_mastered = []
    schools_in_progress = []
    total_time = 0
    
    for row in rows:
        disc_id = row["discipline_id"]
        if disc_id not in disciplines_progress:
            disciplines_progress[disc_id] = {"completion": 0, "count": 0}
        disciplines_progress[disc_id]["completion"] += row["completion"]
        disciplines_progress[disc_id]["count"] += 1
        total_time += row["time_spent"]
        
        if row["completion"] >= 0.9:
            schools_mastered.append(row["school_id"])
        elif row["completion"] > 0:
            schools_in_progress.append(row["school_id"])
    
    # Average completion per discipline
    for disc_id in disciplines_progress:
        dp = disciplines_progress[disc_id]
        dp["completion"] = dp["completion"] / dp["count"] if dp["count"] > 0 else 0
    
    return {
        "disciplines": disciplines_progress,
        "schools_mastered": schools_mastered,
        "schools_in_progress": schools_in_progress,
        "total_hours": round(total_time / 60, 1),
        "concepts_learned": len(schools_mastered) + len(schools_in_progress),
        "weak_areas": [s for s in schools_in_progress if any(r["completion"] < 0.5 for r in rows if r["school_id"] == s)],
        "strengths": schools_mastered,
        "recommended_next": schools_in_progress[:3] if schools_in_progress else list(KNOWLEDGE_GRAPH.keys())[:3]
    }


def quiz_concept(concept_id: str, question_count: int = 5) -> Dict[str, Any]:
    """Generate quiz questions for a concept."""
    school_data = get_school(concept_id)
    if not school_data["success"]:
        return {"error": "Concept not found"}
    
    school = school_data["school"]
    questions = generate_quiz_questions(school, question_count)
    
    return {
        "quiz_id": str(uuid.uuid4()),
        "concept": school["name"],
        "questions": questions,
        "time_limit": question_count * 2,
        "passing_score": 0.6
    }


def grade_quiz(student_id: str, quiz_id: str, answers: List[Dict]) -> Dict[str, Any]:
    """Grade a quiz and provide detailed feedback."""
    correct = sum(1 for a in answers if a.get("correct", False))
    total = len(answers)
    score = correct / total if total > 0 else 0
    
    per_question = []
    for i, a in enumerate(answers):
        per_question.append({
            "question_num": i + 1,
            "correct": a.get("correct", False),
            "feedback": "Correct!" if a.get("correct") else f"The correct answer was: {a.get('correct_answer', 'N/A')}"
        })
    
    areas_to_review = [a.get("topic", "") for a in answers if not a.get("correct", False)]
    
    return {
        "score": round(score, 2),
        "correct": correct,
        "total": total,
        "per_question": per_question,
        "areas_to_review": list(set(areas_to_review)),
        "passed": score >= 0.6,
        "congratulations": "Perfect score! You've mastered this concept!" if score == 1.0 else None
    }


# ---------------------------------------------------------------------------
# Beginner Features
# ---------------------------------------------------------------------------

def explain_like_im_five(concept_id: str) -> Dict[str, Any]:
    """Explain a concept as if to a 5-year-old."""
    school_data = get_school(concept_id)
    if not school_data["success"]:
        return {"error": "Concept not found"}
    
    school = school_data["school"]
    
    return {
        "concept": school["name"],
        "simple_explanation": school["beginner_explanation"],
        "story_analogy": school["real_world_analogy"],
        "drawing_description": f"Imagine a picture showing: {school['real_world_analogy']}",
        "why_it_matters": f"Understanding {school['name']} helps you think about {school_data.get('discipline_id', 'the world')} in a clearer way.",
        "fun_fact": f"Did you know? {school['founder']} developed these ideas during {school['historical_period']}!"
    }


def get_starter_pack() -> Dict[str, Any]:
    """Return a curated 'where to start' guide for absolute beginners."""
    return {
        "recommended_first_3_lessons": [
            {"school": "stoicism", "why": "Practical wisdom for daily life"},
            {"school": "empiricism", "why": "Foundation of how we know things"},
            {"school": "utilitarianism", "why": "Useful framework for ethical decisions"}
        ],
        "learning_tips": [
            "Start with the 'Explain Like I'm 5' feature for each concept",
            "Try the debate simulator to see ideas in action",
            "Take quizzes after each lesson to reinforce learning",
            "Don't rush -- understanding deep ideas takes time",
            "Connect ideas to your own life experiences"
        ],
        "common_pitfalls": [
            "Trying to read advanced texts before understanding basics",
            "Memorizing without understanding the 'why'",
            "Ignoring opposing viewpoints",
            "Getting stuck on one school without exploring alternatives"
        ],
        "motivation_boosters": [
            "Every great philosopher started as a beginner",
            "These ideas have shaped human civilization for millennia",
            "You're joining a conversation that spans thousands of years",
            "Understanding these concepts will change how you see the world"
        ]
    }


def generate_study_plan(hours_per_week: int, goals: List[str]) -> Dict[str, Any]:
    """Generate a realistic study plan."""
    daily_hours = hours_per_week / 7
    
    schedule = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        if day in ["Saturday", "Sunday"]:
            schedule.append({"day": day, "focus": "Review & practice quizzes", "hours": round(daily_hours * 0.8, 1)})
        else:
            schedule.append({"day": day, "focus": f"New content: {random.choice(goals) if goals else 'Exploration'}", "hours": round(daily_hours, 1)})
    
    milestones = [
        {"week": 2, "goal": "Complete first 3 schools of thought"},
        {"week": 4, "goal": "Finish first full discipline"},
        {"week": 8, "goal": "Complete 3 disciplines"},
        {"week": 12, "goal": "Participate in 5 debates"}
    ]
    
    return {
        "weekly_schedule": schedule,
        "milestones": milestones,
        "resources_needed": ["Notebook for reflections", "Quiz practice time", "Debate partner (optional)"],
        "tips": "Consistency beats intensity. Even 20 minutes daily is better than 3 hours once a week."
    }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_misconceptions(school_name: str) -> List[str]:
    """Generate common misconceptions about a school."""
    misconceptions = {
        "Stoicism": ["Stoics suppress all emotions (they transform them)", "Stoicism means being passive (it's about wise action)"],
        "Nihilism": ["Nihilists are depressed (many are liberated)", "Nihilism means doing nothing (it means creating your own meaning)"],
        "Utilitarianism": ["It's just 'the greatest good' without nuance (it has sophisticated variants)", "It ignores individual rights (rule utilitarianism addresses this)"],
        "Behaviorism": ["Behaviorists deny the existence of thoughts (they just don't study them)", "It's only about punishment (reinforcement is central)"],
        "Relativity": ["'Everything is relative' (it's a precise physical theory)", "It proves nothing is certain (it makes very certain predictions)"],
    }
    return misconceptions.get(school_name, ["Common misconception: oversimplifying complex ideas", "Misconception: ignoring historical context"])


def generate_discussion_questions(topic: str) -> List[str]:
    """Generate discussion questions for a topic."""
    return [
        f"How does {topic} apply to modern life?",
        f"What are the strongest objections to {topic}?",
        f"How would different cultures view {topic}?",
        f"Can you think of a real-world example of {topic}?",
        f"How has your thinking changed after studying {topic}?"
    ]


def generate_quiz_questions(school: Dict, count: int) -> List[Dict]:
    """Generate quiz questions for a school."""
    questions = []
    axioms = school["core_axioms"]
    figures = school["key_figures"]
    
    if axioms:
        questions.append({
            "type": "multiple_choice",
            "question": f"Which of the following is a core axiom of {school['name']}?",
            "options": axioms[:3] + ["None of the above"],
            "correct_index": 0,
            "topic": school["name"]
        })
    
    if figures:
        questions.append({
            "type": "multiple_choice",
            "question": f"Who is associated with {school['name']}?",
            "options": figures[:2] + ["Albert Einstein", "Charles Darwin"],
            "correct_index": 0,
            "topic": school["name"]
        })
    
    if school.get("opposing_schools"):
        questions.append({
            "type": "multiple_choice",
            "question": f"Which school opposes {school['name']}?",
            "options": school["opposing_schools"][:2] + ["Pragmatism", "Humanism"],
            "correct_index": 0,
            "topic": school["name"]
        })
    
    # Fill remaining with true/false
    while len(questions) < count:
        questions.append({
            "type": "true_false",
            "question": f"True or False: {school['name']} was developed during {school.get('historical_period', 'ancient times')}.",
            "correct_answer": True,
            "topic": school["name"]
        })
    
    return questions[:count]


def find_axiom_conflicts(school_a: Dict, school_b: Dict) -> List[Dict]:
    """Find logical conflicts between two schools."""
    clashes = []
    
    # Check if they oppose each other
    if school_b["id"] in school_a.get("opposing_schools", []):
        clashes.append({
            "topic": "Direct Opposition",
            "a_position": f"{school_a['name']} explicitly opposes {school_b['name']}",
            "b_position": f"{school_b['name']} is a recognized opposing school"
        })
    
    # Check simulation variable conflicts
    a_vars = school_a.get("simulation_variables", {})
    b_vars = school_b.get("simulation_variables", {})
    for key in set(a_vars.keys()) & set(b_vars.keys()):
        if abs(a_vars[key] - b_vars[key]) > 0.5:
            clashes.append({
                "topic": key.replace("_", " ").title(),
                "a_position": f"{school_a['name']}: {key} = {a_vars[key]}",
                "b_position": f"{school_b['name']}: {key} = {b_vars[key]}"
            })
    
    return clashes


# ---------------------------------------------------------------------------
# Student Management
# ---------------------------------------------------------------------------

def register_student(student_id: str, name: str, email: str, level: str = "beginner", interests: List[str] = None) -> Dict[str, Any]:
    """Register a new student."""
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO students (id, name, email, level, interests) VALUES (?, ?, ?, ?, ?)",
        (student_id, name, email, level, json.dumps(interests or []))
    )
    db.commit()
    return {"success": True, "student_id": student_id}


def log_activity(student_id: str, action: str, details: str = "") -> None:
    """Log a student activity."""
    db = get_db()
    db.execute(
        "INSERT INTO activity_log (student_id, action, details) VALUES (?, ?, ?)",
        (student_id, action, details)
    )
    db.commit()


def update_progress(student_id: str, school_id: str, discipline_id: str, completion: float, time_spent: int = 0) -> None:
    """Update student progress for a school."""
    db = get_db()
    db.execute(
        """INSERT INTO progress (student_id, school_id, discipline_id, completion, time_spent)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT DO UPDATE SET 
           completion = MAX(completion, excluded.completion),
           time_spent = time_spent + excluded.time_spent""",
        (student_id, school_id, discipline_id, completion, time_spent)
    )
    db.commit()


# ---------------------------------------------------------------------------
# Additional Utility Functions
# ---------------------------------------------------------------------------

def get_discipline_overview(discipline_id: str) -> Dict[str, Any]:
    """Get a high-level overview of a discipline."""
    disc = KNOWLEDGE_GRAPH.get(discipline_id)
    if not disc:
        return {"error": "Discipline not found"}
    
    return {
        "id": discipline_id,
        "name": disc["name"],
        "description": disc["description"],
        "school_count": len(disc["schools"]),
        "schools_summary": [{"id": s["id"], "name": s["name"], "founder": s["founder"], "period": s["historical_period"]} for s in disc["schools"]],
        "key_debates": [t for t in DEBATE_TOPICS if any(s["name"] in t for s in disc["schools"])][:5]
    }


def get_daily_challenge() -> Dict[str, Any]:
    """Generate a daily learning challenge."""
    import random
    disc = random.choice(list(KNOWLEDGE_GRAPH.values()))
    school = random.choice(disc["schools"])
    
    return {
        "date": datetime.now().isoformat()[:10],
        "challenge": f"Learn about {school['name']} in {disc['name']}",
        "description": school["beginner_explanation"][:100] + "...",
        "estimated_minutes": 15,
        "discipline": disc["name"],
        "school": school["name"]
    }


def get_random_discovery() -> Dict[str, Any]:
    """Get a random interesting fact from the knowledge graph."""
    disc = random.choice(list(KNOWLEDGE_GRAPH.values()))
    school = random.choice(disc["schools"])
    
    return {
        "fact": f"{school['name']} ({disc['name']}): {school['core_axioms'][0]}",
        "figure": random.choice(school["key_figures"]),
        "period": school["historical_period"],
        "discipline": disc["name"]
    }


def get_figure_profile(figure_name: str) -> Dict[str, Any]:
    """Get a profile of a key figure."""
    figure_name_lower = figure_name.lower()
    for disc in KNOWLEDGE_GRAPH.values():
        for school in disc["schools"]:
            for fig in school["key_figures"]:
                if figure_name_lower in fig.lower():
                    return {
                        "name": fig,
                        "associated_school": school["name"],
                        "discipline": disc["name"],
                        "core_contribution": school["core_axioms"][0],
                        "historical_period": school["historical_period"]
                    }
    return {"error": f"Figure '{figure_name}' not found in knowledge graph"}


def search_across_all(query: str) -> Dict[str, Any]:
    """Search across all disciplines and schools."""
    results = {"disciplines": [], "schools": [], "figures": []}
    q = query.lower()
    
    for did, disc in KNOWLEDGE_GRAPH.items():
        if q in disc["name"].lower() or q in disc.get("description", "").lower():
            results["disciplines"].append({"id": did, "name": disc["name"]})
        
        for school in disc["schools"]:
            if q in school["name"].lower() or any(q in axiom.lower() for axiom in school["core_axioms"]):
                results["schools"].append({"id": school["id"], "name": school["name"], "discipline": disc["name"]})
            
            for fig in school["key_figures"]:
                if q in fig.lower():
                    results["figures"].append({"name": fig, "school": school["name"]})
    
    return results


def get_recommended_debate(student_level: str = "beginner") -> Dict[str, Any]:
    """Get a recommended debate based on student level."""
    if student_level == "beginner":
        topic = "Is it better to follow rules or consider consequences?"
        school_a, school_b = "deontology", "utilitarianism"
    elif student_level == "intermediate":
        topic = "Should markets be free or regulated?"
        school_a, school_b = "classical_economics", "keynesianism"
    else:
        topic = "Is reality fundamentally deterministic or probabilistic?"
        school_a, school_b = "classical_mechanics", "quantum_mechanics"
    
    return {"topic": topic, "school_a": school_a, "school_b": school_b, "level": student_level}


def get_curriculum_pathway(goal: str = "broad_understanding") -> List[Dict]:
    """Get a structured curriculum pathway."""
    pathways = {
        "broad_understanding": ["ethics", "epistemology", "political_theory", "economics", "psychology"],
        "deep_philosophy": ["epistemology", "ethics", "eastern_philosophy", "mathematics"],
        "science_focus": ["physics", "biology", "mathematics", "psychology"],
        "social_impact": ["political_theory", "economics", "sociology", "ethics"]
    }
    
    selected = pathways.get(goal, pathways["broad_understanding"])
    return [{"order": i+1, "discipline": KNOWLEDGE_GRAPH[d]["name"], "id": d} for i, d in enumerate(selected) if d in KNOWLEDGE_GRAPH]


def export_student_report(student_id: str) -> Dict[str, Any]:
    """Export a comprehensive student report."""
    progress = track_progress(student_id)
    
    return {
        "student_id": student_id,
        "generated_at": datetime.now().isoformat(),
        "overall_progress": progress,
        "recommendations": progress.get("recommended_next", []),
        "next_steps": "Continue with recommended schools and take quizzes to assess understanding."
    }


def get_learning_analytics(student_id: str) -> Dict[str, Any]:
    """Get learning analytics for a student."""
    db = get_db()
    cursor = db.execute("SELECT action, COUNT(*) as count FROM activity_log WHERE student_id = ? GROUP BY action", (student_id,))
    activities = {row["action"]: row["count"] for row in cursor.fetchall()}
    
    cursor = db.execute("SELECT AVG(score) as avg_score FROM quiz_results WHERE student_id = ?", (student_id,))
    avg_score = cursor.fetchone()["avg_score"] or 0
    
    return {
        "student_id": student_id,
        "activities": activities,
        "average_quiz_score": round(avg_score, 2),
        "total_activities": sum(activities.values()),
        "most_active_area": max(activities, key=activities.get) if activities else "N/A"
    }


def generate_revision_cards(school_id: str, count: int = 5) -> List[Dict]:
    """Generate revision flashcards for a school."""
    school_data = get_school(school_id)
    if not school_data["success"]:
        return []
    
    school = school_data["school"]
    cards = []
    
    for i, axiom in enumerate(school["core_axioms"][:count]):
        cards.append({
            "front": f"Core Principle {i+1} of {school['name']}:",
            "back": axiom,
            "hint": school["real_world_analogy"]
        })
    
    return cards


def get_search_index() -> Dict[str, Any]:
    """Get a searchable index of all content."""
    index = []
    for did, disc in KNOWLEDGE_GRAPH.items():
        for school in disc["schools"]:
            index.append({
                "id": school["id"],
                "name": school["name"],
                "discipline": disc["name"],
                "discipline_id": did,
                "founder": school["founder"],
                "period": school["historical_period"],
                "axiom_count": len(school["core_axioms"]),
                "figure_count": len(school["key_figures"])
            })
    return {"entries": index, "total": len(index)}


if __name__ == "__main__":
    # Quick smoke test
    print("Knowledge Academy v1.0.0")
    print(f"Disciplines: {len(KNOWLEDGE_GRAPH)}")
    stats = get_knowledge_graph_stats()
    print(f"Schools: {stats['schools']}, Figures: {stats['unique_figures']}, Axioms: {stats['total_axioms']}")
    print(f"Interdisciplinary fields: {stats['interdisciplinary_fields']}")
    print("✅ All systems operational")

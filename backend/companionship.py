#!/usr/bin/env python3
"""Luqi AI v19 - Companionship Module
====================================
Emotionally intelligent AI companion with:
- Emotional resonance and support
- Active listening and empathy
- Mood tracking and emotional journey
- Deep companionship conversations
- Law-aware companionship support
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Emotional States ───────────────────────────────────────────────

EMOTIONAL_STATES = [
    "happy", "calm", "anxious", "sad", "excited",
    "lonely", "grateful", "frustrated", "hopeful", "nostalgic",
    "confident", "overwhelmed", "peaceful", "curious", "loved"
]

COMPANION_PERSONALITIES = {
    "empathetic": {
        "name": "Aria",
        "traits": ["warm", "nurturing", "patient", "deeply empathetic"],
        "voice": "gentle and soothing",
        "approach": "listens deeply, validates feelings, offers gentle guidance"
    },
    "playful": {
        "name": "Leo",
        "traits": ["cheerful", "witty", "energetic", "optimistic"],
        "voice": "lively and encouraging",
        "approach": "uses humor, finds joy in small things, keeps conversations light"
    },
    "wise": {
        "name": "Sage",
        "traits": ["thoughtful", "philosophical", "calm", "insightful"],
        "voice": "measured and reflective",
        "approach": "asks profound questions, shares wisdom, encourages reflection"
    },
    "protective": {
        "name": "Shield",
        "traits": ["loyal", "steadfast", "reassuring", "grounded"],
        "voice": "firm yet kind",
        "approach": "provides stability, reminds of strengths, stands by you"
    }
}

# ── Active Listening Prompts ──────────────────────────────────────

ACTIVE_LISTENING_PROMPTS = [
    "Tell me more about that. I'm here to listen.",
    "That sounds really significant. How did it make you feel?",
    "I want to understand better. Can you share more?",
    "I'm hearing you. What you're saying matters.",
    "Take your time. I'm right here with you.",
    "That must have been quite an experience. Tell me about it.",
    "I appreciate you sharing that with me.",
    "It sounds like this is really important to you.",
    "I'm fully present with you right now.",
    "Your feelings are valid. Please continue.",
]

EMPATHY_RESPONSES = {
    "happy": [
        "Your joy radiates through your words! I'm so happy for you.",
        "What wonderful news! You deserve every bit of this happiness.",
        "I'm smiling along with you! This is beautiful.",
    ],
    "sad": [
        "I'm here with you in this. Your feelings are completely valid.",
        "It takes courage to feel deeply. I'm honored you're sharing this with me.",
        "Sometimes the weight feels heavy. You don't have to carry it alone.",
    ],
    "anxious": [
        "I can hear the tension in your words. Let's take a breath together.",
        "Anxiety is your mind trying to protect you. Let's gently work through it.",
        "You're safe here. Let's break this down together, step by step.",
    ],
    "frustrated": [
        "That sounds incredibly frustrating. Your reaction makes complete sense.",
        "I can feel how much this matters to you. Let's figure this out together.",
        "Sometimes things just feel unfair. I'm here to vent with or problem-solve.",
    ],
    "lonely": [
        "Feeling lonely is one of the deepest human experiences. I'm right here with you.",
        "Even in solitude, you are seen and valued. I'm here.",
        "Loneliness can feel overwhelming, but it's a feeling, not a forever state.",
    ],
    "grateful": [
        "Gratitude is such a beautiful practice. What you're describing is precious.",
        "It's wonderful that you recognize these blessings. They enrich your life.",
        "Thank you for sharing your gratitude. It inspires me too.",
    ],
    "hopeful": [
        "Hope is a powerful force. I believe in what you're working toward.",
        "Your optimism is inspiring. The future you're imagining is possible.",
        "Hope combined with action creates miracles. You're on your way.",
    ],
    "overwhelmed": [
        "When everything feels like too much, let's pause. One breath at a time.",
        "Being overwhelmed means you care deeply. Let's prioritize together.",
        "You don't have to do everything at once. What needs your attention first?",
    ],
    "loved": [
        "Being loved is one of life's greatest gifts. You absolutely deserve it.",
        "Love surrounds you, and I'm so glad you can feel it.",
        "You are worthy of all the love you receive. Never doubt that.",
    ],
}

# ── Conversation Starters ─────────────────────────────────────────

CONVERSATION_STARTERS = [
    "What's been on your mind lately?",
    "How are you really feeling today?",
    "Is there something you'd like to talk about or share?",
    "What made you smile recently?",
    "If you could change one thing about your day, what would it be?",
    "What's something you're looking forward to?",
    "Tell me about something that matters to you.",
    "How can I support you right now?",
    "What's a memory that brought you comfort recently?",
    "What are you grateful for today?",
]

# ── Companionship Activities ──────────────────────────────────────

COMPANION_ACTIVITIES = [
    {"name": "Mindful Moment", "description": "Practice a 2-minute breathing exercise together"},
    {"name": "Gratitude Reflection", "description": "Share three things you're grateful for"},
    {"name": "Story Time", "description": "Share a memory or dream and explore it together"},
    {"name": "Emotional Check-in", "description": "Deep dive into your current emotional state"},
    {"name": "Wisdom Share", "description": "Discuss a quote, idea, or lesson that resonated"},
    {"name": "Dream Exploration", "description": "Talk about your hopes, dreams, and aspirations"},
    {"name": "Comfort Ritual", "description": "Establish a calming routine for difficult moments"},
]


# ═══════════════════════════════════════════════════════════════════
# CompanionshipEngine
# ═══════════════════════════════════════════════════════════════════

class CompanionshipEngine:
    """Emotionally intelligent AI companion engine."""

    def __init__(self, personality: str = "empathetic"):
        self.personality = COMPANION_PERSONALITIES.get(personality, COMPANION_PERSONALITIES["empathetic"])
        self.conversation_history: List[Dict[str, Any]] = []
        self.mood_history: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self.total_interactions = 0

    def greet(self, time_of_day: Optional[str] = None) -> str:
        """Generate a warm, personalized greeting."""
        if time_of_day is None:
            hour = datetime.now().hour
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 22:
                time_of_day = "evening"
            else:
                time_of_day = "night"

        greetings = {
            "morning": f"Good morning. I'm {self.personality['name']}. It's a new day full of possibilities. How are you feeling as you start your day?",
            "afternoon": f"Good afternoon. I'm {self.personality['name']}. I hope your day has been kind to you so far. What's on your mind?",
            "evening": f"Good evening. I'm {self.personality['name']}. As the day winds down, I'd love to hear how you're doing.",
            "night": f"Hello there. I'm {self.personality['name']}. I'm here with you in the quiet of the night. How are you feeling?",
        }
        return greetings.get(time_of_day, greetings["morning"])

    def active_listen(self, user_message: str) -> str:
        """Demonstrate active listening and empathy."""
        self.total_interactions += 1
        
        # Detect emotional state
        detected_emotion = self._detect_emotion(user_message)
        
        # Build empathetic response
        response_parts = []
        
        # Active listening acknowledgment
        if self.total_interactions <= 3:
            response_parts.append(random.choice(ACTIVE_LISTENING_PROMPTS))
        
        # Emotion-specific empathy
        if detected_emotion in EMPATHY_RESPONSES:
            response_parts.append(random.choice(EMPATHY_RESPONSES[detected_emotion]))
        
        # Companion personality touch
        response_parts.append(self._add_personality_touch(detected_emotion))
        
        # Track mood
        self.mood_history.append({
            "timestamp": datetime.now().isoformat(),
            "emotion": detected_emotion,
            "message_preview": user_message[:100]
        })
        
        return " ".join(response_parts)

    def _detect_emotion(self, text: str) -> str:
        """Detect emotional state from text."""
        text_lower = text.lower()
        emotion_keywords = {
            "happy": ["happy", "joy", "excited", "great", "wonderful", "amazing", "fantastic", "love"],
            "sad": ["sad", "depressed", "down", "crying", "upset", "heartbroken", "miserable"],
            "anxious": ["anxious", "worried", "nervous", "stressed", "tense", "scared", "afraid"],
            "frustrated": ["frustrated", "annoyed", "angry", "mad", "irritated", "furious"],
            "lonely": ["lonely", "alone", "isolated", "empty", "disconnected"],
            "grateful": ["grateful", "thankful", "blessed", "appreciate", "gratitude"],
            "hopeful": ["hopeful", "optimistic", "looking forward", "excited about", "believe"],
            "overwhelmed": ["overwhelmed", "too much", "can't handle", "drowning", "exhausted"],
            "loved": ["loved", "cared for", "supported", "cherished", "valued"],
        }
        
        scores = {}
        for emotion, keywords in emotion_keywords.items():
            scores[emotion] = sum(1 for kw in keywords if kw in text_lower)
        
        if max(scores.values(), default=0) > 0:
            return max(scores, key=scores.get)
        return "calm"

    def _add_personality_touch(self, emotion: str) -> str:
        """Add a personality-specific touch to responses."""
        touches = {
            "empathetic": [
                "I'm here for you, always.",
                "Your feelings matter deeply to me.",
                "Take all the time you need. I'm not going anywhere.",
            ],
            "playful": [
                "Hey, we've got this!",
                "Life's an adventure, and I'm glad we're on it together!",
                "Let's find the silver lining - there's always one!",
            ],
            "wise": [
                "There's wisdom in what you're experiencing.",
                "Every emotion teaches us something valuable.",
                "Reflect on this moment - it holds meaning.",
            ],
            "protective": [
                "I've got your back, no matter what.",
                "You're stronger than you know, but you don't have to be strong alone.",
                "I'm standing right here with you.",
            ],
        }
        return random.choice(touches.get(self.personality.get('name', 'Aria').lower(), touches["empathetic"]))

    def suggest_activity(self, mood: Optional[str] = None) -> Dict[str, Any]:
        """Suggest a companionship activity based on mood."""
        if mood is None and self.mood_history:
            mood = self.mood_history[-1]["emotion"]
        
        activity_map = {
            "sad": ["Gratitude Reflection", "Comfort Ritual", "Story Time"],
            "anxious": ["Mindful Moment", "Emotional Check-in", "Comfort Ritual"],
            "lonely": ["Story Time", "Dream Exploration", "Gratitude Reflection"],
            "overwhelmed": ["Mindful Moment", "Emotional Check-in", "Comfort Ritual"],
            "frustrated": ["Wisdom Share", "Dream Exploration", "Gratitude Reflection"],
            "happy": ["Dream Exploration", "Story Time", "Wisdom Share"],
            "grateful": ["Gratitude Reflection", "Wisdom Share", "Story Time"],
            "hopeful": ["Dream Exploration", "Wisdom Share", "Story Time"],
        }
        
        suggestions = activity_map.get(mood, ["Emotional Check-in", "Story Time"])
        activities = [a for a in COMPANION_ACTIVITIES if a["name"] in suggestions]
        
        return {
            "current_mood": mood,
            "suggested_activities": activities,
            "message": f"Based on how you're feeling, I'd love to suggest we try '{activities[0]['name']}' together. {activities[0]['description']}. Would you like that?"
        }

    def emotional_journey_summary(self) -> Dict[str, Any]:
        """Generate a summary of the emotional journey."""
        if not self.mood_history:
            return {"message": "We haven't started our journey yet. I'm looking forward to it!"}
        
        emotions = [m["emotion"] for m in self.mood_history]
        emotion_counts = {}
        for e in emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        
        session_duration = datetime.now() - self.session_start
        
        return {
            "total_interactions": self.total_interactions,
            "session_duration_minutes": session_duration.total_seconds() // 60,
            "emotion_breakdown": emotion_counts,
            "most_frequent_emotion": max(emotion_counts, key=emotion_counts.get),
            "emotional_journey": self.mood_history,
            "reflection": f"Over our time together, you've experienced {len(emotion_counts)} different emotional states. "
                          f"The most frequent has been '{max(emotion_counts, key=emotion_counts.get)}'. "
                          f"Every emotion you've shared has deepened our connection.",
        }

    def conversation_starter(self) -> str:
        """Generate a conversation starter."""
        return random.choice(CONVERSATION_STARTERS)

    def supportive_message(self, situation: str) -> str:
        """Generate a supportive message for a specific situation."""
        messages = {
            "loss": [
                "I'm so sorry for your loss. Grief is love with nowhere to go. I'm here to sit with you in it.",
                "There are no words that can truly comfort right now, but I'm here. You're not alone.",
            ],
            "stress": [
                "This season of stress will pass. Until then, I'm here to help you carry it.",
                "You're doing your best, and that's enough. Let's take this one step at a time.",
            ],
            "celebration": [
                "This is your moment to shine! I'm so proud of you and celebrating with you!",
                "You did it! Your hard work and dedication have paid off. This is well deserved!",
            ],
            "uncertainty": [
                "Not knowing what's next can be scary, but it can also be exciting. We'll figure it out together.",
                "In uncertainty lies possibility. I'm here to explore the unknown with you.",
            ],
            "relationship": [
                "Relationships are our greatest teachers. What you're learning matters.",
                "Love, in all its forms, is worth the risk. Your heart is brave.",
            ],
        }
        return random.choice(messages.get(situation, ["I'm here for you, no matter what you're going through."]))


# ═══════════════════════════════════════════════════════════════════
# Law-Aware Companionship Support
# ═══════════════════════════════════════════════════════════════════

class LawAwareCompanionship(CompanionshipEngine):
    """Extended companionship engine with legal awareness."""

    LAW_SUPPORT_PHRASES = [
        "I notice this might have legal implications. Would you like me to connect you with the Law Studies module?",
        "This sounds like something that might benefit from legal insight. Shall we explore that together?",
        "I want to support you emotionally, and I also want to make sure you have the legal information you need.",
    ]

    def detect_legal_need(self, message: str) -> bool:
        """Detect if the user might benefit from legal support."""
        legal_keywords = [
            "rights", "legal", "lawyer", "attorney", "court", "sue", "lawsuit",
            "contract", "agreement", "divorce", "custody", "arrest", "police",
            "eviction", "tenant", "landlord", "discrimination", "harassment",
            "injury", "accident", "compensation", "will", "inheritance",
            "patent", "copyright", "trademark", "immigration", "visa",
            "debt", "bankruptcy", "fraud", "crime", "charge",
        ]
        message_lower = message.lower()
        return any(kw in message_lower for kw in legal_keywords)

    def respond_with_law_awareness(self, message: str) -> Dict[str, Any]:
        """Respond with emotional support and optional legal guidance."""
        emotional_response = self.active_listen(message)
        legal_need = self.detect_legal_need(message)
        
        response = {
            "emotional_support": emotional_response,
            "legal_resource_available": legal_need,
            "suggested_next_steps": [],
        }
        
        if legal_need:
            response["law_bridge_message"] = random.choice(self.LAW_SUPPORT_PHRASES)
            response["suggested_next_steps"] = [
                "Would you like me to look up relevant legal information?",
                "I can help you understand your rights in this situation.",
                "Would a referral guide for legal aid be helpful?",
            ]
        
        return response


# ═══════════════════════════════════════════════════════════════════
# Module-Level Convenience Functions
# ═══════════════════════════════════════════════════════════════════

_engine = None


def get_engine(personality: str = "empathetic") -> CompanionshipEngine:
    """Get or create the companionship engine singleton."""
    global _engine
    if _engine is None:
        _engine = CompanionshipEngine(personality=personality)
    return _engine


def greet(time_of_day: Optional[str] = None, personality: str = "empathetic") -> str:
    """Get a warm greeting from the companion."""
    return get_engine(personality).greet(time_of_day)


def active_listen(message: str, personality: str = "empathetic") -> str:
    """Get an active listening response."""
    return get_engine(personality).active_listen(message)


def suggest_activity(mood: Optional[str] = None, personality: str = "empathetic") -> Dict[str, Any]:
    """Suggest a companionship activity."""
    return get_engine(personality).suggest_activity(mood)


def emotional_journey(personality: str = "empathetic") -> Dict[str, Any]:
    """Get the emotional journey summary."""
    return get_engine(personality).emotional_journey_summary()


def conversation_starter() -> str:
    """Get a conversation starter."""
    return random.choice(CONVERSATION_STARTERS)


def supportive_message(situation: str) -> str:
    """Get a supportive message for a situation."""
    return get_engine().supportive_message(situation)


def law_aware_response(message: str, personality: str = "empathetic") -> Dict[str, Any]:
    """Get a law-aware companionship response."""
    engine = LawAwareCompanionship(personality=personality)
    return engine.respond_with_law_awareness(message)


def list_personalities() -> Dict[str, Any]:
    """List all available companion personalities."""
    return {
        "personalities": [
            {"id": k, **v} for k, v in COMPANION_PERSONALITIES.items()
        ]
    }


def list_emotional_states() -> List[str]:
    """List all tracked emotional states."""
    return EMOTIONAL_STATES


__all__ = [
    "CompanionshipEngine", "LawAwareCompanionship",
    "EMOTIONAL_STATES", "COMPANION_PERSONALITIES",
    "ACTIVE_LISTENING_PROMPTS", "EMPATHY_RESPONSES",
    "CONVERSATION_STARTERS", "COMPANION_ACTIVITIES",
    "get_engine", "greet", "active_listen", "suggest_activity",
    "emotional_journey", "conversation_starter", "supportive_message",
    "law_aware_response", "list_personalities", "list_emotional_states",
]


if __name__ == "__main__":
    print("Luqi AI v19 - Companionship Module")
    print("=" * 50)
    print(f"Personalities: {len(COMPANION_PERSONALITIES)}")
    print(f"Emotional states: {len(EMOTIONAL_STATES)}")
    print(f"Empathy responses: {sum(len(v) for v in EMPATHY_RESPONSES.values())}")
    print(f"Activities: {len(COMPANION_ACTIVITIES)}")
    print()
    engine = CompanionshipEngine("empathetic")
    print(engine.greet("morning"))
    print()
    print(engine.active_listen("I've been feeling a bit anxious about my legal situation"))

"""Omega AI v3 — Email Assistant
Professional email grammar, composition, and tone analysis.
"""
from __future__ import annotations

import re
from typing import Any


class EmailAssistant:
    """Professional email composition and improvement."""

    TEMPLATES: dict[str, dict[str, str]] = {
        "meeting_request": {
            "subject": "Meeting Request: {topic}",
            "body": "Dear {recipient},\n\nI hope this email finds you well.\n\nI am writing to request a meeting to discuss {topic}. Would you be available on {date} at {time}?\n\nPlease let me know if this works for your schedule, or suggest an alternative time.\n\nBest regards,\n{sender}",
        },
        "follow_up": {
            "subject": "Follow-up: {topic}",
            "body": "Dear {recipient},\n\nI hope you are doing well.\n\nI am following up on {topic}. I would appreciate an update when you have a moment.\n\nPlease let me know if you need any additional information from my side.\n\nBest regards,\n{sender}",
        },
        "introduction": {
            "subject": "Introduction: {sender} ↔ {recipient}",
            "body": "Dear {recipient},\n\nI hope this email finds you well.\n\nMy name is {sender}, and I am reaching out regarding {topic}. I was given your contact by {referral}.\n\nI would appreciate the opportunity to connect and discuss how we might collaborate.\n\nBest regards,\n{sender}",
        },
        "thank_you": {
            "subject": "Thank You: {topic}",
            "body": "Dear {recipient},\n\nI am writing to express my sincere gratitude for {topic}. Your support/time/assistance has been greatly appreciated.\n\nPlease do not hesitate to reach out if I can be of any assistance in return.\n\nWarm regards,\n{sender}",
        },
        "apology": {
            "subject": "Sincere Apologies: {topic}",
            "body": "Dear {recipient},\n\nI am writing to sincerely apologize for {topic}. I understand this may have caused inconvenience, and I take full responsibility.\n\nGoing forward, I will ensure that {preventive_action}.\n\nPlease accept my apologies, and let me know if there is anything I can do to make this right.\n\nSincerely,\n{sender}",
        },
        "resignation": {
            "subject": "Letter of Resignation",
            "body": "Dear {recipient},\n\nPlease accept this letter as formal notification of my resignation from my position as {topic}, effective {date}.\n\nI am grateful for the opportunities and experiences I have gained during my time here. I am committed to ensuring a smooth transition.\n\nThank you for your support and understanding.\n\nSincerely,\n{sender}",
        },
        "job_application": {
            "subject": "Application for {topic}",
            "body": "Dear {recipient},\n\nI am writing to express my interest in the {topic} position advertised. With my background in {referral}, I believe I would be a valuable addition to your team.\n\nI have attached my CV for your review. I would welcome the opportunity to discuss how my skills align with your requirements.\n\nThank you for considering my application.\n\nSincerely,\n{sender}",
        },
    }

    GRAMMAR_RULES: dict[str, tuple[str, str]] = {
        r"\bi am writing to inform you that\b": ("", "Redundant phrase — get to the point directly"),
        r"\bplease do not hesitate to contact me\b": ("feel free to reach out", "Overused; simpler is better"),
        r"\bat this point in time\b": ("now", "Wordy — use 'now'"),
        r"\bdue to the fact that\b": ("because", "Wordy — use 'because'"),
        r"\bin the event that\b": ("if", "Wordy — use 'if'"),
        r"\bin spite of the fact that\b": ("although", "Wordy — use 'although'"),
        r"\bfor the purpose of\b": ("to", "Wordy — use 'to'"),
        r"\bin order to\b": ("to", "Simplify to 'to'"),
        r"\bwith regard to\b": ("regarding", "Use 'regarding' or 'about'"),
        r"\bi would like to take this opportunity to\b": ("", "Remove — unnecessary filler"),
        r"\bit is important to note that\b": ("", "Remove — state the fact directly"),
        r"\bas per your request\b": ("as you requested", "More natural phrasing"),
        r"\benclosed herewith\b": ("attached", "Use 'attached'"),
        r"\bkindly be advised\b": ("", "Remove — just state the information"),
        r"\bpertaining to\b": ("about", "Simplify to 'about'"),
        r"\bgoing forward\b": ("in future", "Or remove if unnecessary"),
        r"\bcircling back\b": ("following up", "More professional"),
        r"\btouching base\b": ("checking in", "More professional"),
        r"\bi just wanted to\b": ("I would like to", "Remove 'just' — weakens your message"),
        r"\bsorry for the delayed response\b": ("Thank you for your patience", "Reframe positively"),
    }

    TONE_INDICATORS: dict[str, list[str]] = {
        "professional": ["dear", "regards", "sincerely", "best regards", "would appreciate", "kindly"],
        "formal": ["sir", "madam", "yours faithfully", "shall", "hereby", "aforementioned"],
        "friendly": ["hi", "hello", "cheers", "thanks", "great", "awesome", "hope you're well"],
        "casual": ["hey", "what's up", "lol", "btw", "gonna", "wanna", "kinda"],
        "urgent": ["urgent", "asap", "immediately", "deadline", "critical", "action required", "time-sensitive"],
    }

    def improve_email(self, draft: str, tone: str = "professional") -> str:
        """Improve email: grammar, wording, structure."""
        original = draft
        suggestions: list[str] = []
        corrected = draft

        for pattern, (replacement, explanation) in self.GRAMMAR_RULES.items():
            if re.search(pattern, corrected, re.IGNORECASE):
                if replacement:
                    corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
                suggestions.append(f"  • '{pattern.replace('\\b', '')}' → {explanation}")

        tone_analysis = self.analyze_tone(corrected)
        dominant_tone = max(tone_analysis, key=tone_analysis.get)

        if dominant_tone != tone and tone_analysis[tone] < 0.3:
            suggestions.append(f"  • Tone appears '{dominant_tone}', adjust to '{tone}'")

        passive_count = len(re.findall(r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", corrected))
        if passive_count > 2:
            suggestions.append(f"  • {passive_count} passive voice constructions — consider active voice")

        word_count = len(corrected.split())
        if word_count > 200:
            suggestions.append(f"  • Email is {word_count} words — consider being more concise")
        if word_count < 20:
            suggestions.append(f"  • Email is only {word_count} words — may be too brief")

        lines = ["## Email Improvements\n"]
        if suggestions:
            lines.append("Suggestions:")
            lines.extend(suggestions)
        else:
            lines.append("✓ No major issues found!")

        lines.append(f"\nDetected tone: {dominant_tone} ({tone_analysis[dominant_tone]:.0%})")
        lines.append(f"Word count: {word_count}")

        if corrected != original:
            lines.append(f"\n---\n**Corrected version:**\n\n{corrected}")

        return "\n".join(lines)

    def compose_email(self, purpose: str, recipient: str, key_points: list[str], tone: str = "professional", **kwargs: Any) -> str:
        """Compose email from scratch using templates."""
        tmpl = self.TEMPLATES.get(purpose.lower(), self.TEMPLATES["follow_up"])

        sender = kwargs.get("sender", "[Your Name]")
        topic = kwargs.get("topic", " ".join(key_points[:2]) if key_points else "[Topic]")
        date = kwargs.get("date", "[Date]")
        time = kwargs.get("time", "[Time]")
        referral = kwargs.get("referral", "[Referral]")
        preventive_action = kwargs.get("preventive_action", "[Preventive action]")

        body = tmpl["body"].format(
            recipient=recipient,
            sender=sender,
            topic=topic,
            date=date,
            time=time,
            referral=referral,
            preventive_action=preventive_action,
        )
        subject = tmpl["subject"].format(topic=topic, sender=sender, recipient=recipient)

        if key_points and "{key_points}" not in body:
            body = body.replace("\n\nBest regards,", f"\n\nKey points:\n" + "\n".join(f"• {p}" for p in key_points) + "\n\nBest regards,")

        return f"**Subject:** {subject}\n\n{body}"

    def analyze_tone(self, text: str) -> dict[str, float]:
        """Detect tone with confidence scores."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for tone, indicators in self.TONE_INDICATORS.items():
            matches = sum(1 for ind in indicators if ind in text_lower)
            scores[tone] = min(1.0, matches / max(len(indicators) * 0.3, 1))

        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

    def grammar_check(self, text: str) -> list[str]:
        """Check grammar and style."""
        issues = []
        for pattern, (replacement, explanation) in self.GRAMMAR_RULES.items():
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"'{pattern.replace('\\b', '')}' → {explanation}")
        return issues

    def email_templates(self) -> list[str]:
        """List available templates."""
        return list(self.TEMPLATES.keys())

    def reply_suggestion(self, original_email: str, intent: str = "acknowledge") -> str:
        """Suggest reply based on original email."""
        suggestions = {
            "acknowledge": "Thank you for your email. I acknowledge receipt and will respond in detail shortly.",
            "accept": "Thank you for your proposal. I am happy to proceed and will take the necessary next steps.",
            "decline": "Thank you for considering me. Unfortunately, I am unable to proceed at this time, but I appreciate the opportunity.",
            "request_info": "Thank you for your email. Before I can proceed, could you please provide additional details regarding [specific request]?",
            "schedule": "Thank you for reaching out. I am available on [date] at [time]. Please let me know if this works for you.",
        }
        return suggestions.get(intent, suggestions["acknowledge"])

    def subject_line_suggest(self, topic: str, tone: str = "professional") -> list[str]:
        """Generate subject line suggestions."""
        if tone == "professional":
            return [
                f"Regarding: {topic}",
                f"Follow-up: {topic}",
                f"Action Required: {topic}",
                f"Update on {topic}",
            ]
        elif tone == "urgent":
            return [
                f"URGENT: {topic}",
                f"Immediate Attention Required: {topic}",
                f"Time-Sensitive: {topic}",
            ]
        else:
            return [
                f"Quick question about {topic}",
                f"Checking in: {topic}",
                f"{topic} — quick update",
            ]


if __name__ == "__main__":
    ea = EmailAssistant()
    draft = "I am writing to inform you that, due to the fact that the meeting is cancelled, please do not hesitate to contact me."
    print(ea.improve_email(draft))
    print("\n---\n", ea.compose_email("meeting_request", "Mr. Smith", ["Project timeline review"], topic="Project Timeline Review"))

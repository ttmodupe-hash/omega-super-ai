"""
OMEGA-LUQI Native Prompt Support Core

Students in primary/high tiers do not always write well-structured prompts.
This module wraps raw input in a context architecture (tier, lab track,
Ubuntu philosophy filter) before it reaches any AI brain.
"""


class LuqiPromptSupport:
    UBUNTU_FRAME = "Umuntu ngumuntu ngabantu"

    @staticmethod
    def enhance_student_prompt(raw_prompt: str, academic_tier: str, lab_track: str) -> str:
        """
        Transform raw student input into a structured, optimized AI prompt.
        Raises ValueError on empty input so callers can return a clean 400.
        """
        cleaned_input = (raw_prompt or "").strip()
        if not cleaned_input:
            raise ValueError("Student prompt is empty.")
        if len(cleaned_input) > 4000:
            cleaned_input = cleaned_input[:4000] + " ...[truncated]"

        return (
            "--- [PROMPT SUPPORT AUTOMATED INJECTION] ---\n"
            f"CONTEXT ARCHITECTURE: Student operates at a '{academic_tier.upper()}' capacity "
            f"inside the '{lab_track.upper()}' lab module.\n"
            f"PHILOSOPHY FILTER: Apply Ubuntu framing ('{LuqiPromptSupport.UBUNTU_FRAME}'). "
            "Translate complex jargon into highly supportive, clear, actionable steps.\n"
            f"STUDENT QUERY: \"{cleaned_input}\"\n"
            "--- [END AUTOMATED WRAPPER] ---\n"
            "Instruction: Diagnose the student's problem comprehensively using the context "
            "above. Provide a friendly, clear, and highly encouraging solution."
        )

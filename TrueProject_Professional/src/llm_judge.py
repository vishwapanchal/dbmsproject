import os
import time
from google import genai
from src.config import Config

class GeminiJudge:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY missing in .env file")
        
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.LLM_MODEL

    def get_verdict(self, new_project, similar_projects):
        """Sends data to Gemini for analysis."""
        
        # Format the evidence
        evidence_text = ""
        for i, proj in enumerate(similar_projects):
            evidence_text += f"\n[EXISTING PROJECT #{i+1}]\n"
            evidence_text += f"Title: {proj['name']}\n"
            evidence_text += f"Synopsis: {proj['synopsis'][:500]}...\n"

        # The Prompt
        prompt = f"""
        You are an expert Plagiarism Detection System for a University.
        
        === NEW STUDENT PROPOSAL ===
        Title: {new_project['title']}
        Synopsis: {new_project['synopsis']}

        === EVIDENCE (TOP MATCHES FROM DATABASE) ===
        {evidence_text}

        === TASK ===
        Compare the NEW PROPOSAL against the EVIDENCE.
        1. Determine if the core idea is copied (even if rephrased).
        2. Provide an "Originality Score" (0% = Copied, 100% = Unique).
        3. Explain your reasoning briefly.

        === OUTPUT FORMAT ===
        Verdict: [Unique / Suspicious / Plagiarized]
        Score: [0-100]%
        Reasoning: [Your analysis]
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"❌ Error contacting Gemini: {e}"

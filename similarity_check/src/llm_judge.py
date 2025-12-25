import os
import json
from openai import OpenAI
from src.config import Config

class GeminiJudge:
    def __init__(self):
        if not Config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY missing. Check src/config.py pathing.")
        
        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=Config.OPENROUTER_API_KEY,
        )
        self.model_name = Config.LLM_MODEL

    def get_verdict(self, new_project, similar_projects):
        """Sends data to the LLM and returns a JSON string."""
        
        evidence_text = ""
        for i, proj in enumerate(similar_projects):
            evidence_text += f"\n[MATCH #{i+1}]\nTitle: {proj['name']}\nSynopsis: {proj['synopsis']}\n"

        # --- UPDATED PROMPT FOR JSON OUTPUT ---
        system_prompt = (
            "You are an expert Project Reviewer. "
            "Analyze the plagiarism risk and return the result strictly as a JSON object."
        )
        
        user_prompt = f"""
        Compare this NEW PROPOSAL against EXISTING MATCHES.

        === NEW PROPOSAL ===
        Title: {new_project['title']}
        Synopsis: {new_project['synopsis']}

        === EXISTING MATCHES ===
        {evidence_text}

        === OUTPUT FORMAT ===
        Return ONLY a valid JSON object with this exact structure (no markdown formatting):
        {{
            "analysis": "Brief conceptual analysis of the new project.",
            "comparison": [
                {{
                    "match_name": "Name of Match 1",
                    "similarity_note": "How it is similar or different"
                }}
            ],
            "verdict": {{
                "status": "Unique" | "Suspicious" | "Plagiarized",
                "score": 0 to 100,
                "reasoning": "Final conclusion"
            }}
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}, # Hints to model to output JSON
                extra_headers={"HTTP-Referer": "http://localhost:3000"}
            )
            content = response.choices[0].message.content
            # Ensure it's valid JSON (or return raw if parsing fails)
            return content
            
        except Exception as e:
            # Return a JSON error structure so the DB insert doesn't fail
            return json.dumps({
                "error": f"AI Check Failed: {str(e)}",
                "verdict": {"status": "Error", "score": 0}
            })
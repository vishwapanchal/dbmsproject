import os
from openai import OpenAI
from src.config import Config

class GeminiJudge:
    def __init__(self):
        if not Config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY missing in .env file")
        
        # Initialize OpenAI client pointing to OpenRouter
        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=Config.OPENROUTER_API_KEY,
        )
        self.model_name = Config.LLM_MODEL

    def get_verdict(self, new_project, similar_projects):
        """Sends data to the LLM for deep conceptual analysis with Tabular Output."""
        
        # Format the evidence
        evidence_text = ""
        for i, proj in enumerate(similar_projects):
            evidence_text += f"\n[MATCH #{i+1}]\n"
            evidence_text += f"Title: {proj['name']}\n"
            evidence_text += f"Similarity Score: {proj.get('similarity', 'N/A')}%\n"
            evidence_text += f"Synopsis: {proj['synopsis']}\n"

        # --- REFINED PROMPT FOR TABULAR OUTPUT ---
        system_prompt = (
            "You are an expert Senior Project Reviewer and Technical Architect for a University. "
            "Your task is to detect plagiarism by comparing a NEW PROPOSAL against EXISTING PROJECTS. "
            "Focus on architectural and conceptual overlaps, not just keywords."
        )
        
        user_prompt = f"""
        === TASK ===
        Compare the "NEW PROPOSAL" against the "EXISTING MATCHES" and generate a report with a COMPARISON TABLE.

        === NEW STUDENT PROPOSAL ===
        Title: {new_project['title']}
        Synopsis: {new_project['synopsis']}

        === EXISTING MATCHES (Potential Duplicates) ===
        {evidence_text}

        === REQUIRED OUTPUT FORMAT ===
        Please strictly follow this structure:

        ### 🧠 Conceptual Analysis
        [Briefly summarize the core technical concept of the new proposal in 2-3 sentences. Identify the problem and the specific solution mechanism.]

        ### 📊 Detailed Comparison Table
        | Match Name | Similarity % | Shared Concepts (The "What") | Architectural Overlap (The "How") | Key Differences |
        | :--- | :--- | :--- | :--- | :--- |
        | [Match #1 Name] | [Score] | [e.g., Both use Face Rec for Attendance] | [e.g., Both use OpenCV + Flask] | [e.g., New project adds GPS geofencing] |
        | [Match #2 Name] | [Score] | ... | ... | ... |
        
        *(If a column is not applicable or the match is irrelevant, state "None" or "Low relevance")*

        ### ⚖️ Final Verdict
        | Metric | Result |
        | :--- | :--- |
        | **Status** | **[Unique / Suspicious / Plagiarized]** |
        | **Originality Score** | **[0-100]%** |
        
        **Reasoning:**
        [Provide a final concluding paragraph justifying the score based on the table above.]
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2, # Low temperature for precise formatting
                extra_headers={
                    "HTTP-Referer": "https://localhost:3000", 
                    "X-Title": "TrueProject Checker"
                }
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Error contacting AI Judge: {e}"
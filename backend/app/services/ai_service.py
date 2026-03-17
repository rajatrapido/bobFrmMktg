import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("models/gemini-2.5-flash")

    def get_summary(self, report_data, timeline_context):
        if not self.api_key:
            return "<b>AI Summary (Mock):</b> Performance looks stable with consistent install volume. Recommend monitoring cost-per-install trends for next week."
        
        try:
            import json
            report_str = json.dumps(report_data, default=str)
            
            prompt = f"""
            You are an expert marketing performance analyst.
            Your task is to analyze the provided weekly performance report data and generate a professional, visually appealing SUMMARY using strict Markdown format.
            The data includes Pan-India metrics, city-first significant movers, campaign/adgroup insights, and auto-generated todos.

            **REPORT DATA (JSON):**
            ---
            {report_str}
            ---

            **YOUR TASK:**
            Generate a complete actionable insights report. Do NOT use HTML tables, use Markdown formats. Use emojis to indicate positive/negative trends.

            **CONTENT AND STRUCTURE RULES:**
            1. **Executive Summary**: A brief high-level summary of Pan-India performance (WoW growth).
            2. **Key Movers**: Highlight the most significant positive and negative Ad Groups or Cities based on the data.
            3. **Root-Cause Signals**: Explain likely movement drivers using CTR/CTI/CPC style shifts and trend windows.
            4. **Actionable Recommendations**: Convert high-impact insights into prioritized actions.
            
            Return ONLY the Markdown content. Do not include markdown code block backticks around the entire output.
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"AI Summary generation failed: {e}")
            return f"**AI Summary Error:** Could not generate full insights. Exception: {e}"

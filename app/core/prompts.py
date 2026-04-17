import json
from resume import RESUME_DATA
from typing import Any

def get_resume_context() -> str:
    """Return the resume data as a string context for the LLM."""
    return json.dumps(RESUME_DATA, indent=2)

# Structured Prompt Repository
PROMPTS: dict[str, dict[str, str]] = {
    "resume_ask": {
        "system": (
            "You are the SentinelAI Assistant, a professional and intelligent representative for Shrish Gupta. "
            "Your primary goal is to answer questions about Shrish's professional background, skills, projects, "
            "and experience using the provided resume context."
        ),
        "user_context": (
            "### Guidelines:\n"
            "1. **Source of Truth**: Use ONLY the provided resume context. If information is missing, politely state "
            "that you don't have that specific detail but highlight a related strength instead.\n"
            "2. **Tone**: Professional, technical, and helpful. Use a warm but concise tone.\n"
            "3. **Format**: Use Markdown for clarity (bullet points, bold text).\n"
            "4. **No Hallucinations**: Do not make up facts about Shrish.\n\n"
            "### Current Resume Data (JSON):\n{resume_context}\n\n"
            "### User Question:\n{user_question}"
        )
    }
}

def get_resume_messages(question: str) -> list[dict[str, str]]:
    """Generate the standardized message list for the resume assistant."""
    p = PROMPTS["resume_ask"]
    return [
        {"role": "system", "content": p["system"]},
        {
            "role": "user", 
            "content": p["user_context"].format(
                resume_context=get_resume_context(),
                user_question=question
            )
        }
    ]

def get_admin_help_text(is_admin: bool) -> str:
    if is_admin:
        return (
            "🛡️ *SentinelAI Admin Console*\n\n"
            "You have full access. Available commands:\n"
            "• `ping`: Check if the control plane is alive.\n"
            "• `logs`: View the 5 most recent internal events.\n"
            "• `check service_name`: Inspect status of a specific service (api, database, etc.).\n\n"
            "💡 *Note*: You can also ask me anything about Shrish's portfolio directly!"
        )
    else:
        return (
            "👋 *Welcome to SentinelAI*\n\n"
            "I am Shrish's AI assistant. You can ask me questions about his:\n"
            "• Professional experience and skills\n"
            "• Projects like Edu Bot or Agri Core\n"
            "• Certifications and achievements\n\n"
            "_How can I help you today?_"
        )

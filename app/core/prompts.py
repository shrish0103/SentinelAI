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
            "1. **Clean Formatting**: Do NOT use Markdown tables. Use simple bullet points or numbered lists instead.\n"
            "2. **No Excessive Bolding**: Use bold text sparingly for key terms only. Do not bold entire paragraphs.\n"
            "3. **Tone**: Professional and concise. Limit response to 3-4 short paragraphs maximum.\n"
            "4. **Source of Truth**: Use ONLY the provided resume context. If information is missing, state it clearly.\n\n"
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
            "🛡️ *Hello Admin! Welcome to the Control Plane.*\n\n"
            "You have elevated permissions to monitor and manage SentinelAI systems.\n\n"
            "🚀 *Core Commands*\n"
            "• `/ping` - Show all service aliases and URLs.\n"
            "• `/ping <alias>` - Ping a specific service.\n"
            "• `/logs [n]` - View last `n` system audit logs.\n\n"
            "🧪 *Testing*\n"
            "• `/test telegram` - Verify alert delivery pipeline.\n"
            "• `/test llm` - Live check of AI provider connectivity.\n\n"
            "💡 *Tip*: You can also type any question about Shrish's portfolio. To see the guest menu, type `/help_guest`."
        )
    else:
        return (
            "👋 *Shrish Gupta's Portfolio Assistant*\n\n"
            "I'm an AI representative for Shrish. Use the commands below to explore his background, or just type a question directly!\n\n"
            "📂 *Portfolio Access*\n"
            "• `/resume` - Request a summary + PDF copy.\n"
            "• `/projects` - Explore his curated builds.\n"
            "• `/education` - Check academic history.\n\n"
            "🤖 *AI Capability (Mode Switch)*\n"
            "• `/ai on` - Enable **General AI Mode** (I will answer anything with full intelligence).\n"
            "• `/ai off` - Return to **Portfolio Mode** (Shrish's personal assistant).\n\n"
            "🎭 *Try the Control Plane (Demo)*\n"
            "Want to see how Shrish monitors his backend infrastructure? Type `/demo on` to enter **Demo Mode**.\n"
            "This unlocks a simulated 'Admin Dashboard' where you can use:\n"
            "• `/logs` - View mock system audit logs.\n"
            "• `/ping` - Check status of registered services (LLM, DB, Cache).\n\n"
            "💡 *Note*: You can also just ask things like _'Where does Shrish work?'_ or _'Tell me about his B.Tech projects.'_"
        )

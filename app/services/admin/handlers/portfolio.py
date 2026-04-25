import os
from services.admin.interfaces import CommandHandler, CommandContext, CommandResult, LLMServiceProtocol
from services.admin.registry import action_registry
from core.config import Settings
import logging

logger = logging.getLogger(__name__)

@action_registry.register("resume", "education", "projects", "certifications")
class PortfolioHandler(CommandHandler):
    def __init__(self, settings: Settings, llm_service: LLMServiceProtocol) -> None:
        self._settings = settings
        self._llm_service = llm_service

    async def handle(self, ctx: CommandContext) -> CommandResult:
        intent = ctx.intent
        
        # 1. SPECIAL CASE: /resume (Returns PDF + AI Summary)
        if intent == "resume":
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            pdf_path = os.path.join(base_dir, "resume.pdf") # PDF is at app/resume.pdf
            
            # Use AI to generate a concise 3-sentence professional summary
            summary, _, _ = await self._llm_service.answer_question(
                "Provide a high-impact, 3-sentence professional summary of Shrish's profile for a recruiter."
            )
            
            message = f"📄 *Shrish Gupta's Professional Profile*\n\n{summary}\n\n👇 *I have uploaded my latest resume.pdf for you below.*"
            
            # Check if file exists, if not, send just the summary
            doc_path = pdf_path if os.path.exists(pdf_path) else None
            if not doc_path:
                message += "\n\n⚠️ _Note: resume.pdf not found on server. Please check environment._"
                
            return CommandResult(success=True, message=message, document_path=doc_path)

        # 2. DYNAMIC PORTFOLIO QUESTIONS (Grounded AI)
        query_map = {
            "education": "Summarize Shrish's academic background, listing IMSEC Ghaziabad and key achievements.",
            "projects": "List Shrish's top 3 most significant projects including SentinelAI, explaining his role and the technology stack.",
            "certifications": "List Shrish's professional certifications and technical courses."
        }
        
        query = query_map.get(intent, f"Explain Shrish's {intent}.")
        
        # Call LLM with Resume Grounding
        answer, model, is_fallback = await self._llm_service.answer_question(query)
        
        emoji_map = {"education": "🎓", "projects": "🚀", "certifications": "📜"}
        emoji = emoji_map.get(intent, "📄")
        
        header = f"{emoji} *{intent.upper()}*\n\n"
        return CommandResult(success=True, message=header + answer)

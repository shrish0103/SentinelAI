from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/privacy-policy", response_class=HTMLResponse, tags=["meta"])
async def privacy_policy() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>SentinelAI Privacy Policy</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                margin: 0;
                background: #0f172a;
                color: #e2e8f0;
            }
            main {
                max-width: 760px;
                margin: 0 auto;
                padding: 48px 20px 72px;
            }
            h1, h2 {
                color: #f8fafc;
            }
            .card {
                background: #111827;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 24px;
                margin-top: 24px;
            }
            p, li {
                line-height: 1.7;
            }
        </style>
    </head>
    <body>
        <main>
            <h1>SentinelAI Privacy Policy</h1>
            <p>
                SentinelAI processes only the information required to provide alert
                notifications, health checks, AI assistant responses, and owner-restricted
                administrative actions.
            </p>

            <section class="card">
                <h2>What SentinelAI May Process</h2>
                <ul>
                    <li>Telegram user IDs for access control</li>
                    <li>Messages or commands sent to the bot</li>
                    <li>Operational logs related to alerts, health checks, and AI provider failures</li>
                </ul>
            </section>

            <section class="card">
                <h2>What SentinelAI Does Not Intend to Do</h2>
                <ul>
                    <li>Collect unnecessary personal data</li>
                    <li>Share personal data with unrelated third parties</li>
                </ul>
            </section>

            <section class="card">
                <h2>Access Control</h2>
                <p>
                    Owner-only actions are restricted using Telegram user ID checks.
                </p>
            </section>

            <section class="card">
                <h2>Retention</h2>
                <p>
                    Operational data may be retained only as needed for debugging,
                    monitoring, and service reliability.
                </p>
            </section>

            <section class="card">
                <h2>Contact</h2>
                <p>
                    For questions about this bot, contact the bot owner.
                </p>
            </section>
        </main>
    </body>
    </html>
    """

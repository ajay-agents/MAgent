import json
from openai import OpenAI

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)

PURPOSE_INSTRUCTIONS = {
    "cold_outreach": (
        "Write a cold sales/outreach email. The goal is to introduce the sender, "
        "establish relevance to the recipient's business, and propose a specific next step "
        "(demo, call, or reply). Keep it concise — no generic fluff."
    ),
    "follow_up": (
        "Write a follow-up email after a previous conversation or meeting. "
        "Reference the prior interaction naturally, restate the key value or action item, "
        "and make it easy for the recipient to respond or move forward."
    ),
    "job_application": (
        "Write a job application email. The sender is applying for a role. "
        "Highlight the most relevant experience, express genuine enthusiasm for the company, "
        "and close with a clear call to action (interview request or portfolio link)."
    ),
    "networking": (
        "Write a networking email. The goal is to open a relationship — not to ask for a job "
        "or sell anything. Establish shared context or mutual interest, be specific about why "
        "this particular person is worth reaching out to, and propose a low-friction connection "
        "(coffee chat, quick call, or async exchange)."
    ),
    "partnership": (
        "Write a business partnership or collaboration proposal email. Clearly describe what "
        "the sender does, why the recipient is a natural partner, and what a partnership would "
        "look like concretely. End with a specific proposal or question."
    ),
    "thank_you": (
        "Write a thank-you / appreciation email. Be specific about what is being appreciated, "
        "why it mattered, and if appropriate, how the sender intends to stay in touch or "
        "reciprocate. Warm but not effusive."
    ),
}

LENGTH_INSTRUCTIONS = {
    "short": "Keep the email under 100 words. Be punchy and direct.",
    "medium": "Aim for 150–200 words. Cover the key points without padding.",
    "long": "Aim for 250–350 words. Give enough detail to be compelling, but no filler.",
}

TONE_INSTRUCTIONS = {
    "professional": "Tone: professional and polished, but not stiff.",
    "friendly": "Tone: warm and personable — reads like it's from a real human, not a template.",
    "formal": "Tone: formal and respectful — appropriate for C-suite or academic contexts.",
    "casual": "Tone: conversational and relaxed — like messaging a smart colleague.",
    "persuasive": "Tone: confident and persuasive — makes a compelling case without being pushy.",
}

SYSTEM_PROMPT = """You are an expert email copywriter. You write emails that sound like they came
from a real person — specific, human, and direct. You never use hollow openers like
"I hope this email finds you well" or "I wanted to reach out". You always return a JSON object
with exactly two keys: "subject" (a concise email subject line) and "body" (the full email body,
plain text, no markdown, no placeholders in square brackets)."""


def generate_email(
    purpose: str,
    tone: str,
    length: str,
    sender_name: str,
    recipient_name: str,
    recipient_email: str,
    context: str | None,
) -> dict:
    purpose_instr = PURPOSE_INSTRUCTIONS.get(purpose, PURPOSE_INSTRUCTIONS["cold_outreach"])
    tone_instr = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
    length_instr = LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["medium"])

    user_prompt = f"""{purpose_instr}

{tone_instr}
{length_instr}

Sender: {sender_name}
Recipient: {recipient_name} ({recipient_email})
{f'Additional context: {context}' if context else ''}

Return only valid JSON with keys "subject" and "body"."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    result = json.loads(response.choices[0].message.content)
    if "subject" not in result or "body" not in result:
        raise ValueError("OpenAI returned unexpected JSON structure")
    return result

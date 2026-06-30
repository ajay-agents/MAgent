import json
from pathlib import Path
from openai import OpenAI

from app.config import settings

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_prompt_cache: dict[str, dict] = {}


def _load_prompt(purpose: str) -> dict:
    """
    Load and parse a purpose .txt file, cached after first read.
    Returns a dict with keys: instruction, example_user, example_assistant.
    File format uses --- SECTION --- delimiters.
    """
    if purpose not in _prompt_cache:
        path = _PROMPTS_DIR / f"{purpose}.txt"
        if not path.exists():
            raise ValueError(f"No prompt file found for purpose '{purpose}' at {path}")

        raw = path.read_text(encoding="utf-8")
        sections: dict[str, str] = {}
        current_key = None
        current_lines: list[str] = []

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("--- ") and stripped.endswith(" ---"):
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = stripped[4:-4].strip().lower()
                current_lines = []
            else:
                current_lines.append(line)

        if current_key:
            sections[current_key] = "\n".join(current_lines).strip()

        required = {"instruction", "example_user", "example_assistant"}
        missing = required - sections.keys()
        if missing:
            raise ValueError(f"Prompt file for '{purpose}' is missing sections: {missing}")

        _prompt_cache[purpose] = sections

    return _prompt_cache[purpose]

client = OpenAI(api_key=settings.openai_api_key)

# GPT-4o-mini pricing (USD per token)
_MODEL = "gpt-4o-mini"
_COST_PER_INPUT_TOKEN  = 0.150 / 1_000_000   # $0.150 per 1M input tokens
_COST_PER_OUTPUT_TOKEN = 0.600 / 1_000_000   # $0.600 per 1M output tokens


def _calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        prompt_tokens * _COST_PER_INPUT_TOKEN + completion_tokens * _COST_PER_OUTPUT_TOKEN,
        8,
    )

LENGTH_INSTRUCTIONS = {
    "short": "Length: under 100 words. Be punchy and direct — every sentence must earn its place.",
    "medium": "Length: 150–200 words. Cover the key points without padding. Cut anything that doesn't move the email forward.",
    "long": "Length: 250–350 words. Give enough detail to be compelling, but cut all filler. More words must mean more value.",
}

TONE_INSTRUCTIONS = {
    "professional": "Tone: professional and polished, but not stiff. Reads like a senior person who respects the recipient's time.",
    "friendly": "Tone: warm and personable — reads like it came from a real human, not a template. Natural contractions, approachable sentences.",
    "formal": "Tone: formal and respectful. Appropriate for C-suite executives, academic contacts, or high-stakes introductions.",
    "casual": "Tone: conversational and relaxed — like messaging a smart colleague you already have rapport with.",
    "persuasive": "Tone: confident and persuasive. Makes a compelling case through specificity and evidence, not pressure or hype.",
}

SYSTEM_PROMPT = (
    "You are an expert email copywriter. You write emails that sound like they came from a real person — "
    "specific, human, and direct. Every email you write passes this test: could it only have been sent to this "
    "specific recipient, or does it read like a template with names swapped in? It must pass.\n\n"
    "Hard rules that apply to every email:\n"
    "- Never open with 'I hope this email finds you well', 'I hope you're doing well', or any variant.\n"
    "- Never open with 'I wanted to reach out' or 'I am reaching out'.\n"
    "- Never use placeholder text in square brackets like [your company] or [specific example].\n"
    "- Never use markdown formatting — plain text only.\n"
    "- The subject line must be specific, not a category label.\n\n"
    "Return a JSON object with exactly two keys: "
    "\"subject\" (a concise, specific subject line) and \"body\" (the full email body, plain text)."
)


def generate_email(
    purpose: str,
    tone: str,
    length: str,
    sender_name: str,
    recipient_name: str,
    recipient_email: str,
    context: str | None,
) -> dict:
    prompt = _load_prompt(purpose)
    tone_instr = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
    length_instr = LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["medium"])

    user_prompt = (
        f"{prompt['instruction']}\n\n"
        f"{tone_instr}\n"
        f"{length_instr}\n\n"
        f"Sender: {sender_name}\n"
        f"Recipient: {recipient_name} ({recipient_email})\n"
        + (f"Context: {context}\n" if context else "")
        + "\nReturn only valid JSON with keys \"subject\" and \"body\"."
    )

    messages = [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": prompt["example_user"]},
        {"role": "assistant", "content": prompt["example_assistant"]},
        {"role": "user",      "content": user_prompt},
    ]

    response = client.chat.completions.create(
        model=_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    result = json.loads(response.choices[0].message.content)
    if "subject" not in result or "body" not in result:
        raise ValueError("OpenAI returned unexpected JSON structure")

    usage = response.usage
    result["ai_model"] = _MODEL
    result["prompt_tokens"] = usage.prompt_tokens
    result["completion_tokens"] = usage.completion_tokens
    result["total_tokens"] = usage.total_tokens
    result["estimated_cost_usd"] = _calculate_cost(usage.prompt_tokens, usage.completion_tokens)
    return result

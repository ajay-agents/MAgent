import json
from openai import OpenAI

from app.config import settings

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

PURPOSE_INSTRUCTIONS = {
    "cold_outreach": (
        "Write a cold outreach email. This is first contact with someone who has no prior relationship with the sender.\n"
        "Your job:\n"
        "- Open with a specific, research-backed hook about the recipient's business — something observed about their product, "
        "a recent launch, a growth signal, or a gap you noticed. Not a generic compliment.\n"
        "- Establish a clear relevance bridge: why the sender's solution maps to this recipient's exact situation right now.\n"
        "- Include a social proof signal — comparable companies or a quantified outcome.\n"
        "- Close with exactly one low-friction ask: a 20-minute call, a reply, or a demo. Not three options.\n"
        "Never write: 'I hope this email finds you well', 'I wanted to reach out', "
        "'We help companies like yours', or any opening that could apply to anyone."
    ),

    "follow_up": (
        "Write a follow-up email after a prior conversation or meeting.\n"
        "Your job:\n"
        "- Reference the prior interaction naturally and specifically — the date, topic, or key moment. "
        "Never write 'as per my last email' or 'just circling back'.\n"
        "- Restate the single most important takeaway from that conversation in one sentence.\n"
        "- If the recipient raised an objection or blocker (legal review, budget check, timing), "
        "address it directly with a concrete resolution — don't ignore it.\n"
        "- Close with one concrete next step that is easy to accept: a specific time, a document to send, a short call.\n"
        "Never: 'Bumping this to the top of your inbox', 're-explaining the full pitch', "
        "or any opener that doesn't reference the prior conversation."
    ),

    "job_application": (
        "Write a job application email. The sender is applying for a role at the recipient's company.\n"
        "Your job:\n"
        "- Lead with the most relevant experience signal — not a career timeline, but the single strongest "
        "credential that directly maps to what this company needs.\n"
        "- Show specific knowledge of the company: a product decision, a public direction, a piece of their work "
        "that demonstrates real attention — not generic admiration.\n"
        "- Include measurable impact where possible (users reached, scale, outcome achieved).\n"
        "- Close with a clear, direct ask: an interview, a portfolio link, or a technical screen.\n"
        "Never write: 'I am writing to express my interest in the role of', "
        "'I've always admired your company', or a chronological career summary in paragraph form."
    ),

    "networking": (
        "Write a networking email to open a relationship. There is no ask, no sale, no job inquiry.\n"
        "Your job:\n"
        "- Establish a specific, genuine trigger for reaching out: a talk attended, an essay read, "
        "a problem space in common, or a mutual connection — be precise about what it was.\n"
        "- Show why this particular person is worth reaching out to, not just anyone in their field.\n"
        "- Propose something low-commitment and easy to accept: a short call, a coffee, "
        "or even just an async exchange of notes.\n"
        "- End without an agenda. The email should feel like genuine curiosity, not a setup.\n"
        "Never mention jobs, sales, favors, or 'picking your brain'. "
        "Never open with a long preamble before getting to the point."
    ),

    "partnership": (
        "Write a business partnership or collaboration proposal email.\n"
        "Your job:\n"
        "- Name the overlap explicitly: the same buyer segment, a complementary product, "
        "a shared market gap that neither company can close alone.\n"
        "- Quantify the opportunity if the context provides data — even a rough estimate is better than nothing.\n"
        "- Propose a concrete, equal first step: a scoping call, a pilot, a joint intro. "
        "Treat the recipient as a peer with equal leverage, not a prospect.\n"
        "- Make clear there is no product overlap — the value is in the combination, not competition.\n"
        "Never: vague synergy language, treating the email like a sales pitch, "
        "or writing 'we'd love to explore a mutually beneficial relationship'."
    ),

    "thank_you": (
        "Write a thank-you email to express genuine appreciation.\n"
        "Your job:\n"
        "- Name exactly what is being appreciated — not 'your help' or 'your support', "
        "but the specific thing the person did.\n"
        "- State the concrete impact: what changed, what was made possible, why it mattered.\n"
        "- Acknowledge what it cost the recipient — their time, their social capital, their effort.\n"
        "- If a reciprocity offer fits naturally, make it. If it doesn't, leave it out entirely.\n"
        "- End warmly and briefly. No ask, no business agenda bundled in.\n"
        "Never write: 'I just wanted to reach out and say thank you so much', "
        "a long recap of the history before getting to the thanks, or pad the email with pleasantries."
    ),
}

# Few-shot examples: one (user_prompt, assistant_response) pair per purpose.
# Injected into the messages array so the model sees a quality target before generating.
PURPOSE_EXAMPLES = {
    "cold_outreach": (
        # user turn
        (
            "Write a cold outreach email.\n"
            "Tone: professional and polished, but not stiff.\n"
            "Length: 150–200 words.\n\n"
            "Sender: Sarah Chen\n"
            "Recipient: Marcus Webb (marcus@kapture.com)\n"
            "Context: They recently launched a new pricing page with a usage-based toggle. "
            "We build activation analytics that show where trial users drop off by pricing tier."
        ),
        # assistant turn
        (
            '{"subject": "One gap in your trial funnel",'
            ' "body": "Your new pricing page is sharp — the three-tier layout with the usage-based toggle is the right call.'
            ' The gap I keep seeing after redesigns like this: trial signups go up, but activation doesn\'t follow,'
            ' because the in-product onboarding hasn\'t been updated to reflect the new value props.\\n\\n'
            'We build activation analytics that show exactly where trial users drop off relative to the pricing tier'
            ' they signed up on. Three companies that went through similar pricing relaunches saw 18–25% improvement'
            ' in trial-to-paid within 90 days.\\n\\n'
            'Worth a 20-minute walkthrough this week? I can show you what your funnel probably looks like'
            ' before you\'ve even connected your data.\\n\\nSarah"}'
        ),
    ),

    "follow_up": (
        (
            "Write a follow-up email.\n"
            "Tone: professional and polished, but not stiff.\n"
            "Length: 150–200 words.\n\n"
            "Sender: Jordan Kim\n"
            "Recipient: Priya Sharma (priya@meridiancorp.com)\n"
            "Context: Spoke last Tuesday about automating their contract renewal workflow. "
            "They were interested but said they needed to check with legal before moving forward."
        ),
        (
            '{"subject": "Following up — contract renewal workflow",'
            ' "body": "Hi Priya,\\n\\n'
            'Quick follow-up from Tuesday. The key number we landed on: your team is spending approximately'
            ' 6 hours per contract renewal coordinating across legal, finance, and the account team —'
            ' and that compounds fast at your renewal volume.\\n\\n'
            'On the legal sign-off question you raised — we have a standard DPA ready to share,'
            ' and two customers in regulated industries have already run it through their legal teams.'
            ' Happy to loop in your counsel directly so they can compare notes rather than starting from scratch.\\n\\n'
            'Should I send the DPA over, or would it be easier to do a 20-minute call with your legal contact this week?\\n\\n'
            'Jordan"}'
        ),
    ),

    "job_application": (
        (
            "Write a job application email.\n"
            "Tone: professional and polished, but not stiff.\n"
            "Length: 150–200 words.\n\n"
            "Sender: Alex Rivera\n"
            "Recipient: Karri Saarinen (karri@linear.app)\n"
            "Context: Applying for a senior product designer role. 5 years experience focused on developer tools. "
            "Led the design system used across 8 product teams at my last company. "
            "Obsessed with Linear's keyboard-first interface decisions, especially the v2 issues view redesign."
        ),
        (
            '{"subject": "Senior Product Designer — 5 years, design systems, developer tools",'
            ' "body": "Hi Karri,\\n\\n'
            'The issues view redesign you shipped in v2 — specifically the way keyboard navigation and'
            ' filter composition work together — is the best interface decision I\'ve seen in a developer tool in years.'
            ' That\'s the kind of craft I\'ve been building toward.\\n\\n'
            'Quick background: I\'m a senior product designer with five years focused exclusively on developer tools.'
            ' At my last company I built and owned the design system used across eight product teams.'
            ' Before that I spent two years at a Series A devtools company leading the redesign of the core workflow'
            ' from scratch, which shipped to 40k daily active developers.\\n\\n'
            'I\'m looking for a place where the bar for craft is set that high.'
            ' Portfolio is at alexrivera.design — happy to do a technical design review whenever works.\\n\\nAlex"}'
        ),
    ),

    "networking": (
        (
            "Write a networking email.\n"
            "Tone: warm and personable.\n"
            "Length: 150–200 words.\n\n"
            "Sender: David Park\n"
            "Recipient: Charity Majors (charity@honeycomb.io)\n"
            "Context: Read her essay on team topology and cognitive load in software organizations. "
            "I'm a VP of Engineering at a 40-person startup working through the same 30-to-100 engineer inflection point she described."
        ),
        (
            '{"subject": "Your team topology essay — it changed something",'
            ' "body": "Hi Charity,\\n\\n'
            'Your piece on team topology and cognitive load has been sitting with me for three months.'
            ' The section on how platform teams create silent dependencies that feel like productivity until they don\'t —'
            ' I\'ve been using that framing in every engineering org conversation I\'ve had since.\\n\\n'
            'I\'m a VP of Engineering at an early-stage company (~40 engineers).'
            ' I\'m working through the same 30-to-100 inflection point you described, and I\'m still finding the right answers.\\n\\n'
            'No ask — I just wanted to say the writing landed.'
            ' If you ever wanted to compare notes with someone living this in real time, I\'d be glad to.\\n\\nDavid"}'
        ),
    ),

    "partnership": (
        (
            "Write a partnership proposal email.\n"
            "Tone: professional and polished, but not stiff.\n"
            "Length: 150–200 words.\n\n"
            "Sender: Emma Torres\n"
            "Recipient: Tom Bradley (tom@ledgerhq.com)\n"
            "Context: We make expense management software (ClearSpend). They make accounting software (Ledger). "
            "Same mid-market buyer. 34% of our customers already use Ledger. "
            "They currently export CSV from us and manually import into Ledger every month — our #1 support ticket."
        ),
        (
            '{"subject": "ClearSpend + Ledger — our users are doing this manually",'
            ' "body": "Hi Tom,\\n\\n'
            'A data point: 34% of our mid-market customers have Ledger in their accounting stack.'
            ' Every month they export a CSV from ClearSpend and manually import it into Ledger —'
            ' 40 minutes per finance admin per month, and our #1 support ticket category.\\n\\n'
            'This is a clean native integration play. Your team gets distribution into 1,200 mid-market finance teams.'
            ' Our users get a workflow they\'ve been requesting since launch.'
            ' No product overlap — our data layer sits underneath your workflows, not alongside them.\\n\\n'
            'The technical lift is modest on both sides.'
            ' Would your partnerships team be open to a 30-minute scoping call?'
            ' Happy to bring our CTO if it\'s useful.\\n\\nEmma"}'
        ),
    ),

    "thank_you": (
        (
            "Write a thank-you email.\n"
            "Tone: warm and personable.\n"
            "Length: under 100 words.\n\n"
            "Sender: Nina Patel\n"
            "Recipient: Ben Morrison (ben@bmorrison.com)\n"
            "Context: Ben introduced me to an investor named Anya. We had three weeks of runway left. "
            "That introduction turned into a term sheet in 11 days — she's leading our seed round."
        ),
        (
            '{"subject": "That introduction mattered more than you know",'
            ' "body": "Hi Ben,\\n\\n'
            'I wanted to write this properly rather than send a Slack message.\\n\\n'
            'The introduction to Anya came at exactly the right moment — we had three weeks of runway'
            ' and were running out of warm paths to investors who understood developer infrastructure.'
            ' That conversation turned into a term sheet in 11 days, and she\'s leading our seed round.\\n\\n'
            'You didn\'t have to spend that capital on us. I didn\'t take it lightly.\\n\\n'
            'When there\'s someone in my network you\'d want to know, the offer is open — just say the word.\\n\\nNina"}'
        ),
    ),
}

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
    purpose_instr = PURPOSE_INSTRUCTIONS.get(purpose, PURPOSE_INSTRUCTIONS["cold_outreach"])
    tone_instr = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
    length_instr = LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["medium"])

    user_prompt = (
        f"{purpose_instr}\n\n"
        f"{tone_instr}\n"
        f"{length_instr}\n\n"
        f"Sender: {sender_name}\n"
        f"Recipient: {recipient_name} ({recipient_email})\n"
        + (f"Context: {context}\n" if context else "")
        + "\nReturn only valid JSON with keys \"subject\" and \"body\"."
    )

    example = PURPOSE_EXAMPLES.get(purpose)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if example:
        example_user, example_assistant = example
        messages.append({"role": "user", "content": example_user})
        messages.append({"role": "assistant", "content": example_assistant})
    messages.append({"role": "user", "content": user_prompt})

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

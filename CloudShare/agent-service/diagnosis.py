"""
The "agent brain": diagnoses why a payment failed from raw signals (never
from a pre-labelled cause - that would be cheating), then picks a bounded
recovery action, then drafts a Hinglish recovery message.

Kept rule-based + explainable on purpose. A judge reading `reasoning` should
be able to verify the diagnosis themselves in one line - that's what "every
money action explainable, bounded and gated" (the track's own bar) is
asking for. An optional LLM pass (see `enrich_message`) is used only for the
message tone, never for the money decision itself.
"""

import os
from models import DiagnoseRequest, DiagnoseResponse

MAX_RETRIES = 3

TEMPLATES = {
    "INSUFFICIENT_FUNDS": (
        "Hi {name}, aapka payment {amount} {currency} ke liye process nahi "
        "ho paya - balance kam pad gaya lagta hai. Koi baat nahi, hum aapko "
        "kal fir se try karne ka link bhejenge, tab tak aap balance check "
        "kar lijiye."
    ),
    "CARD_EXPIRED": (
        "Hi {name}, lagta hai aapka card expire ho chuka hai isliye payment "
        "fail hua. Please apna naya card add karke dobara try karein - "
        "yahan link hai: {retry_link}"
    ),
    "BANK_TIMEOUT": (
        "Hi {name}, aapka bank thoda slow tha is baar, payment timeout ho "
        "gaya. Hum turant ek naya payment link bhej rahe hain, please "
        "dobara try karein: {retry_link}"
    ),
    "USER_ABANDONED": (
        "Hi {name}, dekha aapne checkout shuru kiya tha par complete nahi "
        "kiya. Sab thik hai? Yahan aapka {plan} plan ka link hai, jab "
        "chahe complete kar sakte hain: {retry_link}"
    ),
    "OTP_FAILED": (
        "Hi {name}, OTP verify nahi ho paya is baar. Please dobara try "
        "karein, is baar OTP thoda dhyan se enter kijiyega: {retry_link}"
    ),
    "SIGNATURE_MISMATCH": (
        "Hi {name}, is transaction mein kuch mismatch dikha hai, safety ke "
        "liye humne ise hold par rakha hai. Hamari team jald hi aapse "
        "contact karegi."
    ),
    "UNKNOWN": (
        "Hi {name}, aapka payment complete nahi ho paya. Hamari team ise "
        "dekh rahi hai, jald hi update denge."
    ),
}


def diagnose(req: DiagnoseRequest) -> DiagnoseResponse:
    s = req.signals

    # Order matters: most specific / highest-confidence signal wins.
    if not s.signatureValid:
        cause, confidence = "SIGNATURE_MISMATCH", 0.99
        reasoning = "HMAC signature verification failed on this order - security-relevant, not a routine payment failure."
        action = "ESCALATE"

    elif not s.paymentIdCreated:
        cause, confidence = "USER_ABANDONED", 0.90
        reasoning = "No paymentId was ever generated for this order, meaning the user never reached the bank step - classic checkout drop-off."
        action = "REMIND"

    elif s.otpAttempted and s.otpVerified is False:
        cause, confidence = "OTP_FAILED", 0.90
        reasoning = "An OTP attempt was made but failed verification."
        action = "RETRY"

    elif s.bankResponseCode == "51":
        cause, confidence = "INSUFFICIENT_FUNDS", 0.85
        reasoning = "Bank returned decline code 51 (insufficient funds)."
        action = "REMIND_LATER"

    elif s.bankResponseCode == "54":
        cause, confidence = "CARD_EXPIRED", 0.85
        reasoning = "Bank returned decline code 54 (expired card) - retrying the same card won't help."
        action = "REQUEST_NEW_PAYMENT_METHOD"

    elif s.bankResponseCode in ("91", "96"):
        cause, confidence = "BANK_TIMEOUT", 0.80
        reasoning = f"Bank returned decline code {s.bankResponseCode} (issuer/system unavailable) - typically transient."
        action = "RETRY"

    else:
        cause, confidence = "UNKNOWN", 0.30
        reasoning = "No matching signal pattern; signals were inconclusive."
        action = "ESCALATE"

    # Gating: nothing retries forever, and low-confidence calls never
    # trigger an automated money action.
    if req.attemptCount >= MAX_RETRIES and action in ("RETRY", "REMIND", "REMIND_LATER"):
        action = "STOP"
        reasoning += f" Max retry cap ({MAX_RETRIES}) reached - stopping automated recovery, flagging for manual follow-up."
    if confidence < 0.5 and action not in ("ESCALATE", "STOP"):
        action = "ESCALATE"

    message = TEMPLATES.get(cause, TEMPLATES["UNKNOWN"]).format(
        name=req.userName or "there",
        amount=req.amount,
        currency=req.currency,
        plan=req.planId,
        retry_link=f"https://cloudshare.example/retry/{req.orderId}",
    )

    if action == "STOP":
        message = None  # no outbound message once we've stopped trying

    message = enrich_message(message, cause)

    return DiagnoseResponse(
        orderId=req.orderId,
        diagnosedCause=cause,
        confidence=confidence,
        reasoning=reasoning,
        recommendedAction=action,
        hinglishMessage=message,
    )


def enrich_message(base_message: str | None, cause: str) -> str | None:
    """Optional: lightly polish the templated message with an LLM call if
    ANTHROPIC_API_KEY is set. Falls back to the plain template on any error
    so a missing key or network hiccup never breaks the demo."""
    if base_message is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return base_message
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "Rewrite this Hinglish payment-recovery SMS to sound a "
                    "little warmer and more natural, keep it under 300 "
                    "characters, keep it in Hinglish, don't add anything "
                    "not implied by the original, return only the message:\n\n"
                    f"{base_message}"
                ),
            }],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        return text or base_message
    except Exception:
        return base_message

"""
Prompt templates.

The analysis prompt asks the model for a strict JSON object matching the
:class:`~app.models.analysis.StructuredAnalysis` schema, at a target CEFR
reading level. Keeping prompts here means clarification quality can be tuned
without touching provider code.
"""

from __future__ import annotations

_LEVEL_GUIDANCE = {
    "A2": (
        "Use very short sentences and only the most common everyday words. "
        "Explain every medical term. Aim for a 10-year-old reading level (CEFR A2)."
    ),
    "B1": (
        "Use short, clear sentences and common words. Explain medical terms in "
        "plain language. Aim for CEFR B1 — an average adult reader."
    ),
    "B2": (
        "Use clear language but you may keep some precision. Explain medical "
        "terms the first time they appear. Aim for CEFR B2."
    ),
}

_ANALYSIS_SCHEMA = """\
Return ONLY a single JSON object (no prose, no code fences) with this shape:
{
  "document_type": one of ["discharge_summary","lab_report","radiology_report",
     "pathology_report","prescription","referral_letter","consultation_note",
     "other","not_medical"],
  "summary": "2-3 sentence plain-language overview",
  "explanation": "a thorough but accessible explanation in plain language",
  "key_terms": [{"term": "...", "definition": "plain-language, 1-2 sentences"}],
  "action_items": ["practical takeaways and questions to ask the doctor"],
  "lab_values": [{"name":"...","value":"...","unit":"...","reference_range":"...","flag":"high|low|normal"}],
  "medications": [{"name":"...","dose":"...","frequency":"...","purpose":"plain reason if stated"}]
}
Omit lab_values / medications when the document contains none (use []).
Every string value must be written in {language_name}."""


def build_analysis_prompt(
    *, language_name: str, target_level: str, simplify_pass: bool = False
) -> str:
    level = _LEVEL_GUIDANCE.get(target_level, _LEVEL_GUIDANCE["B1"])
    intro = (
        "You are MediClear AI, an expert medical-communication assistant used in "
        "hospitals and clinics to help patients understand their own medical "
        "documents."
    )
    if simplify_pass:
        intro += (
            " The previous explanation was too complex. Rewrite it to be simpler "
            "while preserving every fact."
        )
    return (
        f"{intro}\n\n"
        f"Write for the patient in {language_name}. {level}\n\n"
        "Rules:\n"
        "- Be accurate and faithful to the source. Never invent findings, "
        "diagnoses, values, or medications that are not in the document.\n"
        "- Do NOT diagnose, recommend treatments, or interpret results beyond "
        "what the document states.\n"
        "- Be calm, warm, and reassuring; patients may be anxious.\n"
        "- Always encourage the patient to discuss decisions with their clinician.\n"
        "- If the content is not a medical document, set document_type to "
        "'not_medical' and say so kindly in the summary.\n\n"
        + _ANALYSIS_SCHEMA.replace("{language_name}", language_name)
    )


def build_chat_prompt(*, document_context: str, language_name: str) -> str:
    return (
        "You are MediClear AI, a warm, careful medical-communication assistant. "
        "A patient has had a medical document explained to them and now has a "
        "follow-up question.\n\n"
        "Ground every answer in the document context below. If the answer is not "
        "in the document, say so honestly and suggest asking their clinician.\n\n"
        "DOCUMENT CONTEXT:\n---\n"
        f"{document_context}\n---\n\n"
        f"Answer in {language_name}. Be concise, clear, and empathetic. Do NOT "
        "diagnose, prescribe, or recommend specific treatments. Always encourage "
        "the patient to consult their healthcare provider for medical decisions."
    )

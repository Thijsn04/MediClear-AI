"""
Demo provider.

A built-in, deterministic provider that requires no API key, so anyone can run
the full UI and API end-to-end for demos, screenshots, and local development.
Enable with ``AI_PROVIDER=demo``. It ignores the document content and returns a
realistic, structured example plus a canned streaming chat reply.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.providers.base import BaseAIProvider, Completion, Message

_DEMO_ANALYSIS = {
    "document_type": "discharge_summary",
    "summary": (
        "This is a hospital discharge summary. It says you were treated for a "
        "chest infection (pneumonia) and are now well enough to go home with "
        "medicine and a follow-up plan."
    ),
    "explanation": (
        "You came to hospital with a fever and a cough and were diagnosed with "
        "pneumonia, which is an infection in the lungs. You were given "
        "antibiotics (medicine that fights infection) and oxygen to help you "
        "breathe. Your blood tests improved and your breathing returned to "
        "normal. The doctors have now decided you are well enough to recover at "
        "home. You should keep taking your antibiotics until they are finished, "
        "even if you feel better, and rest as much as you can."
    ),
    "key_terms": [
        {
            "term": "pneumonia",
            "definition": "An infection that inflames the air sacs in the lungs.",
        },
        {"term": "antibiotic", "definition": "A medicine that fights bacterial infections."},
        {"term": "hypoxia", "definition": "Not enough oxygen reaching the body's tissues."},
    ],
    "action_items": [
        "Finish all your antibiotic tablets, even if you feel better.",
        "Go to your follow-up appointment in 2 weeks.",
        "Contact your doctor if your fever or breathlessness comes back.",
        "Ask your doctor whether you need a chest X-ray to check recovery.",
    ],
    "lab_values": [
        {
            "name": "White blood cells",
            "value": "6.5",
            "unit": "10^9/L",
            "reference_range": "4.0-11.0",
            "flag": "normal",
        },
        {
            "name": "C-reactive protein (CRP)",
            "value": "12",
            "unit": "mg/L",
            "reference_range": "< 5",
            "flag": "high",
        },
    ],
    "medications": [
        {
            "name": "Amoxicillin",
            "dose": "500 mg",
            "frequency": "3 times a day for 5 days",
            "purpose": "to treat the lung infection",
        },
        {
            "name": "Paracetamol",
            "dose": "1 g",
            "frequency": "up to 4 times a day",
            "purpose": "to ease fever and pain",
        },
    ],
}


class DemoProvider(BaseAIProvider):
    @property
    def name(self) -> str:
        return "demo"

    @property
    def model(self) -> str:
        return "demo-canned-v1"

    @property
    def is_configured(self) -> bool:
        return True

    @property
    def supports_images(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    async def _complete(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> Completion:
        await asyncio.sleep(0.2)  # a touch of latency so the UI shows its loading state
        if json_mode:
            return Completion(text=json.dumps(_DEMO_ANALYSIS), input_tokens=0, output_tokens=0)
        return Completion(
            text=(
                "That's a good question. Based on your discharge summary, the "
                "most important thing is to finish your antibiotics and rest. "
                "This is general information, not medical advice - please check "
                "with your doctor about your specific situation."
            ),
            input_tokens=0,
            output_tokens=0,
        )

    async def _stream(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        # Analysis prompts ask for a JSON object; stream the canned JSON so the
        # progressive explanation extractor has something to render. Otherwise
        # (chat) stream the canned answer word by word.
        if "JSON object" in system:
            text = json.dumps(_DEMO_ANALYSIS)
            for i in range(0, len(text), 24):
                await asyncio.sleep(0.01)
                yield text[i : i + 24]
            return
        answer = (
            "That's a good question. Based on your discharge summary, the most "
            "important thing is to finish your antibiotics and rest. This is "
            "general information, not medical advice - please check with your "
            "doctor about your specific situation."
        )
        for word in answer.split():
            await asyncio.sleep(0.02)
            yield word + " "

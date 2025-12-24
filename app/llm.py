from dotenv import load_dotenv
import os

load_dotenv()  # reads .env file automatically

USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"


if USE_GEMINI:
    # REAL Gemini (requires billing)
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel
    from typing import Dict, Any

    # connects to your GCP project
    vertexai.init(
        project=os.getenv("GCP_PROJECT", "llm-blackbox"),
        location=os.getenv("GCP_REGION", "us-central1")
    )

    def ask_gemini(question: str) -> Dict[str, Any]:
        """Send prompt to Gemini and return a dict including telemetry fields.

        Returned dict keys:
          - text (str)
          - prompt_tokens (int)
          - completion_tokens (int)
          - total_tokens (int)
          - safety_ratings (dict)
          - finish_reason (str)
        """
        model = GenerativeModel("gemini-pro")
        # Try to call the managed model and extract fields; fall back gracefully
        resp = model.generate_content(question)
        result_text = getattr(resp, "text", str(resp))

        # Attempt to parse token usage and safety attributes
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        safety = {}
        finish_reason = getattr(resp, "finish_reason", "unknown")

        # VertexAI responses may contain metadata or candidates with token usage
        try:
            # candidate-level info
            candidates = getattr(resp, "candidates", None)
            if candidates:
                # sum over candidates if present
                for c in candidates:
                    tu = getattr(c, "token_usage", None) or getattr(c, "usage", None)
                    if tu:
                        prompt_tokens += int(getattr(tu, "prompt_tokens", 0) or tu.get("prompt_tokens", 0))
                        completion_tokens += int(getattr(tu, "completion_tokens", 0) or tu.get("completion_tokens", 0))
            # top-level token usage
            top_usage = getattr(resp, "token_usage", None) or getattr(resp, "usage", None)
            if top_usage:
                prompt_tokens = int(getattr(top_usage, "prompt_tokens", 0) or top_usage.get("prompt_tokens", 0))
                completion_tokens = int(getattr(top_usage, "completion_tokens", 0) or top_usage.get("completion_tokens", 0))
            total_tokens = prompt_tokens + completion_tokens
        except Exception:
            pass

        # Safety ratings
        try:
            safety = getattr(resp, "safety_attributes", {}) or getattr(resp, "safety_ratings", {})
        except Exception:
            safety = {}

        return {
            "text": result_text,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "safety_ratings": safety,
            "finish_reason": finish_reason,
        }


else:
    # 🔹 FAKE Gemini (NO billing, NO cloud)
    import random
    from typing import Dict, Any

    def ask_gemini(question: str) -> Dict[str, Any]:
        # Simulate variable token usage and occasional safety blocks
        prompt_tokens = min(max(len(question.split()), 1) * random.randint(1, 4), 2000)
        completion_tokens = random.randint(10, 200)
        total_tokens = prompt_tokens + completion_tokens

        # Randomly simulate a safety block for certain keywords
        lower = question.lower()
        safety_ratings = {}
        finish_reason = "STOP"
        if any(k in lower for k in ["kill", "bomb", "illegal", "attack", "violent"]):
            safety_ratings = {"HARM_CATEGORY_DANGEROUS_CONTENT": "HIGH"}
            finish_reason = "SAFETY"
        elif len(question) > 2000 or "EXPLODE_TOKENS" in question:
            # simulate huge token explosion
            prompt_tokens = 200000
            completion_tokens = 50000
            total_tokens = prompt_tokens + completion_tokens
            finish_reason = "STOP"

        text = (
            "🧪 [LOCAL TEST MODE]\n"
            f"Question received: '{question}'\n"
            "This is a stubbed response used for API testing."
        )

        return {
            "text": text,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "safety_ratings": safety_ratings,
            "finish_reason": finish_reason,
        }

from dotenv import load_dotenv
import os

load_dotenv()  # reads .env file automatically

USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"

if USE_GEMINI:
    # REAL Gemini (requires billing)
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel

    """
    Sends a prompt to Gemini and returns the response text.
    """

    # connects to your GCP project
    vertexai.init(
        project="llm-blackbox",
        location="us-central1"
    )

    def ask_gemini(question: str) -> str:
        # managed LLM instance
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(question)
        return response.text

else:
    # 🔹 FAKE Gemini (NO billing, NO cloud)
    def ask_gemini(question: str) -> str:
        return (
            "🧪 [LOCAL TEST MODE]\n"
            f"Question received: '{question}'\n"
            "This is a stubbed response used for API testing."
        )

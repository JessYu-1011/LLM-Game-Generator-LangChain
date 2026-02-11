from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config import config
import os

def get_langchain_model(provider: str = "openai", model_name: str = None, temperature: float = 0.2):
    """
    Factory to get a LangChain ChatModel instance based on provider.
    Ensures the correct model name is used for each specific provider's API.
    """
    provider = provider.lower()

    # --- Force correct model matching per provider ---
    # If no specific model_name is passed from the UI, use the pre-configured ones.
    if provider == "openai":
        model_name = model_name or config.OPENAI_MODEL_NAME or "gpt-4o-mini"
    elif provider in ["google", "gemini"]:
        model_name = model_name or config.GOOGLE_MODEL_NAME or "gemini-1.5-flash"
    elif provider == "groq":
        model_name = model_name or config.GROQ_MODEL_NAME or "llama3-70b-8192"
    elif provider == "mistral":
        # CRITICAL: Ensures Mistral doesn't receive "gpt-4o"
        model_name = model_name or config.MISTRAL_MODEL_NAME or "codestral-latest"
    elif provider == "deepseek":
        model_name = model_name or config.DEEPSEEK_MODEL_NAME or "deepseek-chat"
    elif provider == "inception":
        model_name = model_name or config.INCEPTION_MODEL_NAME or "inception"
    elif provider == "ollama":
        model_name = model_name or config.OLLAMA_MODEL_NAME or "llama3:8b"

    # --- 1. OpenAI (Native) ---
    if provider == "openai":
        return ChatOpenAI(
            model=model_name,
            api_key=config.OPENAI_API_KEY,
            temperature=temperature
        )

    # --- 2. Google Gemini ---
    elif provider in ["google", "gemini"]:
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=temperature
        )

    # --- 3. Ollama (Local) ---
    elif provider == "ollama":
        base_url = config.OLLAMA_BASE_URL
        if base_url and base_url.endswith("/v1"):
            base_url = base_url[:-3]

        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature
        )

    # --- 4. Groq ---
    elif provider == "groq":
        return ChatOpenAI(
            model=model_name,
            api_key=config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature
        )

    # --- 5. Mistral ---
    elif provider == "mistral":
        return ChatOpenAI(
            model=model_name,
            api_key=config.MISTRAL_API_KEY,
            base_url="https://api.mistral.ai/v1",
            temperature=temperature
        )

    # --- 6. DeepSeek ---
    elif provider == "deepseek":
        return ChatOpenAI(
            model=model_name,
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            temperature=temperature
        )

    # --- 7. Inception ---
    elif provider == "inception":
        return ChatOpenAI(
            model=model_name,
            api_key=config.INCEPTION_API_KEY,
            base_url="https://api.inceptionlabs.ai/v1",
            temperature=temperature
        )

    # --- Default Fallback ---
    print(f"[ModelFactory] Warning: Provider '{provider}' not explicitly supported. Falling back to OpenAI Default.")
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=config.OPENAI_API_KEY,
        temperature=temperature
    )
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()


# --- 輔助函式 ---
def get_env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None: return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None: return default
    return value.lower() in ('true', '1', 't', 'yes', 'y')


def get_env_ssl_verify(key: str, default):
    value = os.getenv(key)
    if value is None: return default
    if value.lower() in ('true', '1', 'yes'): return True
    if value.lower() in ('false', '0', 'no'): return False
    return value


class Config:
    # 專案路徑
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_games")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")

    # --- LLM API Keys ---
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    INCEPTION_API_KEY = os.getenv("INCEPTION_API_KEY")

    # --- LLM Models ---
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama3-8b-8192")
    GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-2.5-flash")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL_NAME", "codestral-latest")
    DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
    INCEPTION_MODEL_NAME = os.getenv("INCEPTION_MODEL_NAME", "inception")

    # --- OLLAMA ---
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:8b")

    # --- Fuzzer ---
    FUZZER_RUNNING_TIME = get_env_int("FUZZER_RUNNING_TIME", 30)

    # --- Embedding ---
    LLM_EMBEDDING_PROVIDER = os.getenv("LLM_EMBEDDING_PROVIDER")
    LLM_EMBEDDING_SERVER_ADDRESS = os.getenv("LLM_EMBEDDING_SERVER_ADDRESS")
    LLM_EMBEDDING_SERVER_PORT = os.getenv("LLM_EMBEDDING_SERVER_PORT", "")
    LLM_EMBEDDING_MODEL_TYPE = os.getenv("LLM_EMBEDDING_MODEL_TYPE")
    LLM_EMBEDDING_CLIENT_TOKEN = os.getenv("LLM_EMBEDDING_CLIENT_TOKEN")

    # --- ChromaDB ---
    CHROMA_TENANT = os.getenv("CHROMA_TENANT", "default_tenant")
    CHROMA_DATABASE = os.getenv("CHROMA_DATABASE", "default_database")

    # [FIX] 這裡更新為您的正確 Collection Name
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "arcade_v2_knowledge")

    CHROMA_CLIENT_TYPE = os.getenv("CHROMA_CLIENT_TYPE", "persistent")
    CHROMA_DB_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
    CHROMA_TOKEN = os.getenv("CHROMA_TOKEN")

    CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT = get_env_int("CHROMA_PORT", 8000)
    CHROMA_SSL = get_env_bool("CHROMA_SSL", False)
    CHROMA_SSL_VERIFY = get_env_ssl_verify("CHROMA_SSL_VERIFY", False)

    CHROMA_SERVER_AUTH_CREDENTIALS = os.getenv("CHROMA_SERVER_AUTH_CREDENTIALS", None)
    CHROMA_SERVER_AUTH_PROVIDER = os.getenv("CHROMA_SERVER_AUTH_PROVIDER", None)

    CF_ACCESS_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID", None)
    CF_ACCESS_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET", None)

    ARCADE_SOURCE_DIR = os.path.join(PROJECT_ROOT, "arcade_rag_knowledge_base")
    # 確保兩者一致
    ARCADE_COLLECTION_NAME = CHROMA_COLLECTION_NAME


config = Config()
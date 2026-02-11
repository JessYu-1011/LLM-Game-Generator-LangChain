import chromadb
import chromadb.errors
import hashlib
import requests
import urllib3
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from src.config import config

# 禁用 SSL 憑證警告 (讓 Log 乾淨一點)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RemoteOllamaAuthEF(EmbeddingFunction):
    def __init__(self, base_url: str, api_key: str, model_name: str = "nomic-embed-text", timeout: int = 30):
        base_url = base_url.rstrip("/")
        self.api_url = f"{base_url}/api/embeddings"
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = timeout

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            payload = {
                "model": self.model_name,
                "prompt": text
            }
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
            except Exception as e:
                print(f"[Embedding Error] Failed to embed text: {str(e)}")
                raise e
        return embeddings


@dataclass
class RagConfig:
    tenant: str = config.CHROMA_TENANT
    database: str = config.CHROMA_DATABASE
    collection_name: str = config.ARCADE_COLLECTION_NAME
    client_type: str = config.CHROMA_CLIENT_TYPE
    host: str = config.CHROMA_HOST
    port: int = config.CHROMA_PORT
    ssl: bool = config.CHROMA_SSL
    ssl_verify: bool | str = config.CHROMA_SSL_VERIFY
    chroma_token: str = config.CHROMA_TOKEN
    chroma_server_auth_credentials: str = config.CHROMA_SERVER_AUTH_CREDENTIALS
    chroma_server_auth_provider: str = config.CHROMA_SERVER_AUTH_PROVIDER
    cf_client_id: str = config.CF_ACCESS_CLIENT_ID
    cf_client_secret: str = config.CF_ACCESS_CLIENT_SECRET
    provider: str = config.LLM_EMBEDDING_PROVIDER or 'default'
    base_url: str = config.LLM_EMBEDDING_SERVER_ADDRESS
    base_port: str = config.LLM_EMBEDDING_SERVER_PORT
    model_type: str = config.LLM_EMBEDDING_MODEL_TYPE or 'all-MiniLM-L6-v2'
    embedding_token: str = config.LLM_EMBEDDING_CLIENT_TOKEN


class RagService:
    def __init__(self, rag_config: RagConfig = None):
        if rag_config is None:
            rag_config = RagConfig()

        self.config = rag_config
        self.embedding_function = self._get_embedding_function(
            rag_config.provider,
            rag_config.base_url,
            rag_config.base_port,
            rag_config.model_type,
            rag_config.embedding_token
        )

        # 初始化 Client (包含自動 fallback 邏輯)
        self.client = self._get_client(rag_config)

        actual_collection_name = rag_config.collection_name
        print(f"[RAG] Using Collection: {actual_collection_name}")
        print(f"[RAG] Embedding Model: {rag_config.model_type} ({rag_config.provider})")

        self.collection = self.client.get_or_create_collection(
            name=actual_collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def _get_client(self, config: RagConfig):
        mode = config.client_type.lower()

        if mode == 'cloud':
            print("[RAG] Connecting to Chroma Cloud...")
            return chromadb.CloudClient(
                api_key=config.chroma_token,
                tenant=config.tenant,
                database=config.database
            )

        elif mode == 'http':
            print(f"[RAG] Connecting to Chroma HTTP ({config.host}:{config.port})...")

            # 準備 Headers
            request_headers = {}
            if config.cf_client_id and config.cf_client_secret:
                request_headers["CF-Access-Client-Id"] = config.cf_client_id
                request_headers["CF-Access-Client-Secret"] = config.cf_client_secret

            if config.chroma_server_auth_credentials:
                request_headers["X-Chroma-Token"] = config.chroma_server_auth_credentials
                request_headers["Authorization"] = f"Bearer {config.chroma_server_auth_credentials}"

            # 準備 Settings
            chroma_settings = Settings()
            if config.ssl:
                chroma_settings.chroma_server_ssl_verify = config.ssl_verify

            if config.chroma_server_auth_credentials:
                chroma_settings.chroma_client_auth_provider = config.chroma_server_auth_provider or "chromadb.auth.token_auth.TokenAuthClientProvider"
                chroma_settings.chroma_client_auth_credentials = config.chroma_server_auth_credentials

            target_db = config.database

            # --- 邏輯：嘗試連接指定 DB，失敗則回退到 default_database ---
            if target_db != "default_database":
                try:
                    # 1. 嘗試透過 API 建立 (忽略 405/409 錯誤)
                    try:
                        protocol = "https" if config.ssl else "http"
                        api_url = f"{protocol}://{config.host}:{config.port}/api/v1/databases"
                        requests.post(
                            api_url,
                            json={"name": target_db},
                            params={"tenant": config.tenant},
                            headers=request_headers,
                            verify=config.ssl_verify if config.ssl else True,
                            timeout=3
                        )
                    except Exception:
                        pass  # API 建立失敗不重要，重點是下面能不能連上

                    # 2. 嘗試連線
                    client = chromadb.HttpClient(
                        host=config.host,
                        port=config.port,
                        ssl=config.ssl,
                        headers=request_headers,
                        settings=chroma_settings,
                        tenant=config.tenant,
                        database=target_db
                    )
                    # 測試連線 (這一步很重要，如果 DB 不存在會拋錯)
                    client.heartbeat()
                    print(f"[RAG] ✅ Connected to database: '{target_db}'")
                    return client

                except Exception as e:
                    print(f"[RAG] ⚠️ Could not connect to '{target_db}' (Error: {e})")
                    print(f"[RAG] 🔄 Fallback to 'default_database'.")
                    # 連接失敗，繼續往下執行，使用 default_database

            # 3. 最終手段：使用預設資料庫
            return chromadb.HttpClient(
                host=config.host,
                port=config.port,
                ssl=config.ssl,
                headers=request_headers,
                settings=chroma_settings,
                tenant=config.tenant,
                database="default_database"
            )

        elif mode == 'persistent':
            print(f"[RAG] Using Local Persistent Storage at: {config.CHROMA_DB_DIR}")
            return chromadb.PersistentClient(path=config.CHROMA_DB_DIR)

        else:
            raise ValueError(f"Unsupported Chroma client_type: {mode}")

    def _get_embedding_function(self, provider: str, base_url: str, base_port: str, model_type: str, token: str):
        provider = provider.lower()
        if provider == "ollama":
            full_url = base_url
            if base_port:
                full_url = f"{base_url}:{base_port}"
            return RemoteOllamaAuthEF(
                base_url=full_url,
                api_key=token or "dummy-key",
                model_name=model_type,
                timeout=120
            )
        elif provider == "openai":
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=token,
                model_name=model_type
            )
        else:
            return embedding_functions.DefaultEmbeddingFunction()

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def insert(self, content: str, metadata: dict = None) -> str:
        doc_id = self._hash_content(content)
        self.collection.upsert(
            documents=[content],
            metadatas=[metadata] if metadata else None,
            ids=[doc_id],
        )
        return doc_id

    def batch_insert(self, contents: List[str], metadatas: List[Dict] = None):
        if not contents: return
        ids = [self._hash_content(c) for c in contents]
        batch_size = 100
        for i in range(0, len(contents), batch_size):
            end = min(i + batch_size, len(contents))
            self.collection.upsert(
                documents=contents[i:end],
                metadatas=metadatas[i:end] if metadatas else None,
                ids=ids[i:end]
            )
        print(f"[RAG] Batch insert complete.")

    def query(self, query_text: str, n_results: int = 1) -> str:
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            if results['documents'] and results['documents'][0]:
                return results['documents'][0][0]
            return "No relevant documentation found."
        except Exception as e:
            return f"RAG Query Error: {str(e)}"


# 全域實例
rag_instance = RagService()
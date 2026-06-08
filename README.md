# dskpp (dsk++)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Async](https://img.shields.io/badge/async-supported-green.svg)
![License](https://img.shields.io/badge/license-Apache2.0-lightgrey.svg)
![Status](https://img.shields.io/badge/status-experimental-orange.svg)

A lightweight async Python client for interacting with DeepSeek chat infrastructure through a local bypass + cookie + proof-of-work pipeline, with **OpenAI-compatible API server**.

This project follows the same conceptual direction (and also contains elements from) as:
- [https://github.com/xtekky/deepseek4free](https://github.com/xtekky/deepseek4free)
- [https://github.com/Doremii109/deepseek4free-fix](https://github.com/Doremii109/deepseek4free-fix)

> [!WARNING]
> This project is built around reverse-engineered infrastructure behavior. Use responsibly and be aware that API changes may break functionality without notice.

> [!IMPORTANT]
> Cookie generation is required before using the API client. Run `python run_and_get_cookies.py` first — the client will not work without valid cookies.

---

## overview

dsk++ provides:

* async DeepSeek chat client
* streaming response support with dual format parsing
* session-based conversation handling
* automated cookie acquisition system
* local Cloudflare bypass server
* WASM-based proof-of-work solver with async thread pool
* concurrent file upload support using asyncio.gather()
* automatic Cloudflare detection and cookie refresh
* **OpenAI-compatible API server** for use with AI agents (Cline, LangChain, OpenAI SDK, etc.)

---

## installation

### clone repo

> [!CAUTION]
> Do not cd (change directory) into it, you'll import it like dskpp.api!

```bash
git clone https://github.com/fundiman/dskpp
```

### install dependencies

> [!NOTE]
> The `requirements.txt` file was generated with `pipreqs`.

```bash
pip install -r requirements.txt
```

**System dependencies (Linux / server environments):**

* google-chrome or chromium
* xvfb (for headless fallback)
* python 3.10+

---

## quick start

> [!IMPORTANT]
> Before using the API client, cookies must be generated:

```bash
python run_and_get_cookies.py
```

This will:

* start local bypass server
* launch Chromium automation
* solve Cloudflare challenges
* store cookies in `dsk/dsk/cookies.json`

> [!NOTE]
> The bypass server runs locally on port 8021 by default. Ensure this port is available.

---

## OpenAI-compatible API

dskpp can be used as an **OpenAI-compatible API server**, allowing integration with AI agents like **Cline**, **LangChain**, **OpenAI Python SDK**, and others.

### start the server

```bash
python server.py
```

### start with authentication

```bash
export AUTH_KEY=your-secret-key
python server.py
```

### environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_PORT` | `8021` | Server port |
| `DOCKERMODE` | `false` | Docker mode flag (headless Chrome) |
| `AUTH_KEY` | *(empty)* | API key for Bearer auth. If not set, auth is disabled |
| `MODEL_NAME` | `deepseek-chat` | Default model name |

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/models` | List available models |
| `POST` | `/v1/chat/completions` | Chat completion (streaming + non-streaming) |
| `GET` | `/health` | Health check |
| `GET` | `/cookies` | Get Cloudflare bypass cookies (original) |
| `GET` | `/html` | Get page HTML with cookies (original) |

### authentication

The server supports two authentication methods:

1. **Authorization header** (recommended for AI agents):
   ```
   Authorization: Bearer your-secret-key
   ```

2. **Query parameter**:
   ```
   ?key=your-secret-key
   ```

If `AUTH_KEY` is not set, authentication is disabled and all requests are accepted.

### available models

| Model ID | Description |
|----------|-------------|
| `deepseek-chat` | Standard DeepSeek chat model |
| `deepseek-reasoner` | DeepSeek with reasoning/thinking enabled |

### use with Cline

Configure Cline to use your dskpp server:

```json
{
  "apiProvider": "openai",
  "openAiBaseUrl": "http://localhost:8021/v1",
  "openAiApiKey": "your-secret-key",
  "openAiModelId": "deepseek-chat"
}
```

### use with OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8021/v1",
    api_key="your-secret-key",
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    stream=True,
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### use with LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8021/v1",
    api_key="your-secret-key",
    model="deepseek-chat",
)

response = llm.invoke("Hello!")
print(response.content)
```

### example: curl

```bash
# List models
curl http://localhost:8021/v1/models

# Chat completion (non-streaming)
curl -X POST http://localhost:8021/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Chat completion (streaming)
curl -X POST http://localhost:8021/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

---

## project structure

```
dskpp/
│
├── api.py                     # async DeepSeek API client
├── server.py                  # FastAPI server (bypass + OpenAI-compatible API)
├── openai_compat.py           # OpenAI API models and helpers
├── CloudflareBypasser.py      # Chromium-based challenge solver
├── bypass.py                  # automation helper logic
├── pow.py                     # WASM proof-of-work solver (async)
├── run_and_get_cookies.py     # bootstrap cookie acquisition
│
├── dsk/                       # runtime cookie storage
├── wasm/                      # WASM binaries for hashing
└── README.md
```

---

## usage (Python API client)

### initialize client

```python
from dskpp.api import DeepSeekAPI
import asyncio

api = DeepSeekAPI(auth_token="your_token")
```

> [!NOTE]
> The auth token is obtained after logging into DeepSeek chat. Extract it from browser developer tools (Application → Local Storage → chat.deepseek.com → USER_TOKEN).

---

### create chat session

```python
session_id = await api.create_chat_session()
```

---

### delete chat session

```python
result = await api.delete_chat_session(session_id)
print(result)  # "Successfully deleted session: session_id"
```

---

### file upload (concurrent multiple files)

```python
file_ids = await api.upload_files([
    "document.pdf",
    "image.png",
    "data.csv"
])
print(file_ids)  # ['file_id_1', 'file_id_2', 'file_id_3']
```

---

### streaming chat with file references

```python
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="Analyze these uploaded files",
    ref_file_ids=file_ids,
    thinking_enabled=True,
    search_enabled=False
):
    print(chunk.get("content", ""), end="")
```

---

### chat with search

```python
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="What's the latest news about AI?",
    thinking_enabled=True,
    search_enabled=True
):
    print(chunk.get("content", ""), end="")
```

---

### streaming response format

The client parses DeepSeek's SSE format and returns dictionaries:

```python
{
    'type': 'text',
    'content': 'incremental text...',
    'finish_reason': None     # 'stop' when complete, None otherwise
}
```

---

### non-streaming usage (aggregated)

```python
response = ""
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="Hello world"
):
    response += chunk.get("content", "")
```

---

### cleanup

```python
await api.delete_chat_session(session)
await api.close()
```

---

## server mode

Run bypass server manually:

```bash
python server.py
```

Default endpoint:

```
http://localhost:8021
```

Endpoints:

* `/cookies` → returns validated cookies + user-agent
* `/html` → returns raw HTML + cookies header metadata

---

## docker mode

Enable Docker compatibility:

```bash
export DOCKERMODE=true
```

This enables:

* headless Chromium adjustments
* sandbox flags
* remote debugging port support

> [!NOTE]
> Set `DOCKERMODE=true` when running inside containers to avoid sandbox-related crashes.

---

## architecture

The system is composed of three core layers:

### 1. API layer (`api.py`)

Async client for session-based chat interaction with:
- concurrent file uploads using asyncio.gather()
- streaming response parsing for DeepSeek SSE format
- automatic retry logic with Cloudflare detection and cookie refresh
- async session management with curl_cffi

### 2. Server layer (`server.py`)

FastAPI server providing:
- OpenAI-compatible REST API (`/v1/models`, `/v1/chat/completions`)
- WebSocket proxy to upstream DeepSeek API
- Bearer token authentication
- Cloudflare bypass via Chromium automation
- cookie extraction and validation

### 3. OpenAI compatibility layer (`openai_compat.py`)

Pydantic models and helpers for:
- OpenAI request/response format conversion
- Messages array to prompt string conversion
- Model name mapping to DeepSeek parameters
- SSE streaming chunk formatting

### 4. PoW layer (`pow.py`)

WebAssembly-based solver with async wrapper using asyncio.to_thread() to keep event loop responsive during CPU-bound computations.

---

## async design notes

The system is designed around non-blocking execution:

* network I/O uses async HTTP sessions from curl_cffi
* streaming responses use async generators that yield control between chunks
* blocking WASM computations are offloaded to threads via asyncio.to_thread()
* browser automation runs in separate processes
* cookie acquisition runs outside event loop control path
* concurrent file uploads using asyncio.gather()

---

## error handling

The client provides specific exceptions for different failure modes:

```python
from dskpp.api import (
    AuthenticationError,    # Invalid/expired token
    RateLimitError,         # API rate limit exceeded
    NetworkError,           # Network communication failure
    CloudflareError,        # Cloudflare block detected
    UploadFilesUnavailable, # Search enabled during file upload
    APIError               # Generic API error with status code
)
```

---

## notes

> [!CAUTION]
> This project is experimental and based on reverse-engineered behavior of DeepSeek's infrastructure. DeepSeek may modify their API at any time, which could break this client — while efforts will be made to address issues, full compatibility cannot be guaranteed. Use of this client may also violate DeepSeek's terms of service and could result in account suspension or banning. Please use at your own risk.

> [!TIP]
> If you encounter Cloudflare blocks, try deleting `dsk/dsk/cookies.json` and re-running `python run_and_get_cookies.py` to refresh your cookies.

> [!NOTE]
> The client automatically handles both SSE event lines and data lines, parsing the simplified chunk format (just 'v' field) that appears after the first response chunk.

---

## license

This project is licensed under [Apache 2.0](LICENSE).
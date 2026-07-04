# dskpp (dsk++)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Async](https://img.shields.io/badge/async-supported-green.svg)
![License](https://img.shields.io/badge/license-Apache2.0-lightgrey.svg)
![Status](https://img.shields.io/badge/status-experimental-orange.svg)

A lightweight async Python client for interacting with DeepSeek chat infrastructure through a local bypass + cookie + proof-of-work pipeline.

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

> [!TIP]
> Chrome and xvfb are only used for Cloudflare clearance during cookie generation. In normal usage you acquire cookies once and they last for days — you'll only need these if you're spamming requests aggressively enough to trigger Cloudflare challenges.

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

## project structure

```
dskpp/
│
├── api.py                     # async DeepSeek API client
├── server.py                 # FastAPI bypass + cookie server
├── CloudflareBypasser.py     # Chromium-based challenge solver
├── bypass.py                 # automation helper logic
├── pow.py                   # WASM proof-of-work solver (async)
├── run_and_get_cookies.py   # bootstrap cookie acquisition
│
├── dsk/                     # runtime cookie storage
├── wasm/                    # WASM binaries for hashing
└── README.md
```

---

## usage

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
# Upload multiple files concurrently
file_ids = await api.upload_files([
    "document.pdf",
    "image.png",
    "data.csv"
])

# file_ids returned in same order as input
print(file_ids)  # ['file_id_1', 'file_id_2', 'file_id_3']
```

> [!NOTE]
> The system uploads all files simultaneously using `asyncio.gather()` for maximum efficiency.

---

### streaming chat with file references

```python
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="Analyze these uploaded files",
    ref_file_ids=file_ids,  # List of file IDs from upload
    thinking_enabled=True,
    search_enabled=False  # Must be False when using files
):
    # chunk is a dictionary with 'content' key
    print(chunk.get("content", ""), end="")
```

> [!WARNING]
> File uploads require `search_enabled=False`. Attempting to use both will raise `UploadFilesUnavailable`.

---

### chat with search

```python
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="What's the latest news about AI?",
    thinking_enabled=True,
    search_enabled=True  # Enables web search for current info
):
    print(chunk.get("content", ""), end="")
```

---

### streaming response format

The client parses DeepSeek's SSE format and returns dictionaries:

```python
{
    'type': 'text',           # Type of chunk (text, message_ids, etc.)
    'content': 'incremental text...',  # The actual content
    'finish_reason': None     # 'stop' when complete, None otherwise
}
```

> [!NOTE]
> The parser automatically handles both full format (with 'p' and 'o' fields) and simplified format (just 'v' field) chunks.

---

### non-streaming usage (aggregated)

A fully buffered response can be constructed manually:

```python
response = ""

async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="Hello world"
):
    response += chunk.get("content", "")
```

---

### list conversations

```python
sessions = await api.list_conversations()
for s in sessions:
    print(s['title'], s['id'], s['current_message_id'])
```

Each session object contains: `id`, `title`, `updated_at`, `pinned`, `current_message_id`, `seq_id`, `inserted_at`, `model_type`, `agent`, `version`.

Paginate by passing the last session's `seq_id` as cursor:
```python
next_page = await api.list_conversations(cursor=str(sessions[-1]['seq_id']))
```

---

### conversation history

```python
history = await api.get_history(session_id)
print(history)
```

---

### stop stream generation

Stop an active response mid-generation. The `message_id` is automatically tracked from the last `chat_completion` call:

```python
response = await api.stop_stream(chat_session_id=session_id)
print(response)
# {"code": 0, "msg": "", "data": {"biz_code": 0, "biz_msg": "", "biz_data": None}}
```

A specific `message_id` can also be passed directly:

```python
response = await api.stop_stream(
    chat_session_id=session_id,
    message_id=2  # response message ID
)
```

> [!NOTE]
> After `chat_completion` yields a chunk with `type: 'message_ids'`, its `response_message_id` is automatically stored and used by `stop_stream` when no `message_id` is given.

---

### continue stream generation

Resume a stopped stream. The `message_id` is automatically tracked from the last `chat_completion` call:

```python
async for chunk in api.continue_stream(chat_session_id=session_id):
    print(chunk.get("content", ""), end="", flush=True)
```

The first yielded chunk contains the full text generated before the stop, followed by incremental content as generation continues. Works the same as `chat_completion` — same chunk format, same finish signal.

A specific `message_id` can also be passed:

```python
async for chunk in api.continue_stream(
    chat_session_id=session_id,
    message_id=2,
    fallback_to_resume=True,
):
    print(chunk.get("content", ""), end="", flush=True)
```

> [!NOTE]
> `fallback_to_resume` (default `True`) allows the API to fall back to a resume mechanism if the original generation context is lost.

---

### index prepare (handshake)

Initialize the session environment before making other calls. Can be parallelized with other startup tasks:

```python
# Run concurrently with session creation to hide latency
prepare_task = asyncio.create_task(api.index_prepare())
session_id = await api.create_chat_session()
prepare_result = await prepare_task
```

### search index

Search the knowledge base / indexed content using a query string:

```python
async for chunk in api.search_query(query="machine learning"):
    print(chunk.get("content", ""), end="")
```

Each chunk contains keys: `type`, `content`, `message_id`, `seq_id`, `is_begin`, `is_end`, `is_think`.

---

### cleanup

> [!IMPORTANT]
> Always close the session when done to free resources:

```python
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

### 2. bypass layer (`server.py`)

FastAPI + Chromium automation for:

* Cloudflare bypass
* cookie extraction
* page validation

### 3. PoW layer (`pow.py`)

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
* colored warning outputs for better visibility

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

## example: full flow with file upload

```python
import asyncio
from dskpp.api import DeepSeekAPI

async def main():
    api = DeepSeekAPI("your_token_here")

    # Create session
    session = await api.create_chat_session()
    print(f"Session created: {session}")

    # Upload files concurrently
    file_ids = await api.upload_files([
        "report.pdf",
        "data.xlsx"
    ])
    print(f"Uploaded files: {file_ids}")

    # Chat with file context
    async for chunk in api.chat_completion(
        session,
        "Analyze these files and summarize key points",
        ref_file_ids=file_ids,
        search_enabled=False  # Required for file uploads
    ):
        print(chunk.get("content", ""), end="")

    # Cleanup
    await api.delete_chat_session(session)
    await api.close()

asyncio.run(main())
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
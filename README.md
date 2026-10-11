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
> Follow the quick-start steps below for cookie acquisition. The client loads cookies from `dsk/cookies.json` inside this repository, or uses an empty cookie dictionary if that file is absent or invalid.

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

```bash
git clone https://github.com/fundiman/dskpp
cd dskpp
```

Run installation and cookie setup commands from the repository directory.
Run application scripts that import `dskpp.api` from its parent directory,
or put that parent directory on `PYTHONPATH`.

### install dependencies

> [!NOTE]
> The `requirements.txt` file was generated with `pipreqs`.

```bash
pip install -r requirements.txt
```

**System dependencies (Linux / server environments):**

* Google Chrome at `/usr/bin/google-chrome` (change `browser_path` in `server.py` to use Chromium or another location)
* xvfb (when using `--headless` or `DOCKERMODE=true`)
* python 3.10+

> [!TIP]
> Browser automation is used for cookie acquisition and refresh. Normal API requests use `curl_cffi`. Cookie lifetime depends on the server and browser environment; refresh them when necessary.

---

## quick start

> [!IMPORTANT]
> Run these commands from the repository directory to generate cookies and place them where the client reads them:

```bash
python run_and_get_cookies.py
cp dsk/dsk/cookies.json dsk/cookies.json
```

This will:

* start local bypass server
* launch Chromium automation
* solve Cloudflare challenges
* store cookies in `dsk/dsk/cookies.json` relative to the working directory; the copy command places them in the client's `dsk/cookies.json`

The bootstrap script leaves the bypass server running in the background.
The automatic refresh helper (`bypass.py`) also writes to the working-directory
path `dsk/dsk/cookies.json`, while the client reloads the repository-relative
`dsk/cookies.json`. These paths currently differ, so a refresh does not
automatically replace the client's cookie file.

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

# Successful file IDs retain input order; failed/timed-out IDs are omitted
print(file_ids)  # ['file_id_1', 'file_id_2', 'file_id_3']
```

> [!NOTE]
> Uploads run concurrently using `asyncio.gather()`. Each upload waits up to 60 seconds for processing, polling every 2 seconds. Processing failures/timeouts return an empty ID that is filtered out; request failures can raise an exception for the upload operation.

---

### streaming chat with file references

```python
async for chunk in api.chat_completion(
    chat_session_id=session_id,
    prompt="Analyze these uploaded files",
    ref_file_ids=file_ids,  # List of file IDs from upload
    thinking_enabled=True,
    search_enabled=True,  # Web search works together with file references
    show_thinking=True   # Include reasoning chunks in the output
):
    # chunk is a dictionary with 'content' key
    print(chunk.get("content", ""), end="")
```

File references, web search, and reasoning can all be enabled together.
Model selection is automatic;
the client no longer sends `model_type` or `x-model-type`.

Pass `show_thinking=True` to `chat_completion` or `continue_stream` to receive
reasoning as chunks with `type='thinking'`. By default, reasoning is omitted
from the output; `thinking_enabled` controls whether the model reasons.
Search citations are rendered as Markdown links when source URLs are available.

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
    'type': 'text',           # 'text', or 'thinking' when show_thinking=True
    'content': 'incremental text...',  # The actual content
    'finish_reason': None     # 'stop' when complete, None otherwise
}
```

> [!NOTE]
> The parser handles response snapshots, fragment appends, BATCH operations, and simplified string 'v' chunks. It filters out tool content. Unresolved citation markers are removed. `chat_completion` tracks message IDs internally rather than yielding them; `continue_stream` can also yield explicit `message_ids` events.

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

Session objects are returned as supplied by the server. Typical fields include
`id`, `title`, `updated_at`, `pinned`, `current_message_id`, and `seq_id`;
additional metadata may vary. Use `pinned=True` to request pinned sessions.

Paginate by passing the last session's `seq_id` as cursor:
```python
if sessions:
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
> `chat_completion` stores the `response_message_id` internally when it receives a message-ID event. `stop_stream` uses that ID when no explicit `message_id` is given, and raises `ValueError` if no ID is known.

---

### continue stream generation

Resume a stopped stream. The `message_id` is automatically tracked from the last `chat_completion` call:

```python
async for chunk in api.continue_stream(chat_session_id=session_id):
    print(chunk.get("content", ""), end="", flush=True)
```

When the server sends an accumulated snapshot, the client emits the active
fragment's content, followed by incremental content as generation continues.
This is not necessarily the full response across all fragments. Reasoning is
included only with `show_thinking=True`. Text chunks and the finish signal use
the same format as `chat_completion`.

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

Call the index preparation endpoint when needed. The client does not require
this call before `chat_completion`. It can be parallelized with startup tasks:

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

* `/cookies?url=https://chat.deepseek.com` → returns browser cookies + user-agent (does not validate that `cf_clearance` is present)
* `/html?url=https://chat.deepseek.com` → returns raw HTML with `cookies` and `user_agent` response headers

Both endpoints require `url` and accept optional `retries` (default 5) and
`proxy` parameters. `SERVER_PORT` overrides the manual server's port; the
cookie helper scripts still connect to port 8021.

---

## docker mode

Enable Docker compatibility:

```bash
export DOCKERMODE=true
```

This enables:

* an Xvfb virtual display for the headed Chromium process
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
- retries and Cloudflare detection for regular JSON requests, uploads, and conversation listing; streaming requests do not automatically retry or refresh cookies
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
* cookie acquisition uses async HTTP requests and a separate server process
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
    APIError               # Generic API error with status code
)
```

---

`CloudflareError` and `UploadFilesUnavailable` remain defined for compatibility,
but current request paths do not raise them. The retry wrappers in
`_make_request`, file upload, and conversation listing can wrap authentication,
rate-limit, or API errors in `NetworkError` after retries; streaming calls
raise `AuthenticationError`, `RateLimitError`, or `APIError` directly.

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

    # Chat with file context, web search, and reasoning
    async for chunk in api.chat_completion(
        session,
        "Analyze these files and verify key points using web search",
        ref_file_ids=file_ids,
        thinking_enabled=True,
        search_enabled=True,
        show_thinking=True
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
> If you encounter Cloudflare blocks, regenerate cookies from the repository directory with `python run_and_get_cookies.py`, then copy `dsk/dsk/cookies.json` to `dsk/cookies.json`. Recreate the client to load the updated file.

> [!NOTE]
> The client automatically handles both SSE event lines and data lines, parsing the simplified chunk format (just 'v' field) that appears after the first response chunk.

---

## license

This project is licensed under [Apache 2.0](LICENSE).

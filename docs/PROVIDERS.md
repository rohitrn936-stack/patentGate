# The LLM provider layer

Everything an agent needs from a model — messages, a model name, tools,
streaming, structured output, token usage, a normalized error hierarchy — lives
in `llm/`. Agents depend only on that; they never import `openai` or
`anthropic`.

```python
from llm import get_llm, Message

llm = get_llm(agent="agent1")                     # provider chosen by env config
result = llm.complete_structured(
    [Message.system(SYSTEM_PROMPT), Message.user(user_text)],
    MyPydanticSchema,                              # validated return type
)
llm.model                                         # resolved model id
```

## Configuration

Resolved by `llm/config.py`, first non-empty wins:

1. Per-agent override — `AGENT1_LLM_PROVIDER`, `AGENT2_LLM_MODEL`, `IMAGE_LLM_API_KEY`, …
2. Global — `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`,
   `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`, `LLM_MAX_TOKENS`
3. Legacy fallback — `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `API_KEY`,
   `OPENAI_MODEL` / `MODEL_NAME`
4. Built-in default — provider `openai`, per-provider default model

Agent keys: `AGENT1`–`AGENT4`, `IMAGE`.

## Built-in providers

| `LLM_PROVIDER` | SDK          | Default model                | Notes |
|---------------|--------------|------------------------------|-------|
| `openai`      | `openai`     | `gpt-4o-mini`                | native JSON mode |
| `anthropic`   | `anthropic`  | `claude-sonnet-4-20250514`   | JSON via prompt + tolerant parse |
| `gemini`      | `openai`     | `gemini-2.0-flash`           | Google's OpenAI-compatible endpoint |
| `openrouter`  | `openai`     | `openai/gpt-4o-mini`         | `https://openrouter.ai/api/v1` |
| `local`       | `openai`     | `llama3.1`                   | Ollama/vLLM/LM Studio; no key required |

`gemini`, `openrouter` and `local` are thin `base_url` subclasses of the OpenAI
provider (`llm/providers/compatible.py`), so only two real SDK dependencies
cover every provider.

## Adding a provider

1. Create `llm/providers/<name>_provider.py`:

   ```python
   from ..base import LLMProvider
   from ..registry import register_provider
   from ..types import LLMResponse, Message, StreamEvent

   @register_provider
   class MyProvider(LLMProvider):
       name = "myprovider"                 # <- the LLM_PROVIDER value
       default_model = "my-default"
       supports_json_mode = True           # False => base class nudges + tolerant-parses

       def _validate_config(self) -> None:
           if not self.api_key:
               from ..errors import LLMConfigError
               raise LLMConfigError("MYPROVIDER_API_KEY is required", provider=self.name)
           self._client = ...              # build the SDK client here

       def _complete(self, messages, *, model, temperature, max_tokens, tools, response_format) -> LLMResponse:
           ...                             # map SDK exceptions to llm.errors.* types

       def _stream(self, messages, *, model, temperature, max_tokens, tools):
           yield StreamEvent(type="text", text=...)
           yield StreamEvent(type="done")
   ```

   If the API is OpenAI-wire-compatible, subclass `OpenAIProvider` and set
   `name` + `_default_base_url` instead (see `compatible.py`).

2. Import it in `llm/providers/__init__.py`.

That's the whole change. `get_llm()`, the CLI, the backend and the tests pick it
up with no further edits. `LLM_PROVIDER=myprovider` now works.

## What the base class gives you for free

- Retry with exponential backoff on `LLMRateLimitError` / `LLMTimeoutError` /
  `LLMProviderError` (bounded by `LLM_MAX_RETRIES` and the timeout budget).
- `complete_structured(messages, schema)` — JSON-mode request where supported,
  code-fence stripping, first-JSON-block extraction, Pydantic validation, and a
  single repair round-trip on failure.
- `Usage` token accounting on every `LLMResponse`.
- One error taxonomy: `LLMConfigError`, `LLMAuthError`, `LLMRateLimitError`,
  `LLMTimeoutError`, `LLMBadResponseError`, `LLMProviderError`.

## Testing without a network

```python
from llm.testing import use_fake_llm

with use_fake_llm(responses=['{"answer": 42}']):
    out = get_llm(agent="agent1").complete_structured(msgs, Schema)
```

`use_fake_llm` points `LLM_PROVIDER` at the in-memory `FakeProvider`, which
returns scripted responses (or raises scripted `LLMError`s) and records calls.

# 模型调用抽象层
# 设计原则：provider 无关，切换模型只改配置文件
# 支持 mock provider 用于全链路联调
# 统一重试与超时策略

import json
import os
import re
import time
import hashlib
import threading
import urllib.request
import urllib.error
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# ── Config ─────────────────────────────────────────────────────

def load_config(profile: str = "mock") -> Dict[str, Any]:
    """Load provider configuration from config/providers.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "providers.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    if profile not in config.get('profiles', {}):
        raise ValueError(f"Unknown profile: {profile}. Available: {list(config.get('profiles', {}).keys())}")
    profile_config = config['profiles'][profile]
    defaults = config.get('defaults', {})
    return {
        'base_url': profile_config.get('base_url', defaults.get('base_url', '')),
        'model_id': profile_config.get('model_id', defaults.get('model_id', '')),
        'api_key': profile_config.get('api_key', defaults.get('api_key', '')),
        'provider': profile_config.get('provider', profile),
        'timeout_ms': profile_config.get('timeout_ms', defaults.get('timeout_ms', 300000)),
        'max_retries': profile_config.get('max_retries', defaults.get('max_retries', 3)),
        'retry_backoff_ms': profile_config.get('retry_backoff_ms', defaults.get('retry_backoff_ms', 1000)),
        'mock_response_dir': profile_config.get('mock_response_dir', ''),
        'max_total_input_tokens': defaults.get('max_total_input_tokens', 25000000),
        'max_total_output_tokens': defaults.get('max_total_output_tokens', 4000000),
        'max_rate_limit_retries': defaults.get('max_rate_limit_retries', 5),
        'rate_limit_backoff_ms': defaults.get('rate_limit_backoff_ms', 5000),
        'rate_limit_backoff_multiplier': defaults.get('rate_limit_backoff_multiplier', 2.0),
        'tpm_limit': defaults.get('tpm_limit', 0),
        'rpm_limit': defaults.get('rpm_limit', 0),
    }


# ── Exceptions ──────────────────────────────────────────────────

class TokenBudgetExceededError(Exception):
    """Raised when cumulative token usage exceeds configured limits."""

    def __init__(self, message: str, direction: str, current_total: int, limit: int):
        super().__init__(message)
        self.direction = direction  # 'input' or 'output'
        self.current_total = current_total
        self.limit = limit


class RateLimitError(Exception):
    """Raised on HTTP 429 — triggers exponential backoff retry."""
    pass


# ── Evidence Logger ────────────────────────────────────────────

class EvidenceLogger:
    """Records every model call to a structured evidence log."""

    def __init__(self, run_id: str, logs_dir: str = "logs/runs",
                 max_input_tokens: int = 25000000, max_output_tokens: int = 4000000):
        self.run_id = run_id
        self.run_dir = Path(logs_dir) / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.calls_path = self.run_dir / "calls.jsonl"
        self.manifest_path = self.run_dir / "manifest.json"
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_latency_ms = 0
        self.success_count = 0
        self.failure_count = 0
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.completed_chunks = []  # list of chunk_id strings
        self.start_time = datetime.now(timezone.utc).isoformat()
        self._lock = threading.RLock()  # reentrant lock for thread-safe concurrent calls
        self._write_manifest()

    def log_call(self, *,
                 provider: str,
                 model_id: str,
                 task_name: str,
                 input_volume: str,
                 input_token: int,
                 output_token: int,
                 latency_ms: int,
                 retry_count: int,
                 finish_reason: str,
                 input_digest: str,
                 output_path: str = "",
                 error: Optional[str] = None) -> str:
        """Record one call. Returns call_id. Thread-safe."""
        with self._lock:
            self.call_count += 1
            call_id = f"{self.run_id}-{self.call_count:04d}"
            total_token = input_token + output_token
            self.total_input_tokens += input_token
            self.total_output_tokens += output_token
            self.total_latency_ms += latency_ms
            if error:
                self.failure_count += 1
            else:
                self.success_count += 1

            record = {
                'call_id': call_id,
                'run_id': self.run_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'provider': provider,
                'model_id': model_id,
                'task_name': task_name,
                'input_volume': input_volume,
                'input_token': input_token,
                'output_token': output_token,
                'total_token': total_token,
                'latency_ms': latency_ms,
                'retry_count': retry_count,
                'finish_reason': finish_reason,
                'input_digest': input_digest,
                'output_path': output_path,
                'error': error or '',
                'tool_name': '',
                'tool_type': '',
                'afp_cost': '',
                'retrieval_trace': '',
                'target_uri': '',
            }

            with open(self.calls_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

            self._write_manifest()
            return call_id

    def log_provenance(self, *,
                       query: str,
                       ov_hits: list,
                       fetched_cites: list,
                       cited: list,
                       unused: list,
                       step_id: str = "") -> str:
        """
        Log a provenance record: the full chain from query → retrieval → citation.

        Args:
            query: The original search query text
            ov_hits: List of {uri, level, score, abstract} from OpenViking
            fetched_cites: cite_ids fetched from cite_index for the hits
            cited: cite_ids actually used in the final output
            unused: cite_ids fetched but not used
            step_id: Optional identifier for this provenance step
        """
        if not step_id:
            step_id = f"prov-{hashlib.sha256(query.encode()).hexdigest()[:8]}"

        prov_path = self.run_dir / "provenance.jsonl"

        with self._lock:
            # Compute citation metrics
            citation_yield = len(cited) / len(fetched_cites) if fetched_cites else 0.0
            unique_hit_uris = len(set(h.get('uri', '') for h in ov_hits if h.get('uri')))
            hit_utilization = 0.0

            record = {
            'step_id': step_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'query': query,
            'ov_hits': ov_hits,
            'fetched_cite_count': len(fetched_cites),
            'cited_count': len(cited),
            'unused_count': len(unused),
            'cited_cite_ids': cited,
            'unused_cite_ids': unused,
            'citation_yield': citation_yield,       # cited / fetched
            'hit_utilization': hit_utilization,     # contributing URIs / total unique hit URIs
        }
        with open(prov_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

        return step_id

    def _write_manifest(self):
        """Write manifest to disk. Caller must hold _lock or this is called from within _lock."""
        with self._lock:
            manifest = {
            'run_id': self.run_id,
            'start_time': self.start_time,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'call_count': self.call_count,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_latency_ms': self.total_latency_ms,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'max_total_input_tokens': self.max_input_tokens,
            'max_total_output_tokens': self.max_output_tokens,
            'completed_chunks': self.completed_chunks,
        }
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def mark_chunk_completed(self, chunk_id: str):
        """Record a completed chunk."""
        if chunk_id not in self.completed_chunks:
            self.completed_chunks.append(chunk_id)
            self._write_manifest()


# ── LLM Client ─────────────────────────────────────────────────

class LLMClient:
    """Provider-agnostic LLM client with retry, timeout, and evidence logging."""

    def __init__(self, profile: str = "mock", run_id: Optional[str] = None, logs_dir: str = None):
        self.config = load_config(profile)
        self.profile = profile
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if logs_dir is None:
            # Default to absolute path relative to this script's base
            logs_dir = str(Path(__file__).parent.parent.parent / "logs" / "runs")
        self.logger = EvidenceLogger(self.run_id, logs_dir=logs_dir,
            max_input_tokens=self.config.get('max_total_input_tokens', 25000000),
            max_output_tokens=self.config.get('max_total_output_tokens', 4000000))

    def _resolve_env_var(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns in a config value."""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_name = value[2:-1]
            return os.environ.get(env_name, value)
        return value

    def _call_openai_compatible(self, messages: List[Dict], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Real provider: call an OpenAI-compatible chat completions API."""
        base_url = self._resolve_env_var(self.config['base_url']).rstrip('/')
        api_key = self._resolve_env_var(self.config['api_key'])
        model_id = self.config['model_id']
        timeout_sec = self.config['timeout_ms'] / 1000

        url = f"{base_url}/chat/completions"
        payload = {
            'model': model_id,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode('utf-8')
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitError(f"HTTP 429: rate limited")
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            raise RuntimeError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")

    def _call_mock(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Mock provider: read local response file."""
        mock_dir = Path(self.config.get('mock_response_dir', 'config/mock_responses'))
        # Hash the input to find a matching mock response
        input_str = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(input_str.encode('utf-8')).hexdigest()[:16]
        mock_file = mock_dir / f"{digest}.json"

        if mock_file.exists():
            with open(mock_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Fallback: return a default mock response
        return {
            'choices': [{'message': {'content': '[MOCK] This is a placeholder response. Configure mock responses in config/mock_responses/.'}}],
            'usage': {'prompt_tokens': len(input_str) // 3, 'completion_tokens': 20, 'total_tokens': len(input_str) // 3 + 20},
            'finish_reason': 'stop',
        }

    def _check_input_budget(self, estimated_input_tokens: int):
        """Check if estimated input tokens would exceed the cumulative input budget. Thread-safe."""
        with self.logger._lock:
            limit = self.logger.max_input_tokens
            current = self.logger.total_input_tokens
            projected = current + estimated_input_tokens
            if projected > limit:
                msg = (f"TOKEN BUDGET EXCEEDED (input): "
                       f"current cumulative input = {current:,}, "
                       f"estimated next call = {estimated_input_tokens:,}, "
                       f"projected = {projected:,}, "
                       f"limit = {limit:,}. "
                       f"Completed chunks: {self.logger.completed_chunks}")
                raise TokenBudgetExceededError(msg, 'input', current, limit)

    def _check_output_budget(self, output_token: int):
        """Check if output tokens would exceed the cumulative output budget. Thread-safe."""
        with self.logger._lock:
            limit = self.logger.max_output_tokens
            current = self.logger.total_output_tokens
            projected = current + output_token
            if projected > limit:
                msg = (f"TOKEN BUDGET EXCEEDED (output): "
                       f"current cumulative output = {current:,}, "
                       f"this call = {output_token:,}, "
                       f"projected = {projected:,}, "
                       f"limit = {limit:,}. "
                       f"Completed chunks: {self.logger.completed_chunks}")
                raise TokenBudgetExceededError(msg, 'output', current, limit)

    def chat(self, *,
             messages: List[Dict],
             task_name: str = "unknown",
             input_volume: str = "",
             max_tokens: int = 4096,
             temperature: float = 0.0,
             output_path: str = "",
             mock_response: str = None) -> Dict[str, Any]:
        """Send a chat completion request. Returns response dict with 'content' and 'usage' keys."""
        provider = self.config['provider']
        model_id = self.config['model_id']
        retry_count = 0
        start_time = time.time()

        # Compute input digest
        input_str = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        input_digest = hashlib.sha256(input_str.encode('utf-8')).hexdigest()

        # Pre-flight budget check (estimate from input string length)
        estimated_input = len(input_str) // 3  # rough estimate: ~3 chars per token
        self._check_input_budget(estimated_input)

        while retry_count <= self.config['max_retries']:
            try:
                if provider == 'mock':
                    if mock_response is not None:
                        # Use provided mock response (for falsifiable testing)
                        # Estimate tokens using char count, not json.dumps size
                        prompt_chars = sum(len(m.get('content', '')) for m in messages)
                        est_input = int(prompt_chars * 0.75)  # use TOKEN_COEFFICIENT
                        response = {
                            'choices': [{'message': {'content': mock_response}}],
                            'usage': {'prompt_tokens': est_input,
                                      'completion_tokens': len(mock_response) // 3,
                                      'total_tokens': est_input + len(mock_response) // 3},
                            'finish_reason': 'stop',
                        }
                    else:
                        response = self._call_mock(messages)
                else:
                    response = self._call_openai_compatible(
                        messages, max_tokens=max_tokens, temperature=temperature)

                latency_ms = int((time.time() - start_time) * 1000)
                usage = response.get('usage', {})
                input_token = usage.get('prompt_tokens', 0)
                output_token = usage.get('completion_tokens', 0)
                content = response['choices'][0]['message']['content']

                # Post-call output budget check (with real token count)
                self._check_output_budget(output_token)

                self.logger.log_call(
                    provider=provider,
                    model_id=model_id,
                    task_name=task_name,
                    input_volume=input_volume,
                    input_token=input_token,
                    output_token=output_token,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                    finish_reason=response.get('finish_reason', 'stop'),
                    input_digest=input_digest,
                    output_path=output_path,
                )

                return {
                    'content': content,
                    'usage': usage,
                    'finish_reason': response.get('finish_reason', 'stop'),
                    'latency_ms': latency_ms,
                }

            except TokenBudgetExceededError:
                # Don't retry on budget exceeded — propagate immediately
                raise

            except RateLimitError as e:
                retry_count += 1
                if retry_count > self.config.get('max_rate_limit_retries', 5):
                    raise
                backoff = self.config['rate_limit_backoff_ms'] * (
                    self.config['rate_limit_backoff_multiplier'] ** (retry_count - 1))
                backoff = min(backoff, 120000)  # cap at 2 minutes
                print(f"  [RATE LIMITED] retry {retry_count}/{self.config.get('max_rate_limit_retries', 5)} "
                      f"in {backoff/1000:.0f}s...", end=' ', flush=True)
                time.sleep(backoff / 1000)

            except Exception as e:
                retry_count += 1
                if retry_count > self.config['max_retries']:
                    latency_ms = int((time.time() - start_time) * 1000)
                    self.logger.log_call(
                        provider=provider,
                        model_id=model_id,
                        task_name=task_name,
                        input_volume=input_volume,
                        input_token=0,
                        output_token=0,
                        latency_ms=latency_ms,
                        retry_count=retry_count - 1,
                        finish_reason='error',
                        input_digest=input_digest,
                        output_path=output_path,
                        error=str(e),
                    )
                    raise
                backoff = self.config['retry_backoff_ms'] * (2 ** (retry_count - 1))
                time.sleep(backoff / 1000)

    def chunked_chat(self, *, messages: List[Dict], chunk_size: int = 100000, **kwargs) -> List[Dict[str, Any]]:
        """TODO: Long input chunking and continuation. Splits messages into chunks
        that fit within context limits, processes each chunk, and merges results."""
        raise NotImplementedError("chunked_chat: TODO - implement long input splitting and continuation")


# ── Convenience ────────────────────────────────────────────────

def get_client(profile: str = "mock", run_id: Optional[str] = None) -> LLMClient:
    """Factory function to get a configured LLM client."""
    return LLMClient(profile=profile, run_id=run_id)
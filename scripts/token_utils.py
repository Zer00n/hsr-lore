"""
Token estimation utility.
Shared coefficient for Chinese character → token conversion.
Calibrated via A1 tokenizer calibration against real doubao API.
"""
# Default coefficient: Chinese chars × 0.75 = estimated tokens
# Will be updated after A1 calibration against real doubao tokenizer
TOKEN_COEFFICIENT = 0.75

# Max tokens per chunk (550K = 600K context window minus 50K safety margin)
MAX_TOKENS_PER_CHUNK = 550_000

# Prompt overhead: system_prompt + user_prompt template (not including corpus)
PROMPT_OVERHEAD = 2_000

# Per-entry overhead: avg chars for "[cite_id]\n{clean}\n" formatting
PER_ENTRY_OVERHEAD = 18


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string using the calibrated coefficient."""
    return int(len(text) * TOKEN_COEFFICIENT)


def estimate_chunk_tokens(entries, clean_key='clean') -> int:
    """Estimate total prompt tokens for a list of entries.

    Args:
        entries: List of dicts with a 'clean' text field
        clean_key: Key name for the text field (default 'clean')
    """
    clean_chars = sum(len(e.get(clean_key, '')) for e in entries)
    overhead_chars = len(entries) * PER_ENTRY_OVERHEAD
    return estimate_tokens(clean_chars + overhead_chars) + PROMPT_OVERHEAD


def estimate_entry_tokens(entry, clean_key='clean') -> int:
    """Estimate prompt tokens for a single entry."""
    return estimate_tokens(len(entry.get(clean_key, '')) + PER_ENTRY_OVERHEAD)


def update_coefficient(new_coefficient: float):
    """Update the global token coefficient after calibration."""
    global TOKEN_COEFFICIENT
    TOKEN_COEFFICIENT = new_coefficient

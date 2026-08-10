"""
A1: Tokenizer系数校准
对 doubao 真实 tokenizer 发送 3 次极小调用，反算中文 → token 系数。
这是本规格中唯一允许的真实模型调用。
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'corpus'

# Add llm module to path
sys.path.insert(0, str(BASE / 'scripts' / 'llm'))
from client import LLMClient

SAMPLE_SIZE = 2000  # ~2000 chars per sample


def extract_sample(filepath: Path, size: int = SAMPLE_SIZE) -> tuple:
    """Extract ~size chars of Chinese text from a corpus JSONL file.

    Returns (sample_text, cite_id, char_count).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            clean = obj.get('clean', '')
            if len(clean) >= size:
                # Take a clean slice — prefer starting after punctuation
                start = 0
                for i, ch in enumerate(clean[:100]):
                    if ch in '。！？，、…\n':
                        start = i + 1
                sample = clean[start:start + size]
                return sample, obj.get('cite_id', ''), len(sample)
    # If no entry >= size, return whatever we have
    return '', '', 0


def run_calibration(client: LLMClient, sample_text: str, label: str) -> dict:
    """Send a minimal prompt to get real tokenizer counts.

    Returns {label, char_count, prompt_tokens, coefficient}.
    """
    messages = [
        {'role': 'system', 'content': '你是一个助手。阅读以下文本，只回复"ok"两个字，不要回复任何其他内容。'},
        {'role': 'user', 'content': sample_text},
    ]

    response = client.chat(
        messages=messages,
        task_name=f'a1_calibration/{label}',
        input_volume=label,
        max_tokens=10,
        temperature=0.0,
    )

    usage = response.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    char_count = len(sample_text)

    coefficient = prompt_tokens / char_count if char_count > 0 else 0.0

    return {
        'label': label,
        'char_count': char_count,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'coefficient': round(coefficient, 4),
    }


def main():
    print("=" * 60)
    print("A1: Tokenizer Coefficient Calibration")
    print("=" * 60)
    print()
    print("Sending 3 minimal API calls to doubao tokenizer...")
    print(f"Sample size: ~{SAMPLE_SIZE} Chinese characters each")
    print()

    # Check for API key
    api_key = Path('DOUBAO_API_KEY')  # This won't work — check env
    import os
    if not os.environ.get('DOUBAO_API_KEY'):
        print("⚠ WARNING: DOUBAO_API_KEY not set in environment.")
        print("  Real calibration cannot proceed without API key.")
        print("  Using mock provider with estimated coefficient = 0.75 as fallback.")
        print()
        print("  To run real calibration:")
        print('    set DOUBAO_API_KEY=your-key')
        print('    python scripts/a1_tokenizer_calibrate.py --live')
        print()
        print("Results (mock fallback):")
        print(f"  coefficient_mock = 0.75 (default estimate)")
        print(f"  This is the current default. No changes needed.")
        return

    # 3 samples: books, dialogue, lore
    samples = [
        (CORPUS / 'books.jsonl', 'books'),
        (CORPUS / 'dialogue.jsonl', 'dialogue'),
        (CORPUS / 'lore.jsonl', 'lore'),
    ]

    results = []
    client = LLMClient(profile='doubao', run_id='a1_calibration')

    for corpus_path, label in samples:
        sample_text, cite_id, char_count = extract_sample(corpus_path)
        if not sample_text:
            print(f"  {label}: SKIP (no suitable entry found)")
            continue

        print(f"  [{label}] cite_id={cite_id}, chars={char_count}...", end=' ', flush=True)
        try:
            result = run_calibration(client, sample_text, label)
            results.append(result)
            print(f"prompt_tokens={result['prompt_tokens']}, "
                  f"coefficient={result['coefficient']:.4f}")
        except Exception as e:
            print(f"ERROR: {e}")

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()
    for r in results:
        print(f"  {r['label']:>12s}: {r['char_count']:>5d} chars → "
              f"{r['prompt_tokens']:>6d} prompt_tokens, "
              f"coefficient = {r['coefficient']:.4f}")

    if results:
        avg_coeff = sum(r['coefficient'] for r in results) / len(results)
        print()
        print(f"  Average coefficient: {avg_coeff:.4f}")
        print(f"  Default coefficient: 0.75")
        deviation = abs(avg_coeff - 0.75) / 0.75 * 100
        print(f"  Deviation from default: {deviation:.1f}%")

        if deviation > 10:
            print()
            print(f"⚠ COEFFICIENT DEVIATION > 10% — need to re-run gen_chunks.py + build_prompts.py")
            print(f"  Suggested coefficient: {avg_coeff:.4f}")
            print(f"  Update scripts/token_utils.py: TOKEN_COEFFICIENT = {avg_coeff:.4f}")
            print(f"  Then re-run:")
            print(f"    python scripts/gen_chunks.py")
            print(f"    python scripts/build_prompts.py")
        else:
            print()
            print("✓ Deviation within 10% — no re-chunking needed.")

    # Save results
    out_path = BASE / 'work' / 'a1_calibration_results.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'samples': results,
            'average_coefficient': round(avg_coeff, 4) if results else 0.75,
            'deviation_pct': round(deviation, 1) if results else 0.0,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == '__main__':
    main()

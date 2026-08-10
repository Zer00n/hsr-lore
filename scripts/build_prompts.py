"""
真实 Prompt 拼装验证
对全部 pass1 块真实构造 system_prompt + user_prompt，不发送给模型。
检查占位符残留、token 上限、格式正确性、编码。
"""
import json, sys, io, os, re, yaml
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CORPUS = BASE / 'corpus'
CONFIG = BASE / 'config'
TASKS = BASE / 'tasks'
PROMPTS = WORK / 'prompts'

sys.path.insert(0, str(BASE / 'scripts'))
from token_utils import TOKEN_COEFFICIENT, estimate_tokens as count_tokens

def load_chunks():
    with open(CONFIG / 'task_chunks.json', 'r', encoding='utf-8') as f:
        return json.load(f)['chunks']

def load_cite_index():
    idx = {}
    with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                idx[rec['cite_id']] = rec
    return idx

def load_task_card(task_id):
    path = TASKS / f'{task_id}.yaml'
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def build_corpus_entries(cite_ids, cite_index):
    """Build the [cite_id]\\nclean\\n\\n block for a chunk."""
    lines = []
    for cid in cite_ids:
        rec = cite_index.get(cid)
        if rec and rec.get('clean'):
            lines.append(f"[{cid}]\n{rec['clean']}\n")
    return '\n'.join(lines)

def main():
    PROMPTS.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    cite_index = load_cite_index()
    task_card = load_task_card('T1_entity_relation')

    if not task_card:
        print("ERROR: T1 task card not found")
        return

    system_prompt = task_card.get('system_prompt', '')
    user_template = task_card.get('user_prompt_template', '')

    print(f"System prompt: {len(system_prompt)} chars, ~{count_tokens(system_prompt)} tokens")
    print(f"User template: {len(user_template)} chars\n")

    report = {'chunks': [], 'issues': []}
    total_estimated = 0
    total_actual = 0

    for chunk in chunks:
        cid = chunk['chunk_id']
        vol = chunk['volume']
        cite_ids = chunk['cite_ids']

        # Build corpus entries
        corpus_text = build_corpus_entries(cite_ids, cite_index)

        # Build user prompt
        user_prompt = user_template.replace('{volume_name}', vol)
        user_prompt = user_prompt.replace('{entry_count}', str(len(cite_ids)))
        user_prompt = user_prompt.replace('{scope_description}', chunk.get('description', ''))
        user_prompt = user_prompt.replace('{corpus_entries}', corpus_text)

        # Build full prompt
        full_prompt = system_prompt + '\n\n' + user_prompt

        # Stats
        actual_chars = len(full_prompt)
        actual_tokens = count_tokens(full_prompt)
        estimated_tokens = chunk['token_est']
        deviation = (actual_tokens - estimated_tokens) / estimated_tokens * 100 if estimated_tokens else 0

        # Check for unreplaced placeholders
        unreplaced = re.findall(r'\{[a-z_]+\}', full_prompt)

        result = {
            'chunk_id': cid,
            'volume': vol,
            'entry_count': len(cite_ids),
            'full_chars': actual_chars,
            'full_tokens_est': actual_tokens,
            'estimated_in_plan': estimated_tokens,
            'deviation_pct': round(deviation, 1),
            'unreplaced_placeholders': unreplaced,
            'over_limit': actual_tokens > 600_000,
        }
        report['chunks'].append(result)

        total_estimated += estimated_tokens
        total_actual += actual_tokens

        # Save full prompt
        with open(PROMPTS / f'{cid}.txt', 'w', encoding='utf-8') as f:
            f.write(full_prompt)

        # Collect issues
        if unreplaced:
            report['issues'].append(f'{cid}: unreplaced placeholders: {unreplaced}')
        if result['over_limit']:
            report['issues'].append(f'{cid}: OVER LIMIT ({actual_tokens} > 600,000)')

        print(f"{cid} {vol:>15s} {len(cite_ids):>6,d} entries → {actual_chars:>10,d} chars ~{actual_tokens:>10,d} tokens (plan: {estimated_tokens:>10,d}, {deviation:>+5.1f}%)")

        # Spot check: first 20 lines of corpus for 3 chunks
        if cid in ('C001', 'C008', 'C018'):
            lines = corpus_text.split('\n')[:20]
            print(f"\n  --- {cid} corpus first 20 lines ---")
            for l in lines:
                print(f"  {l[:120]}")
            print()

    # Encoding check: read back the largest prompt
    largest = max(report['chunks'], key=lambda x: x['full_chars'])
    with open(PROMPTS / f"{largest['chunk_id']}.txt", 'r', encoding='utf-8') as f:
        content = f.read()
    has_garbled = any(ord(c) > 0xFFFF or (0xD800 <= ord(c) <= 0xDFFF) for c in content[:10000])
    if not has_garbled:
        print("Encoding check: PASS (no garbled characters) ✓")
    else:
        print("Encoding check: FAIL (garbled characters detected) ✗")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(report['chunks'])} chunks")
    print(f"  Total chars: {total_actual:,}")
    print(f"  Total tokens (est): {total_actual:,}")
    print(f"  Total plan estimate: {total_estimated:,}")
    print(f"  Overall deviation: {(total_actual - total_estimated)/total_estimated*100:+.1f}%")
    print(f"  Over limit blocks: {sum(1 for c in report['chunks'] if c['over_limit'])}")
    print(f"  Issues: {len(report['issues'])}")

    if report['issues']:
        print(f"\nISSUES:")
        for i in report['issues']:
            print(f"  {i}")

    # Save report
    report['summary'] = {
        'total_chars': total_actual,
        'total_tokens': total_actual,
        'total_plan_estimate': total_estimated,
        'overall_deviation_pct': round((total_actual - total_estimated)/total_estimated*100, 1),
        'over_limit_count': sum(1 for c in report['chunks'] if c['over_limit']),
        'encoding_ok': not has_garbled,
    }
    with open(WORK / 'prompt_assembly_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Print largest prompt head + tail
    print(f"\n{'='*60}")
    print(f"LARGEST PROMPT: {largest['chunk_id']} ({largest['volume']}, {largest['full_chars']:,} chars)")
    print(f"{'='*60}")
    with open(PROMPTS / f"{largest['chunk_id']}.txt", 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print("--- First 100 lines ---")
    for l in lines[:100]:
        print(l.rstrip()[:150])
    print(f"\n... ({len(lines)-120} lines omitted) ...\n")
    print("--- Last 20 lines ---")
    for l in lines[-20:]:
        print(l.rstrip()[:150])

    print(f"\nPrompts saved to: {PROMPTS}")

if __name__ == '__main__':
    main()

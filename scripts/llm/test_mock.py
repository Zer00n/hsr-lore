"""
B3: Mock provider 验证 — 20 次假调用，验证日志结构完整
"""
import json
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.llm.client import get_client

mock_dir = "config/mock_responses"
os.makedirs(mock_dir, exist_ok=True)

test_messages = [
    [{"role": "user", "content": "Test task %d: HSR lore analysis." % i}]
    for i in range(1, 21)
]

task_names = [
    "character_relation", "timeline_ordering", "faction_analysis",
    "planet_lore_summary", "dialogue_sentiment", "entity_linking",
    "contradiction_detection", "narrative_gap", "relationship_graph",
    "power_ranking", "species_classification", "event_causality",
    "cultural_analysis", "language_style", "plot_arc_detection",
    "character_arc", "faction_conflict", "worldview_consistency",
    "cross_reference", "timeline_contradiction",
]

volumes = ["lore", "books", "characters", "narrative", "dialogue", "artifacts", "rogue"]

for i, msgs in enumerate(test_messages):
    input_str = json.dumps(msgs, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(input_str.encode('utf-8')).hexdigest()[:16]
    mock_file = os.path.join(mock_dir, digest + ".json")
    with open(mock_file, 'w', encoding='utf-8') as f:
        json.dump({
            'choices': [{'message': {'content': 'Mock response %d: analysis result.' % (i+1)}}],
            'usage': {'prompt_tokens': 150 + i*10, 'completion_tokens': 200 + i*15, 'total_tokens': 350 + i*25},
            'finish_reason': 'stop',
        }, f, ensure_ascii=False)

client = get_client(profile="mock", run_id="mock_test_001")

print("Run ID: %s" % client.run_id)
print("Provider: %s" % client.config['provider'])
print()

for i in range(20):
    msgs = test_messages[i]
    task = task_names[i]
    vol = volumes[i % len(volumes)]
    response = client.chat(
        messages=msgs, task_name=task, input_volume=vol,
        max_tokens=2048, output_path="work/outputs/%s.json" % task,
    )
    print("[%2d] %s: %d tokens, %dms" % (i+1, task, response['usage']['total_tokens'], response['latency_ms']))

print()

manifest_path = "logs/runs/%s/manifest.json" % client.run_id
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

print("=" * 50)
print("MANIFEST")
print("=" * 50)
print(json.dumps(manifest, ensure_ascii=False, indent=2))

calls_path = "logs/runs/%s/calls.jsonl" % client.run_id
call_count = 0
total_tokens = 0
with open(calls_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            call = json.loads(line)
            call_count += 1
            total_tokens += call['total_token']

print("\nVerification:")
print("  Calls: %d/20" % call_count)
print("  Manifest count match: %s" % (manifest['call_count'] == call_count))
print("  Manifest token match: %s" % (manifest['total_tokens'] == total_tokens))
print("  All passed: %s" % (manifest['call_count'] == 20 and manifest['total_tokens'] == total_tokens))
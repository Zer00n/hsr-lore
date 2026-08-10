import json
import pathlib

base = pathlib.Path(r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData')

with open(base / 'TextMap/TextMapCHS.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Type:', type(data).__name__)
if isinstance(data, dict):
    keys = list(data.keys())
    print('Key count:', len(keys))
    first_key = keys[0]
    print(f'Value for key {first_key}:', json.dumps(data[first_key], ensure_ascii=False)[:200])
elif isinstance(data, list):
    print('Length:', len(data))
    print('First item:', json.dumps(data[0], ensure_ascii=False)[:200])
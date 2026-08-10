import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load AvatarConfig
with open(r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData\ExcelOutput\AvatarConfig.json', 'r', encoding='utf-8') as f:
    avatars = json.load(f)

# Load TextMapCHS for name resolution
with open(r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData\TextMap\TextMapCHS.json', 'r', encoding='utf-8') as f:
    textmap = json.load(f)

# Sort by AvatarID descending
avatars_sorted = sorted(avatars, key=lambda x: x['AvatarID'], reverse=True)

# Find the last 15 non-{NICKNAME} avatars
non_nickname = []
for a in avatars_sorted:
    name_hash = str(a['AvatarName']['Hash'])
    name = textmap.get(name_hash, 'NOT_FOUND')
    if name != '{NICKNAME}':
        non_nickname.append((a, name))
    if len(non_nickname) >= 15:
        break

print('=== Last 15 Non-NICKNAME Avatars by ID (descending) ===')
for a, name in non_nickname:
    print(f"ID={a['AvatarID']:>8}  Name={name}")

print(f'\n=== Total avatars: {len(avatars)} ===')
print(f'=== NICKNAME avatars in top IDs: {sum(1 for a in avatars_sorted if textmap.get(str(a["AvatarName"]["Hash"]), "") == "{NICKNAME}")} ===')
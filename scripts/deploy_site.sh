#!/usr/bin/env bash
# deploy_site.sh — 生成真数据、构建验证、提交推送
# 周一晚上只需要跑这一个脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SITE_DIR="$REPO_ROOT/site"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  deploy_site.sh — 真数据生成 → 构建验证 → 提交推送          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 步骤 1: 生成真数据 ──────────────────────────────────────────────

echo "▶ 步骤 1/3: 生成真数据"
echo "  运行 build_site_data.py（pass1 + pass2）..."
cd "$REPO_ROOT"
python scripts/build_site_data.py --input output/pass1 --pass2 --filter-mode filter 2>&1
echo ""

echo "  运行 build_stats.py..."
python scripts/build_stats.py 2>&1
echo ""

# 报告体积
echo "  site/public/data/ 各文件体积："
for f in "$SITE_DIR/public/data"/*.json; do
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)
    name=$(basename "$f")
    printf "    %-24s %'d bytes\n" "$name" "$size"
done
echo ""

# ── 步骤 2: 本地构建验证 ────────────────────────────────────────────

echo "▶ 步骤 2/3: 本地构建验证"
cd "$SITE_DIR"
npm run build 2>&1
echo ""
echo "  构建成功 ✓"
echo ""

# ── 步骤 3: 提交并推送 ──────────────────────────────────────────────

echo "▶ 步骤 3/3: 提交并推送"
echo ""
echo "  ⚠ 即将把 site/public/data/*.json（真数据）提交并推送到 GitHub。"
echo "  请确认这些数据不包含不应公开的敏感信息（如 API 密钥）、"
echo "  且确实是想发布的数据（而非示例数据）。"
echo ""
read -rp "  确认推送？[y/N] " yn

if [[ ! "$yn" =~ ^[yY]$ ]]; then
    echo ""
    echo "  已取消。未推送任何数据。"
    exit 0
fi

cd "$SITE_DIR"
git add -A
git diff --cached --stat

# 提交消息含时间戳
commit_msg="deploy: 接入真数据 $(date '+%Y-%m-%d %H:%M')"
echo ""
echo "  提交信息：$commit_msg"
git commit -m "$commit_msg"

echo ""
echo "  推送到 origin main..."
git push origin main

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  部署完成 ✓"
echo "  数据已推送到 GitHub，Cloudflare Pages 将自动触发构建。"
echo "════════════════════════════════════════════════════════════════"

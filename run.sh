#!/bin/bash
# 抓取 -> 去重筛选 -> mihomo 校验 -> 原子替换 dist/clash.yaml
set -euo pipefail
cd "$(dirname "$0")"
MIHOMO="${MIHOMO:-./mihomo}"; export MIHOMO
SOURCES="${SOURCES:-sources_barabama.yaml}"
mkdir -p dist output/raw
python3 scraper.py -c "$SOURCES" -o output/raw
OUT=dist/.clash.new.yaml python3 pick400.py
rm -rf /tmp/mtfull && mkdir -p /tmp/mtfull
"$MIHOMO" -t -d /tmp/mtfull -f dist/.clash.new.yaml | tail -1 | grep -q "successful"
mv dist/.clash.new.yaml dist/clash.yaml
echo "UPDATED $(grep -c '^- name:\|^  - name:' dist/clash.yaml) $(date '+%F %T')"

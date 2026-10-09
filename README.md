# node-scraper

抓取公开免费节点 → 去重筛选 → mihomo 校验 → GeoIP 重命名，输出 Clash/Mihomo 配置 `dist/clash.yaml`（默认最多 400 个节点）。

## 自动更新
GitHub Actions（`.github/workflows/update.yml`）每天北京时间 **08:00 / 12:00 / 18:00** 运行，结果提交到 `dist/clash.yaml`。也可在 Actions → Update nodes → Run workflow 手动触发。
注：GitHub 定时任务高峰期可能延迟几分钟到几十分钟；仓库 60 天无活动会自动停用定时任务（本仓库每次更新都会提交，一般不会触发）。

订阅地址：`https://raw.githubusercontent.com/<用户名>/<仓库>/main/dist/clash.yaml`

## 本地运行
    pip install -r requirements.txt
    # 下载 mihomo 放到当前目录，或 export MIHOMO=/path/to/mihomo
    ./run.sh

可选环境变量：`SOURCES`（来源配置，默认 sources_barabama.yaml，另有 sources_gh.yaml）、`LIMIT`（节点数，默认 400）。

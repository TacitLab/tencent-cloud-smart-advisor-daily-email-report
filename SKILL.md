---
name: tencent-smart-advisor-daily-email-report
description: Generate intelligent daily reports from Tencent Smart Advisor emails using Skill composition. Orchestrates himalaya (email), summarize (content analysis), and LLM reasoning to produce insights. Supports multi-account/architecture report grouping, local caching with deduplication, and period-over-period comparison.
metadata:
  openclaw:
    emoji: 📊
    requires:
      skills:
        - himalaya
        - summarize
      bins:
        - jq
        - bash
        - summarize
---

# Tencent Smart Advisor Daily Report

**Orchestration Skill** — This skill composes specialized skills (`himalaya`, `summarize`) to generate intelligent reports from Tencent Smart Advisor emails, with support for:

- **Multi-account/Architecture Grouping** — Reports organized by APPID and architecture diagram
- **Local Caching with Deduplication** — Emails stored in `~/.advisor` with automatic dedup
- **Period-over-Period Comparison** — Compare current report with previous cycles

---

## Dependencies

```bash
# Required skills (must be installed)
openclaw skills install himalaya
openclaw skills install summarize

# Required binaries
# - jq (JSON processing)
# - bash
# - summarize (from summarize skill)
```

---

## Cache Architecture

Emails and attachments are stored in a hierarchical structure:

```
~/.advisor/
├── index.json                    # Email metadata index (for deduplication)
├── accounts.json                 # Account name mappings
├── reports/                      # Processed reports
│   └── 1312346585/              # APPID
│       └── 2026-02-25/          # Date
│           ├── arch-nff1ftst/   # Architecture diagram
│           │   ├── risk-report.json
│           │   ├── inspection-report.json
│           │   └── capacity-report.json
│           └── daily-summary.md
├── raw/                          # Raw email content
│   └── 1312346585/
│       └── 2026-02-25/
│           ├── 3120-content.txt
│           ├── 3120-meta.json
│           └── attachments/
└── compare/                      # Period comparison cache
    └── 1312346585/
        └── arch-nff1ftst/
            ├── prev-date.txt
            └── diff.json
```

---

## Quick Start

### Generate Today's Report (All Accounts)

```bash
# Fetch new emails, update cache, generate report
./scripts/advisor-report.sh --today

# Generate report with period comparison
./scripts/advisor-report.sh --today --compare
```

### Generate Report for Specific Account

```bash
./scripts/advisor-report.sh --appid 1312346585 --today
```

### Force Refresh (Ignore Cache)

```bash
./scripts/advisor-report.sh --today --force
```

---

## Scripts Reference

### 1. advisor-report.sh — Main Report Generator

```bash
Usage: ./scripts/advisor-report.sh [OPTIONS]

Options:
  --today              Generate report for today
  --date YYYY-MM-DD    Generate report for specific date
  --appid ID           Filter by specific APPID
  --architecture NAME  Filter by architecture diagram name
  --compare            Enable period-over-period comparison
  --force              Ignore cache, re-fetch all emails
  --output FORMAT      Output format: markdown|json|terminal (default: markdown)
  --cache-dir PATH     Cache directory (default: ~/.advisor)
```

### 2. advisor-sync.sh — Email Sync & Cache Update

```bash
Usage: ./scripts/advisor-sync.sh [OPTIONS]

Options:
  --since-hours N      Sync emails from last N hours (default: 24)
  --dry-run            Show what would be synced without downloading
  --prune-days N       Remove cache entries older than N days
```

### 3. advisor-compare.sh — Period Comparison

```bash
Usage: ./scripts/advisor-compare.sh [OPTIONS]

Options:
  --appid ID           Account to compare (required)
  --architecture NAME  Architecture to compare (optional)
  --current DATE       Current period date (default: today)
  --previous DATE      Previous period date (auto-detected if not specified)
```

---

## Manual Operations

### Step 1: Sync Emails to Cache

```bash
# Create cache directory
mkdir -p ~/.advisor/{raw,reports,compare}

# Fetch and parse emails
himalaya envelope list from:email@advisor.cloud.tencent.com --output json | \
  ./scripts/parse-and-cache.sh
```

The `parse-and-cache.sh` script:
1. Parses email subject to extract APPID, report type, architecture name
2. Checks index.json for duplicates (by message-id)
3. Downloads email content and attachments to appropriate cache directory
4. Updates index.json with metadata

### Step 2: Parse Cached Data

The system uses the `summarize` tool to extract content from Excel attachments:

```bash
# Parse Excel attachments using summarize
summarize ~/.advisor/raw/1312346585/2026-02-25/attachments/*.xlsx --json
```

### Step 3: Generate Structured Report

```bash
# Generate per-account/architecture reports
python3 ./scripts/generate-report.py \
  --appid 1312346585 \
  --date 2026-02-25 \
  --cache-dir ~/.advisor \
  --output-format markdown
```

---

## Report Structure

### Per-Account Report

```markdown
# 📊 腾讯云智能顾问日报 | 2026-02-25

## 账号概览: 1312346585 (深圳市腾讯计算机系统有限公司)

### 架构图: arch-nff1ftst (游戏行业架构图)

#### 评估时间: 2026-02-25 17:09:01

| 资源类型 | 数量 | 占比 |
|---------|-----:|-----:|
| CVM | 5 | 38.46% |
| MySQL | 4 | 30.77% |
| Redis | 1 | 7.69% |
| CKafka | 1 | 7.69% |
| EMR-HDFS | 1 | 7.69% |
| CLB | 1 | 7.69% |

#### 负载状态

| 状态 | 数量 |
|-----|-----:|
| 🔴 严重高负载 | 1 |
| 🟠 高负载 | 1 |
| 🟢 正常负载 | 0 |
| ⚪ 未充分使用 | 11 |

#### 风险汇总

| 级别 | 数量 | 变化(较昨日) |
|-----|-----:|:-----------:|
| 🔴 高风险 | 7 | ↑ +2 |
| 🟡 中风险 | 13 | ↓ -3 |
| ✅ 健康 | 104 | → 0 |

#### 高风险详情

| 云产品 | 评估项 | 影响资源 | 风险描述 | 持续天数 |
|--------|--------|----------|----------|---------:|
| EdgeOne | DDoS防护未配置 | zone-xxx | 默认策略不足 | **34天** 🔺 |
| EdgeOne | 签名冲突 | 4个域名 | 与COS源站冲突 | 17天 |

---

### 架构图: other-arch (电商架构)

[...]
```

---

## Period-over-Period Comparison

When `--compare` is enabled, the report includes:

### Risk Trend

```markdown
## 趋势对比 (较 2026-02-24)

| 指标 | 昨日 | 今日 | 变化 |
|-----|-----:|-----:|:----:|
| 高风险 | 5 | 7 | 🔺 +2 |
| 中风险 | 16 | 13 | 🟢 -3 |
| 健康 | 102 | 104 | → +2 |

### 新增风险

| 云产品 | 评估项 | 风险级别 |
|--------|--------|---------:|
| CVM | 磁盘使用率过高 | 🔴 高风险 |

### 已解决风险

| 云产品 | 评估项 | 原级别 |
|--------|--------|-------:|
| COS | 存储桶公开访问 | 🟡 中风险 |

### 持续未处理风险 (>15天)

| 云产品 | 评估项 | 持续天数 |
|--------|--------|---------:|
| EdgeOne | DDoS防护未配置 | **34天** ⏰ |
```

---

## Cache Index Format

`~/.advisor/index.json`:

```json
{
  "version": "1.0",
  "lastSync": "2026-02-26T17:00:00Z",
  "emails": {
    "3120": {
      "messageId": "<abc123@tencent.com>",
      "subject": "腾讯云智能顾问(TSA)-架构风险治理报告-arch-nff1ftst",
      "appId": "1312346585",
      "accountName": "深圳市腾讯计算机系统有限公司",
      "reportType": "risk",
      "architecture": "arch-nff1ftst",
      "date": "2026-02-25",
      "timestamp": "2026-02-25T17:09:01+08:00",
      "cachedAt": "2026-02-26T09:00:00Z",
      "attachments": [
        "腾讯云智能顾问评估结果_xxx.xlsx"
      ]
    }
  }
}
```

---

## Deduplication Logic

1. **Primary Key**: Message-ID from email headers
2. **Fallback**: Subject + Date + APPID combination
3. **Update Strategy**: If same report type for same account/architecture on same date, keep latest

```bash
# Check if email already cached
./scripts/check-duplicate.sh <message-id>
```

---

## Platform Formatting

### Discord
- Full Markdown tables supported
- Use `<https://url>` for link preview suppression

### Telegram
- Tables converted to formatted lists
- Use emoji indicators for quick scanning

### Terminal/CLI
- Compact table format
- Color coding (if terminal supports)

---

## Heartbeat Integration

Add to `HEARTBEAT.md`:

```markdown
## Tencent Smart Advisor Daily Check

Run at 09:00 daily:

```bash
# Sync and check for critical alerts
./scripts/advisor-sync.sh --since-hours 24
./scripts/check-critical.sh --notify
```
```

---

## Troubleshooting

### Cache Corruption

```bash
# Rebuild index from cached files
./scripts/rebuild-index.sh

# Clear cache for specific date
rm -rf ~/.advisor/raw/1312346585/2026-02-25
```

### Missing Account Names

Edit `~/.advisor/accounts.json`:

```json
{
  "1312346585": "深圳市腾讯计算机系统有限公司",
  "other-appid": "Account Display Name"
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│           Tencent Smart Advisor Report Skill                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐   │
│  │  himalaya   │────▶│  Cache      │────▶│  Report Gen     │   │
│  │  (fetch)    │     │  Manager    │     │  (shell script) │   │
│  └─────────────┘     └──────┬──────┘     └────────┬────────┘   │
│                             │                      │            │
│                      ┌──────▼──────┐              ▼            │
│                      │  ~/.advisor │     ┌─────────────────┐   │
│                      │  /raw       │────▶│  summarize      │   │
│                      │  /reports   │     │  (required)     │   │
│                      └─────────────┘     └─────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

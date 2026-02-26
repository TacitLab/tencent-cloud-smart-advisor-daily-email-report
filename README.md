# Tencent Smart Advisor Daily Email Report

[![GitHub](https://img.shields.io/github/license/TacitLab/tencent-smart-advisor-daily-email-report)](LICENSE)

An OpenClaw Skill for generating intelligent daily reports from Tencent Smart Advisor (腾讯云智能顾问) emails.

## Features

- **Multi-Account/Architecture Grouping** — Organize reports by APPID and architecture diagram
- **Local Caching with Deduplication** — Emails stored in `~/.advisor` with automatic deduplication via message-id
- **Period-over-Period Comparison** — Compare current report with previous cycles to track trends
- **Pure Shell Implementation** — No Python dependencies, uses existing OpenClaw skills
- **Auto Account Name Mapping** — Automatically extracts and maps account names from emails

## Quick Start

```bash
# Install required skills
openclaw skills install himalaya
openclaw skills install summarize

# Generate today's report
./scripts/advisor-report.sh --today

# Generate with period comparison
./scripts/advisor-report.sh --today --compare

# Generate for specific account
./scripts/advisor-report.sh --appid 1234567890 --today
```

## Dependencies

- `himalaya` — Email fetching (OpenClaw skill)
- `summarize` — Excel content extraction (OpenClaw skill)
- `jq` — JSON processing
- `bash` — Script execution

## Cache Structure

```
~/.advisor/
├── index.json              # Email deduplication index
├── accounts.json           # Account name mappings
├── reports/                # Generated reports
│   └── 1234567890/        # APPID
│       └── 2026-02-25/    # Date
│           └── arch-name/ # Architecture
└── raw/                    # Cached emails
```

## Scripts

| Script | Purpose |
|--------|---------|
| `advisor-report.sh` | Main orchestrator — sync emails and generate reports |
| `advisor-sync.sh` | Email sync and cache management |
| `generate-report.sh` | Generate per-account/architecture reports |
| `daily-summary.sh` | Aggregate daily summary |
| `advisor-compare.sh` | Period comparison tool |

## Report Example

```markdown
# 📊 Tencent Smart Advisor Daily Report | 2026-02-25

## Account: Example Corp (1234567890)

### Architecture: production-arch

**Report Type**: 🔴 Risk Governance Report

#### Risk Summary

| Level | Count |
|-------|------:|
| 🔴 High Risk | 7 |
| 🟡 Medium Risk | 13 |
| ✅ Healthy | 104 |

#### High Risk Details

1. **CVM — Disk Usage Too High**
   - Category: Performance
   - Suggestion: Expand disk or clean up files
```

## Configuration

### Account Name Mapping

The system automatically extracts account names from emails. To manually override:

```bash
# Edit ~/.advisor/accounts.json
{
  "1234567890": "Your Company Name",
  "other-appid": "Another Account"
}
```

## Documentation

- [中文文档](README.zh-CN.md)
- [SKILL.md](SKILL.md) — Detailed technical documentation

## License

MIT

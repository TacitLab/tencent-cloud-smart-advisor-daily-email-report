---
name: tencent-smart-advisor-daily-email-report
description: Generate intelligent daily reports from Tencent Smart Advisor emails using Skill composition. Orchestrates himalaya (email), summarize (content analysis), and LLM reasoning to produce insights. Use when users need to (1) analyze Tencent Smart Advisor emails from email@advisor.cloud.tencent.com, (2) get summarized reports of cloud resource status, capacity, and risk assessments, (3) monitor Tencent Cloud infrastructure through email notifications.
metadata:
  openclaw:
    emoji: 📊
    requires:
      skills:
        - himalaya
        - summarize
      bins:
        - jq
---

# Tencent Smart Advisor Daily Report

**Orchestration Skill** — This skill does not implement email fetching or document parsing itself. Instead, it composes existing specialized skills (`himalaya`, `summarize`) to generate intelligent reports from Tencent Smart Advisor emails.

## Dependencies

This skill requires the following skills to be installed:

1. **himalaya** — Email CLI for fetching emails and attachments
   - Install: `openclaw skills install himalaya`
   - Config: Requires `~/.config/himalaya/config.toml` with IMAP credentials

2. **summarize** — Content extraction and summarization
   - Install: `openclaw skills install summarize`
   - Config: Requires `GEMINI_API_KEY` or other LLM provider key

## Prerequisites

Before using this skill, ensure:

```bash
# 1. himalaya is installed and configured
himalaya --version
himalaya envelope list --limit 1

# 2. summarize is installed
which summarize

# 3. jq is available for JSON processing
jq --version
```

## Quick Start

### Generate Today's Report

```bash
# Step 1: Fetch recent emails from Tencent Advisor
himalaya envelope list from:email@advisor.cloud.tencent.com --output json | jq '.[0:10]'

# Step 2: Read email content (replace ID with actual ID)
himalaya message read <email-id>

# Step 3: Download attachments
himalaya attachment download <email-id> --dir /tmp/advisor-attachments

# Step 4: Summarize attachments
summarize /tmp/advisor-attachments/*.xlsx --model google/gemini-3-flash-preview
summarize /tmp/advisor-attachments/*.pdf --model google/gemini-3-flash-preview
```

## Automated Report Generation

### Using the Shell Script

```bash
# Generate report for last N hours (default: 24)
./scripts/generate-report.sh 24

# Generate report for last 7 days
./scripts/generate-report.sh 168
```

The script:
1. Uses `himalaya` to fetch emails from `email@advisor.cloud.tencent.com`
2. Downloads attachments to temp directory
3. Calls `summarize` on each attachment
4. Outputs structured JSON for LLM analysis

### Manual Orchestration

If you need finer control:

```bash
# 1. List recent advisor emails
ADVISOR_EMAILS=$(himalaya envelope list from:email@advisor.cloud.tencent.com since:$(date -u -d '24 hours ago' +%Y-%m-%d) --output json)

# 2. Extract email IDs
EMAIL_IDS=$(echo "$ADVISOR_EMAILS" | jq -r '.[].id')

# 3. Process each email
for ID in $EMAIL_IDS; do
    # Read email body
    himalaya message read "$ID"
    
    # Download attachments
    himalaya attachment download "$ID" --dir "/tmp/advisor/$ID"
done

# 4. Summarize all attachments
for FILE in /tmp/advisor/*/*.{xlsx,pdf,csv}; do
    [ -f "$FILE" ] && summarize "$FILE" --json
done
```

## Report Types

Tencent Smart Advisor sends these email types:

| Email Type | Subject Pattern | Attachment Type |
|-----------|-----------------|-----------------|
| **Capacity Report** | `架构负载报告` | .xlsx, .pdf |
| **Inspection Report** | `日常巡检报告` | .xlsx |
| **Risk Report** | `架构风险治理报告` | .xlsx |
| **Alert** | `告警` | varies |

## LLM-Powered Summary

After gathering raw data via the scripts above, present it to the LLM for intelligent summarization:

**Prompt Pattern:**
```
Based on the following Tencent Smart Advisor data, generate a daily report:

[Raw email subjects and metadata from himalaya]
[Extracted content from summarize]

Please provide:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Action Items (prioritized)
4. Trending Analysis (if applicable)
```

## Heartbeat Integration

Add to `HEARTBEAT.md` for periodic checks:

```markdown
## Tencent Smart Advisor Check (every 6 hours)
Check for critical alerts from Tencent Advisor:

```bash
# Run the check script
./scripts/check-critical.sh
```
```

The check script returns non-zero if critical items are found.

## Troubleshooting

### "himalaya not found"
```bash
openclaw skills install himalaya
```

### "summarize not found"
```bash
openclaw skills install summarize
```

### No emails returned
- Verify himalaya config: `himalaya account list`
- Check sender filter: emails must be from `email@advisor.cloud.tencent.com`
- Verify date range: Tencent Advisor typically sends daily reports

### Attachment download fails
- Check directory permissions
- Ensure email has attachments: `himalaya message read <id>` shows attachment count

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Tencent Smart Advisor Skill (Orchestration Layer)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │  himalaya   │    │  summarize  │    │  LLM Reasoning      │ │
│  │  (email)    │───▶│  (extract)  │───▶│  (intelligent       │ │
│  │             │    │             │    │   summary)          │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│         ▲                                                │      │
│         │                                                ▼      │
│  ┌─────────────┐                              ┌─────────────────┴─┐
│  │  IMAP/SMTP  │                              │  Final Report     │
│  │  Server     │                              │  (natural lang)   │
│  └─────────────┘                              └───────────────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

This skill acts as the **conductor**, not the **musician**.

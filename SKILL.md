---
name: tencent-smart-advisor-daily-email-report
description: Generate intelligent daily reports from Tencent Smart Advisor emails with advanced content extraction, attachment processing, and actionable insights. Automatically monitors email@advisor.cloud.tencent.com, extracts metrics from HTML/attachments, classifies reports by type (capacity/inspection/alert/cost/security), and generates comprehensive summaries with highlights, action items, and dashboard links. Use when users need to (1) analyze Tencent Smart Advisor emails with detailed content extraction, (2) monitor cloud resource reports with intelligent summarization, (3) set up automated daily reports with heartbeat notifications for critical alerts.
---

# Tencent Smart Advisor Daily Email Report

Intelligent email analysis and reporting system for Tencent Smart Advisor.

## Quick Start

### 1. Configure Email Connection

```bash
# Set environment variables
export EMAIL_HOST="imap.gmail.com"
export EMAIL_USER="your-email@gmail.com"
export EMAIL_PASS="your-app-password"
export EMAIL_SENDER="email@advisor.cloud.tencent.com"

# Or use the setup wizard
python3 scripts/setup_email.py
```

### 2. Generate Daily Report

```bash
# Generate intelligent report with full analysis
cd /root/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/skills/tencent-smart-advisor-daily-email-report
source config/email.env
python3 scripts/tencent_advisor_analyzer.py

# Output as JSON
python3 scripts/tencent_advisor_analyzer.py --format json

# Save to file
python3 scripts/tencent_advisor_analyzer.py --output report.md
```

### 3. Set Up Heartbeat Hook (Optional)

Add to HEARTBEAT.md for periodic checks:

```markdown
## Tencent Smart Advisor Check
Run every 30 minutes to check for critical alerts:
```bash
python3 /path/to/scripts/heartbeat_hook.py
```
If critical/high importance emails found, returns alert notification.
```

## Features

### 1. Advanced Content Extraction
- **HTML Parsing**: Extracts structured data from HTML emails
- **Attachment Support**: Downloads and processes CSV/Excel/PDF attachments
- **Link Extraction**: Captures all dashboard/report links
- **Metrics Recognition**: Automatically identifies CPU, memory, disk usage metrics

### 2. Intelligent Classification
Emails are classified by type:
- **Capacity Reports**: Resource usage, load monitoring
- **Inspection Reports**: Best practices, AI analysis (DeepSeek/Hunyuan)
- **Alerts**: Warnings, risks, anomalies
- **Cost Reports**: Billing, expense analysis
- **Security Reports**: Security assessments

### 3. Smart Summarization
Generates comprehensive reports with:
- **Executive Summary**: Overall status and key metrics
- **Highlights**: Important findings and recommendations
- **Action Items**: Suggested next steps
- **Dashboard Links**: Direct links to detailed reports

### 4. Heartbeat Integration
- Periodic checks for critical/high importance emails
- Automatic notifications when attention required
- Configurable check intervals

## Output Format

### Report Structure

```markdown
# 腾讯智能顾问日报 - 2026-02-25

## 📊 概览
过去24小时收到3封邮件，包括容量报告:1封, 巡检报告:1封, 告警:1封

## 📈 邮件分类统计
- 📊 容量报告: 1 封
- 🔍 巡检报告: 1 封
- 🚨 告警: 1 封

## ⚠️ 需要关注
- **架构负载报告** - 容量监测报告 - 架构ID: arch-xxx, APPID: 1312346585

## 💡 重点信息
- CPU使用率达到85%，建议扩容
- 检测到3个安全风险

## 🎯 建议操作
- 查看详细容量报告
- 处理安全告警

## 📋 详细报告

### 腾讯云智能顾问(TSA)-架构负载报告
- **类型**: 📊 容量报告
- **重要性**: high
- **摘要**: 容量监测报告 - 架构ID: arch-nff1ftst, APPID: 1312346585
- **附件**: capacity_report.csv
- **查看详情**: [点击访问](https://...)

---
*报告生成时间: 17:20 | 统计周期: 过去24小时*
```

## Scripts Reference

### Main Scripts

- **`scripts/tencent_advisor_analyzer.py`**: Main analyzer with full content extraction
  - `--hours`: Time range (default: 24)
  - `--format`: Output format (markdown/json)
  - `--output`: Save to file
  - `--hook`: Run as heartbeat hook

- **`scripts/heartbeat_hook.py`**: Periodic check for critical alerts
  - Returns JSON notification if critical/high items found
  - Returns "HEARTBEAT_OK" if no action needed

- **`scripts/setup_email.py`**: Interactive configuration wizard

- **`scripts/email_daily_report.py`**: Legacy basic reporter (deprecated)

### Data Storage

```
data/
├── email_history.json      # Historical email data
├── latest_report.json      # Latest generated report
└── attachments/            # Downloaded attachments
    ├── {email_id}_report.csv
    ├── {email_id}_data.xlsx
    └── ...
```

## Heartbeat Integration

### Setup in HEARTBEAT.md

Add this to your HEARTBEAT.md for automatic monitoring:

```markdown
### Tencent Smart Advisor Alert Check (every 30 min)
Check for critical/high importance emails from Tencent Advisor:
```bash
python3 /root/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/skills/tencent-smart-advisor-daily-email-report/scripts/heartbeat_hook.py
```
If returns non-zero exit code, alert contains critical items requiring attention.
```

### Heartbeat Output Format

**Normal (HEARTBEAT_OK)**:
```
HEARTBEAT_OK
```

**Alert Detected**:
```json
{
  "type": "tencent_advisor_alert",
  "timestamp": "2026-02-25T17:20:00",
  "summary": "检测到 1 项紧急, 2 项重要",
  "critical_count": 1,
  "high_count": 2,
  "items": [
    {
      "subject": "架构负载报告",
      "type": "capacity_report",
      "importance": "high",
      "summary": "CPU使用率超过阈值"
    }
  ]
}
```

## Usage Examples

### Basic Daily Report
```bash
python3 scripts/tencent_advisor_analyzer.py
```

### Check Last 48 Hours
```bash
python3 scripts/tencent_advisor_analyzer.py --hours 48
```

### JSON Output for Automation
```bash
python3 scripts/tencent_advisor_analyzer.py --format json --output report.json
```

### Heartbeat Check
```bash
python3 scripts/heartbeat_hook.py
```

## Email Configuration

For detailed email provider setup, see [references/email_configuration.md](references/email_configuration.md).

### Supported Providers

| Provider | IMAP Server | Notes |
|----------|-------------|-------|
| Gmail | `imap.gmail.com` | Requires app-specific password |
| Tencent Exmail | `imap.exmail.qq.com` | Enterprise recommended |
| QQ Mail | `imap.qq.com` | Enable IMAP first |
| Outlook | `imap-mail.outlook.com` | Microsoft ecosystem |

## Advanced Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_HOST` | IMAP server | Required |
| `EMAIL_USER` | Email address | Required |
| `EMAIL_PASS` | App-specific password | Required |
| `EMAIL_SENDER` | Monitor sender | `email@advisor.cloud.tencent.com` |
| `EMAIL_HOURS` | Default lookback | `24` |

### Config File Location

```
config/email.env          # Environment variables
config/email_config.json  # JSON configuration
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Authentication failed | Use app-specific password, verify IMAP enabled |
| Attachments not saved | Check `data/attachments/` directory permissions |
| HTML parsing errors | Normal for complex emails, text extraction still works |
| No metrics extracted | Some reports are notification-only, check dashboard links |

For detailed troubleshooting, see [references/email_configuration.md](references/email_configuration.md).

## Integration Examples

### With OpenClaw Heartbeat

1. Add hook command to HEARTBEAT.md
2. Heartbeat runs periodically
3. If critical alerts found, OpenClaw receives notification
4. Agent can then generate full report or take action

### With Cron

```bash
# Daily report at 9 AM
0 9 * * * cd /path/to/skill && source config/email.env && python3 scripts/tencent_advisor_analyzer.py --output /path/to/reports/daily-$(date +\%Y\%m\%d).md

# Hourly heartbeat check
0 * * * * cd /path/to/skill && source config/email.env && python3 scripts/heartbeat_hook.py || echo "Alert detected"
```

## Architecture

```
Email → IMAP Fetch → Content Extraction (HTML/Attachments/Links)
                           ↓
                    Classification (Capacity/Inspection/Alert/Cost/Security)
                           ↓
                    Information Extraction (Metrics/Alerts/Recommendations)
                           ↓
                    Report Generation (Summary/Highlights/Actions/Links)
                           ↓
                    Output (Markdown/JSON/Heartbeat Alert)
```

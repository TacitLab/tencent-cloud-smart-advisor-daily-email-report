---
name: tencent-smart-advisor-daily-email-report
description: Generate daily email reports from Tencent Smart Advisor (email@advisor.cloud.tencent.com). Automatically reads emails from the last 24 hours, extracts key information, identifies important decisions and data changes, compares with previous day trends, and generates structured professional reports. Supports customizable check times (default 9 AM daily). Use when users need to (1) automate Tencent Smart Advisor email summarization and analysis, (2) track AI recommendations and technical decision trends, (3) intelligently monitor Tencent Cloud service-related emails.
---

# Tencent Smart Advisor Daily Email Report

Generate structured daily reports from Tencent Smart Advisor emails.

## Quick Start

### 1. Configure Email Connection

```bash
# Set environment variables
export EMAIL_HOST="imap.exmail.qq.com"
export EMAIL_USER="your-email@company.com"
export EMAIL_PASS="your-app-password"
export EMAIL_SENDER="email@advisor.cloud.tencent.com"
```

Or use the interactive setup:
```bash
python3 scripts/setup_email.py
```

### 2. Generate Daily Report

```bash
# Generate report for last 24 hours
python3 scripts/email_daily_report.py

# Specify time range
python3 scripts/email_daily_report.py --hours 48

# Save to file
python3 scripts/email_daily_report.py --output report.md
```

### 3. Set Up Scheduled Task

```bash
# Add to crontab - runs daily at 9 AM
0 9 * * * /usr/bin/python3 /path/to/scripts/email_daily_report.py
```

## Core Features

- **Smart Email Summarization**: Reads emails from the last 24 hours, deduplicates and clusters topics
- **Key Information Extraction**: Identifies core data points, decision items, and important changes
- **Trend Comparison**: Compares with previous day's data, identifies changes and patterns
- **Structured Report Output**: Generates executive summary with categorized information and actionable recommendations

## Output Format

The generated report includes:
- **Executive Summary**: Email count, important items, urgent matters
- **Trend Analysis**: Day-over-day changes, new topics
- **Detailed Content**: Important decisions, urgent items, data points by category
- **Action Recommendations**: Prioritized next steps

## Scripts Reference

- **`scripts/email_daily_report.py`**: Main script for generating daily reports
- **`scripts/trend_analyzer.py`**: Weekly trend analysis and insights
- **`scripts/setup_email.py`**: Interactive configuration wizard

## Email Configuration

For detailed email provider setup, authentication, and troubleshooting, see [references/email_configuration.md](references/email_configuration.md).

### Supported Providers

| Provider | IMAP Server | Notes |
|----------|-------------|-------|
| Tencent Exmail | `imap.exmail.qq.com` | Recommended for enterprise |
| QQ Mail | `imap.qq.com` | Enable IMAP first |
| Gmail | `imap.gmail.com` | Use app-specific password |
| Outlook | `imap-mail.outlook.com` | Microsoft ecosystem |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_HOST` | IMAP server address | `imap.exmail.qq.com` |
| `EMAIL_USER` | Email address | Required |
| `EMAIL_PASS` | App-specific password | Required |
| `EMAIL_SENDER` | Sender to monitor | `email@advisor.cloud.tencent.com` |
| `EMAIL_HOURS` | Lookback period | `24` |

## Usage Examples

### Basic Usage
User: "Generate yesterday's email report"
- Run email_daily_report.py
- Produce structured report with summary, trends, and recommendations

### Advanced Configuration
User: "Set up daily 8 AM check for advisor emails with trend analysis"
1. Run setup_email.py for interactive configuration
2. Set check time to 08:00
3. Configure specific sender filtering
4. Enable trend analysis
5. Set up cron job

### Weekly Trend Analysis
User: "Analyze this week's advisor email trends"
1. Load past 7 days of email data
2. Generate trend charts and comparisons
3. Identify important change patterns
4. Provide trend analysis and predictions

## Error Handling

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| Authentication failed | Check app-specific password, verify IMAP enabled |
| Connection timeout | Verify IMAP server address and port 993 |
| Parse errors | Check email encoding format |
| Permission denied | Ensure script has file read/write permissions |

For detailed troubleshooting, see [references/email_configuration.md](references/email_configuration.md).

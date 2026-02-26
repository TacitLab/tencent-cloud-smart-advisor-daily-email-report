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

## Report Output Format

When generating the final report, use **Markdown syntax** for all elements including headings, tables, blockquotes, code blocks, lists, and text formatting.

---

### 1. Headings (标题)

Use ATX-style headings with `#` symbols:

```markdown
# 一级标题 - 报告主标题
## 二级标题 - 主要章节
### 三级标题 - 小节
#### 四级标题 - 详细分类
##### 五级标题 - 可选细分
```

**Recommended Structure:**
```markdown
# 📊 腾讯云智能顾问日报 | YYYY-MM-DD

## 一、评估概览

### 账号维度统计

#### 高风险详情
```

---

### 2. Tables (表格)

| Element | Syntax | Example |
|---------|--------|---------|
| Header | `| Column 1 | Column 2 |` | `| 风险项 | 影响资源 |` |
| Separator | `| --- | --- |` | `| --- | --- | --- |` |
| Alignment | `|:---|:---:|---:|` | Left / Center / Right |
| Cell Content | `| data | data |` | `| 高风险 | 5个实例 |` |

**Example:**
```markdown
| 云产品 | 评估项 | 影响资源 | 风险描述 |
|--------|--------|----------|----------|
| EdgeOne | 访问鉴权签名冲突 | 4个域名 | 与COS源站冲突 |
| CVM | 磁盘使用率过高 | 1个实例 | 使用率>90% |
```

---

### 3. Blockquotes (引用)

Use `>` for highlighting important notes, tips, or warnings:

```markdown
> ⚠️ **风险提示**: 该风险已持续34天未处理，建议立即关注。

> 💡 **优化建议**: 建议在业务低峰期进行配置调整。

> 🔗 **参考文档**: [腾讯云文档中心](https://cloud.tencent.com/document)
```

---

### 4. Code Blocks (代码块)

Use fenced code blocks with language identifiers:

````markdown
```bash
# Shell command example
himalaya envelope list from:email@advisor.cloud.tencent.com
```

```json
{
  "account": "1312346585",
  "highRisk": 7,
  "mediumRisk": 13
}
```

```python
# Python snippet
import pandas as pd
df = pd.read_excel('report.xlsx')
```
````

**Inline code**: Use backticks for short code fragments like `himalaya` or `email@advisor.cloud.tencent.com`.

---

### 5. Lists (列表)

**Unordered Lists (无序列表):**
```markdown
- EdgeOne 安全风险
  - 访问鉴权签名冲突
  - 源站地址配置不合理
- CVM 性能问题
  - 磁盘使用率过高
  - 内存使用率过高
```

**Ordered Lists (有序列表):**
```markdown
1. 立即处理高风险项目
2. 优化中风险配置
3. 规划低成本改进
   1. 转包年包月
   2. 释放闲置资源
```

**Task Lists (任务列表):**
```markdown
- [x] 已处理：DDoS防护配置
- [ ] 待处理：签名冲突修复
- [ ] 计划中：HTTPS全面开启
```

---

### 6. Text Formatting (文本格式)

| Style | Syntax | Example |
|-------|--------|---------|
| Bold (粗体) | `**text**` | **高风险** |
| Italic (斜体) | `*text*` | *待确认* |
| Strikethrough (删除线) | `~~text~~` | ~~已过期~~ |
| Bold + Italic | `***text***` | ***紧急*** |

---

### 7. Links & Images (链接与图片)

```markdown
[控制台链接](https://console.cloud.tencent.com/advisor)
[产品文档](https://cloud.tencent.com/product/advisor "悬停提示")

![风险趋势图](https://example.com/chart.png "风险趋势")
```

---

### 8. Horizontal Rules (分隔线)

Use `---` or `***` to separate sections:

```markdown
---

## 下一章节
```

---

### 9. Complete Example (完整示例)

```markdown
# 📊 腾讯云智能顾问日报 | 2026-02-25

> 📅 报告生成时间: 2026-02-26 16:15 (UTC+8)  
> 📧 数据来源: 腾讯云智能顾问邮件订阅

---

## 一、评估概览

| 账号 | 评估时间 | 🔴 高风险 | 🟡 中风险 | ✅ 健康 | 总计 |
|------|----------|----------:|----------:|--------:|-----:|
| 账号A | 14:20:52 | 7 | 13 | 104 | 124 |
| 账号B | 16:23:08 | 27 | 65 | 287 | 379 |
| **合计** | - | **34** | **78** | **391** | **503** |

---

## 二、高风险项目 🔴

> ⚠️ **以下项目需立即处理，已持续超过15天未解决！**

### 1. EdgeOne 安全风险

| 评估项 | 影响资源 | 风险描述 | 持续天数 |
|--------|----------|----------|----------|
| 站点未配置自定义DDoS防护 | `zone-34xkcnw3pdoq` | 默认策略无法满足防护需求 | **34天** |
| 访问鉴权签名冲突 | 4个域名 | 与COS源站冲突 | 17天 |

**影响域名清单:**
- `lb.isa-test.com`
- `cos-auth-test.isa-test.com`
- `cos-auth-test2.isa-test.com`
- `soc-sign-test.isa-test.com`

**建议命令:**
```bash
# 检查域名配置
tencentcloud-cli edgeone describe-domain-config --domain lb.isa-test.com
```

---

## 三、待办事项

### 🔴 P0 - 立即处理（安全风险）

- [ ] **EdgeOne**: 配置DDoS自定义防护策略 - `isa-test.com` 站点
- [ ] **EdgeOne**: 修复访问鉴权签名冲突 - 4个COS相关域名

### 🟡 P1 - 本周处理（成本/性能）

- [ ] **CVM**: 2台实例转为包年包月（已按量计费**120天**）
- [ ] **EdgeOne**: 开启HTTPS - 27个域名

### 🟢 P2 - 计划优化

- [ ] 升级TLS版本 - 禁用TLS1.0/1.1
- [ ] 开启主机/数据库安全防护

---

## 四、控制台快捷链接

| 产品 | 控制台 | 文档 |
|------|--------|------|
| 智能顾问 | [控制台](https://console.cloud.tencent.com/advisor) | [文档](https://cloud.tencent.com/product/advisor) |
| EdgeOne | [控制台](https://console.cloud.tencent.com/edgeone) | [文档](https://cloud.tencent.com/document/product/1552) |
| CVM | [控制台](https://console.cloud.tencent.com/cvm) | [文档](https://cloud.tencent.com/document/product/213) |
```

---

### 10. Platform Considerations (平台适配)

根据对话环境自动选择输出格式：

#### 平台检测
通过系统提示中的 `channel` 参数判断当前平台：
- `channel=telegram` → 使用列表格式
- `channel=discord` → 可使用标准Markdown表格
- `channel=whatsapp` → 使用纯文本列表格式
- `channel=web` → 可使用标准Markdown表格

#### 格式适配规则

**Telegram / WhatsApp (不支持表格):**
```markdown
**账号1** - 深圳市腾讯计算机系统有限公司
评估时间: 14:20:52
🔴 高风险: 7 | 🟡 中风险: 13 | ✅ 健康: 104

**高风险项目:**
• EdgeOne DDoS防护未配置 - 34天
• CVM 磁盘使用率过高 - 12天
```

**Discord / Web / 其他 (支持表格):**
```markdown
| 账号 | 评估时间 | 🔴 高风险 | 🟡 中风险 | ✅ 健康 |
|------|----------|----------:|----------:|--------:|
| 账号1 | 14:20:52 | 7 | 13 | 104 |
```

**Discord:**
- ✅ 支持所有Markdown语法
- ⚠️ 避免过宽的表格（>80字符会换行）
- 💡 使用 `<https://url>` 隐藏长链接预览

**Telegram:**
- ✅ 基础Markdown支持良好
- ❌ **不支持表格语法** - 必须使用列表格式
- 💡 使用 **粗体** 代替标题强调

**WhatsApp:**
- ❌ 不支持表格，必须使用列表形式
- ✅ 支持 `*粗体*` 和 `_斜体_`
- 💡 使用 emoji 和换行增强可读性

### 11. Formatting Tips

1. **Risk Indicators**: Use emoji for quick visual scanning
   - 🔴 高风险 / Critical
   - 🟡 中风险 / Warning
   - 🟢 低风险 / Info
   - ✅ 健康 / Healthy

2. **Numeric Alignment**: Right-align numbers for easier comparison
   ```markdown
   | 资源数 | 风险天数 |
   |-------:|---------:|
   |     42 |       17 |
   |      5 |        3 |
   ```

3. **Multi-line Cells**: Use `<br>` for line breaks within cells
   ```markdown
   | 描述 |
   |------|
   | 第一行<br>第二行 |
   ```

4. **Lists in Tables**: Use comma separation or numbered items
   ```markdown
   | 影响资源 |
   |----------|
   | 1. lb.isa-test.com<br>2. test.isa-test.com |
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

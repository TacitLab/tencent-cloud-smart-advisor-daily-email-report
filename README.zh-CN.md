# 腾讯云智能顾问日报生成器

[![GitHub](https://img.shields.io/github/license/TacitLab/tencent-smart-advisor-daily-email-report)](LICENSE)

OpenClaw Skill，用于从腾讯云智能顾问邮件生成智能日报。

## 功能特性

- **多账号/架构图分组** — 按 APPID 和架构图组织报告
- **本地缓存与去重** — 邮件存储在 `~/.advisor`，通过 message-id 自动去重
- **周期对比** — 对比当前报告与上期数据，追踪趋势变化
- **纯 Shell 实现** — 无 Python 依赖，使用现有 OpenClaw skills
- **自动账号名称映射** — 自动从邮件提取并映射账号名称

## 快速开始

```bash
# 安装所需 skills
openclaw skills install himalaya
openclaw skills install summarize

# 生成今日报告
./scripts/advisor-report.sh --today

# 生成带周期对比的报告
./scripts/advisor-report.sh --today --compare

# 生成指定账号的报告
./scripts/advisor-report.sh --appid 1234567890 --today
```

## 依赖项

- `himalaya` — 邮件获取（OpenClaw skill）
- `summarize` — Excel 内容提取（OpenClaw skill）
- `jq` — JSON 处理
- `bash` — 脚本执行

## 缓存结构

```
~/.advisor/
├── index.json              # 邮件去重索引
├── accounts.json           # 账号名称映射
├── reports/                # 生成的报告
│   └── 1234567890/        # APPID
│       └── 2026-02-25/    # 日期
│           └── arch-name/ # 架构图
└── raw/                    # 缓存的邮件
```

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `advisor-report.sh` | 主入口 — 同步邮件并生成报告 |
| `advisor-sync.sh` | 邮件同步与缓存管理 |
| `generate-report.sh` | 生成单账号/架构报告 |
| `daily-summary.sh` | 聚合生成日报汇总 |
| `advisor-compare.sh` | 周期对比工具 |

## 报告示例

```markdown
# 📊 腾讯云智能顾问日报 | 2026-02-25

## 账号: 示例公司 (1234567890)

### 架构图: production-arch

**报告类型**: 🔴 架构风险治理报告

#### 风险评估汇总

| 级别 | 数量 |
|------|-----:|
| 🔴 高风险 | 7 |
| 🟡 中风险 | 13 |
| ✅ 健康 | 104 |

#### 高风险详情

1. **CVM — 磁盘使用率过高**
   - 类别: 性能
   - 建议: 扩容云硬盘或清理磁盘内容
```

## 配置说明

### 账号名称映射

系统会自动从邮件中提取账号名称。如需手动覆盖：

```bash
# 编辑 ~/.advisor/accounts.json
{
  "1234567890": "您的公司名称",
  "other-appid": "另一个账号"
}
```

## 文档

- [English Documentation](README.md)
- [SKILL.md](SKILL.md) — 详细技术文档

## 许可证

MIT

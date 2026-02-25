# 腾讯智能顾问邮件日报系统 - 快速开始

## 🚀 安装和配置

### 1. 基础配置
```bash
# 克隆或复制skill到OpenClaw工作目录
cd /path/to/openclaw/workspace

# 进入skill目录
cd email-daily-report

# 运行配置向导
python3 scripts/setup_email.py
```

### 2. 手动配置（可选）
如果自动配置失败，可以手动设置环境变量：

```bash
# 创建配置文件
mkdir -p config
cat > config/email.env << 'EOF'
export EMAIL_HOST="imap.exmail.qq.com"
export EMAIL_USER="your-email@company.com"
export EMAIL_PASS="your-app-password"
export EMAIL_SENDER="email@advisor.cloud.tencent.com"
export EMAIL_HOURS="24"
EOF

# 加载配置
source config/email.env
```

### 3. 测试运行
```bash
# 测试基础功能
python3 scripts/email_daily_report.py --hours 24 --verbose

# 保存报告到文件
python3 scripts/email_daily_report.py --output /tmp/daily_report.md

# 指定不同时间范围
python3 scripts/email_daily_report.py --hours 48
```

## 📅 设置定时任务

### 使用crontab（Linux/Mac）
```bash
# 编辑crontab
crontab -e

# 添加以下行（每天早上9点执行）
0 9 * * * cd /path/to/email-daily-report && /usr/bin/python3 scripts/email_daily_report.py >> /var/log/email-report.log 2>&1

# 查看cron任务
crontab -l
```

### 使用systemd定时器（高级）
创建服务文件 `/etc/systemd/system/email-report.service`：
```ini
[Unit]
Description=Email Daily Report
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/path/to/email-daily-report
ExecStart=/usr/bin/python3 scripts/email_daily_report.py
EnvironmentFile=/path/to/email-daily-report/config/email.env

[Install]
WantedBy=multi-user.target
```

创建定时器文件 `/etc/systemd/system/email-report.timer`：
```ini
[Unit]
Description=Run Email Report Daily
Requires=email-report.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

启用并启动定时器：
```bash
sudo systemctl enable email-report.timer
sudo systemctl start email-report.timer
sudo systemctl status email-report.timer
```

## 📊 使用示例

### 基础使用
```python
from scripts.email_daily_report import EmailDailyReport

# 创建报告生成器
reporter = EmailDailyReport()

# 生成24小时报告
report = reporter.run(hours=24)
print(report)
```

### 高级配置
```python
# 自定义配置
import os
os.environ['EMAIL_HOST'] = 'imap.gmail.com'
os.environ['EMAIL_USER'] = 'user@gmail.com'
os.environ['EMAIL_SENDER'] = 'advisor@company.com'

# 生成报告
reporter = EmailDailyReport()
report = reporter.run(hours=48, sender='specific@sender.com')
```

## 🔧 故障排除

### 连接问题
```bash
# 测试邮箱连接
python3 -c "
import os
os.environ['EMAIL_HOST'] = 'your-host'
os.environ['EMAIL_USER'] = 'your-user'
os.environ['EMAIL_PASS'] = 'your-pass'

from scripts.email_daily_report import EmailDailyReport
reporter = EmailDailyReport()
print('连接测试...')
# 这里会尝试连接并报告结果
"
```

### 日志查看
```bash
# 查看详细日志
tail -f /var/log/email-report.log

# 查看最近报告
ls -la /tmp/daily_report*.md
cat /tmp/daily_report_latest.md
```

### 常见问题
1. **认证失败**: 检查应用专用密码设置
2. **连接超时**: 确认IMAP服务器地址
3. **无邮件**: 检查发件人地址是否正确
4. **权限错误**: 确保脚本有执行权限

## 📈 趋势分析

### 生成趋势报告
```bash
# 生成周趋势分析
python3 scripts/trend_analyzer.py

# 查看历史数据
ls -la data/
cat data/email_history.json
```

### 数据可视化（高级）
可以集成matplotlib生成图表：
```python
from scripts.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer('data/')
trends = analyzer.analyze_weekly_trends(current_data)
# 生成包含图表的报告
```

## 🔗 集成建议

### 与Slack集成
```bash
# 发送报告到Slack
python3 scripts/email_daily_report.py | slack-cli send --channel="#daily-reports"
```

### 与邮件系统集成
```bash
# 自动发送报告邮件
python3 scripts/email_daily_report.py | mail -s "Daily Email Report" manager@company.com
```

### 与日历集成
可以自动创建日历提醒来处理重要邮件事项。

## 🚀 高级功能

### 多邮箱监控
可以同时监控多个发件人的邮件：
```bash
# 监控多个发件人
for sender in "sender1@company.com" "sender2@company.com"; do
    python3 scripts/email_daily_report.py --sender "$sender" --output "/tmp/report_${sender}.md"
done
```

### 智能分类
基于机器学习的高级分类（需要额外配置）：
```python
# 启用智能分类
reporter.enable_smart_classification()
report = reporter.run()
```

### 自定义模板
可以自定义报告模板格式：
```python
# 加载自定义模板
reporter.load_template('templates/custom_template.md')
report = reporter.run()
```

## 📞 支持

如有问题：
1. 查看详细日志：`--verbose` 参数
2. 检查配置文件和环境变量
3. 验证邮箱连接和网络设置
4. 参考 `references/email_configuration.md` 中的故障排除指南

---
*邮件日报系统 - 让邮件管理更智能*
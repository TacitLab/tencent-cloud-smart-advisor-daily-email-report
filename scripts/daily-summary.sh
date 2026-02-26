#!/bin/bash
#
# daily-summary.sh - Aggregate all reports into a single daily summary
# Usage: ./daily-summary.sh --date YYYY-MM-DD [--cache-dir PATH]
#

set -e

DATE=""
CACHE_DIR="${HOME}/.advisor"
OUTPUT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --date) DATE="$2"; shift 2 ;;
    --cache-dir) CACHE_DIR="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --date YYYY-MM-DD    Report date (default: today)"
      echo "  --cache-dir PATH     Cache directory (default: ~/.advisor)"
      echo "  --output PATH        Output file path"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

[[ -z "$DATE" ]] && DATE=$(date +%Y-%m-%d)

echo "📊 Generating daily summary for ${DATE}..."

REPORTS_DIR="${CACHE_DIR}/reports"
[[ ! -d "$REPORTS_DIR" ]] && { echo "  ⚠️ No reports directory"; exit 0; }

# Count reports for this date
REPORT_COUNT=$(find "$REPORTS_DIR" -path "*/${DATE}/*/report.markdown" 2>/dev/null | wc -l)
echo "  📂 Found ${REPORT_COUNT} report(s)"

if [[ $REPORT_COUNT -eq 0 ]]; then
  echo "  ⚠️ No reports found for ${DATE}"
  exit 0
fi

# Generate summary markdown
{
  echo "# 📊 腾讯云智能顾问日报 | ${DATE}"
  echo ""
  echo "> 📅 报告生成时间: $(date '+%Y-%m-%d %H:%M') (UTC+8)"
  echo "> 📧 数据来源: 腾讯云智能顾问邮件订阅"
  echo ""
  echo "---"
  echo ""
  
  # Aggregate summary
  echo "## 一、总体概览"
  echo ""
  echo "| 统计项 | 数量 |"
  echo "|--------|-----:|"
  echo "| 🔴 高风险总数 | - |"
  echo "| 🟡 中风险总数 | - |"
  echo "| 🟢 低风险总数 | - |"
  echo "| ✅ 健康资源 | - |"
  echo ""
  echo "---"
  echo ""
  
  # Per-account summary
  echo "## 二、账号维度统计"
  echo ""
  
  # Find all accounts with reports for this date
  for ACCOUNT_DIR in "$REPORTS_DIR"/*; do
    [[ -d "$ACCOUNT_DIR" ]] || continue
    APPID=$(basename "$ACCOUNT_DIR")
    
    # Find architectures
    DATE_DIR="${ACCOUNT_DIR}/${DATE}"
    [[ -d "$DATE_DIR" ]] || continue
    
    for ARCH_DIR in "$DATE_DIR"/*; do
      [[ -d "$ARCH_DIR" ]] || continue
      ARCH=$(basename "$ARCH_DIR")
      
      # Get account name
      ACCOUNT_NAME="$APPID"
      if [[ -f "${CACHE_DIR}/accounts.json" ]]; then
        MAPPED=$(jq -r ".[\"${APPID}\"] // empty" "${CACHE_DIR}/accounts.json" 2>/dev/null)
        [[ -n "$MAPPED" ]] && ACCOUNT_NAME="$MAPPED"
      fi
      
      echo "### ${ACCOUNT_NAME} (${APPID})"
      echo ""
      [[ "$ARCH" != "default" ]] && echo "**架构图**: ${ARCH}"
      echo ""
      
      # Include the report content if exists
      if [[ -f "${ARCH_DIR}/report.markdown" ]]; then
        cat "${ARCH_DIR}/report.markdown"
        echo ""
        echo "---"
        echo ""
      fi
    done
  done
  
  # Action items
  echo "## 三、待办事项汇总"
  echo ""
  echo "### 🔴 P0 - 立即处理（安全风险）"
  echo ""
  echo "- [ ] 审查所有高风险项目"
  echo ""
  echo "### 🟡 P1 - 本周处理（成本/性能优化）"
  echo ""
  echo "- [ ] 优化中风险配置项"
  echo ""
  echo "### 🟢 P2 - 计划内优化"
  echo ""
  echo "- [ ] 持续关注健康资源趋势"
  echo ""
  echo "---"
  echo ""
  
  # Links
  echo "## 四、控制台快捷链接"
  echo ""
  echo "| 产品 | 控制台 | 文档 |"
  echo "|------|--------|------|"
  echo "| 智能顾问 | [控制台](https://console.cloud.tencent.com/advisor) | [文档](https://cloud.tencent.com/product/advisor) |"
  echo "| EdgeOne | [控制台](https://console.cloud.tencent.com/edgeone) | [文档](https://cloud.tencent.com/document/product/1552) |"
  echo "| CVM | [控制台](https://console.cloud.tencent.com/cvm) | [文档](https://cloud.tencent.com/document/product/213) |"
  echo ""
  
} > "${OUTPUT:-${REPORTS_DIR}/daily-summary-${DATE}.md}"

echo "✅ Summary saved to ${OUTPUT:-${REPORTS_DIR}/daily-summary-${DATE}.md}"
exit 0

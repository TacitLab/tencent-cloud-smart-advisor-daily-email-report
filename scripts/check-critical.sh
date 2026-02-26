#!/bin/bash
#
# Tencent Smart Advisor Critical Alert Checker
# Returns non-zero exit code if critical alerts are found
# For use in HEARTBEAT.md periodic checks
#

set -euo pipefail

SENDER="email@advisor.cloud.tencent.com"
HOURS=${1:-6}  # Default: check last 6 hours

# Check for critical/risk/alert emails
check_critical() {
    local since_date
    since_date=$(date -u -d "$HOURS hours ago" +%Y-%m-%d 2>/dev/null || date -v-${HOURS}H +%Y-%m-%d)
    
    # Check if himalaya is available
    if ! command -v himalaya &> /dev/null; then
        echo "HEARTBEAT_OK (himalaya not installed)"
        exit 0
    fi
    
    # Search for emails with critical keywords in subject
    local critical_emails
    critical_emails=$(himalaya envelope list \
        from:"$SENDER" \
        since:"$since_date" \
        subject:"告警\|风险\|critical\|urgent" \
        --output json 2>/dev/null | jq -c '.[]' || true)
    
    if [ -z "$critical_emails" ]; then
        echo "HEARTBEAT_OK"
        exit 0
    fi
    
    # Count critical items
    local count
    count=$(echo "$critical_emails" | jq -s 'length')
    
    if [ "$count" -eq 0 ]; then
        echo "HEARTBEAT_OK"
        exit 0
    fi
    
    # Output alert notification as JSON
    echo "$critical_emails" | jq -s '{
        type: "tencent_advisor_alert",
        timestamp: now | todate,
        summary: "检测到 \(. | length) 项需要关注的腾讯云智能顾问通知",
        count: (. | length),
        items: [.[] | {
            id: .id,
            subject: .subject,
            date: .date
        }]
    }'
    
    # Return non-zero to indicate alert condition
    exit 1
}

check_critical "$@"

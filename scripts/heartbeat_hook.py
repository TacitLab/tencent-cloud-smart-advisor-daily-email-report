#!/usr/bin/env python3
"""
Heartbeat Hook for Tencent Smart Advisor
Runs periodically to check for new emails and notify if important items found.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tencent_advisor_analyzer import TencentAdvisorAnalyzer
import json
from datetime import datetime

def heartbeat_check():
    """Run as heartbeat hook - check for critical/high importance emails"""
    analyzer = TencentAdvisorAnalyzer()
    
    # Only check last 1 hour for heartbeat
    analyzer.hours_back = 1
    
    # Fetch and analyze
    emails = analyzer.fetch_emails()
    
    if not emails:
        return None  # No action needed
    
    # Check for critical or high importance items
    critical_items = []
    high_items = []
    
    for email in emails:
        importance = email.get('importance', 'normal')
        if importance == 'critical':
            critical_items.append(email)
        elif importance == 'high':
            high_items.append(email)
    
    # Generate notification if important items found
    if critical_items or high_items:
        notification = {
            'type': 'tencent_advisor_alert',
            'timestamp': datetime.now().isoformat(),
            'summary': f"检测到 {len(critical_items)} 项紧急, {len(high_items)} 项重要",
            'critical_count': len(critical_items),
            'high_count': len(high_items),
            'items': []
        }
        
        for item in critical_items + high_items:
            notification['items'].append({
                'subject': item['subject'],
                'type': item.get('type', 'unknown'),
                'importance': item.get('importance'),
                'summary': item.get('key_info', {}).get('summary', ''),
                'time': item.get('date', '')
            })
        
        return notification
    
    return None

if __name__ == '__main__':
    result = heartbeat_check()
    if result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)  # Exit with error code to trigger notification
    else:
        print("HEARTBEAT_OK")
        sys.exit(0)

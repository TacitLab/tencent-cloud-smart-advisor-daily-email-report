#!/usr/bin/env python3
"""
Email Daily Report Generator
Automatically reads emails from specified sender, summarizes 24-hour information,
extracts key content and compares with previous day's changes.
"""

import imaplib
import email
import json
import os
import re
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailDailyReport:
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST', 'imap.exmail.qq.com')
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_pass = os.getenv('EMAIL_PASS', '')
        self.target_sender = os.getenv('EMAIL_SENDER', 'email@advisor.cloud.tencent.com')
        self.hours_back = int(os.getenv('EMAIL_HOURS', '24'))
        
        # Data storage
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, 'email_history.json')
        
        logger.info(f"Initializing email daily report system - Monitoring sender: {self.target_sender}")
    
    def connect_to_mailbox(self) -> imaplib.IMAP4_SSL:
        """Connect to mailbox"""
        try:
            mail = imaplib.IMAP4_SSL(self.email_host)
            mail.login(self.email_user, self.email_pass)
            mail.select('INBOX')
            logger.info("Successfully connected to mailbox")
            return mail
        except Exception as e:
            logger.error(f"Mailbox connection failed: {e}")
            raise
    
    def search_emails_from_sender(self, mail: imaplib.IMAP4_SSL, since_date: datetime) -> List[str]:
        """Search emails from specified sender within time range"""
        try:
            since_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f'(FROM "{self.target_sender}" SINCE "{since_str}")'
            
            logger.info(f"Search criteria: {search_criteria}")
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("No emails found")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} emails")
            return email_ids
            
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return []
    
    def parse_email(self, mail: imaplib.IMAP4_SSL, email_id: str) -> Dict:
        """Parse single email"""
        try:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            subject = self.decode_mime_words(email_message.get('Subject', ''))
            from_addr = email_message.get('From', '')
            date_str = email_message.get('Date', '')
            
            try:
                email_date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except:
                email_date = datetime.now()
            
            body = self.extract_email_body(email_message)
            
            return {
                'id': email_id.decode(),
                'subject': subject,
                'from': from_addr,
                'date': email_date.isoformat(),
                'body': body,
                'size': len(raw_email),
                'importance': self.assess_importance(subject, body)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse email {email_id}: {e}")
            return None
    
    def decode_mime_words(self, text: str) -> str:
        """Decode MIME encoded text"""
        decoded_parts = []
        for part, encoding in decode_header(text):
            if isinstance(part, bytes):
                if encoding:
                    decoded_parts.append(part.decode(encoding))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(part)
        return ''.join(decoded_parts)
    
    def extract_email_body(self, email_message) -> str:
        """Extract email body"""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html":
                    try:
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        text_content = re.sub(r'<[^>]+>', '', html_content)
                        body += text_content
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        
        return body.strip()
    
    def assess_importance(self, subject: str, body: str) -> str:
        """Assess email importance"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        high_importance_words = ['urgent', 'important', 'decision', 'critical', 'immediate', 'asap', 
                                'budget', 'strategy', 'roadmap', 'emergency', 'high priority']
        
        medium_importance_words = ['update', 'meeting', 'review', 'report', 'analysis', 'plan']
        
        high_count = sum(1 for word in high_importance_words if word in subject_lower or word in body_lower)
        medium_count = sum(1 for word in medium_importance_words if word in subject_lower or word in body_lower)
        
        if high_count >= 2:
            return 'high'
        elif high_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def categorize_emails(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize emails"""
        categories = {
            'decisions': [],
            'updates': [],
            'alerts': [],
            'general': []
        }
        
        for email in emails:
            subject_lower = email['subject'].lower()
            body_lower = email['body'].lower()
            
            decision_keywords = ['decision', 'decide', 'approve', 'approval', 'budget', 'strategy', 'roadmap']
            if any(keyword in subject_lower or keyword in body_lower for keyword in decision_keywords):
                categories['decisions'].append(email)
                continue
            
            alert_keywords = ['alert', 'warning', 'error', 'failure', 'urgent', 'emergency', 'critical']
            if any(keyword in subject_lower or keyword in body_lower for keyword in alert_keywords):
                categories['alerts'].append(email)
                continue
            
            update_keywords = ['update', 'progress', 'status', 'report', 'summary', 'review']
            if any(keyword in subject_lower or keyword in body_lower for keyword in update_keywords):
                categories['updates'].append(email)
                continue
            
            categories['general'].append(email)
        
        return categories
    
    def extract_key_data(self, emails: List[Dict]) -> Dict:
        """Extract key data points"""
        key_data = {
            'total_emails': len(emails),
            'by_importance': {'high': 0, 'medium': 0, 'low': 0},
            'by_category': {'decisions': 0, 'updates': 0, 'alerts': 0, 'general': 0},
            'key_decisions': [],
            'urgent_items': [],
            'data_points': []
        }
        
        for email in emails:
            key_data['by_importance'][email['importance']] += 1
            
            if 'decision' in email['subject'].lower() or 'decide' in email['body'].lower():
                decision_info = self.extract_decision_info(email)
                if decision_info:
                    key_data['key_decisions'].append(decision_info)
            
            if email['importance'] == 'high':
                key_data['urgent_items'].append({
                    'subject': email['subject'],
                    'summary': email['body'][:200] + '...' if len(email['body']) > 200 else email['body']
                })
            
            data_points = self.extract_data_points(email['body'])
            key_data['data_points'].extend(data_points)
        
        return key_data
    
    def extract_decision_info(self, email: Dict) -> Optional[Dict]:
        """Extract decision information"""
        body = email['body'].lower()
        
        decision_patterns = [
            r'decision.*?(?:on|for|about).*?(?=\n|$)',
            r'approve.*?(?=\n|$)',
            r'budget.*?(?:increase|decrease|adjust)',
            r'strategy.*?(?:change|update|modify)'
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                return {
                    'subject': email['subject'],
                    'decision': matches[0],
                    'date': email['date']
                }
        
        return None
    
    def extract_data_points(self, text: str) -> List[Dict]:
        """Extract data points (numbers, percentages)"""
        data_points = []
        
        percent_matches = re.findall(r'(\d+(?:\.\d+)?)%', text)
        for match in percent_matches:
            data_points.append({
                'type': 'percentage',
                'value': float(match),
                'context': self.find_context(text, match + '%')
            })
        
        number_matches = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', text)
        for match in number_matches:
            if len(match) > 3 and not match.startswith('0'):
                try:
                    value = float(match.replace(',', ''))
                    if value > 100:
                        data_points.append({
                            'type': 'number',
                            'value': value,
                            'context': self.find_context(text, match)
                        })
                except:
                    pass
        
        return data_points
    
    def find_context(self, text: str, target: str, context_size: int = 50) -> str:
        """Find context around target text"""
        index = text.find(target)
        if index == -1:
            return ""
        
        start = max(0, index - context_size)
        end = min(len(text), index + len(target) + context_size)
        return text[start:end].strip()
    
    def compare_with_history(self, current_data: Dict) -> Dict:
        """Compare with historical data"""
        comparison = {
            'email_count_change': 0,
            'new_topics': [],
            'trending_keywords': [],
            'significant_changes': []
        }
        
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if 'total_emails' in history:
                    comparison['email_count_change'] = current_data['total_emails'] - history['total_emails']
                    
            except Exception as e:
                logger.error(f"History comparison failed: {e}")
        
        self.save_history(current_data)
        return comparison
    
    def save_history(self, data: Dict):
        """Save historical data"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("History data saved")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def generate_report(self, emails: List[Dict], key_data: Dict, comparison: Dict) -> str:
        """Generate daily report"""
        if not emails:
            return "# Email Daily Report\n\nNo emails from specified sender today.\n"
        
        categories = self.categorize_emails(emails)
        
        report = f"""# Email Daily Report - {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
- New emails: {key_data['total_emails']}"""
        
        if comparison['email_count_change'] != 0:
            change_symbol = "↑" if comparison['email_count_change'] > 0 else "↓"
            report += f" ({change_symbol} {abs(comparison['email_count_change'])} vs yesterday)"
        
        report += f"""
- Important emails: {key_data['by_importance']['high']} (with key decisions)
- Urgent items: {len(key_data['urgent_items'])} (require immediate attention)

## Trend Analysis"""
        
        if comparison['email_count_change'] != 0:
            trend = "increased" if comparison['email_count_change'] > 0 else "decreased"
            report += f"\n- Email volume: {trend} {abs(comparison['email_count_change'])} vs yesterday"
        
        report += f"""
- High importance: {key_data['by_importance']['high']}
- Medium importance: {key_data['by_importance']['medium']}  
- Low importance: {key_data['by_importance']['low']}

## Detailed Content

### Important Decisions"""
        
        if key_data['key_decisions']:
            for i, decision in enumerate(key_data['key_decisions'], 1):
                report += f"\n{i}. **{decision['subject']}** - {decision['decision'][:100]}..."
        else:
            report += "\nNo explicit decision emails today."
        
        report += f"""

### Urgent Items"""
        
        if key_data['urgent_items']:
            for item in key_data['urgent_items']:
                report += f"\n- **{item['subject']}** - {item['summary'][:150]}..."
        else:
            report += "\nNo urgent items today."
        
        report += f"""

### Category Statistics
- Decisions: {len(categories['decisions'])}
- Updates: {len(categories['updates'])}  
- Alerts: {len(categories['alerts'])}
- General: {len(categories['general'])}

### Data Highlights"""
        
        if key_data['data_points']:
            for i, data_point in enumerate(key_data['data_points'][:5], 1):
                report += f"\n{i}. {data_point['value']} {data_point['type']} - {data_point['context'][:80]}..."
        else:
            report += "\nNo significant data points found today."
        
        report += f"""

## Action Recommendations
Based on today's email analysis:"""
        
        recommendations = []
        if key_data['by_importance']['high'] > 0:
            recommendations.append("**High Priority**: Address high-importance emails")
        if len(key_data['key_decisions']) > 0:
            recommendations.append("**Follow-up**: Monitor decision items from emails")
        if len(key_data['urgent_items']) > 0:
            recommendations.append("**Urgent**: Prioritize urgent email items")
        if comparison['email_count_change'] > 5:
            recommendations.append("**Volume Spike**: Email volume significantly increased, optimize email management")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"\n{i}. {rec}"
        else:
            report += "\nEmails are routine today, process normally."
        
        report += "\n"
        return report
    
    def run(self, hours: int = 24, sender: str = None) -> str:
        """Run complete daily report generation"""
        try:
            logger.info(f"Starting email daily report - Time range: {hours} hours")
            
            if sender:
                self.target_sender = sender
            
            since_date = datetime.now() - timedelta(hours=hours)
            mail = self.connect_to_mailbox()
            email_ids = self.search_emails_from_sender(mail, since_date)
            
            if not email_ids:
                logger.info("No matching emails found")
                mail.logout()
                return self.generate_report([], {}, {})
            
            emails = []
            for email_id in email_ids:
                email_data = self.parse_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.logout()
            logger.info(f"Successfully parsed {len(emails)} emails")
            
            key_data = self.extract_key_data(emails)
            comparison = self.compare_with_history(key_data)
            report = self.generate_report(emails, key_data, comparison)
            
            logger.info("Email daily report generation completed")
            return report
            
        except Exception as e:
            logger.error(f"Daily report generation failed: {e}")
            return f"# Email Daily Report Failed\n\nError: {str(e)}\n\nPlease check email configuration and network connection."

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Email Daily Report Generator')
    parser.add_argument('--hours', type=int, default=24, help='Time range in hours')
    parser.add_argument('--sender', type=str, help='Specify sender (override environment variable)')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    reporter = EmailDailyReport()
    report = reporter.run(hours=args.hours, sender=args.sender)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")
    else:
        print(report)

if __name__ == '__main__':
    main()

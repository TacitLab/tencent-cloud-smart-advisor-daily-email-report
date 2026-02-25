#!/usr/bin/env python3
"""
邮件日报自动生成脚本
自动读取指定邮箱的邮件，汇总24小时内信息，提炼关键内容并对比前一天变化
"""

import imaplib
import email
import json
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
import argparse
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailDailyReport:
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST', 'imap.exmail.qq.com')
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_pass = os.getenv('EMAIL_PASS', '')
        self.target_sender = os.getenv('EMAIL_SENDER', 'email@advisor.cloud.tencent.com')  # 默认腾讯智能顾问邮箱
        self.hours_back = int(os.getenv('EMAIL_HOURS', '24'))
        
        # 数据存储
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, 'email_history.json')
        
        logger.info(f"初始化邮件日报系统 - 监控发件人: {self.target_sender}")
    
    def connect_to_mailbox(self) -> imaplib.IMAP4_SSL:
        """连接到邮箱"""
        try:
            mail = imaplib.IMAP4_SSL(self.email_host)
            mail.login(self.email_user, self.email_pass)
            mail.select('INBOX')
            logger.info("成功连接到邮箱")
            return mail
        except Exception as e:
            logger.error(f"邮箱连接失败: {e}")
            raise
    
    def search_emails_from_sender(self, mail: imaplib.IMAP4_SSL, since_date: datetime) -> List[str]:
        """搜索指定发件人在时间范围内的邮件"""
        try:
            # 构建搜索条件
            since_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f'(FROM "{self.target_sender}" SINCE "{since_str}")'
            
            logger.info(f"搜索条件: {search_criteria}")
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("未找到邮件")
                return []
            
            email_ids = messages[0].split()
            logger.info(f"找到 {len(email_ids)} 封邮件")
            return email_ids
            
        except Exception as e:
            logger.error(f"搜索邮件失败: {e}")
            return []
    
    def parse_email(self, mail: imaplib.IMAP4_SSL, email_id: str) -> Dict:
        """解析单封邮件"""
        try:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # 提取基本信息
            subject = self.decode_mime_words(email_message.get('Subject', ''))
            from_addr = email_message.get('From', '')
            date_str = email_message.get('Date', '')
            
            # 解析日期
            try:
                email_date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except:
                email_date = datetime.now()
            
            # 提取正文
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
            logger.error(f"解析邮件 {email_id} 失败: {e}")
            return None
    
    def decode_mime_words(self, text: str) -> str:
        """解码MIME编码的文本"""
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
        """提取邮件正文"""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html":
                    # 简单处理HTML，提取文本
                    try:
                        html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        # 简单的HTML标签移除
                        text_content = re.sub(r'<[^>]+>', '', html_content)
                        body += text_content
                    except:
                        pass
        else:
            # 单部分邮件
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass
        
        return body.strip()
    
    def assess_importance(self, subject: str, body: str) -> str:
        """评估邮件重要性"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        # 高重要性关键词
        high_importance_words = ['urgent', '紧急', 'important', '重要', 'decision', '决策', 
                                'critical', '关键', 'immediate', '立即', 'asap', 'budget',
                                '预算', 'strategy', '战略', 'roadmap', '路线图']
        
        # 中重要性关键词
        medium_importance_words = ['update', '更新', 'meeting', '会议', 'review', '审核',
                                  'report', '报告', 'analysis', '分析', 'plan', '计划']
        
        high_count = sum(1 for word in high_importance_words if word in subject_lower or word in body_lower)
        medium_count = sum(1 for word in medium_importance_words if word in subject_lower or word in body_lower)
        
        if high_count >= 2:
            return 'high'
        elif high_count >= 1 or medium_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def categorize_emails(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """邮件分类"""
        categories = {
            'decisions': [],
            'updates': [],
            'alerts': [],
            'general': []
        }
        
        for email in emails:
            subject_lower = email['subject'].lower()
            body_lower = email['body'].lower()
            
            # 决策类邮件
            decision_keywords = ['decision', 'decide', 'approve', 'approval', 'budget', 'strategy', 'roadmap']
            if any(keyword in subject_lower or keyword in body_lower for keyword in decision_keywords):
                categories['decisions'].append(email)
                continue
            
            # 警报类邮件
            alert_keywords = ['alert', 'warning', 'error', 'failure', 'urgent', 'emergency', 'critical']
            if any(keyword in subject_lower or keyword in body_lower for keyword in alert_keywords):
                categories['alerts'].append(email)
                continue
            
            # 更新类邮件
            update_keywords = ['update', 'progress', 'status', 'report', 'summary', 'review']
            if any(keyword in subject_lower or keyword in body_lower for keyword in update_keywords):
                categories['updates'].append(email)
                continue
            
            # 一般邮件
            categories['general'].append(email)
        
        return categories
    
    def extract_key_data(self, emails: List[Dict]) -> Dict:
        """提取关键数据点"""
        key_data = {
            'total_emails': len(emails),
            'by_importance': {'high': 0, 'medium': 0, 'low': 0},
            'by_category': {'decisions': 0, 'updates': 0, 'alerts': 0, 'general': 0},
            'key_decisions': [],
            'urgent_items': [],
            'data_points': []
        }
        
        for email in emails:
            # 统计重要性
            key_data['by_importance'][email['importance']] += 1
            
            # 提取决策信息
            if 'decision' in email['subject'].lower() or 'decide' in email['body'].lower():
                decision_info = self.extract_decision_info(email)
                if decision_info:
                    key_data['key_decisions'].append(decision_info)
            
            # 提取紧急事项
            if email['importance'] == 'high':
                key_data['urgent_items'].append({
                    'subject': email['subject'],
                    'summary': email['body'][:200] + '...' if len(email['body']) > 200 else email['body']
                })
            
            # 提取数据点（数字、百分比等）
            data_points = self.extract_data_points(email['body'])
            key_data['data_points'].extend(data_points)
        
        return key_data
    
    def extract_decision_info(self, email: Dict) -> Optional[Dict]:
        """提取决策信息"""
        body = email['body'].lower()
        
        # 查找决策相关的句子
        decision_patterns = [
            r'决定.*?(?:关于|针对|为).*?(?=\n|$)',
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
        """提取数据点（数字、百分比等）"""
        data_points = []
        
        # 提取百分比
        percent_matches = re.findall(r'(\d+(?:\.\d+)?)%', text)
        for match in percent_matches:
            data_points.append({
                'type': 'percentage',
                'value': float(match),
                'context': self.find_context(text, match + '%')
            })
        
        # 提取数字（可能代表金额、数量等）
        number_matches = re.findall(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', text)
        for match in number_matches:
            # 跳过日期和简单数字
            if len(match) > 3 and not match.startswith('0'):
                try:
                    value = float(match.replace(',', ''))
                    if value > 100:  # 过滤掉小数字
                        data_points.append({
                            'type': 'number',
                            'value': value,
                            'context': self.find_context(text, match)
                        })
                except:
                    pass
        
        return data_points
    
    def find_context(self, text: str, target: str, context_size: int = 50) -> str:
        """查找目标文本的上下文"""
        index = text.find(target)
        if index == -1:
            return ""
        
        start = max(0, index - context_size)
        end = min(len(text), index + len(target) + context_size)
        return text[start:end].strip()
    
    def compare_with_history(self, current_data: Dict) -> Dict:
        """与历史数据对比"""
        comparison = {
            'email_count_change': 0,
            'new_topics': [],
            'trending_keywords': [],
            'significant_changes': []
        }
        
        # 加载历史数据
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                # 对比邮件数量变化
                if 'total_emails' in history:
                    comparison['email_count_change'] = current_data['total_emails'] - history['total_emails']
                
                # 对比主题变化（简化实现）
                # 这里可以添加更复杂的主题对比逻辑
                
            except Exception as e:
                logger.error(f"历史数据对比失败: {e}")
        
        # 保存当前数据作为历史
        self.save_history(current_data)
        
        return comparison
    
    def save_history(self, data: Dict):
        """保存历史数据"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("历史数据已保存")
        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")
    
    def generate_report(self, emails: List[Dict], key_data: Dict, comparison: Dict) -> str:
        """生成日报"""
        if not emails:
            return "# 邮件日报\n\n今天没有收到指定发件人的邮件。\n"
        
        # 分类邮件
        categories = self.categorize_emails(emails)
        
        # 构建报告
        report = f"""# 邮件日报 - {datetime.now().strftime('%Y年%m月%d日')}

## 📊 执行摘要
- 新邮件：{key_data['total_emails']}封"""
        
        if comparison['email_count_change'] != 0:
            change_symbol = "↑" if comparison['email_count_change'] > 0 else "↓"
            report += f"（{change_symbol} {abs(comparison['email_count_change'])}封 vs 昨日）"
        
        report += f"""
- 重要邮件：{key_data['by_importance']['high']}封（包含关键决策信息）
- 紧急事项：{len(key_data['urgent_items'])}封（需要立即处理）

## 📈 趋势分析"""
        
        if comparison['email_count_change'] != 0:
            trend = "增长" if comparison['email_count_change'] > 0 else "减少"
            report += f"\n- 邮件总量：{trend} {abs(comparison['email_count_change'])}封 vs 昨日"
        
        report += f"""
- 高重要性：{key_data['by_importance']['high']}封
- 中重要性：{key_data['by_importance']['medium']}封  
- 一般重要性：{key_data['by_importance']['low']}封

## 📋 详细内容

### 🎯 重要决策"""
        
        if key_data['key_decisions']:
            for i, decision in enumerate(key_data['key_decisions'], 1):
                report += f"\n{i}. **{decision['subject']}** - {decision['decision'][:100]}..."
        else:
            report += "\n今天没有明确的决策类邮件。"
        
        report += f"""

### ⚡ 紧急事项"""
        
        if key_data['urgent_items']:
            for item in key_data['urgent_items']:
                report += f"\n- **{item['subject']}** - {item['summary'][:150]}..."
        else:
            report += "\n今天没有紧急事项。"
        
        report += f"""

### 📊 分类统计
- 决策类：{len(categories['decisions'])}封
- 更新类：{len(categories['updates'])}封  
- 警报类：{len(categories['alerts'])}封
- 一般类：{len(categories['general'])}封

### 📈 数据要点"""
        
        if key_data['data_points']:
            # 显示前5个数据点
            for i, data_point in enumerate(key_data['data_points'][:5], 1):
                report += f"\n{i}. {data_point['value']} {data_point['type']} - {data_point['context'][:80]}..."
        else:
            report += "\n今天没有发现明显的数据要点。"
        
        report += f"""

## 🎯 行动建议
基于今天的邮件分析，建议关注以下事项："""
        
        # 生成行动建议
        recommendations = []
        if key_data['by_importance']['high'] > 0:
            recommendations.append("**优先级高**：处理标记为重要的邮件")
        if len(key_data['key_decisions']) > 0:
            recommendations.append("**决策跟进**：关注邮件中的决策事项")
        if len(key_data['urgent_items']) > 0:
            recommendations.append("**紧急处理**：优先处理紧急邮件事项")
        if comparison['email_count_change'] > 5:
            recommendations.append("**邮件激增**：今天邮件数量显著增加，建议优化邮件管理")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"\n{i}. {rec}"
        else:
            report += "\n今天邮件较为常规，按正常流程处理即可。"
        
        report += "\n"
        
        return report
    
    def run(self, hours: int = 24, sender: str = None) -> str:
        """运行完整的邮件日报生成流程"""
        try:
            logger.info(f"开始生成邮件日报 - 时间范围: {hours}小时")
            
            # 使用指定的发件人或默认发件人
            if sender:
                self.target_sender = sender
            
            # 计算时间范围
            since_date = datetime.now() - timedelta(hours=hours)
            
            # 连接邮箱
            mail = self.connect_to_mailbox()
            
            # 搜索邮件
            email_ids = self.search_emails_from_sender(mail, since_date)
            
            if not email_ids:
                logger.info("未找到符合条件的邮件")
                mail.logout()
                return self.generate_report([], {}, {})
            
            # 解析所有邮件
            emails = []
            for email_id in email_ids:
                email_data = self.parse_email(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.logout()
            
            logger.info(f"成功解析 {len(emails)} 封邮件")
            
            # 提取关键信息
            key_data = self.extract_key_data(emails)
            
            # 与历史对比
            comparison = self.compare_with_history(key_data)
            
            # 生成报告
            report = self.generate_report(emails, key_data, comparison)
            
            logger.info("邮件日报生成完成")
            return report
            
        except Exception as e:
            logger.error(f"邮件日报生成失败: {e}")
            return f"# 邮件日报生成失败\n\n错误信息: {str(e)}\n\n请检查邮箱配置和网络连接。"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='邮件日报自动生成工具')
    parser.add_argument('--hours', type=int, default=24, help='时间范围（小时）')
    parser.add_argument('--sender', type=str, help='指定发件人（覆盖环境变量）')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # 创建日报生成器
    reporter = EmailDailyReport()
    
    # 生成报告
    report = reporter.run(hours=args.hours, sender=args.sender)
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到: {args.output}")
    else:
        print(report)

if __name__ == '__main__':
    main()
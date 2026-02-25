#!/usr/bin/env python3
"""
趋势分析器 - 用于分析邮件数据的历史趋势和变化模式
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter
import numpy as np

class TrendAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, 'email_history.json')
        self.trends_file = os.path.join(data_dir, 'trends.json')
        
        os.makedirs(data_dir, exist_ok=True)
    
    def analyze_weekly_trends(self, current_data: Dict) -> Dict:
        """分析周趋势"""
        # 加载历史数据
        history = self.load_history()
        
        if not history:
            return {
                'weekly_change': 0,
                'trending_keywords': [],
                'pattern_changes': [],
                'prediction': 'insufficient_data'
            }
        
        # 分析7天趋势
        weekly_analysis = {
            'email_volume_trend': self.analyze_volume_trend(history, days=7),
            'keyword_trends': self.analyze_keyword_trends(history, days=7),
            'importance_trends': self.analyze_importance_trends(history, days=7),
            'category_trends': self.analyze_category_trends(history, days=7)
        }
        
        return weekly_analysis
    
    def analyze_volume_trend(self, history: List[Dict], days: int = 7) -> Dict:
        """分析邮件数量趋势"""
        if len(history) < 2:
            return {'trend': 'stable', 'change_rate': 0}
        
        # 获取最近几天的邮件数量
        recent_volumes = [day.get('total_emails', 0) for day in history[-days:]]
        
        if len(recent_volumes) < 2:
            return {'trend': 'stable', 'change_rate': 0}
        
        # 计算变化率
        change_rate = 0
        if len(recent_volumes) >= 2:
            latest = recent_volumes[-1]
            previous = recent_volumes[-2]
            if previous > 0:
                change_rate = ((latest - previous) / previous) * 100
        
        # 判断趋势
        if abs(change_rate) < 5:
            trend = 'stable'
        elif change_rate > 20:
            trend = 'significantly_increasing'
        elif change_rate > 5:
            trend = 'increasing'
        elif change_rate < -20:
            trend = 'significantly_decreasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'change_rate': change_rate,
            'recent_volumes': recent_volumes
        }
    
    def analyze_keyword_trends(self, history: List[Dict], days: int = 7) -> List[Dict]:
        """分析关键词趋势"""
        if len(history) < 2:
            return []
        
        # 提取最近和之前的关键词
        recent_keywords = []
        previous_keywords = []
        
        for i, day_data in enumerate(history[-days:]):
            keywords = day_data.get('keywords', [])
            if i >= days - 3:  # 最近3天
                recent_keywords.extend(keywords)
            else:
                previous_keywords.extend(keywords)
        
        # 计算关键词频率
        recent_counter = Counter(recent_keywords)
        previous_counter = Counter(previous_keywords)
        
        # 找出新兴关键词
        trending_keywords = []
        for keyword, recent_count in recent_counter.items():
            previous_count = previous_counter.get(keyword, 0)
            if recent_count > previous_count * 1.5 and recent_count >= 2:
                trending_keywords.append({
                    'keyword': keyword,
                    'recent_count': recent_count,
                    'previous_count': previous_count,
                    'trend': 'emerging'
                })
        
        # 找出衰退关键词
        declining_keywords = []
        for keyword, previous_count in previous_counter.items():
            recent_count = recent_counter.get(keyword, 0)
            if recent_count < previous_count * 0.5 and previous_count >= 2:
                declining_keywords.append({
                    'keyword': keyword,
                    'recent_count': recent_count,
                    'previous_count': previous_count,
                    'trend': 'declining'
                })
        
        return trending_keywords + declining_keywords
    
    def analyze_importance_trends(self, history: List[Dict], days: int = 7) -> Dict:
        """分析重要性趋势"""
        if len(history) < 2:
            return {'trend': 'stable'}
        
        recent_importance = []
        for day_data in history[-days:]:
            importance_dist = day_data.get('by_importance', {})
            recent_importance.append(importance_dist)
        
        # 计算高重要性邮件比例趋势
        high_importance_ratios = []
        for imp_dist in recent_importance:
            total = sum(imp_dist.values())
            if total > 0:
                high_ratio = imp_dist.get('high', 0) / total * 100
                high_importance_ratios.append(high_ratio)
        
        if len(high_importance_ratios) < 2:
            return {'trend': 'stable'}
        
        # 判断趋势
        latest_ratio = high_importance_ratios[-1]
        avg_ratio = np.mean(high_importance_ratios[:-1])
        
        if latest_ratio > avg_ratio * 1.2:
            trend = 'increasing_importance'
        elif latest_ratio < avg_ratio * 0.8:
            trend = 'decreasing_importance'
        else:
            trend = 'stable_importance'
        
        return {
            'trend': trend,
            'latest_ratio': latest_ratio,
            'average_ratio': avg_ratio,
            'ratios': high_importance_ratios
        }
    
    def analyze_category_trends(self, history: List[Dict], days: int = 7) -> Dict:
        """分析分类趋势"""
        if len(history) < 2:
            return {'trend': 'stable'}
        
        recent_categories = []
        for day_data in history[-days:]:
            cat_dist = day_data.get('by_category', {})
            recent_categories.append(cat_dist)
        
        # 分析各分类的变化
        category_trends = {}
        categories = ['decisions', 'updates', 'alerts', 'general']
        
        for category in categories:
            category_counts = [cat_dist.get(category, 0) for cat_dist in recent_categories]
            if len(category_counts) >= 2:
                latest = category_counts[-1]
                previous_avg = np.mean(category_counts[:-1]) if len(category_counts) > 1 else latest
                
                if latest > previous_avg * 1.5:
                    trend = 'significantly_increasing'
                elif latest > previous_avg * 1.1:
                    trend = 'increasing'
                elif latest < previous_avg * 0.5:
                    trend = 'significantly_decreasing'
                elif latest < previous_avg * 0.9:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                category_trends[category] = {
                    'trend': trend,
                    'latest_count': latest,
                    'previous_average': previous_avg,
                    'counts': category_counts
                }
        
        return category_trends
    
    def generate_trend_insights(self, analysis: Dict) -> List[str]:
        """生成趋势洞察"""
        insights = []
        
        # 邮件数量趋势洞察
        volume_trend = analysis.get('email_volume_trend', {})
        if volume_trend.get('change_rate', 0) > 20:
            insights.append(f"📈 邮件数量显著增长（+{volume_trend['change_rate']:.1f}%），建议关注邮件管理效率")
        elif volume_trend.get('change_rate', 0) < -20:
            insights.append(f"📉 邮件数量显著下降（{volume_trend['change_rate']:.1f}%），可能反映业务活动变化")
        
        # 重要性趋势洞察
        importance_trend = analysis.get('importance_trends', {})
        if importance_trend.get('trend') == 'increasing_importance':
            insights.append("⚠️ 高重要性邮件比例上升，建议优先处理重要事项")
        elif importance_trend.get('trend') == 'decreasing_importance':
            insights.append("✅ 高重要性邮件比例下降，整体邮件压力减轻")
        
        # 关键词趋势洞察
        keyword_trends = analysis.get('keyword_trends', [])
        emerging_keywords = [kw for kw in keyword_trends if kw.get('trend') == 'emerging']
        if emerging_keywords:
            top_keywords = [kw['keyword'] for kw in emerging_keywords[:3]]
            insights.append(f"🔍 新兴关键词：{', '.join(top_keywords)} - 反映当前关注热点")
        
        return insights
    
    def load_history(self) -> List[Dict]:
        """加载历史数据"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载历史数据失败: {e}")
            return []
    
    def generate_weekly_report(self, current_data: Dict) -> str:
        """生成周趋势报告"""
        weekly_analysis = self.analyze_weekly_trends(current_data)
        
        report = f"""# 周趋势分析报告 - {datetime.now().strftime('%Y年%m月%d日')}

## 📊 本周邮件趋势概览

### 📈 邮件数量趋势
- 趋势状态：{weekly_analysis.get('email_volume_trend', {}).get('trend', 'unknown')}
- 变化率：{weekly_analysis.get('email_volume_trend', {}).get('change_rate', 0):.1f}%
- 最近数量：{weekly_analysis.get('email_volume_trend', {}).get('recent_volumes', [])[-3:]}

### 🔑 关键词趋势
"""
        
        keyword_trends = weekly_analysis.get('keyword_trends', [])
        if keyword_trends:
            for trend in keyword_trends[:5]:
                report += f"- **{trend['keyword']}**: {trend['trend']} (最近：{trend['recent_count']}，之前：{trend['previous_count']})\n"
        else:
            report += "- 本周关键词趋势相对稳定\n"
        
        report += f"""

### 📊 重要性趋势
- 高重要性邮件趋势：{weekly_analysis.get('importance_trends', {}).get('trend', 'unknown')}
- 当前比例：{weekly_analysis.get('importance_trends', {}).get('latest_ratio', 0):.1f}%
- 平均比例：{weekly_analysis.get('importance_trends', {}).get('average_ratio', 0):.1f}%

### 📂 分类趋势
"""
        
        category_trends = weekly_analysis.get('category_trends', {})
        for category, trend_data in category_trends.items():
            report += f"- **{category}**: {trend_data['trend']} (当前：{trend_data['latest_count']}，平均：{trend_data['previous_average']:.1f})\n"
        
        # 生成洞察
        insights = self.generate_trend_insights(weekly_analysis)
        if insights:
            report += f"""

## 💡 趋势洞察
"""
            for insight in insights:
                report += f"- {insight}\n"
        
        report += "\n---\n*报告由邮件日报系统自动生成*"
        
        return report

# 使用示例
if __name__ == '__main__':
    analyzer = TrendAnalyzer('/tmp/email_data')
    
    # 示例当前数据
    current_data = {
        'total_emails': 15,
        'by_importance': {'high': 3, 'medium': 8, 'low': 4},
        'by_category': {'decisions': 4, 'updates': 6, 'alerts': 2, 'general': 3},
        'keywords': ['budget', 'strategy', 'AI', 'meeting', 'review'],
        'date': datetime.now().isoformat()
    }
    
    # 生成周趋势报告
    report = analyzer.generate_weekly_report(current_data)
    print(report)
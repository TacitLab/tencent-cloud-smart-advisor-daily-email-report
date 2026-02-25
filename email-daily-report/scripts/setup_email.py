#!/usr/bin/env python3
"""
邮箱配置和设置脚本
用于测试邮箱连接和配置定时任务
"""

import os
import sys
import json
import getpass
from typing import Dict
import imaplib
import smtplib
from datetime import datetime

def test_email_connection(config: Dict) -> bool:
    """测试邮箱连接"""
    try:
        print(f"正在连接到 {config['host']}...")
        
        # 测试IMAP连接
        mail = imaplib.IMAP4_SSL(config['host'])
        mail.login(config['user'], config['password'])
        
        # 检查收件箱
        status, messages = mail.select('INBOX')
        if status == 'OK':
            print("✅ IMAP连接成功")
            
            # 获取邮件数量
            status, msg_nums = mail.search(None, 'ALL')
            if status == 'OK':
                email_count = len(msg_nums[0].split())
                print(f"📧 收件箱中有 {email_count} 封邮件")
            
            mail.logout()
            return True
        else:
            print("❌ 无法选择收件箱")
            return False
            
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP连接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

def interactive_setup() -> Dict:
    """交互式配置设置"""
    print("=" * 50)
    print("📧 邮件日报系统 - 配置向导")
    print("=" * 50)
    
    config = {}
    
    # 邮箱服务商选择
    print("\n1. 选择邮箱服务商:")
    print("   1. 腾讯企业邮 (exmail.qq.com)")
    print("   2. QQ邮箱 (imap.qq.com)")
    print("   3. Gmail (imap.gmail.com)")
    print("   4. Outlook (imap-mail.outlook.com)")
    print("   5. 自定义")
    
    provider_choice = input("   请选择 (1-5): ").strip()
    
    provider_map = {
        '1': {'host': 'imap.exmail.qq.com', 'name': '腾讯企业邮'},
        '2': {'host': 'imap.qq.com', 'name': 'QQ邮箱'},
        '3': {'host': 'imap.gmail.com', 'name': 'Gmail'},
        '4': {'host': 'imap-mail.outlook.com', 'name': 'Outlook'},
        '5': {'host': '', 'name': '自定义'}
    }
    
    if provider_choice in provider_map:
        provider_info = provider_map[provider_choice]
        config['host'] = provider_info['host']
        print(f"   ✅ 已选择: {provider_info['name']}")
    else:
        print("❌ 无效选择，使用腾讯企业邮作为默认")
        config['host'] = 'imap.exmail.qq.com'
    
    if provider_choice == '5':
        config['host'] = input("   请输入IMAP服务器地址: ").strip()
    
    # 邮箱地址
    print("\n2. 输入邮箱地址:")
    config['user'] = input("   邮箱地址: ").strip()
    
    # 密码/应用专用密码
    print("\n3. 输入邮箱密码或应用专用密码:")
    print("   💡 提示: 建议使用应用专用密码，更安全")
    config['password'] = getpass.getpass("   密码: ").strip()
    
    # 监控的发件人
    print("\n4. 设置要监控的发件人:")
    print("   例如: email@advisor.cloud.tencent.com")
    config['sender'] = input("   发件人地址: ").strip()
    
    # 检查时间
    print("\n5. 设置日报生成时间:")
    print("   默认: 09:00 (早上9点)")
    time_input = input("   时间 (HH:MM, 24小时制): ").strip()
    if time_input and len(time_input) == 5 and ':' in time_input:
        config['check_time'] = time_input
    else:
        config['check_time'] = '09:00'
        print("   ✅ 使用默认时间: 09:00")
    
    # 时间范围
    print("\n6. 设置检查的时间范围:")
    print("   默认: 24小时 (过去一天的邮件)")
    hours_input = input("   时间范围 (小时): ").strip()
    if hours_input.isdigit() and int(hours_input) > 0:
        config['hours'] = int(hours_input)
    else:
        config['hours'] = 24
        print("   ✅ 使用默认范围: 24小时")
    
    return config

def save_config(config: Dict, config_file: str):
    """保存配置到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 配置已保存到: {config_file}")
        return True
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False

def generate_cron_config(config: Dict) -> str:
    """生成cron配置"""
    check_time = config.get('check_time', '09:00')
    hour, minute = check_time.split(':')
    
    # 获取脚本路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'email_daily_report.py')
    
    cron_line = f"{minute} {hour} * * * /usr/bin/python3 {script_path} >> /var/log/email-report.log 2>&1"
    
    return cron_line

def setup_cron_job(cron_line: str):
    """设置cron任务"""
    print(f"\n📅 建议的cron任务:")
    print(f"   {cron_line}")
    print(f"\n💡 设置方法:")
    print(f"   1. 运行: crontab -e")
    print(f"   2. 添加这行到文件末尾")
    print(f"   3. 保存并退出")
    print(f"\n📋 验证cron任务:")
    print(f"   运行: crontab -l")
    print(f"   查看是否已添加成功")

def create_env_file(config: Dict, env_file: str):
    """创建环境变量文件"""
    env_content = f"""# 邮件日报系统 - 环境变量配置
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# IMAP服务器配置
export EMAIL_HOST="{config['host']}"
export EMAIL_USER="{config['user']}"
export EMAIL_PASS="{config['password']}"

# 监控配置
export EMAIL_SENDER="{config['sender']}"
export EMAIL_HOURS="{config['hours']}"
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"\n✅ 环境变量文件已创建: {env_file}")
        print(f"   使用方法: source {env_file}")
    except Exception as e:
        print(f"❌ 创建环境变量文件失败: {e}")

def main():
    """主函数"""
    print("🚀 开始配置邮件日报系统...")
    
    # 配置目录
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    config_file = os.path.join(config_dir, 'email_config.json')
    env_file = os.path.join(config_dir, 'email.env')
    
    # 交互式配置
    config = interactive_setup()
    
    print("\n" + "=" * 50)
    print("🔍 正在测试邮箱连接...")
    
    # 测试连接
    if test_email_connection(config):
        print("✅ 邮箱连接测试成功！")
    else:
        print("❌ 邮箱连接测试失败，请检查配置")
        retry = input("是否重新配置？(y/n): ").strip().lower()
        if retry == 'y':
            config = interactive_setup()
            if not test_email_connection(config):
                print("❌ 连接仍然失败，请手动检查邮箱设置")
                return
        else:
            return
    
    # 保存配置
    if save_config(config, config_file):
        # 创建环境变量文件
        create_env_file(config, env_file)
        
        # 生成cron配置
        cron_line = generate_cron_config(config)
        setup_cron_job(cron_line)
        
        print("\n" + "=" * 50)
        print("🎉 邮件日报系统配置完成！")
        print("\n📋 后续步骤:")
        print(f"   1. 运行: source {env_file}")
        print(f"   2. 测试日报: python3 scripts/email_daily_report.py")
        print(f"   3. 设置cron任务（见上方建议）")
        print(f"   4. 查看日志: tail -f /var/log/email-report.log")
        print("\n💡 提示:")
        print("   - 首次运行建议手动测试，确认正常工作")
        print("   - 可以修改时间范围: --hours 48 (检查48小时)")
        print("   - 可以指定不同发件人: --sender 'other@company.com'")
        
    else:
        print("❌ 配置保存失败，请重试")

if __name__ == '__main__':
    main()
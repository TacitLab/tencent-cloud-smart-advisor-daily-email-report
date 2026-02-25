#!/usr/bin/env python3
"""
Email Configuration and Setup Script
For testing email connections and configuring scheduled tasks
"""

import os
import sys
import json
import getpass
from typing import Dict
import imaplib
from datetime import datetime

def test_email_connection(config: Dict) -> bool:
    """Test email connection"""
    try:
        print(f"Connecting to {config['host']}...")
        
        mail = imaplib.IMAP4_SSL(config['host'])
        mail.login(config['user'], config['password'])
        
        status, messages = mail.select('INBOX')
        if status == 'OK':
            print("✅ IMAP connection successful")
            
            status, msg_nums = mail.search(None, 'ALL')
            if status == 'OK':
                email_count = len(msg_nums[0].split())
                print(f"📧 Inbox contains {email_count} emails")
            
            mail.logout()
            return True
        else:
            print("❌ Cannot select inbox")
            return False
            
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def interactive_setup() -> Dict:
    """Interactive configuration setup"""
    print("=" * 50)
    print("📧 Email Daily Report System - Configuration Wizard")
    print("=" * 50)
    
    config = {}
    
    print("\n1. Select email provider:")
    print("   1. Tencent Exmail (exmail.qq.com)")
    print("   2. QQ Mail (imap.qq.com)")
    print("   3. Gmail (imap.gmail.com)")
    print("   4. Outlook (imap-mail.outlook.com)")
    print("   5. Custom")
    
    provider_choice = input("   Select (1-5): ").strip()
    
    provider_map = {
        '1': {'host': 'imap.exmail.qq.com', 'name': 'Tencent Exmail'},
        '2': {'host': 'imap.qq.com', 'name': 'QQ Mail'},
        '3': {'host': 'imap.gmail.com', 'name': 'Gmail'},
        '4': {'host': 'imap-mail.outlook.com', 'name': 'Outlook'},
        '5': {'host': '', 'name': 'Custom'}
    }
    
    if provider_choice in provider_map:
        provider_info = provider_map[provider_choice]
        config['host'] = provider_info['host']
        print(f"   ✅ Selected: {provider_info['name']}")
    else:
        print("❌ Invalid selection, using Tencent Exmail as default")
        config['host'] = 'imap.exmail.qq.com'
    
    if provider_choice == '5':
        config['host'] = input("   Enter IMAP server address: ").strip()
    
    print("\n2. Enter email address:")
    config['user'] = input("   Email address: ").strip()
    
    print("\n3. Enter email password or app-specific password:")
    print("   💡 Tip: Use app-specific password for better security")
    config['password'] = getpass.getpass("   Password: ").strip()
    
    print("\n4. Set sender to monitor:")
    print("   Example: email@advisor.cloud.tencent.com")
    config['sender'] = input("   Sender address: ").strip()
    
    print("\n5. Set daily report generation time:")
    print("   Default: 09:00 (9 AM)")
    time_input = input("   Time (HH:MM, 24-hour format): ").strip()
    if time_input and len(time_input) == 5 and ':' in time_input:
        config['check_time'] = time_input
    else:
        config['check_time'] = '09:00'
        print("   ✅ Using default time: 09:00")
    
    print("\n6. Set check time range:")
    print("   Default: 24 hours (past day's emails)")
    hours_input = input("   Time range (hours): ").strip()
    if hours_input.isdigit() and int(hours_input) > 0:
        config['hours'] = int(hours_input)
    else:
        config['hours'] = 24
        print("   ✅ Using default range: 24 hours")
    
    return config

def save_config(config: Dict, config_file: str):
    """Save configuration to file"""
    try:
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Configuration saved to: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def generate_cron_config(config: Dict) -> str:
    """Generate cron configuration"""
    check_time = config.get('check_time', '09:00')
    hour, minute = check_time.split(':')
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'email_daily_report.py')
    
    cron_line = f"{minute} {hour} * * * /usr/bin/python3 {script_path} >> /var/log/email-report.log 2>&1"
    
    return cron_line

def setup_cron_job(cron_line: str):
    """Set up cron job"""
    print(f"\n📅 Recommended cron job:")
    print(f"   {cron_line}")
    print(f"\n💡 Setup instructions:")
    print(f"   1. Run: crontab -e")
    print(f"   2. Add this line to the end of the file")
    print(f"   3. Save and exit")
    print(f"\n📋 Verify cron job:")
    print(f"   Run: crontab -l")
    print(f"   Check if added successfully")

def create_env_file(config: Dict, env_file: str):
    """Create environment variables file"""
    env_content = f"""# Email Daily Report System - Environment Variables
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# IMAP Server Configuration
export EMAIL_HOST="{config['host']}"
export EMAIL_USER="{config['user']}"
export EMAIL_PASS="{config['password']}"

# Monitoring Configuration
export EMAIL_SENDER="{config['sender']}"
export EMAIL_HOURS="{config['hours']}"
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"\n✅ Environment file created: {env_file}")
        print(f"   Usage: source {env_file}")
    except Exception as e:
        print(f"❌ Failed to create environment file: {e}")

def main():
    """Main function"""
    print("🚀 Starting Email Daily Report System configuration...")
    
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    config_file = os.path.join(config_dir, 'email_config.json')
    env_file = os.path.join(config_dir, 'email.env')
    
    config = interactive_setup()
    
    print("\n" + "=" * 50)
    print("🔍 Testing email connection...")
    
    if test_email_connection(config):
        print("✅ Email connection test successful!")
    else:
        print("❌ Email connection test failed, please check configuration")
        retry = input("Reconfigure? (y/n): ").strip().lower()
        if retry == 'y':
            config = interactive_setup()
            if not test_email_connection(config):
                print("❌ Connection still failed, please manually check email settings")
                return
        else:
            return
    
    if save_config(config, config_file):
        create_env_file(config, env_file)
        
        cron_line = generate_cron_config(config)
        setup_cron_job(cron_line)
        
        print("\n" + "=" * 50)
        print("🎉 Email Daily Report System configuration complete!")
        print("\n📋 Next steps:")
        print(f"   1. Run: source {env_file}")
        print(f"   2. Test report: python3 scripts/email_daily_report.py")
        print(f"   3. Set up cron job (see instructions above)")
        print(f"   4. View logs: tail -f /var/log/email-report.log")
        print("\n💡 Tips:")
        print("   - Test manually first to confirm everything works")
        print("   - Change time range: --hours 48 (check 48 hours)")
        print("   - Specify different sender: --sender 'other@company.com'")
        
    else:
        print("❌ Configuration save failed, please retry")

if __name__ == '__main__':
    main()

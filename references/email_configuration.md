# Email Configuration Reference

Detailed guide for configuring email providers and troubleshooting.

## Supported Email Providers

### Tencent Exmail (Recommended)
- **IMAP Server**: `imap.exmail.qq.com`
- **Port**: 993 (SSL)
- **SMTP Server**: `smtp.exmail.qq.com`
- **Ports**: 465 (SSL) or 587 (TLS)
- **Best for**: Enterprise users, stable and secure

### QQ Mail
- **IMAP Server**: `imap.qq.com`
- **Port**: 993 (SSL)
- **Note**: Enable IMAP service in settings first

### Gmail
- **IMAP Server**: `imap.gmail.com`
- **Port**: 993 (SSL)
- **Note**: Requires app-specific password with 2FA enabled

### Outlook/Hotmail
- **IMAP Server**: `imap-mail.outlook.com`
- **Port**: 993 (SSL)
- **Best for**: Microsoft ecosystem integration

## Security Configuration

### App-Specific Passwords (Recommended)

#### Gmail
1. Enable 2-factor authentication
2. Visit: https://myaccount.google.com/apppasswords
3. Generate app-specific password
4. Use generated password in configuration

#### Tencent Exmail / QQ Mail
1. Login to email settings
2. Enable IMAP/SMTP service
3. Generate authorization code
4. Use authorization code as password

#### Outlook
1. Enable 2-factor authentication
2. Visit: https://account.microsoft.com/security
3. Generate app password
4. Use generated password

### Environment Variables

```bash
# IMAP Server Configuration
export EMAIL_HOST="imap.exmail.qq.com"
export EMAIL_USER="your-email@company.com"
export EMAIL_PASS="your-app-password"

# Monitoring Configuration
export EMAIL_SENDER="email@advisor.cloud.tencent.com"
export EMAIL_HOURS="24"
```

## Troubleshooting

### Connection Failures

**Symptom**: `imaplib.IMAP4.error: [AUTHENTICATIONFAILED] Invalid credentials`

**Solutions**:
1. Verify username and password are correct
2. Confirm using app-specific password (not main password)
3. Verify IMAP service is enabled
4. Check network connectivity and firewall settings

**Symptom**: `Connection refused` or `Timeout`

**Solutions**:
1. Verify IMAP server address is correct
2. Confirm port 993 is open
3. Check firewall and network settings
4. Try different network environment

### Authentication Issues

**Symptom**: `Invalid credentials` but password is correct

**Solutions**:
1. Confirm 2-factor authentication is enabled
2. Verify correct app-specific password is used
3. Check account has IMAP access permission
4. Verify account is not locked or restricted

### Search Issues

**Symptom**: No emails found or incomplete results

**Solutions**:
1. Check search criteria syntax is correct
2. Confirm time range settings are reasonable
3. Verify sender address matches exactly
4. Check mailbox has sufficient email volume

## Performance Optimization

### Connection Pooling
- Reuse IMAP connections to reduce overhead
- Set reasonable connection timeouts
- Use connection pools for multiple mailboxes

### Search Optimization
- Use precise time ranges
- Avoid full mailbox searches
- Use combined search criteria effectively

### Data Caching
- Cache frequently used mailbox info
- Store historical data locally
- Clean up expired cache regularly

## Security Best Practices

### Password Management
- Always use app-specific passwords
- Rotate passwords regularly
- Never hardcode passwords in code
- Use environment variables for sensitive data

### Network Security
- Always use SSL/TLS encryption
- Verify server certificates
- Avoid transmitting sensitive info on public networks

### Data Protection
- Encrypt sensitive data stored locally
- Clean up temporary files regularly
- Restrict data access permissions
- Comply with data protection regulations

## Monitoring and Maintenance

### Health Checks
- Regularly check mailbox connection status
- Monitor authentication failure rates
- Track search performance metrics

### Logging
- Log all connections and operations
- Monitor errors and exceptions
- Analyze log data regularly

### Backup Strategy
- Regularly backup configuration files
- Save important historical data
- Establish disaster recovery plan

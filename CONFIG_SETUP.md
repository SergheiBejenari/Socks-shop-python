# 🔧 Configuration Setup Guide

This guide explains how to configure the test automation framework for different environments using Pydantic settings and environment files.

## 📁 Configuration Files Structure

```
project-root/
├── .env.example          # Example configuration (safe to commit)
├── .env.local.example    # Example sensitive data (safe to commit)
├── .env.development      # Development settings (safe to commit)
├── .env.testing          # CI/CD settings (safe to commit) 
├── .env.production       # Production settings (safe to commit)
├── .env                  # Your local settings (DO NOT commit)
├── .env.local            # Your sensitive data (DO NOT commit)
└── .gitignore            # Must exclude .env and .env.local
```

## 🚀 Quick Setup

### 1. **Copy Example Files**
```bash
# Copy main configuration
cp .env.example .env

# Copy sensitive data template
cp .env.local.example .env.local
```

### 2. **Edit Configuration Files**
```bash
# Edit your local settings
nano .env

# Edit sensitive data
nano .env.local
```

### 3. **Set Environment Variable**
```bash
# For development
export ENVIRONMENT=development

# For testing/CI
export ENVIRONMENT=testing

# For production
export ENVIRONMENT=production
```

## 🎯 Configuration Loading Priority

Settings are loaded in this priority order (highest to lowest):

1. **Environment Variables** - `export BROWSER__HEADLESS=true`
2. **`.env.local` file** - Sensitive data, never committed
3. **`.env` file** - Your local settings, never committed  
4. **Environment-specific files** - `.env.development`, `.env.testing`, etc.
5. **Default values** - Hard-coded in `settings.py`

## 🌍 Environment-Specific Configuration

### **Development Environment**
```bash
ENVIRONMENT=development
```
- **Browser**: Headed mode with slow motion for debugging
- **Logging**: DEBUG level with detailed output
- **Tests**: Reduced parallelism, no cleanup for inspection
- **Performance**: Relaxed thresholds

### **Testing/CI Environment** 
```bash
ENVIRONMENT=testing
```
- **Browser**: Headless with optimized arguments
- **Logging**: INFO level, structured format
- **Tests**: High parallelism, automatic cleanup
- **Performance**: Strict thresholds for CI validation

### **Production Environment**
```bash
ENVIRONMENT=production
```
- **Browser**: Security hardened, minimal features
- **Logging**: WARNING level, file-only output
- **Tests**: Monitoring focused, performance testing enabled
- **Security**: SSL validation enforced, short JWT expiry

## 🔑 Sensitive Data Management

### **Local Development**
Store in `.env.local` (never commit):
```bash
DATABASE_PASSWORD=your_local_password
API_SECRET_KEY=your_development_api_key
JWT_SECRET=your_jwt_secret_for_dev
```

### **CI/CD Pipelines**
Set as environment variables in your CI system:

#### GitHub Actions:
```yaml
env:
  ENVIRONMENT: testing
  DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
  API_SECRET_KEY: ${{ secrets.API_SECRET_KEY }}
```

#### Jenkins:
```groovy
environment {
    ENVIRONMENT = 'testing'
    DATABASE_PASSWORD = credentials('database-password')
    API_SECRET_KEY = credentials('api-secret-key')
}
```

#### Docker:
```bash
docker run \
  -e ENVIRONMENT=testing \
  -e DATABASE_PASSWORD="$DATABASE_PASSWORD" \
  -e API_SECRET_KEY="$API_SECRET_KEY" \
  your-test-image
```

## ⚙️ Configuration Categories

### **Browser Settings**
```bash
# Basic browser config
BROWSER__NAME=chromium              # chromium, firefox, webkit
BROWSER__HEADLESS=true              # true/false
BROWSER__VIEWPORT_WIDTH=1920        # Viewport width
BROWSER__VIEWPORT_HEIGHT=1080       # Viewport height

# Performance settings
BROWSER__TIMEOUT=30000              # Timeout in milliseconds
BROWSER__SLOW_MO=0                  # Slow motion delay
MAX_CONCURRENT_BROWSERS=5           # Max parallel browsers

# Recording and debugging
BROWSER__RECORD_VIDEO=false         # Record test videos
BROWSER__SCREENSHOT_MODE=only-on-failure  # Screenshot capture mode
BROWSER__ARGS="--no-sandbox,--disable-gpu"  # Browser arguments
```

### **API Settings**
```bash
# Basic API config
API_BASE_URL=http://localhost:8080/api  # API base URL
API__TIMEOUT=30                         # Request timeout in seconds
API__MAX_RETRIES=3                      # Max retry attempts
API__VALIDATE_SSL=true                  # Validate SSL certificates
```

### **Logging Settings**
```bash
# Logging configuration
LOGGING__LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGGING__CONSOLE_ENABLED=true       # Log to console
LOGGING__FILE_ENABLED=true          # Log to file
LOGGING__FILE_PATH=logs/automation.log  # Log file path
LOGGING__MAX_FILE_SIZE_MB=100       # Max file size before rotation
```

### **Test Settings**
```bash
# Test execution
TEST__PARALLEL_WORKERS=4            # Number of parallel workers
TEST__CLEANUP_DATA=true             # Clean up test data
TEST__REPORT_FORMATS="html,allure"  # Report formats

# Feature flags
TEST__ENABLE_VISUAL_TESTING=false   # Visual regression testing
TEST__ENABLE_ACCESSIBILITY_TESTING=false  # Accessibility testing
TEST__ENABLE_API_CONTRACT_TESTING=true    # API contract testing
```

## 🛡️ Security Best Practices

### **1. Never Commit Sensitive Data**
Add to `.gitignore`:
```gitignore
.env
.env.local
.env.*.local
```

### **2. Use Strong Secret Keys**
```bash
# Generate secure secret key (32+ characters)
SECRET_KEY="$(openssl rand -base64 32)"
JWT_SECRET="$(openssl rand -base64 32)"
```

### **3. Environment-Specific Security**
- **Development**: Relaxed settings for debugging
- **Testing**: Moderate security for CI pipelines
- **Production**: Maximum security hardening

### **4. Rotate Secrets Regularly**
- Change API keys quarterly
- Rotate JWT secrets monthly
- Update database passwords as needed

## 🚨 Common Issues & Solutions

### **Issue: Configuration Not Loading**
```bash
# Check environment variable
echo $ENVIRONMENT

# Verify file exists
ls -la .env*

# Check file permissions
chmod 644 .env .env.local
```

### **Issue: Pydantic Validation Errors**
```python
from src.config.settings import get_settings

# Debug configuration loading
try:
    settings = get_settings()
    print(settings.model_dump_safe())  # Safe dump without secrets
except Exception as e:
    print(f"Config error: {e}")
```

### **Issue: Browser Launch Failures**
```bash
# Check browser configuration
BROWSER__NAME=chromium
BROWSER__HEADLESS=true
BROWSER__ARGS="--no-sandbox,--disable-dev-shm-usage"

# For CI environments, always use headless
BROWSER__HEADLESS=true
```

## 🔍 Debugging Configuration

### **Print Current Configuration**
```python
from src.config.settings import get_settings

settings = get_settings()
print(f"Environment: {settings.environment}")
print(f"Browser: {settings.browser.name}")
print(f"API URL: {settings.api.base_url}")

# Safe dump (excludes sensitive data)
import json
print(json.dumps(settings.model_dump_safe(), indent=2))
```

### **Validate Configuration**
```python
from src.config.settings import Settings

# Validate specific environment
try:
    settings = Settings(environment="production")
    print("✅ Production config valid")
except Exception as e:
    print(f"❌ Production config error: {e}")
```

## 📚 Advanced Usage

### **Dynamic Configuration**
```python
from src.config.settings import get_settings

settings = get_settings()

# Get browser launch options
browser_opts = settings.get_browser_launch_options()

# Get API client config  
api_config = settings.get_api_client_config()

# Check environment
if settings.is_production():
    # Production-specific logic
    pass
```

### **Override Settings Programmatically**
```python
from src.config.settings import Settings

# Override for specific test
settings = Settings(
    browser__headless=False,
    test__parallel_workers=1,
    logging__level="DEBUG"
)
```

This configuration system provides maximum flexibility while maintaining security and environment-specific optimizations!
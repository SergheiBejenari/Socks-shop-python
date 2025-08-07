from src.core.browser_manager import browser_session, get_browser_config_summary

# Configuration-driven browser usage
with browser_session() as session:  # Uses .env settings
    page = session.browser.new_page()
    page.goto("http://localhost:8080")

# Debug current config
config = get_browser_config_summary()
print(f"Using {config['browser_name']} in {config['environment']} mode")
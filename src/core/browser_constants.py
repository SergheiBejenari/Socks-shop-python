# src/core/browser_constants.py
"""
Browser Management Constants

This module defines constants and enums used throughout the browser
management system to avoid magic strings and improve maintainability.

Key Design Benefits:
- No Magic Strings: All browser-related constants in one place
- Type Safety: Enum values prevent typos and invalid values
- Easy Maintenance: Change constants in one place
- IDE Support: Autocompletion and validation

Interview Highlights:
- Professional approach to constants management
- Elimination of magic strings anti-pattern
- Type-safe browser configuration
"""

from enum import Enum
from typing import Dict, List


class BrowserType(str, Enum):
    """Supported browser types."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROME = "chrome"  # Alias for chromium
    SAFARI = "webkit"  # Alias for webkit


class BrowserErrorKeywords:
    """
    Keywords that indicate specific types of browser errors.

    These are used to classify exceptions based on error messages
    from Playwright and browser engines.
    """

    # Browser crash indicators
    CRASH_KEYWORDS = [
        "crash",
        "crashed",
        "terminated",
        "disconnected",
        "closed",
        "connection lost",
        "browser closed",
        "session terminated"
    ]

    # Navigation failure indicators
    NAVIGATION_KEYWORDS = [
        "timeout",
        "net::",
        "dns",
        "connection",
        "network error",
        "navigation timeout",
        "page load timeout",
        "dns_probe_finished",
        "connection_refused",
        "connection_timed_out",
        "name_not_resolved"
    ]

    # Browser launch failure indicators
    LAUNCH_KEYWORDS = [
        "executable",
        "permission denied",
        "not found",
        "launch timeout",
        "browser launch",
        "failed to launch",
        "startup timeout"
    ]

    @classmethod
    def is_crash_error(cls, error_message: str) -> bool:
        """Check if error message indicates browser crash."""
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in cls.CRASH_KEYWORDS)

    @classmethod
    def is_navigation_error(cls, error_message: str) -> bool:
        """Check if error message indicates navigation failure."""
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in cls.NAVIGATION_KEYWORDS)

    @classmethod
    def is_launch_error(cls, error_message: str) -> bool:
        """Check if error message indicates launch failure."""
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in cls.LAUNCH_KEYWORDS)


class WaitUntilOptions(str, Enum):
    """Page navigation wait conditions."""

    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"
    COMMIT = "commit"


class BrowserDefaults:
    """Default values for browser configuration."""

    # Viewport settings
    DEFAULT_VIEWPORT_WIDTH = 1920
    DEFAULT_VIEWPORT_HEIGHT = 1080
    MOBILE_VIEWPORT_WIDTH = 375
    MOBILE_VIEWPORT_HEIGHT = 667

    # Timeout settings (in milliseconds)
    DEFAULT_TIMEOUT = 30000
    LAUNCH_TIMEOUT = 60000
    NAVIGATION_TIMEOUT = 30000

    # Performance settings
    DEFAULT_SLOW_MO = 0
    DEBUG_SLOW_MO = 200

    # Session management
    MAX_CONCURRENT_BROWSERS = 10
    MAX_IDLE_TIME_HOURS = 1
    CLEANUP_INTERVAL_MINUTES = 30

    # Locale and timezone
    DEFAULT_LOCALE = "en-US"
    DEFAULT_TIMEZONE = "UTC"


class ChromiumArgs:
    """Chromium-specific command line arguments."""

    # Security and sandboxing
    SECURITY_ARGS = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
    ]

    # Performance optimization
    PERFORMANCE_ARGS = [
        "--disable-gpu",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-ipc-flooding-protection",
    ]

    # Feature disabling
    FEATURE_ARGS = [
        "--disable-features=TranslateUI",
        "--disable-features=VizDisplayCompositor",
        "--disable-extensions-http-throttling",
    ]

    # Headless-specific arguments
    HEADLESS_ARGS = [
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",
        "--disable-javascript",  # Only for specific use cases
    ]

    @classmethod
    def get_default_args(cls, headless: bool = True) -> List[str]:
        """Get default Chromium arguments."""
        args = cls.SECURITY_ARGS + cls.PERFORMANCE_ARGS + cls.FEATURE_ARGS

        if headless:
            args.extend(cls.HEADLESS_ARGS)

        return args


class FirefoxArgs:
    """Firefox-specific command line arguments."""

    BASIC_ARGS = [
        "-no-remote",
        "-new-instance",
    ]

    HEADLESS_ARGS = [
        "-headless",
    ]

    @classmethod
    def get_default_args(cls, headless: bool = True) -> List[str]:
        """Get default Firefox arguments."""
        args = cls.BASIC_ARGS.copy()

        if headless:
            args.extend(cls.HEADLESS_ARGS)

        return args


class WebKitArgs:
    """WebKit-specific command line arguments."""

    # WebKit has fewer configurable options
    BASIC_ARGS: List[str] = []

    @classmethod
    def get_default_args(cls, headless: bool = True) -> List[str]:
        """Get default WebKit arguments."""
        return cls.BASIC_ARGS.copy()


class BrowserExecutables:
    """Browser executable names by platform."""

    EXECUTABLES: Dict[str, Dict[str, List[str]]] = {
        BrowserType.CHROMIUM: {
            "linux": ["chromium", "chromium-browser", "google-chrome", "chrome"],
            "darwin": ["Chromium.app", "Google Chrome.app"],
            "windows": ["chrome.exe", "chromium.exe", "msedge.exe"]
        },
        BrowserType.FIREFOX: {
            "linux": ["firefox", "firefox-esr"],
            "darwin": ["Firefox.app"],
            "windows": ["firefox.exe"]
        },
        BrowserType.WEBKIT: {
            "linux": [],  # WebKit not commonly available on Linux
            "darwin": ["Safari.app"],  # Safari uses WebKit
            "windows": []  # WebKit not available on Windows
        }
    }

    @classmethod
    def get_executables_for_browser(cls, browser_type: BrowserType, platform: str) -> List[str]:
        """Get list of possible executables for browser type and platform."""
        return cls.EXECUTABLES.get(browser_type, {}).get(platform.lower(), [])


class BrowserCapabilities:
    """Browser-specific capabilities and limitations."""

    SUPPORTS_EXTENSIONS = {
        BrowserType.CHROMIUM: True,
        BrowserType.FIREFOX: True,
        BrowserType.WEBKIT: False,
    }

    SUPPORTS_MOBILE_EMULATION = {
        BrowserType.CHROMIUM: True,
        BrowserType.FIREFOX: True,
        BrowserType.WEBKIT: True,
    }

    SUPPORTS_GEOLOCATION = {
        BrowserType.CHROMIUM: True,
        BrowserType.FIREFOX: True,
        BrowserType.WEBKIT: True,
    }

    @classmethod
    def supports_feature(cls, browser_type: BrowserType, feature: str) -> bool:
        """Check if browser supports specific feature."""
        feature_map = {
            "extensions": cls.SUPPORTS_EXTENSIONS,
            "mobile_emulation": cls.SUPPORTS_MOBILE_EMULATION,
            "geolocation": cls.SUPPORTS_GEOLOCATION,
        }

        if feature in feature_map:
            return feature_map[feature].get(browser_type, False)

        return False


class ErrorClassificationRules:
    """Rules for classifying browser errors into specific exception types."""

    # Priority order matters - more specific rules first
    CLASSIFICATION_RULES = [
        {
            "exception_type": "BrowserLaunchException",
            "keywords": BrowserErrorKeywords.LAUNCH_KEYWORDS,
            "priority": 1
        },
        {
            "exception_type": "BrowserCrashException",
            "keywords": BrowserErrorKeywords.CRASH_KEYWORDS,
            "priority": 2
        },
        {
            "exception_type": "BrowserNavigationException",
            "keywords": BrowserErrorKeywords.NAVIGATION_KEYWORDS,
            "priority": 3
        }
    ]

    @classmethod
    def classify_error(cls, error_message: str) -> str:
        """
        Classify error message into appropriate exception type.

        Args:
            error_message: Error message to classify

        Returns:
            str: Exception type name or "BrowserException" for generic errors
        """
        error_lower = error_message.lower()

        # Sort by priority and check each rule
        sorted_rules = sorted(cls.CLASSIFICATION_RULES, key=lambda x: x["priority"])

        for rule in sorted_rules:
            if any(keyword in error_lower for keyword in rule["keywords"]):
                return rule["exception_type"]

        # Default to generic browser exception
        return "BrowserException"
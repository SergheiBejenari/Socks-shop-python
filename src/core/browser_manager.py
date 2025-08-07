# src/core/browser_manager.py
"""
Browser Management System for Test Automation Framework

This module provides enterprise-grade browser management with:
- Multiple browser support (Chrome, Firefox, Safari/WebKit)
- Session management and isolation
- Automatic cleanup and resource management
- Browser health monitoring
- Cross-platform compatibility
- Performance optimization

Key Design Patterns:
- Factory Pattern: Browser and context creation
- Singleton Pattern: Global browser manager
- Context Manager: Automatic resource cleanup
- Observer Pattern: Browser event monitoring
- Strategy Pattern: Different browser configurations

Interview Highlights:
- Production-ready browser lifecycle management
- Multi-browser and multi-session support
- Automatic resource cleanup and error handling
- Performance monitoring and optimization
- Cross-platform browser management
"""

import asyncio
import platform
import shutil
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from playwright.async_api import (
    Browser as AsyncBrowser,
    BrowserContext as AsyncBrowserContext,
    Page as AsyncPage,
    Playwright as AsyncPlaywright,
    async_playwright
)
from playwright.sync_api import (
    Browser as SyncBrowser,
    BrowserContext as SyncBrowserContext,
    Page as SyncPage,
    Playwright as SyncPlaywright,
    sync_playwright
)

from exceptions.browser import (
    BrowserException,
    BrowserLaunchException,
    BrowserCrashException,
    BrowserNavigationException
)
from exceptions.enums import ErrorSeverity
from logger import get_logger, get_performance_timer
from retry import retry_with_backoff, create_browser_retry_config
from src.config.settings import Settings, get_settings


@dataclass
class BrowserSession:
    """
    Information about an active browser session.

    This class tracks browser instances, contexts, and pages
    for monitoring and cleanup purposes.
    """

    session_id: str
    browser_name: str
    browser: Union[SyncBrowser, AsyncBrowser]
    contexts: List[Union[SyncBrowserContext, AsyncBrowserContext]] = field(default_factory=list)
    pages: List[Union[SyncPage, AsyncPage]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    @property
    def age(self) -> timedelta:
        """Get session age."""
        return datetime.now() - self.created_at

    @property
    def idle_time(self) -> timedelta:
        """Get time since last activity."""
        return datetime.now() - self.last_activity


class BrowserFactory:
    """
    Factory for creating browser instances using configuration settings.

    This factory uses Pydantic settings to configure browsers instead
    of hardcoded constants, making it flexible and environment-aware.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize browser factory with settings.

        Args:
            settings: Application settings (loads from environment if None)
        """
        self.settings = settings or get_settings()
        self.logger = get_logger("browser_factory")
        self._browser_paths = self._detect_browser_paths()

    def _detect_browser_paths(self) -> Dict[str, Optional[str]]:
        """Detect installed browser paths on the system."""
        paths = {}
        system = platform.system().lower()

        # Browser executable patterns by platform
        browser_executables = {
            "chromium": {
                "linux": ["chromium", "chromium-browser", "google-chrome", "chrome"],
                "darwin": ["Chromium.app", "Google Chrome.app"],
                "windows": ["chrome.exe", "chromium.exe", "msedge.exe"]
            },
            "firefox": {
                "linux": ["firefox", "firefox-esr"],
                "darwin": ["Firefox.app"],
                "windows": ["firefox.exe"]
            },
            "webkit": {
                "linux": [],
                "darwin": ["Safari.app"],
                "windows": []
            }
        }

        for browser, executables in browser_executables.items():
            system_executables = executables.get(system, [])
            for executable in system_executables:
                path = shutil.which(executable)
                if path:
                    paths[browser] = path
                    break
            else:
                paths[browser] = None

        self.logger.debug("Detected browser paths", paths=paths)
        return paths

    def create_launch_options(
            self,
            browser_name: Optional[str] = None,
            **overrides
    ) -> Dict[str, Any]:
        """
        Create browser launch options from configuration.

        Args:
            browser_name: Browser type (uses config default if None)
            **overrides: Override specific settings

        Returns:
            Dictionary of launch options for Playwright
        """
        # Use browser name from config or parameter
        browser = browser_name or self.settings.browser.name

        # Start with configuration defaults
        base_options = {
            "headless": self.settings.browser.headless,
            "timeout": self.settings.browser.timeout,
            "slow_mo": self.settings.browser.slow_mo,
            "args": self.settings.browser.args.copy(),
        }

        # Apply any overrides
        base_options.update(overrides)

        # Add browser-specific arguments
        browser_args = self._get_browser_specific_args(browser, base_options.get("headless", True))
        base_options["args"].extend(browser_args)

        # Set executable path if detected
        if browser in self._browser_paths and self._browser_paths[browser]:
            base_options["executable_path"] = self._browser_paths[browser]

        self.logger.debug(
            f"Created launch options for {browser}",
            browser=browser,
            headless=base_options["headless"],
            args_count=len(base_options["args"])
        )

        return base_options

    def _get_browser_specific_args(self, browser_name: str, headless: bool) -> List[str]:
        """Get browser-specific command line arguments."""
        args = []

        if browser_name in ["chromium", "chrome"]:
            # Chromium/Chrome arguments
            args = [
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
            ]

            if headless:
                args.extend([
                    "--disable-extensions",
                    "--disable-plugins",
                ])

        elif browser_name == "firefox":
            # Firefox arguments
            args = ["-no-remote", "-new-instance"]
            if headless:
                args.append("-headless")

        # WebKit has fewer configurable options

        return args

    def create_context_options(
            self,
            **overrides
    ) -> Dict[str, Any]:
        """
        Create browser context options from configuration.

        Args:
            **overrides: Override specific settings

        Returns:
            Dictionary of context options for Playwright
        """
        options = {
            "viewport": {
                "width": self.settings.browser.viewport_width,
                "height": self.settings.browser.viewport_height,
            },
            "locale": "en-US",  # Could be added to settings
            "timezone_id": "UTC",  # Could be added to settings
        }

        # Apply overrides
        options.update(overrides)

        return options


class BrowserManager:
    """
    Central browser management system using configuration settings.

    This class provides high-level browser management functionality
    with configuration-driven behavior that adapts to different environments.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize browser manager with settings.

        Args:
            settings: Application settings (loads from environment if None)
        """
        self.settings = settings or get_settings()
        self.logger = get_logger("browser_manager")
        self.factory = BrowserFactory(self.settings)

        # Session tracking
        self._sessions: Dict[str, BrowserSession] = {}
        self._playwright_instance: Optional[Union[SyncPlaywright, AsyncPlaywright]] = None

        # Get cleanup settings from configuration
        self._max_idle_time = timedelta(hours=1)  # Could be configurable

        self.logger.info(
            "Browser manager initialized",
            max_browsers=self.settings.browser.max_concurrent_browsers,
            browser_type=self.settings.browser.name,
            headless=self.settings.browser.headless
        )

    @contextmanager
    def browser_session(
            self,
            browser_name: Optional[str] = None,
            **launch_options
    ):
        """
        Context manager for browser sessions with automatic cleanup.

        Args:
            browser_name: Browser type (uses config default if None)
            **launch_options: Browser launch options

        Yields:
            BrowserSession: Active browser session

        Example:
            >>> with manager.browser_session("chromium", headless=False) as session:
            ...     page = session.browser.new_page()
            ...     page.goto("https://example.com")
        """
        session = None
        try:
            session = self.launch_browser(browser_name, **launch_options)
            yield session
        finally:
            if session:
                self.close_session(session.session_id)

    @asynccontextmanager
    async def async_browser_session(
            self,
            browser_name: Optional[str] = None,
            **launch_options
    ):
        """
        Async context manager for browser sessions.

        Args:
            browser_name: Browser type (uses config default if None)
            **launch_options: Browser launch options

        Yields:
            BrowserSession: Active browser session
        """
        session = None
        try:
            session = await self.launch_browser_async(browser_name, **launch_options)
            yield session
        finally:
            if session:
                await self.close_session_async(session.session_id)

    @retry_with_backoff(
        config=create_browser_retry_config(),
        operation_name="launch_browser"
    )
    def launch_browser(
            self,
            browser_name: Optional[str] = None,
            session_id: Optional[str] = None,
            **launch_options
    ) -> BrowserSession:
        """
        Launch a new browser instance using configuration settings.

        Args:
            browser_name: Browser type (uses config default if None)
            session_id: Optional session ID (generates if None)
            **launch_options: Override launch options

        Returns:
            BrowserSession: Information about the launched browser

        Raises:
            BrowserLaunchException: If browser fails to launch
            BrowserException: For other browser-related errors
        """
        # Check concurrent browser limit from settings
        if len(self._sessions) >= self.settings.browser.max_concurrent_browsers:
            self._cleanup_idle_sessions()
            if len(self._sessions) >= self.settings.browser.max_concurrent_browsers:
                raise BrowserException(
                    "Maximum concurrent browsers reached",
                    severity=ErrorSeverity.HIGH
                ).add_context("max_browsers", self.settings.browser.max_concurrent_browsers)

        session_id = session_id or str(uuid4())
        browser_name = browser_name or self.settings.browser.name

        with get_performance_timer(f"launch_{browser_name}") as timer:
            try:
                # Initialize Playwright if needed
                if self._playwright_instance is None:
                    self._playwright_instance = sync_playwright().start()

                # Get browser launcher
                if browser_name in ["chromium", "chrome"]:
                    launcher = self._playwright_instance.chromium
                elif browser_name == "firefox":
                    launcher = self._playwright_instance.firefox
                elif browser_name in ["webkit", "safari"]:
                    launcher = self._playwright_instance.webkit
                else:
                    raise BrowserLaunchException(
                        f"Unsupported browser: {browser_name}",
                        browser_name=browser_name
                    )

                # Create launch options from configuration
                options = self.factory.create_launch_options(browser_name, **launch_options)

                # Launch browser
                browser = launcher.launch(**options)

                # Create session
                session = BrowserSession(
                    session_id=session_id,
                    browser_name=browser_name,
                    browser=browser
                )

                self._sessions[session_id] = session

                self.logger.info(
                    f"Browser {browser_name} launched successfully",
                    session_id=session_id,
                    browser_name=browser_name,
                    headless=options.get("headless", True)
                )

                return session

            except Exception as e:
                self.logger.error(
                    f"Failed to launch {browser_name}",
                    browser_name=browser_name,
                    error=str(e)
                )

                # Classify error and raise appropriate exception
                if "executable" in str(e).lower():
                    raise BrowserLaunchException(
                        f"Browser executable not found: {e}",
                        browser_name=browser_name
                    )
                elif "timeout" in str(e).lower():
                    raise BrowserLaunchException(
                        f"Browser launch timeout: {e}",
                        browser_name=browser_name
                    )
                else:
                    raise BrowserLaunchException(
                        f"Browser launch failed: {e}",
                        browser_name=browser_name,
                        original_exception=e
                    )

    async def launch_browser_async(
            self,
            browser_name: Optional[str] = None,
            session_id: Optional[str] = None,
            **launch_options
    ) -> BrowserSession:
        """
        Launch browser asynchronously.

        Args:
            browser_name: Browser type (uses config default if None)
            session_id: Optional session ID
            **launch_options: Browser launch options

        Returns:
            BrowserSession: Information about the launched browser
        """
        if len(self._sessions) >= self.settings.browser.max_concurrent_browsers:
            await self._cleanup_idle_sessions_async()
            if len(self._sessions) >= self.settings.browser.max_concurrent_browsers:
                raise BrowserException(
                    "Maximum concurrent browsers reached",
                    severity=ErrorSeverity.HIGH
                )

        session_id = session_id or str(uuid4())
        browser_name = browser_name or self.settings.browser.name

        try:
            # Initialize async Playwright if needed
            if self._playwright_instance is None:
                self._playwright_instance = await async_playwright().start()

            # Get browser launcher
            if browser_name in ["chromium", "chrome"]:
                launcher = self._playwright_instance.chromium
            elif browser_name == "firefox":
                launcher = self._playwright_instance.firefox
            elif browser_name in ["webkit", "safari"]:
                launcher = self._playwright_instance.webkit
            else:
                raise BrowserLaunchException(
                    f"Unsupported browser: {browser_name}",
                    browser_name=browser_name
                )

            # Create launch options
            options = self.factory.create_launch_options(browser_name, **launch_options)

            # Launch browser
            browser = await launcher.launch(**options)

            # Create session
            session = BrowserSession(
                session_id=session_id,
                browser_name=browser_name,
                browser=browser
            )

            self._sessions[session_id] = session

            self.logger.info(
                f"Async browser {browser_name} launched successfully",
                session_id=session_id,
                browser_name=browser_name
            )

            return session

        except Exception as e:
            self.logger.error(
                f"Failed to launch async {browser_name}",
                browser_name=browser_name,
                error=str(e)
            )
            raise BrowserLaunchException(
                f"Async browser launch failed: {e}",
                browser_name=browser_name,
                original_exception=e
            )

    def close_session(self, session_id: str) -> bool:
        """
        Close a browser session and clean up resources.

        Args:
            session_id: Session ID to close

        Returns:
            bool: True if session was closed successfully
        """
        if session_id not in self._sessions:
            self.logger.warning(f"Session {session_id} not found for closure")
            return False

        session = self._sessions[session_id]

        try:
            with get_performance_timer(f"close_session_{session.browser_name}"):
                # Close all pages
                for page in session.pages:
                    try:
                        page.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing page: {e}")

                # Close all contexts
                for context in session.contexts:
                    try:
                        context.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing context: {e}")

                # Close browser
                session.browser.close()

                # Remove from sessions
                del self._sessions[session_id]

                self.logger.info(
                    f"Session {session_id} closed successfully",
                    session_id=session_id,
                    browser_name=session.browser_name,
                    session_age=session.age.total_seconds()
                )

                return True

        except Exception as e:
            self.logger.error(
                f"Error closing session {session_id}: {e}",
                session_id=session_id,
                error=str(e)
            )
            # Still remove from sessions to prevent leaks
            if session_id in self._sessions:
                del self._sessions[session_id]
            return False

    async def close_session_async(self, session_id: str) -> bool:
        """Close browser session asynchronously."""
        if session_id not in self._sessions:
            self.logger.warning(f"Async session {session_id} not found for closure")
            return False

        session = self._sessions[session_id]

        try:
            # Close all pages
            for page in session.pages:
                try:
                    await page.close()
                except Exception as e:
                    self.logger.warning(f"Error closing async page: {e}")

            # Close all contexts
            for context in session.contexts:
                try:
                    await context.close()
                except Exception as e:
                    self.logger.warning(f"Error closing async context: {e}")

            # Close browser
            await session.browser.close()

            # Remove from sessions
            del self._sessions[session_id]

            self.logger.info(
                f"Async session {session_id} closed successfully",
                session_id=session_id,
                browser_name=session.browser_name
            )

            return True

        except Exception as e:
            self.logger.error(f"Error closing async session {session_id}: {e}")
            if session_id in self._sessions:
                del self._sessions[session_id]
            return False

    def create_context(
            self,
            session_id: str,
            **context_options
    ) -> Union[SyncBrowserContext, AsyncBrowserContext]:
        """
        Create a new browser context using configuration settings.

        Args:
            session_id: Target session ID
            **context_options: Override context options

        Returns:
            Browser context instance

        Raises:
            BrowserException: If session not found or context creation fails
        """
        if session_id not in self._sessions:
            raise BrowserException(
                f"Session {session_id} not found",
                severity=ErrorSeverity.HIGH
            )

        session = self._sessions[session_id]
        session.update_activity()

        try:
            # Create context options from configuration
            options = self.factory.create_context_options(**context_options)
            context = session.browser.new_context(**options)
            session.contexts.append(context)

            self.logger.debug(
                f"Context created in session {session_id}",
                session_id=session_id,
                context_count=len(session.contexts),
                viewport=f"{options['viewport']['width']}x{options['viewport']['height']}"
            )

            return context

        except Exception as e:
            # Check for browser crash during context creation
            if any(keyword in str(e).lower() for keyword in ['crash', 'terminated', 'disconnected']):
                raise BrowserCrashException(
                    f"Browser crashed while creating context: {e}",
                    original_exception=e
                ).add_context("session_id", session_id)

            raise BrowserException(
                f"Failed to create context: {e}",
                original_exception=e
            ).add_context("session_id", session_id)

    async def create_context_async(
            self,
            session_id: str,
            **context_options
    ) -> AsyncBrowserContext:
        """Create browser context asynchronously."""
        if session_id not in self._sessions:
            raise BrowserException(f"Async session {session_id} not found")

        session = self._sessions[session_id]
        session.update_activity()

        try:
            options = self.factory.create_context_options(**context_options)
            context = await session.browser.new_context(**options)
            session.contexts.append(context)

            self.logger.debug(f"Async context created in session {session_id}")
            return context

        except Exception as e:
            raise BrowserException(
                f"Failed to create async context: {e}",
                original_exception=e
            )

    def create_page(
            self,
            session_id: str,
            context: Optional[Union[SyncBrowserContext, AsyncBrowserContext]] = None
    ) -> Union[SyncPage, AsyncPage]:
        """
        Create a new page in a browser session.

        Args:
            session_id: Target session ID
            context: Specific context to use (creates new one if None)

        Returns:
            Page instance
        """
        if session_id not in self._sessions:
            raise BrowserException(f"Session {session_id} not found")

        session = self._sessions[session_id]
        session.update_activity()

        try:
            if context is None:
                context = self.create_context(session_id)

            page = context.new_page()
            session.pages.append(page)

            self.logger.debug(
                f"Page created in session {session_id}",
                session_id=session_id,
                page_count=len(session.pages)
            )

            return page

        except Exception as e:
            # Check for browser crash during page creation
            if any(keyword in str(e).lower() for keyword in ['crash', 'terminated', 'disconnected']):
                raise BrowserCrashException(
                    f"Browser crashed while creating page: {e}",
                    original_exception=e
                ).add_context("session_id", session_id)

            raise BrowserException(
                f"Failed to create page: {e}",
                original_exception=e
            ).add_context("session_id", session_id)

    async def create_page_async(
            self,
            session_id: str,
            context: Optional[AsyncBrowserContext] = None
    ) -> AsyncPage:
        """Create page asynchronously."""
        if session_id not in self._sessions:
            raise BrowserException(f"Async session {session_id} not found")

        session = self._sessions[session_id]
        session.update_activity()

        try:
            if context is None:
                context = await self.create_context_async(session_id)

            page = await context.new_page()
            session.pages.append(page)

            self.logger.debug(f"Async page created in session {session_id}")
            return page

        except Exception as e:
            # Check for browser crash during page creation
            if any(keyword in str(e).lower() for keyword in ['crash', 'terminated', 'disconnected']):
                raise BrowserCrashException(
                    f"Browser crashed while creating async page: {e}",
                    original_exception=e
                ).add_context("session_id", session_id)

            raise BrowserException(f"Failed to create async page: {e}")

    def navigate_to(
            self,
            session_id: str,
            url: str,
            timeout: Optional[int] = None,
            wait_until: str = "load"
    ) -> bool:
        """
        Navigate to URL with configuration-aware settings.

        Args:
            session_id: Target session ID
            url: URL to navigate to
            timeout: Navigation timeout (uses config default if None)
            wait_until: When to consider navigation successful

        Returns:
            bool: True if navigation successful

        Raises:
            BrowserNavigationException: For navigation failures
            BrowserCrashException: If browser crashes during navigation
        """
        if session_id not in self._sessions:
            raise BrowserException(f"Session {session_id} not found")

        session = self._sessions[session_id]
        session.update_activity()

        if not session.pages:
            raise BrowserException("No pages available for navigation")

        page = session.pages[0]  # Use first page
        current_url = None

        # Use timeout from settings if not specified
        nav_timeout = timeout or self.settings.browser.timeout

        try:
            current_url = page.url

            with get_performance_timer(f"navigate_to_{url}") as timer:
                page.goto(url, timeout=nav_timeout, wait_until=wait_until)
                timer.add_metric("target_url", url)
                timer.add_metric("final_url", page.url)
                timer.add_metric("timeout_used", nav_timeout)

            self.logger.info(
                f"Navigation successful",
                session_id=session_id,
                target_url=url,
                final_url=page.url,
                timeout=nav_timeout
            )

            return True

        except Exception as e:
            error_message = str(e).lower()

            # Classify error based on content
            if any(keyword in error_message for keyword in ['crash', 'terminated', 'disconnected', 'closed']):
                raise BrowserCrashException(
                    f"Browser crashed during navigation to {url}",
                    last_url=current_url,
                    original_exception=e
                ).add_context("session_id", session_id).add_context("target_url", url)

            elif any(keyword in error_message for keyword in ['timeout', 'net::', 'dns', 'connection']):
                raise BrowserNavigationException(
                    f"Navigation to {url} failed: {e}",
                    target_url=url,
                    current_url=current_url,
                    navigation_timeout=nav_timeout,
                    original_exception=e
                ).add_context("session_id", session_id)

            else:
                raise BrowserException(
                    f"Unexpected error during navigation: {e}",
                    original_exception=e
                ).add_context("session_id", session_id).add_context("target_url", url)

    async def navigate_to_async(
            self,
            session_id: str,
            url: str,
            timeout: Optional[int] = None,
            wait_until: str = "load"
    ) -> bool:
        """Navigate to URL asynchronously with proper error handling."""
        if session_id not in self._sessions:
            raise BrowserException(f"Async session {session_id} not found")

        session = self._sessions[session_id]
        session.update_activity()

        if not session.pages:
            raise BrowserException("No pages available for async navigation")

        page = session.pages[0]  # Use first page
        current_url = None
        nav_timeout = timeout or self.settings.browser.timeout

        try:
            current_url = page.url
            await page.goto(url, timeout=nav_timeout, wait_until=wait_until)

            self.logger.info(
                f"Async navigation successful",
                session_id=session_id,
                target_url=url,
                final_url=page.url
            )

            return True

        except Exception as e:
            error_message = str(e).lower()

            # Classify error based on content
            if any(keyword in error_message for keyword in ['crash', 'terminated', 'disconnected']):
                raise BrowserCrashException(
                    f"Browser crashed during async navigation to {url}",
                    last_url=current_url,
                    original_exception=e
                ).add_context("session_id", session_id)

            elif any(keyword in error_message for keyword in ['timeout', 'net::', 'dns', 'connection']):
                raise BrowserNavigationException(
                    f"Async navigation to {url} failed: {e}",
                    target_url=url,
                    current_url=current_url,
                    navigation_timeout=nav_timeout,
                    original_exception=e
                ).add_context("session_id", session_id)

            else:
                raise BrowserException(f"Unexpected async navigation error: {e}")

    def check_browser_health(self, session_id: str) -> Dict[str, Any]:
        """
        Check browser health and detect potential crashes.

        Args:
            session_id: Session ID to check

        Returns:
            Dict with health information

        Raises:
            BrowserCrashException: If browser has crashed
        """
        if session_id not in self._sessions:
            raise BrowserException(f"Session {session_id} not found")

        session = self._sessions[session_id]

        try:
            browser = session.browser
            health_info = {
                "session_id": session_id,
                "browser_name": session.browser_name,
                "session_age": session.age.total_seconds(),
                "contexts_count": len(session.contexts),
                "pages_count": len(session.pages),
                "is_connected": True,  # Will be updated based on checks
                "last_activity": session.last_activity.isoformat()
            }

            # Try to get browser version (this will fail if browser crashed)
            try:
                if hasattr(browser, 'version'):
                    health_info["browser_version"] = browser.version()
                else:
                    # For browsers without direct version access, try through a page
                    if session.pages:
                        page = session.pages[0]
                        user_agent = page.evaluate("() => navigator.userAgent")
                        health_info["user_agent"] = user_agent
            except Exception as e:
                # Browser might be crashed or disconnected
                health_info["is_connected"] = False
                health_info["error"] = str(e)

                # Raise crash exception
                raise BrowserCrashException(
                    f"Browser health check failed - browser appears to have crashed",
                    crash_reason=str(e),
                    original_exception=e
                ).add_context("health_info", health_info)

            return health_info

        except BrowserCrashException:
            # Re-raise crash exceptions
            raise
        except Exception as e:
            # Unexpected errors during health check
            raise BrowserException(
                f"Health check failed: {e}",
                original_exception=e
            ).add_context("session_id", session_id)

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get session information by ID."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[BrowserSession]:
        """Get list of all active sessions."""
        return list(self._sessions.values())

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions."""
        total_sessions = len(self._sessions)
        browser_counts = {}
        total_contexts = 0
        total_pages = 0

        for session in self._sessions.values():
            browser_counts[session.browser_name] = browser_counts.get(session.browser_name, 0) + 1
            total_contexts += len(session.contexts)
            total_pages += len(session.pages)

        return {
            "total_sessions": total_sessions,
            "browser_counts": browser_counts,
            "total_contexts": total_contexts,
            "total_pages": total_pages,
            "max_concurrent_browsers": self.settings.browser.max_concurrent_browsers,
            "utilization_percent": (total_sessions / self.settings.browser.max_concurrent_browsers) * 100
        }

    def _cleanup_idle_sessions(self) -> int:
        """Clean up idle browser sessions."""
        cleaned = 0
        current_time = datetime.now()

        # Find idle sessions
        idle_sessions = []
        for session_id, session in self._sessions.items():
            if current_time - session.last_activity > self._max_idle_time:
                idle_sessions.append(session_id)

        # Close idle sessions
        for session_id in idle_sessions:
            if self.close_session(session_id):
                cleaned += 1

        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} idle browser sessions")

        return cleaned

    async def _cleanup_idle_sessions_async(self) -> int:
        """Clean up idle sessions asynchronously."""
        cleaned = 0
        current_time = datetime.now()

        # Find idle sessions
        idle_sessions = []
        for session_id, session in self._sessions.items():
            if current_time - session.last_activity > self._max_idle_time:
                idle_sessions.append(session_id)

        # Close idle sessions
        for session_id in idle_sessions:
            if await self.close_session_async(session_id):
                cleaned += 1

        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} idle async browser sessions")

        return cleaned

    def cleanup_all_sessions(self) -> int:
        """Close all active browser sessions."""
        session_ids = list(self._sessions.keys())
        cleaned = 0

        for session_id in session_ids:
            if self.close_session(session_id):
                cleaned += 1

        # Cleanup Playwright instance
        if self._playwright_instance:
            try:
                if hasattr(self._playwright_instance, 'stop'):
                    self._playwright_instance.stop()
                self._playwright_instance = None
            except Exception as e:
                self.logger.warning(f"Error stopping Playwright: {e}")

        self.logger.info(f"Cleaned up all {cleaned} browser sessions")
        return cleaned

    async def cleanup_all_sessions_async(self) -> int:
        """Close all active sessions asynchronously."""
        session_ids = list(self._sessions.keys())
        cleaned = 0

        for session_id in session_ids:
            if await self.close_session_async(session_id):
                cleaned += 1

        # Cleanup async Playwright instance
        if self._playwright_instance:
            try:
                if hasattr(self._playwright_instance, 'stop'):
                    await self._playwright_instance.stop()
                self._playwright_instance = None
            except Exception as e:
                self.logger.warning(f"Error stopping async Playwright: {e}")

        self.logger.info(f"Cleaned up all {cleaned} async browser sessions")
        return cleaned

    def __del__(self):
        """Cleanup resources when manager is destroyed."""
        try:
            self.cleanup_all_sessions()
        except Exception as e:
            # Don't raise exceptions in destructor
            pass


# Global browser manager instance
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager(settings: Optional[Settings] = None) -> BrowserManager:
    """
    Get the global browser manager instance using configuration.

    Args:
        settings: Application settings (loads from environment if None)

    Returns:
        BrowserManager: Global browser manager instance configured from settings
    """
    global _browser_manager

    if _browser_manager is None:
        _browser_manager = BrowserManager(settings)

    return _browser_manager


def cleanup_browsers() -> int:
    """
    Clean up all browser instances managed by the global manager.

    Returns:
        int: Number of sessions cleaned up
    """
    if _browser_manager:
        return _browser_manager.cleanup_all_sessions()
    return 0


# Convenience functions for common browser operations
@contextmanager
def browser_session(browser_name: Optional[str] = None, **launch_options):
    """
    Convenience context manager for browser sessions using configuration.

    Args:
        browser_name: Browser type (uses config default if None)
        **launch_options: Override browser launch options

    Yields:
        BrowserSession: Active browser session

    Example:
        >>> # Use configured browser (from .env or settings)
        >>> with browser_session() as session:
        ...     page = session.browser.new_page()
        ...     page.goto("http://localhost:8080")

        >>> # Override configuration
        >>> with browser_session("firefox", headless=False) as session:
        ...     page = session.browser.new_page()
        ...     page.goto("http://localhost:8080")
    """
    manager = get_browser_manager()
    with manager.browser_session(browser_name, **launch_options) as session:
        yield session


@asynccontextmanager
async def async_browser_session(browser_name: Optional[str] = None, **launch_options):
    """
    Convenience async context manager for browser sessions using configuration.

    Args:
        browser_name: Browser type (uses config default if None)
        **launch_options: Override browser launch options

    Yields:
        BrowserSession: Active browser session
    """
    manager = get_browser_manager()
    async with manager.async_browser_session(browser_name, **launch_options) as session:
        yield session


# Configuration-aware helper functions
def create_configured_browser_session(
        url: Optional[str] = None,
        browser_name: Optional[str] = None,
        **overrides
) -> BrowserSession:
    """
    Create browser session with automatic navigation using configuration.

    Args:
        url: URL to navigate to (uses SOCK_SHOP_BASE_URL from config if None)
        browser_name: Browser type (uses config default if None)
        **overrides: Override configuration settings

    Returns:
        BrowserSession: Configured browser session

    Example:
        >>> # Navigate to configured base URL
        >>> session = create_configured_browser_session()

        >>> # Navigate to specific URL with config overrides
        >>> session = create_configured_browser_session(
        ...     url="http://example.com",
        ...     headless=False
        ... )
    """
    manager = get_browser_manager()
    settings = manager.settings

    # Launch browser with configuration
    session = manager.launch_browser(browser_name, **overrides)

    # Navigate if URL provided
    if url:
        manager.navigate_to(session.session_id, url)
    elif hasattr(settings, 'sock_shop_base_url'):
        manager.navigate_to(session.session_id, settings.sock_shop_base_url)

    return session


def get_browser_config_summary() -> Dict[str, Any]:
    """
    Get summary of current browser configuration.

    Returns:
        Dict: Browser configuration summary for debugging

    Example:
        >>> config = get_browser_config_summary()
        >>> print(f"Browser: {config['browser_name']}")
        >>> print(f"Headless: {config['headless']}")
    """
    settings = get_settings()

    return {
        "environment": settings.environment.value,
        "browser_name": settings.browser.name,
        "headless": settings.browser.headless,
        "viewport": f"{settings.browser.viewport_width}x{settings.browser.viewport_height}",
        "timeout": settings.browser.timeout,
        "max_concurrent": settings.browser.max_concurrent_browsers,
        "sock_shop_url": settings.sock_shop_base_url,
        "api_base_url": settings.api.base_url,
        "debug_mode": settings.debug,
    }
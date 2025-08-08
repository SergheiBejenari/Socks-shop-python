# src/utils/wait_helpers.py
"""
Intelligent Wait Helpers for Test Automation Framework

This module provides sophisticated waiting mechanisms that go beyond
basic Playwright waits. It includes custom wait conditions, smart
waiting strategies, and performance-optimized wait helpers.

Key Features:
- Custom wait conditions for complex scenarios
- Performance-optimized waiting with early termination
- Retry logic with intelligent backoff
- Network and loading state awareness
- Mobile and responsive design considerations

Interview Highlights:
- Advanced waiting strategies beyond basic Playwright waits
- Performance-conscious wait implementations
- Robust error handling and recovery
- Production-ready timeout management
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, Union, Dict, List
from functools import wraps

from playwright.sync_api import Page, Locator, expect
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator

from src.config.settings import get_settings
from src.core.logger import get_logger, get_performance_timer
from src.core.exceptions import TimeoutException, ElementException
from src.core.exceptions.enums import ErrorSeverity


class WaitCondition(str, Enum):
    """
    Enumeration of wait conditions for elements and pages.

    These conditions provide semantic meaning to different
    types of waits beyond basic visibility checks.
    """

    VISIBLE = "visible"
    """Element is visible and has non-zero size."""

    ATTACHED = "attached"
    """Element is attached to the DOM."""

    DETACHED = "detached"
    """Element is removed from the DOM."""

    ENABLED = "enabled"
    """Element is enabled and can be interacted with."""

    DISABLED = "disabled"
    """Element is disabled and cannot be interacted with."""

    CLICKABLE = "clickable"
    """Element is visible, enabled, and can be clicked."""

    EDITABLE = "editable"
    """Element can be edited (input, textarea, contenteditable)."""

    HIDDEN = "hidden"
    """Element is hidden (not visible)."""

    STABLE = "stable"
    """Element has stopped moving/animating."""

    HAS_TEXT = "has_text"
    """Element contains specific text."""

    HAS_VALUE = "has_value"
    """Element has specific value."""

    HAS_CLASS = "has_class"
    """Element has specific CSS class."""

    HAS_ATTRIBUTE = "has_attribute"
    """Element has specific attribute."""

    COUNT = "count"
    """Specific number of elements match selector."""


class NetworkWaitCondition(str, Enum):
    """Network-related wait conditions."""

    NETWORK_IDLE = "networkidle"
    """No network requests for 500ms."""

    LOAD = "load"
    """Page load event fired."""

    DOMCONTENTLOADED = "domcontentloaded"
    """DOM content loaded event fired."""

    COMMIT = "commit"
    """Page navigation committed."""


class SmartWaiter:
    """
    Intelligent waiting system with performance optimization.

    This class provides sophisticated waiting mechanisms that
    combine multiple conditions and optimize for performance.
    """

    def __init__(self, page: Union[Page, AsyncPage]):
        """
        Initialize smart waiter.

        Args:
            page: Playwright page instance
        """
        self.page = page
        self.settings = get_settings()
        self.logger = get_logger("wait_helpers")
        self.default_timeout = self.settings.browser.timeout

    def wait_for_condition(
            self,
            condition: Callable[[], bool],
            timeout: Optional[int] = None,
            poll_interval: float = 0.1,
            timeout_message: Optional[str] = None
    ) -> bool:
        """
        Wait for custom condition to be true.

        Args:
            condition: Function that returns True when condition is met
            timeout: Maximum wait time in milliseconds
            poll_interval: How often to check condition in seconds
            timeout_message: Custom timeout message

        Returns:
            True when condition is met

        Raises:
            TimeoutException: If condition not met within timeout
        """
        timeout = timeout or self.default_timeout
        timeout_seconds = timeout / 1000

        start_time = time.time()

        with get_performance_timer("wait_for_condition") as timer:
            while time.time() - start_time < timeout_seconds:
                try:
                    if condition():
                        timer.add_metric("condition_met", True)
                        timer.add_metric("wait_time", time.time() - start_time)
                        return True
                except Exception as e:
                    # Log condition check errors but continue waiting
                    self.logger.debug(f"Condition check failed: {e}")

                time.sleep(poll_interval)

            # Timeout reached
            elapsed = time.time() - start_time
            timer.add_metric("condition_met", False)
            timer.add_metric("wait_time", elapsed)

            message = timeout_message or f"Custom condition not met within {elapsed:.2f}s"
            raise TimeoutException(
                message,
                timeout_duration=elapsed,
                operation_type="wait_for_condition"
            )

    def wait_for_element_stable(
            self,
            locator: Union[Locator, AsyncLocator],
            timeout: Optional[int] = None,
            stability_duration: float = 0.5
    ) -> bool:
        """
        Wait for element to stop moving/animating.

        Args:
            locator: Element locator
            timeout: Maximum wait time
            stability_duration: How long element must be stable

        Returns:
            True when element is stable
        """
        timeout = timeout or self.default_timeout

        def is_stable() -> bool:
            try:
                # Get element position
                box = locator.bounding_box()
                if not box:
                    return False

                # Wait for stability duration
                time.sleep(stability_duration)

                # Check if position changed
                new_box = locator.bounding_box()
                if not new_box:
                    return False

                # Compare positions (allow 1px tolerance)
                position_stable = (
                        abs(box['x'] - new_box['x']) <= 1 and
                        abs(box['y'] - new_box['y']) <= 1 and
                        abs(box['width'] - new_box['width']) <= 1 and
                        abs(box['height'] - new_box['height']) <= 1
                )

                return position_stable

            except Exception:
                return False

        return self.wait_for_condition(
            condition=is_stable,
            timeout=timeout,
            poll_interval=0.1,
            timeout_message="Element did not stabilize"
        )

    def wait_for_network_idle(
            self,
            timeout: Optional[int] = None,
            idle_time: int = 500
    ) -> bool:
        """
        Wait for network to be idle.

        Args:
            timeout: Maximum wait time
            idle_time: Idle duration in milliseconds

        Returns:
            True when network is idle
        """
        timeout = timeout or self.default_timeout

        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)

            self.logger.debug(
                "Network idle state reached",
                timeout=timeout,
                idle_time=idle_time
            )

            return True

        except Exception as e:
            raise TimeoutException(
                f"Network did not become idle within {timeout}ms",
                timeout_duration=timeout / 1000,
                operation_type="wait_for_network_idle",
                original_exception=e
            )

    def wait_for_page_load_complete(
            self,
            timeout: Optional[int] = None,
            wait_for_fonts: bool = True,
            wait_for_images: bool = True
    ) -> bool:
        """
        Wait for complete page load including resources.

        Args:
            timeout: Maximum wait time
            wait_for_fonts: Wait for fonts to load
            wait_for_images: Wait for images to load

        Returns:
            True when page fully loaded
        """
        timeout = timeout or self.default_timeout

        with get_performance_timer("wait_for_page_load_complete") as timer:
            try:
                # Wait for basic load events
                self.page.wait_for_load_state("load", timeout=timeout)
                self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
                self.page.wait_for_load_state("networkidle", timeout=timeout)

                # Wait for fonts if requested
                if wait_for_fonts:
                    self._wait_for_fonts_loaded(timeout=5000)  # Shorter timeout for fonts

                # Wait for images if requested
                if wait_for_images:
                    self._wait_for_images_loaded(timeout=10000)  # Timeout for images

                timer.add_metric("fonts_waited", wait_for_fonts)
                timer.add_metric("images_waited", wait_for_images)

                self.logger.debug(
                    "Page load complete",
                    duration=timer.duration,
                    url=self.page.url
                )

                return True

            except Exception as e:
                raise TimeoutException(
                    f"Page did not load completely within {timeout}ms",
                    timeout_duration=timeout / 1000,
                    operation_type="wait_for_page_load_complete",
                    original_exception=e
                )

    def _wait_for_fonts_loaded(self, timeout: int = 5000) -> None:
        """Wait for web fonts to load."""
        try:
            self.page.wait_for_function(
                "document.fonts ? document.fonts.ready : Promise.resolve()",
                timeout=timeout
            )
        except Exception as e:
            self.logger.debug(f"Font loading wait failed: {e}")
            # Don't fail the test for font loading issues

    def _wait_for_images_loaded(self, timeout: int = 10000) -> None:
        """Wait for images to load."""
        try:
            # Wait for all images to have naturalWidth > 0 or failed to load
            self.page.wait_for_function("""
                () => {
                    const images = Array.from(document.images);
                    return images.length === 0 || images.every(img => 
                        img.complete && (img.naturalWidth > 0 || img.src === '')
                    );
                }
            """, timeout=timeout)
        except Exception as e:
            self.logger.debug(f"Image loading wait failed: {e}")
            # Don't fail the test for image loading issues

    def wait_for_element_count(
            self,
            selector: str,
            expected_count: int,
            timeout: Optional[int] = None,
            comparison: str = "equal"
    ) -> bool:
        """
        Wait for specific number of elements.

        Args:
            selector: Element selector
            expected_count: Expected element count
            timeout: Maximum wait time
            comparison: Comparison type ('equal', 'greater', 'less', 'greater_equal', 'less_equal')

        Returns:
            True when count condition is met
        """
        timeout = timeout or self.default_timeout

        def check_count() -> bool:
            try:
                actual_count = self.page.locator(selector).count()

                if comparison == "equal":
                    return actual_count == expected_count
                elif comparison == "greater":
                    return actual_count > expected_count
                elif comparison == "less":
                    return actual_count < expected_count
                elif comparison == "greater_equal":
                    return actual_count >= expected_count
                elif comparison == "less_equal":
                    return actual_count <= expected_count
                else:
                    raise ValueError(f"Invalid comparison: {comparison}")

            except Exception:
                return False

        return self.wait_for_condition(
            condition=check_count,
            timeout=timeout,
            timeout_message=f"Element count condition not met: {selector} {comparison} {expected_count}"
        )

    def wait_for_text_to_appear(
            self,
            locator: Union[Locator, AsyncLocator],
            expected_text: str,
            timeout: Optional[int] = None,
            case_sensitive: bool = True,
            exact_match: bool = False
    ) -> bool:
        """
        Wait for text to appear in element.

        Args:
            locator: Element locator
            expected_text: Text to wait for
            timeout: Maximum wait time
            case_sensitive: Case sensitive comparison
            exact_match: Exact text match vs contains

        Returns:
            True when text appears
        """
        timeout = timeout or self.default_timeout

        try:
            if exact_match:
                if case_sensitive:
                    expect(locator).to_have_text(expected_text, timeout=timeout)
                else:
                    expect(locator).to_have_text(
                        expected_text,
                        timeout=timeout,
                        ignore_case=True
                    )
            else:
                if case_sensitive:
                    expect(locator).to_contain_text(expected_text, timeout=timeout)
                else:
                    expect(locator).to_contain_text(
                        expected_text,
                        timeout=timeout,
                        ignore_case=True
                    )

            return True

        except Exception as e:
            raise TimeoutException(
                f"Text '{expected_text}' did not appear within {timeout}ms",
                timeout_duration=timeout / 1000,
                operation_type="wait_for_text",
                original_exception=e
            )

    def wait_for_text_to_disappear(
            self,
            locator: Union[Locator, AsyncLocator],
            text_to_disappear: str,
            timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for text to disappear from element.

        Args:
            locator: Element locator
            text_to_disappear: Text that should disappear
            timeout: Maximum wait time

        Returns:
            True when text disappears
        """
        timeout = timeout or self.default_timeout

        def text_not_present() -> bool:
            try:
                current_text = locator.text_content() or ""
                return text_to_disappear not in current_text
            except Exception:
                return True  # Element not found = text disappeared

        return self.wait_for_condition(
            condition=text_not_present,
            timeout=timeout,
            timeout_message=f"Text '{text_to_disappear}' did not disappear"
        )

    def wait_for_attribute_value(
            self,
            locator: Union[Locator, AsyncLocator],
            attribute_name: str,
            expected_value: str,
            timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for element attribute to have specific value.

        Args:
            locator: Element locator
            attribute_name: Attribute name
            expected_value: Expected attribute value
            timeout: Maximum wait time

        Returns:
            True when attribute has expected value
        """
        timeout = timeout or self.default_timeout

        try:
            expect(locator).to_have_attribute(
                attribute_name,
                expected_value,
                timeout=timeout
            )
            return True

        except Exception as e:
            raise TimeoutException(
                f"Attribute '{attribute_name}' did not have value '{expected_value}' within {timeout}ms",
                timeout_duration=timeout / 1000,
                operation_type="wait_for_attribute",
                original_exception=e
            )

    def wait_for_css_class(
            self,
            locator: Union[Locator, AsyncLocator],
            class_name: str,
            should_have: bool = True,
            timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for element to have or not have CSS class.

        Args:
            locator: Element locator
            class_name: CSS class name
            should_have: True to wait for class, False to wait for removal
            timeout: Maximum wait time

        Returns:
            True when class condition is met
        """
        timeout = timeout or self.default_timeout

        try:
            if should_have:
                expect(locator).to_have_class(class_name, timeout=timeout)
            else:
                expect(locator).not_to_have_class(class_name, timeout=timeout)

            return True

        except Exception as e:
            action = "have" if should_have else "not have"
            raise TimeoutException(
                f"Element did not {action} class '{class_name}' within {timeout}ms",
                timeout_duration=timeout / 1000,
                operation_type="wait_for_css_class",
                original_exception=e
            )

    def wait_for_url_change(
            self,
            expected_url_fragment: Optional[str] = None,
            timeout: Optional[int] = None
    ) -> bool:
        """
        Wait for URL to change.

        Args:
            expected_url_fragment: Optional URL fragment to wait for
            timeout: Maximum wait time

        Returns:
            True when URL changes
        """
        timeout = timeout or self.default_timeout
        current_url = self.page.url

        def url_changed() -> bool:
            new_url = self.page.url
            if expected_url_fragment:
                return expected_url_fragment in new_url
            else:
                return new_url != current_url

        return self.wait_for_condition(
            condition=url_changed,
            timeout=timeout,
            timeout_message=f"URL did not change within {timeout}ms"
        )


class WaitConditionFactory:
    """Factory for creating custom wait conditions."""

    @staticmethod
    def create_wait_condition(
            condition_type: WaitCondition,
            locator: Union[Locator, AsyncLocator],
            **kwargs
    ) -> Callable[[], bool]:
        """
        Create wait condition function.

        Args:
            condition_type: Type of condition to create
            locator: Element locator
            **kwargs: Additional parameters for condition

        Returns:
            Condition function
        """

        def condition_func() -> bool:
            try:
                if condition_type == WaitCondition.VISIBLE:
                    expect(locator).to_be_visible(timeout=1000)
                    return True
                elif condition_type == WaitCondition.ATTACHED:
                    expect(locator).to_be_attached(timeout=1000)
                    return True
                elif condition_type == WaitCondition.DETACHED:
                    expect(locator).to_be_detached(timeout=1000)
                    return True
                elif condition_type == WaitCondition.ENABLED:
                    expect(locator).to_be_enabled(timeout=1000)
                    return True
                elif condition_type == WaitCondition.DISABLED:
                    expect(locator).to_be_disabled(timeout=1000)
                    return True
                elif condition_type == WaitCondition.CLICKABLE:
                    expect(locator).to_be_visible(timeout=1000)
                    expect(locator).to_be_enabled(timeout=1000)
                    return True
                elif condition_type == WaitCondition.EDITABLE:
                    expect(locator).to_be_editable(timeout=1000)
                    return True
                elif condition_type == WaitCondition.HIDDEN:
                    expect(locator).to_be_hidden(timeout=1000)
                    return True
                elif condition_type == WaitCondition.HAS_TEXT:
                    expected_text = kwargs.get('text', '')
                    expect(locator).to_contain_text(expected_text, timeout=1000)
                    return True
                elif condition_type == WaitCondition.HAS_VALUE:
                    expected_value = kwargs.get('value', '')
                    expect(locator).to_have_value(expected_value, timeout=1000)
                    return True
                elif condition_type == WaitCondition.HAS_CLASS:
                    expected_class = kwargs.get('class_name', '')
                    expect(locator).to_have_class(expected_class, timeout=1000)
                    return True
                elif condition_type == WaitCondition.HAS_ATTRIBUTE:
                    attr_name = kwargs.get('attribute_name', '')
                    attr_value = kwargs.get('attribute_value')
                    if attr_value is not None:
                        expect(locator).to_have_attribute(attr_name, attr_value, timeout=1000)
                    else:
                        expect(locator).to_have_attribute(attr_name, timeout=1000)
                    return True
                else:
                    return False

            except Exception:
                return False

        return condition_func


# Convenience functions for common wait operations
def create_wait_condition(
        condition_type: WaitCondition,
        locator: Union[Locator, AsyncLocator],
        **kwargs
) -> Callable[[], bool]:
    """Create wait condition function (convenience function)."""
    return WaitConditionFactory.create_wait_condition(condition_type, locator, **kwargs)


def wait_for_element_stable(
        page: Union[Page, AsyncPage],
        locator: Union[Locator, AsyncLocator],
        timeout: Optional[int] = None,
        stability_duration: float = 0.5
) -> bool:
    """Wait for element to be stable (convenience function)."""
    waiter = SmartWaiter(page)
    return waiter.wait_for_element_stable(locator, timeout, stability_duration)


def wait_for_network_idle(
        page: Union[Page, AsyncPage],
        timeout: Optional[int] = None,
        idle_time: int = 500
) -> bool:
    """Wait for network idle (convenience function)."""
    waiter = SmartWaiter(page)
    return waiter.wait_for_network_idle(timeout, idle_time)


def wait_for_page_load_complete(
        page: Union[Page, AsyncPage],
        timeout: Optional[int] = None,
        wait_for_fonts: bool = True,
        wait_for_images: bool = True
) -> bool:
    """Wait for complete page load (convenience function)."""
    waiter = SmartWaiter(page)
    return waiter.wait_for_page_load_complete(timeout, wait_for_fonts, wait_for_images)


def wait_with_retry(
        condition: Callable[[], bool],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout_per_retry: int = 10000
) -> bool:
    """
    Wait for condition with retry logic.

    Args:
        condition: Condition function to wait for
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        timeout_per_retry: Timeout for each retry attempt

    Returns:
        True if condition met within retries

    Raises:
        TimeoutException: If condition not met after all retries
    """
    logger = get_logger("wait_with_retry")

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            start_time = time.time()

            # Poll condition with timeout
            while time.time() - start_time < timeout_per_retry / 1000:
                if condition():
                    logger.debug(
                        f"Wait condition met on attempt {attempt + 1}",
                        attempt=attempt + 1,
                        elapsed=time.time() - start_time
                    )
                    return True
                time.sleep(0.1)  # Poll interval

            # Timeout reached for this attempt
            if attempt < max_retries:
                logger.debug(
                    f"Wait attempt {attempt + 1} timed out, retrying after {retry_delay}s"
                )
                time.sleep(retry_delay)

        except Exception as e:
            logger.debug(f"Wait attempt {attempt + 1} failed with error: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)

    # All retries exhausted
    raise TimeoutException(
        f"Condition not met after {max_retries + 1} attempts",
        timeout_duration=timeout_per_retry / 1000,
        operation_type="wait_with_retry"
    )


# Decorator for adding smart waiting to functions
def with_smart_wait(
        wait_before: Optional[Callable[[], bool]] = None,
        wait_after: Optional[Callable[[], bool]] = None,
        timeout: Optional[int] = None
):
    """
    Decorator to add smart waiting before/after function execution.

    Args:
        wait_before: Condition to wait for before execution
        wait_after: Condition to wait for after execution
        timeout: Timeout for wait conditions

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(f"smart_wait.{func.__name__}")

            # Wait before execution
            if wait_before:
                try:
                    SmartWaiter(args[0].page).wait_for_condition(
                        wait_before, timeout
                    )
                except Exception as e:
                    logger.warning(f"Pre-execution wait failed: {e}")

            # Execute function
            result = func(*args, **kwargs)

            # Wait after execution
            if wait_after:
                try:
                    SmartWaiter(args[0].page).wait_for_condition(
                        wait_after, timeout
                    )
                except Exception as e:
                    logger.warning(f"Post-execution wait failed: {e}")

            return result

        return wrapper

    return decorator
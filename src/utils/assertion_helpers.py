# src/utils/assertion_helpers.py
"""
Advanced Assertion Helpers for Test Automation Framework

This module provides sophisticated assertion mechanisms that go beyond
basic assertions. It includes soft assertions, custom matchers,
performance assertions, and comprehensive validation helpers.

Key Features:
- Soft assertions that collect multiple failures
- Custom assertion matchers for complex validations
- Performance and timing assertions
- Visual and accessibility assertions
- Detailed failure reporting with context

Interview Highlights:
- Production-ready assertion patterns
- Soft assertion implementation for better test reporting
- Custom assertion DSL for domain-specific validations
- Performance-conscious assertion design
"""

import re
import time
from typing import Any, Dict, List, Optional, Union, Callable, Pattern
from pathlib import Path
from dataclasses import dataclass, field

from playwright.sync_api import Page, Locator, expect
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator

from src.config.settings import get_settings
from src.core.exceptions.enums import ErrorSeverity
from src.core.logger import get_logger, log_assertion
from src.core.exceptions import (
    AutomationException,
    ElementException,
    TestAssertionException
)


@dataclass
class AssertionFailure:
    """Details about a single assertion failure."""

    message: str
    expected: Any
    actual: Any
    assertion_type: str
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert failure to dictionary for reporting."""
        return {
            "message": self.message,
            "expected": str(self.expected),
            "actual": str(self.actual),
            "assertion_type": self.assertion_type,
            "timestamp": self.timestamp,
            "context": self.context,
            "severity": self.severity.value,
            "screenshot_path": self.screenshot_path
        }


class SoftAssertions:
    """
    Soft assertion collector that allows tests to continue after failures.

    This class collects assertion failures without immediately failing
    the test, allowing comprehensive validation of multiple conditions.
    """

    def __init__(self, page: Optional[Union[Page, AsyncPage]] = None):
        """
        Initialize soft assertions.

        Args:
            page: Optional page for screenshots on failures
        """
        self.page = page
        self.failures: List[AssertionFailure] = []
        self.logger = get_logger("soft_assertions")
        self.settings = get_settings()

    def assert_equal(
            self,
            actual: Any,
            expected: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """
        Assert two values are equal.

        Args:
            actual: Actual value
            expected: Expected value
            message: Custom failure message
            severity: Failure severity

        Returns:
            Self for method chaining
        """
        passed = actual == expected

        if not passed:
            failure_message = message or f"Expected {expected}, but got {actual}"
            screenshot_path = self._capture_screenshot("assertion_equal_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=expected,
                actual=actual,
                assertion_type="equal",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

            self.logger.warning(
                "Soft assertion failed",
                assertion_type="equal",
                expected=expected,
                actual=actual,
                message=failure_message
            )

        # Log assertion result
        log_assertion("equal", expected, actual, passed)

        return self

    def assert_not_equal(
            self,
            actual: Any,
            expected: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert two values are not equal."""
        passed = actual != expected

        if not passed:
            failure_message = message or f"Expected {actual} to not equal {expected}"
            screenshot_path = self._capture_screenshot("assertion_not_equal_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"not {expected}",
                actual=actual,
                assertion_type="not_equal",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("not_equal", f"not {expected}", actual, passed)
        return self

    def assert_contains(
            self,
            container: Union[str, List, Dict],
            item: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert container contains item."""
        passed = item in container

        if not passed:
            failure_message = message or f"Expected '{container}' to contain '{item}'"
            screenshot_path = self._capture_screenshot("assertion_contains_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"contains {item}",
                actual=container,
                assertion_type="contains",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("contains", f"contains {item}", container, passed)
        return self

    def assert_not_contains(
            self,
            container: Union[str, List, Dict],
            item: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert container does not contain item."""
        passed = item not in container

        if not passed:
            failure_message = message or f"Expected '{container}' to not contain '{item}'"
            screenshot_path = self._capture_screenshot("assertion_not_contains_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"not contains {item}",
                actual=container,
                assertion_type="not_contains",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("not_contains", f"not contains {item}", container, passed)
        return self

    def assert_matches_pattern(
            self,
            actual: str,
            pattern: Union[str, Pattern],
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert string matches regex pattern."""
        if isinstance(pattern, str):
            regex_pattern = re.compile(pattern)
        else:
            regex_pattern = pattern

        passed = bool(regex_pattern.search(actual))

        if not passed:
            failure_message = message or f"Expected '{actual}' to match pattern '{regex_pattern.pattern}'"
            screenshot_path = self._capture_screenshot("assertion_pattern_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"matches {regex_pattern.pattern}",
                actual=actual,
                assertion_type="matches_pattern",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("matches_pattern", regex_pattern.pattern, actual, passed)
        return self

    def assert_greater_than(
            self,
            actual: Union[int, float],
            expected: Union[int, float],
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert actual value is greater than expected."""
        passed = actual > expected

        if not passed:
            failure_message = message or f"Expected {actual} to be greater than {expected}"
            screenshot_path = self._capture_screenshot("assertion_greater_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"> {expected}",
                actual=actual,
                assertion_type="greater_than",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("greater_than", f"> {expected}", actual, passed)
        return self

    def assert_less_than(
            self,
            actual: Union[int, float],
            expected: Union[int, float],
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert actual value is less than expected."""
        passed = actual < expected

        if not passed:
            failure_message = message or f"Expected {actual} to be less than {expected}"
            screenshot_path = self._capture_screenshot("assertion_less_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=f"< {expected}",
                actual=actual,
                assertion_type="less_than",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("less_than", f"< {expected}", actual, passed)
        return self

    def assert_between(
            self,
            actual: Union[int, float],
            min_value: Union[int, float],
            max_value: Union[int, float],
            inclusive: bool = True,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert value is between min and max."""
        if inclusive:
            passed = min_value <= actual <= max_value
            expected_desc = f"between {min_value} and {max_value} (inclusive)"
        else:
            passed = min_value < actual < max_value
            expected_desc = f"between {min_value} and {max_value} (exclusive)"

        if not passed:
            failure_message = message or f"Expected {actual} to be {expected_desc}"
            screenshot_path = self._capture_screenshot("assertion_between_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=expected_desc,
                actual=actual,
                assertion_type="between",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("between", expected_desc, actual, passed)
        return self

    def assert_true(
            self,
            condition: bool,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert condition is True."""
        passed = condition is True

        if not passed:
            failure_message = message or f"Expected condition to be True, but got {condition}"
            screenshot_path = self._capture_screenshot("assertion_true_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=True,
                actual=condition,
                assertion_type="true",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("true", True, condition, passed)
        return self

    def assert_false(
            self,
            condition: bool,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert condition is False."""
        passed = condition is False

        if not passed:
            failure_message = message or f"Expected condition to be False, but got {condition}"
            screenshot_path = self._capture_screenshot("assertion_false_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=False,
                actual=condition,
                assertion_type="false",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("false", False, condition, passed)
        return self

    def assert_none(
            self,
            actual: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert value is None."""
        passed = actual is None

        if not passed:
            failure_message = message or f"Expected None, but got {actual}"
            screenshot_path = self._capture_screenshot("assertion_none_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected=None,
                actual=actual,
                assertion_type="none",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("none", None, actual, passed)
        return self

    def assert_not_none(
            self,
            actual: Any,
            message: Optional[str] = None,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> "SoftAssertions":
        """Assert value is not None."""
        passed = actual is not None

        if not passed:
            failure_message = message or "Expected value to not be None"
            screenshot_path = self._capture_screenshot("assertion_not_none_failure")

            failure = AssertionFailure(
                message=failure_message,
                expected="not None",
                actual=actual,
                assertion_type="not_none",
                severity=severity,
                screenshot_path=screenshot_path
            )

            self.failures.append(failure)

        log_assertion("not_none", "not None", actual, passed)
        return self

    def add_failure(
            self,
            message: str,
            expected: Any = None,
            actual: Any = None,
            assertion_type: str = "custom",
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            context: Optional[Dict[str, Any]] = None
    ) -> "SoftAssertions":
        """Add custom failure to soft assertions."""
        screenshot_path = self._capture_screenshot("custom_assertion_failure")

        failure = AssertionFailure(
            message=message,
            expected=expected,
            actual=actual,
            assertion_type=assertion_type,
            severity=severity,
            context=context or {},
            screenshot_path=screenshot_path
        )

        self.failures.append(failure)

        self.logger.warning(
            "Custom soft assertion failure added",
            message=message,
            assertion_type=assertion_type,
            severity=severity.value
        )

        return self

    def has_failures(self) -> bool:
        """Check if there are any assertion failures."""
        return len(self.failures) > 0

    def get_failures(self) -> List[AssertionFailure]:
        """Get all assertion failures."""
        return self.failures.copy()

    def get_failure_count(self) -> int:
        """Get number of failures."""
        return len(self.failures)

    def get_failures_by_severity(self, severity: ErrorSeverity) -> List[AssertionFailure]:
        """Get failures filtered by severity."""
        return [f for f in self.failures if f.severity == severity]

    def clear_failures(self) -> None:
        """Clear all assertion failures."""
        self.failures.clear()

    def assert_all(self) -> None:
        """
        Raise exception if there are any failures.

        This should be called at the end of test to fail if soft assertions failed.
        """
        if self.has_failures():
            # Group failures by severity
            critical_failures = self.get_failures_by_severity(ErrorSeverity.CRITICAL)
            high_failures = self.get_failures_by_severity(ErrorSeverity.HIGH)
            medium_failures = self.get_failures_by_severity(ErrorSeverity.MEDIUM)
            low_failures = self.get_failures_by_severity(ErrorSeverity.LOW)

            # Create comprehensive failure message
            failure_summary = []

            if critical_failures:
                failure_summary.append(f"Critical failures: {len(critical_failures)}")
            if high_failures:
                failure_summary.append(f"High severity failures: {len(high_failures)}")
            if medium_failures:
                failure_summary.append(f"Medium severity failures: {len(medium_failures)}")
            if low_failures:
                failure_summary.append(f"Low severity failures: {len(low_failures)}")

            summary_text = ", ".join(failure_summary)

            # Create detailed failure messages
            failure_details = []
            for i, failure in enumerate(self.failures, 1):
                detail = f"{i}. [{failure.assertion_type}] {failure.message}"
                if failure.screenshot_path:
                    detail += f" (screenshot: {failure.screenshot_path})"
                failure_details.append(detail)

            main_message = f"Soft assertions failed: {summary_text}\n" + "\n".join(failure_details)

            # Determine overall severity (highest severity wins)
            if critical_failures:
                severity = ErrorSeverity.CRITICAL
            elif high_failures:
                severity = ErrorSeverity.HIGH
            elif medium_failures:
                severity = ErrorSeverity.MEDIUM
            else:
                severity = ErrorSeverity.LOW

            # Create exception with all failure data
            exception = TestAssertionException(
                message=main_message,
                assertion_type="soft_assertions",
                severity=severity
            ).add_context("failure_count", len(self.failures)) \
                .add_context("failure_details", [f.to_dict() for f in self.failures])

            raise exception

    def _capture_screenshot(self, name: str) -> Optional[str]:
        """Capture screenshot if page is available."""
        if not self.page or not self.settings.browser.screenshot_on_failure:
            return None

        try:
            screenshots_dir = Path("reports/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"soft_assertion_{name}_{timestamp}.png"
            screenshot_path = screenshots_dir / filename

            self.page.screenshot(path=str(screenshot_path), full_page=True)
            return str(screenshot_path)

        except Exception as e:
            self.logger.warning(f"Failed to capture screenshot: {e}")
            return None

    def __enter__(self) -> "SoftAssertions":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - automatically call assert_all."""
        if exc_type is None:  # Only check soft assertions if no other exception
            self.assert_all()


class CustomMatchers:
    """
    Custom assertion matchers for domain-specific validations.

    These matchers provide semantic assertions specific to the
    application domain (e-commerce, socks, etc.).
    """

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if string is valid email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
        return bool(re.match(email_pattern, email))

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Check if string is valid phone number format."""
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,}
        return bool(re.match(phone_pattern, phone))

    @staticmethod
    def is_valid_price(price: str) -> bool:
        """Check if string is valid price format."""
        price_pattern = r'^\$?\d+\.?\d{0,2}
        return bool(re.match(price_pattern, price))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if string is valid URL format."""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*
        return bool(re.match(url_pattern, url))

    @staticmethod
    def contains_sock_sizes(text: str) -> bool:
        """Check if text contains valid sock sizes."""
        sock_sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        return any(size in text.upper() for size in sock_sizes)

    @staticmethod
    def is_valid_credit_card(card_number: str) -> bool:
        """Check if string is valid credit card number format."""
        # Remove spaces and hyphens
        cleaned = re.sub(r'[\s-]', '', card_number)

        # Check length and digits only
        if not re.match(r'^\d{13,19}, cleaned):
            return False

        # Simple Luhn algorithm check
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]

            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10

        return luhn_checksum(cleaned) == 0


class ElementAssertions:
    """
    Specialized assertions for web elements.

    These assertions work with Playwright locators to provide
    comprehensive element validation.
    """

    def __init__(self, locator: Union[Locator, AsyncLocator], page: Optional[Union[Page, AsyncPage]] = None):
        """
        Initialize element assertions.

        Args:
            locator: Element locator
            page: Optional page for screenshots
        """
        self.locator = locator
        self.page = page
        self.logger = get_logger("element_assertions")

    def should_be_visible(
            self,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element is visible."""
        try:
            expect(self.locator).to_be_visible(timeout=timeout or 30000)
            log_assertion("element_visible", True, True, True)
        except Exception as e:
            log_assertion("element_visible", True, False, False)
            failure_message = message or f"Element should be visible but is not"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_be_hidden(
            self,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element is hidden."""
        try:
            expect(self.locator).to_be_hidden(timeout=timeout or 30000)
            log_assertion("element_hidden", True, True, True)
        except Exception as e:
            log_assertion("element_hidden", True, False, False)
            failure_message = message or f"Element should be hidden but is visible"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_contain_text(
            self,
            expected_text: str,
            case_sensitive: bool = True,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element contains specific text."""
        try:
            if case_sensitive:
                expect(self.locator).to_contain_text(expected_text, timeout=timeout or 30000)
            else:
                expect(self.locator).to_contain_text(
                    expected_text,
                    timeout=timeout or 30000,
                    ignore_case=True
                )
            log_assertion("element_contains_text", expected_text, "found", True)
        except Exception as e:
            actual_text = self.locator.text_content() or ""
            log_assertion("element_contains_text", expected_text, actual_text, False)
            failure_message = message or f"Element should contain text '{expected_text}' but contains '{actual_text}'"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_have_exact_text(
            self,
            expected_text: str,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element has exact text."""
        try:
            expect(self.locator).to_have_text(expected_text, timeout=timeout or 30000)
            log_assertion("element_exact_text", expected_text, expected_text, True)
        except Exception as e:
            actual_text = self.locator.text_content() or ""
            log_assertion("element_exact_text", expected_text, actual_text, False)
            failure_message = message or f"Element should have text '{expected_text}' but has '{actual_text}'"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_have_attribute(
            self,
            attribute_name: str,
            expected_value: Optional[str] = None,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element has specific attribute value."""
        try:
            if expected_value is not None:
                expect(self.locator).to_have_attribute(
                    attribute_name,
                    expected_value,
                    timeout=timeout or 30000
                )
            else:
                expect(self.locator).to_have_attribute(
                    attribute_name,
                    timeout=timeout or 30000
                )
            log_assertion("element_attribute", expected_value or "present", "found", True)
        except Exception as e:
            actual_value = self.locator.get_attribute(attribute_name)
            log_assertion("element_attribute", expected_value, actual_value, False)
            failure_message = message or f"Element attribute '{attribute_name}' assertion failed"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_have_class(
            self,
            class_name: str,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element has specific CSS class."""
        try:
            expect(self.locator).to_have_class(class_name, timeout=timeout or 30000)
            log_assertion("element_class", class_name, "found", True)
        except Exception as e:
            actual_classes = self.locator.get_attribute("class") or ""
            log_assertion("element_class", class_name, actual_classes, False)
            failure_message = message or f"Element should have class '{class_name}' but has classes '{actual_classes}'"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_be_enabled(
            self,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element is enabled."""
        try:
            expect(self.locator).to_be_enabled(timeout=timeout or 30000)
            log_assertion("element_enabled", True, True, True)
        except Exception as e:
            log_assertion("element_enabled", True, False, False)
            failure_message = message or "Element should be enabled but is disabled"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_be_disabled(
            self,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert element is disabled."""
        try:
            expect(self.locator).to_be_disabled(timeout=timeout or 30000)
            log_assertion("element_disabled", True, True, True)
        except Exception as e:
            log_assertion("element_disabled", True, False, False)
            failure_message = message or "Element should be disabled but is enabled"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self

    def should_have_count(
            self,
            expected_count: int,
            timeout: Optional[int] = None,
            message: Optional[str] = None
    ) -> "ElementAssertions":
        """Assert locator matches expected number of elements."""
        try:
            expect(self.locator).to_have_count(expected_count, timeout=timeout or 30000)
            log_assertion("element_count", expected_count, expected_count, True)
        except Exception as e:
            actual_count = self.locator.count()
            log_assertion("element_count", expected_count, actual_count, False)
            failure_message = message or f"Expected {expected_count} elements but found {actual_count}"
            raise ElementException(
                failure_message,
                original_exception=e
            )
        return self


class PerformanceAssertions:
    """
    Performance-related assertions for timing and resource usage.

    These assertions help validate performance requirements
    and catch performance regressions.
    """

    def __init__(self, page: Union[Page, AsyncPage]):
        """
        Initialize performance assertions.

        Args:
            page: Playwright page instance
        """
        self.page = page
        self.logger = get_logger("performance_assertions")
        self.settings = get_settings()

    def page_load_time_should_be_less_than(
            self,
            max_seconds: float,
            message: Optional[str] = None
    ) -> "PerformanceAssertions":
        """Assert page load time is within acceptable limits."""
        try:
            # Use Navigation Timing API to get load time
            load_time = self.page.evaluate("""
                () => {
                    const perfData = performance.getEntriesByType('navigation')[0];
                    return perfData ? perfData.loadEventEnd - perfData.navigationStart : 0;
                }
            """)

            load_time_seconds = load_time / 1000
            passed = load_time_seconds <= max_seconds

            log_assertion("page_load_time", f"<= {max_seconds}s", f"{load_time_seconds:.2f}s", passed)

            if not passed:
                failure_message = message or f"Page load time {load_time_seconds:.2f}s exceeds limit {max_seconds}s"
                raise TestAssertionException(
                    failure_message,
                    assertion_type="performance",
                    severity=ErrorSeverity.MEDIUM
                )

        except Exception as e:
            if isinstance(e, TestAssertionException):
                raise
            self.logger.warning(f"Could not measure page load time: {e}")

        return self

    def network_requests_should_be_less_than(
            self,
            max_requests: int,
            message: Optional[str] = None
    ) -> "PerformanceAssertions":
        """Assert number of network requests is reasonable."""
        try:
            # Get resource timing entries
            request_count = self.page.evaluate("""
                () => performance.getEntriesByType('resource').length
            """)

            passed = request_count <= max_requests

            log_assertion("network_requests", f"<= {max_requests}", request_count, passed)

            if not passed:
                failure_message = message or f"Page made {request_count} requests, exceeding limit {max_requests}"
                raise TestAssertionException(
                    failure_message,
                    assertion_type="performance",
                    severity=ErrorSeverity.LOW
                )

        except Exception as e:
            if isinstance(e, TestAssertionException):
                raise
            self.logger.warning(f"Could not measure network requests: {e}")

        return self


# Convenience functions for creating assertions
def assert_that(locator: Union[Locator, AsyncLocator],
                page: Optional[Union[Page, AsyncPage]] = None) -> ElementAssertions:
    """Create element assertions for locator."""
    return ElementAssertions(locator, page)


def soft_assert(page: Optional[Union[Page, AsyncPage]] = None) -> SoftAssertions:
    """Create soft assertions instance."""
    return SoftAssertions(page)


def assert_performance(page: Union[Page, AsyncPage]) -> PerformanceAssertions:
    """Create performance assertions for page."""
    return PerformanceAssertions(page)


# Decorator for automatic soft assertion checking
def with_soft_assertions(func):
    """Decorator that automatically creates and checks soft assertions."""

    def wrapper(*args, **kwargs):
        # Assume first argument has a page attribute (page object pattern)
        page = getattr(args[0], 'page', None) if args else None

        with soft_assert(page) as assertions:
            # Pass soft assertions to function
            kwargs['soft_assertions'] = assertions
            return func(*args, **kwargs)

    return wrapper
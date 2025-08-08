"""
Element-Related Exception Classes

This module defines exceptions specific to web element operations including
element location failures, interaction problems, state validation issues,
and element-specific timeouts.

Key Design Patterns:
- Detailed context for element debugging
- Smart selector suggestions for not found errors
- State machine aware exceptions
- Performance metrics for element operations

Interview Highlights:
- Comprehensive element error handling
- Selector analysis and suggestions
- DOM state awareness
- Cross-framework compatibility (Playwright, Selenium patterns)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta

from .base import AutomationException
from .enums import ErrorCategory, ErrorSeverity, RetryStrategy


class ElementException(AutomationException):
    """
    Base class for all element-related exceptions.

    This exception covers element interactions, location,
    and state validation issues.
    """

    def __init__(
            self,
            message: str,
            selector: Optional[str] = None,
            selector_type: Optional[str] = None,
            element_type: Optional[str] = None,
            page_url: Optional[str] = None,
            parent_selector: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize element exception with element-specific context.

        Args:
            message: Error description
            selector: Element selector used
            selector_type: Type of selector (css, xpath, text, etc.)
            element_type: HTML element type (button, input, div, etc.)
            page_url: Current page URL
            parent_selector: Parent element selector if nested
            **kwargs: Additional arguments for AutomationException
        """
        # Set element-specific defaults
        kwargs.setdefault('category', ErrorCategory.ELEMENT)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(message=message, **kwargs)

        # Store element information
        self.selector = selector
        self.selector_type = selector_type
        self.element_type = element_type
        self.page_url = page_url
        self.parent_selector = parent_selector

        # Add context
        if selector:
            self.add_context("selector", selector)
            self.add_context("selector_length", len(selector))
            self._analyze_selector(selector)

        if selector_type:
            self.add_context("selector_type", selector_type)
            self.add_tag(f"selector_{selector_type}")

        if element_type:
            self.add_context("element_type", element_type)
            self.add_tag(f"element_{element_type}")

        if page_url:
            self.add_context("page_url", page_url)

        if parent_selector:
            self.add_context("parent_selector", parent_selector)
            self.add_tag("nested_element")

        # Add common element recovery suggestions
        self._add_common_element_suggestions()

    def _analyze_selector(self, selector: str) -> None:
        """Analyze selector for potential issues."""
        # Check for common selector problems
        issues = []

        if len(selector) > 100:
            issues.append("very_long_selector")

        if selector.count(" ") > 5:
            issues.append("deeply_nested")

        if "nth-child" in selector or "nth-of-type" in selector:
            issues.append("position_dependent")

        if selector.startswith("//") or selector.startswith("("):
            self.add_tag("xpath_selector")
        elif selector.startswith("#"):
            self.add_tag("id_selector")
        elif selector.startswith("."):
            self.add_tag("class_selector")

        if issues:
            self.add_context("selector_issues", issues)
            for issue in issues:
                self.add_tag(f"selector_{issue}")

    def _add_common_element_suggestions(self) -> None:
        """Add common recovery suggestions for element issues."""
        self.add_recovery_suggestion("Verify element selector is correct")
        self.add_recovery_suggestion("Check if element is visible on the page")
        self.add_recovery_suggestion("Wait for page to load completely")
        self.add_recovery_suggestion("Verify element is not inside a frame/iframe")

        if self.parent_selector:
            self.add_recovery_suggestion("Check if parent element exists first")


class ElementNotFoundException(ElementException):
    """
    Exception for when elements cannot be located on the page.

    This exception is raised when element selectors don't match
    any elements in the DOM or when elements are not in the
    expected state for interaction.
    """

    def __init__(
            self,
            message: str,
            selector: str,
            timeout_used: Optional[int] = None,
            similar_selectors: Optional[List[str]] = None,
            found_count: int = 0,
            expected_count: Optional[int] = None,
            search_time_ms: Optional[float] = None,
            **kwargs
    ):
        """
        Initialize element not found exception.

        Args:
            message: Error description
            selector: Element selector that failed
            timeout_used: Wait timeout used in milliseconds
            similar_selectors: List of similar selectors to try
            found_count: Number of elements actually found
            expected_count: Expected number of elements
            search_time_ms: Time spent searching for element
            **kwargs: Additional exception arguments
        """
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Element not found: {message}",
            selector=selector,
            **kwargs
        )

        self.timeout_used = timeout_used
        self.similar_selectors = similar_selectors or []
        self.found_count = found_count
        self.expected_count = expected_count
        self.search_time_ms = search_time_ms

        # Add detailed context
        if timeout_used:
            self.add_context("timeout_used", timeout_used)
            if timeout_used < 5000:
                self.add_tag("short_timeout")

        if similar_selectors:
            self.add_context("similar_selectors", similar_selectors)
            self.add_context("alternatives_count", len(similar_selectors))

        self.add_context("found_count", found_count)

        if expected_count is not None:
            self.add_context("expected_count", expected_count)
            if found_count > 0:
                self.add_tag("partial_match")

        if search_time_ms:
            self.add_context("search_time_ms", search_time_ms)
            self.add_metadata("element_search_ms", search_time_ms)

        # Add specific recovery suggestions
        self._add_not_found_suggestions()

    def _add_not_found_suggestions(self) -> None:
        """Add not-found-specific recovery suggestions."""
        self.add_recovery_suggestion("Check if selector syntax is correct")
        self.add_recovery_suggestion("Verify element exists in current page state")

        if self.timeout_used and self.timeout_used < 10000:
            self.add_recovery_suggestion("Increase wait timeout for slow-loading elements")

        self.add_recovery_suggestion("Check if element is dynamically created")
        self.add_recovery_suggestion("Verify element is not removed by JavaScript")

        if self.similar_selectors:
            for i, alt_selector in enumerate(self.similar_selectors[:3], 1):
                self.add_recovery_suggestion(f"Try alternative selector {i}: {alt_selector}")

        if self.found_count > 0 and self.expected_count:
            if self.found_count < self.expected_count:
                self.add_recovery_suggestion(f"Found {self.found_count} elements, expected {self.expected_count}")
            else:
                self.add_recovery_suggestion(f"Found {self.found_count} elements, selector may be too broad")

        # Suggest selector improvements based on type
        if self.selector:
            if self.selector.startswith("//"):
                self.add_recovery_suggestion("Consider using CSS selector instead of XPath")
            elif " " in self.selector and not ">" in self.selector:
                self.add_recovery_suggestion("Consider using direct child selector (>) for better specificity")


class ElementInteractionException(ElementException):
    """
    Exception for element interaction failures.

    This exception is raised when elements are found but cannot
    be interacted with due to state, visibility, or other issues.
    """

    def __init__(
            self,
            message: str,
            interaction_type: str,
            selector: Optional[str] = None,
            element_state: Optional[Dict[str, Any]] = None,
            coordinates: Optional[Tuple[float, float]] = None,
            retry_count: int = 0,
            **kwargs
    ):
        """
        Initialize element interaction exception.

        Args:
            message: Error description
            interaction_type: Type of interaction (click, type, select, etc.)
            selector: Element selector
            element_state: Current element state (visible, enabled, etc.)
            coordinates: Element coordinates if available
            retry_count: Number of retries attempted
            **kwargs: Additional exception arguments
        """
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL_JITTER)

        super().__init__(
            message=f"Element interaction failed ({interaction_type}): {message}",
            selector=selector,
            **kwargs
        )

        self.interaction_type = interaction_type
        self.element_state = element_state or {}
        self.coordinates = coordinates
        self.retry_count = retry_count

        # Add interaction context
        self.add_context("interaction_type", interaction_type)
        self.add_tag(f"interaction_{interaction_type}")

        if element_state:
            self.add_context("element_state", element_state)
            self._analyze_element_state(element_state)

        if coordinates:
            self.add_context("coordinates", {"x": coordinates[0], "y": coordinates[1]})
            # Check if element might be off-screen
            if coordinates[0] < 0 or coordinates[1] < 0:
                self.add_tag("element_offscreen")

        if retry_count > 0:
            self.add_context("retry_count", retry_count)
            self.add_metadata("interaction_retries", retry_count)

        # Add interaction-specific suggestions
        self._add_interaction_suggestions()

    def _analyze_element_state(self, state: Dict[str, Any]) -> None:
        """Analyze element state for issues."""
        issues = []

        if not state.get("visible", True):
            issues.append("not_visible")
            self.add_tag("element_not_visible")

        if not state.get("enabled", True):
            issues.append("disabled")
            self.add_tag("element_disabled")

        if state.get("readonly", False):
            issues.append("readonly")
            self.add_tag("element_readonly")

        if state.get("covered", False):
            issues.append("covered_by_other_element")
            self.add_tag("element_covered")

        if state.get("animating", False):
            issues.append("still_animating")
            self.add_tag("element_animating")

        if issues:
            self.add_context("state_issues", issues)

    def _add_interaction_suggestions(self) -> None:
        """Add interaction-specific recovery suggestions."""
        interaction_suggestions = {
            "click": [
                "Check if element is clickable (not disabled/hidden)",
                "Try scrolling element into view",
                "Wait for animations or transitions to complete",
                "Check if element is covered by another element",
                "Try clicking with JavaScript as fallback"
            ],
            "type": [
                "Verify element is editable (input, textarea, contenteditable)",
                "Check if element is enabled and not readonly",
                "Clear existing text before typing new text",
                "Focus on element before typing",
                "Check for input validation preventing typing"
            ],
            "select": [
                "Verify element is a select dropdown",
                "Check if option values exist in the dropdown",
                "Wait for dropdown options to load",
                "Try selecting by different method (value, text, index)"
            ],
            "hover": [
                "Ensure element is visible and in viewport",
                "Check if element has hover handlers attached",
                "Wait for element to be stable (not moving)"
            ],
            "drag": [
                "Verify both source and target elements exist",
                "Check if elements support drag and drop",
                "Ensure elements are not overlapping incorrectly"
            ]
        }

        suggestions = interaction_suggestions.get(
            self.interaction_type.lower(),
            ["Verify element is ready for interaction"]
        )

        for suggestion in suggestions:
            self.add_recovery_suggestion(suggestion)

        # Add state-specific suggestions
        if self.element_state:
            if not self.element_state.get("visible", True):
                self.add_recovery_suggestion("Element is not visible - wait or scroll into view")
            if not self.element_state.get("enabled", True):
                self.add_recovery_suggestion("Element is disabled - check page state")
            if self.element_state.get("covered", False):
                self.add_recovery_suggestion("Element is covered - remove overlapping elements")


class ElementStateException(ElementException):
    """
    Exception for element state validation failures.

    This exception is raised when elements are in an unexpected
    state that prevents the desired operation or validation.
    """

    def __init__(
            self,
            message: str,
            expected_state: Dict[str, Any],
            actual_state: Dict[str, Any],
            selector: Optional[str] = None,
            state_check_duration_ms: Optional[float] = None,
            **kwargs
    ):
        """
        Initialize element state exception.

        Args:
            message: Error description
            expected_state: Expected element state
            actual_state: Actual element state
            selector: Element selector
            state_check_duration_ms: Time spent checking state
            **kwargs: Additional exception arguments
        """
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Element state mismatch: {message}",
            selector=selector,
            **kwargs
        )

        self.expected_state = expected_state
        self.actual_state = actual_state
        self.state_check_duration_ms = state_check_duration_ms

        # Add state context
        self.add_context("expected_state", expected_state)
        self.add_context("actual_state", actual_state)

        # Find state differences
        differences = self._find_state_differences(expected_state, actual_state)
        if differences:
            self.add_context("state_differences", differences)
            for diff in differences:
                self.add_tag(f"state_diff_{diff}")

        if state_check_duration_ms:
            self.add_context("state_check_duration_ms", state_check_duration_ms)
            self.add_metadata("state_check_ms", state_check_duration_ms)

        # Add state-specific suggestions
        self._add_state_suggestions(differences)

    def _find_state_differences(
            self,
            expected: Dict[str, Any],
            actual: Dict[str, Any]
    ) -> List[str]:
        """Find differences between expected and actual states."""
        differences = []

        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if actual_value != expected_value:
                differences.append(key)

        return differences

    def _add_state_suggestions(self, differences: List[str]) -> None:
        """Add state-specific recovery suggestions."""
        state_suggestions = {
            "visible": [
                "Wait for element to become visible",
                "Check if element is hidden by CSS or JavaScript",
                "Scroll element into viewport"
            ],
            "enabled": [
                "Wait for element to become enabled",
                "Check for form validation that might disable element",
                "Verify prerequisite conditions are met"
            ],
            "selected": [
                "Verify element supports selection (checkbox, radio, option)",
                "Check if selection is prevented by validation",
                "Wait for selection state to update"
            ],
            "checked": [
                "Verify element is a checkbox or radio button",
                "Check if element state is controlled by JavaScript",
                "Try clicking element to change checked state"
            ],
            "text": [
                "Wait for text content to update",
                "Check if text is loaded asynchronously",
                "Verify text is not hidden by CSS"
            ],
            "value": [
                "Wait for input value to update",
                "Check if value is set by JavaScript",
                "Verify input accepts the expected value"
            ]
        }

        # Add suggestions based on differences
        for diff in differences:
            suggestions = state_suggestions.get(diff, [])
            for suggestion in suggestions:
                self.add_recovery_suggestion(suggestion)

        # Generic suggestions
        self.add_recovery_suggestion("Wait for page/element state to update")
        self.add_recovery_suggestion("Check for JavaScript errors affecting element state")
        self.add_recovery_suggestion("Verify element isn't modified by dynamic content")


class ElementTimeoutException(ElementException):
    """
    Exception for element-related timeout operations.

    This exception is raised when element wait conditions
    exceed their configured timeout values.
    """

    def __init__(
            self,
            message: str,
            selector: str,
            wait_condition: str,
            timeout: int,
            polling_interval: Optional[int] = None,
            checks_performed: Optional[int] = None,
            **kwargs
    ):
        """
        Initialize element timeout exception.

        Args:
            message: Error description
            selector: Element selector
            wait_condition: Condition being waited for
            timeout: Timeout value in milliseconds
            polling_interval: Polling interval if applicable
            checks_performed: Number of checks performed
            **kwargs: Additional exception arguments
        """
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Element wait timeout: {message}",
            selector=selector,
            **kwargs
        )

        self.wait_condition = wait_condition
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.checks_performed = checks_performed

        # Add timeout context
        self.add_context("wait_condition", wait_condition)
        self.add_context("timeout", timeout)
        self.add_tag(f"wait_{wait_condition}")

        if polling_interval:
            self.add_context("polling_interval", polling_interval)

        if checks_performed:
            self.add_context("checks_performed", checks_performed)
            self.add_metadata("element_checks", checks_performed)

        # Calculate approximate wait duration
        if polling_interval and checks_performed:
            approx_duration = polling_interval * checks_performed
            self.add_context("approx_wait_duration", approx_duration)

        # Add timeout-specific suggestions
        self._add_timeout_suggestions()

    def _add_timeout_suggestions(self) -> None:
        """Add timeout-specific recovery suggestions."""
        self.add_recovery_suggestion("Increase timeout duration for this wait condition")

        if self.timeout < 10000:
            self.add_recovery_suggestion(f"Current timeout {self.timeout}ms may be too short")

        self.add_recovery_suggestion("Verify element loads correctly under this condition")

        wait_suggestions = {
            "visible": "Element may be permanently hidden - check CSS and JavaScript",
            "clickable": "Element may be disabled or covered - check page state",
            "present": "Element may not exist - verify selector and page content",
            "text": "Text may not appear - check async loading",
            "value": "Value may not change - check form logic",
            "enabled": "Element may stay disabled - check enabling conditions"
        }

        suggestion = wait_suggestions.get(
            self.wait_condition,
            "Check if wait condition can be met"
        )
        self.add_recovery_suggestion(suggestion)

        if self.polling_interval and self.polling_interval > 1000:
            self.add_recovery_suggestion("Consider reducing polling interval for faster detection")
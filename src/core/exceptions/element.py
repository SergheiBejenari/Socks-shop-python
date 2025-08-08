# src/core/exceptions/element/__init__.py
"""
Element Exception Package
"""

from .element_exception import ElementException
from .not_found_exception import ElementNotFoundException
from .interaction_exception import ElementInteractionException
from .state_exception import ElementStateException

__all__ = [
    "ElementException",
    "ElementNotFoundException",
    "ElementInteractionException",
    "ElementStateException"
]

# ========================================================================================
# src/core/exceptions/element/element_exception.py
"""
Base Element Exception Class - SOLID Implementation
"""

from typing import Optional

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
            element_type: Optional[str] = None,
            page_url: Optional[str] = None,
            **kwargs
    ):
        # Set element-specific defaults
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(message=message, **kwargs)

        self.selector = selector
        self.element_type = element_type
        self.page_url = page_url

        if selector:
            self.add_context("selector", selector)
        if element_type:
            self.add_context("element_type", element_type)
        if page_url:
            self.add_context("page_url", page_url)

    def _determine_category(self) -> ErrorCategory:
        """Return element error category."""
        return ErrorCategory.ELEMENT

    def _initialize_exception(self) -> None:
        """Initialize element-specific recovery suggestions."""
        self.add_recovery_suggestion("Verify element selector is correct")
        self.add_recovery_suggestion("Check if element is visible on the page")
        self.add_recovery_suggestion("Wait for page to load completely")
        self.add_recovery_suggestion("Verify element is not inside a frame/iframe")


# ========================================================================================
# src/core/exceptions/element/not_found_exception.py
"""
Element Not Found Exception - SRP Implementation
"""

from typing import Optional, List

from .element_exception import ElementException
from ..enums import ErrorSeverity, RetryStrategy


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
            **kwargs
    ):
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Element not found: {message}",
            selector=selector,
            **kwargs
        )

        self.timeout_used = timeout_used
        self.similar_selectors = similar_selectors or []

        if timeout_used:
            self.add_context("timeout_used", timeout_used)
        if similar_selectors:
            self.add_context("similar_selectors", similar_selectors)

    def _initialize_exception(self) -> None:
        """Initialize not-found-specific recovery suggestions."""
        super()._initialize_exception()

        self.add_recovery_suggestion("Check if selector syntax is correct")
        self.add_recovery_suggestion("Verify element exists in current page state")
        self.add_recovery_suggestion("Increase wait timeout for slow-loading elements")
        self.add_recovery_suggestion("Check if element is dynamically created")

        if self.similar_selectors:
            self.add_recovery_suggestion(f"Try similar selectors: {', '.join(self.similar_selectors)}")


# ========================================================================================
# src/core/exceptions/element/interaction_exception.py
"""
Element Interaction Exception - SRP Implementation
"""

from typing import Optional

from .element_exception import ElementException
from ..enums import ErrorSeverity, RetryStrategy


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
            element_state: Optional[str] = None,
            **kwargs
    ):
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL_JITTER)

        super().__init__(
            message=f"Element interaction failed ({interaction_type}): {message}",
            selector=selector,
            **kwargs
        )

        self.interaction_type = interaction_type
        self.element_state = element_state

        self.add_context("interaction_type", interaction_type)
        if element_state:
            self.add_context("element_state", element_state)

    def _initialize_exception(self) -> None:
        """Initialize interaction-specific recovery suggestions."""
        super()._initialize_exception()

        interaction_suggestions = {
            "click": [
                "Check if element is clickable (not disabled/hidden)",
                "Try scrolling element into view",
                "Wait for animations or transitions to complete",
                "Check if element is covered by another element"
            ],
            "type": [
                "Verify element is editable (input, textarea, contenteditable)",
                "Check if element is enabled and not readonly",
                "Clear existing text before typing new text",
                "Focus on element before typing"
            ],
            "select": [
                "Verify element is a select dropdown",
                "Check if option values exist in the dropdown",
                "Wait for dropdown options to load"
            ]
        }

        suggestions = interaction_suggestions.get(self.interaction_type.lower(), [])
        for suggestion in suggestions:
            self.add_recovery_suggestion(suggestion)


# ========================================================================================
# src/core/exceptions/element/state_exception.py
"""
Element State Exception - SRP Implementation
"""

from typing import Optional

from .element_exception import ElementException
from ..enums import ErrorSeverity, RetryStrategy


class ElementStateException(ElementException):
    """
    Exception for element state validation failures.

    This exception is raised when elements are in an unexpected
    state that prevents the desired operation or validation.
    """

    def __init__(
            self,
            message: str,
            expected_state: str,
            actual_state: str,
            selector: Optional[str] = None,
            **kwargs
    ):
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Element state mismatch: {message}",
            selector=selector,
            **kwargs
        )

        self.expected_state = expected_state
        self.actual_state = actual_state

        self.add_context("expected_state", expected_state)
        self.add_context("actual_state", actual_state)

    def _initialize_exception(self) -> None:
        """Initialize state-specific recovery suggestions."""
        super()._initialize_exception()

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
            ]
        }

        # Add suggestions based on expected state
        suggestions = state_suggestions.get(self.expected_state.lower(), [])
        for suggestion in suggestions:
            self.add_recovery_suggestion(suggestion)

        # Generic state suggestions
        self.add_recovery_suggestion("Wait for page/element state to update")
        self.add_recovery_suggestion("Check for JavaScript errors affecting element state")
        self.add_recovery_suggestion("Verify element isn't modified by dynamic content")
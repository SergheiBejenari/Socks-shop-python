# src/models/base.py
"""
Base Models and Common Types for Test Data

This module provides the foundation for all data models used throughout
the test automation framework. It demonstrates enterprise-level data
modeling with comprehensive validation and serialization.

Key Design Patterns:
- Domain Model Pattern: Rich domain objects with behavior
- Value Object Pattern: Immutable data structures
- Factory Pattern: Model creation with validation
- Builder Pattern: Complex object construction

Interview Highlights:
- Modern Pydantic v2 features and best practices
- Type-safe data modeling with comprehensive validation
- Serialization/deserialization with custom formats
- Integration-ready for APIs and databases
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field
)


class BaseEntity(BaseModel):
    """
    Base class for all domain entities.

    Provides common functionality like ID generation, timestamps,
    and serialization methods that all domain entities need.

    Features:
    - Automatic ID generation
    - Created/updated timestamps
    - Type-safe serialization
    - Validation hooks
    """

    model_config = ConfigDict(
        # Enable extra validation and assignment validation
        validate_assignment=True,
        extra="forbid",
        # Use enums by value for JSON serialization
        use_enum_values=True,
        # Populate by name for API compatibility
        populate_by_name=True,
        # Generate JSON schema for documentation
        json_schema_serialization_defaults_required=True
    )

    # Common entity fields
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the entity",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the entity was created",
        examples=["2024-01-15T10:30:00Z"]
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        description="When the entity was last updated",
        examples=["2024-01-15T15:45:30Z"]
    )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                # Try parsing common formats
                from dateutil.parser import parse
                return parse(v)
        return v

    @model_validator(mode="after")
    def validate_timestamps(self) -> "BaseEntity":
        """Ensure timestamp consistency."""
        if self.updated_at and self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self

    def touch(self) -> "BaseEntity":
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
        return self

    @computed_field
    @property
    def age_seconds(self) -> float:
        """Computed field: Age of entity in seconds."""
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds()

    def to_dict(self, include_computed: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary with options.

        Args:
            include_computed: Include computed fields

        Returns:
            Dict representation of the model
        """
        data = self.model_dump(mode="json")

        if include_computed:
            data["age_seconds"] = self.age_seconds

        return data

    def to_json_string(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json_string(cls, json_str: str) -> "BaseEntity":
        """Create instance from JSON string."""
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEntity":
        """Create instance from dictionary."""
        return cls.model_validate(data)


class Currency(str, Enum):
    """Supported currencies for the e-commerce platform."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"

    @classmethod
    def get_symbol(cls, currency: "Currency") -> str:
        """Get currency symbol."""
        symbols = {
            cls.USD: "$",
            cls.EUR: "€",
            cls.GBP: "£",
            cls.JPY: "¥"
        }
        return symbols.get(currency, currency.value)


class Money(BaseModel):
    """
    Value object for monetary amounts with currency.

    This class ensures type safety for financial calculations
    and provides currency conversion capabilities.
    """

    model_config = ConfigDict(frozen=True)  # Immutable value object

    amount: Decimal = Field(
        description="Monetary amount",
        ge=0,  # Non-negative amounts only
        decimal_places=2,
        examples=[29.99, 0.00, 1500.50]
    )

    currency: Currency = Field(
        default=Currency.USD,
        description="Currency code",
        examples=["USD", "EUR", "GBP"]
    )

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v) -> Decimal:
        """Convert to Decimal and validate."""
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @computed_field
    @property
    def formatted(self) -> str:
        """Formatted currency string."""
        symbol = Currency.get_symbol(self.currency)
        return f"{symbol}{self.amount:.2f}"

    def add(self, other: "Money") -> "Money":
        """Add two Money objects (same currency only)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency
        )

    def multiply(self, factor: Union[int, float, Decimal]) -> "Money":
        """Multiply amount by a factor."""
        if isinstance(factor, (int, float)):
            factor = Decimal(str(factor))

        return Money(
            amount=self.amount * factor,
            currency=self.currency
        )

    def __str__(self) -> str:
        return self.formatted


class Address(BaseModel):
    """
    Address value object with validation.

    Supports international addresses with proper validation
    for different countries and postal code formats.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace
        validate_assignment=True
    )

    street: str = Field(
        min_length=1,
        max_length=200,
        description="Street address",
        examples=["123 Main Street", "45 Oak Avenue Apt 2B"]
    )

    city: str = Field(
        min_length=1,
        max_length=100,
        description="City name",
        examples=["New York", "London", "Tokyo"]
    )

    state: Optional[str] = Field(
        default=None,
        max_length=50,
        description="State or province",
        examples=["CA", "New York", "Ontario"]
    )

    postal_code: str = Field(
        min_length=3,
        max_length=20,
        description="Postal or ZIP code",
        examples=["90210", "SW1A 1AA", "100-0001"]
    )

    country: str = Field(
        min_length=2,
        max_length=3,
        description="Country code (ISO 2 or 3 letter)",
        examples=["US", "GB", "JP", "USA", "GBR", "JPN"]
    )

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate and normalize country code."""
        v = v.upper()

        # Common country codes (could be expanded with a proper library)
        valid_codes = {
            "US", "USA", "GB", "GBR", "JP", "JPN",
            "DE", "DEU", "FR", "FRA", "IT", "ITA",
            "ES", "ESP", "CA", "CAN", "AU", "AUS"
        }

        if v not in valid_codes:
            raise ValueError(f"Invalid country code: {v}")

        return v

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str, info) -> str:
        """Basic postal code validation by country."""
        if not info.data:
            return v

        country = info.data.get("country", "").upper()

        # Basic patterns (could be expanded)
        if country in ["US", "USA"] and not v.replace("-", "").isdigit():
            raise ValueError("US postal codes must be numeric")

        return v

    @computed_field
    @property
    def formatted_address(self) -> str:
        """Formatted address string."""
        parts = [self.street, self.city]

        if self.state:
            parts.append(f"{self.state} {self.postal_code}")
        else:
            parts.append(self.postal_code)

        parts.append(self.country)

        return ", ".join(parts)

    def __str__(self) -> str:
        return self.formatted_address


class ContactInfo(BaseModel):
    """
    Contact information with validation.

    Supports various contact methods with appropriate validation
    for email addresses, phone numbers, and other contact details.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    email: Optional[str] = Field(
        default=None,
        max_length=254,  # RFC 5321 limit
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="Email address",
        examples=["john.doe@example.com", "user@company.co.uk"]
    )

    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Phone number",
        examples=["+1-555-123-4567", "020 7946 0958", "+81 3-1234-5678"]
    )

    mobile: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Mobile phone number",
        examples=["+1-555-987-6543", "07911 123456"]
    )

    @field_validator("phone", "mobile")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        """Basic phone number validation."""
        if not v:
            return v

        # Remove common separators for validation
        digits_only = ''.join(char for char in v if char.isdigit() or char == '+')

        if len(digits_only) < 10:
            raise ValueError("Phone number too short")

        if len(digits_only) > 15:  # ITU-T E.164 standard
            raise ValueError("Phone number too long")

        return v

    @model_validator(mode="after")
    def validate_contact_info(self) -> "ContactInfo":
        """Ensure at least one contact method is provided."""
        if not any([self.email, self.phone, self.mobile]):
            raise ValueError("At least one contact method must be provided")

        return self


class AuditInfo(BaseModel):
    """
    Audit information for tracking changes.

    Provides comprehensive audit trail for entities including
    who made changes, when, and from where.
    """

    created_by: Optional[str] = Field(
        default=None,
        description="Who created the entity",
        examples=["user123", "admin@company.com", "system"]
    )

    updated_by: Optional[str] = Field(
        default=None,
        description="Who last updated the entity"
    )

    created_from_ip: Optional[str] = Field(
        default=None,
        pattern=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$',
        description="IP address of creator",
        examples=["192.168.1.1", "2001:db8::1"]
    )

    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User agent string of the client"
    )

    source: Optional[str] = Field(
        default="api",
        description="Source system or interface",
        examples=["web", "mobile_app", "api", "admin_panel", "import"]
    )


class PaginationInfo(BaseModel):
    """
    Pagination information for API responses.

    Provides standard pagination metadata for collections
    following REST API best practices.
    """

    page: int = Field(
        ge=1,
        description="Current page number (1-based)",
        examples=[1, 5, 10]
    )

    page_size: int = Field(
        ge=1,
        le=1000,  # Reasonable upper limit
        description="Number of items per page",
        examples=[10, 25, 50, 100]
    )

    total_items: int = Field(
        ge=0,
        description="Total number of items",
        examples=[0, 42, 1500]
    )

    @computed_field
    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if self.total_items == 0:
            return 0
        return (self.total_items + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next_page(self) -> bool:
        """Whether there is a next page."""
        return self.page < self.total_pages

    @computed_field
    @property
    def has_previous_page(self) -> bool:
        """Whether there is a previous page."""
        return self.page > 1

    @computed_field
    @property
    def start_index(self) -> int:
        """Start index of items on current page (0-based)."""
        return (self.page - 1) * self.page_size

    @computed_field
    @property
    def end_index(self) -> int:
        """End index of items on current page (0-based)."""
        return min(self.start_index + self.page_size - 1, self.total_items - 1)


class ErrorInfo(BaseModel):
    """
    Structured error information for API responses.

    Provides consistent error reporting across all API endpoints
    with detailed debugging information.
    """

    error_code: str = Field(
        description="Machine-readable error code",
        examples=["VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"]
    )

    message: str = Field(
        description="Human-readable error message",
        examples=["Invalid email address", "Product not found", "Access denied"]
    )

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details",
        examples=[{"field": "email", "constraint": "format"}]
    )

    suggestion: Optional[str] = Field(
        default=None,
        description="Suggestion for resolving the error",
        examples=["Please provide a valid email address", "Try logging in again"]
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the error occurred"
    )


# Type aliases for common types
EntityId = str
EmailAddress = str
PhoneNumber = str
IPAddress = str
CountryCode = str
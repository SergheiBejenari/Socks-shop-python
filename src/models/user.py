# src/models/user.py
"""
User Domain Models

This module defines user-related models for the Sock Shop application,
including user accounts, authentication, and profile management.

Key Domain Concepts:
- User: Main user entity with authentication
- UserProfile: Extended user information
- UserCredentials: Authentication credentials
- UserPreferences: User settings and preferences

Interview Highlights:
- Domain-driven design with rich user models
- Security-conscious credential handling
- Comprehensive user profile modeling
- Type-safe user state management
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
    computed_field
)

from base import BaseEntity, Address, ContactInfo, AuditInfo


class UserRole(str, Enum):
    """User roles for access control."""

    CUSTOMER = "customer"
    ADMIN = "admin"
    MODERATOR = "moderator"
    GUEST = "guest"

    def get_permissions(self) -> Set[str]:
        """Get permissions for this role."""
        permission_map = {
            UserRole.GUEST: {"view_products", "view_categories"},
            UserRole.CUSTOMER: {
                "view_products", "view_categories", "place_orders",
                "view_own_orders", "manage_own_profile", "add_to_cart"
            },
            UserRole.MODERATOR: {
                "view_products", "view_categories", "moderate_reviews",
                "view_user_profiles", "manage_products"
            },
            UserRole.ADMIN: {
                "view_products", "view_categories", "place_orders",
                "view_own_orders", "manage_own_profile", "add_to_cart",
                "moderate_reviews", "view_user_profiles", "manage_products",
                "manage_users", "view_analytics", "system_admin"
            }
        }
        return permission_map.get(self, set())


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"

    @property
    def can_login(self) -> bool:
        """Check if user can log in with this status."""
        return self in [UserStatus.ACTIVE]

    @property
    def requires_verification(self) -> bool:
        """Check if status requires email verification."""
        return self == UserStatus.PENDING_VERIFICATION


class Gender(str, Enum):
    """Gender options."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class UserCredentials(BaseModel):
    """
    User authentication credentials with security best practices.

    This model handles sensitive authentication data with proper
    security considerations for password storage and validation.
    """

    model_config = ConfigDict(
        # Don't include credentials in string representation
        repr_include={"username"},
        validate_assignment=True
    )

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_.-]+$',
        description="Unique username",
        examples=["john_doe", "user123", "alice.smith"]
    )

    email: str = Field(
        max_length=254,
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="User's email address",
        examples=["john@example.com", "user@company.co.uk"]
    )

    password_hash: Optional[SecretStr] = Field(
        default=None,
        description="Hashed password (never store plaintext)",
        repr=False  # Never show in repr
    )

    salt: Optional[SecretStr] = Field(
        default=None,
        description="Password salt for hashing",
        repr=False  # Never show in repr
    )

    last_login: Optional[datetime] = Field(
        default=None,
        description="When user last logged in",
        examples=["2024-01-15T10:30:00Z"]
    )

    login_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of failed login attempts"
    )

    locked_until: Optional[datetime] = Field(
        default=None,
        description="Account locked until this time"
    )

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Additional email validation."""
        # Block common disposable email domains in production
        blocked_domains = {
            "tempmail.com", "10minutemail.com", "guerrillamail.com"
        }

        domain = v.split("@")[1].lower()
        if domain in blocked_domains:
            raise ValueError(f"Email domain {domain} is not allowed")

        return v.lower()  # Normalize to lowercase

    @model_validator(mode="after")
    def validate_lock_status(self) -> "UserCredentials":
        """Validate account lock status."""
        if self.locked_until and self.locked_until <= datetime.now(timezone.utc):
            # Lock has expired, reset login attempts
            self.locked_until = None
            self.login_attempts = 0

        return self

    @computed_field
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return self.locked_until > datetime.now(timezone.utc)

    def increment_login_attempts(self) -> None:
        """Increment failed login attempts and lock if necessary."""
        self.login_attempts += 1

        # Lock account after 5 failed attempts for 30 minutes
        if self.login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc).replace(
                minute=datetime.now(timezone.utc).minute + 30
            )

    def reset_login_attempts(self) -> None:
        """Reset login attempts after successful login."""
        self.login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)


class UserProfile(BaseModel):
    """
    Extended user profile information.

    Contains personal information, preferences, and non-authentication
    related user data.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    first_name: str = Field(
        min_length=1,
        max_length=50,
        description="User's first name",
        examples=["John", "Alice", "Bob"]
    )

    last_name: str = Field(
        min_length=1,
        max_length=50,
        description="User's last name",
        examples=["Doe", "Smith", "Johnson"]
    )

    display_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Public display name",
        examples=["Johnny", "Alice S.", "The Bob"]
    )

    date_of_birth: Optional[datetime] = Field(
        default=None,
        description="User's date of birth",
        examples=["1990-05-15"]
    )

    gender: Optional[Gender] = Field(
        default=None,
        description="User's gender"
    )

    bio: Optional[str] = Field(
        default=None,
        max_length=500,
        description="User biography or description"
    )

    avatar_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        pattern=r'^https?://.+',
        description="URL to user's avatar image",
        examples=["https://example.com/avatars/user123.jpg"]
    )

    # Contact information
    contact: ContactInfo = Field(
        default_factory=ContactInfo,
        description="Contact information"
    )

    # Address information
    addresses: List[Address] = Field(
        default_factory=list,
        description="User addresses (billing, shipping, etc.)",
        max_length=10  # Maximum 10 addresses per user
    )

    # Preferences
    newsletter_subscribed: bool = Field(
        default=False,
        description="Whether user is subscribed to newsletter"
    )

    marketing_emails: bool = Field(
        default=False,
        description="Whether user accepts marketing emails"
    )

    preferred_language: str = Field(
        default="en",
        pattern=r'^[a-z]{2}(-[A-Z]{2})?$',
        description="Preferred language (ISO 639-1 format)",
        examples=["en", "en-US", "fr", "de", "ja"]
    )

    timezone: str = Field(
        default="UTC",
        description="User's timezone",
        examples=["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate date of birth is reasonable."""
        if not v:
            return v

        now = datetime.now(timezone.utc)
        age_years = (now - v).days / 365.25

        if age_years < 13:
            raise ValueError("User must be at least 13 years old")

        if age_years > 150:
            raise ValueError("Invalid date of birth")

        return v

    @field_validator("display_name", mode="after")
    @classmethod
    def generate_display_name(cls, v: Optional[str], info) -> Optional[str]:
        """Generate display name if not provided."""
        if v:
            return v

        # Generate from first and last name
        if info.data:
            first = info.data.get("first_name", "")
            last = info.data.get("last_name", "")
            if first and last:
                return f"{first} {last[0]}."  # "John D."

        return v

    @computed_field
    @property
    def full_name(self) -> str:
        """Full name of the user."""
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def age(self) -> Optional[int]:
        """User's age in years."""
        if not self.date_of_birth:
            return None

        now = datetime.now(timezone.utc)
        return int((now - self.date_of_birth).days / 365.25)

    def get_primary_address(self) -> Optional[Address]:
        """Get the primary (first) address."""
        return self.addresses[0] if self.addresses else None

    def add_address(self, address: Address) -> None:
        """Add a new address."""
        if len(self.addresses) >= 10:
            raise ValueError("Maximum number of addresses reached")
        self.addresses.append(address)


class User(BaseEntity):
    """
    Main user entity combining credentials, profile, and system data.

    This is the aggregate root for the user domain, combining all
    user-related information with proper encapsulation and behavior.
    """

    # Authentication and system data
    credentials: UserCredentials = Field(
        description="User authentication credentials"
    )

    profile: UserProfile = Field(
        description="User profile information"
    )

    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        description="User's role in the system"
    )

    status: UserStatus = Field(
        default=UserStatus.PENDING_VERIFICATION,
        description="Current account status"
    )

    # System tracking
    audit: AuditInfo = Field(
        default_factory=AuditInfo,
        description="Audit information"
    )

    # Verification
    email_verified: bool = Field(
        default=False,
        description="Whether email has been verified"
    )

    phone_verified: bool = Field(
        default=False,
        description="Whether phone has been verified"
    )

    verification_token: Optional[str] = Field(
        default=None,
        description="Email verification token",
        repr=False  # Don't show in repr
    )

    # Analytics
    last_activity: Optional[datetime] = Field(
        default=None,
        description="When user was last active"
    )

    signup_source: Optional[str] = Field(
        default=None,
        description="Where user signed up from",
        examples=["web", "mobile_app", "social_google", "social_facebook"]
    )

    @model_validator(mode="after")
    def validate_user_state(self) -> "User":
        """Validate user state consistency."""
        # Email must be verified for active status
        if self.status == UserStatus.ACTIVE and not self.email_verified:
            raise ValueError("Active users must have verified email")

        # Ensure credentials email matches contact email
        if (self.profile.contact.email and
                self.profile.contact.email != self.credentials.email):
            raise ValueError("Contact email must match credentials email")

        return self

    @computed_field
    @property
    def permissions(self) -> Set[str]:
        """Get user permissions based on role."""
        return self.role.get_permissions()

    @computed_field
    @property
    def can_login(self) -> bool:
        """Check if user can log in."""
        return (
                self.status.can_login and
                not self.credentials.is_locked and
                self.email_verified
        )

    @computed_field
    @property
    def display_identifier(self) -> str:
        """Get user identifier for display."""
        if self.profile.display_name:
            return self.profile.display_name
        return self.profile.full_name

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def activate(self) -> None:
        """Activate user account after verification."""
        if not self.email_verified:
            raise ValueError("Cannot activate user without email verification")

        self.status = UserStatus.ACTIVE
        self.verification_token = None
        self.touch()

    def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend user account."""
        self.status = UserStatus.SUSPENDED
        if reason:
            self.audit.source = f"suspended: {reason}"
        self.touch()

    def verify_email(self, token: str) -> bool:
        """Verify email with token."""
        if self.verification_token != token:
            return False

        self.email_verified = True
        self.verification_token = None

        # Auto-activate if pending verification
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE

        self.touch()
        return True

    def update_last_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def change_role(self, new_role: UserRole, changed_by: Optional[str] = None) -> None:
        """Change user role (admin operation)."""
        old_role = self.role
        self.role = new_role

        if changed_by:
            self.audit.updated_by = changed_by
            self.audit.source = f"role_change: {old_role} -> {new_role}"

        self.touch()

    def to_public_dict(self) -> Dict[str, Any]:
        """
        Return public user data (safe for API responses).

        Excludes sensitive information like passwords, tokens, etc.
        """
        return {
            "id": self.id,
            "username": self.credentials.username,
            "display_name": self.display_identifier,
            "role": self.role.value,
            "status": self.status.value,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "profile": {
                "first_name": self.profile.first_name,
                "last_name": self.profile.last_name,
                "display_name": self.profile.display_name,
                "avatar_url": self.profile.avatar_url,
                "bio": self.profile.bio,
            }
        }

    @classmethod
    def create_new_user(
            cls,
            username: str,
            email: str,
            first_name: str,
            last_name: str,
            password_hash: str,
            salt: str,
            **kwargs
    ) -> "User":
        """
        Factory method to create a new user.

        Args:
            username: Unique username
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            password_hash: Hashed password
            salt: Password salt
            **kwargs: Additional user data

        Returns:
            User: New user instance
        """
        credentials = UserCredentials(
            username=username,
            email=email,
            password_hash=SecretStr(password_hash),
            salt=SecretStr(salt)
        )

        contact = ContactInfo(email=email)

        profile = UserProfile(
            first_name=first_name,
            last_name=last_name,
            contact=contact,
            **kwargs.get("profile", {})
        )

        verification_token = str(uuid4())

        return cls(
            credentials=credentials,
            profile=profile,
            status=UserStatus.PENDING_VERIFICATION,
            email_verified=False,
            verification_token=verification_token,
            audit=AuditInfo(
                created_by=kwargs.get("created_by", "system"),
                source=kwargs.get("source", "registration")
            ),
            **{k: v for k, v in kwargs.items() if k not in ["profile", "created_by", "source"]}
        )
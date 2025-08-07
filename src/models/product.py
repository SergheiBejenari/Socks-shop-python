# src/models/product.py
"""
Product Domain Models for Sock Shop

This module defines product-related models for the e-commerce application,
including products, categories, inventory, and pricing information.

Key Domain Concepts:
- Product: Main product entity with all details
- Category: Product categorization system
- ProductVariant: Size, color, style variations
- Inventory: Stock tracking and availability
- Pricing: Price management with discounts

Interview Highlights:
- Rich domain modeling for e-commerce products
- Complex product variant handling
- Inventory management with stock tracking
- Flexible pricing system with promotions
- Search and filtering capabilities
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field
)

from base import BaseEntity, Money


class ProductStatus(str, Enum):
    """Product availability status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"
    OUT_OF_STOCK = "out_of_stock"

    @property
    def is_available_for_purchase(self) -> bool:
        """Check if product can be purchased."""
        return self in [ProductStatus.ACTIVE]

    @property
    def is_visible_to_customers(self) -> bool:
        """Check if product should be shown to customers."""
        return self in [ProductStatus.ACTIVE, ProductStatus.OUT_OF_STOCK]


class SockSize(str, Enum):
    """Sock sizes for the Sock Shop."""

    XS = "xs"  # Extra Small
    S = "s"  # Small
    M = "m"  # Medium
    L = "l"  # Large
    XL = "xl"  # Extra Large
    XXL = "xxl"  # Double Extra Large

    @property
    def display_name(self) -> str:
        """Get display name for size."""
        size_names = {
            SockSize.XS: "Extra Small",
            SockSize.S: "Small",
            SockSize.M: "Medium",
            SockSize.L: "Large",
            SockSize.XL: "Extra Large",
            SockSize.XXL: "Double Extra Large"
        }
        return size_names[self]


class SockMaterial(str, Enum):
    """Sock materials available in the shop."""

    COTTON = "cotton"
    WOOL = "wool"
    SYNTHETIC = "synthetic"
    BAMBOO = "bamboo"
    SILK = "silk"
    BLEND = "blend"

    @property
    def description(self) -> str:
        """Get material description."""
        descriptions = {
            SockMaterial.COTTON: "Soft and breathable cotton",
            SockMaterial.WOOL: "Warm and moisture-wicking wool",
            SockMaterial.SYNTHETIC: "Durable synthetic material",
            SockMaterial.BAMBOO: "Eco-friendly bamboo fiber",
            SockMaterial.SILK: "Luxurious silk blend",
            SockMaterial.BLEND: "Mixed material blend"
        }
        return descriptions[self]


class Category(BaseEntity):
    """
    Product category for organizing products.

    Categories can be hierarchical with parent-child relationships
    to create a structured product taxonomy.
    """

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Category name",
        examples=["Men's Socks", "Athletic", "Dress Socks"]
    )

    slug: str = Field(
        min_length=1,
        max_length=100,
        pattern=r'^[a-z0-9-]+$',
        description="URL-friendly category identifier",
        examples=["mens-socks", "athletic", "dress-socks"]
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Category description"
    )

    parent_id: Optional[str] = Field(
        default=None,
        description="Parent category ID for hierarchical structure"
    )

    image_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        pattern=r'^https?://.+',
        description="Category image URL"
    )

    sort_order: int = Field(
        default=0,
        ge=0,
        description="Sort order for display"
    )

    is_featured: bool = Field(
        default=False,
        description="Whether category is featured on homepage"
    )

    seo_title: Optional[str] = Field(
        default=None,
        max_length=60,
        description="SEO page title"
    )

    seo_description: Optional[str] = Field(
        default=None,
        max_length=160,
        description="SEO meta description"
    )

    @field_validator("slug")
    @classmethod
    def validate_slug_uniqueness(cls, v: str) -> str:
        """Validate slug format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug must contain only alphanumeric characters and hyphens")
        return v.lower()

    @computed_field
    @property
    def full_path(self) -> str:
        """Get full category path for breadcrumbs."""
        # In a real implementation, this would traverse parent categories
        return self.name  # Simplified for now

    def get_breadcrumb_path(self) -> List[str]:
        """Get breadcrumb path as list of category names."""
        # In a real implementation, this would build full hierarchy
        return [self.name]


class ProductVariant(BaseModel):
    """
    Product variant representing different options (size, color, etc.).

    Each variant has its own SKU, pricing, and inventory tracking
    while sharing the base product information.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Variant unique identifier"
    )

    sku: str = Field(
        min_length=1,
        max_length=50,
        description="Stock Keeping Unit - unique product identifier",
        examples=["SOCK-COT-BLK-M", "SOCK-WOL-RED-L"]
    )

    size: SockSize = Field(
        description="Sock size"
    )

    color: str = Field(
        min_length=1,
        max_length=50,
        description="Color name",
        examples=["Black", "Navy Blue", "Heather Gray", "Bright Red"]
    )

    color_hex: Optional[str] = Field(
        default=None,
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Hex color code for display",
        examples=["#000000", "#FF0000", "#0066CC"]
    )

    material: SockMaterial = Field(
        description="Primary sock material"
    )

    price: Money = Field(
        description="Variant price"
    )

    compare_at_price: Optional[Money] = Field(
        default=None,
        description="Original price (for showing discounts)"
    )

    cost_price: Optional[Money] = Field(
        default=None,
        description="Cost price for margin calculations",
        repr=False  # Don't show in string representation
    )

    weight_grams: Optional[int] = Field(
        default=None,
        ge=0,
        le=1000,
        description="Product weight in grams"
    )

    barcode: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=13,
        description="UPC/EAN barcode"
    )

    @field_validator("sku")
    @classmethod
    def validate_sku_format(cls, v: str) -> str:
        """Validate SKU format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("SKU must contain only alphanumeric characters, hyphens, and underscores")
        return v.upper()

    @model_validator(mode="after")
    def validate_pricing(self) -> "ProductVariant":
        """Validate pricing relationships."""
        if self.compare_at_price and self.compare_at_price.currency != self.price.currency:
            raise ValueError("Compare price must use same currency as price")

        if self.compare_at_price and self.compare_at_price.amount <= self.price.amount:
            raise ValueError("Compare price must be higher than current price")

        if self.cost_price and self.cost_price.currency != self.price.currency:
            raise ValueError("Cost price must use same currency as price")

        return self

    @computed_field
    @property
    def is_on_sale(self) -> bool:
        """Check if variant is currently on sale."""
        return self.compare_at_price is not None

    @computed_field
    @property
    def discount_amount(self) -> Optional[Money]:
        """Calculate discount amount."""
        if not self.compare_at_price:
            return None

        discount = self.compare_at_price.amount - self.price.amount
        return Money(amount=discount, currency=self.price.currency)

    @computed_field
    @property
    def discount_percentage(self) -> Optional[int]:
        """Calculate discount percentage."""
        if not self.compare_at_price:
            return None

        discount_pct = ((self.compare_at_price.amount - self.price.amount) /
                        self.compare_at_price.amount) * 100
        return round(discount_pct)

    @computed_field
    @property
    def margin_percentage(self) -> Optional[int]:
        """Calculate profit margin percentage."""
        if not self.cost_price:
            return None

        if self.cost_price.amount == 0:
            return 100

        margin_pct = ((self.price.amount - self.cost_price.amount) /
                      self.price.amount) * 100
        return round(margin_pct)


class Inventory(BaseModel):
    """
    Inventory tracking for product variants.

    Manages stock levels, availability, and inventory movements
    with support for different inventory tracking policies.
    """

    model_config = ConfigDict(validate_assignment=True)

    variant_id: str = Field(
        description="Associated product variant ID"
    )

    quantity: int = Field(
        default=0,
        ge=0,
        description="Current stock quantity"
    )

    reserved_quantity: int = Field(
        default=0,
        ge=0,
        description="Quantity reserved for pending orders"
    )

    incoming_quantity: int = Field(
        default=0,
        ge=0,
        description="Quantity expected from incoming shipments"
    )

    minimum_quantity: int = Field(
        default=0,
        ge=0,
        description="Minimum stock level (reorder point)"
    )

    maximum_quantity: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum stock level"
    )

    track_inventory: bool = Field(
        default=True,
        description="Whether to track inventory for this variant"
    )

    allow_backorder: bool = Field(
        default=False,
        description="Allow orders when out of stock"
    )

    location: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Storage location (warehouse, shelf, etc.)"
    )

    supplier: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Primary supplier name"
    )

    last_restock_date: Optional[datetime] = Field(
        default=None,
        description="When inventory was last restocked"
    )

    @model_validator(mode="after")
    def validate_inventory_levels(self) -> "Inventory":
        """Validate inventory level relationships."""
        if self.reserved_quantity > self.quantity:
            raise ValueError("Reserved quantity cannot exceed available quantity")

        if self.maximum_quantity and self.maximum_quantity < self.minimum_quantity:
            raise ValueError("Maximum quantity must be greater than minimum quantity")

        return self

    @computed_field
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (not reserved)."""
        return self.quantity - self.reserved_quantity

    @computed_field
    @property
    def total_incoming_quantity(self) -> int:
        """Total quantity including incoming stock."""
        return self.quantity + self.incoming_quantity

    @computed_field
    @property
    def needs_restock(self) -> bool:
        """Check if inventory needs restocking."""
        return self.available_quantity <= self.minimum_quantity

    @computed_field
    @property
    def is_in_stock(self) -> bool:
        """Check if item is in stock and available."""
        if not self.track_inventory:
            return True  # Always available if not tracking

        return self.available_quantity > 0 or self.allow_backorder

    def reserve_stock(self, quantity: int) -> bool:
        """
        Reserve stock for an order.

        Args:
            quantity: Quantity to reserve

        Returns:
            bool: True if reservation successful
        """
        if quantity <= 0:
            return False

        if self.available_quantity >= quantity:
            self.reserved_quantity += quantity
            return True

        return False

    def release_stock(self, quantity: int) -> bool:
        """
        Release reserved stock.

        Args:
            quantity: Quantity to release

        Returns:
            bool: True if release successful
        """
        if quantity <= 0:
            return False

        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            return True

        return False

    def fulfill_stock(self, quantity: int) -> bool:
        """
        Fulfill an order by reducing available stock.

        Args:
            quantity: Quantity to fulfill

        Returns:
            bool: True if fulfillment successful
        """
        if quantity <= 0:
            return False

        if self.reserved_quantity >= quantity and self.quantity >= quantity:
            self.quantity -= quantity
            self.reserved_quantity -= quantity
            return True

        return False


class Product(BaseEntity):
    """
    Main product entity for the Sock Shop.

    This is the aggregate root that contains all product information
    including variants, pricing, inventory, and metadata.
    """

    # Basic product information
    name: str = Field(
        min_length=1,
        max_length=200,
        description="Product name",
        examples=["Classic Cotton Crew Socks", "Merino Wool Hiking Socks"]
    )

    slug: str = Field(
        min_length=1,
        max_length=200,
        pattern=r'^[a-z0-9-]+$',
        description="URL-friendly product identifier",
        examples=["classic-cotton-crew-socks", "merino-wool-hiking-socks"]
    )

    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Product description"
    )

    short_description: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Brief product summary for listings"
    )

    # Categorization
    category_id: str = Field(
        description="Primary category ID"
    )

    tags: List[str] = Field(
        default_factory=list,
        max_length=20,  # Max 20 tags
        description="Product tags for search and filtering",
        examples=[["comfortable", "breathable", "everyday"], ["athletic", "moisture-wicking", "cushioned"]]
    )

    # Product status and visibility
    status: ProductStatus = Field(
        default=ProductStatus.ACTIVE,
        description="Product status"
    )

    is_featured: bool = Field(
        default=False,
        description="Featured product flag"
    )

    # Media and images
    images: List[str] = Field(
        default_factory=list,
        max_length=10,  # Max 10 images
        description="Product image URLs",
        examples=[["https://example.com/sock1-front.jpg", "https://example.com/sock1-detail.jpg"]]
    )

    primary_image_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="Primary product image URL"
    )

    # Product variants (different sizes, colors, materials)
    variants: List[ProductVariant] = Field(
        default_factory=list,
        min_length=1,  # Must have at least one variant
        description="Product variants (size, color, material combinations)"
    )

    # SEO and metadata
    seo_title: Optional[str] = Field(
        default=None,
        max_length=60,
        description="SEO page title"
    )

    seo_description: Optional[str] = Field(
        default=None,
        max_length=160,
        description="SEO meta description"
    )

    # Product specifications
    brand: Optional[str] = Field(
        default="Sock Shop",
        max_length=100,
        description="Product brand"
    )

    care_instructions: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Care and washing instructions"
    )

    origin_country: Optional[str] = Field(
        default=None,
        max_length=2,
        pattern=r'^[A-Z]{2}$',
        description="Country of origin (ISO 2-letter code)"
    )

    # Analytics and performance
    view_count: int = Field(
        default=0,
        ge=0,
        description="Number of times product was viewed"
    )

    purchase_count: int = Field(
        default=0,
        ge=0,
        description="Number of times product was purchased"
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate and normalize slug."""
        return v.lower()

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v) -> List[str]:
        """Validate and normalize tags."""
        if isinstance(v, str):
            # Split string tags by comma
            tags = [tag.strip().lower() for tag in v.split(",") if tag.strip()]
        else:
            tags = [str(tag).strip().lower() for tag in v if str(tag).strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    @field_validator("images", mode="before")
    @classmethod
    def validate_images(cls, v) -> List[str]:
        """Validate image URLs."""
        if isinstance(v, str):
            return [v]

        valid_images = []
        for img in v:
            img_str = str(img).strip()
            if img_str and (img_str.startswith('http://') or img_str.startswith('https://')):
                valid_images.append(img_str)

        return valid_images

    @model_validator(mode="after")
    def validate_product_data(self) -> "Product":
        """Validate product data consistency."""
        # Ensure we have at least one variant
        if not self.variants:
            raise ValueError("Product must have at least one variant")

        # Validate SKU uniqueness within variants
        skus = [variant.sku for variant in self.variants]
        if len(skus) != len(set(skus)):
            raise ValueError("All variant SKUs must be unique")

        # Set primary image if not provided
        if not self.primary_image_url and self.images:
            self.primary_image_url = self.images[0]

        # Generate short description if not provided
        if not self.short_description and self.description:
            # Take first sentence or first 150 characters
            sentences = self.description.split('.')
            if sentences and len(sentences[0]) <= 150:
                self.short_description = sentences[0] + '.'
            else:
                self.short_description = self.description[:147] + '...'

        return self

    @computed_field
    @property
    def price_range(self) -> Dict[str, Money]:
        """Get price range across all variants."""
        if not self.variants:
            return {}

        prices = [variant.price for variant in self.variants]
        min_price = min(prices, key=lambda p: p.amount)
        max_price = max(prices, key=lambda p: p.amount)

        return {
            "min": min_price,
            "max": max_price
        }

    @computed_field
    @property
    def available_sizes(self) -> List[SockSize]:
        """Get list of available sizes."""
        return list(set(variant.size for variant in self.variants))

    @computed_field
    @property
    def available_colors(self) -> List[str]:
        """Get list of available colors."""
        return list(set(variant.color for variant in self.variants))

    @computed_field
    @property
    def available_materials(self) -> List[SockMaterial]:
        """Get list of available materials."""
        return list(set(variant.material for variant in self.variants))

    @computed_field
    @property
    def has_sale_variants(self) -> bool:
        """Check if any variants are on sale."""
        return any(variant.is_on_sale for variant in self.variants)

    def get_variant_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Find variant by SKU."""
        for variant in self.variants:
            if variant.sku == sku.upper():
                return variant
        return None

    def get_variants_by_size(self, size: SockSize) -> List[ProductVariant]:
        """Get all variants of a specific size."""
        return [v for v in self.variants if v.size == size]

    def get_variants_by_color(self, color: str) -> List[ProductVariant]:
        """Get all variants of a specific color."""
        color_lower = color.lower()
        return [v for v in self.variants if v.color.lower() == color_lower]

    def get_default_variant(self) -> Optional[ProductVariant]:
        """Get the default variant (lowest price, medium size preferred)."""
        if not self.variants:
            return None

        # Prefer medium size if available, otherwise cheapest
        medium_variants = [v for v in self.variants if v.size == SockSize.M]
        if medium_variants:
            return min(medium_variants, key=lambda v: v.price.amount)

        return min(self.variants, key=lambda v: v.price.amount)

    def increment_view_count(self) -> None:
        """Increment product view count."""
        self.view_count += 1
        self.touch()

    def increment_purchase_count(self, quantity: int = 1) -> None:
        """Increment product purchase count."""
        self.purchase_count += quantity
        self.touch()

    @classmethod
    def create_simple_product(
            cls,
            name: str,
            description: str,
            category_id: str,
            price: Money,
            sku: str,
            size: SockSize = SockSize.M,
            color: str = "Black",
            material: SockMaterial = SockMaterial.COTTON,
            **kwargs
    ) -> "Product":
        """
        Factory method to create a simple product with one variant.

        Args:
            name: Product name
            description: Product description
            category_id: Category ID
            price: Product price
            sku: Stock keeping unit
            size: Sock size
            color: Color name
            material: Sock material
            **kwargs: Additional product data

        Returns:
            Product: New product instance
        """
        # Generate slug from name
        slug = name.lower().replace(' ', '-').replace('_', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')

        # Create single variant
        variant = ProductVariant(
            sku=sku,
            size=size,
            color=color,
            material=material,
            price=price
        )

        return cls(
            name=name,
            slug=slug,
            description=description,
            category_id=category_id,
            variants=[variant],
            **kwargs
        )
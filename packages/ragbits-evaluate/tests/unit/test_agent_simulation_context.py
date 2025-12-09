"""Tests for agent simulation context models."""

from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext


class TestDomainContext:
    """Tests for DomainContext dataclass."""

    @staticmethod
    def test_domain_context_creation() -> None:
        """Test creating a DomainContext with all fields."""
        context = DomainContext(
            domain_type="retail",
            currency="SAR",
            locale="ar_SA",
            available_merchants=[{"name": "Store A"}, {"name": "Store B"}],
            available_products=[{"name": "Product 1"}, {"name": "Product 2"}],
            business_rules={"min_order": 50, "delivery_fee": 10},
        )

        assert context.domain_type == "retail"
        assert context.currency == "SAR"
        assert context.locale == "ar_SA"
        assert len(context.available_merchants) == 2
        assert len(context.available_products) == 2
        assert context.business_rules["min_order"] == 50

    @staticmethod
    def test_domain_context_defaults() -> None:
        """Test DomainContext with default values."""
        context = DomainContext(domain_type="food")

        assert context.domain_type == "food"
        assert context.currency == "USD"
        assert context.locale == "en_US"
        assert context.available_merchants == []
        assert context.available_products == []
        assert context.business_rules == {}

    @staticmethod
    def test_format_for_prompt_minimal() -> None:
        """Test format_for_prompt with minimal data."""
        context = DomainContext(domain_type="travel")

        output = context.format_for_prompt()

        assert "Domain: travel" in output
        assert "Currency: USD" in output
        assert "Locale: en_US" in output
        # Should not include merchants/products when empty
        assert "Available Merchants" not in output
        assert "Sample Products" not in output

    @staticmethod
    def test_format_for_prompt_with_business_rules() -> None:
        """Test format_for_prompt includes business rules."""
        context = DomainContext(
            domain_type="retail",
            currency="EUR",
            business_rules={"prices_include_vat": True, "free_shipping_above": 100},
        )

        output = context.format_for_prompt()

        assert "Domain: retail" in output
        assert "Currency: EUR" in output
        assert "Business Rules:" in output
        assert "prices_include_vat=True" in output
        assert "free_shipping_above=100" in output

    @staticmethod
    def test_format_for_prompt_with_merchants() -> None:
        """Test format_for_prompt includes merchants."""
        context = DomainContext(
            domain_type="food",
            available_merchants=[
                {"name": "Restaurant A"},
                {"name": "Restaurant B"},
                {"name": "Restaurant C"},
            ],
        )

        output = context.format_for_prompt()

        assert "Available Merchants:" in output
        assert "Restaurant A" in output
        assert "Restaurant B" in output
        assert "Restaurant C" in output

    @staticmethod
    def test_format_for_prompt_truncates_merchants() -> None:
        """Test format_for_prompt truncates long merchant lists."""
        merchants = [{"name": f"Store {i}"} for i in range(10)]
        context = DomainContext(
            domain_type="retail",
            available_merchants=merchants,
        )

        output = context.format_for_prompt()

        # Should show first 5
        assert "Store 0" in output
        assert "Store 4" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show Store 5-9
        assert "Store 5" not in output

    @staticmethod
    def test_format_for_prompt_with_products() -> None:
        """Test format_for_prompt includes products."""
        context = DomainContext(
            domain_type="groceries",
            available_products=[
                {"name": "Milk"},
                {"name": "Bread"},
                {"name": "Eggs"},
            ],
        )

        output = context.format_for_prompt()

        assert "Sample Products:" in output
        assert "Milk" in output
        assert "Bread" in output
        assert "Eggs" in output

    @staticmethod
    def test_format_for_prompt_truncates_products() -> None:
        """Test format_for_prompt truncates long product lists."""
        products = [{"name": f"Product {i}"} for i in range(15)]
        context = DomainContext(
            domain_type="retail",
            available_products=products,
        )

        output = context.format_for_prompt()

        # Should show first 10
        assert "Product 0" in output
        assert "Product 9" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show Product 10-14
        assert "Product 10" not in output

    @staticmethod
    def test_format_for_prompt_complete() -> None:
        """Test format_for_prompt with all fields populated."""
        context = DomainContext(
            domain_type="retail",
            currency="SAR",
            locale="ar_SA",
            available_merchants=[{"name": "Saudi Mall"}],
            available_products=[{"name": "Headphones"}],
            business_rules={"prices_in_local_currency": True},
        )

        output = context.format_for_prompt()

        assert "Domain: retail" in output
        assert "Currency: SAR" in output
        assert "Locale: ar_SA" in output
        assert "Saudi Mall" in output
        assert "Headphones" in output
        assert "prices_in_local_currency=True" in output

    @staticmethod
    def test_format_for_prompt_handles_dict_without_name() -> None:
        """Test format_for_prompt handles dicts without 'name' key."""
        context = DomainContext(
            domain_type="custom",
            available_merchants=[{"id": 1, "code": "ABC"}],
            available_products=[{"sku": "123"}],
        )

        output = context.format_for_prompt()

        # Should convert dict to string when no 'name' key
        assert "Available Merchants:" in output
        assert "Sample Products:" in output


class TestDataSnapshot:
    """Tests for DataSnapshot dataclass."""

    @staticmethod
    def test_data_snapshot_creation() -> None:
        """Test creating a DataSnapshot with all fields."""
        snapshot = DataSnapshot(
            merchants=[{"name": "Burger House"}, {"name": "Pizza Place"}],
            sample_products=[{"name": "Classic Burger"}, {"name": "Pepperoni Pizza"}],
            categories=["burgers", "pizza", "drinks"],
            max_price=50.0,
            min_price=5.0,
        )

        assert len(snapshot.merchants) == 2
        assert len(snapshot.sample_products) == 2
        assert len(snapshot.categories) == 3
        assert snapshot.max_price == 50.0
        assert snapshot.min_price == 5.0

    @staticmethod
    def test_data_snapshot_defaults() -> None:
        """Test DataSnapshot with default values."""
        snapshot = DataSnapshot()

        assert snapshot.merchants == []
        assert snapshot.sample_products == []
        assert snapshot.categories == []
        assert snapshot.max_price is None
        assert snapshot.min_price is None

    @staticmethod
    def test_format_for_prompt_empty() -> None:
        """Test format_for_prompt with empty data."""
        snapshot = DataSnapshot()

        output = snapshot.format_for_prompt()

        assert output == ""

    @staticmethod
    def test_format_for_prompt_with_merchants() -> None:
        """Test format_for_prompt includes merchants."""
        snapshot = DataSnapshot(
            merchants=[
                {"name": "Restaurant A"},
                {"name": "Restaurant B"},
            ],
        )

        output = snapshot.format_for_prompt()

        assert "Available merchants:" in output
        assert "Restaurant A" in output
        assert "Restaurant B" in output

    @staticmethod
    def test_format_for_prompt_truncates_merchants() -> None:
        """Test format_for_prompt truncates long merchant lists."""
        merchants = [{"name": f"Store {i}"} for i in range(20)]
        snapshot = DataSnapshot(merchants=merchants)

        output = snapshot.format_for_prompt(max_items=15)

        # Should show first 15
        assert "Store 0" in output
        assert "Store 14" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show Store 15-19
        assert "Store 15" not in output

    @staticmethod
    def test_format_for_prompt_with_products() -> None:
        """Test format_for_prompt includes products."""
        snapshot = DataSnapshot(
            sample_products=[
                {"name": "Burger"},
                {"name": "Fries"},
                {"name": "Soda"},
            ],
        )

        output = snapshot.format_for_prompt()

        assert "Sample products:" in output
        assert "Burger" in output
        assert "Fries" in output
        assert "Soda" in output

    @staticmethod
    def test_format_for_prompt_truncates_products() -> None:
        """Test format_for_prompt truncates long product lists."""
        products = [{"name": f"Product {i}"} for i in range(25)]
        snapshot = DataSnapshot(sample_products=products)

        output = snapshot.format_for_prompt(max_items=15)

        # Should show first 15
        assert "Product 0" in output
        assert "Product 14" in output
        # Should show "and X more"
        assert "and 10 more" in output
        # Should not show Product 15-24
        assert "Product 15" not in output

    @staticmethod
    def test_format_for_prompt_with_categories() -> None:
        """Test format_for_prompt includes categories."""
        snapshot = DataSnapshot(
            categories=["burgers", "pizza", "drinks", "desserts"],
        )

        output = snapshot.format_for_prompt()

        assert "Categories:" in output
        assert "burgers" in output
        assert "pizza" in output
        assert "drinks" in output
        assert "desserts" in output

    @staticmethod
    def test_format_for_prompt_truncates_categories() -> None:
        """Test format_for_prompt truncates long category lists."""
        categories = [f"category_{i}" for i in range(15)]
        snapshot = DataSnapshot(categories=categories)

        output = snapshot.format_for_prompt()

        # Should show first 10
        assert "category_0" in output
        assert "category_9" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show category_10-14
        assert "category_10" not in output

    @staticmethod
    def test_format_for_prompt_with_price_range() -> None:
        """Test format_for_prompt includes price range."""
        snapshot = DataSnapshot(
            max_price=100.0,
            min_price=10.0,
        )

        output = snapshot.format_for_prompt()

        assert "Price range:" in output
        assert "10" in output
        assert "100" in output

    @staticmethod
    def test_format_for_prompt_with_max_price_only() -> None:
        """Test format_for_prompt with max_price only uses 0 for min."""
        snapshot = DataSnapshot(max_price=50.0)

        output = snapshot.format_for_prompt()

        assert "Price range: 0 - 50.0" in output

    @staticmethod
    def test_format_for_prompt_complete() -> None:
        """Test format_for_prompt with all fields populated."""
        snapshot = DataSnapshot(
            merchants=[{"name": "Burger House"}],
            sample_products=[{"name": "Classic Burger"}, {"name": "Fries"}],
            categories=["burgers", "sides"],
            max_price=30.0,
            min_price=5.0,
        )

        output = snapshot.format_for_prompt()

        assert "Available merchants:" in output
        assert "Burger House" in output
        assert "Sample products:" in output
        assert "Classic Burger" in output
        assert "Fries" in output
        assert "Categories:" in output
        assert "burgers" in output
        assert "sides" in output
        assert "Price range:" in output

    @staticmethod
    def test_format_for_prompt_handles_dict_without_name() -> None:
        """Test format_for_prompt handles dicts without 'name' key."""
        snapshot = DataSnapshot(
            merchants=[{"id": 1, "code": "ABC"}],
            sample_products=[{"sku": "123"}],
        )

        output = snapshot.format_for_prompt()

        # Should convert dict to string when no 'name' key
        assert "Available merchants:" in output
        assert "Sample products:" in output

    @staticmethod
    def test_format_for_prompt_custom_max_items() -> None:
        """Test format_for_prompt respects custom max_items parameter."""
        merchants = [{"name": f"Store {i}"} for i in range(10)]
        snapshot = DataSnapshot(merchants=merchants)

        output = snapshot.format_for_prompt(max_items=3)

        # Should show first 3
        assert "Store 0" in output
        assert "Store 2" in output
        # Should show "and X more"
        assert "and 7 more" in output
        # Should not show Store 3+
        assert "Store 3" not in output

"""Tests for agent simulation context models."""

from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext


class TestDomainContext:
    """Tests for DomainContext dataclass."""

    @staticmethod
    def test_domain_context_creation() -> None:
        """Test creating a DomainContext with all fields."""
        context = DomainContext(
            domain_type="customer_support",
            locale="de_DE",
            metadata={"ticket_statuses": ["open", "pending", "resolved"], "priority_levels": 3},
        )

        assert context.domain_type == "customer_support"
        assert context.locale == "de_DE"
        assert context.metadata["ticket_statuses"] == ["open", "pending", "resolved"]
        assert context.metadata["priority_levels"] == 3

    @staticmethod
    def test_domain_context_defaults() -> None:
        """Test DomainContext with default values."""
        context = DomainContext(domain_type="search")

        assert context.domain_type == "search"
        assert context.locale == "en_US"
        assert context.metadata == {}

    @staticmethod
    def test_format_for_prompt_minimal() -> None:
        """Test format_for_prompt with minimal data."""
        context = DomainContext(domain_type="booking")

        output = context.format_for_prompt()

        assert "Domain: booking" in output
        assert "Locale: en_US" in output
        # Should not include metadata section when empty
        assert "Additional context" not in output

    @staticmethod
    def test_format_for_prompt_with_metadata() -> None:
        """Test format_for_prompt includes metadata."""
        context = DomainContext(
            domain_type="qa",
            locale="fr_FR",
            metadata={"max_response_length": 500, "allow_citations": True},
        )

        output = context.format_for_prompt()

        assert "Domain: qa" in output
        assert "Locale: fr_FR" in output
        assert "Additional context:" in output
        assert "max_response_length: 500" in output
        assert "allow_citations: True" in output

    @staticmethod
    def test_format_for_prompt_truncates_long_lists() -> None:
        """Test format_for_prompt truncates long lists in metadata."""
        long_list = [f"item_{i}" for i in range(20)]
        context = DomainContext(
            domain_type="search",
            metadata={"available_items": long_list},
        )

        output = context.format_for_prompt()

        # Should show first 15 (DEFAULT_MAX_ITEMS_IN_PROMPT)
        assert "item_0" in output
        assert "item_14" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show items beyond limit
        assert "item_15" not in output

    @staticmethod
    def test_format_for_prompt_non_list_metadata() -> None:
        """Test format_for_prompt handles non-list metadata values."""
        context = DomainContext(
            domain_type="assistant",
            metadata={
                "response_style": "formal",
                "max_turns": 10,
                "features_enabled": {"search": True, "calendar": False},
            },
        )

        output = context.format_for_prompt()

        assert "response_style: formal" in output
        assert "max_turns: 10" in output
        assert "features_enabled:" in output


class TestDataSnapshot:
    """Tests for DataSnapshot dataclass."""

    @staticmethod
    def test_data_snapshot_creation() -> None:
        """Test creating a DataSnapshot with all fields."""
        snapshot = DataSnapshot(
            entities={
                "topics": ["billing", "technical", "returns"],
                "users": [{"id": "u1", "name": "John"}, {"id": "u2", "name": "Jane"}],
            },
            description="Customer support knowledge base",
        )

        assert len(snapshot.entities["topics"]) == 3
        assert len(snapshot.entities["users"]) == 2
        assert snapshot.description == "Customer support knowledge base"

    @staticmethod
    def test_data_snapshot_defaults() -> None:
        """Test DataSnapshot with default values."""
        snapshot = DataSnapshot()

        assert snapshot.entities == {}
        assert snapshot.description == ""

    @staticmethod
    def test_format_for_prompt_empty() -> None:
        """Test format_for_prompt with empty data."""
        snapshot = DataSnapshot()

        output = snapshot.format_for_prompt()

        assert output == ""

    @staticmethod
    def test_format_for_prompt_with_description() -> None:
        """Test format_for_prompt includes description."""
        snapshot = DataSnapshot(
            description="Test dataset for QA system",
            entities={"documents": ["doc1", "doc2"]},
        )

        output = snapshot.format_for_prompt()

        assert "Context: Test dataset for QA system" in output

    @staticmethod
    def test_format_for_prompt_with_entities() -> None:
        """Test format_for_prompt includes entities."""
        snapshot = DataSnapshot(
            entities={
                "categories": ["electronics", "clothing", "books"],
                "locations": ["NYC", "LA", "Chicago"],
            },
        )

        output = snapshot.format_for_prompt()

        assert "categories:" in output
        assert "electronics" in output
        assert "clothing" in output
        assert "books" in output
        assert "locations:" in output
        assert "NYC" in output

    @staticmethod
    def test_format_for_prompt_truncates_entities() -> None:
        """Test format_for_prompt truncates long entity lists."""
        items = [f"item_{i}" for i in range(20)]
        snapshot = DataSnapshot(entities={"items": items})

        output = snapshot.format_for_prompt(max_items=15)

        # Should show first 15
        assert "item_0" in output
        assert "item_14" in output
        # Should show "and X more"
        assert "and 5 more" in output
        # Should not show items beyond limit
        assert "item_15" not in output

    @staticmethod
    def test_format_for_prompt_with_dict_entities() -> None:
        """Test format_for_prompt handles dict entities with 'name' key."""
        snapshot = DataSnapshot(
            entities={
                "agents": [
                    {"name": "Support Agent", "id": 1},
                    {"name": "Sales Agent", "id": 2},
                ],
            },
        )

        output = snapshot.format_for_prompt()

        assert "agents:" in output
        assert "Support Agent" in output
        assert "Sales Agent" in output

    @staticmethod
    def test_format_for_prompt_handles_dict_without_name() -> None:
        """Test format_for_prompt handles dicts without 'name' key."""
        snapshot = DataSnapshot(
            entities={
                "records": [{"id": 1, "code": "ABC"}, {"id": 2, "code": "DEF"}],
            },
        )

        output = snapshot.format_for_prompt()

        # Should convert dict to string when no 'name' key
        assert "records:" in output

    @staticmethod
    def test_format_for_prompt_skips_empty_entities() -> None:
        """Test format_for_prompt skips empty entity lists."""
        snapshot = DataSnapshot(
            entities={
                "filled": ["a", "b", "c"],
                "empty": [],
            },
        )

        output = snapshot.format_for_prompt()

        assert "filled:" in output
        # Empty list should not appear
        assert "empty:" not in output

    @staticmethod
    def test_format_for_prompt_custom_max_items() -> None:
        """Test format_for_prompt respects custom max_items parameter."""
        items = [f"item_{i}" for i in range(10)]
        snapshot = DataSnapshot(entities={"items": items})

        output = snapshot.format_for_prompt(max_items=3)

        # Should show first 3
        assert "item_0" in output
        assert "item_2" in output
        # Should show "and X more"
        assert "and 7 more" in output
        # Should not show item_3+
        assert "item_3" not in output

    @staticmethod
    def test_format_for_prompt_complete() -> None:
        """Test format_for_prompt with all fields populated."""
        snapshot = DataSnapshot(
            entities={
                "documents": [{"name": "FAQ"}, {"name": "Guide"}],
                "tags": ["important", "archived"],
            },
            description="Knowledge base snapshot",
        )

        output = snapshot.format_for_prompt()

        assert "Context: Knowledge base snapshot" in output
        assert "documents:" in output
        assert "FAQ" in output
        assert "Guide" in output
        assert "tags:" in output
        assert "important" in output
        assert "archived" in output

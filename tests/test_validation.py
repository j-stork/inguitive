"""Comprehensive tests for the form validation layer."""

import pytest
from fastapi.testclient import TestClient

from inguitive import (
    CustomValidator,
    FormSchema,
    ValidationError,
    create_app,
    field,
    validate_form,
)

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def simple_app():
    """Create a simple inguitive app for testing."""
    return create_app()


# =============================================================================
# 0. FormSchema Inheritance Tests
# =============================================================================

class TestFormSchemaInheritance:
    """Tests for FormSchema inheritance functionality."""

    class BaseUserSchema(FormSchema):
        """Base schema with common user fields."""
        username = field(str, required=True, min_length=3)
        email = field(str, required=True, regex=r'^[\w.-]+@[\w.-]+\.\w+$')

    class ExtendedUserSchema(BaseUserSchema):
        """Child schema that inherits from base and adds more fields."""
        first_name = field(str, required=True)
        last_name = field(str, required=True)

    class MultiLevelSchema(ExtendedUserSchema):
        """Grandchild schema testing multiple levels of inheritance."""
        age = field(int, default=18, min_value=0, max_value=150)

    class OverrideFieldSchema(BaseUserSchema):
        """Child schema that overrides a parent field."""
        username = field(str, required=True, min_length=5)  # More restrictive

    def test_child_inherits_parent_fields(self):
        """Child schema inherits all fields from parent."""
        schema = self.ExtendedUserSchema({
            "username": "john_doe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
        assert schema.is_valid
        assert schema.username == "john_doe"
        assert schema.email == "john@example.com"
        assert schema.first_name == "John"
        assert schema.last_name == "Doe"

    def test_child_missing_required_parent_field(self):
        """Child schema requires all inherited parent fields."""
        schema = self.ExtendedUserSchema({
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe"
            # Missing email (required field from parent)
        })
        assert not schema.is_valid
        assert "email" in schema.errors
        assert "required" in schema.errors["email"][0].lower()

    def test_parent_field_validation_enforced_in_child(self):
        """Parent field validation rules are enforced in child schemas."""
        schema = self.ExtendedUserSchema({
            "username": "jo",  # Too short for parent's min_length=3
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
        assert not schema.is_valid
        assert "username" in schema.errors
        assert "3 characters" in schema.errors["username"][0]

    def test_multiple_inheritance_levels(self):
        """Multiple levels of inheritance work correctly."""
        schema = self.MultiLevelSchema({
            "username": "john_doe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "age": "25"
        })
        assert schema.is_valid
        assert schema.username == "john_doe"
        assert schema.email == "john@example.com"
        assert schema.first_name == "John"
        assert schema.last_name == "Doe"
        assert schema.age == 25

    def test_field_override_in_child(self):
        """Child field overrides parent field with same name."""
        # Child requires min_length=5, parent only required min_length=3
        schema = self.OverrideFieldSchema({
            "username": "john",  # Valid for parent (>=3) but not child (>=5)
            "email": "john@example.com"
        })
        assert not schema.is_valid
        assert "username" in schema.errors
        assert "5 characters" in schema.errors["username"][0]

        # Now try with valid length
        schema = self.OverrideFieldSchema({
            "username": "john_doe",  # Valid for child (>=5)
            "email": "john@example.com"
        })
        assert schema.is_valid
        assert schema.username == "john_doe"

    def test_child_schema_has_all_parent_fields(self):
        """Child schema _fields contains all parent fields."""
        assert "username" in self.ExtendedUserSchema._fields
        assert "email" in self.ExtendedUserSchema._fields
        assert "first_name" in self.ExtendedUserSchema._fields
        assert "last_name" in self.ExtendedUserSchema._fields

    def test_multi_level_schema_has_all_fields(self):
        """Multi-level schema has fields from all ancestor classes."""
        expected_fields = {"username", "email", "first_name", "last_name", "age"}
        actual_fields = set(self.MultiLevelSchema._fields.keys())
        assert actual_fields == expected_fields

    def test_override_schema_uses_child_field_definition(self):
        """Overridden field uses child's field definition, not parent's."""
        parent_username_field = self.BaseUserSchema._fields["username"]
        child_username_field = self.OverrideFieldSchema._fields["username"]

        # They should be different objects (child overrides parent)
        assert parent_username_field is not child_username_field

        # Verify child field enforces its own rules (min_length=5)
        # "john" is 4 chars, which would pass parent's min_length=3 but fail child's min_length=5
        schema = self.OverrideFieldSchema({"username": "john", "email": "john@example.com"})
        assert not schema.is_valid
        assert "username" in schema.errors
        assert "5 characters" in schema.errors["username"][0]

        # "john_doe" is 8 chars, which passes both
        schema = self.OverrideFieldSchema({"username": "john_doe", "email": "john@example.com"})
        assert schema.is_valid

    def test_multiple_inheritance_conflict_resolution(self):
        """Multiple inheritance with conflicting fields: first base in MRO wins."""
        # Create base classes with conflicting field definitions
        class BaseA(FormSchema):
            x = field(str, min_length=1)  # Less restrictive

        class BaseB(BaseA):
            x = field(str, min_length=5)  # More restrictive
            y = field(str, required=True)

        class BaseC(BaseA):
            x = field(str, min_length=3)  # Medium restrictive
            z = field(str, required=True)

        # D inherits from B then C - B should win conflicts due to MRO
        class D(BaseB, BaseC):
            pass

        # Verify D has all fields from B and C
        assert "x" in D._fields
        assert "y" in D._fields
        assert "z" in D._fields

        # Verify D's x field uses B's stricter validation (min_length=5)
        d_schema = D({"x": "abc", "y": "test", "z": "test"})
        assert not d_schema.is_valid
        assert "x" in d_schema.errors
        assert "5 characters" in d_schema.errors["x"][0]

        # Now try with x that satisfies B's min_length=5
        d_schema = D({"x": "abcdef", "y": "test", "z": "test"})
        assert d_schema.is_valid


# =============================================================================
# 1. Type Coercion Tests
# =============================================================================

class TestTypeCoercion:
    """Tests for type coercion from string form data to Python types."""

    class StringSchema(FormSchema):
        name = field(str)

    class IntSchema(FormSchema):
        count = field(int)

    class FloatSchema(FormSchema):
        price = field(float)

    class BoolSchema(FormSchema):
        active = field(bool)

    def test_string_fields_remain_strings(self):
        """String fields remain strings."""
        schema = self.StringSchema({"name": "test_value"})
        assert schema.name == "test_value"
        assert isinstance(schema.name, str)
        assert schema.is_valid

    def test_string_field_with_whitespace_is_stripped(self):
        """String fields are stripped of leading/trailing whitespace."""
        schema = self.StringSchema({"name": "  test  "})
        assert schema.name == "test"
        assert schema.is_valid

    def test_string_field_with_empty_string(self):
        """Empty string becomes default (empty string)."""
        schema = self.StringSchema({"name": ""})
        assert schema.name == ""
        assert schema.is_valid

    def test_int_coercion_from_string(self):
        """Integer fields coerce from string to int."""
        schema = self.IntSchema({"count": "42"})
        assert schema.count == 42
        assert isinstance(schema.count, int)
        assert schema.is_valid

    def test_int_coercion_from_negative_string(self):
        """Integer fields handle negative numbers."""
        schema = self.IntSchema({"count": "-10"})
        assert schema.count == -10
        assert schema.is_valid

    def test_int_coercion_from_empty_string_uses_default(self):
        """Empty string for int field uses default (0)."""
        schema = self.IntSchema({"count": ""})
        assert schema.count == 0
        assert schema.is_valid

    def test_int_coercion_with_invalid_string_uses_default(self):
        """Invalid string for int field uses default."""
        schema = self.IntSchema({"count": "not_a_number"})
        assert schema.count == 0
        assert schema.is_valid

    def test_int_coercion_with_custom_default(self):
        """Int field with custom default uses it for invalid input."""
        class CustomIntSchema(FormSchema):
            count = field(int, default=100)

        schema = CustomIntSchema({"count": "invalid"})
        assert schema.count == 100

    def test_float_coercion_from_string(self):
        """Float fields coerce from string to float."""
        schema = self.FloatSchema({"price": "3.14"})
        assert schema.price == 3.14
        assert isinstance(schema.price, float)
        assert schema.is_valid

    def test_float_coercion_from_scientific_notation(self):
        """Float fields handle scientific notation."""
        schema = self.FloatSchema({"price": "1.5e2"})
        assert schema.price == 150.0
        assert schema.is_valid

    def test_float_coercion_from_empty_string_uses_default(self):
        """Empty string for float field uses default (0.0)."""
        schema = self.FloatSchema({"price": ""})
        assert schema.price == 0.0
        assert schema.is_valid

    def test_bool_coercion_truthy_values(self):
        """Boolean fields coerce truthy string values correctly."""
        truthy_values = ["true", "True", "TRUE", "1", "on", "On", "ON", "yes", "Yes", "YES", "y", "Y"]
        for value in truthy_values:
            schema = self.BoolSchema({"active": value})
            assert schema.active is True
            assert schema.is_valid

    def test_bool_coercion_falsy_values(self):
        """Boolean fields coerce falsy string values correctly."""
        falsy_values = ["false", "False", "FALSE", "0", "off", "Off", "OFF", "no", "No", "NO", "n", "N", ""]
        for value in falsy_values:
            schema = self.BoolSchema({"active": value})
            assert schema.active is False
            assert schema.is_valid

    def test_bool_coercion_with_custom_default(self):
        """Boolean field with custom default uses it."""
        class CustomBoolSchema(FormSchema):
            active = field(bool, default=True)

        schema = CustomBoolSchema({"active": "invalid"})
        assert schema.active is True

    def test_bool_coercion_unknown_value_defaults_to_false(self):
        """Unknown boolean string values default to False."""
        schema = self.BoolSchema({"active": "maybe"})
        assert schema.active is False


# =============================================================================
# 2. Required Field Tests
# =============================================================================

class TestRequiredFieldValidation:
    """Tests for required field validation."""

    class RequiredStringSchema(FormSchema):
        name = field(str, required=True)

    class OptionalStringSchema(FormSchema):
        name = field(str, required=False)

    class RequiredIntSchema(FormSchema):
        count = field(int, required=True)

    def test_required_field_present_and_valid(self):
        """Required field present and valid passes validation."""
        schema = self.RequiredStringSchema({"name": "test"})
        assert schema.is_valid
        assert schema.name == "test"

    def test_required_field_missing(self):
        """Required field missing results in ValidationError."""
        schema = self.RequiredStringSchema({})
        assert not schema.is_valid
        assert "name" in schema.errors
        assert "required" in schema.errors["name"][0].lower()

    def test_required_field_empty_string(self):
        """Required field with empty string results in ValidationError."""
        schema = self.RequiredStringSchema({"name": ""})
        assert not schema.is_valid
        assert "name" in schema.errors

    def test_required_field_whitespace_only(self):
        """Required field with whitespace only results in ValidationError."""
        schema = self.RequiredStringSchema({"name": "   "})
        assert not schema.is_valid
        assert "name" in schema.errors

    def test_required_field_with_custom_error_message(self):
        """Required field with custom error message uses it."""
        class CustomErrorSchema(FormSchema):
            name = field(str, required=True, error_message="Name is required!")

        schema = CustomErrorSchema({})
        assert not schema.is_valid
        assert schema.errors["name"][0] == "Name is required!"

    def test_optional_field_missing_uses_default(self):
        """Optional field missing uses default value."""
        schema = self.OptionalStringSchema({})
        assert schema.is_valid
        assert schema.name is None  # default for field(str) is None

    def test_optional_field_with_custom_default(self):
        """Optional field with custom default uses it."""
        class CustomDefaultSchema(FormSchema):
            name = field(str, default="default_name")

        schema = CustomDefaultSchema({})
        assert schema.is_valid
        assert schema.name == "default_name"

    def test_required_int_field_missing(self):
        """Required int field missing results in ValidationError."""
        schema = self.RequiredIntSchema({})
        assert not schema.is_valid
        assert "count" in schema.errors

    def test_required_int_field_zero_is_valid(self):
        """Required int field with 0 is valid."""
        schema = self.RequiredIntSchema({"count": "0"})
        assert schema.is_valid
        assert schema.count == 0


# =============================================================================
# 3. Validator Tests
# =============================================================================

class TestBuiltInValidators:
    """Tests for built-in validators."""

    class MinLengthSchema(FormSchema):
        text = field(str, min_length=5)

    class MaxLengthSchema(FormSchema):
        text = field(str, max_length=5)

    class MinValueSchema(FormSchema):
        value = field(int, min_value=10)

    class MaxValueSchema(FormSchema):
        value = field(int, max_value=10)

    class RegexSchema(FormSchema):
        email = field(str, regex=r'^[\w.-]+@[\w.-]+\.\w+$')

    class CombinedValidatorsSchema(FormSchema):
        password = field(str, min_length=8, max_length=20, regex=r'^[a-zA-Z0-9]+$')

    def test_min_length_validator_passes(self):
        """MinLength validator passes for long enough strings."""
        schema = self.MinLengthSchema({"text": "hello"})
        assert schema.is_valid

    def test_min_length_validator_fails(self):
        """MinLength validator fails for short strings."""
        schema = self.MinLengthSchema({"text": "hi"})
        assert not schema.is_valid
        assert "text" in schema.errors
        assert "5 characters" in schema.errors["text"][0]

    def test_max_length_validator_passes(self):
        """MaxLength validator passes for short enough strings."""
        schema = self.MaxLengthSchema({"text": "hi"})
        assert schema.is_valid

    def test_max_length_validator_fails(self):
        """MaxLength validator fails for long strings."""
        schema = self.MaxLengthSchema({"text": "hello world"})
        assert not schema.is_valid
        assert "text" in schema.errors
        assert "5 characters" in schema.errors["text"][0]

    def test_min_value_validator_passes(self):
        """MinValue validator passes for large enough numbers."""
        schema = self.MinValueSchema({"value": "15"})
        assert schema.is_valid

    def test_min_value_validator_fails(self):
        """MinValue validator fails for small numbers."""
        schema = self.MinValueSchema({"value": "5"})
        assert not schema.is_valid
        assert "value" in schema.errors
        assert "10" in schema.errors["value"][0]

    def test_max_value_validator_passes(self):
        """MaxValue validator passes for small enough numbers."""
        schema = self.MaxValueSchema({"value": "5"})
        assert schema.is_valid

    def test_max_value_validator_fails(self):
        """MaxValue validator fails for large numbers."""
        schema = self.MaxValueSchema({"value": "15"})
        assert not schema.is_valid
        assert "value" in schema.errors
        assert "10" in schema.errors["value"][0]

    def test_regex_validator_passes(self):
        """Regex validator passes for matching patterns."""
        schema = self.RegexSchema({"email": "test@example.com"})
        assert schema.is_valid

    def test_regex_validator_fails(self):
        """Regex validator fails for non-matching patterns."""
        schema = self.RegexSchema({"email": "not-an-email"})
        assert not schema.is_valid
        assert "email" in schema.errors

    def test_multiple_validators_on_same_field(self):
        """Multiple validators on same field all run."""
        schema = self.CombinedValidatorsSchema({"password": "short"})
        assert not schema.is_valid
        assert "password" in schema.errors
        # Should have multiple errors
        assert len(schema.errors["password"]) >= 1

    def test_multiple_validators_all_pass(self):
        """Multiple validators all pass for valid input."""
        schema = self.CombinedValidatorsSchema({"password": "validpassword123"})
        assert schema.is_valid


class TestCustomValidators:
    """Tests for custom validators."""

    def test_custom_validator_function(self):
        """Custom validator function works correctly."""

        def is_even(value):
            if not isinstance(value, int):
                return False
            return value % 2 == 0

        class EvenNumberSchema(FormSchema):
            number = field(int, validators=[CustomValidator(is_even, "Must be even")])

        schema = EvenNumberSchema({"number": "4"})
        assert schema.is_valid

        schema = EvenNumberSchema({"number": "3"})
        assert not schema.is_valid
        assert "number" in schema.errors

    def test_custom_validator_returns_error_string(self):
        """Custom validator can return error string."""

        def validate_positive(value):
            if isinstance(value, int) and value < 0:
                return "Must be positive"
            return True

        class PositiveSchema(FormSchema):
            value = field(int, validators=[CustomValidator(validate_positive)])

        schema = PositiveSchema({"value": "-5"})
        assert not schema.is_valid
        assert schema.errors["value"][0] == "Must be positive"

    def test_custom_validator_exception_handled(self):
        """Custom validator exceptions are caught and converted to error messages."""

        def buggy_validator(value):
            raise ValueError("Something went wrong")

        class BuggySchema(FormSchema):
            value = field(str, validators=[CustomValidator(buggy_validator)])

        schema = BuggySchema({"value": "test"})
        assert not schema.is_valid
        assert "value" in schema.errors

    def test_multiple_custom_validators(self):
        """Multiple custom validators work together."""

        def is_positive(value):
            return isinstance(value, int) and value > 0

        def is_less_than_100(value):
            return isinstance(value, int) and value < 100

        class RangeSchema(FormSchema):
            number = field(
                int,
                validators=[
                    CustomValidator(is_positive, "Must be positive"),
                    CustomValidator(is_less_than_100, "Must be less than 100"),
                ],
            )

        schema = RangeSchema({"number": "50"})
        assert schema.is_valid

        schema = RangeSchema({"number": "-5"})
        assert not schema.is_valid

        schema = RangeSchema({"number": "150"})
        assert not schema.is_valid


# =============================================================================
# 4. Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and ValidationError class."""

    class ErrorSchema(FormSchema):
        name = field(str, required=True)
        age = field(int, required=True, min_value=0, max_value=150)
        email = field(str, required=True, regex=r'.*@.*')

    def test_single_field_error(self):
        """Single field error is captured correctly."""
        schema = self.ErrorSchema({"name": "test", "age": "20", "email": "invalid"})
        assert not schema.is_valid
        assert "email" in schema.errors
        assert "name" not in schema.errors
        assert "age" not in schema.errors

    def test_multiple_field_errors(self):
        """Multiple field errors are all captured."""
        schema = self.ErrorSchema({})  # All fields missing or invalid
        assert not schema.is_valid
        assert len(schema.errors) >= 2

    def test_error_message_customization(self):
        """Custom error messages are used."""

        class CustomErrorSchema(FormSchema):
            name = field(str, required=True, error_message="Please provide your name")
            age = field(int, min_value=0, error_message="Age cannot be negative")

        schema = CustomErrorSchema({})
        assert not schema.is_valid
        assert "name" in schema.errors
        assert schema.errors["name"][0] == "Please provide your name"

    def test_validation_error_exception_structure(self):
        """ValidationError exception has correct structure."""
        schema = self.ErrorSchema({})
        try:
            schema.validate()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert isinstance(e.errors, dict)
            assert len(e.errors) > 0
            # Test string representation
            assert "Validation failed" in str(e)

    def test_validation_error_first_error(self):
        """ValidationError.first_error() returns first error."""
        schema = self.ErrorSchema({})
        try:
            schema.validate()
        except ValidationError as e:
            assert e.first_error() is not None
            assert isinstance(e.first_error(), str)

    def test_validation_error_first_error_for_field(self):
        """ValidationError.first_error(field) returns error for specific field."""
        schema = self.ErrorSchema({})
        try:
            schema.validate()
        except ValidationError as e:
            name_error = e.first_error("name")
            assert name_error is not None
            assert "name" in name_error.lower() or "required" in name_error.lower()

    def test_validation_error_has_errors(self):
        """ValidationError.has_errors() checks for errors."""
        schema = self.ErrorSchema({})
        try:
            schema.validate()
        except ValidationError as e:
            assert e.has_errors() is True
            assert e.has_errors("name") is True
            # age might not have error if not required
            # But name should have error

    def test_validation_error_repr(self):
        """ValidationError has useful repr."""
        schema = self.ErrorSchema({})
        try:
            schema.validate()
        except ValidationError as e:
            assert "ValidationError" in repr(e)

    def test_errors_property_returns_copy(self):
        """errors property returns a copy, not the original."""
        schema = self.ErrorSchema({})
        errors = schema.errors
        errors["new_field"] = ["new error"]
        assert "new_field" not in schema.errors

    def test_is_valid_property(self):
        """is_valid property correctly reports validation status."""
        valid_schema = self.ErrorSchema({"name": "test", "age": "25", "email": "test@example.com"})
        assert valid_schema.is_valid is True

        invalid_schema = self.ErrorSchema({})
        assert invalid_schema.is_valid is False


# =============================================================================
# 5. Decorator Integration Tests
# =============================================================================

class TestDecoratorIntegration:
    """Tests for @validate_form decorator integration with @app.trigger_handler."""

    def test_decorator_with_trigger_handler_basic(self):
        """@validate_form works with @app.trigger_handler."""

        class TestSchema(FormSchema):
            title = field(str, required=True)
            count = field(int, default=0)

        app = create_app()
        received_form = None

        @app.trigger_handler
        @validate_form(TestSchema)
        def handle_form(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post(
            "/_trigger/handle_form",
            data={"title": "test_title", "count": "5"},
        )

        assert response.status_code == 200
        assert received_form is not None
        assert received_form.title == "test_title"
        assert received_form.count == 5
        assert received_form.is_valid

    def test_decorator_raises_validation_error(self):
        """@validate_form raises ValidationError for invalid data."""

        class RequiredSchema(FormSchema):
            title = field(str, required=True)

        app = create_app()

        @app.trigger_handler
        @validate_form(RequiredSchema)
        def handle_form(form: RequiredSchema) -> str:
            return "OK"

        client = TestClient(app)
        # Missing required field
        with pytest.raises(ValidationError):
            client.post("/_trigger/handle_form", data={})

    def test_decorator_with_handle_errors_false(self):
        """@validate_form with handle_errors=False injects errors dict."""

        class TestSchema(FormSchema):
            title = field(str, required=True)

        app = create_app()
        received_errors = None

        @app.trigger_handler
        @validate_form(TestSchema, handle_errors=False)
        def handle_form(form: TestSchema, errors: dict) -> str:
            nonlocal received_errors
            received_errors = errors
            return "OK" if not errors else "ERROR"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={})

        assert response.status_code == 200
        assert received_errors is not None
        assert "title" in received_errors

    def test_decorator_with_custom_form_data_param(self):
        """@validate_form works with custom form_data_param name."""

        class TestSchema(FormSchema):
            title = field(str)

        app = create_app()
        received_form = None

        @app.trigger_handler
        @validate_form(TestSchema, form_data_param="form_data")
        def handle_form(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={"title": "test"})

        assert response.status_code == 200
        assert received_form is not None

    def test_decorator_with_async_handler(self):
        """@validate_form works with async trigger handlers."""

        class TestSchema(FormSchema):
            title = field(str, required=True)

        app = create_app()
        received_form = None

        @app.trigger_handler
        @validate_form(TestSchema)
        async def handle_form_async(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form_async", data={"title": "async_test"})

        assert response.status_code == 200
        assert received_form is not None
        assert received_form.title == "async_test"

    def test_decorator_preserves_handler_name(self):
        """@validate_form preserves the handler's __name__."""

        class TestSchema(FormSchema):
            title = field(str)

        app = create_app()

        @app.trigger_handler
        @validate_form(TestSchema)
        def my_custom_handler(form: TestSchema) -> str:
            return "OK"

        assert my_custom_handler.__name__ == "my_custom_handler"

    def test_decorator_stacking_order(self):
        """Decorator stacking order: @validate_form on top of @app.trigger_handler."""

        class TestSchema(FormSchema):
            title = field(str, required=True)

        app = create_app()
        received_form = None

        # This is the recommended order: @validate_form on top
        @app.trigger_handler
        @validate_form(TestSchema)
        def handle_form(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={"title": "test"})

        assert response.status_code == 200
        assert received_form is not None

    def test_decorator_with_extra_fields_ignored(self):
        """Extra fields in form data are ignored (only schema fields are processed)."""

        class TestSchema(FormSchema):
            title = field(str)

        app = create_app()
        received_form = None

        @app.trigger_handler
        @validate_form(TestSchema)
        def handle_form(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post(
            "/_trigger/handle_form",
            data={"title": "test", "extra_field": "ignored", "another": "also_ignored"},
        )

        assert response.status_code == 200
        assert received_form.title == "test"

    def test_decorator_with_missing_optional_fields(self):
        """Missing optional fields use defaults."""

        class TestSchema(FormSchema):
            title = field(str, required=True)
            count = field(int, default=42)

        app = create_app()
        received_form = None

        @app.trigger_handler
        @validate_form(TestSchema)
        def handle_form(form: TestSchema) -> str:
            nonlocal received_form
            received_form = form
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/handle_form", data={"title": "test"})

        assert response.status_code == 200
        assert received_form.title == "test"
        assert received_form.count == 42


# =============================================================================
# 6. Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_empty_form_data(self):
        """Empty form data (empty dict) is handled correctly."""

        class OptionalSchema(FormSchema):
            title = field(str, default="default")

        schema = OptionalSchema({})
        assert schema.title == "default"
        assert schema.is_valid

    def test_none_form_data(self):
        """None form data is handled as empty dict."""

        class OptionalSchema(FormSchema):
            title = field(str, default="default")

        schema = OptionalSchema(None)
        assert schema.title == "default"
        assert schema.is_valid

    def test_extra_fields_in_form_data(self):
        """Extra fields in form data are ignored."""

        class SimpleSchema(FormSchema):
            title = field(str)

        schema = SimpleSchema({"title": "test", "extra": "ignored", "another": "also_ignored"})
        assert schema.title == "test"
        assert schema.is_valid

    def test_missing_optional_fields_use_defaults(self):
        """Missing optional fields use their defaults."""

        class DefaultSchema(FormSchema):
            title = field(str, default="default_title")
            count = field(int, default=10)
            active = field(bool, default=True)

        schema = DefaultSchema({})
        assert schema.title == "default_title"
        assert schema.count == 10
        assert schema.active is True
        assert schema.is_valid

    def test_non_string_values_in_form_data(self):
        """Non-string values in form data are handled (though unlikely from HTTP)."""

        class IntSchema(FormSchema):
            count = field(int)

        # In practice, form data values are always strings, but test robustness
        schema = IntSchema({"count": 42})  # int instead of "42"
        # Should still work due to coercion
        assert schema.count == 42

    def test_field_coerce_disabled(self):
        """Field with coerce=False keeps raw value."""

        class NoCoerceSchema(FormSchema):
            value = field(str, coerce=False)

        schema = NoCoerceSchema({"value": "test"})
        assert schema.value == "test"

    def test_schema_with_no_fields(self):
        """Schema with no fields is valid."""

        class EmptySchema(FormSchema):
            pass

        schema = EmptySchema({"anything": "ignored"})
        assert schema.is_valid

    def test_field_attribute_access_for_nonexistent_field(self):
        """Accessing non-existent field attribute raises AttributeError."""

        class SimpleSchema(FormSchema):
            title = field(str)

        schema = SimpleSchema({"title": "test"})
        with pytest.raises(AttributeError):
            _ = schema.nonexistent

    def test_schema_repr(self):
        """Schema has useful repr."""

        class SimpleSchema(FormSchema):
            title = field(str)
            count = field(int)

        schema = SimpleSchema({"title": "test", "count": "42"})
        repr_str = repr(schema)
        assert "SimpleSchema" in repr_str
        assert "title" in repr_str
        assert "count" in repr_str

    def test_coercion_of_boolean_from_various_strings(self):
        """Boolean coercion handles various string representations."""

        class BoolSchema(FormSchema):
            flag = field(bool)

        # Test various truthy strings
        for value in ["true", "True", "TRUE", "1", "on", "On", "ON", "yes", "Yes", "y"]:
            schema = BoolSchema({"flag": value})
            assert schema.flag is True, f"Failed for: {value}"

        # Test various falsy strings
        for value in ["false", "False", "FALSE", "0", "off", "Off", "OFF", "no", "No", "n"]:
            schema = BoolSchema({"flag": value})
            assert schema.flag is False, f"Failed for: {value}"

    def test_float_coercion_preserves_decimal(self):
        """Float coercion preserves decimal precision."""

        class FloatSchema(FormSchema):
            value = field(float)

        schema = FloatSchema({"value": "3.14159"})
        assert abs(schema.value - 3.14159) < 0.00001


# =============================================================================
# 7. Integration Tests with Existing Functionality
# =============================================================================

class TestIntegrationWithExistingCode:
    """Tests to ensure validation layer integrates with existing inguitive code."""

    def test_validation_does_not_break_existing_handlers(self):
        """Existing handlers without validation still work."""
        app = create_app()
        called = False

        @app.trigger_handler
        def simple_handler() -> str:
            nonlocal called
            called = True
            return "OK"

        client = TestClient(app)
        response = client.post("/_trigger/simple_handler")

        assert response.status_code == 200
        assert called is True

    def test_validation_does_not_break_form_data_injection(self):
        """Existing form_data injection still works."""
        app = create_app()
        received_data = None

        @app.trigger_handler
        def handle_form_data(form_data: dict) -> str:
            nonlocal received_data
            received_data = form_data
            return "OK"

        client = TestClient(app)
        client.post("/_trigger/handle_form_data", data={"key": "value"})

        assert received_data == {"key": "value"}

    def test_validation_exports_available_from_inguitive(self):
        """All validation classes are exported from inguitive package."""
        from inguitive import (
            CustomValidator,
            FormSchema,
            MaxLengthValidator,
            MaxValueValidator,
            MinLengthValidator,
            MinValueValidator,
            RegexValidator,
            RequiredValidator,
            ValidationError,
            Validator,
            field,
            validate_form,
        )
        # If we can import them all, the exports are working
        assert CustomValidator is not None
        assert FormSchema is not None
        assert MaxLengthValidator is not None
        assert MaxValueValidator is not None
        assert MinLengthValidator is not None
        assert MinValueValidator is not None
        assert RegexValidator is not None
        assert RequiredValidator is not None
        assert ValidationError is not None
        assert Validator is not None
        assert field is not None
        assert validate_form is not None


# =============================================================================
# 8. Complex Scenario Tests
# =============================================================================

class TestComplexScenarios:
    """Tests for complex, real-world scenarios."""

    def test_user_registration_form(self):
        """Test a complete user registration form scenario."""

        class UserRegistrationSchema(FormSchema):
            username = field(str, required=True, min_length=3, max_length=20)
            email = field(str, required=True, regex=r'^[\w.-]+@[\w.-]+\.\w+$')
            password = field(str, required=True, min_length=8)
            age = field(int, default=18, min_value=13, max_value=150)
            subscribe = field(bool, default=False)

        # Valid data
        valid_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "securepassword123",
            "age": "25",
            "subscribe": "true",
        }
        schema = UserRegistrationSchema(valid_data)
        assert schema.is_valid
        assert schema.username == "john_doe"
        assert schema.email == "john@example.com"
        assert schema.password == "securepassword123"
        assert schema.age == 25
        assert schema.subscribe is True

        # Invalid data - missing required fields
        invalid_data = {"username": "jo"}  # Too short, missing email and password
        schema = UserRegistrationSchema(invalid_data)
        assert not schema.is_valid
        assert "username" in schema.errors
        assert "email" in schema.errors
        assert "password" in schema.errors

        # Invalid data - invalid email format
        invalid_email_data = {
            "username": "john_doe",
            "email": "not-an-email",
            "password": "securepassword123",
        }
        schema = UserRegistrationSchema(invalid_email_data)
        assert not schema.is_valid
        assert "email" in schema.errors

    def test_nested_validation_with_decorator(self):
        """Test validation decorator with complex handler logic."""

        class ProductSchema(FormSchema):
            name = field(str, required=True, min_length=1)
            price = field(float, required=True, min_value=0)
            quantity = field(int, default=1, min_value=1)

        app = create_app()
        products = []

        @app.trigger_handler
        @validate_form(ProductSchema)
        def add_product(form: ProductSchema) -> str:
            products.append({
                "name": form.name,
                "price": form.price,
                "quantity": form.quantity,
            })
            return f"Added {form.name}"

        client = TestClient(app)

        # Add valid products
        response1 = client.post(
            "/_trigger/add_product",
            data={"name": "Widget", "price": "19.99", "quantity": "10"},
        )
        assert response1.status_code == 200
        assert len(products) == 1

        response2 = client.post(
            "/_trigger/add_product",
            data={"name": "Gadget", "price": "29.99"},  # quantity uses default
        )
        assert response2.status_code == 200
        assert len(products) == 2

        # Try to add invalid product
        with pytest.raises(ValidationError):
            client.post(
                "/_trigger/add_product",
                data={"name": "", "price": "-5.00"},  # Invalid name and price
            )

        # Products list should not have changed
        assert len(products) == 2

    def test_form_with_custom_validators(self):
        """Test form with custom validator functions."""

        def validate_username_available(username):
            """Simulate checking if username is available."""
            taken_usernames = {"admin", "root", "test"}
            if username in taken_usernames:
                return "Username is already taken"
            return True

        class UserSchema(FormSchema):
            username = field(
                str,
                required=True,
                validators=[CustomValidator(validate_username_available)],
            )

        # Available username
        schema = UserSchema({"username": "unique_user"})
        assert schema.is_valid

        # Taken username
        schema = UserSchema({"username": "admin"})
        assert not schema.is_valid
        assert "username" in schema.errors
        assert "already taken" in schema.errors["username"][0]

    def test_conditional_validation_based_on_other_fields(self):
        """Test validation where field requirements depend on other fields."""

        class ShippingSchema(FormSchema):
            use_shipping = field(bool, default=False)
            shipping_address = field(str, required=False)  # Will validate conditionally

            def validate(self):
                """Custom validation logic."""
                if self.use_shipping and not self.shipping_address:
                    self._errors["shipping_address"] = ["Shipping address is required when using shipping"]
                return super().validate()

        # Without shipping - no shipping address needed
        schema = ShippingSchema({"use_shipping": "false", "shipping_address": ""})
        assert schema.is_valid

        # With shipping but no address - should fail
        schema = ShippingSchema({"use_shipping": "true", "shipping_address": ""})
        assert not schema.is_valid

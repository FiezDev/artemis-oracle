# Prompt for Generating Python Unit Tests with pytest

Here's a comprehensive prompt you can use to generate high-quality Python unit tests:

---

## Recommended Prompt

```
Generate comprehensive pytest unit tests for the following Python code:

[PASTE YOUR CODE HERE]

Requirements for the tests:
1. Use pytest framework conventions (test_ prefix, assert statements)
2. Include tests for:
   - Happy path scenarios (expected behavior)
   - Edge cases (empty inputs, None values, boundary conditions)
   - Error handling (invalid inputs, expected exceptions)
3. Use appropriate pytest features:
   - @pytest.fixture for setup/teardown when needed
   - @pytest.mark.parametrize for parameterized tests when testing multiple inputs
   - @pytest.raises for testing expected exceptions
4. Follow naming convention: test_<function_name>_<scenario>
5. Include docstrings explaining what each test validates
6. Aim for high code coverage but prioritize meaningful tests over coverage percentage

Output format:
- Complete, runnable test file
- Include necessary imports
- Add comments explaining complex test logic
```

---

## Alternative: Step-by-Step Prompt

If you want more control, use this iterative approach:

```
I have a Python function/module that I need to test with pytest.

Here's the code:
[PASTE YOUR CODE]

Please help me write tests by:
1. First, identify all functions/methods that need testing
2. List the test scenarios for each (happy path, edge cases, errors)
3. Generate the complete test file with proper structure
```

---

## Tips for Better Results

1. **Include context**: Share the full module or function you're testing
2. **Specify dependencies**: Mention any external services, databases, or APIs that need mocking
3. **Coverage goals**: Mention if you need 100% coverage or have specific requirements
4. **Mocking needs**: If your code makes HTTP requests or file operations, mention that mocking is needed

---

## Example Usage

**Input:**
```python
def calculate_discount(price, discount_percent):
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)
```

**Prompt:**
```
Generate pytest unit tests for this function:

def calculate_discount(price, discount_percent):
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)

Include tests for happy path, edge cases, and error handling.
```

**Expected Output:**
```python
import pytest

def test_calculate_discount_happy_path():
    """Test normal discount calculation."""
    assert calculate_discount(100, 20) == 80.0
    assert calculate_discount(50, 10) == 45.0

def test_calculate_discount_zero_percent():
    """Test with 0% discount."""
    assert calculate_discount(100, 0) == 100.0

def test_calculate_discount_hundred_percent():
    """Test with 100% discount."""
    assert calculate_discount(100, 100) == 0.0

@pytest.mark.parametrize("price,discount,expected", [
    (100, 25, 75.0),
    (200, 50, 100.0),
    (99.99, 33.33, 66.6633),
])
def test_calculate_discount_various_inputs(price, discount, expected):
    """Test various input combinations."""
    assert calculate_discount(price, discount) == pytest.approx(expected)

def test_calculate_discount_negative_percent_raises():
    """Test that negative discount raises ValueError."""
    with pytest.raises(ValueError, match="Discount must be between 0 and 100"):
        calculate_discount(100, -10)

def test_calculate_discount_over_hundred_raises():
    """Test that discount over 100 raises ValueError."""
    with pytest.raises(ValueError, match="Discount must be between 0 and 100"):
        calculate_discount(100, 110)
```

---

## Quick Reference: Common pytest Patterns

| Pattern | Use Case |
|---------|----------|
| `assert x == y` | Basic equality check |
| `pytest.approx(value)` | Float comparison with tolerance |
| `@pytest.fixture` | Shared setup/teardown |
| `@pytest.mark.parametrize` | Data-driven tests |
| `pytest.raises(Exception)` | Test expected exceptions |
| `@pytest.mark.skip` | Skip a test temporarily |
| `monkeypatch.setattr()` | Mock/patch objects |

---

Good luck with your testing!

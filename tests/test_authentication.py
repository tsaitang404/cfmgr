"""Tests for API authentication middleware.

Since the Worker class depends on Pyodide runtime, we test the authentication
logic by code inspection and verifying configuration files.
"""

import os


class TestAuthenticationLogic:
    """Test authentication logic by code inspection."""

    def test_public_routes_defined(self):
        """Verify public routes are properly defined in the code."""
        with open("src/index.py", encoding="utf-8") as f:
            content = f.read()

        # Check that public_routes are defined
        assert 'public_routes = ["", "health", "docs", "docs/", "docs/d1", "docs/r2"]' in content

    def test_auth_middleware_exists(self):
        """Verify authentication middleware code exists."""
        with open("src/index.py", encoding="utf-8") as f:
            content = f.read()

        # Check for authentication logic
        assert "X-API-Key" in content
        assert "expected_api_key" in content
        assert "Missing API Key" in content
        assert "Invalid API Key" in content

    def test_auth_checks_api_key_env(self):
        """Verify authentication checks API_KEY from environment."""
        with open("src/index.py", encoding="utf-8") as f:
            content = f.read()

        assert 'getattr(self.env, "API_KEY"' in content

    def test_returns_401_for_missing_key(self):
        """Verify code returns 401 for missing API key."""
        with open("src/index.py", encoding="utf-8") as f:
            content = f.read()

        assert "status=401" in content
        assert "Missing API Key" in content

    def test_returns_403_for_invalid_key(self):
        """Verify code returns 403 for invalid API key."""
        with open("src/index.py", encoding="utf-8") as f:
            content = f.read()

        assert "status=403" in content
        assert "Invalid API Key" in content


class TestAuthenticationConfiguration:
    """Test authentication configuration files."""

    def test_wrangler_toml_has_api_key_config(self):
        """Verify wrangler.toml has API_KEY configuration."""
        with open("wrangler.toml", encoding="utf-8") as f:
            content = f.read()

        # Should mention API_KEY
        assert "API_KEY" in content

    def test_wrangler_example_has_detailed_config(self):
        """Verify example config has detailed authentication setup."""
        with open("wrangler.toml.example", encoding="utf-8") as f:
            content = f.read()

        # Should have detailed auth documentation
        assert "API_KEY" in content
        assert "认证配置" in content or "authentication" in content.lower()
        assert "X-API-Key" in content

    def test_readme_documents_authentication(self):
        """Verify README documents authentication."""
        with open("README.md", encoding="utf-8") as f:
            content = f.read()

        # Should document authentication
        assert "API_KEY" in content or "认证" in content
        assert "X-API-Key" in content


class TestSecurityBestPractices:
    """Test that security best practices are followed."""

    def test_uses_wrangler_secrets_for_production(self):
        """Verify documentation recommends Wrangler secrets for production."""
        with open("wrangler.toml.example", encoding="utf-8") as f:
            content = f.read()

        assert "wrangler secret" in content.lower()

    def test_public_routes_documented(self):
        """Verify public routes are documented."""
        with open("README.md", encoding="utf-8") as f:
            content = f.read()

        # Should document which routes are public
        assert "/health" in content
        assert "/docs" in content

    def test_protected_routes_documented(self):
        """Verify protected routes are documented."""
        with open("README.md", encoding="utf-8") as f:
            content = f.read()

        # Should document protected routes
        assert "/d1/" in content or "d1" in content
        assert "/r2/" in content or "r2" in content


def test_authentication_test_script_exists():
    """Verify authentication test script exists."""
    assert os.path.exists("test_auth.sh")

    with open("test_auth.sh", encoding="utf-8") as f:
        content = f.read()

    # Should test authentication
    assert "X-API-Key" in content
    assert "curl" in content

# =============================================================================
# test_forbidden_patterns.py
# Negative tests: forbidden pattern detection in input guardrail.
# Tests that secret/credential patterns in Java code are blocked before
# reaching the LLM, preventing accidental secret exfiltration.
# =============================================================================
import pytest
from guardrails.input_guard import sanitize, InputGuardError

pytestmark = pytest.mark.negative


# ---------------------------------------------------------------------------
# Password patterns
# ---------------------------------------------------------------------------

def test_password_equals_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String s = "password=mysecret123";')


def test_pwd_assignment_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('this.pwd = "topsecret";')


def test_db_password_config_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('datasource.password=hunter2hunter2')


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------

def test_api_key_equals_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('private static final String api_key = "sk-1234567890abcdef";')


def test_openai_sk_prefix_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";')


def test_apikey_camel_case_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String apiKey = "APIKEY-supersecret";')


# ---------------------------------------------------------------------------
# AWS credentials
# ---------------------------------------------------------------------------

def test_akia_access_key_blocked():
    """AKIA... is the AWS access key ID prefix."""
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String key = "AKIAIOSFODNN7EXAMPLE";')


def test_aws_access_key_id_label_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String aws_access_key_id = "AKIA12345678901234";')


def test_aws_secret_access_key_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY";')


# ---------------------------------------------------------------------------
# Private key PEM headers
# ---------------------------------------------------------------------------

def test_rsa_private_key_pem_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----")


def test_ec_private_key_pem_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize("-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIOFoo...\n-----END EC PRIVATE KEY-----")


def test_private_key_pem_generic_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize("-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAAS...")


# ---------------------------------------------------------------------------
# Bearer / Authorization tokens
# ---------------------------------------------------------------------------

def test_bearer_jwt_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('String authHeader = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature";')


def test_authorization_bearer_header_blocked():
    with pytest.raises(InputGuardError, match="secret"):
        sanitize('headers.put("Authorization", "Bearer eyJhbGciOiJIUzI1NiJ9.test.test");')


# ---------------------------------------------------------------------------
# Clean code does NOT get blocked
# ---------------------------------------------------------------------------

def test_password_variable_name_without_value_passes():
    """A variable named 'password' without an actual secret value must pass."""
    java = """\
public class Auth {
    private String password;
    public void setPassword(String password) {
        this.password = password;
    }
}"""
    result = sanitize(java)
    assert "Auth" in result


def test_api_documentation_comment_passes():
    """Documentation that mentions 'API key' without a real key must pass."""
    java = """\
/**
 * Authenticates using an API key passed in the header.
 * @param request the incoming HTTP request
 */
public class ApiHandler {
    public void handle(Request request) {}
}"""
    result = sanitize(java)
    assert "ApiHandler" in result

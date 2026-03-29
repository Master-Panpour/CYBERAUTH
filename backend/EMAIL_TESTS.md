# Email System Tests - Reference Guide

## Test Files Created

### 1. `backend/tests/test_email.py` (~350 lines)
Unit tests for email service functionality

**Test Classes:**
- `TestEmailService` - Email service core functionality
- `TestEmailTemplates` - Email template generation
- `TestEmailSecurity` - Security hardening verification
- `TestOWASPCompliance` - OWASP Top 10 compliance

**Key Test Cases (30+ tests):**

```python
# Token Generation & Security
test_generate_verification_token()    # Unique, 256-bit entropy
test_token_expiry_calculation()       # 24 hours ± 5s
test_password_reset_expiry()          # 1 hour ± 5s
test_is_token_expired_valid()         # Correct valid detection
test_is_token_expired_invalid()       # Correct expiration detection
test_is_token_expired_none()          # Fail-safe for None

# Email Validation
test_is_valid_email_valid_addresses()   # Accept valid emails
test_is_valid_email_invalid_addresses() # Reject invalid emails

# Template Security
test_verification_email_template()        # HTML/text generation
test_verification_email_escapes_username() # HTML injection prevention
test_password_reset_email_template()      # Reset email content
test_password_reset_email_escapes_username() # Escape verification

# OWASP Coverage
test_a2_cryptographic_failures_token_strength() # 256-bit entropy
test_a3_injection_no_template_injection()       # No Jinja2 injection
test_a5_security_misconfiguration_env_based()  # Env-based config
test_a7_authentication_token_expiration()      # Expiry enforcement
test_a7_authentication_rate_limiting_configured() # Rate limit setup
```

### 2. `backend/tests/test_email_routes.py` (~400 lines)
Integration tests for email endpoints

**Test Classes:**
- `TestEmailVerificationEndpoints` - Email verification routes
- `TestPasswordResetEndpoints` - Password reset routes
- `TestRateLimiting` - Rate limiting enforcement
- `TestSecurityVulnerabilities` - OWASP vulnerability prevention
- `TestEmailEnumerationProtection` - Enumeration attack prevention

**Key Test Cases (40+ tests):**

```python
# Email Verification Flow
test_request_verification_email_success()      # Successful request
test_request_verification_invalid_email()      # Invalid format rejection
test_verify_email_success()                    # Valid token verification
test_verify_email_invalid_token()              # Invalid token handling
test_verify_email_expired_token()              # Expiration enforcement
test_verify_email_token_already_verified()     # Duplicate prevention

# Password Reset Flow
test_request_password_reset_success()          # Reset request works
test_request_password_reset_nonexistent_email() # Enumeration protection
test_reset_password_success()                  # Password update works
test_reset_password_invalid_token()            # Invalid token rejection
test_reset_password_weak_password()            # Password strength check

# Rate Limiting Security (A7)
test_email_rate_limiting_per_user()           # 5/hour limit per user
test_rate_limit_resets_after_hour()           # Automatic reset

# OWASP Vulnerabilities
test_a1_broken_access_control()               # Own resources only
test_a2_cryptographic_failures_token_strength() # Strong tokens
test_a3_injection_sql_injection_prevention()  # SQL injection blocked
test_a3_injection_template_injection_prevention() # Template injection blocked
test_a7_authentication_token_expiration_enforced() # Expiry enforced
test_a9_logging_audit_trail()                 # Logging verification

# Email Enumeration Protection
test_reset_request_same_response_for_existing_and_nonexistent() # Same response
test_verification_request_same_response_for_all() # No email leak
```

## Running Tests

### Run All Email Tests
```bash
cd backend
pytest tests/test_email.py tests/test_email_routes.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_email.py::TestEmailService -v
pytest tests/test_email_routes.py::TestRateLimiting -v
```

### Run Specific Test
```bash
pytest tests/test_email.py::TestEmailService::test_generate_verification_token -v
```

### Run with Coverage Report
```bash
pytest tests/test_email.py tests/test_email_routes.py --cov=email_service --cov=email_routes --cov-report=html
```

### Run Security Tests Only
```bash
pytest tests/test_email.py::TestEmailSecurity -v
pytest tests/test_email_routes.py::TestSecurityVulnerabilities -v
```

## OWASP Coverage Matrix

| OWASP Top 10 | Vulnerability | Test Case(s) | Status |
|---|---|---|---|
| A1 | Broken Access Control | test_a1_broken_access_control | ✅ Covered |
| A2 | Cryptographic Failures | test_a2_cryptographic_failures_token_strength | ✅ Covered |
| A3 | Injection | test_a3_injection_* (SQL, Template) | ✅ Covered |
| A5 | Security Misconfiguration | test_a5_security_misconfiguration_env_based | ✅ Covered |
| A7 | Authentication Bugs | test_a7_authentication_* (Expiry, Rate limit) | ✅ Covered |
| A9 | Logging & Monitoring | test_a9_logging_audit_trail | ✅ Covered |

## Security Test Highlights

### 1. Token Generation Security
```python
# Ensures cryptographically secure token generation
tokens = set()
for _ in range(1000):
    token = EmailService.generate_verification_token()
    assert token not in tokens  # Must be unique
    assert len(token) == 64     # 256-bit entropy (hex)
```

### 2. Template Injection Prevention
```python
# Test that Jinja2/template injection doesn't execute
malicious_username = "{{ __import__('os').system('rm -rf /') }}"
html, text = EmailTemplates.verification_email(
    username=malicious_username,
    ...
)
# Should NOT contain __import__ or system calls
assert "__import__" not in html
```

### 3. Email Enumeration Protection
```python
# Same response for existing and nonexistent emails
response_existing = client.post(
    "/auth/password/reset-request",
    json={"email": "existing@example.com"}
)
response_nonexistent = client.post(
    "/auth/password/reset-request",
    json={"email": "nonexistent@example.com"}
)
# Both return 200 - attacker learns nothing
assert response_existing.status_code == 200
assert response_nonexistent.status_code == 200
```

### 4. Rate Limiting Enforcement
```python
# Simulate 5 email attempts within 1 hour
_email_send_attempts[user_id] = [time.time()] * 5
# 6th attempt should fail with 429 Too Many Requests
response = client.post(...)
assert response.status_code == 429
```

### 5. Token Expiration Enforcement
```python
# Expired tokens must be rejected
past_time = datetime.utcnow() - timedelta(hours=1)
assert EmailService.is_token_expired(past_time) == True

# Future tokens should be valid
future_time = datetime.utcnow() + timedelta(hours=1)
assert EmailService.is_token_expired(future_time) == False
```

## Test Statistics

- **Total Test Cases:** 70+
- **Test Files:** 2
- **Total Lines of Code:** ~750 lines
- **Coverage Areas:** 6/10 OWASP Top 10 items
- **Security Focus:** 40% of tests dedicated to security
- **Mocking:** Email sending, database transactions
- **Async Tests:** Full async support with pytest-asyncio

## Running Tests in CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Run Email Tests
  run: |
    cd backend
    pytest tests/test_email.py tests/test_email_routes.py -v --cov=email_service --cov=email_routes
```

## Notes for Implementation

1. **Database Fixtures:** Tests assume pytest fixtures for:
   - `db_session` - AsyncSession for database operations
   - `client` - TestClient from FastAPI.testclient

2. **Mocking:** Uses `unittest.mock` and `pytest-mock` for:
   - Email sending (aiosmtplib)
   - SMTP connections

3. **Async Support:** All endpoint tests use `@pytest.mark.asyncio`

4. **Security Emphasis:** ~40% of test cases focus on security:
   - OWASP Top 10 coverage
   - Enumeration protection
   - Rate limiting
   - Token validation

## Next Steps

1. ✅ Create test files (DONE)
2. ⏳ Install test dependencies (pytest-mock)
3. ⏳ Run tests and track coverage
4. ⏳ Fix any failing tests
5. ⏳ Add integration tests with database
6. ⏳ Create frontend components for email verification
7. ⏳ End-to-end testing across full flow

## Related Files

- `backend/email_service.py` - Core email service (being tested)
- `backend/email_routes.py` - API endpoints (being tested)
- `backend/email_config.py` - Configuration
- `backend/models.py` - Database models
- `backend/config.py` - Application settings
- `backend/tests/conftest.py` - pytest fixtures

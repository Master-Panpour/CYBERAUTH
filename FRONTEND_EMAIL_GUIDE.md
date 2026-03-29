# Frontend Implementation Guide - Email Verification System

## 🎯 Overview

This guide outlines the frontend components and integration points needed to complete the email verification system (Phase 1.1).

---

## 📋 Tasks Required

### 1. Email Verification Request Form

**Component Name:** `VerifyEmailRequest.jsx`  
**Purpose:** Allow users to request an email verification link  
**Estimated Lines:** 80-100

**UI Elements:**
- Email input field (with validation feedback)
- "Send Verification Email" button
- Loading state during API call
- Success message confirmation
- Error message display
- "Resend" option with rate-limit warning (5/hour)

**State Management:**
```javascript
- email: string (user input)
- loading: boolean (during API call)
- success: boolean (after successful send)
- error: string | null (error message)
- attempts: number (track resend attempts)
- cooldownTime: number (remaining seconds until can resend)
```

**API Endpoint:**
```
POST /auth/email/verify-request
Request: { email: string }
Response: { message: string, email: string }
Status: 200 OK or 429 Too Many Requests (rate limit)
```

**UX Flow:**
1. User enters email → click "Send"
2. Disable button + show spinner
3. API call with email
4. Success: Show "Check your email for verification link"
5. Start 1-hour cooldown timer
6. Error: Show error message, enable retry

---

### 2. Email Verification Form

**Component Name:** `VerifyEmail.jsx`  
**Purpose:** Allow users to verify their email with a token  
**Estimated Lines:** 100-120

**UI Elements:**
- Token input field (paste from email link)
- "Verify Email" button
- Loading state
- Success confirmation
- Error message (with "resend" link if expired)
- Optional: Countdown timer showing token expiry

**State Management:**
```javascript
- token: string (from URL params or manual entry)
- loading: boolean
- success: boolean
- error: string | null
- message: string | null
- tokenExpiryTime: datetime (calculated from response)
- timeRemaining: number (seconds until expiry)
```

**API Endpoint:**
```
POST /auth/email/verify
Request: { token: string }
Response: { message: string, email_verified: boolean }
Status: 200 OK, 400 Bad Request (expired), 404 Not Found (invalid)
```

**Token Source (two options):**
1. **From Email Link:** `https://app.cyberauth.com/verify-email?token=abc123`
   - Extract token from URL params
   - Auto-submit or show "Verify" button

2. **From User Input:** Manual token paste
   - Text field for token
   - User clicks "Verify"

**UX Flow - From Email Link:**
1. User clicks link with token
2. Extract token from URL
3. Display: "Verifying your email..."
4. Auto-submit to API
5. Success: "Email verified! Redirecting to dashboard..."
6. Redirect to `/dashboard` after 2 seconds

**UX Flow - Manual Entry:**
1. User pastes token in form
2. Click "Verify"
3. Show loading spinner
4. Success: "Email verified successfully!"
5. Enable next action (e.g., enable MFA setup)

**Error Handling:**
- **Expired token (400):** Show "Link expired. Request a new verification email"
  - Display "Resend Verification Email" button (links to VerifyEmailRequest)
- **Invalid token (404):** Show "Invalid verification token"
  - Display "Request new email" button
- **Already verified (400):** Show "Your email is already verified"

---

### 3. Password Reset Request Form

**Component Name:** `ResetPasswordRequest.jsx`  
**Purpose:** Allow users to request a password reset link  
**Estimated Lines:** 80-100

**UI Elements:**
- Email input field
- "Send Password Reset Email" button
- Loading state
- Success confirmation (without confirming email existence)
- Error message
- Rate limit warning

**State Management:**
```javascript
- email: string
- loading: boolean
- submitted: boolean
- error: string | null
- attempts: number
- cooldownTime: number
```

**API Endpoint:**
```
POST /auth/password/reset-request
Request: { email: string }
Response: { message: string }
Status: 200 OK (always, even if email doesn't exist)
Status: 429 Too Many Requests (rate limit)
```

**Security Note:** Response is identical whether email exists or not
- This prevents email enumeration attacks
- Don't show "Email not found" error
- Always show generic success message

**UX Flow:**
1. User enters email
2. Click "Send Reset Email"
3. Always show: "If an account exists with this email, you'll receive a password reset link"
4. Do NOT indicate whether email exists
5. Rate limit to 5 requests/hour

---

### 4. Password Reset Form

**Component Name:** `ResetPassword.jsx`  
**Purpose:** Allow users to reset password with a valid token  
**Estimated Lines:** 120-150

**UI Elements:**
- Password reset token (from URL or manual input)
- New password field
- Confirm password field
- Password strength indicator
- "Reset Password" button
- Loading state
- Error/success messages
- Password requirements checklist

**State Management:**
```javascript
- token: string
- newPassword: string
- confirmPassword: string
- loading: boolean
- success: boolean
- error: string | null
- showPassword: boolean (toggle visibility)
- passwordStrength: number (0-100%)
- passwordFeedback: string
```

**Password Requirements Display:**
```
✓/✗ At least 12 characters
✓/✗ At least one uppercase letter (A-Z)
✓/✗ At least one lowercase letter (a-z)
✓/✗ At least one number (0-9)
✓/✗ At least one special character (!@#$%^&*)
✓/✗ Passwords match
```

**API Endpoint:**
```
POST /auth/password/reset
Request: { token: string, new_password: string }
Response: { message: string, success: boolean }
Status: 200 OK, 400 Bad Request (weak password/expired token), 404 Not Found
```

**UX Flow - From Email Link:**
1. User clicks reset link: `https://app.cyberauth.com/reset-password?token=xyz789`
2. Extract token from URL
3. Display password reset form
4. Show password requirements checklist
5. Validate as user types (password strength meter)
6. User enters new password
7. Click "Reset Password"
8. Validate passwords match
9. Call API
10. Success: "Password reset successfully! Redirecting to login..."
11. Redirect to `/login` after 2 seconds
12. User logs in with new password

**UX Flow - Manual Entry:**
1. User pastes token in form
2. Enter new password
3. Show password strength feedback
4. Click "Reset Password"
5. Same flow as above

**Error Handling:**
- **Weak password (422):** Show specific requirement not met
  - Highlight checklist item in red
  - Don't allow submit
- **Expired token (400):** Show "Link expired. Request a new password reset"
  - Display "Send New Reset Email" button
- **Invalid token (404):** Show "Invalid or expired reset token"
- **Passwords don't match (client validation):** Show "Passwords must match"

---

## 🔌 API Integration

### API Client Functions

**Create functions in `src/api/auth.js`:**

```javascript
// Email Verification
async function requestEmailVerification(email) {
  // POST /auth/email/verify-request
  // Returns: { message, email }
  // Throws: Error with status (429 for rate limit)
}

async function verifyEmail(token) {
  // POST /auth/email/verify
  // Returns: { message, email_verified }
  // Throws: Error with status (400 expired, 404 invalid)
}

// Password Reset
async function requestPasswordReset(email) {
  // POST /auth/password/reset-request
  // Returns: { message }
  // Note: Always returns 200, doesn't confirm email exists
  // Throws: Error with status (429 for rate limit)
}

async function resetPassword(token, newPassword) {
  // POST /auth/password/reset
  // Returns: { message, success }
  // Throws: Error with status (400, 404, 422)
}
```

**Example Implementation:**

```javascript
// src/api/auth.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export async function requestEmailVerification(email) {
  const response = await fetch(`${API_BASE_URL}/auth/email/verify-request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
    credentials: 'include',  // Send cookies with request
  });
  
  if (!response.ok) {
    const error = await response.json();
    const err = new Error(error.detail || 'Failed to send verification email');
    err.status = response.status;
    throw err;
  }
  
  return response.json();
}

export async function verifyEmail(token) {
  const response = await fetch(`${API_BASE_URL}/auth/email/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    const err = new Error(error.detail || 'Failed to verify email');
    err.status = response.status;
    throw err;
  }
  
  return response.json();
}

// ... similar for password reset
```

---

## 🛣️ Routing Integration

### Add Routes to React Router

**`src/App.jsx` or routing config:**

```javascript
import VerifyEmailRequest from './components/VerifyEmailRequest';
import VerifyEmail from './components/VerifyEmail';
import ResetPasswordRequest from './components/ResetPasswordRequest';
import ResetPassword from './components/ResetPassword';

// In your routes array:
{
  path: '/verify-email-request',
  element: <VerifyEmailRequest />,
  protected: false,  // Anonymous users can access
},
{
  path: '/verify-email',
  element: <VerifyEmail />,
  protected: false,
},
{
  path: '/reset-password-request',
  element: <ResetPasswordRequest />,
  protected: false,
},
{
  path: '/reset-password',
  element: <ResetPassword />,
  protected: false,
},
```

### Email Link Destinations

**Backend sends these email links:**

```
Verification Email:
https://app.cyberauth.com/verify-email?token=abc123xyz789...

Password Reset Email:
https://app.cyberauth.com/reset-password?token=xyz789abc123...
```

---

## 🎨 UI/UX Patterns

### Shared Components & Utilities

**Password Strength Meter:**
```javascript
// src/components/PasswordStrengthMeter.jsx
export function evaluatePasswordStrength(password) {
  let score = 0;
  const requirements = {
    minLength: password.length >= 12,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
  };
  
  // Calculate score and return { score, requirements, feedback }
}
```

**Rate Limit Counter:**
```javascript
// Countdown timer for resend button
// Show "Resend in X seconds" if rate limited
const [cooldownSeconds, setCooldownSeconds] = useState(0);
```

**Loading States:**
```javascript
// Show spinner/skeleton during API calls
// Disable buttons during loading
// Show appropriate loading text
```

### Error Messages

**Consistent Error Display:**
- Use toast notifications or inline error boxes
- Show specific, helpful error messages
- Provide recovery actions (e.g., "Resend email" link)

**Don't Show Information Leakage:**
- ❌ "Email not found" (reveals valid emails)
- ✅ "If an account exists..." (hides valid emails)

---

## 🧪 Testing Considerations

### Test Scenarios

1. **Happy Path:**
   - User requests verification email
   - User clicks link in email
   - Email is verified
   - User logged in

2. **Expired Token:**
   - User clicks old verification link
   - Shows "Link expired"
   - Offer to resend email

3. **Rate Limiting:**
   - User clicks resend 6 times in 1 hour
   - 5th succeeds, 6th shows rate limit error
   - Message: "Too many requests. Try again later"

4. **Password Reset:**
   - User forgot password
   - Requests reset link
   - Receives email with token
   - Resets password successfully
   - Logs in with new password

5. **Security - Enumeration:**
   - Request reset for existing email: Same response
   - Request reset for fake email: Same response
   - Confirms user can't tell valid emails

---

## 📦 Dependencies

**Already Included:**
- React 18.2.0
- Vite 5.2.0
- React Router

**Might Need:**
- `react-toastify` for toast notifications
- `react-hook-form` for form management
- `zxcvbn` for password strength calculation

---

## 📝 TODO Checklist - Frontend

- [ ] Create VerifyEmailRequest.jsx component
- [ ] Create VerifyEmail.jsx component
- [ ] Create ResetPasswordRequest.jsx component
- [ ] Create ResetPassword.jsx component
- [ ] Add API functions to auth.js
- [ ] Add routes to React Router config
- [ ] Create PasswordStrengthMeter component
- [ ] Test email verification flow
- [ ] Test password reset flow
- [ ] Test rate limiting errors
- [ ] Test expired token scenarios
- [ ] Write component unit tests
- [ ] Test e2e with backend
- [ ] Document user flows

---

## 🔗 Related Backend Files

- `backend/email_service.py` - Email sending logic
- `backend/email_routes.py` - API endpoints
- `backend/schemas.py` - Request/response schemas
- `backend/models.py` - User model with email fields
- `backend/EMAIL_TESTS.md` - Test documentation

---

## 🚀 Next Steps

1. Create the 4 React components above
2. Integrate with API client functions
3. Add routes to React Router
4. Test complete flows with backend
5. Deploy and validate in staging environment

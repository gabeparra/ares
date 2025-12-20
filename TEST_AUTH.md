# Testing Auth0 Admin Role Authentication

## Quick Test from Browser Console

After logging in, open browser console (F12) and run:

```javascript
// Get your access token
const token = window.authToken;

// Test the check-admin endpoint
fetch("/api/v1/auth/check-admin", {
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
})
  .then((r) => r.json())
  .then((data) => console.log("Admin check result:", data))
  .catch((err) => console.error("Error:", err));
```

## Testing with curl

```bash
# First, get your access token from the browser (window.authToken)
TOKEN="your-access-token-here"

# Test the endpoint
curl -X GET http://localhost:8000/api/v1/auth/check-admin \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

## Check Backend Logs

The backend now logs detailed information. Check logs with:

```bash
# If using Docker
docker-compose logs -f backend

# If running locally
# Look at the console output where you ran: python manage.py runserver
```

You should see logs like:

- "Requesting Management API token from..."
- "Checking roles for user..."
- "User X has Y roles: [...]"
- Any errors that occur

## Common Issues

1. **Management API token fails**:

   - Check that `AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET` are set correctly
   - Verify these are for a Machine-to-Machine application with Management API access
   - Ensure the application has `read:users` and `read:roles` permissions

2. **User not found**:

   - Check that the user ID (sub claim) is correct
   - Verify the user exists in Auth0

3. **Role not found**:

   - Verify the role ID `rol_BysmqyxaOLmdalmX` exists in Auth0
   - Check that the user is assigned this role in Auth0 Dashboard
   - The role name should be "admin" (case-insensitive)

4. **403 Forbidden**:
   - The Management API application needs proper permissions
   - Check Auth0 Dashboard → Applications → Your M2M App → APIs → Auth0 Management API → Permissions

## Verify Auth0 Setup

1. Go to Auth0 Dashboard → Applications → Machine-to-Machine Applications
2. Find your application (using AUTH0_CLIENT_ID)
3. Go to APIs tab → Auth0 Management API
4. Ensure these permissions are enabled:

   - `read:users`
   - `read:roles`
   - `read:role_members`

5. Go to User Management → Users → Find your user
6. Go to Roles tab → Verify the user has the "admin" role assigned
7. Go to User Management → Roles → Find "admin" role
8. Verify the role ID matches `rol_BysmqyxaOLmdalmX`

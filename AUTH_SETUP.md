# Auth0 Setup Guide for ARES

This guide explains how to configure Auth0 authentication for ARES.

## Prerequisites

- An Auth0 account (free tier available at https://auth0.com)
- Auth0 application configured

## Step 1: Create Auth0 Application

1. Log in to your Auth0 Dashboard
2. Go to **Applications** → **Applications**
3. Click **Create Application**
4. Choose **Single Page Web Applications**
5. Click **Create**

## Step 2: Configure Auth0 Application

1. In your application settings, configure:

   **Allowed Callback URLs:**
   ```
   http://localhost,http://localhost:3000,http://127.0.0.1,http://127.0.0.1:3000
   ```
   (Add your production domain when deploying)

   **Allowed Logout URLs:**
   ```
   http://localhost,http://localhost:3000,http://127.0.0.1,http://127.0.0.1:3000
   ```

   **Allowed Web Origins:**
   ```
   http://localhost,http://localhost:3000,http://127.0.0.1,http://127.0.0.1:3000
   ```

2. Scroll down and click **Save Changes**

## Step 3: Create Auth0 API (Optional but Recommended)

1. Go to **Applications** → **APIs**
2. Click **Create API**
3. Fill in:
   - **Name**: ARES API
   - **Identifier**: `https://ares-api` (or your domain)
   - **Signing Algorithm**: RS256
4. Click **Create**
5. Note the **Identifier** (this is your Audience)

## Step 4: Configure Environment Variables

Create or update your `.env` file:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id-here
AUTH0_CLIENT_SECRET=your-client-secret-here  # Not needed for SPA, but useful for backend
AUTH0_AUDIENCE=https://ares-api  # The API identifier from Step 3
```

**Where to find these values:**
- `AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., `myapp.auth0.com`)
- `AUTH0_CLIENT_ID`: Found in your Application settings
- `AUTH0_CLIENT_SECRET`: Found in your Application settings (not used for SPA, but good to have)
- `AUTH0_AUDIENCE`: The API identifier you created in Step 3

## Step 5: Restart Services

After updating `.env`:

```bash
docker-compose down
docker-compose up --build
```

## Step 6: Test Authentication

1. Open `http://localhost` in your browser
2. You should see a **Log In** button in the header
3. Click it to authenticate with Auth0
4. After logging in, you should see your user info and a **Log Out** button

## Troubleshooting

### "Auth0 Not Configured" Message

- Check that all Auth0 environment variables are set in `.env`
- Restart the Docker containers after updating `.env`
- Verify the values are correct (no extra spaces, correct domain format)

### "Invalid token" or 401 Errors

- Verify your `AUTH0_AUDIENCE` matches the API identifier
- Check that the API is enabled in Auth0
- Ensure the token is being sent in API requests (check browser console)

### CORS Errors

- Verify your callback URLs are correctly configured in Auth0
- Check that `CORS_ALLOWED_ORIGINS` in Django settings includes your frontend URL

### Token Expiration

- Tokens are automatically refreshed using refresh tokens
- If you see authentication errors, try logging out and back in

## Security Notes

- Never commit your `.env` file to version control
- Use different Auth0 applications for development and production
- Regularly rotate your Auth0 client secrets
- Enable MFA in Auth0 for additional security

## Next Steps

- Configure user roles and permissions in Auth0
- Set up API scopes for fine-grained access control
- Implement user profile management
- Add social login providers (Google, GitHub, etc.)


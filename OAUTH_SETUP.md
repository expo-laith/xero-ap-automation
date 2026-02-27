# Xero OAuth Setup Guide

## Overview
This application now uses a proper OAuth flow to authenticate with Xero. Refresh tokens are automatically rotated and persisted to Azure storage.

## Initial Setup

### 1. Create Xero App
1. Go to https://developer.xero.com/app/manage
2. Create a new app or use existing app
3. Note your `Client ID` and `Client Secret`
4. Set redirect URI to: `https://your-app.azurewebsites.net/callback`

### 2. Upload Initial Secrets File to Azure

Create a file `/home/xero_secrets.json` on your Azure Web App with:

```json
{
  "client_id": "YOUR_XERO_CLIENT_ID",
  "client_secret": "YOUR_XERO_CLIENT_SECRET",
  "redirect_uri": "https://your-app.azurewebsites.net/callback",
  "refresh_token": "",
  "tenant_id": ""
}
```

Upload via:
- Azure Portal → App Service → SSH
- Or use FTP/FTPS
- Or use Azure CLI: `az webapp ssh`

### 3. Authorize the Application

1. Navigate to your app: `https://your-app.azurewebsites.net`
2. Click "Authorize Xero" button
3. Log in to Xero and grant permissions
4. You'll be redirected back with success message
5. The refresh token and tenant ID are now saved to `/home/xero_secrets.json`

## How It Works

### OAuth Flow
1. User clicks "Authorize Xero" → redirects to `/authorize-xero`
2. App redirects to Xero login page
3. User logs in and grants permissions
4. Xero redirects back to `/callback` with authorization code
5. App exchanges code for access token and refresh token
6. Tokens are saved to `/home/xero_secrets.json`

### Token Rotation
- Every time the app refreshes the access token, Xero may rotate the refresh token
- The new refresh token is automatically persisted to `/home/xero_secrets.json`
- This ensures the app never loses access

### Persistent Storage
- All tokens are stored in `/home/xero_secrets.json` on Azure
- The `/home` directory persists across app restarts
- No environment variables needed
- No hardcoded tokens in code

## File Structure

```
/home/xero_secrets.json          # Persistent token storage (Azure)
processor.py                      # Uses SECRETS_PATH = "/home/xero_secrets.json"
app.py                           # OAuth routes: /authorize-xero, /callback
templates/index.html             # UI with "Authorize Xero" button
```

## Troubleshooting

### "Secrets file not found"
- Upload initial secrets file to `/home/xero_secrets.json` on Azure
- Ensure it contains at least: client_id, client_secret, redirect_uri

### "Missing refresh_token"
- Click "Authorize Xero" button to complete OAuth flow
- Check that redirect_uri matches exactly in Xero app settings

### Token refresh fails
- Re-authorize by clicking "Authorize Xero" button
- This will generate a fresh refresh token

## Security Notes

This is an internal tool. For production:
- Add state parameter validation in OAuth flow
- Implement PKCE (Proof Key for Code Exchange)
- Add HTTPS enforcement
- Implement proper error handling and logging
- Consider encrypting secrets at rest

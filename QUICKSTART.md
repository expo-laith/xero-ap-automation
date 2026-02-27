# Quick Start Guide - OAuth Implementation

## What Changed?

Your Xero AP automation app now uses a proper OAuth flow instead of hardcoded refresh tokens.

## Key Changes

1. **Persistent Storage**: All tokens stored in `/home/xero_secrets.json` on Azure
2. **OAuth Flow**: Users click "Authorize Xero" button to authenticate
3. **Automatic Token Rotation**: Refresh tokens automatically rotate and persist
4. **No Environment Variables**: Everything is file-based

## Files Modified

- `processor.py` - Uses `/home/xero_secrets.json` for token storage
- `app.py` - Added `/authorize-xero` and `/callback` routes
- `templates/index.html` - Added "Authorize Xero" button
- `.gitignore` - Added xero_secrets.json to prevent accidental commits

## Files Created

- `OAUTH_SETUP.md` - Detailed OAuth setup instructions
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment guide
- `xero_secrets.json.example` - Template for secrets file
- `QUICKSTART.md` - This file

## How to Deploy

### 1. Push to GitHub
```bash
git add .
git commit -m "Implement OAuth flow with persistent token storage"
git push origin main
```

### 2. Upload Secrets to Azure
After deployment, SSH to Azure and create `/home/xero_secrets.json`:
```json
{
  "client_id": "YOUR_XERO_CLIENT_ID",
  "client_secret": "YOUR_XERO_CLIENT_SECRET",
  "redirect_uri": "https://your-app.azurewebsites.net/callback",
  "refresh_token": "",
  "tenant_id": ""
}
```

### 3. Authorize Xero
1. Visit your app: `https://your-app.azurewebsites.net`
2. Click "Authorize Xero"
3. Log in to Xero
4. Done! Tokens are now saved

## How It Works

```
User clicks "Authorize Xero"
    ↓
Redirects to Xero login
    ↓
User grants permissions
    ↓
Xero redirects to /callback
    ↓
App exchanges code for tokens
    ↓
Tokens saved to /home/xero_secrets.json
    ↓
Ready to use!
```

## Token Rotation

Every time the app refreshes the access token:
1. Xero may return a new refresh token
2. App automatically saves the new refresh token
3. Next run uses the updated token
4. No manual intervention needed

## Testing Locally

To test locally, create `xero_secrets.json` in project root:
```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8000/callback",
  "refresh_token": "",
  "tenant_id": ""
}
```

Update `SECRETS_PATH` in processor.py temporarily:
```python
SECRETS_PATH = "xero_secrets.json"  # For local testing
```

Run:
```bash
uvicorn app:app --reload
```

Visit `http://localhost:8000` and click "Authorize Xero"

**Remember to change `SECRETS_PATH` back to `/home/xero_secrets.json` before deploying!**

## Troubleshooting

### "Secrets file not found"
- Upload secrets file to `/home/xero_secrets.json` on Azure
- Ensure it has client_id, client_secret, redirect_uri

### "Missing refresh_token"
- Click "Authorize Xero" button to complete OAuth flow

### Token refresh fails
- Re-authorize by clicking "Authorize Xero"
- Check redirect_uri matches Xero app settings exactly

### App can't write to /home
- Verify Azure App Service has write permissions to /home
- Check Azure logs for permission errors

## Next Steps

1. ✅ Deploy code to Azure
2. ✅ Upload initial secrets file
3. ✅ Authorize Xero
4. ✅ Test AP process
5. ✅ Verify token rotation works

## Support

For detailed instructions, see:
- `OAUTH_SETUP.md` - Complete OAuth setup guide
- `DEPLOYMENT_CHECKLIST.md` - Deployment steps and verification

## Security Note

This is an internal tool. For production use, consider:
- Adding state parameter validation
- Implementing PKCE
- Encrypting secrets at rest
- Adding comprehensive error handling

# Google API Credentials Setup

## Step 1: Create Project
1. Go to https://console.cloud.google.com/
2. Sign in with `icc-intake@mtu.edu`
3. Click project dropdown → **New Project** 
4. Name: `RFP-Automation` → **Create**

## Step 2: Enable APIs
1. Go to **APIs & Services** → **Library**
2. Search and enable: **Gmail API**
3. Search and enable: **Google Sheets API**

## Step 3: OAuth Consent Screen
1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **Internal** (or External) → **Create**
3. Fill in:
   - App name: `RFP Automation System`
   - User support email: Your email
   - Developer contact: Your email
4. Click **Save and Continue**
5. Add scopes:
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/spreadsheets.readonly`
6. Click **Save and Continue** → **Save and Continue**

## Step 4: Create Credentials
1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `RFP Desktop Client`
5. Click **Create**

## Step 5: Download File
1. Click download icon next to your credential
2. Rename file to: `icc-intake_credentials.json`
3. Move to: `config/icc-intake_credentials.json`

## Step 6: First Authentication
```bash
python main.py --status
```
1. Browser opens automatically
2. Sign in with your account
3. Click **Advanced** → **Go to RFP Automation System (unsafe)**
4. Click **Allow**
5. Done - `token.json` created automatically

## Troubleshooting

**"Access blocked"** → Enable both APIs and configure OAuth consent screen

**"redirect_uri_mismatch"** → Use Desktop app type, delete `token.json` and retry

**"invalid_grant"** → Delete `config\token.json` and re-authenticate

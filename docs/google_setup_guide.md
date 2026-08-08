# Google Cloud Setup Guide for Jarvis

This guide walks you through setting up Google Cloud credentials so Jarvis can access Gmail, Calendar, Drive, Contacts, Tasks, Sheets, Docs, and YouTube on your behalf.

## 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it `Jarvis OS` (or anything you like)
4. Click **Create**

## 2. Enable Required APIs

Navigate to **APIs & Services → Library** and enable each of these:

| API | Search For | Purpose |
|-----|-----------|---------|
| Gmail API | `Gmail API` | Read/send emails |
| Google Calendar API | `Google Calendar API` | Read/create events |
| Google Drive API | `Google Drive API` | Search/read/upload files |
| People API | `People API` | Contact lookup |
| Google Tasks API | `Tasks API` | Task management |
| Google Sheets API | `Google Sheets API` | Spreadsheet read/write |
| Google Docs API | `Google Docs API` | Document read/create |
| YouTube Data API v3 | `YouTube Data API` | Video search/info |

## 3. Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace org)
3. Fill in:
   - **App name**: `Jarvis OS`
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes** and add:
   ```
   openid
   email
   profile
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/drive
   https://www.googleapis.com/auth/contacts.readonly
   https://www.googleapis.com/auth/tasks
   https://www.googleapis.com/auth/spreadsheets
   https://www.googleapis.com/auth/documents
   https://www.googleapis.com/auth/youtube.readonly
   ```
6. Click **Save and Continue**
7. On the **Test users** page, add your Google account email(s)
8. Click **Save and Continue**

> **Note**: While in "Testing" mode, only test users you add can authenticate. To allow any Google account, you'll need to publish the app (requires Google review for sensitive scopes).

## 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Choose **Web application**
4. Name it `Jarvis Local`
5. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:8000/api/oauth/auth/google/callback
   http://127.0.0.1:8000/api/oauth/auth/google/callback
   ```
6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

## 5. Configure Jarvis

Add the credentials to your `.env` file in the project root:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

## 6. Restart Jarvis

```bash
python -m jarvis serve --reload
```

Then go to **Settings → Integrations → Google Workspace** and click **Connect to Google**.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Access blocked: This app's request is invalid" | Check your redirect URIs match exactly |
| "Error 403: access_denied" | Add your email to test users in the consent screen |
| "Token has been expired or revoked" | Disconnect and reconnect your Google account in Jarvis Settings |
| Scopes not granted | Delete the account in Jarvis, then reconnect — Google only prompts for new scopes on fresh consent |

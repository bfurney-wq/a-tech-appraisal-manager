# A-Tech Appraisal Manager

Internal order management and AI-powered report writing tool for A-Tech Appraisal Co., LLC.

## Quick Start (Local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Deploy to Streamlit Cloud (Free)

1. Push this folder to a new GitHub repo
2. Go to https://share.streamlit.io
3. Click "New app" â connect your GitHub â select this repo â set `app.py` as the main file
4. Click Deploy
5. Once live, go to the Settings tab in the app to add your OpenAI API key and Gmail credentials

## Setup After Deploy

### OpenAI API Key (for AI report writing)
1. Go to https://platform.openai.com/api-keys
2. Create a new key
3. Paste it in the app's Settings tab

### Gmail App Password (for auto-emails)
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication if not already on
3. Go to App Passwords â create one for "Mail"
4. Paste the 16-character password in the app's Settings tab

## Features

- **Order Pipeline** â track appraisals from intake to completion
- **AI Narrative Writer** â GPT-4o generates USPAP-compliant UAD narratives from field notes
- **Auto-Email** â clients get notified automatically when appraisals complete
- **XML Export** â export order data for TOTAL import
- **Photo Management** â upload and view property photos per order
- **Activity Log** â full audit trail of all actions
- **Search & Filter** â find orders by status, appraiser, address, or client

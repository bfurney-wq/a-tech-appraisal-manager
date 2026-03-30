
# AppraisalOS

Internal appraisal order management and AI report writing tool for A-Tech Appraisal Co.

## Features

- Local user authentication with hashed passwords
- Order intake with document extraction (engagement letters, P&S agreements)
- Section-by-section AI report drafting with facts-only guardrails
- Editable report sections saved to database with review status tracking
- QC checklist and revision tracking with AI-assisted revision responses
- Short-term rental income analysis (external STR generator)
- AI Advisor for USPAP, Fannie Mae, FHA/HUD questions
- Built-in calculators (GLA, Net/Gross adjustment)
- External tool links (MLS Grid, FEMA Flood Maps, County Records, Census)
- Workfile bundle export (order JSON, sections, QC, activity, files)
- Activity log and status history
- Legacy database migration support

## Demo login

- Email: `demo@appraisalos.local`
- Password: `demo123`

## Secrets

Use `.streamlit/secrets.toml` or environment variables:

```toml
OPENAI_API_KEY = "sk-..."
```

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Honest limitations

This project does not pretend to be a validated UAD 3.6 delivery engine.
It exports a real workfile bundle instead. For production UAD delivery,
build that as a separate verified module with schema validation and lender testing.

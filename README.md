# ExamGuard – Online Exam Monitoring & Analytics Platform

ExamGuard is an academic/internship-grade Flask application for online-exam monitoring and integrity analytics.

## Stack
Flask, Flask-SQLAlchemy, SQLite, OpenCV, Pandas, NumPy, Scikit-learn, Matplotlib, Seaborn, Faker and LangChain/OpenAI.

## Demo accounts
- Manager: `manager@examguard.com` / `manager123`
- Admin: `admin@examguard.com` / `admin123`
- Candidate: `candidate@examguard.com` / `candidate123`

## Run on Windows

```powershell
cd C:\path	o\examguard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

The application factory no longer runs at import time. The SQLite database is created/rebuilt when the application starts. If an incompatible legacy schema is detected, the academic/demo migration strategy rebuilds the database so missing-column errors are avoided.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Integrity scoring

Configured in `config.py`:

- Face absence = 10
- Multiple faces = 30
- Tab switch = 10
- Focus loss = 5
- Fullscreen exit = 10
- Low risk: 80–100
- Medium risk: 50–79
- High risk: 0–49

Scores are monitoring indicators for authorized human invigilator review and are not automatic findings of misconduct.

## AI report

Every report uses these five required sections:

1. SESSION SUMMARY
2. MONITORING OBSERVATIONS
3. INTEGRITY ANALYSIS
4. RISK INDICATORS
5. INVIGILATOR REVIEW NOTES

If no `OPENAI_API_KEY` is available, or an LLM call fails/returns an invalid structure, ExamGuard uses the deterministic report generator.

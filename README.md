# ExamGuard — Online Exam Monitoring & Analytics Platform

ExamGuard is a Python/Flask-based online examination monitoring and integrity analytics platform developed as an internship project.

The system combines candidate authentication, examination session management, OpenCV-based face-presence monitoring, browser/session event logging, rule-based suspicious-event detection, integrity scoring, analytics, evidence management, and AI-assisted integrity reports.

> **Important:** Monitoring events and integrity scores are indicators for authorized human review. They are not automatic findings of misconduct.

## Project Objectives

- Provide a web-based platform for online examination monitoring.
- Manage candidate authentication and examination sessions.
- Monitor face presence using OpenCV Haar Cascade.
- Record relevant browser/session activity with timestamps.
- Detect predefined suspicious event patterns using transparent rules.
- Calculate an integrity/risk indicator from monitoring events.
- Provide analytics and visualizations for examination sessions.
- Maintain evidence and event records.
- Generate session-level integrity reports.
- Provide reporting/export capabilities for authorized users.

## Major Modules

1. **Candidate Authentication & Session Management** — candidate registration/login, roles, and exam-session lifecycle.
2. **Face Presence Monitoring** — webcam frame processing and face-presence tracking using OpenCV Haar Cascade.
3. **Browser Activity & Event Logging** — records supported focus, tab, fullscreen, and session events.
4. **Suspicious Event Detection Engine** — applies configurable rules to monitoring events.
5. **Integrity Scoring Module** — converts selected monitoring signals into a normalized integrity score and risk level.
6. **AI Integrity Report Agent** — produces structured natural-language session summaries using LangChain/LLM when configured.
7. **Data Science & Analytics** — session statistics, score distributions, event frequencies, visualizations, and exploratory clustering.
8. **Alert & Evidence Management** — stores monitoring evidence and incident-related records.
9. **Examination Monitoring Dashboard** — provides KPI cards, charts, session information, and monitoring views.
10. **Reporting & Export** — supports session/report information and data export.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Flask | Web application/backend |
| Flask-SQLAlchemy / SQLAlchemy | Database integration |
| SQLite | Persistent relational storage |
| OpenCV | Webcam processing and face detection |
| Pandas | Data processing and analytics |
| NumPy | Numerical operations |
| Scikit-learn | K-Means clustering / exploratory analytics |
| Matplotlib / Seaborn | Data visualization |
| LangChain / LangChain OpenAI | AI-assisted integrity reports |
| HTML / CSS / JavaScript | Web interface |
| Faker | Synthetic test-data generation |
| Git / GitHub | Version control and project management |

## Project Structure

```text
Online-Exam-Monitoring-System/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── LICENSE
│
├── ai/
├── analytics/
├── assets/
├── auth/
├── data/
├── database/
├── evidence/
├── models/
├── monitoring/
├── routes/
├── scoring/
├── static/
├── templates/
├── tests/
└── utils/
```

### Important directories

- `ai/` — AI integrity/report agents
- `analytics/` — KPI calculations, scoring analytics, clustering and visualizations
- `auth/` — authentication and security logic
- `database/` — database setup and models
- `monitoring/` — face monitoring, browser monitoring and suspicious-event detection
- `routes/` — Flask route modules
- `scoring/` — integrity scoring and suspicious-event logic
- `tests/` — automated tests
- `templates/` — HTML pages
- `static/` — CSS and JavaScript assets
- `assets/haarcascades/` — OpenCV Haar Cascade model file

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/VindhyaSri803/Online-Exam-Monitoring-System.git
cd Online-Exam-Monitoring-System
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

If PowerShell blocks script activation, you can use the virtual-environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Alternatively, activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Environment configuration

Copy `.env.example` to `.env` and configure any optional API settings required by the AI report functionality.

The application can use a deterministic report generator when an LLM/API configuration is unavailable.

### 5. Run the application

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Demo Accounts

The development/demo configuration provides:

| Role | Email | Password |
|---|---|---|
| Manager | `manager@examguard.com` | `manager123` |
| Invigilator/Admin | `admin@examguard.com` | `admin123` |
| Candidate | `candidate@examguard.com` | `candidate123` |

For real deployment, replace demo credentials with secure account management and stronger authentication controls.

## Integrity Scoring

The project uses weighted monitoring indicators to calculate an integrity-oriented score.

Current documented indicators include:

| Monitoring event | Weight |
|---|---:|
| Face absence | 10 |
| Multiple faces | 30 |
| Tab switch | 10 |
| Focus loss | 5 |
| Fullscreen exit | 10 |

Risk levels are represented as:

- **Low:** 80–100
- **Medium:** 50–79
- **High:** 0–49

These values are monitoring indicators intended to support authorized invigilator review.

## Analytics

The dashboard analytics include:

- Integrity score distribution
- Risk-level distribution
- Event frequency
- Face-presence ratio distribution
- Suspicious-event rule breakdown
- Integrity score vs. suspicious-event scatter analysis
- Session-level summaries
- Exploratory K-Means clustering where sufficient data are available

## AI Integrity Reports

The AI report workflow is designed around five sections:

1. SESSION SUMMARY
2. MONITORING OBSERVATIONS
3. INTEGRITY ANALYSIS
4. RISK INDICATORS
5. INVIGILATOR REVIEW NOTES

If an LLM/API call is unavailable or fails, the application can fall back to a deterministic report generator.

## Testing

Run the automated tests with:

```powershell
python -m unittest discover -s tests -v
```

The `tests/` directory contains tests covering areas such as:

- Authentication
- Monitoring
- Integrity scoring
- Analytics
- AI reporting

## Agile Documentation

Agile project records are maintained separately in the `agile/` directory:

```text
agile/
├── Online_Exam_Monitoring_Sprint_Backlog_Milestones_1_to_4.xlsx
├── Defect_Tracking.xlsx
└── Unit_Test_Plan.xlsx
```

The sprint backlog tracks user stories, MoSCoW priority, dependencies, assignees, sprint/milestone and completion status.

## Project Documentation

The complete internship project report is maintained in:

```text
docs/
└── ExamGuard_Internship_Project_Documentation.docx
```

The report covers:

- Internship overview
- Problem statement
- Project idea and motivation
- Proposed solution
- Objectives and scope
- Technologies
- System architecture
- Major modules
- Development milestones
- Challenges and solutions
- Testing and analytics
- Conclusion and future scope

## Milestones

### Milestone 1
- System architecture
- SQLite database
- Candidate authentication
- Candidate photo capture
- Synthetic session/activity data

### Milestone 2
- Haar Cascade face monitoring
- Browser/session activity logging
- Suspicious-event detection

### Milestone 3
- Integrity scoring
- Data analytics
- Visualizations
- K-Means exploratory analysis
- AI report workflow
- Evidence management

### Milestone 4
- Module integration
- Testing and defect fixing
- Dashboard and reporting
- Repository preparation
- Final documentation and validation

## Privacy and Security Notes

The prototype is intended for controlled academic/internship demonstration.

A production deployment would require additional measures including:

- Explicit candidate consent
- Stronger authentication
- Role-based authorization
- Secure/encrypted evidence storage
- Appropriate data-retention policies
- Audit logging
- Privacy controls
- Scalability and performance testing

## License

This project is released under the MIT License. See `LICENSE` for details.

## Project Status

The project has been developed as an internship prototype with integrated monitoring, analytics, reporting, testing and documentation components.

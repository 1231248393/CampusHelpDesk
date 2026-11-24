CampusHelpDesk Phase 6.2 - AI-assisted complaint triage

This patch preserves the existing React + Vite student UI, Flask API, MySQL
schema, JWT student/admin separation, and existing complaint endpoints.

Features:
- Draft complaint analysis endpoint: POST /api/complaints/analyze
- Suggested category, priority and sentiment
- Similarity suggestions against only the logged-in student's own previous
  complaints (maximum 100 latest records)
- Student form button: Analyze with AI
- Existing complaint submission still requires the student to submit manually

IMPORTANT ACCURACY NOTE:
This is an explainable keyword/rule-based prototype, not a trained ML model.
It does not automatically change saved complaints or admin status. Review
suggestions before submission. A properly trained model needs a labelled,
representative complaint dataset and evaluation.

APPLY ON UBUNTU:
1. Stop the running project (Ctrl+C in its terminals, or use your existing
   campus.sh stop command if available).
2. Back up the exact files:
   cd ~/CampusHelpDesk
   cp backend/app.py backend/app.py.phase6-backup
   cp frontend/src/App.jsx frontend/src/App.jsx.phase6-backup
   [If backend/complaint_ai.py exists, back it up too.]
3. Extract this ZIP. Copy its contents into the matching project paths,
   preserving the backend/ and frontend/ folder structure.
   Example if extracted to ~/Downloads/CampusHelpDesk-Phase6.2-patch:
   cp ~/Downloads/CampusHelpDesk-Phase6.2-patch/backend/app.py backend/app.py
   cp ~/Downloads/CampusHelpDesk-Phase6.2-patch/backend/complaint_ai.py backend/complaint_ai.py
   cp ~/Downloads/CampusHelpDesk-Phase6.2-patch/backend/seed_students.py backend/seed_students.py
   cp ~/Downloads/CampusHelpDesk-Phase6.2-patch/frontend/src/App.jsx frontend/src/App.jsx
4. No database migration is required for this phase.
5. Start backend using your existing run method. Start the existing student and
   admin frontends on their configured ports (do not start duplicate servers).
6. Log in as a student, open Submit New Complaint, enter title and description,
   then click Analyze with AI. Confirm the suggestions and submit normally.

BACKEND QUICK CHECK:
From backend/ with the project's virtual environment active:
  python -m py_compile app.py complaint_ai.py seed_students.py
  curl -i http://127.0.0.1:5000/api/health

The analyze endpoint requires the student's existing Bearer JWT. It does not
accept anonymous requests and does not expose other students' complaint data.

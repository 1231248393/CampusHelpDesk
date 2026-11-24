# CampusHelpDesk Phase 7 – Safe Upgrade Status

## Safety contract
- This release is an incremental patch; it does not replace the project or database.
- Existing student/admin authentication, complaint APIs, complaint records, and current portal routes are preserved.
- Migration `004_phase7_foundation.sql` is additive (`CREATE TABLE IF NOT EXISTS`) and is safe to re-run.
- The migration is NOT run automatically. Back up MySQL first and apply it manually only if it has not already been applied.
- The existing complaint triage remains rule-based/advisory. No trained-ML accuracy is claimed.

## Implemented in this release

### Admin portal
- Existing Phase 7.1 priority editing, activity history and filtered CSV export retained.
- Admin complaint details now list evidence attachments and provide authenticated downloads.
- Existing analytics and complaint status management retained.

### Student portal
- Each complaint now has a Track action with its status/priority change timeline.
- Students can optionally attach one PDF, PNG or JPEG (max 5 MB) when submitting a complaint.
- Uploads are extension-allowlisted, signature-checked, stored under randomized server filenames, and are not served as public static files.
- Students can download only attachments belonging to their own complaints.
- Students can rate a complaint after it reaches Resolved and optionally leave a comment.
- Existing login, registration, notifications, complaint submission, filtering and refresh flows retained.

### Backend APIs added
- `GET /api/student/complaints/<id>/history`
- `GET|POST /api/student/complaints/<id>/feedback`
- `GET|POST /api/student/complaints/<id>/attachments`
- `GET /api/student/attachments/<id>/download`
- `GET /api/admin/complaints/<id>/attachments`
- `GET /api/admin/attachments/<id>/download`

All new routes require JWT authentication and verify student ownership or administrator role.

## Remaining Phase 7 work
- 7.2: staff login, role-based staff workspace, department administration and complaint assignment workflow.
- 7.3: date-range analytics, department metrics and PDF/XLSX reports. Current dashboard charts and CSV export are present.
- 7.4: additional threaded comments, admin replies and richer notification centre. Attachments, timeline and resolution feedback are implemented in this release.
- 7.5: a real trained/evaluated ML pipeline requires an approved labelled dataset and evaluation. Current triage is rule-based only.
- 7.6: full DB-backed integration/security tests, audit-log wiring, restore rehearsal and deployment hardening.

## Verification performed in the build environment
- Student Vite production build: PASS.
- Admin Vite production build: PASS.
- Python syntax compilation for `backend/app.py`, migration runner and AI helper: PASS.
- Live MySQL integration, real authenticated uploads/downloads and browser end-to-end tests: NOT run in this environment.

## Database migration
Migration `004_phase7_foundation.sql` creates the tables needed for departments/staff, assignments, comments, feedback, attachments and audit logs. It does not alter or delete existing complaint/student/admin rows. Back up the database before applying it.

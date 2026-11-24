# CampusHelpDesk – Phase 7 Safe Upgrade (Student + Admin)

This is an incremental patch for the existing CampusHelpDesk project. It preserves the two separate portals and the existing authentication/complaint workflows.

## New visible features

### Student portal (`localhost:5174`)
- **Track** button on each complaint opens a timeline of status and priority changes.
- Optional evidence upload while submitting a complaint: PDF, PNG or JPEG, max 5 MB.
- Authenticated attachment download for the complaint owner.
- Five-star resolution feedback and optional comment after a complaint is marked Resolved.

### Admin portal (`localhost:5175`)
- Existing analytics, CSV export, priority editing and complaint history are retained.
- Complaint details can list and download student evidence attachments.

### Backend (`localhost:5000`)
New JWT-protected student history, feedback and attachment endpoints, plus admin-only attachment listing/download endpoints. Students can access only their own complaints and files.

## Apply safely

1. Extract this patch ZIP.
2. Run the included installer. Default target is `~/CampusHelpDesk`:

   ```bash
   chmod +x apply_phase7_patch.sh
   ./apply_phase7_patch.sh
   ```

   Or specify a project path:

   ```bash
   ./apply_phase7_patch.sh /path/to/CampusHelpDesk
   ```

   The installer backs up every destination file into `backups/phase7-safe-patch-<timestamp>/` before copying. It does not touch `.env`, node_modules, venv, or database contents.

3. If migration 004 has not already been applied, back up MySQL first:

   ```bash
   cd ~/CampusHelpDesk/backend
   ./backup_database.sh
   ./venv/bin/python apply_migrations.py
   ```

   If migration 004 was already applied, do not needlessly rerun the full migration runner; the migration itself uses `CREATE TABLE IF NOT EXISTS` and is re-runnable.

4. Build both portals:

   ```bash
   cd ~/CampusHelpDesk/frontend && pnpm install && pnpm build
   cd ~/CampusHelpDesk/admin-frontend && pnpm install && pnpm build
   ```

5. Restart services:

   ```bash
   cd ~/CampusHelpDesk
   ./stop.sh
   ./start.sh
   ```

6. Test:
   - Student: open a complaint with **Track**; submit a new complaint with an optional PDF/JPEG/PNG attachment; mark a test complaint Resolved from admin and submit feedback as the student.
   - Admin: open the same complaint and confirm the attachment appears and downloads.
   - Confirm both logins and existing complaint records remain intact.

## Safety and limitations
- The original ZIP and your live local project are not modified by ChatGPT; the installer changes the target only when you run it.
- The installer creates file backups first.
- Migration 004 is additive. No `DROP`, `TRUNCATE`, or delete of existing complaints is used.
- Uploaded files are stored in `backend/uploads/complaints/` with random server-side names and are served only through authenticated routes.
- Current AI triage is rule-based/advisory, not a trained ML model.
- This release does not complete every Phase 7 roadmap item. Staff login/assignment, PDF/XLSX reporting, trained ML, comment threads, audit wiring and production security testing remain follow-up work.
- Builds and Python syntax checks passed here. Live MySQL/API/browser integration tests must still be run on your Ubuntu machine.

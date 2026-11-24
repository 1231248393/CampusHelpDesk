-- CampusHelpDesk Phase 7 foundation (additive only).
-- Safe to re-run. Does not alter, rename, delete, or truncate existing records.
-- Apply after migrations 001, 002, and 003.

CREATE TABLE IF NOT EXISTS departments (
  department_id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  description VARCHAR(500) NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (department_id),
  UNIQUE KEY uq_departments_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staff_members (
  staff_id INT NOT NULL AUTO_INCREMENT,
  department_id INT NULL,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL,
  username VARCHAR(80) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login TIMESTAMP NULL DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (staff_id),
  UNIQUE KEY uq_staff_email (email),
  UNIQUE KEY uq_staff_username (username),
  KEY idx_staff_department (department_id),
  CONSTRAINT fk_staff_department FOREIGN KEY (department_id)
    REFERENCES departments (department_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_assignments (
  assignment_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  department_id INT NULL,
  staff_id INT NULL,
  assigned_by_admin_id INT NULL,
  notes VARCHAR(1000) NULL,
  is_current BOOLEAN NOT NULL DEFAULT TRUE,
  assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (assignment_id),
  KEY idx_assignment_complaint_current (complaint_id, is_current),
  KEY idx_assignment_staff_current (staff_id, is_current),
  CONSTRAINT fk_assignment_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE,
  CONSTRAINT fk_assignment_department FOREIGN KEY (department_id)
    REFERENCES departments (department_id) ON DELETE SET NULL,
  CONSTRAINT fk_assignment_staff FOREIGN KEY (staff_id)
    REFERENCES staff_members (staff_id) ON DELETE SET NULL,
  CONSTRAINT fk_assignment_admin FOREIGN KEY (assigned_by_admin_id)
    REFERENCES admins (admin_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_comments (
  comment_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  author_role ENUM('admin','staff','student') NOT NULL,
  author_id INT NOT NULL,
  visibility ENUM('student','internal') NOT NULL DEFAULT 'student',
  message TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (comment_id),
  KEY idx_comments_complaint_created (complaint_id, created_at),
  CONSTRAINT fk_comment_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_feedback (
  feedback_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  student_id INT NOT NULL,
  rating TINYINT UNSIGNED NOT NULL,
  comment VARCHAR(1000) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (feedback_id),
  UNIQUE KEY uq_feedback_complaint_student (complaint_id, student_id),
  KEY idx_feedback_created (created_at),
  CONSTRAINT chk_feedback_rating CHECK (rating BETWEEN 1 AND 5),
  CONSTRAINT fk_feedback_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE,
  CONSTRAINT fk_feedback_student FOREIGN KEY (student_id)
    REFERENCES students (student_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_attachments (
  attachment_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  student_id INT NULL,
  original_name VARCHAR(255) NOT NULL,
  storage_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(120) NOT NULL,
  file_size BIGINT UNSIGNED NOT NULL,
  sha256 CHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (attachment_id),
  KEY idx_attachments_complaint (complaint_id),
  CONSTRAINT fk_attachment_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE,
  CONSTRAINT fk_attachment_student FOREIGN KEY (student_id)
    REFERENCES students (student_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGINT NOT NULL AUTO_INCREMENT,
  actor_role ENUM('admin','staff','student','system') NOT NULL,
  actor_id INT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id VARCHAR(80) NULL,
  details JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (audit_id),
  KEY idx_audit_entity (entity_type, entity_id),
  KEY idx_audit_actor (actor_role, actor_id),
  KEY idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- CampusHelpDesk Phase 6 database upgrade.
-- Safe to run repeatedly: all tables and indexes use IF NOT EXISTS.
-- Run only after migrations 001_admin_auth.sql and 002_student_accounts.sql.

CREATE TABLE IF NOT EXISTS complaint_ai_reviews (
  review_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  suggested_category VARCHAR(100) NULL,
  suggested_department VARCHAR(150) NULL,
  suggested_priority VARCHAR(20) NULL,
  sentiment VARCHAR(30) NULL,
  model_type VARCHAR(80) NOT NULL DEFAULT 'transparent-rule-based-v1',
  confidence DECIMAL(4,3) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (review_id),
  KEY idx_ai_reviews_complaint_latest (complaint_id, review_id),
  CONSTRAINT fk_ai_review_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
  notification_id BIGINT NOT NULL AUTO_INCREMENT,
  student_id INT NOT NULL,
  complaint_id INT NULL,
  title VARCHAR(160) NOT NULL,
  message VARCHAR(500) NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (notification_id),
  KEY idx_notifications_student_created (student_id, created_at),
  KEY idx_notifications_complaint (complaint_id),
  CONSTRAINT fk_notification_student FOREIGN KEY (student_id)
    REFERENCES students (student_id) ON DELETE CASCADE,
  CONSTRAINT fk_notification_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS complaint_status_history (
  history_id BIGINT NOT NULL AUTO_INCREMENT,
  complaint_id INT NOT NULL,
  admin_id INT NULL,
  change_type ENUM('status','priority') NOT NULL,
  old_value VARCHAR(40) NULL,
  new_value VARCHAR(40) NOT NULL,
  changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (history_id),
  KEY idx_complaint_history (complaint_id, changed_at),
  CONSTRAINT fk_history_complaint FOREIGN KEY (complaint_id)
    REFERENCES complaints (complaint_id) ON DELETE CASCADE,
  CONSTRAINT fk_history_admin FOREIGN KEY (admin_id)
    REFERENCES admins (admin_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

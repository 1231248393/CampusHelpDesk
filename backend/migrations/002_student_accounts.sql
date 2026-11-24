-- Student accounts and private complaint ownership.
-- Run once against campus_helpdesk. Existing complaint rows are preserved.
CREATE TABLE IF NOT EXISTS students (
  student_id INT NOT NULL AUTO_INCREMENT,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL,
  roll_number VARCHAR(50) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login TIMESTAMP NULL DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (student_id),
  UNIQUE KEY uq_students_email (email),
  UNIQUE KEY uq_students_roll_number (roll_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add student_id only when the existing complaints table does not have it.
SET @has_student_id = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'complaints'
    AND COLUMN_NAME = 'student_id'
);
SET @student_id_ddl = IF(
  @has_student_id = 0,
  'ALTER TABLE complaints ADD COLUMN student_id INT NULL AFTER complaint_id',
  'SELECT 1'
);
PREPARE student_id_stmt FROM @student_id_ddl;
EXECUTE student_id_stmt;
DEALLOCATE PREPARE student_id_stmt;

SET @has_student_index = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'complaints'
    AND INDEX_NAME = 'idx_complaints_student_id'
);
SET @student_index_ddl = IF(
  @has_student_index = 0,
  'CREATE INDEX idx_complaints_student_id ON complaints (student_id)',
  'SELECT 1'
);
PREPARE student_index_stmt FROM @student_index_ddl;
EXECUTE student_index_stmt;
DEALLOCATE PREPARE student_index_stmt;

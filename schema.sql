-- Create database (run this once in MySQL Workbench)
CREATE DATABASE IF NOT EXISTS event_mini CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE event_mini;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events table (sample data)
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    event_date DATE NOT NULL,
    description TEXT
);

-- Registrations table
CREATE TABLE IF NOT EXISTS registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_user_event (user_id, event_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Seed a few sample events
INSERT INTO events (title, event_date, description) VALUES
('Tech Talk: Intro to AI', DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'A friendly intro to AI basics.'),
('Workshop: Web Dev 101', DATE_ADD(CURDATE(), INTERVAL 14 DAY), 'Hands-on HTML/CSS/JS workshop.'),
('Career Q&A with Alumni', DATE_ADD(CURDATE(), INTERVAL 21 DAY), 'Ask anything about career paths.')
ON DUPLICATE KEY UPDATE description = VALUES(description);
SELECT * FROM events;
SET SQL_SAFE_UPDATES = 0;
DELETE FROM events
WHERE id NOT IN (
    SELECT min_id
    FROM (
        SELECT MIN(id) AS min_id
        FROM events
        GROUP BY title, event_date
    ) AS keepers
);
SET SQL_SAFE_UPDATES = 1;


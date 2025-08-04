-- Fix database schema issues

-- Add missing columns to occurrences table
ALTER TABLE occurrences ADD COLUMN IF NOT EXISTS color VARCHAR(7) DEFAULT '#ef4444';
ALTER TABLE occurrences ADD COLUMN IF NOT EXISTS is_span BOOLEAN DEFAULT FALSE;
ALTER TABLE occurrences ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE occurrences ADD COLUMN IF NOT EXISTS end_date DATE;

-- Create global_events table if it doesn't exist
CREATE TABLE IF NOT EXISTS global_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    color VARCHAR(7) DEFAULT '#ef4444',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add some sample data for testing
INSERT INTO global_events (user_id, title, description, date, color) VALUES 
    (1, 'World War II', 'Global conflict from 1939-1945', '1939-09-01', '#dc2626'),
    (1, 'Moon Landing', 'First human steps on the moon', '1969-07-20', '#2563eb'),
    (1, 'Internet Created', 'ARPANET becomes operational', '1969-10-29', '#059669')
ON CONFLICT DO NOTHING;

-- Add some sample timelines if they don't exist
INSERT INTO timelines (user_id, title, description, start_date, end_date) VALUES 
    (1, 'My Life', 'Personal timeline of important events', '1990-01-01', '2025-12-31'),
    (1, 'Career Journey', 'Professional milestones and achievements', '2010-01-01', '2025-12-31'),
    (1, 'Project Timeline', 'Development timeline for current project', '2024-01-01', '2025-12-31')
ON CONFLICT DO NOTHING;

-- Add some sample occurrences
INSERT INTO occurrences (timeline_id, title, description, date, color) VALUES 
    (1, 'Graduation', 'Completed university degree', '2015-05-15', '#059669'),
    (1, 'First Job', 'Started first professional position', '2016-06-01', '#2563eb'),
    (1, 'Marriage', 'Wedding day', '2020-08-15', '#dc2626'),
    (2, 'Promotion', 'Advanced to senior position', '2022-03-01', '#059669'),
    (2, 'New Company', 'Started at new organization', '2023-01-15', '#2563eb')
ON CONFLICT DO NOTHING; 
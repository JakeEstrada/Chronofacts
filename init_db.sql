DROP TABLE IF EXISTS media_chunks, media, messages, occurrences, global_events, timelines, users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE timelines (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT,
    description TEXT,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE spans (
    id SERIAL PRIMARY KEY,
    timeline_id INTEGER NOT NULL REFERENCES timelines(id),
    title TEXT,
    start_date DATE,
    end_date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE occurrences (
    id SERIAL PRIMARY KEY,
    timeline_id INTEGER NOT NULL REFERENCES timelines(id),
    title TEXT,
    date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title TEXT,
    date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE timeline_events (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id),
    timeline_id INTEGER NOT NULL REFERENCES timelines(id),
    added_by_user_id INTEGER REFERENCES users(id)
);

CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    span_id INTEGER REFERENCES spans(id),
    occurrence_id INTEGER REFERENCES occurrences(id),
    event_id INTEGER REFERENCES events(id),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (span_id IS NOT NULL)::int +
        (occurrence_id IS NOT NULL)::int +
        (event_id IS NOT NULL)::int = 1
    )
);

CREATE TABLE media (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    file_url VARCHAR(255),
    file_type VARCHAR(50), -- e.g., "mp3", "mp4", "pdf", "jpg"
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE media_chunks (
    id SERIAL PRIMARY KEY,
    upload_id VARCHAR(255),  -- UUID for the upload session
    chunk_index INTEGER,     -- e.g., 0, 1, 2, ...
    data BYTEA,              -- or use file_path TEXT if using disk
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add a default admin user
INSERT INTO users (username, password_hash, email) VALUES 
        ('admin', '$2b$12$eol0Z2p4NwwOTkZ58jg4PuyN4Mwsq9GY5fHSQKKgMn/pwzlve8jxq', 'liminalInnovation@gmail.com'), 
        ('viewer', '$2b$12$xveP7AntaOSzJneYK6mUp.//N0lvpQpoRNNFh4hIsGLT6asbGheGe', 'JakeEstrada4@gmail.com')
;

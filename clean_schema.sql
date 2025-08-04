-- Clean database schema based on user requirements
DROP TABLE IF EXISTS media_chunks, media, instances, occurrences, spans, timelines, users CASCADE;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Timelines table
CREATE TABLE timelines (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    start_date DATE,
    end_date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spans table
CREATE TABLE spans (
    id SERIAL PRIMARY KEY,
    timeline_id INTEGER NOT NULL REFERENCES timelines(id),
    title VARCHAR(255),
    start_date DATE,
    end_date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Occurrences table
CREATE TABLE occurrences (
    id SERIAL PRIMARY KEY,
    timeline_id INTEGER NOT NULL REFERENCES timelines(id),
    title VARCHAR(255),
    date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Instances table
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    span_id INTEGER REFERENCES spans(id),
    occurrence_id INTEGER REFERENCES occurrences(id),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (span_id IS NOT NULL)::int +
        (occurrence_id IS NOT NULL)::int = 1
    )
);

-- Media table
CREATE TABLE media (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    file_url VARCHAR(255),
    file_type VARCHAR(50),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Media chunks table
CREATE TABLE media_chunks (
    id SERIAL PRIMARY KEY,
    upload_id VARCHAR(255),
    chunk_index INTEGER,
    data BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add default users
INSERT INTO users (username, password_hash, email) VALUES 
    ('admin', '$2b$12$eol0Z2p4NwwOTkZ58jg4PuyN4Mwsq9GY5fHSQKKgMn/pwzlve8jxq', 'liminalInnovation@gmail.com'), 
    ('viewer', '$2b$12$xveP7AntaOSzJneYK6mUp.//N0lvpQpoRNNFh4hIsGLT6asbGheGe', 'JakeEstrada4@gmail.com')
ON CONFLICT DO NOTHING; 
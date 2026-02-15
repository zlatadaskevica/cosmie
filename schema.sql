-- SQL schema for Supabase PostgreSQL

-- Store unique users with hashed passwords.
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Store user-level API preferences linked by user_id.
CREATE TABLE IF NOT EXISTS preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_code VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT unique_user_api_preference UNIQUE (user_id, api_code)
);

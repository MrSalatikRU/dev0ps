ALTER ROLE postgres PASSWORD 'postgres';

CREATE DATABASE IF NOT EXISTS db_telegram_bot;

\c db_telegram_bot;

CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS phones (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(255) NOT NULL
);
ALTER ROLE postgres PASSWORD 'postgres';

CREATE USER repl_user WITH REPLICATION ENCRYPTED PASSWORD 'repl_user';
SELECT pg_create_physical_replication_slot('replication_slot');

\c db_telegram_bot;

CREATE EXTENSION file_fdw;
CREATE SERVER pglog FOREIGN DATA WRAPPER file_fdw;

CREATE FOREIGN TABLE pglog (
    log_line text
) SERVER pglog OPTIONS (filename 'log/pglog.log', format 'text');

CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS phones (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(255) NOT NULL
);

CREATE TABLE hba ( lines text ); 
COPY hba FROM '/var/lib/postgresql/data/pg_hba.conf'; 
INSERT INTO hba (lines) VALUES ('host replication repl_user 0.0.0.0/0 md5'); 
COPY hba TO '/var/lib/postgresql/data/pg_hba.conf'; 
SELECT pg_reload_conf();
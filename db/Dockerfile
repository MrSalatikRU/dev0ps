FROM postgres:16

RUN mkdir -p /oracle/pg_data/archive
RUN chown -R postgres /oracle/pg_data/archive

COPY init.sql docker-entrypoint-initdb.d/init.sql

EXPOSE $DB_PORT
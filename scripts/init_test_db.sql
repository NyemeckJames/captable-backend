-- Runs once, on first initialisation of the postgres volume.
-- The suite needs a database of its own: integration tests create and drop the
-- whole schema, which must never happen against the working database.
CREATE DATABASE captable_test;

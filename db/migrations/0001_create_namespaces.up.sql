-- Spec 05 foundation: create the four empty domain namespaces.
-- No domain tables, run-history tables or source-dependent objects are created.
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;

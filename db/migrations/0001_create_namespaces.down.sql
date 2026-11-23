-- Roll back only the namespaces created by 0001.
-- RESTRICT (the default) prevents silently dropping any later domain objects.
DROP SCHEMA IF EXISTS ops RESTRICT;
DROP SCHEMA IF EXISTS gold RESTRICT;
DROP SCHEMA IF EXISTS silver RESTRICT;
DROP SCHEMA IF EXISTS bronze RESTRICT;

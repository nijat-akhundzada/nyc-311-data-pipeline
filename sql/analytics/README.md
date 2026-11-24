# Gold analytics

Run from the checkout with PostgreSQL `psql` and the configured migrated pipeline database:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/analytics/01_agency_volume.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/analytics/02_complaint_monthly_trends.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/analytics/03_borough_distribution.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/analytics/04_resolution_by_agency.sql
```

These analyze the actually published creation cohort, not all NYC requests or historical
backlog. Date roles use UTC calendar dates. Unknown categories remain SQL NULL. Resolution
metrics use eligible recorded closures with explicit denominators and missing-date counts;
they are not official SLA fulfillment or causal agency rankings. Do not join every SCD2
version into current-fact volume queries. Zero prior-month volume gives NULL percentage change.

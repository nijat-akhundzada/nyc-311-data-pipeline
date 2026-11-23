# Source smoke test — PARTIAL; ADR approval still blocked

Source: NYC Open Data / Socrata `erm2-nwe9`, `https://data.cityofnewyork.us/resource/erm2-nwe9.json`.

## Current conclusions

- **Volume:** earlier live count proves 3,655,759 raw rows in the 2025 local-calendar span. No validated/loaded fact count is claimed.
- **503 diagnosis:** basic and ordered reads now succeed; invalid columns produce a distinct HTTP 400 `query.soql.no-such-column`. A system-field identity query still returned 503. This rules out a blanket lack of SELECT/order/system-field support, but does not identify the server-side cause. DNS errors/timeouts are separate transport failures. No Retry-After header appeared on the captured 503; 429 behavior was not induced.
- **Creation pagination:** first three rows plus the three after cursor `(2025-01-01T00:00:17.000, 63581480)` exactly equal the six-row reference. At timestamp `2025-01-01T00:00:50.000`, two ordered text keys were `63575947`, `63581601`; resuming with `unique_key > "63575947"` returned only `63581601`. This verifies bounded ordering and tie-predicate behavior, not durable DB checkpointing or crash recovery. The independent identical-query replay attempt hit a DNS timeout. Both sampled tie keys have equal width; no variable-width lexical/numeric equivalence is claimed. Retain text comparisons throughout.
- **Update extraction:** explicit `:updated_at` returns `fixed_timestamp` values ending in `Z`. A creation-bounded update range ordered by `:updated_at,unique_key` returned two rows at `2025-12-26T18:32:48.496Z`, keys `63572417`, `63572426`; resuming after the first returned the second exactly. Syntax/filter/order/tie support is verified for this sample. Reliability as a complete change feed is NOT established: one update response was flagged out of date, full replacements can stamp all rows, and deletions are not exposed by this cursor.
- **Freshness:** first-page and update-window responses had `X-SODA2-Data-Out-Of-Date: true`, dated to the prior refresh; other responses were `false`. The unfiltered basic read returned request `71208448`, but the later ordinary identity filter returned `[]`. This is an unresolved cross-query discrepancy, not evidence of a state transition or confirmed deletion. Do not accept these mixed responses as a consistent snapshot.
- **Time:** observed event strings use millisecond precision without offset, e.g. `2026-11-22T02:06:22.000`; update metadata uses UTC `Z`. Publisher-specific timezone/DST semantics remain unconfirmed. `America/New_York` is still a proposed interpretation, not verified fact. HTTP Date/Last-Modified are not per-request event times or change cursors.
- **SCD2:** status, agency and complaint type remain defensible candidate tracked fields; no genuine same-request tracked change has been observed. Different requests/statuses, metadata changes or absence do not prove SCD2 history. Preserve a small redacted baseline and re-observe across daily refreshes. Boundaries describe observation time, never reconstructed pre-observation history.

Recommendation: **do not accept ADR-001 yet**. Remaining gates are consistent fresh responses and repeatability across refreshes, real tracked changes, confirmed timezone/DST and reviewed shared contracts. If availability persists, pause live probing and use approved fixture-only infrastructure work; propose bounded cohort reconciliation or an official dated export for backfill with explicit limitations. Neither fallback proves live incremental correctness. Full fallback/readiness details are in `context/implementation-readiness.md`.

Local assertions against temporary captured bodies passed: reference equals first + resumed creation page; tie resume equals the second tie row; update resume equals the second update row. These are source-audit comparisons, not application unit/integration tests. No personal/location payloads or large source extracts were committed.

## Initial discovery probes

Verification date: 2026-11-23 (session date). Read-only discovery probes without credentials or app token. No raw service-request payloads were stored in the repo; later evidence below retains only minimal non-location projections. No pipeline execution is claimed.

Metadata request succeeded (curl exit 0):

```sh
curl -fsS --max-time 40 'https://data.cityofnewyork.us/api/views/erm2-nwe9.json' -o /tmp/nyc311-metadata.json
```

Relevant metadata types: `unique_key`, `agency`, `agency_name`, `complaint_type`, `descriptor`, `status`, `borough`, `incident_zip` are text; `created_date`, `closed_date`, `due_date`, `resolution_action_updated_date` are calendar dates. Metadata describes daily updates. These are declarations, not observed row-value validation.

Count request succeeded (curl exit 0):

```sh
curl -fsS --max-time 60 --get 'https://data.cityofnewyork.us/resource/erm2-nwe9.json' \
  --data-urlencode '$select=count(*) as records,min(created_date) as earliest,max(created_date) as latest' \
  --data-urlencode '$where=created_date >= "2025-01-01T00:00:00" AND created_date < "2026-01-01T00:00:00"'
```

Exact aggregate response:

```json
[{"records":"3655759","earliest":"2025-01-01T00:00:12.000","latest":"2025-12-31T23:59:28.000"}]
```

This establishes sufficient raw volume for the queried local-calendar span, not a UTC window, uniqueness or a million validated/loaded facts.

Three row probes returned HTTP 503 (curl exit 22), each attempted once:

1. `$select=unique_key,created_date,closed_date,agency,complaint_type,status,borough,:updated_at`, `$where=created_date >= "2025-01-01T00:00:00" AND created_date < "2025-01-02T00:00:00"`, `$order=created_date ASC,unique_key ASC`, `$limit=3`.
2. `$select=unique_key,created_date,status,:updated_at`, `$limit=2`, no filter/order.
3. Same filter/order/limit as probe 1; select the same fields except `:updated_at`.

Each used `curl -fsS --get` with parameters passed via `--data-urlencode`, against the resource URL above; maximum time 60 seconds for probes 1/2 and 30 seconds for probe 3. No row sample was received. HTTP 503 does not prove system-field support or lack of support. Headers were not captured, so Retry-After is unverified. Stop further probes for this discovery session; future audit requests need bounded backoff.

[Official NYC changes](https://www.nyc.gov/opendata/news/all-news/311-Service-Requests-Updates) confirm the 2020-present split and preservation of backend field names despite display-label changes. [System fields](https://dev.socrata.com/docs/system-fields) documents explicit `:updated_at` selection and full-replacement caveats. [Floating timestamps](https://dev.socrata.com/docs/datatypes/floating_timestamp) have no embedded timezone. [Token guidance](https://dev.socrata.com/docs/app-tokens) permits simple unauthenticated queries and describes HTTP 429; no endpoint-specific numeric quota was verified.

Outstanding: successful redacted row sample, publisher timezone/DST confirmation, equal-timestamp pagination/text ordering, missing/duplicate keys, update-cursor support and late-update coverage, real tracked state differences across observations, rate-limit/Retry-After policy, and exact approved backfill bounds. Do not deliberately generate 429s. ADR-001 remains PROPOSED; downstream specs remain gated.

Useful source metadata: https://dev.socrata.com/foundry/data.cityofnewyork.us/erm2-nwe9


## Follow-up technical audit — 2026-11-23
Only small read-only GETs were used, without a token. All resource requests target `https://data.cityofnewyork.us/resource/erm2-nwe9.json`; no dataset download or pipeline implementation occurred. Exact decoded parameter values are recorded below. Curl supplies URL encoding via one `--data-urlencode` per parameter. Diagnostics captured headers with `-D /tmp/nyc311-TAG.headers` and bodies with `-o /tmp/nyc311-TAG.body`; raw bodies remain outside git. HTTP error bodies were unavailable where `-f` suppressed them. The initial basic/count/invalid diagnostic used `-sS --max-time 25`; later requests used `-fsS --connect-timeout 8 --max-time 25` (final four: 20 seconds). The system request completed under the normal sandbox path; network failures were retried with authorized escalation, never an alternate host or DNS bypass.
Initial sandbox DNS failures (curl 6, HTTP 000) occurred for basic/count/invalid and first/resume/ties/identity. These are local transport failures, not HTTP 503 or proof of query rejection. Authorized attempts for count/tiepage/repeat/updateknown timed out resolving DNS (curl 28, HTTP 000); no HTTP response was received. Total final diagnostic definitions below: 17, with limits at most six rows except count/group aggregates; aggregate scans are server-side and may still have cost. No automatic retry loop or intentional 429 load was used.

### basic
Request parameters:

```json
{
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:26:37 GMT
X-SODA2-Fields: ["unique_key","created_date","closed_date","agency","agency_name","complaint_type","descriptor","descriptor_2","location_type","incident_zip","incident_address","street_name","cross_street_1","cross_street_2","intersection_street_1","intersection_street_2","address_type","city","landmark","facility_type","status","due_date","resolution_description","resolution_action_updated_date","community_board","council_district","police_precinct","bbl","borough","x_coordinate_state_plane","y_coordinate_state_plane","open_data_channel_type","park_facility_name","park_borough","vehicle_type","taxi_company_borough","taxi_pick_up_location","bridge_highway_name","bridge_highway_direction","road_ramp","bridge_highway_segment","latitude","longitude","location",":@computed_region_f5dn_yrer",":@computed_region_yeji_bk3q",":@computed_region_sbqj_enih",":@computed_region_92fq_4b7q"]
X-SODA2-Types: ["text","floating_timestamp","floating_timestamp","text","text","text","text","text","text","text","text","text","text","text","text","text","text","text","text","text","text","floating_timestamp","text","floating_timestamp","text","text","text","text","text","number","number","text","text","text","text","text","text","text","text","text","text","number","number","point","number","number","number","number"]
X-SODA2-Data-Out-Of-Date: false
X-SODA2-Truth-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-SODA2-Secondary-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-Socrata-RequestId: 293464a68883df33105d64a82e9e7149
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "71208448",
    "created_date": "2026-11-22T02:06:22.000",
    "agency": "DOHMH",
    "complaint_type": "Food Establishment",
    "status": "In Progress"
  }
]
```

### count
Request parameters:

```json
{
  "$select": "count(*)"
}
```
Response: `No HTTP response (DNS timeout)`.

No response body retained/received.

### invalid
Request parameters:

```json
{
  "$select": "definitely_not_a_real_field",
  "$limit": "1"
}
```
Response: `HTTP/1.1 400 Bad Request`.

```text
Date: Mon, 23 Nov 2026 11:27:32 GMT
X-Socrata-RequestId: 924fe27442cf907dc88906ad4a37fbf0
```

Error response:

```json
{
  "message": "Query coordinator error: query.soql.no-such-column; No such column: definitely_not_a_real_field; position: Map(row -> 1, column -> 8, line -> \"SELECT `definitely_not_a_real_field` LIMIT 1\\n       ^\")",
  "errorCode": "query.soql.no-such-column",
  "data": {
    "column": "definitely_not_a_real_field",
    "dataset": "foxtrot.15655",
    "position": {
      "row": 1,
      "column": 8,
      "line": "SELECT `definitely_not_a_real_field` LIMIT 1\n       ^"
    }
  }
}
```

### page
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\"",
  "$order": "created_date ASC,unique_key ASC",
  "$limit": "6"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:27:54 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text"]
X-SODA2-Data-Out-Of-Date: false
X-SODA2-Truth-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-SODA2-Secondary-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-Socrata-RequestId: 846ba04aae9b712cf70a2233a4b5bd27
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63577994",
    "created_date": "2025-01-01T00:00:12.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  },
  {
    "unique_key": "63584096",
    "created_date": "2025-01-01T00:00:13.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  },
  {
    "unique_key": "63581480",
    "created_date": "2025-01-01T00:00:17.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  },
  {
    "unique_key": "63575612",
    "created_date": "2025-01-01T00:00:19.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Illegal Fireworks"
  },
  {
    "unique_key": "63586536",
    "created_date": "2025-01-01T00:00:34.000",
    "status": "Closed",
    "agency": "HPD",
    "complaint_type": "HEAT/HOT WATER"
  },
  {
    "unique_key": "63593943",
    "created_date": "2025-01-01T00:00:37.000",
    "status": "Closed",
    "agency": "HPD",
    "complaint_type": "HEAT/HOT WATER"
  }
]
```

### update
Request parameters:

```json
{
  "$select": "unique_key,created_date,closed_date,status,agency,complaint_type,resolution_action_updated_date,:created_at,:updated_at",
  "$where": "unique_key=\"71208448\"",
  "$limit": "1"
}
```
Response: `HTTP/1.1 503 Service Unavailable`.

```text
Date: Mon, 23 Nov 2026 11:27:54 GMT
X-Socrata-RequestId: fa35c969ba28f9b56ee04c2c99cd8401
```

No response body retained/received.

### first
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\"",
  "$order": "created_date ASC,unique_key ASC",
  "$limit": "3"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:28:46 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: 9c760139c6d5dbfbdd8205e363d36442
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63577994",
    "created_date": "2025-01-01T00:00:12.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  },
  {
    "unique_key": "63584096",
    "created_date": "2025-01-01T00:00:13.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  },
  {
    "unique_key": "63581480",
    "created_date": "2025-01-01T00:00:17.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential"
  }
]
```

### resume
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\" AND (created_date > \"2025-01-01T00:00:17.000\" OR (created_date = \"2025-01-01T00:00:17.000\" AND unique_key > \"63581480\"))",
  "$order": "created_date ASC,unique_key ASC",
  "$limit": "3"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:28:48 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: 0668a1a185cd8cab45c0ac5416d4ef18
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63575612",
    "created_date": "2025-01-01T00:00:19.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Illegal Fireworks"
  },
  {
    "unique_key": "63586536",
    "created_date": "2025-01-01T00:00:34.000",
    "status": "Closed",
    "agency": "HPD",
    "complaint_type": "HEAT/HOT WATER"
  },
  {
    "unique_key": "63593943",
    "created_date": "2025-01-01T00:00:37.000",
    "status": "Closed",
    "agency": "HPD",
    "complaint_type": "HEAT/HOT WATER"
  }
]
```

### ties
Request parameters:

```json
{
  "$select": "created_date,count(*) as n",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\"",
  "$group": "created_date",
  "$having": "count(*) > 1",
  "$order": "created_date ASC",
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:28:48 GMT
X-SODA2-Fields: ["created_date","n"]
X-SODA2-Types: ["floating_timestamp","number"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: 80dfaf08a1a52b565fb7afb4ab1fa81c
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "created_date": "2025-01-01T00:00:50.000",
    "n": "2"
  }
]
```

### system
Request parameters:

```json
{
  "$select": "unique_key,:updated_at",
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:28:18 GMT
X-SODA2-Fields: ["unique_key",":updated_at"]
X-SODA2-Types: ["text","fixed_timestamp"]
X-SODA2-Data-Out-Of-Date: false
X-SODA2-Truth-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-SODA2-Secondary-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-Socrata-RequestId: 8ac00fa745876354a909869890142aa0
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "52014695",
    ":updated_at": "2025-12-26T17:37:06.316Z"
  }
]
```

### identity
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type,resolution_action_updated_date",
  "$where": "unique_key=\"71208448\"",
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:28:49 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type","resolution_action_updated_date"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text","floating_timestamp"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: 4003ce62be2cdbc68aeecd2631dd376d
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[]
```

### tiepage
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type",
  "$where": "created_date = '2025-01-01T00:00:50.000'",
  "$order": "created_date ASC,unique_key ASC",
  "$limit": "3"
}
```
Response: `No HTTP response (DNS timeout)`.

No response body retained/received.

### repeat
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type",
  "$where": "created_date >= '2025-01-01T00:00:00' AND created_date < '2025-01-01T00:05:00' AND (created_date > '2025-01-01T00:00:17.000' OR (created_date = '2025-01-01T00:00:17.000' AND unique_key > '63581480'))",
  "$order": "created_date ASC,unique_key ASC",
  "$limit": "3"
}
```
Response: `No HTTP response (DNS timeout)`.

No response body retained/received.

### updateknown
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type,resolution_action_updated_date,:updated_at",
  "$where": "unique_key = '63577994'",
  "$limit": "1"
}
```
Response: `No HTTP response (DNS timeout)`.

No response body retained/received.

### tiecheck
Request parameters:

```json
{
  "$select": "unique_key,created_date",
  "$where": "created_date=\"2025-01-01T00:00:50.000\"",
  "$order": "unique_key ASC",
  "$limit": "3"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:30:27 GMT
X-SODA2-Fields: ["unique_key","created_date"]
X-SODA2-Types: ["text","floating_timestamp"]
X-SODA2-Data-Out-Of-Date: false
X-SODA2-Truth-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-SODA2-Secondary-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-Socrata-RequestId: e29b4cb2cf1d9ab613e121a436e8dc1d
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63575947",
    "created_date": "2025-01-01T00:00:50.000"
  },
  {
    "unique_key": "63581601",
    "created_date": "2025-01-01T00:00:50.000"
  }
]
```

### updatewindow
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type,:updated_at",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\" AND :updated_at >= \"2025-01-01T00:00:00Z\" AND :updated_at < \"2026-11-24T00:00:00Z\"",
  "$order": ":updated_at ASC,unique_key ASC",
  "$limit": "2"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:30:31 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type",":updated_at"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text","fixed_timestamp"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: b0cb74fb7542c744d3fd21a1d207b46a
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63572417",
    "created_date": "2025-01-01T00:02:31.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential",
    ":updated_at": "2025-12-26T18:32:48.496Z"
  },
  {
    "unique_key": "63572426",
    "created_date": "2025-01-01T00:00:42.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential",
    ":updated_at": "2025-12-26T18:32:48.496Z"
  }
]
```

### tieresume
Request parameters:

```json
{
  "$select": "unique_key,created_date",
  "$where": "created_date=\"2025-01-01T00:00:50.000\" AND unique_key > \"63575947\"",
  "$order": "unique_key ASC",
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:41:22 GMT
X-SODA2-Fields: ["unique_key","created_date"]
X-SODA2-Types: ["text","floating_timestamp"]
X-SODA2-Data-Out-Of-Date: true
X-SODA2-Truth-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-SODA2-Secondary-Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
Last-Modified: Sun, 22 Nov 2026 02:37:44 GMT
X-Socrata-RequestId: c4b0a5711d3108f4db2b53c446691972
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63581601",
    "created_date": "2025-01-01T00:00:50.000"
  }
]
```

### updateresume
Request parameters:

```json
{
  "$select": "unique_key,created_date,status,agency,complaint_type,:updated_at",
  "$where": "created_date >= \"2025-01-01T00:00:00\" AND created_date < \"2025-01-01T00:05:00\" AND :updated_at >= \"2025-01-01T00:00:00Z\" AND :updated_at < \"2026-11-24T00:00:00Z\" AND (:updated_at > \"2025-12-26T18:32:48.496Z\" OR (:updated_at = \"2025-12-26T18:32:48.496Z\" AND unique_key > \"63572417\"))",
  "$order": ":updated_at ASC,unique_key ASC",
  "$limit": "1"
}
```
Response: `HTTP/1.1 200 OK`.

```text
Date: Mon, 23 Nov 2026 11:41:19 GMT
X-SODA2-Fields: ["unique_key","created_date","status","agency","complaint_type",":updated_at"]
X-SODA2-Types: ["text","floating_timestamp","text","text","text","fixed_timestamp"]
X-SODA2-Data-Out-Of-Date: false
X-SODA2-Truth-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-SODA2-Secondary-Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
Last-Modified: Mon, 23 Nov 2026 02:37:55 GMT
X-Socrata-RequestId: ca1ef6264691772cd34a29aeddf6102d
```

Minimal response projection (location, descriptions and other unused fields omitted):

```json
[
  {
    "unique_key": "63572426",
    "created_date": "2025-01-01T00:00:42.000",
    "status": "Closed",
    "agency": "NYPD",
    "complaint_type": "Noise - Residential",
    ":updated_at": "2025-12-26T18:32:48.496Z"
  }
]
```

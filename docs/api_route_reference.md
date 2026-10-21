# API route reference

Every route in the Tech Rep Scheduler API, with its purpose, inputs, and outputs. The interactive version is at `http://localhost:8000/docs` when the backend is running.

## Conventions

- **Base URL:** `http://localhost:8000`
- **Format:** JSON request and response bodies (`Content-Type: application/json`).
- **Timestamps in request bodies** (`start_time`, `end_time`) must be ISO 8601 with a UTC offset, for example `2026-11-07T08:00:00-07:00`. A timestamp without an offset is rejected with 422.
- **Time windows:** `end_time` must be after `start_time`. List filters `start` and `end` return records that overlap `[start, end)`.
- **Dates** are `YYYY-MM-DD`. **Times** are `HH:MM:SS`.
- **Status filters** use the query parameter `status`, for example `?status=open`.

### Errors

All errors return a JSON body with a `detail` field.

| Status | When | Body |
| --- | --- | --- |
| 404 | The ID in the path does not exist | `{"detail": "Demand not found"}` |
| 409 | Duplicate value, overlap, unknown foreign key, or invalid status change | `{"detail": "Overlaps an existing pay period"}` |
| 422 | The request fails validation | `{"detail": [{"loc": ["body", "end_time"], "msg": "...", "type": "..."}]}` |

## Route summary

| Method | Path | Function |
| --- | --- | --- |
| GET | [`/health`](#get-health) | Liveness check |
| GET | [`/reps`](#get-reps) | List Tech Reps |
| POST | [`/reps`](#post-reps) | Create a Tech Rep |
| GET | [`/reps/{rep_id}`](#get-repsrep_id) | Get one Tech Rep |
| PATCH | [`/reps/{rep_id}`](#patch-repsrep_id) | Update a Tech Rep |
| GET | [`/reps/{rep_id}/certifications`](#get-repsrep_idcertifications) | List a rep's certifications |
| PUT | [`/reps/{rep_id}/certifications/{aircraft_type_id}`](#put-repsrep_idcertificationsaircraft_type_id) | Add or update a certification |
| DELETE | [`/reps/{rep_id}/certifications/{aircraft_type_id}`](#delete-repsrep_idcertificationsaircraft_type_id) | Remove a certification |
| GET | [`/aircraft-types`](#get-aircraft-types) | List aircraft types |
| POST | [`/aircraft-types`](#post-aircraft-types) | Create an aircraft type |
| GET | [`/aircraft-types/{type_id}`](#get-aircraft-typestype_id) | Get one aircraft type |
| GET | [`/mro-locations`](#get-mro-locations) | List MRO locations |
| POST | [`/mro-locations`](#post-mro-locations) | Create an MRO location |
| GET | [`/mro-locations/{mro_id}`](#get-mro-locationsmro_id) | Get one MRO location |
| GET | [`/mro-locations/{mro_id}/travel-times`](#get-mro-locationsmro_idtravel-times) | List travel times to an MRO |
| PUT | [`/mro-locations/{mro_id}/travel-times/{home_base}`](#put-mro-locationsmro_idtravel-timeshome_base) | Set travel time from a home base |
| DELETE | [`/mro-locations/{mro_id}/travel-times/{home_base}`](#delete-mro-locationsmro_idtravel-timeshome_base) | Remove a travel time |
| GET | [`/cba/rules`](#get-cbarules) | List CBA rule sets |
| GET | [`/cba/rules/active`](#get-cbarulesactive) | Get the rule set in effect on a date |
| GET | [`/cba/shift-patterns`](#get-cbashift-patterns) | List shift patterns and start windows |
| GET | [`/cba/holidays`](#get-cbaholidays) | List statutory holidays |
| POST | [`/cba/holidays`](#post-cbaholidays) | Add a statutory holiday |
| GET | [`/cba/pay-periods`](#get-cbapay-periods) | List pay periods |
| POST | [`/cba/pay-periods`](#post-cbapay-periods) | Add a pay period |
| DELETE | [`/cba/pay-periods/{period_id}`](#delete-cbapay-periodsperiod_id) | Remove a pay period |
| GET | [`/unavailability`](#get-unavailability) | List rep time off |
| POST | [`/unavailability`](#post-unavailability) | Record rep time off |
| GET | [`/unavailability/{entry_id}`](#get-unavailabilityentry_id) | Get one time-off entry |
| PATCH | [`/unavailability/{entry_id}`](#patch-unavailabilityentry_id) | Change a time-off status |
| GET | [`/demands`](#get-demands) | List MRO demands |
| POST | [`/demands`](#post-demands) | Create an MRO demand |
| GET | [`/demands/{demand_id}`](#get-demandsdemand_id) | Get one demand |
| PATCH | [`/demands/{demand_id}`](#patch-demandsdemand_id) | Change a demand status |
| GET | [`/demands/{demand_id}/responses`](#get-demandsdemand_idresponses) | List solicitation responses |
| PUT | [`/demands/{demand_id}/responses/{rep_id}`](#put-demandsdemand_idresponsesrep_id) | Record a rep's accept or decline |
| DELETE | [`/demands/{demand_id}/responses/{rep_id}`](#delete-demandsdemand_idresponsesrep_id) | Remove a response |
| GET | [`/assignments`](#get-assignments) | List assignments |
| POST | [`/assignments`](#post-assignments) | Create a manual assignment |
| GET | [`/assignments/{assignment_id}`](#get-assignmentsassignment_id) | Get one assignment |
| PATCH | [`/assignments/{assignment_id}`](#patch-assignmentsassignment_id) | Change an assignment's status, rep, or times |
| POST | [`/schedule/run`](#post-schedulerun) | Run the CBA-aware solver on stored data |
| POST | [`/schedule/solve`](#post-schedulesolve) | Run the placeholder solver on inline data |
| GET | [`/cba/sick-leave-allowance`](#sick-leave-allowance) | Sick days allowed from each month to year end |
| PUT | [`/cba/sick-leave-allowance/{month}`](#sick-leave-allowance) | Set one month's allowance |
| GET, POST | [`/training/types`](#training) | List or add training types |
| GET, PATCH, DELETE | [`/training/types/{type_id}`](#training) | One training type |
| GET, POST | [`/training/records`](#training) | List, record completed training, or submit dates |
| GET, PATCH, DELETE | [`/training/records/{record_id}`](#training) | One training record |
| POST | [`/training/records/{record_id}/approve`](#training) | Approve submitted dates |
| POST | [`/training/records/{record_id}/reject`](#training) | Reject submitted dates |
| GET | [`/training/due`](#training) | Reps due for training within N days |
| GET | [`/leave-balances`](#leave-balances) | List vacation, stat, and sick balances |
| PUT, DELETE | [`/leave-balances/{rep_id}/{year}/{leave_type}`](#leave-balances) | Set or remove a balance |
| GET, POST | [`/vacation/bids`](#vacation) | List or add vacation bids |
| GET, PATCH, DELETE | [`/vacation/bids/{bid_id}`](#vacation) | One bid |
| POST | [`/vacation/bids/import`](#vacation) | Import bids from CSV |
| POST | [`/vacation/award`](#vacation) | Award a year's bids by seniority |
| GET | [`/vacation/capacity`](#vacation) | Reps off and places left per week |
| GET, POST | [`/maintenance-events`](#maintenance-events) | List or add HMS and unplanned events |
| POST | [`/maintenance-events/import`](#maintenance-events) | Import events from CSV |
| GET, PATCH, DELETE | [`/maintenance-events/{event_id}`](#maintenance-events) | One event |
| GET | [`/maintenance-events/{event_id}/staffing-options`](#maintenance-events) | Available reps and reassignments |
| GET | [`/overtime/opportunities`](#overtime) | Unfilled demand with eligible reps by seniority |
| GET, POST | [`/alerts`](#alerts) | Alert feed, filterable by location |
| POST | [`/alerts/scan`](#alerts) | Raise coverage, shortage, and training alerts |
| GET, PATCH, DELETE | [`/alerts/{alert_id}`](#alerts) | One alert; PATCH acknowledges |
| GET | [`/dashboards/workforce`](#dashboards) | Available, assigned, and on-leave reps |
| GET | [`/dashboards/coverage`](#dashboards) | Seats needed and filled per MRO per week |

---

## Health

### GET /health

Liveness check. Does not touch the database.

**Response 200**

```json
{"status": "ok"}
```

---

## Tech Reps

### GET /reps

List all Tech Reps, ordered by ID.

**Response 200:** array of [TechRep](#techrep).

### POST /reps

Create a Tech Rep and, optionally, certifications without dates.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | string | Yes | 1 to 200 characters |
| `home_base` | string | Yes | 1 to 200 characters. Compared with `mro_locations.location` and `airport_code` to detect field service, and with `travel_times.home_base` |
| `email` | string | No | Unique, up to 254 characters |
| `classification` | string | No | Up to 60 characters, for example `AME` |
| `cba_group` | integer | No | 1 to 5 (Article 18). Group 1 at a major base uses the 26-week averaging period |
| `union_seniority_date` | date | No | Seniority tie-break after `seniority_rank` |
| `seniority_rank` | integer | No | 1 is most senior. Separate from `id`: a rehired rep keeps their ID but gets a new rank. Orders overtime offers, mandatory overtime (reverse), and vacation awards |
| `phone` | string | No | Contact number, 7 to 30 digits, spaces, `+`, `-`, `.`, or brackets |
| `shift_pattern_code` | string | No | One of the codes from `/cba/shift-patterns` |
| `shift_cycle_start` | date | No | Day 1 of the pattern's cycle. Needed to tell work days from days off |
| `banked_ot_hours` | number | No | 0 to 80, default 0 |
| `certified_aircraft_type_ids` | integer[] | No | Up to 100 IDs |

```json
{
  "name": "Ana Lopez",
  "home_base": "YYC",
  "email": "ana.lopez@example.com",
  "cba_group": 1,
  "union_seniority_date": "2015-03-01",
  "shift_pattern_code": "5-5-4",
  "shift_cycle_start": "2026-11-02",
  "certified_aircraft_type_ids": [1, 2]
}
```

**Response 201:** [TechRep](#techrep).

**Errors:** 409 if the email is taken or an aircraft type or shift pattern does not exist.

### GET /reps/{rep_id}

Get one Tech Rep.

**Path:** `rep_id` (integer)

**Response 200:** [TechRep](#techrep). **Errors:** 404.

### PATCH /reps/{rep_id}

Update a Tech Rep. Only fields in the body change. Send `null` to clear an optional field; `name`, `home_base`, `active`, and `banked_ot_hours` cannot be null.

**Path:** `rep_id` (integer)

**Body:** any subset of the [POST /reps](#post-reps) fields except `certified_aircraft_type_ids`, plus `active` (boolean).

```json
{"shift_pattern_code": "5-2", "shift_cycle_start": "2026-11-02", "active": true}
```

**Response 200:** [TechRep](#techrep). **Errors:** 404; 409 if the email is taken or the shift pattern does not exist; 422 if a required field is null.

### GET /reps/{rep_id}/certifications

List a rep's certifications with dates.

**Path:** `rep_id` (integer)

**Response 200:** array of [Certification](#certification). **Errors:** 404.

### PUT /reps/{rep_id}/certifications/{aircraft_type_id}

Add a certification, or update its dates if it exists. The solver treats a certification as valid when `certified_on` is on or before the demand start and `expires_on` is on or after the demand end.

**Path:** `rep_id` (integer), `aircraft_type_id` (integer)

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `certified_on` | date | No | |
| `expires_on` | date | No | Must be on or after `certified_on` |

```json
{"certified_on": "2024-01-15", "expires_on": "2027-01-15"}
```

**Response 200:** [Certification](#certification). **Errors:** 404 for an unknown rep or aircraft type; 422 for bad dates.

### DELETE /reps/{rep_id}/certifications/{aircraft_type_id}

Remove a certification.

**Response 204:** no body. **Errors:** 404.

---

## Aircraft types

### GET /aircraft-types

List aircraft types, ordered by model name.

**Response 200:** array of [AircraftType](#aircrafttype).

### POST /aircraft-types

Create an aircraft type.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `model_name` | string | Yes | Unique, 1 to 100 characters |
| `manufacturer` | string | No | Up to 100 characters |

```json
{"model_name": "737 MAX 8", "manufacturer": "Boeing"}
```

**Response 201:** [AircraftType](#aircrafttype). **Errors:** 409 if the model name exists.

### GET /aircraft-types/{type_id}

Get one aircraft type.

**Response 200:** [AircraftType](#aircrafttype). **Errors:** 404.

---

## MRO locations and travel times

### GET /mro-locations

List MRO locations, ordered by facility name.

**Response 200:** array of [MroLocation](#mrolocation).

### POST /mro-locations

Create an MRO location.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `facility_name` | string | Yes | 1 to 200 characters |
| `location` | string | Yes | 1 to 200 characters, for example `Calgary` |
| `airport_code` | string | No | Exactly 3 uppercase letters |
| `timezone` | string | No | IANA name, default `UTC`. Used to split hours by local day |
| `covering_base` | string | No | Home base whose team covers this MRO, for example `YYC`. The solver and overtime list prefer that team |

```json
{"facility_name": "YYC Hangar 1", "location": "Calgary", "airport_code": "YYC", "timezone": "America/Edmonton"}
```

**Response 201:** [MroLocation](#mrolocation). **Errors:** 422 for an unknown timezone or bad airport code.

### GET /mro-locations/{mro_id}

Get one MRO location.

**Response 200:** [MroLocation](#mrolocation). **Errors:** 404.

### GET /mro-locations/{mro_id}/travel-times

List one-way travel times from home bases to this MRO.

**Response 200:** array of [TravelTime](#traveltime). **Errors:** 404.

### PUT /mro-locations/{mro_id}/travel-times/{home_base}

Set the one-way travel time from a home base to this MRO, creating or replacing it. Travel counts toward the 16 h duty day (CBA 21-1.03) and is paid at the field service rate (21-2.02).

**Path:** `mro_id` (integer), `home_base` (string, URL-encoded; must match the rep's `home_base` text)

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `travel_hours` | number | Yes | 0 to 24 |
| `distance_km` | integer | No | 0 or more |

```json
{"travel_hours": 2.5, "distance_km": 690}
```

**Response 200:** [TravelTime](#traveltime). **Errors:** 404 for an unknown MRO.

### DELETE /mro-locations/{mro_id}/travel-times/{home_base}

Remove a travel time. The solver then assumes 0 h and returns a warning.

**Response 204:** no body. **Errors:** 404.

---

## CBA rules and calendars

### GET /cba/rules

List all CBA rule sets, ordered by `effective_from`.

**Response 200:** array of [CbaRules](#cbarules).

### GET /cba/rules/active

Get the rule set in effect on a date.

**Query**

| Parameter | Type | Required | Notes |
| --- | --- | --- | --- |
| `on` | date | No | Default today |

**Response 200:** [CbaRules](#cbarules). **Errors:** 404 if no rule set covers the date.

### GET /cba/shift-patterns

List shift patterns (CBA 19-1.08 to 19-1.11) with their allowed start-time windows (19-5).

**Response 200:** array of [ShiftPattern](#shiftpattern).

### GET /cba/holidays

List statutory holidays.

**Query:** `start` (date, optional), `end` (date, optional). Both bounds are inclusive.

**Response 200:** array of [Holiday](#holiday).

### POST /cba/holidays

Add a statutory holiday. The CBA does not list the 11 dates, so load them here.

**Body:** [Holiday](#holiday).

```json
{"holiday_date": "2026-12-25", "name": "Christmas Day"}
```

**Response 201:** [Holiday](#holiday). **Errors:** 409 if a holiday exists on that date.

### GET /cba/pay-periods

List pay periods that overlap `[start, end)`. Dates with no row use semi-monthly periods (1st to 15th, 16th to month end).

**Query:** `start` (date, optional), `end` (date, optional)

**Response 200:** array of [PayPeriod](#payperiod).

### POST /cba/pay-periods

Add a pay period. Used for the 8 h voluntary overtime tier (CBA 16-1.04).

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `start_date` | date | Yes | |
| `end_date` | date | Yes | Exclusive. Must be after `start_date` |

```json
{"start_date": "2026-11-01", "end_date": "2026-11-16"}
```

**Response 201:** [PayPeriod](#payperiod). **Errors:** 409 if it overlaps an existing period.

### DELETE /cba/pay-periods/{period_id}

Remove a pay period.

**Response 204:** no body. **Errors:** 404.

---

## Rep unavailability

### GET /unavailability

List time-off entries.

**Query**

| Parameter | Type | Notes |
| --- | --- | --- |
| `rep_id` | integer | |
| `status` | string | `requested`, `approved`, `denied`, or `cancelled` |
| `start`, `end` | date-time | Overlapping window |

**Response 200:** array of [Unavailability](#unavailability), ordered by `start_time`.

### POST /unavailability

Record a period when a rep cannot be scheduled. Only `approved` entries block the solver; `requested` vacation can be granted by [`/schedule/run`](#post-schedulerun) within the weekly cap. Creating an entry or changing its status recounts `used_days` on the rep's vacation and sick [balances](#leave-balances) and runs the compliance check, which alerts on vacation and sick limits.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `rep_id` | integer | Yes | |
| `reason` | string | Yes | `vacation`, `sick`, `training`, `bereavement`, `parental`, `union_leave`, `unpaid_leave`, `jury_duty`, or `other` |
| `start_time` | date-time | Yes | With offset |
| `end_time` | date-time | Yes | With offset, after `start_time` |
| `status` | string | No | Default `approved` |
| `notes` | string | No | Up to 500 characters |

```json
{
  "rep_id": 1,
  "reason": "vacation",
  "start_time": "2026-12-20T00:00:00-07:00",
  "end_time": "2027-01-03T00:00:00-07:00"
}
```

**Response 201:** [Unavailability](#unavailability). **Errors:** 409 for an unknown rep.

### GET /unavailability/{entry_id}

Get one time-off entry.

**Response 200:** [Unavailability](#unavailability). **Errors:** 404.

### PATCH /unavailability/{entry_id}

Change a time-off status.

**Body**

```json
{"status": "cancelled"}
```

**Response 200:** [Unavailability](#unavailability). **Errors:** 404.

---

## MRO demands and responses

### GET /demands

List demands, ordered by priority then start time.

**Query**

| Parameter | Type | Notes |
| --- | --- | --- |
| `mro_id` | integer | |
| `demand_type` | string | `base_coverage` or `aog` |
| `status` | string | `open`, `filled`, or `cancelled` |
| `start`, `end` | date-time | Overlapping window |

**Response 200:** array of [Demand](#demand).

### POST /demands

Create a demand. Each demand is one duty period; the solver rejects demands longer than the 16 h duty day, so enter multi-day coverage as one demand per shift.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `mro_id` | integer | Yes | |
| `aircraft_type_id` | integer | Yes | |
| `start_time` | date-time | Yes | With offset |
| `end_time` | date-time | Yes | With offset, after `start_time` |
| `demand_type` | string | No | `base_coverage` (default, planned, 21-2), `aog` (unplanned, 21-3), or a maintenance event type: `heavy_check`, `induction`, `rts`, `lease_return`, `hard_landing`, `hail_damage`, `mro_support` |
| `maintenance_event_id` | integer | No | The maintenance event this demand staffs |
| `reps_needed` | integer | No | 1 to 50, default 1 |
| `priority` | integer | No | 1 (most urgent) to 5, default 3 |
| `notes` | string | No | Up to 500 characters |

```json
{
  "mro_id": 1,
  "aircraft_type_id": 1,
  "demand_type": "base_coverage",
  "start_time": "2026-11-07T08:00:00-07:00",
  "end_time": "2026-11-07T18:00:00-07:00",
  "reps_needed": 2,
  "priority": 2
}
```

**Response 201:** [Demand](#demand). **Errors:** 409 for an unknown MRO or aircraft type.

### GET /demands/{demand_id}

Get one demand.

**Response 200:** [Demand](#demand). **Errors:** 404.

### PATCH /demands/{demand_id}

Change a demand status. The solver only schedules `open` demands.

**Body**

```json
{"status": "filled"}
```

**Response 200:** [Demand](#demand). **Errors:** 404.

### GET /demands/{demand_id}/responses

List the solicitation responses for a demand, oldest first.

**Response 200:** array of [DemandResponse](#demandresponse). **Errors:** 404.

### PUT /demands/{demand_id}/responses/{rep_id}

Record that a rep accepted or declined a demand (CBA 21-2.06, 21-3.07), creating or replacing the response. Once a demand has any response, reps who did not accept can only be assigned mandatorily, in reverse seniority, when `/schedule/run` is called with `allow_mandatory: true`.

**Body**

```json
{"response": "accepted"}
```

`response` is `accepted` or `declined`.

**Response 200:** [DemandResponse](#demandresponse). **Errors:** 404 for an unknown demand or rep.

### DELETE /demands/{demand_id}/responses/{rep_id}

Remove a response.

**Response 204:** no body. **Errors:** 404.

---

## Assignments

### GET /assignments

List assignments, ordered by start time.

**Query**

| Parameter | Type | Notes |
| --- | --- | --- |
| `rep_id` | integer | |
| `mro_id` | integer | |
| `demand_id` | integer | |
| `status` | string | `proposed`, `confirmed`, `in_progress`, `completed`, or `cancelled` |
| `start`, `end` | date-time | Overlapping window |

**Response 200:** array of [Assignment](#assignment).

### POST /assignments

Create an assignment manually, to override the solver. It is saved even when it breaks a CBA or company rule; the [compliance check](architecture.md#compliance-checks) runs on the rep around the new assignment, writes findings to alerts, and returns them as `warnings`. Only the no-overlap rule blocks the request.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `rep_id` | integer | Yes | |
| `mro_id` | integer | Yes | |
| `start_time` | date-time | Yes | With offset |
| `end_time` | date-time | Yes | With offset, after `start_time` |
| `aircraft_type_id` | integer | No | |
| `demand_id` | integer | No | Counts toward the demand's `reps_needed` |
| `status` | string | No | `proposed` (default) or `confirmed` |
| `overtime_type` | string | No | `none` (default), `voluntary`, or `mandatory` |
| `overtime_hours` | number | No | 0 to 999, default 0. Feeds the pay-period overtime tier |
| `travel_hours` | number | No | One way, 0 to 24, default 0 |

```json
{
  "rep_id": 1,
  "mro_id": 1,
  "demand_id": 3,
  "start_time": "2026-11-09T08:00:00-07:00",
  "end_time": "2026-11-09T16:00:00-07:00",
  "status": "confirmed"
}
```

**Response 201:** [Assignment](#assignment) plus `warnings`, an array of [ComplianceWarning](#compliancewarning). **Errors:** 409 if the rep has an overlapping live assignment or an ID does not exist.

### GET /assignments/{assignment_id}

Get one assignment.

**Response 200:** [Assignment](#assignment). **Errors:** 404.

### PATCH /assignments/{assignment_id}

Change an assignment's status, rep, or times. Send only the fields to change: `status`, `rep_id`, `start_time`, `end_time`. Rep and times can change while the assignment is live (not `completed` or `cancelled`). Allowed status changes:

| From | To |
| --- | --- |
| `proposed` | `confirmed`, `cancelled` |
| `confirmed` | `in_progress`, `cancelled` |
| `in_progress` | `completed`, `cancelled` |
| `completed`, `cancelled` | None (final) |

**Body**

```json
{"status": "confirmed"}
```

```json
{"rep_id": 7, "start_time": "2026-11-09T09:00:00-07:00"}
```

The compliance check runs on the new rep (and the old rep when it changed). Findings are returned, not blocking.

**Response 200:** [Assignment](#assignment) plus `warnings`. **Errors:** 404; 409 for a status change not in the table, editing a final assignment, or an overlap; 422 if `end_time` is not after `start_time`.

---

## Scheduling

### POST /schedule/run

Propose assignments for open demands in a time window, using stored reps, certifications, time off, existing assignments, travel times, pay periods, holidays, and the CBA rules in effect on `start_time`. See [architecture.md](architecture.md#solver-flow) for the constraints and objective.

**Body**

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `start_time` | date-time | Yes | With offset |
| `end_time` | date-time | Yes | With offset. Window at most 366 days, so a full year fits in one run |
| `mro_id` | integer | No | Only schedule demands at this MRO |
| `save` | boolean | No | Default `false`. When `true`, saves proposals as `proposed` assignments |
| `allow_mandatory` | boolean | No | Default `false`. When `true`, may assign reps who did not accept a solicited demand |

```json
{
  "start_time": "2026-11-01T00:00:00-06:00",
  "end_time": "2026-12-01T00:00:00-07:00",
  "save": true,
  "allow_mandatory": false
}
```

**Response 200**

| Field | Type | Notes |
| --- | --- | --- |
| `status` | string | CP-SAT status: `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `MODEL_INVALID`, or `UNKNOWN` |
| `cba_rules_id` | integer | Rule set used |
| `assignments` | [ProposedAssignment](#proposedassignment)[] | |
| `unfilled` | [UnfilledDemand](#unfilleddemand)[] | Demands not fully staffed, with the reason |
| `warnings` | string[] | Data gaps, such as a missing travel time, and weeks already over the vacation cap |
| `vacation_granted` | integer[] | `requested` vacation entries granted within the weekly cap, most senior first. With `save`, they become `approved` |
| `vacation_not_granted` | integer[] | Requested vacation that did not fit under the cap or overlaps existing work |
| `violations` | [ComplianceWarning](#compliancewarning)[] | With `save`: compliance findings for each rep given work, also written to alerts |

With `save`, the run window is also scanned for coverage gaps and shortages (see [`/alerts/scan`](#alerts)).

```json
{
  "status": "OPTIMAL",
  "cba_rules_id": 1,
  "assignments": [
    {
      "assignment_id": 12,
      "demand_id": 4,
      "rep_id": 6,
      "mro_id": 1,
      "start_time": "2026-11-04T06:00:00-07:00",
      "end_time": "2026-11-04T19:00:00-07:00",
      "field_service": true,
      "mandatory": false,
      "travel_hours": 2.5,
      "paid_hours": 22.0,
      "overtime_hours": 0.0,
      "premium_hours": 11.0
    }
  ],
  "unfilled": [
    {"demand_id": 5, "still_needed": 1, "reason": "No eligible rep: 1 over the max duty day once travel is added"}
  ],
  "warnings": ["No travel time from Edmonton to YYC Hangar 1; assumed 0 h"]
}
```

**Errors:** 422 if no CBA rules are in effect on `start_time` or the window is over 366 days; 409 if the schedule changed while saving (run again).

### POST /schedule/solve

Placeholder solver that matches requests to certified reps from data in the body. It does not read the database or apply CBA rules. Use [`/schedule/run`](#post-schedulerun) for real scheduling.

**Body**

```json
{
  "reps": [
    {"id": 1, "certified_aircraft_type_ids": [10]},
    {"id": 2, "certified_aircraft_type_ids": [10, 20]}
  ],
  "requests": [
    {"id": 100, "aircraft_type_id": 20},
    {"id": 101, "aircraft_type_id": 10}
  ]
}
```

`reps` and `requests` each accept up to 500 items.

**Response 200**

```json
{
  "status": "OPTIMAL",
  "assignments": [{"request_id": 100, "rep_id": 2}, {"request_id": 101, "rep_id": 1}],
  "unassigned_request_ids": []
}
```

## Sick leave allowance

`GET /cba/sick-leave-allowance` lists, per month, the sick days a rep may take from the 1st of that month to year end (`month`, `max_days`, `needs_review`). January (12) and October (4) come from the requirements; the other months are a straight line between them and are flagged `needs_review`. `PUT /cba/sick-leave-allowance/{month}` with `{"max_days": 9}` sets a month and clears `needs_review`.

## Training

| Route | Notes |
| --- | --- |
| `GET /training/types`, `POST /training/types` | Body: `name`, `recurrence_months` (null for one-off), `is_mandatory` (default true), `aircraft_type_id` (endorsement courses: completing one adds that certification to the rep) |
| `PATCH`, `DELETE /training/types/{type_id}` | 409 when records still use the type |
| `GET /training/records` | Filters: `rep_id`, `training_type_id`, `status` (`submitted`, `approved`, `rejected`) |
| `POST /training/records` | Body: `rep_id`, `training_type_id`, and either `completed_on` (history; stored as `approved`, `expires_on` defaults to `completed_on` plus the recurrence) or `scheduled_start` and `scheduled_end` (the training department submits dates; stored as `submitted`) |
| `PATCH /training/records/{record_id}` | New scheduled dates on approved training cancel its leave and send it back to `submitted` |
| `DELETE /training/records/{record_id}` | Also cancels its leave |
| `POST /training/records/{record_id}/approve` | Creates an approved `training` leave row, cancels `proposed` assignments in the way, and returns `cancelled_assignment_ids` and compliance `warnings` for confirmed work that clashes |
| `POST /training/records/{record_id}/reject` | Optional body `note` (up to 400 characters), appended to `notes` for the training department. Sets `rejected` and cancels any leave row |
| `GET /training/due?days=60` | Active reps whose training expires within `days`, has expired, or (mandatory only) was never completed: `rep_id`, `rep_name`, `training_type_id`, `training_type_name`, `is_mandatory`, `expires_on`, `days_left`, `next_scheduled_start`, `location` (`Calgary`, or `Toronto` for eastern-based reps) |

## Leave balances

`GET /leave-balances` (filters `rep_id`, `year`, `leave_type`) returns `rep_id`, `year`, `leave_type` (`vacation`, `stat`, `sick`), `entitled_days`, `used_days`, and `remaining_days`. `PUT /leave-balances/{rep_id}/{year}/{leave_type}` with `{"entitled_days": 20, "used_days": 0}` sets a balance; `DELETE` removes it.

`used_days` for `vacation` and `sick` is recounted from approved leave whenever leave changes. A day counts when it is a work day: a shift pattern work day, or Monday to Friday for reps without a pattern. `stat` usage is entered by hand.

## Vacation

| Route | Notes |
| --- | --- |
| `GET /vacation/bids` | Filters: `rep_id`, `year`, `status` (`submitted`, `awarded`, `denied`, `withdrawn`) |
| `POST /vacation/bids` | Body: `rep_id`, `year`, `week_start` (a Monday), `preference_rank` (1 is first choice). 409 for a repeated week or rank |
| `PATCH /vacation/bids/{bid_id}` | `preference_rank` or `status`. Moving an awarded bid to another status cancels its leave |
| `DELETE /vacation/bids/{bid_id}` | Cancels the leave of an awarded bid |
| `POST /vacation/bids/import` | `text/csv` body with `rep_id` or `email`, `week_start`, `preference_rank`, and optional `year` (defaults to the ISO year of `week_start`). All rows or none: any bad row returns 422 with one entry per line |
| `POST /vacation/award` | Body `{"year": 2027}`. Takes reps in seniority order and each rep's bids by preference. A week is awarded while it is under `max_reps_off_per_week` and the rep has enough vacation balance (a rep with no balance on file is denied). Awards become approved vacation leave for Monday to Monday in the rep's home timezone. Returns `awarded` bid IDs and `denied` with a reason each |
| `GET /vacation/capacity?year=2027` | Every week starting in the year: `week_start`, `cap`, `reps_off`, `remaining`, `rep_ids` |

```csv
email,week_start,preference_rank
ana.lopez@example.com,2027-07-05,1
ana.lopez@example.com,2027-08-02,2
```

## Maintenance events

Heavy Maintenance Schedule and unplanned events are entered by hand or by CSV. There is no external HMS integration.

| Route | Notes |
| --- | --- |
| `GET /maintenance-events` | Filters: `mro_id`, `aircraft_type_id`, `event_type`, `status`, and `start`, `end` dates (overlapping) |
| `POST /maintenance-events` | Body: `aircraft_type_id`, `mro_id`, `tail_number`, `event_type` (`heavy_check`, `induction`, `rts`, `aog`, `lease_return`, `hard_landing`, `hail_damage`, `mro_support`), `induction_date`, `rts_date`, optional `reps_required` and `notes`. Returns the event with `demand_ids` |
| `POST /maintenance-events/import` | `text/csv` body with `tail_number`, `event_type`, `induction_date`, `rts_date`, `aircraft_type` (model name) or `aircraft_type_id`, `mro` (airport code or facility name) or `mro_id`, and optional `reps_required`, `notes`. All rows or none |
| `PATCH /maintenance-events/{event_id}` | `tail_number`, `induction_date`, `rts_date`, `reps_required`, `status`, `notes` |
| `DELETE /maintenance-events/{event_id}` | Cancels the event's demands first |
| `GET /maintenance-events/{event_id}/staffing-options` | Per open shift: the [OvertimeOpportunity](#overtime) fields plus `reassignments`, reps on lower-priority proposed or confirmed work at the same time who would be free if moved |

**Generated demand.** Creating or importing an event adds one demand per support day: a day shift from 07:00 for 10 h local time, from `induction_date` to `rts_date` inclusive (`induction` and `rts` events get one day). `reps_needed` is `reps_required`, which defaults to 2 for `heavy_check` and 1 otherwise. Priority: `aog` 1; `hard_landing`, `hail_damage`, `rts` 2; `induction`, `heavy_check`, `lease_return` 3; `mro_support` 4.

**Date changes.** When the dates, staffing, or status change, the event's demands follow: days no longer covered are cancelled and their live assignments get a `date_conflict` alert, new days get new demands and one `date_conflict` alert for the MRO, and open demands take the new `reps_required`. Cancelling the event cancels all its demands.

## Overtime

`GET /overtime/opportunities?start=...&end=...&mro_id=` lists open demands in the window that are still short of reps. Each has `demand_id`, `mro_id`, `aircraft_type_id`, `demand_type`, `start_time`, `end_time`, `priority`, `reps_needed`, `still_needed`, and:

- `eligible`: reps with a valid certification, no approved leave or training, and minimum rest (field service rest when away from base) around existing work. Most senior first, which is the order to offer voluntary overtime; mandatory overtime goes from the end. Each has `rep_id`, `name`, `seniority_rank`, `response` to a solicitation, `field_service`, `home_team` (based at the MRO's `covering_base`; listed first), and `pattern_day_off` (true when the shift falls on a pattern day off).
- `ineligible`: the other reps with a `reason`.

## Alerts

| Route | Notes |
| --- | --- |
| `GET /alerts` | Newest first. Filters: `mro_id` (location), `rep_id`, `demand_id`, `alert_type`, `severity` (`info`, `warning`, `critical`), `acknowledged`, `limit` (default 200) |
| `POST /alerts` | Add an alert by hand |
| `PATCH /alerts/{alert_id}` | `{"acknowledged": true}` |
| `POST /alerts/scan` | Query `start`, `end` (default now to 90 days ahead) and `training_days` (default 60). Raises `coverage_gap` (critical within 7 days), `no_qualified_rep`, `shortage` (more reps needed on a day at an MRO than qualified reps not on leave, worst day per week), `training_due`, `schedule_horizon` (a `7-7` rep has shift days in the next `schedule_publish_days` with no assignment, leave, or training), and `vacation_unused` (vacation and stat days for the year not all in the schedule; next year is checked from December 1). Acknowledges earlier alerts of these types that no longer apply. Returns `created` and `resolved` |

Alert types: `coverage_gap`, `no_qualified_rep`, `shortage`, `date_conflict`, `training_due`, `training_expired`, `training_conflict`, `vacation_limit`, `sick_limit`, `rest`, `shift_pattern`, `qualification`, `seniority`, `no_aircraft`, `schedule_horizon`, `vacation_unused`. Compliance types come from the [compliance check](architecture.md#compliance-checks); `date_conflict` comes from maintenance event changes.

## Dashboards

- `GET /dashboards/workforce?start=...&end=...&mro_id=`: `available`, `assigned`, and `on_leave` counts, and `reps` with `status`, `mro_ids`, `leave_reasons`, and `assigned_hours`. With `mro_id`, only reps based at or assigned to that MRO.
- `GET /dashboards/coverage?start=...&end=...&mro_id=`: per MRO and week, `shifts`, `seats_needed`, `seats_filled`, and `gap`.

Both accept windows up to 366 days.

---

## Response schemas

### TechRep

```json
{
  "id": 1,
  "name": "Ana Lopez",
  "email": "ana.lopez@example.com",
  "home_base": "YYC",
  "active": true,
  "classification": "AME",
  "cba_group": 1,
  "union_seniority_date": "2015-03-01",
  "shift_pattern_code": "5-5-4",
  "shift_cycle_start": "2026-11-02",
  "banked_ot_hours": 0.0,
  "seniority_rank": 12,
  "phone": "(403) 555-0142",
  "certified_aircraft_type_ids": [1, 2]
}
```

`email`, `classification`, `cba_group`, `union_seniority_date`, `shift_pattern_code`, `shift_cycle_start`, `seniority_rank`, and `phone` can be `null`.

### Certification

```json
{"aircraft_type_id": 1, "certified_on": "2024-01-15", "expires_on": "2027-01-15"}
```

Both dates can be `null`.

### AircraftType

```json
{"id": 1, "model_name": "737 MAX 8", "manufacturer": "Boeing"}
```

### MroLocation

```json
{"id": 1, "facility_name": "YYC Hangar 1", "location": "Calgary", "airport_code": "YYC", "timezone": "America/Edmonton"}
```

### TravelTime

```json
{"home_base": "YVR", "mro_id": 1, "travel_hours": 2.5, "distance_km": 690}
```

### CbaRules

| Field | Type | CBA | Meaning |
| --- | --- | --- | --- |
| `id`, `name` | integer, string | | |
| `effective_from`, `effective_to` | date, date or null | | `effective_to` is exclusive; null is open-ended |
| `min_rest_hours` | number | 19-7.01 | Rest between shifts (10) |
| `min_rest_hours_trade` | number | 19-7.02 | Rest after a trade or pickup (8) |
| `max_consecutive_scheduled_days` | integer | 19-1.05 | (7) |
| `max_consecutive_worked_days` | integer | 19-1.06 | (11) |
| `min_hours_off_per_set` | number | 19-1.07 | (48) |
| `three_days_off_window_days` | integer | 19-1.07 | Rolling window for the days-off run (28) |
| `consecutive_days_off_required` | integer | 19-1.07 | Length of that run (3) |
| `avg_weekly_hours` | number | 19-1.01 to 19-1.03 | (40) |
| `averaging_weeks_major_base`, `averaging_weeks_other_base` | integer | 19-1.01, 19-1.02 | (26, 52) |
| `major_bases` | string[] | 19-1.01 | Bases using the 26-week period for Group 1 |
| `averaging_anchor_date` | date or null | | Start of the first averaging period; null uses `effective_from` |
| `max_field_duty_hours` | number | 21-1.03 | Duty day including travel (16) |
| `post_field_rest_hours` | number | 21-1.05 | (10) |
| `base_coverage_notice_hours` | integer | 21-2.01 | (48) |
| `max_vehicle_travel_km` | integer | 21-1.09 | (550) |
| `field_service_rate` | number | 21-2.02 | (1.5) |
| `aog_pay_buffer_hours` | number | 21-3.02 | Paid before start and after return (2) |
| `ot_rate_voluntary` | number | 16-1.04 | First tier (1.5) |
| `ot_voluntary_tier_hours` | number | 16-1.04 | Tier size per pay period (8) |
| `ot_rate_voluntary_over_tier` | number | 16-1.04 | (1.75) |
| `ot_rate_mandatory` | number | 16-1.06, 21-2.12 | (2.0) |
| `max_banked_ot_hours` | number | 15-4.02 | (80) |
| `stat_holiday_rate` | number | 29-3.08 | (1.5) |
| `min_days_off_between_rotations` | integer | | Full days off between two runs of worked days (2) |
| `max_reps_off_per_week` | integer | | Company-wide cap on reps on approved vacation in one week (3) |
| `continuity_lookback_days` | integer | | Days of history the solver uses to keep reps at the same MRO (90) |
| `schedule_publish_days` | integer | | Days ahead each rep's schedule must be plotted (30) |

Values in brackets are the 2024-2029 agreement defaults.

### ShiftPattern

```json
{
  "code": "5-5-4",
  "description": "5 on, 5 off, 4 on, 5 off, 5 on, 4 off (Groups I, II, Base Planner)",
  "cycle": "WWWWWOOOOOWWWWOOOOOWWWWWOOOO",
  "shift_hours": 11.42,
  "paid_meal_breaks": 2,
  "cba_reference": "19-1.08",
  "requires_consecutive_days_off": true,
  "start_windows": [
    {"shift_name": "day", "earliest_start": "05:00:00", "latest_start": "08:00:00"},
    {"shift_name": "afternoon", "earliest_start": "13:00:00", "latest_start": "15:00:00"},
    {"shift_name": "night", "earliest_start": "18:00:00", "latest_start": "21:00:00"}
  ]
}
```

`cycle` has one character per day from `shift_cycle_start`: `W` is a work day, `O` is a day off.

### Holiday

```json
{"holiday_date": "2026-12-25", "name": "Christmas Day"}
```

### PayPeriod

```json
{"id": 1, "start_date": "2026-11-01", "end_date": "2026-11-16"}
```

`end_date` is exclusive.

### Unavailability

```json
{
  "id": 1,
  "rep_id": 1,
  "reason": "vacation",
  "start_time": "2026-12-20T00:00:00-07:00",
  "end_time": "2027-01-03T00:00:00-07:00",
  "status": "approved",
  "notes": null
}
```

### Demand

```json
{
  "id": 3,
  "mro_id": 1,
  "aircraft_type_id": 1,
  "demand_type": "base_coverage",
  "start_time": "2026-11-07T08:00:00-07:00",
  "end_time": "2026-11-07T18:00:00-07:00",
  "reps_needed": 2,
  "priority": 2,
  "status": "open",
  "notes": null
}
```

### DemandResponse

```json
{"demand_id": 3, "rep_id": 1, "response": "accepted", "responded_at": "2026-10-17T08:00:17-06:00"}
```

### Assignment

```json
{
  "id": 12,
  "rep_id": 6,
  "mro_id": 1,
  "aircraft_type_id": 1,
  "demand_id": 4,
  "start_time": "2026-11-04T06:00:00-07:00",
  "end_time": "2026-11-04T19:00:00-07:00",
  "status": "proposed",
  "overtime_type": "none",
  "overtime_hours": 0.0,
  "travel_hours": 2.5,
  "created_at": "2026-10-17T08:00:18-06:00"
}
```

`start_time` and `end_time` are on-site times. The rep is away from base for `travel_hours` before and after.

### ProposedAssignment

| Field | Type | Meaning |
| --- | --- | --- |
| `assignment_id` | integer or null | Saved assignment ID when `save` is true |
| `demand_id`, `rep_id`, `mro_id` | integer | |
| `start_time`, `end_time` | date-time | On-site times |
| `field_service` | boolean | The MRO is away from the rep's home base |
| `mandatory` | boolean | Assigned without the rep's acceptance |
| `travel_hours` | number | One way |
| `paid_hours` | number | On-site hours, plus round-trip travel and AOG buffers for field service |
| `overtime_hours` | number | Hours on days off, past the regular shift, or past the averaging budget |
| `premium_hours` | number | Extra pay above straight time, in hours. Excludes the 1.75x tier surcharge, which is applied per pay period |

### UnfilledDemand

| Field | Type | Meaning |
| --- | --- | --- |
| `demand_id` | integer | |
| `still_needed` | integer | Reps still required |
| `reason` | string | Why the solver could not fill it, for example `No eligible rep: 3 did not accept; set allow_mandatory to assign in reverse seniority` |

### ComplianceWarning

| Field | Type | Meaning |
| --- | --- | --- |
| `alert_type` | string | `rest`, `shift_pattern`, `training_conflict`, `training_expired`, `vacation_limit`, `sick_limit`, `qualification`, `seniority`, or `no_aircraft` |
| `severity` | string | `info`, `warning`, or `critical` |
| `message` | string | For example `Ana Lopez: 6.0 h rest before assignment 41 on 2026-11-03, under the 10 h minimum` |
| `rep_id` | integer | |
| `mro_id`, `demand_id`, `assignment_id` | integer or null | Set when the finding is about one assignment |

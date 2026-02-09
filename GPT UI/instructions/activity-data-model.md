# Activity Data Model
## Complete Schema Definition for Amanita Activities

**Источник:** `GPT UI/docs/Zeya888 — Estonians888 — Estonian Eventify.pdf`  
**Версия:** 1.0  
**Дата:** 2025-01-13

---

## 0. Core Concept: Event vs Service

The Activity data model introduces a **first-class discriminator** `activity_type` with two values:
- `event` — scheduled occurrences with fixed dates/times
- `service` — on-demand offerings by appointment

**Why this is model-level differentiation:**

This is **not a UI concern** and **not a minor field variation**. It affects:
- how time is represented (schedule vs availability),
- how capacity is interpreted (group events vs individual sessions),
- how pricing is structured (tickets vs hourly rates),
- how search and filtering work,
- which fields are required at review and publication stages.

**Unified Lifecycle, Divergent Semantics:**

Both activity types:
- share the same lifecycle (Draft → Review → Approved → Published),
- pass through the same policy gate (КоныРода),
- appear in the same discovery surface,
- are governed by the same privacy and compliance rules.

They differ only where semantics truly diverge:
- timing (schedule vs availability),
- participation (group capacity vs session mode),
- booking and engagement.

---

## 1. Identity & Lifecycle (common for all)

**Fields:**
- `activity_id` (string) — unique identifier
- `activity_type` (enum: `"event"` | `"service"`) — **key discriminator**
- `active` (boolean) — lifecycle indicator: `false` = draft (not in search), `true` = published. **No status enum** (Draft/SentToReview/Approved/Published) anywhere in backend, API, or web layer; approval/review semantics are enforced at **UI level via built-in gate keeper instruction**.
- `versioning` (object) — drafts/versions, audit trail
- `creator/owner_reference` (string) — pseudonymous Activator identifier (no PII)
- `timestamps` (object):
  - `created_at` (ISO 8601)
  - `updated_at` (ISO 8601)
  - `published_at` (ISO 8601, optional)

**Notes:**
- `activity_type` is the first field after ID, emphasizing its criticality
- `creator/owner` is a reference, not PII (privacy-first approach)
- `versioning` supports change history
- **Policy:** No ActivityStatus enum anywhere. Only `active` (bool). Gate keeper validation is UI-level.

---

## 2. Core Description (common for all)

**Fields:**
- `title` (string) — Activity name
- `short_summary` (string) — brief description
- `full_description` (string) — detailed description
- `format` (enum) — controlled list + `"other"`:
  - `"session"` — one-time session
  - `"workshop"` — workshop format
  - `"ceremony"` — ceremony format
  - `"class_regular"` — recurring class
  - `"class_single"` — single class occurrence
  - `"retreat"` — retreat format
  - `"performance"` — performance/show
  - `"other"` — other format (requires `format_other_label`)
- `format_other_label` (string, optional) — user-provided label when `format = "other"`
- `categories` (object) — two-level taxonomy + fallback:
  - `primary` (object) — level 1 category
  - `secondary` (array) — level 2 categories
  - `freeform_user_tags` (array, optional) — unmapped user terms
- `age_groups` (array of enum) — target age groups:
  - `"babies"`
  - `"toddlers"`
  - `"primary_schoolers"`
  - `"teenagers"`
  - `"youngsters_18_25"`
  - `"adults"`
  - `"seniors"`
- `parental_accompaniment` (enum, optional) — for children's activities:
  - `"allowed"` — parents may accompany
  - `"required"` — parents must accompany
  - `"optional"` — parents may choose
- `language_requirements` (object):
  - `mode` (enum):
    - `"irrelevant"` — language not important
    - `"understand_only"` — understanding required
    - `"speak_and_understand"` — speaking and understanding required
    - `"mixed"` — multiple languages with different requirements
  - `languages_to_understand` (array of string) — ISO 639-1 language codes
  - `languages_to_speak` (array of string) — ISO 639-1 language codes
- `media` (object, optional):
  - `official_site` (string, URL)
  - `social_links` (array of object):
    - `platform` (enum: `"instagram"` | `"facebook"` | `"vk"` | `"telegram"` | `"other"`)
    - `url` (string)
    - `account` (string, optional)
  - `event_service_specific_links` (array of string, optional) — type-specific links
- `policy_notes` (string, optional) — disclaimers/restrictions (no clinical content)

**Notes:**
- `format` is a controlled list with fallback `"other"`
- `taxonomy` is two-level with user suggestion capability
- `language_requirements` is a structured model (mode + language lists)
- `parental_accompaniment` is specific to children's activities

---

## 3. Delivery & Location (common, with nuances)

**Fields:**
- `delivery_mode` (enum): `"in_person"` | `"online"` | `"hybrid"`
- `location_info` (object):
  - `city` (string, optional)
  - `area` (string, optional)
  - `venue` (string, optional) — applicable for in-person
  - `online_platform` (string, optional) — platform name for online
  - `online_link` (string, URL, optional) — applicable for online/hybrid
- `service_area` (object, optional) — more common for services:
  - `radius` (number, optional) — radius in km
  - `districts` (array of string, optional)
  - `travel_notes` (string, optional)

**Notes:**
- `service_area` is more commonly used for services but can be general
- `delivery_mode` is common for both types

---

## 4. Timing (main differentiation point)

**Critical distinction:**

### If `activity_type = "event"`:

**Fields:**
- `event_timing` (object):
  - `schedule_model` (enum): `"fixed_dates"` | `"recurring"`
  - `fixed_dates` (array of object, conditional):
    - `start` (ISO 8601)
    - `end` (ISO 8601)
    - `timezone` (string, IANA timezone)
  - `recurring` (object, conditional):
    - `recurrence_rule` (string) — RRULE format
    - `start_date` (ISO 8601)
    - `end_date` (ISO 8601, optional)
    - `timezone` (string, IANA timezone)
  - `exceptions` (array of object, optional):
    - `date` (ISO 8601)
    - `reason` (string, optional)
  - `overrides` (array of object, optional):
    - `date` (ISO 8601)
    - `start` (ISO 8601)
    - `end` (ISO 8601)
  - `next_occurrence` (ISO 8601, computed) — ability to compute next occurrence

### If `activity_type = "service"`:

**Fields:**
- `service_timing` (object):
  - `availability_type` (enum):
    - `"by_request"` — by appointment/request
    - `"fixed_windows"` — fixed availability windows
    - `"bookable_slots"` — (future) bookable time slots
  - `availability_windows` (array of object, conditional):
    - `day_of_week` (enum: `"monday"` | `"tuesday"` | `"wednesday"` | `"thursday"` | `"friday"` | `"saturday"` | `"sunday"`)
    - `start_time` (string, HH:MM format)
    - `end_time` (string, HH:MM format)
    - `timezone` (string, IANA timezone)
  - `booking_policy` (string) — how to book/appoint

**☑ Rule:** `event_timing` and `service_timing` are **mutually exclusive**.

**Notes:**
- This is the only section where data structure **completely differs** by type
- Event = fixed dates/schedule
- Service = availability/booking policy
- Mutually exclusive fields = explicit architectural decision against ambiguity

---

## 5. Participation & Capacity (semantic differentiation)

### If `activity_type = "event"`:

**Fields:**
- `event_capacity` (object):
  - `group_capacity` (number, optional) — total seats/participants
  - `seats` (number, optional) — available seats
  - `min_participants` (number, optional)
  - `max_participants` (number, optional)

### If `activity_type = "service"`:

**Fields:**
- `service_participation` (object):
  - `session_mode` (enum):
    - `"one_to_one"` — individual session
    - `"family"` — family session
    - `"small_group"` — small group session
  - `concurrent_clients` (number, default: 1) — usually 1, but can be more
  - `practitioner_to_client_model` (string, optional) — description (no personalization)

**☑ Rule:** `event_capacity` and `service_participation` are **mutually exclusive**.

**Notes:**
- Event focuses on group capacity (seats, participants)
- Service focuses on session mode (1:1, family, small group)
- `concurrent_clients` is specific to services (usually 1, but can be more)

---

## 6. Duration & Pricing (partially common, but structure differs)

### If `activity_type = "event"`:

**Fields:**
- `event_duration` (object):
  - `duration_type` (enum): `"per_occurrence"` | `"fixed"`
  - `per_occurrence` (object, conditional):
    - `duration_minutes` (number) — duration per occurrence
  - `fixed` (string, conditional) — fixed duration description
- `event_pricing` (object):
  - `pricing_type` (enum): `"ticket_price"` | `"donation"` | `"free"`
  - `ticket_price` (object, conditional):
    - `amount` (number)
    - `currency` (string, ISO 4217)
    - `price_range` (object, optional):
      - `min` (number)
      - `max` (number)

### If `activity_type = "service"`:

**Fields:**
- `service_duration_options` (array of object):
  - `duration_minutes` (number) — e.g., 30, 60, 90, custom
  - `label` (string, optional) — e.g., "Standard", "Extended"
- `service_pricing_model` (object):
  - `model` (enum):
    - `"per_session"` — per session pricing
    - `"per_hour"` — hourly pricing
    - `"per_package"` — package pricing
    - `"donation"` — donation-based
    - `"free"` — free service
  - `package_definition` (object, optional):
    - `sessions_count` (number)
    - `total_price` (number)
    - `currency` (string, ISO 4217)

**☑ Rule:** `event_duration`/`event_pricing` and `service_duration_options`/`service_pricing_model` are **mutually exclusive**.

**Notes:**
- Event = fixed duration per event
- Service = duration options (30/60/90 minutes)
- Event = pricing as ticket/event price
- Service = pricing model (per_session, per_hour, per_package)

---

## 7. Booking / CTA (call-to-action) (differentiation)

### If `activity_type = "event"`:

**Fields:**
- `event_cta` (object):
  - `event_page_link` (string, URL)
  - `tickets_link` (string, URL, optional)

### If `activity_type = "service"`:

**Fields:**
- `service_cta` (object):
  - `booking_url` (string, URL, optional) — Calendly/site/form
  - `contact_channel` (object, optional):
    - `type` (enum): `"social_link"` | `"email"` | `"phone"` | `"other"`
    - `value` (string)
  - `amanita_booking` (boolean, default: false) — "Amanita booking (future)"

**☑ Rule:** `event_cta` and `service_cta` are **mutually exclusive**.

**Notes:**
- Event = links to event page and tickets
- Service = booking URL or contact via public channel
- "Amanita booking (future)" = platform may provide booking in the future

---

## 8. Source & Provenance (common for all)

**Fields:**
- `sources` (object):
  - `canonical_url` (string, URL, optional)
  - `source_type` (enum): `"manual"` | `"link"` | `"screenshot"` | `"pdf"`
  - `raw_asset_ref` (string, optional) — TTL reference to raw asset
  - `dedup_hints` (object, optional):
    - `possible_duplicates` (array of string) — activity IDs
    - `update_vs_new` (enum, optional): `"update"` | `"new"`

**Notes:**
- `sources` tracks data origin
- `dedup_hints` supports deduplication and updates
- `raw_asset_ref` with TTL = temporary storage of source files

---

## 9. Review Metadata (common for all)

**Fields:**
- `review_submission` (object):
  - `submitted_at` (ISO 8601)
  - `notes` (string, optional)
- `policy_gate_result` (object):
  - `status` (enum): `"approved"` | `"rejected"` | `"needs_clarification"`
  - `reasons` (array of object) — structured reasons:
    - `code` (string) — reason code
    - `message` (string) — human-readable message
    - `field` (string, optional) — related field
  - `policy_ref` (string) — КоныРода version/reference

**Notes:**
- `policy_gate_result` = result of КоныРода Gate check
- `reasons` = structured reasons (not free-form text)
- `policy_ref` = version of policy used for check

---

## 10. Conditional Field Rules

### Rule 1: Activity Type Determines Field Sets

**If `activity_type = "event"`:**
- MUST have: `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`
- MUST NOT have: `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`

**If `activity_type = "service"`:**
- MUST have: `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`
- MUST NOT have: `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`

### Rule 2: Common Fields

These fields are extracted the same way regardless of type:
- `title`, `short_summary`, `full_description`
- `format`, `categories`, `taxonomy`
- `age_groups`, `parental_accompaniment`
- `language_requirements`
- `delivery_mode`, `location_info`
- `media`, `external_links`
- `sources`, `review_metadata`

---

## 11. Field Completeness Requirements by Status

### Draft Status (minimum completeness):
- `activity_type` (required)
- `title` (required)
- `short_summary` or `full_description` (at least one required)
- Conditional fields based on `activity_type` (see Rule 1)

### SentToReview Status (review completeness):
- All Draft requirements +
- `full_description` (required, minimum 50 characters)
- `format` (required)
- `delivery_mode` (required)
- `location_info` (required if `delivery_mode != "online"`)
- Complete timing information (event_timing or service_timing)
- Complete participation information (event_capacity or service_participation)

### Approved Status (publication readiness):
- All SentToReview requirements +
- All optional fields that affect discovery/search
- Complete media/external links (if applicable)
- Complete CTA information (event_cta or service_cta)

---

## 12. Architecture Principles

### 12.1 One Field → One Meaning
- One field → one value
- No overloaded or ambiguous fields
- No free-form text where controlled values exist
- All enums and categories must be canonical

### 12.2 Conditional Fields Based on Type
- Some fields are mutually exclusive based on `activity_type`
- This must be validated at schema level
- Attempting to represent services as "events without dates" leads to ambiguity

### 12.3 Unified Lifecycle, Divergent Semantics
- Both types share the same lifecycle
- Both types pass through the same policy gate
- Both types appear in the same discovery surface
- They differ only where semantics truly diverge

---

**Статус документа:** ✅ Complete  
**Использование:** Reference for parsing, validation, and normalization instructions  
**Связанные документы:**
- `GPT UI/docs/tasks/task-Ingest-Deep-Parsing.md` — uses this model for field extraction
- `GPT UI/docs/tasks/task-Ingest-validation.md` — uses this model for validation rules
- `GPT UI/docs/tasks/task-activity-normalizer.md` — uses this model for normalization

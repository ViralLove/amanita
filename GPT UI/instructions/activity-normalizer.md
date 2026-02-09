# Activity Normalizer Instruction
## Canonical Structuring & Data Normalization

### Purpose

Activity Normalizer is responsible for transforming **validated and policy-admitted input**
into the **canonical Activity data model** used by the Amanita backend.

Its purpose is to:
- normalize extracted Activity data,
- enforce canonical formats and controlled vocabularies,
- prepare a clean, predictable payload for backend API consumption.

This instruction is purely **structural and deterministic**.

It does NOT:
- parse raw input,
- ask clarification questions,
- evaluate policy compliance,
- call backend APIs,
- decide statuses or transitions.

---

## 1. Scope of Responsibility

This instruction is activated **only in INGEST mode**.

It handles:
- normalization of validated Activity data into canonical JSON format,
- enforcement of canonical formats and controlled vocabularies,
- conditional field normalization based on `activity_type` (event vs service),
- preparation of clean, predictable payload for backend API consumption.

It does NOT:
- parse raw input (Ingest Deep Parsing does this),
- validate structural completeness (Ingest Validation does this),
- evaluate policy compliance (KоныРода Gate does this),
- interact with backend systems (API Orchestrator does this),
- decide statuses or transitions (backend systems do this).

**Normalization Principles:**
- One field → one meaning
- No overloaded or ambiguous fields
- No free-form text where controlled values exist
- All enums and categories must be canonical
- Conditional fields are mutually exclusive (event_* vs service_*)

**Activity Data Model Reference:**

This instruction MUST normalize data into the **Activity Data Model** defined in:
- `GPT UI/docs/activity-data-model.md`

The model defines:
- Complete field structure for all Activity types
- Conditional fields based on `activity_type` (event vs service)
- Enum values for all controlled vocabularies
- Canonical formats and structures

**Critical:** Normalization MUST handle conditional fields based on `activity_type`:
- If `activity_type = "event"` → normalize `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`
- If `activity_type = "service"` → normalize `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`

---

## 2. Source of Truth

The document **Activity Data Model** (`GPT UI/docs/activity-data-model.md`) is the **single authoritative source** for canonical schema and normalization rules.

This instruction MUST:
- follow Activity Data Model exactly,
- not reinterpret or modify field structures,
- not invent new fields or enum values,
- not deviate from canonical formats.

If ambiguity exists:
- resolve it conservatively,
- prioritize strictness over convenience,
- reject ambiguity early.

**Activity Data Model Location:**
- `GPT UI/docs/activity-data-model.md`

**Critical:** This instruction does NOT create schema rules. It only normalizes data according to Activity Data Model.

---

## 3. When This Instruction Is Applied

Activity Normalizer is applied:

- **after** Ingest Validation completes validation,
- **after** KоныРода Gate completes policy evaluation (if Gate activated),
- **before** API Orchestrator calls backend API.

It is activated in two scenarios:

1. **After Validation (Draft-ready):**
   - Validation status = "Draft-ready"
   - Gate НЕ активируется (только для SentToReview-ready/Approved-ready)
   - Normalizer получает данные напрямую от Validation
   - Normalizer нормализует данные для создания Draft через API Orchestrator

2. **After Gate (SentToReview-ready/Approved-ready):**
   - Validation status = "SentToReview-ready" или "Approved-ready"
   - Validation активирует Gate
   - Gate выполняет policy evaluation
   - Gate возвращает `policy_gate_result.status = "approved"`
   - Gate передает данные в Normalizer
   - Normalizer получает данные от Gate (включая `policy_gate_result`)
   - Normalizer нормализует данные для отправки на review или публикации

**Activation Conditions:**

Normalizer активируется ТОЛЬКО если:
- Validation completed successfully (validation_status = "Draft-ready" или "SentToReview-ready" или "Approved-ready")
- If Gate activated: Gate returned `policy_gate_result.status = "approved"`
- All required fields for normalization are present

Normalizer НЕ активируется если:
- Validation status = "Draft-not-ready" или "SentToReview-not-ready" или "Approved-not-ready"
- Gate returned `policy_gate_result.status = "rejected"` или `"needs_clarification"`
- Required fields for normalization are missing

---

## 4. Input Contract

This instruction receives as input:

- a structured Activity draft produced by:
  - Ingest Validation Instruction,
  - and (when applicable) KоныРода Admission Gate;
- with all required fields for the current stage present;
- without raw sources (screenshots, PDFs, unstructured text);
- with `activity_type` already determined and validated.

**Note:** This section describes the **structure** of input data.  
For the **workflow** of how Normalizer is activated, see Sections 10-12.

### 4.1 Input from Ingest Validation (Draft-ready)

**When:** Validation status = "Draft-ready", Gate не активируется

**Input structure from Validation:**
```json
{
  "validated_data": {
    // All validated fields matching Activity Data Model
    // See GPT UI/docs/activity-data-model.md for complete schema
    "activity_type": "event" | "service",
    "title": "string",
    "full_description": "string",
    // ... all other validated fields
    // Conditional fields based on activity_type:
    // If event: event_timing, event_capacity, event_duration, event_pricing, event_cta
    // If service: service_timing, service_participation, service_duration_options, service_pricing_model, service_cta
  },
  "validation_metadata": {
    "validation_status": "Draft-ready",
    "missing_fields": {
      "Draft": ["field1", "field2"],
      "SentToReview": ["field3", "field4"],
      "Approved": ["field5"]
    },
    "ambiguities": [...],
    "duplicate_hints": [...],
    "update_vs_new": "new" | "update" | "ambiguous",
    "existing_activity_hint": {...} | null,
    "safety_flags": [...]
  }
}
```

**Reference:** For complete structure, see Ingest Validation Instruction Section 12 (Output Contract).

**Note:** `policy_gate_result` отсутствует, так как Gate не активировался.

### 4.2 Input from KоныРода Gate (SentToReview-ready/Approved-ready)

**When:** Gate активировался и вернул `policy_gate_result.status = "approved"`

**Input structure from Gate:**
```json
{
  "validated_data": {
    // All validated fields от Validation (unchanged)
    // See Section 4.1 for structure
  },
  "validation_metadata": {
    // All validation_metadata от Validation (unchanged)
    // See Section 4.1 for structure
  },
  "policy_gate_result": {
    "status": "approved",
    "reasons": [
      {
        "code": "string",
        "message": "string",
        "field": "string" | null,
        "principle_ref": "string"
      }
    ],
    "policy_ref": "string",
    "clarification_prompt": null
  }
}
```

**Reference:** For complete structure, see KоныРода Gate Instruction Section 10 (Output Contract).

**Note:** `policy_gate_result` присутствует и должен быть включен в нормализованный JSON.

### 4.3 Minimum Requirements for Normalization

Normalizer requires for normalization:

**For all inputs:**
- `activity_type` (определен и валидирован)
- `title` (предоставлен)
- `full_description` или `short_summary` (минимум одно предоставлено)
- Conditional fields based on `activity_type` (если применимо)

**Algorithm for checking minimum requirements:**

```
1. Normalizer receives input (from Validation or Gate)
2. Check activity_type:
   - If missing → return "normalization_failed: activity_type_missing"
   - If not "event" or "service" → return "normalization_failed: invalid_activity_type"

3. Check minimum required fields:
   - If title missing → return "normalization_failed: title_missing"
   - If full_description AND short_summary missing → return "normalization_failed: description_missing"

4. Check conditional fields based on activity_type:
   - If activity_type = "event" → check for event_* fields (if applicable)
   - If activity_type = "service" → check for service_* fields (if applicable)

5. If any required field missing:
   - Return "normalization_failed: missing_required_fields"
   - List missing fields
   - Hand control back to Validation (NOT directly to user)

6. If all requirements met → proceed with normalization
```

**Important:** Normalizer НЕ может напрямую запрашивать данные у user — только через Validation.

---

## 5. Normalization Algorithm

Normalizer выполняет нормализацию в следующей последовательности:

### 5.1 Normalization Steps

**Algorithm (execute in order):**

```
1. **Validate Input:**
   - Check minimum requirements (Section 4.3)
   - If insufficient data → return "normalization_failed"
   - Hand control back to Validation

2. **Preserve activity_type:**
   - activity_type уже валидирован upstream
   - Сохранить без изменений
   - Использовать для определения условных полей

3. **Normalize Common Fields:**
   - Text fields (title, short_summary, full_description) → trim whitespace, remove duplicates
   - Format → map to canonical enum values
   - Categories & Taxonomy → map to two-level taxonomy
   - Age Groups → normalize to canonical groups
   - Language Requirements → normalize structure
   - Location → normalize structure (delivery_mode, location_info, service_area)
   - Media & External Links → normalize structure

4. **Normalize Conditional Fields Based on activity_type:**
   - If activity_type = "event":
     - Normalize event_timing (schedule_model, fixed_dates/recurring, exceptions, overrides)
     - Normalize event_capacity (group_capacity, seats, min/max participants)
     - Normalize event_duration (duration_type, per_occurrence/fixed)
     - Normalize event_pricing (pricing_type, ticket_price/donation/free)
     - Normalize event_cta (event_page_link, tickets_link)
     - Remove any service_* fields if present
   
   - If activity_type = "service":
     - Normalize service_timing (availability_type, availability_windows, booking_policy)
     - Normalize service_participation (session_mode, concurrent_clients)
     - Normalize service_duration_options (array of duration_minutes, label)
     - Normalize service_pricing_model (model, package_definition)
     - Normalize service_cta (booking_url, contact_channel, amanita_booking)
     - Remove any event_* fields if present

5. **Check Conditional Field Integrity:**
   - Verify mutually exclusive fields (event_* vs service_*)
   - If conflicts detected → return "normalization_failed: conditional_field_conflict"
   - Specify which fields conflict

6. **Normalize Sources & Provenance:**
   - Normalize sources structure (canonical_url, source_type, raw_asset_ref, dedup_hints)
   - Include validation_metadata in sources (if applicable)

7. **Normalize Review Metadata:**
   - If policy_gate_result present (from Gate) → include in review_metadata
   - Structure policy_gate_result according to Activity Data Model Section 9
   - If policy_gate_result absent (from Validation) → review_metadata.policy_gate_result = null

8. **Validate Output Structure:**
   - Check all enum values match canonical values from Activity Data Model
   - Check all nested structures match Activity Data Model schema
   - Check conditional fields integrity (event_* vs service_*)
   - If validation fails → return "normalization_failed: invalid_structure"

9. **Return Normalized JSON:**
   - Return fully normalized Activity JSON object
   - Compliant with Activity Data Model
   - Deterministic for the same input
   - Free of ambiguity and free-form artifacts
```

**Important:** Normalization is structural, not semantic. Normalizer does NOT interpret meaning, invent data, or apply policy logic.

---

## 6. Field Normalization Rules

### 6.1 Text Fields

- Trim whitespace.
- Remove duplicate or redundant phrasing.
- Preserve original meaning; do not rewrite creatively.
- Ensure descriptions are neutral and factual.

### 6.2 Formats

- Map user-provided formats to canonical format enums.
- Canonical enum values (see `GPT UI/docs/activity-data-model.md` Section 2):
  - `"session"` — one-time session
  - `"workshop"` — workshop format
  - `"ceremony"` — ceremony format
  - `"class_regular"` — recurring class
  - `"class_single"` — single class occurrence
  - `"retreat"` — retreat format
  - `"performance"` — performance/show
  - `"other"` — other format (requires `format_other_label`)

- If no exact match exists:
  - use `other`,
  - preserve original label in `format_other_label`.

Examples:
- "какао церемония" → `ceremony`
- "регулярные танцы" → `class_regular` (if recurring) or `session` (if one-time)
- "еженедельный кружок" → `class_regular`
- "разовое мероприятие" → `session`

### 6.3 Categories & Taxonomy

- Map categories to the predefined two-level taxonomy.
- Assign:
  - primary category (level 1),
  - optional secondary categories (level 2).
- Preserve unmapped user terms as `freeform_user_tags`.

If no suitable category exists:
- flag a taxonomy gap,
- do not invent new categories.

### 6.4 Age Groups

- Normalize age indications to canonical groups (see `GPT UI/docs/activity-data-model.md` Section 2):
  - `"babies"`
  - `"toddlers"`
  - `"primary_schoolers"`
  - `"teenagers"`
  - `"youngsters_18_25"`
  - `"adults"`
  - `"seniors"`

- Resolve conflicts conservatively.
- If ambiguous:
  - require clarification upstream.

- Related field: `parental_accompaniment` (enum: `"allowed"` | `"required"` | `"optional"`)
  - Normalize only if age_groups include children (babies, toddlers, primary_schoolers, teenagers)

### 6.5 Language Requirements

Normalize language rules into structure (see `GPT UI/docs/activity-data-model.md` Section 2):

- `mode` (enum):
  - `"irrelevant"` — language not important
  - `"understand_only"` — understanding required
  - `"speak_and_understand"` — speaking and understanding required
  - `"mixed"` — multiple languages with different requirements

- `languages_to_understand` (array of string) — ISO 639-1 language codes (e.g., "ru", "en")
- `languages_to_speak` (array of string) — ISO 639-1 language codes

If language is "not important":
- set `mode` to `"irrelevant"`.
- set `languages_to_understand` and `languages_to_speak` to empty arrays.

### 6.6 Location

Normalize location into structure (see `GPT UI/docs/activity-data-model.md` Section 3):

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

For in-person:
- normalize city and venue names if provided.
- do not infer precise addresses unless explicitly given.

For online:
- ensure `online_platform` or `online_link` exists.

For hybrid:
- ensure both in-person location and online link are present.

### 6.7 Timing Normalization (Event vs Service)

**CRITICAL:** Timing normalization differs based on `activity_type`.

#### For `activity_type = "event"`:

Normalize `event_timing` structure (see `GPT UI/docs/activity-data-model.md` Section 4):

- `schedule_model` (enum): `"fixed_dates"` | `"recurring"`

- If `schedule_model = "fixed_dates"`:
  - `fixed_dates` (array of object):
    - `start` (ISO 8601)
    - `end` (ISO 8601)
    - `timezone` (string, IANA timezone)

- If `schedule_model = "recurring"`:
  - `recurring` (object):
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

- Time zones must be explicit (IANA format).
- If schedule is "TBA":
  - mark explicitly as such (use `schedule_model: "fixed_dates"` with empty `fixed_dates` array and note).

#### For `activity_type = "service"`:

Normalize `service_timing` structure (see `GPT UI/docs/activity-data-model.md` Section 4):

- `availability_type` (enum):
  - `"by_request"` — by appointment/request
  - `"fixed_windows"` — fixed availability windows
  - `"bookable_slots"` — (future) bookable time slots

- `availability_windows` (array of object, conditional — if `availability_type = "fixed_windows"`):
  - `day_of_week` (enum: `"monday"` | `"tuesday"` | `"wednesday"` | `"thursday"` | `"friday"` | `"saturday"` | `"sunday"`)
  - `start_time` (string, HH:MM format)
  - `end_time` (string, HH:MM format)
  - `timezone` (string, IANA timezone)

- `booking_policy` (string) — how to book/appoint

**☑ Rule:** Normalize `event_timing` OR `service_timing`, never both.

### 6.8 Participation & Capacity Normalization (Event vs Service)

**CRITICAL:** Capacity normalization differs based on `activity_type`.

#### For `activity_type = "event"`:

Normalize `event_capacity` structure (see `GPT UI/docs/activity-data-model.md` Section 5):

- `group_capacity` (number, optional) — total seats/participants
- `seats` (number, optional) — available seats
- `min_participants` (number, optional)
- `max_participants` (number, optional)

#### For `activity_type = "service"`:

Normalize `service_participation` structure (see `GPT UI/docs/activity-data-model.md` Section 5):

- `session_mode` (enum):
  - `"one_to_one"` — individual session
  - `"family"` — family session
  - `"small_group"` — small group session
- `concurrent_clients` (number, default: 1) — usually 1, but can be more
- `practitioner_to_client_model` (string, optional) — description (no personalization)

**☑ Rule:** Normalize `event_capacity` OR `service_participation`, never both.

### 6.9 Duration & Pricing Normalization (Event vs Service)

**CRITICAL:** Duration and pricing normalization differs based on `activity_type`.

#### For `activity_type = "event"`:

Normalize `event_duration` structure (see `GPT UI/docs/activity-data-model.md` Section 6):

- `duration_type` (enum): `"per_occurrence"` | `"fixed"`
- If `duration_type = "per_occurrence"`:
  - `per_occurrence` (object):
    - `duration_minutes` (number) — duration per occurrence
- If `duration_type = "fixed"`:
  - `fixed` (string) — fixed duration description

Normalize `event_pricing` structure:

- `pricing_type` (enum): `"ticket_price"` | `"donation"` | `"free"`
- If `pricing_type = "ticket_price"`:
  - `ticket_price` (object):
    - `amount` (number)
    - `currency` (string, ISO 4217)
    - `price_range` (object, optional):
      - `min` (number)
      - `max` (number)

#### For `activity_type = "service"`:

Normalize `service_duration_options` array (see `GPT UI/docs/activity-data-model.md` Section 6):

- Array of objects:
  - `duration_minutes` (number) — e.g., 30, 60, 90, custom
  - `label` (string, optional) — e.g., "Standard", "Extended"

Normalize `service_pricing_model` structure:

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

**☑ Rule:** Normalize `event_duration`/`event_pricing` OR `service_duration_options`/`service_pricing_model`, never both.

### 6.10 Booking / CTA Normalization (Event vs Service)

**CRITICAL:** CTA normalization differs based on `activity_type`.

#### For `activity_type = "event"`:

Normalize `event_cta` structure (see `GPT UI/docs/activity-data-model.md` Section 7):

- `event_page_link` (string, URL)
- `tickets_link` (string, URL, optional)

#### For `activity_type = "service"`:

Normalize `service_cta` structure (see `GPT UI/docs/activity-data-model.md` Section 7):

- `booking_url` (string, URL, optional) — Calendly/site/form
- `contact_channel` (object, optional):
  - `type` (enum): `"social_link"` | `"email"` | `"phone"` | `"other"`
  - `value` (string)
- `amanita_booking` (boolean, default: false) — "Amanita booking (future)"

**☑ Rule:** Normalize `event_cta` OR `service_cta`, never both.

---

## 7. Conditional Field Processing

### 7.1 Conditional Field Processing Algorithm

**Purpose:** Ensures mutually exclusive fields (event_* vs service_*) are properly normalized based on `activity_type`.

**Algorithm:**

```
1. **Check activity_type:**
   - If activity_type = "event" → proceed to event normalization
   - If activity_type = "service" → proceed to service normalization
   - If activity_type missing or invalid → return "normalization_failed: activity_type_missing_or_invalid"

2. **If activity_type = "event":**
   - Normalize event_* fields (event_timing, event_capacity, event_duration, event_pricing, event_cta)
   - Check for presence of service_* fields:
     - If service_timing present → remove, log warning
     - If service_participation present → remove, log warning
     - If service_duration_options present → remove, log warning
     - If service_pricing_model present → remove, log warning
     - If service_cta present → remove, log warning
   - Verify event_* fields are properly normalized (according to Section 6.7-6.10)

3. **If activity_type = "service":**
   - Normalize service_* fields (service_timing, service_participation, service_duration_options, service_pricing_model, service_cta)
   - Check for presence of event_* fields:
     - If event_timing present → remove, log warning
     - If event_capacity present → remove, log warning
     - If event_duration present → remove, log warning
     - If event_pricing present → remove, log warning
     - If event_cta present → remove, log warning
   - Verify service_* fields are properly normalized (according to Section 6.7-6.10)

4. **If conflicts detected:**
   - Return "normalization_failed: conditional_field_conflict"
   - List conflicting fields
   - Specify which fields were removed
   - Hand control back to Validation
```

### 7.2 Mutually Exclusive Field Rules

**Rules:**

- If `activity_type = "event"`:
  - `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta` MUST be present (if applicable)
  - `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta` MUST NOT be present

- If `activity_type = "service"`:
  - `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta` MUST be present (if applicable)
  - `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta` MUST NOT be present

**If contradictions are detected:**
- fail normalization,
- return errors for correction,
- specify which conditional fields conflict.

---

## 8. Data Integrity Rules

The instruction MUST ensure:

- no contradictory fields (e.g. online + physical address without hybrid);
- no mixed units (dates vs date-times);
- no duplicate schedule entries;
- consistent internal references.
- **no mutually exclusive fields** (event_* vs service_* based on activity_type).

**Conditional Field Integrity:**

- If `activity_type = "event"`:
  - `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta` MUST be present (if applicable)
  - `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta` MUST NOT be present

- If `activity_type = "service"`:
  - `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta` MUST be present (if applicable)
  - `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta` MUST NOT be present

**Validation Checks:**

```
1. **Check delivery_mode consistency:**
   - If delivery_mode = "in_person" → location_info.city or location_info.venue must exist
   - If delivery_mode = "online" → location_info.online_platform or location_info.online_link must exist
   - If delivery_mode = "hybrid" → both in-person location and online link must exist

2. **Check timing consistency:**
   - If activity_type = "event" → event_timing must be properly structured
   - If activity_type = "service" → service_timing must be properly structured
   - No duplicate schedule entries

3. **Check enum values:**
   - All enum values must match canonical values from Activity Data Model
   - If enum value not canonical → return "normalization_failed: invalid_enum_value"

4. **Check conditional fields:**
   - Verify mutually exclusive fields (event_* vs service_*)
   - If conflicts detected → return "normalization_failed: conditional_field_conflict"
```

If contradictions are detected:
- fail normalization,
- return errors for correction,
- specify which conditional fields conflict.

---

## 9. Output Contract

This instruction produces output for **API Orchestrator**.

**Note:** This section describes the **structure** of output data.  
For the **workflow** of how Normalizer passes data to API Orchestrator, see Section 12.

**Output structure for API Orchestrator:**
```json
{
  // All 8 sections from Activity Data Model:
  
  // 1. Identity & Lifecycle
  "activity_id": "string" | null, // null для новых Activities
  "activity_type": "event" | "service",
  "status": "Draft" | "SentToReview" | "Approved" | "Published",
  "versioning": {...} | null,
  "creator_reference": "string",
  "timestamps": {
    "created_at": "ISO 8601",
    "updated_at": "ISO 8601",
    "published_at": "ISO 8601" | null
  },
  
  // 2. Core Description
  "title": "string",
  "short_summary": "string" | null,
  "full_description": "string",
  "format": "session" | "workshop" | "ceremony" | "class_regular" | "class_single" | "retreat" | "performance" | "other",
  "format_other_label": "string" | null,
  "categories": {
    "primary": {...},
    "secondary": [...],
    "freeform_user_tags": [...] | null
  },
  "age_groups": ["babies", "toddlers", ...],
  "parental_accompaniment": "allowed" | "required" | "optional" | null,
  "language_requirements": {
    "mode": "irrelevant" | "understand_only" | "speak_and_understand" | "mixed",
    "languages_to_understand": ["ru", "en"],
    "languages_to_speak": ["ru", "en"]
  },
  "media": {...} | null,
  "external_links": [...] | null,
  
  // 3. Delivery & Location
  "delivery_mode": "in_person" | "online" | "hybrid",
  "location_info": {
    "city": "string" | null,
    "area": "string" | null,
    "venue": "string" | null,
    "online_platform": "string" | null,
    "online_link": "string" | null
  },
  "service_area": {...} | null,
  
  // 4. Timing (conditional based on activity_type)
  // If event:
  "event_timing": {...} | null,
  // If service:
  "service_timing": {...} | null,
  
  // 5. Participation & Capacity (conditional based on activity_type)
  // If event:
  "event_capacity": {...} | null,
  // If service:
  "service_participation": {...} | null,
  
  // 6. Duration & Pricing (conditional based on activity_type)
  // If event:
  "event_duration": {...} | null,
  "event_pricing": {...} | null,
  // If service:
  "service_duration_options": [...] | null,
  "service_pricing_model": {...} | null,
  
  // 7. Booking / CTA (conditional based on activity_type)
  // If event:
  "event_cta": {...} | null,
  // If service:
  "service_cta": {...} | null,
  
  // 8. Source & Provenance
  "sources": {
    "canonical_url": "string" | null,
    "source_type": "manual" | "link" | "screenshot" | "pdf",
    "raw_asset_ref": "string" | null,
    "dedup_hints": {...} | null
  },
  
  // 9. Review Metadata (if applicable)
  "review_metadata": {
    "review_submission": {...} | null,
    "policy_gate_result": {...} | null // включен, если получен от Gate
  }
}
```

**Reference:** This structure MUST match Activity Data Model (`GPT UI/docs/activity-data-model.md`).

**Output Conditions:**

- **If normalization succeeds:**
  - Normalizer passes normalized JSON to API Orchestrator
  - API Orchestrator continues with backend API call
  - Normalizer includes `policy_gate_result` in `review_metadata` if received from Gate

- **If normalization fails:**
  - Normalizer does NOT pass data to API Orchestrator
  - Normalizer returns error to Validation (NOT directly to user)
  - API Orchestrator is not activated

---

## 10. Integration with Ingest Validation

### 10.1 Integration Protocol

**Activation Protocol:**

This integration applies **when Ingest Validation completes** and `validation_status = "Draft-ready"` (Gate не активируется).

**Workflow:**
```
1. Ingest Validation completes validation
2. Validation checks validation_status:
   - If "Draft-ready" → Validation передает данные в Normalizer (Gate не активируется)
   - If "SentToReview-ready" или "Approved-ready" → Validation активирует Gate (Gate передает данные в Normalizer)
   - If "Draft-not-ready" или "SentToReview-not-ready" или "Approved-not-ready" → Validation НЕ передает данные в Normalizer

3. Validation passes to Normalizer:
   - validated_data (all validated fields)
   - validation_metadata (validation_status, missing_fields, ambiguities, etc.)

4. Normalizer receives data from Validation:
   - Checks minimum requirements for normalization (Section 4.3)
   - If insufficient data → returns "normalization_failed: missing_required_fields"
   - Requests completion through Validation (NOT directly from user)

5. Validation handles normalization_failed:
   - Validation requests missing fields from user
   - After completion, Validation re-passes data to Normalizer

6. Normalizer performs normalization:
   - Executes normalization algorithm (Section 5)
   - Returns normalized JSON to API Orchestrator
```

**Note:** This section describes the **workflow** of activation.  
For the **structure** of input data, see Section 4.1 (Input from Ingest Validation).

**Important:** Normalizer НЕ может напрямую запрашивать данные у user — только через Validation.

---

## 11. Integration with KоныРода Gate

### 11.1 Integration Protocol

**Handoff Protocol:**

This integration applies **when Gate returns** `policy_gate_result.status = "approved"`.

**Workflow:**
```
1. Gate completes policy evaluation
2. Gate checks policy_gate_result.status:
   - If "approved" → Gate передает данные в Normalizer
   - If "rejected" или "needs_clarification" → Gate НЕ передает данные в Normalizer

3. Gate passes to Normalizer:
   - validated_data (unchanged from Validation)
   - validation_metadata (unchanged from Validation)
   - policy_gate_result (new structure from Gate)

4. Normalizer receives data from Gate:
   - Checks policy_gate_result.status (должен быть "approved")
   - Checks minimum requirements for normalization (Section 4.3)
   - If insufficient data → returns "normalization_failed: missing_required_fields"
   - Requests completion through Validation (NOT directly from user)

5. Normalizer performs normalization:
   - Executes normalization algorithm (Section 5)
   - Includes policy_gate_result in review_metadata
   - Structures policy_gate_result according to Activity Data Model Section 9
   - Returns normalized JSON to API Orchestrator
```

**Note:** This section describes the **workflow** of handoff.  
For the **structure** of input data, see Section 4.2 (Input from KоныРода Gate).

**Important:** Normalizer only receives data if Gate status = "approved". Rejected or clarification-required activities never reach Normalizer.

**Policy Gate Result Handling:**

Normalizer MUST include `policy_gate_result` in normalized JSON:
- Place in `review_metadata.policy_gate_result`
- Structure according to Activity Data Model Section 9
- Preserve all fields from Gate (status, reasons, policy_ref, clarification_prompt)
- Do NOT modify or reinterpret policy_gate_result

---

## 12. Integration with API Orchestrator

### 12.1 Integration Protocol

**Handoff Protocol:**

This integration applies **when Normalizer completes** normalization successfully.

**Workflow:**
```
1. Normalizer completes normalization
2. Normalizer checks normalization result:
   - If normalization succeeded → Normalizer передает данные в API Orchestrator
   - If normalization failed → Normalizer НЕ передает данные в API Orchestrator (returns error to Validation)

3. Normalizer passes to API Orchestrator:
   - Fully normalized Activity JSON object (all 8 sections from Activity Data Model)
   - review_metadata (including policy_gate_result if received from Gate)

4. API Orchestrator receives data from Normalizer:
   - Checks structure (should match Activity Data Model)
   - Determines API operation (create_draft_activity, send_activity_to_review, publish_activity, etc.)
   - Executes backend API call

5. API Orchestrator handles backend response:
   - If success → returns result to Base Instruction
   - If error → handles error according to API Orchestrator rules
```

**Note:** This section describes the **workflow** of handoff.  
For the **structure** of output data, see Section 9 (Output Contract).

**Important:** API Orchestrator is the only module that can call backend APIs. Normalizer only prepares data for API Orchestrator.

---

## 13. Edge Cases & Validation

### 13.1 Activity Type Missing or Invalid

**Scenario:** `activity_type` missing or not "event" or "service"

**Decision Logic:**
- Normalizer checks activity_type (Section 4.3)
- If missing → return "normalization_failed: activity_type_missing"
- If invalid → return "normalization_failed: invalid_activity_type"
- Hand control back to Validation

**Example:**
- Input: validated_data without activity_type
- Decision: "normalization_failed: activity_type_missing" → return to Validation

### 13.2 Conditional Field Conflicts

**Scenario:** Both event_* and service_* fields present

**Decision Logic:**
- Normalizer checks conditional fields (Section 7)
- If activity_type = "event" but service_* fields present → remove service_* fields, log warning
- If activity_type = "service" but event_* fields present → remove event_* fields, log warning
- If conflicts critical → return "normalization_failed: conditional_field_conflict"

**Example:**
- Input: activity_type = "event", but service_timing present
- Decision: Remove service_timing, normalize event_timing

### 13.3 Invalid Enum Values

**Scenario:** Enum value does not match canonical value from Activity Data Model

**Decision Logic:**
- Normalizer checks all enum values (Section 6)
- If enum value not canonical → return "normalization_failed: invalid_enum_value"
- Specify which field and value are invalid
- Hand control back to Validation

**Example:**
- Input: format = "yoga_class" (not in canonical enum)
- Decision: "normalization_failed: invalid_enum_value" → return to Validation

### 13.4 Missing Required Fields

**Scenario:** Required fields for normalization are missing

**Decision Logic:**
- Normalizer checks minimum requirements (Section 4.3)
- If required fields missing → return "normalization_failed: missing_required_fields"
- List missing fields
- Request completion through Validation (NOT directly from user)

**Example:**
- Input: activity_type = "event", but event_timing missing
- Decision: "normalization_failed: missing_required_fields" → return to Validation

### 13.5 Policy Gate Result Missing (when expected)

**Scenario:** Normalizer expects policy_gate_result but it's missing

**Decision Logic:**
- If validation_status = "SentToReview-ready" or "Approved-ready" → policy_gate_result should be present
- If policy_gate_result missing → log warning, continue normalization without it
- If policy_gate_result present but status != "approved" → should not happen (Gate only passes "approved")

**Example:**
- Input: validation_status = "SentToReview-ready", but policy_gate_result missing
- Decision: Log warning, continue normalization, review_metadata.policy_gate_result = null

### 13.6 Policy Gate Result Present (when not expected)

**Scenario:** Normalizer receives policy_gate_result but validation_status = "Draft-ready"

**Decision Logic:**
- If validation_status = "Draft-ready" → policy_gate_result should NOT be present
- If policy_gate_result present → log warning, ignore it (should not happen)
- Continue normalization without policy_gate_result

**Example:**
- Input: validation_status = "Draft-ready", but policy_gate_result present
- Decision: Log warning, ignore policy_gate_result, continue normalization

### 13.7 Invalid Structure

**Scenario:** Input structure does not match Activity Data Model

**Decision Logic:**
- Normalizer validates output structure (Section 5, step 8)
- If structure invalid → return "normalization_failed: invalid_structure"
- Specify which fields are invalid
- Hand control back to Validation

**Example:**
- Input: event_timing structure missing required fields
- Decision: "normalization_failed: invalid_structure" → return to Validation

### 13.8 Normalization Failure

**Scenario:** Normalization fails for any reason

**Decision Logic:**
- Normalizer returns error to Validation (NOT directly to user)
- Error format: "normalization_failed: <reason>"
- List affected fields
- Validation handles error and requests completion from user

**Example:**
- Input: Multiple normalization failures
- Decision: Return all errors to Validation, Validation requests completion from user

---

## 14. Example Formulations

### 14.1 Normalized Event Example

**Input from Validation (Draft-ready):**
```json
{
  "validated_data": {
    "activity_type": "event",
    "title": "Morning Yoga Practice",
    "full_description": "Join us for a morning yoga session focused on empowerment and self-discovery...",
    "format": "class_regular",
    "delivery_mode": "in_person",
    "location_info": {
      "city": "Tallinn",
      "venue": "Yoga Studio"
    },
    "event_timing": {
      "schedule_model": "recurring",
      "recurring": {
        "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
        "start_date": "2025-02-01T08:00:00+02:00",
        "timezone": "Europe/Tallinn"
      }
    },
    "event_capacity": {
      "max_participants": 20
    },
    "event_duration": {
      "duration_type": "per_occurrence",
      "per_occurrence": {
        "duration_minutes": 60
      }
    },
    "event_pricing": {
      "pricing_type": "free"
    },
    "event_cta": {
      "event_page_link": "https://example.com/yoga"
    }
  },
  "validation_metadata": {
    "validation_status": "Draft-ready"
  }
}
```

**Output for API Orchestrator:**
```json
{
  "activity_id": null,
  "activity_type": "event",
  "status": "Draft",
  "versioning": null,
  "creator_reference": "user_123",
  "timestamps": {
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z",
    "published_at": null
  },
  "title": "Morning Yoga Practice",
  "short_summary": null,
  "full_description": "Join us for a morning yoga session focused on empowerment and self-discovery...",
  "format": "class_regular",
  "format_other_label": null,
  "categories": {
    "primary": {...},
    "secondary": [...],
    "freeform_user_tags": null
  },
  "age_groups": ["adults"],
  "parental_accompaniment": null,
  "language_requirements": {
    "mode": "irrelevant",
    "languages_to_understand": [],
    "languages_to_speak": []
  },
  "media": null,
  "external_links": null,
  "delivery_mode": "in_person",
  "location_info": {
    "city": "Tallinn",
    "area": null,
    "venue": "Yoga Studio",
    "online_platform": null,
    "online_link": null
  },
  "service_area": null,
  "event_timing": {
    "schedule_model": "recurring",
    "recurring": {
      "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
      "start_date": "2025-02-01T08:00:00+02:00",
      "end_date": null,
      "timezone": "Europe/Tallinn"
    },
    "exceptions": null,
    "overrides": null
  },
  "event_capacity": {
    "group_capacity": null,
    "seats": null,
    "min_participants": null,
    "max_participants": 20
  },
  "event_duration": {
    "duration_type": "per_occurrence",
    "per_occurrence": {
      "duration_minutes": 60
    }
  },
  "event_pricing": {
    "pricing_type": "free"
  },
  "event_cta": {
    "event_page_link": "https://example.com/yoga",
    "tickets_link": null
  },
  "sources": {
    "canonical_url": null,
    "source_type": "manual",
    "raw_asset_ref": null,
    "dedup_hints": null
  },
  "review_metadata": {
    "review_submission": null,
    "policy_gate_result": null
  }
}
```

### 14.2 Normalized Service Example

**Input from Gate (SentToReview-ready):**
```json
{
  "validated_data": {
    "activity_type": "service",
    "title": "Individual Coaching Session",
    "full_description": "One-on-one coaching session focused on personal growth...",
    "format": "session",
    "delivery_mode": "hybrid",
    "location_info": {
      "city": "Tallinn",
      "online_link": "https://example.com/coaching"
    },
    "service_timing": {
      "availability_type": "by_request",
      "booking_policy": "Contact via email or booking form"
    },
    "service_participation": {
      "session_mode": "one_to_one",
      "concurrent_clients": 1
    },
    "service_duration_options": [
      {
        "duration_minutes": 60,
        "label": "Standard"
      }
    ],
    "service_pricing_model": {
      "model": "per_session",
      "package_definition": null
    },
    "service_cta": {
      "booking_url": "https://example.com/booking",
      "contact_channel": {
        "type": "email",
        "value": "coach@example.com"
      },
      "amanita_booking": false
    }
  },
  "validation_metadata": {
    "validation_status": "SentToReview-ready"
  },
  "policy_gate_result": {
    "status": "approved",
    "reasons": [
      {
        "code": "activation_aligned",
        "message": "Activity aligns with activation-oriented principles",
        "field": null,
        "principle_ref": "KоныРода.pdf - Activation principles, Section 2"
      }
    ],
    "policy_ref": "KоныРода.pdf v1.0",
    "clarification_prompt": null
  }
}
```

**Output for API Orchestrator:**
```json
{
  "activity_id": null,
  "activity_type": "service",
  "status": "SentToReview",
  "versioning": null,
  "creator_reference": "user_456",
  "timestamps": {
    "created_at": "2025-01-15T11:00:00Z",
    "updated_at": "2025-01-15T11:00:00Z",
    "published_at": null
  },
  "title": "Individual Coaching Session",
  "short_summary": null,
  "full_description": "One-on-one coaching session focused on personal growth...",
  "format": "session",
  "format_other_label": null,
  "categories": {
    "primary": {...},
    "secondary": [...],
    "freeform_user_tags": null
  },
  "age_groups": ["adults"],
  "parental_accompaniment": null,
  "language_requirements": {
    "mode": "irrelevant",
    "languages_to_understand": [],
    "languages_to_speak": []
  },
  "media": null,
  "external_links": null,
  "delivery_mode": "hybrid",
  "location_info": {
    "city": "Tallinn",
    "area": null,
    "venue": null,
    "online_platform": null,
    "online_link": "https://example.com/coaching"
  },
  "service_area": null,
  "service_timing": {
    "availability_type": "by_request",
    "availability_windows": null,
    "booking_policy": "Contact via email or booking form"
  },
  "service_participation": {
    "session_mode": "one_to_one",
    "concurrent_clients": 1,
    "practitioner_to_client_model": null
  },
  "service_duration_options": [
    {
      "duration_minutes": 60,
      "label": "Standard"
    }
  ],
  "service_pricing_model": {
    "model": "per_session",
    "package_definition": null
  },
  "service_cta": {
    "booking_url": "https://example.com/booking",
    "contact_channel": {
      "type": "email",
      "value": "coach@example.com"
    },
    "amanita_booking": false
  },
  "sources": {
    "canonical_url": null,
    "source_type": "manual",
    "raw_asset_ref": null,
    "dedup_hints": null
  },
  "review_metadata": {
    "review_submission": null,
    "policy_gate_result": {
      "status": "approved",
      "reasons": [
        {
          "code": "activation_aligned",
          "message": "Activity aligns with activation-oriented principles",
          "field": null,
          "principle_ref": "KоныРода.pdf - Activation principles, Section 2"
        }
      ],
      "policy_ref": "KоныРода.pdf v1.0",
      "clarification_prompt": null
    }
  }
}
```

### 14.3 Normalization Failure Example

**Input from Validation:**
```json
{
  "validated_data": {
    "activity_type": "event",
    "title": "Yoga Workshop",
    "event_timing": {...},
    "service_timing": {...} // CONFLICT: both event_* and service_* fields present
  },
  "validation_metadata": {
    "validation_status": "Draft-ready"
  }
}
```

**Normalization Result:**
```json
{
  "normalization_failed": true,
  "error_code": "conditional_field_conflict",
  "message": "Both event_* and service_* fields present. activity_type = 'event', but service_timing is present.",
  "conflicting_fields": ["service_timing"],
  "action": "return_to_validation"
}
```

**Response to Validation:**
- Normalizer returns error to Validation
- Validation requests clarification from user
- After clarification, Validation re-passes data to Normalizer

---

## 15. Validation Checklist

### 15.1 Pre-Implementation Checklist

- [ ] Activity Data Model studied and canonical schema understood
- [ ] Integration with Ingest Validation understood (Section 10)
- [ ] Integration with KоныРода Gate understood (Section 11)
- [ ] Integration with API Orchestrator understood (Section 12)
- [ ] Conditional field processing understood (Section 7)
- [ ] Normalization Algorithm understood (Section 5)
- [ ] Field Normalization Rules understood (Section 6)
- [ ] Data Integrity Rules understood (Section 8)

### 15.2 Post-Implementation Testing Checklist

- [ ] Normalization works correctly for event (all conditional fields)
- [ ] Normalization works correctly for service (all conditional fields)
- [ ] Conditional field conflicts handled correctly (event_* vs service_*)
- [ ] Enum values normalized correctly (all canonical values)
- [ ] Integration with Validation works correctly (Draft-ready workflow)
- [ ] Integration with Gate works correctly (SentToReview-ready/Approved-ready workflow)
- [ ] Policy gate result included correctly in review_metadata
- [ ] Edge cases handled correctly (Section 13)
- [ ] Examples match Activity Data Model structure
- [ ] Output structure matches Activity Data Model

### 15.3 Quality Criteria

- [ ] All enum values match canonical values from Activity Data Model
- [ ] All conditional fields normalized correctly (event_* vs service_*)
- [ ] All normalization algorithms are deterministic (same behavior in same situations)
- [ ] Output structure matches Activity Data Model exactly
- [ ] No invented data (all data from input)
- [ ] No semantic interpretation (structural transformation only)
- [ ] Policy gate result preserved correctly (if received from Gate)

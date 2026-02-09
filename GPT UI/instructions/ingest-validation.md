# Ingest Validation Instruction
## Input Validation & Missing-Data Resolution

### Purpose

Ingest Validation Instruction is responsible for **validating all incoming input intended to create or modify Activities**.

Its role is to:
- receive structured data from Ingest Deep Parsing (for non-dialogue input),
- extract and validate fields from dialogue (for step-by-step input),
- validate structural completeness for the current step,
- identify missing required data,
- resolve ambiguities and missing fields,
- prepare validated data for normalization.

This instruction **never performs raw extraction** (Ingest Deep Parsing does this for non-dialogue input),  
**never publishes data**, **never calls backend APIs**,  
and **never makes policy or approval decisions**.

---

## 1. Scope of Responsibility

This instruction is activated **only in INGEST mode**.

It handles:
- new Activity creation (one Activity per input),
- updates to existing Activities,
- validation of structured data from Ingest Deep Parsing,
- validation of dialogue input (when user provides data step-by-step).

It does NOT:
- perform raw extraction (Ingest Deep Parsing does this),
- decide whether an Activity is allowed (KоныРода Gate does this),
- normalize data into canonical JSON (Activity Normalizer does this),
- interact with backend systems (API Orchestrator does this),
- process multiple Activities in one input (rejected by Base Instruction).

### 1.1 Review-First Default (Strict Protocol Mode)

**Default target readiness for intent "add":**
- Target readiness: `SentToReview-ready` (Review-first)
- All SentToReview-required fields must be collected upfront
- Format, delivery_mode, location_info, event_timing/service_timing must be requested in first validation round

**Draft-only exception:**
- Only if user explicitly requests: "черновик", "минимум", "draft only"
- Target readiness: `Draft-ready`
- Only Draft-required fields collected

**Implementation:**
```
1. Detect user intent:
   - IF intent == "add" AND no explicit "черновик"/"минимум" → target = SentToReview-ready, protocol = strict
   - IF intent == "add" AND explicit "черновик"/"минимум" → target = Draft-ready, protocol = relaxed

2. First validation round:
   - Collect ALL missing required fields for target readiness level
   - Present as structured batch list (not one-by-one)
   - Include enum options where applicable
   - Reference: Base Instruction Section 1.5 (Batch Field Requests)

3. Block progression:
   - IF missing_required_fields[] is NOT empty → BLOCK
   - Do NOT proceed to Normalizer/Gate/API
   - Do NOT say "ready for review" until all required fields present
   - Create ingest_validation_report with stop_the_line.blocked = true
```

**Reference:** Base Instruction Section 1.5 (Strict Protocol Mode, Review-First Default)

### 1.2 Batch Field Requests (Not One-by-One)

**In first validation round:**
- Return ALL missing required fields for selected readiness level
- Do NOT ask one field at a time
- Present as structured list with enum options where applicable

**Example format (correct):**
```
Для отправки на ревью нужно заполнить:

1. format — выбери одно значение:
   - performance
   - session
   - workshop
   - ceremony
   - class_single / class_regular
   - retreat
   - other (тогда нужно ещё format_other_label)

2. delivery_mode — выбери:
   - in_person
   - online
   - hybrid

3. location_info — требуется если delivery_mode != "online"
   - city
   - venue (для in_person)
   - online_platform (для online/hybrid)

4. event_timing — требуется для event:
   - schedule_model (fixed_dates | recurring)
   - dates/times

Напиши все значения одним сообщением.
```

**Prohibited format (incorrect):**
```
Какой format? (waiting for response)
Какой delivery_mode? (waiting for response)
...
```

**Implementation:**
```
1. Collect ALL missing required fields for target readiness level
2. Group by category (format, delivery, location, timing)
3. Present as structured list with enum options
4. Request all values in one message
5. Wait for user response
6. Validate all provided values
7. IF any missing or invalid → request corrections (batch mode again)
```

**Reference:** Base Instruction Section 1.5 (Batch Field Requests)

### 1.3 Non-Dialogue Input: Mandatory Deep Parsing Pre-Step

**For non-dialogue input (image/pdf/link):**
- Deep Parsing MUST be activated BEFORE asking clarifying questions
- GPT MUST NOT ask questions until `deep_parsing_artifact` is produced
- Questions MUST reference `ambiguities[]` and `missing_required_fields[]` from artifact

**Workflow:**
```
1. User provides: image/pdf/link
2. Activate Deep Parsing → produce deep_parsing_artifact
3. Analyze artifact:
   - IF ambiguities[] present → ask about ambiguities (batch mode)
   - IF missing_required_fields[] present → ask about missing fields (batch mode)
   - Reference artifact fields explicitly
4. Proceed to Validation only after Deep Parsing artifact is complete
```

**Stop-the-line rule:**
- IF `deep_parsing_artifact` is missing for non-dialogue input → BLOCK
- Do NOT proceed to Validation without Deep Parsing artifact
- Do NOT ask questions before artifact is received

**Deep Parsing: Early Format Extraction:**
- Deep Parsing MUST attempt to extract format and other enums early
- If confidence < 0.5 → set `format: null` + add to `ambiguities[]` with suggested enum values
- Ingest Validation MUST convert ambiguity to user question (batch mode)
- Do NOT wait until validation stage to discover format is missing

**Reference:** Base Instruction Section 1.5 (Non-Dialogue Input: Mandatory Deep Parsing Pre-Step, Deep Parsing: Early Format Extraction)

**One Activity per Input Rule:**
- Base Instruction enforces "one Activity per input" before routing to this instruction
- If Ingest Deep Parsing detects multiple Activities (fallback detection):
  → Reject input
  → Inform user: "I detected multiple Activities. Please submit one Activity at a time."
  → Do NOT proceed with any Activity

**Activity Data Model Reference:**

This instruction MUST validate fields according to the **Activity Data Model** defined in:
- `GPT UI/docs/activity-data-model.md`

The model defines:
- Complete field structure for all Activity types
- Conditional fields based on `activity_type` (event vs service)
- Field completeness requirements by status (Draft → Review → Approved)
- Enum values for all controlled vocabularies

**Critical:** Validation MUST check conditional fields based on `activity_type`:
- If `activity_type = "event"` → validate `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`
- If `activity_type = "service"` → validate `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`

---

## 2. Input Contract

This instruction receives input from two sources:

### 2.1 Input from Ingest Deep Parsing (Non-Dialogue Input)

**Note:** This section describes the **structure** of input data.  
For the **workflow** of how Deep Parsing is activated, see Section 11.1.

**Input structure from Deep Parsing:**
```json
{
  "extracted_data": {
    "activity_type": "event" | "service" | null,
    "title": string | null,
    "full_description": string | null,
    // ... all other fields from Activity Data Model
  },
  "metadata": {
    "source_type": "text" | "screenshot" | "pdf" | "link" | "mixed",
    "sources": [...],
    "confidence_scores": {
      "activity_type": 0.0-1.0,
      "title": 0.0-1.0,
      // ... confidence for each field
    },
    "ambiguities": [
      {
        "field": "event_timing.date",
        "type": "date",
        "values": [...]
      }
    ],
    "missing_required_fields": ["title", "event_timing"],
    "conflicts": [
      {
        "field": "title",
        "sources": [...],
        "resolved_value": "..."
      }
    ]
  }
}
```

---

## 3. Information Extraction Rules

**Note:** This instruction receives structured input from **Ingest Deep Parsing Instruction** (for non-dialogue input) or extracts from dialogue (for step-by-step input).

It does NOT perform raw extraction. Instead, it:
- validates extracted fields from parsing,
- checks completeness according to Activity Data Model,
- identifies missing required fields.

**Activity Data Model Reference:** See `GPT UI/docs/activity-data-model.md` for complete field definitions.

### 3.1 Common Fields (for both event and service)

These fields are validated the same way regardless of `activity_type`:

**Required for Draft:**
- `activity_type` (enum: `"event"` | `"service"`) — **MUST be determined and validated first**
- `title` (string) — required, minimum 1 character
- At least one of:
  - `short_summary` (string), or
  - `full_description` (string)

**Required for SentToReview:**
- All Draft requirements +
- `full_description` (string) — required, minimum 50 characters
- `format` (enum) — required, must be valid enum value or "other" (with format_other_label)
- `delivery_mode` (enum) — required, must be "in_person" | "online" | "hybrid"
- `location_info` (object) — required if `delivery_mode != "online"`

**Optional (but validated if present):**
- `short_summary` (string, optional)
- `categories` (object) — two-level taxonomy
- `age_groups` (array of enum, optional)
- `parental_accompaniment` (enum, optional)
- `language_requirements` (object, optional)
- `media` (object, optional)
- `sources` (object)

**Validation algorithm for common fields:**
```
1. Check activity_type:
   - If missing → REJECT, request clarification
   - If not "event" or "service" → REJECT, request clarification
   - If ambiguous (from Deep Parsing) → request clarification

2. Check title:
   - If missing → REJECT, request title
   - If empty string → REJECT, request title
   - If present → ACCEPT

3. Check description:
   - For Draft: if both short_summary and full_description missing → REJECT, request description
   - For SentToReview: if full_description missing or < 50 chars → REJECT, request full description

4. Check format (for SentToReview):
   - If missing → REJECT, request format
   - If "other" → check format_other_label is present
   - If invalid enum value → REJECT, request valid format

5. Check delivery_mode (for SentToReview):
   - If missing → REJECT, request delivery mode
   - If invalid enum value → REJECT, request valid delivery mode

6. Check location_info (for SentToReview):
   - If delivery_mode != "online" AND location_info missing → REJECT, request location
   - If delivery_mode == "online" → location_info optional
```

### 3.2 Conditional Fields (depend on activity_type)

**☑ Rule:** Conditional fields are mutually exclusive. If `activity_type = "event"`, `service_timing` and other service fields MUST NOT be present (and vice versa).

**If `activity_type = "event"`:**
- `event_timing` (object) — required for Draft and SentToReview
- `event_capacity` (object, optional)
- `event_duration` (object, optional)
- `event_pricing` (object, optional)
- `event_cta` (object, optional)

**If `activity_type = "service"`:**
- `service_timing` (object) — required for Draft and SentToReview
- `service_participation` (object, optional)
- `service_duration_options` (array, optional)
- `service_pricing_model` (object, optional)
- `service_cta` (object, optional)

**Mutually Exclusive Fields Check:**
```
1. If activity_type = "event":
   - Check that NO service_* fields are present:
     - service_timing → REJECT, error: "Event Activities cannot have service_timing. Use event_timing instead."
     - service_participation → REJECT, error: "Event Activities cannot have service_participation. Use event_capacity instead."
     - service_duration_options → REJECT, error: "Event Activities cannot have service_duration_options. Use event_duration instead."
     - service_pricing_model → REJECT, error: "Event Activities cannot have service_pricing_model. Use event_pricing instead."
     - service_cta → REJECT, error: "Event Activities cannot have service_cta. Use event_cta instead."

2. If activity_type = "service":
   - Check that NO event_* fields are present:
     - event_timing → REJECT, error: "Service Activities cannot have event_timing. Use service_timing instead."
     - event_capacity → REJECT, error: "Service Activities cannot have event_capacity. Use service_participation instead."
     - event_duration → REJECT, error: "Service Activities cannot have event_duration. Use service_duration_options instead."
     - event_pricing → REJECT, error: "Service Activities cannot have event_pricing. Use service_pricing_model instead."
     - event_cta → REJECT, error: "Service Activities cannot have event_cta. Use service_cta instead."
```

---

## 4. Validation Levels

Validation MUST be context-aware and **stage-dependent**.

Validation rules are defined in `GPT UI/docs/activity-data-model.md` Section 11.

### 4.1 Draft-Level Validation

**Minimum requirements for Draft status** (see Activity Data Model Section 11):

**Common fields (required for all types):**
- `activity_type` (enum: `"event"` | `"service"`) — **MUST be determined and validated first**
- `title` (string) — required, minimum 1 character
- At least one of:
  - `short_summary` (string), or
  - `full_description` (string)

**Conditional fields (based on activity_type):**
- If `activity_type = "event"`:
  - `event_timing` (object) — required (at least schedule_model must be present)
- If `activity_type = "service"`:
  - `service_timing` (object) — required (at least availability_type must be present)

**Detailed validation algorithm:**
```
1. **Check activity_type:**
   - If missing → REJECT
     - Error: "Activity type is required. Is this an event (scheduled occurrence) or a service (available by appointment)?"
     - Request clarification
   - If not "event" or "service" → REJECT
     - Error: "Activity type must be 'event' or 'service'. Please specify."
     - Request clarification
   - If ambiguous (from Deep Parsing, confidence < 0.5) → REJECT
     - Error: "I couldn't determine if this is an event or service. Please clarify: Is this a scheduled event with fixed dates, or a service available by appointment?"
     - Request clarification
   - If present and valid → CONTINUE

2. **Check common required fields:**
   - If title missing → REJECT
     - Error: "Title is required for Draft status. Please provide a title for this Activity."
     - Request title
   - If title empty string → REJECT
     - Error: "Title cannot be empty. Please provide a title for this Activity."
     - Request title
   - If both short_summary and full_description missing → REJECT
     - Error: "Description is required for Draft status. Please provide either a short summary or a full description."
     - Request description
   - If at least one description present → CONTINUE

3. **Check conditional fields based on activity_type:**
   - If activity_type = "event":
     - If event_timing missing → REJECT
       - Error: "Event timing is required for Draft status. Please provide event dates and times."
       - Request timing
     - If event_timing present but schedule_model missing → REJECT
       - Error: "Event timing must include schedule_model (fixed_dates or recurring). Please provide complete timing information."
       - Request complete timing
     - If service_timing present → REJECT (mutually exclusive)
       - Error: "Event Activities cannot have service_timing. Please remove service_timing and provide event_timing instead."
       - Request correction
   - If activity_type = "service":
     - If service_timing missing → REJECT
       - Error: "Service timing is required for Draft status. Please provide availability information (by_request, fixed_windows, or bookable_slots)."
       - Request timing
     - If service_timing present but availability_type missing → REJECT
       - Error: "Service timing must include availability_type. Please provide complete availability information."
       - Request complete timing
     - If event_timing present → REJECT (mutually exclusive)
       - Error: "Service Activities cannot have event_timing. Please remove event_timing and provide service_timing instead."
       - Request correction

4. **Check for mutually exclusive fields:**
   - If activity_type = "event" AND any service_* fields present → REJECT
     - List all conflicting fields
     - Error: "Event Activities cannot have service-specific fields. Please remove: [list of service_* fields]"
   - If activity_type = "service" AND any event_* fields present → REJECT
     - List all conflicting fields
     - Error: "Service Activities cannot have event-specific fields. Please remove: [list of event_* fields]"

5. **If all Draft requirements met:**
   - Set validation_status = "Draft-ready"
   - ACCEPT for Draft status
   - Proceed to next validation level (if requested)
```

**If minimum Draft data is not present:**
- GPT MUST list missing fields,
- request them from the user,
- and block progression until provided.

### 4.2 Review-Level Validation (Pre-Review Check)

**Requirements for SentToReview status** (see Activity Data Model Section 11):

**Common fields (required for all types):**
- All Draft requirements +
- `full_description` (string) — required, minimum 50 characters
- `format` (enum) — required
- `delivery_mode` (enum) — required
- `location_info` (object) — required if `delivery_mode != "online"`

**Conditional fields (based on activity_type):**
- If `activity_type = "event"`:
  - `event_timing` (object) — required, complete timing information
  - `event_capacity` (object) — recommended
- If `activity_type = "service"`:
  - `service_timing` (object) — required, complete availability information
  - `service_participation` (object) — recommended

**Detailed validation algorithm:**
```
1. **Verify all Draft requirements are met:**
   - Run Draft validation algorithm
   - If Draft validation fails → REJECT
     - Error: "Draft requirements must be met before submitting for review."
     - Return to Draft validation
     - List missing Draft fields
   - If Draft validation passes → CONTINUE

2. **Check common SentToReview fields:**
   - If full_description missing → REJECT
     - Error: "Full description is required for review submission. Please provide a detailed description (minimum 50 characters)."
     - Request full description
   - If full_description present but < 50 chars → REJECT
     - Error: "Full description must be at least 50 characters. Current length: [X] characters. Please provide more details."
     - Request expanded description
   - If format missing → REJECT
     - Error: "Format is required for review submission. Please specify the format (session, workshop, ceremony, class_regular, class_single, retreat, performance, or other)."
     - Request format
   - If format = "other" AND format_other_label missing → REJECT
     - Error: "If format is 'other', please provide a label describing the format."
     - Request format_other_label
   - If delivery_mode missing → REJECT
     - Error: "Delivery mode is required for review submission. Please specify: in_person, online, or hybrid."
     - Request delivery mode
   - If delivery_mode != "online" AND location_info missing → REJECT
     - Error: "Location information is required for in-person or hybrid activities. Please provide location details."
     - Request location_info
   - If delivery_mode == "online" → location_info optional

3. **Check conditional fields based on activity_type:**
   - If activity_type = "event":
     - If event_timing missing → REJECT
       - Error: "Event timing is required for review submission. Please provide complete timing information."
       - Request complete timing
     - If event_timing present but incomplete:
       - If schedule_model missing → REJECT
         - Error: "Event timing must include schedule_model (fixed_dates or recurring)."
         - Request schedule_model
       - If schedule_model = "fixed_dates" AND fixed_dates array empty → REJECT
         - Error: "Fixed dates array cannot be empty. Please provide at least one date."
         - Request fixed_dates
       - If schedule_model = "recurring" AND recurrence_rule missing → REJECT
         - Error: "Recurring events must include recurrence_rule (RRULE format)."
         - Request recurrence_rule
     - If event_capacity missing → WARN (recommended, not required)
       - Note: "Event capacity is recommended for review submission."
   - If activity_type = "service":
     - If service_timing missing → REJECT
       - Error: "Service timing is required for review submission. Please provide complete availability information."
       - Request complete timing
     - If service_timing present but incomplete:
       - If availability_type missing → REJECT
         - Error: "Service timing must include availability_type (by_request, fixed_windows, or bookable_slots)."
         - Request availability_type
       - If availability_type = "fixed_windows" AND availability_windows array empty → REJECT
         - Error: "Fixed windows array cannot be empty. Please provide at least one availability window."
         - Request availability_windows
     - If service_participation missing → WARN (recommended, not required)
       - Note: "Service participation information is recommended for review submission."

4. **Check for mutually exclusive fields:**
   - If activity_type = "event" AND any service_* fields present → REJECT
     - List all conflicting fields
     - Error: "Event Activities cannot have service-specific fields. Please remove: [list of service_* fields]"
   - If activity_type = "service" AND any event_* fields present → REJECT
     - List all conflicting fields
     - Error: "Service Activities cannot have event-specific fields. Please remove: [list of event_* fields]"

5. **If all SentToReview requirements met:**
   - Set validation_status = "SentToReview-ready"
   - ACCEPT for review submission
   - Proceed to KоныРода Gate (not in scope of this instruction)
```

**If any required field is missing:**

**Artifact Creation:**

After completing Review-Level Validation, Ingest Validation MUST create `ingest_validation_report`:

```json
{
  "artifact_id": "validation_<ISO_timestamp>",
  "version": "v1",
  "timestamp": "ISO 8601",
  "protocol_mode": "strict" | "relaxed",
  "target_readiness": "SentToReview-ready" | "Draft-ready",
  "readiness_level": "SentToReview-ready" | "Draft-ready" | "not_ready",
  "activity_type": "event" | "service" | null,
  "required_fields_status": {
    "senttoreview": {
      "required": [...],
      "present": [...],
      "missing": [...],
      "status": "complete" | "incomplete"
    }
  },
  "missing_required_fields": [
    {
      "field": "format",
      "readiness_level": "SentToReview-ready",
      "field_type": "enum",
      "enum_options": [...],
      "conditional": false
    }
  ],
  "invalid_fields": [...],
  "mutual_exclusion_checks": [...],
  "validation_metadata": {
    "deep_parsing_artifact_ref": "deep_parsing_<timestamp>" | null,
    "validation_round": 1
  },
  "stop_the_line": {
    "blocked": true | false,
    "blocked_reasons": ["missing_required_fields"] | [],
    "can_proceed": false | true
  }
}
```

**Stop-the-line check:**
```
IF ingest_validation_report.stop_the_line.blocked == true:
    → DO NOT proceed to Normalizer/Gate/API
    → Request missing fields from user (batch mode)
    → Re-validate after user response
    → Create new ingest_validation_report
    → Repeat until stop_the_line.blocked == false
```

**Reference:** Base Instruction Section 1.5 (Rule 2: Stop-the-Line Conditions)
- the instruction MUST list missing fields,
- request them from the user,
- and block progression until provided.

### 4.3 Approved-Level Validation (Publication Readiness)

**Requirements for Approved status** (see Activity Data Model Section 11):

**Common fields (required for all types):**
- All SentToReview requirements +
- All optional fields that affect discovery/search
- Complete `media`/external links (if applicable)

**Conditional fields (based on activity_type):**
- If `activity_type = "event"`:
  - `event_cta` (object) — recommended for publication
- If `activity_type = "service"`:
  - `service_cta` (object) — recommended for publication

**Detailed validation algorithm:**
```
1. **Verify all SentToReview requirements are met:**
   - Run SentToReview validation algorithm
   - If SentToReview validation fails → REJECT
     - Error: "Review requirements must be met before publication."
     - Return to SentToReview validation
     - List missing SentToReview fields
   - If SentToReview validation passes → CONTINUE

2. **Check optional fields for discovery/search:**
   - If categories missing → WARN (recommended)
     - Note: "Categories help users discover your Activity. Consider adding categories."
   - If age_groups missing → WARN (recommended)
     - Note: "Age groups help users find age-appropriate Activities. Consider adding age groups."
   - If language_requirements missing → WARN (recommended if multilingual)
     - Note: "Language requirements help users find Activities in their language. Consider adding language requirements."

3. **Check media/external links:**
   - If media missing → WARN (recommended)
     - Note: "Media and external links help users learn more about your Activity. Consider adding links."
   - If media present but incomplete:
     - Validate URL formats
     - Check for broken links (if possible)

4. **Check conditional fields based on activity_type:**
   - If activity_type = "event":
     - If event_cta missing → WARN (recommended)
       - Note: "Event CTA (event page link, tickets link) is recommended for publication."
     - If event_cta present:
       - Validate event_page_link is valid URL
       - Validate tickets_link is valid URL (if present)
   - If activity_type = "service":
     - If service_cta missing → WARN (recommended)
       - Note: "Service CTA (booking URL, contact channel) is recommended for publication."
     - If service_cta present:
       - Validate booking_url is valid URL (if present)
       - Validate contact_channel structure (if present)

5. **If all Approved requirements met:**
   - Set validation_status = "Approved-ready"
   - ACCEPT for publication
   - Note: "Approved status is typically set by policy gate (КоныРода), but validation ensures data completeness for publication."
```

**Note:** Approved status is typically set by policy gate (КоныРода), but validation ensures data completeness for publication.

---

## 5. Conditional Fields Validation

This section provides detailed validation algorithms for conditional fields based on `activity_type`.

### 5.1 Event Fields Validation

**If `activity_type = "event"`, validate the following fields:**

#### 5.1.1 event_timing Validation

**Required for:** Draft, SentToReview

**Structure:**
```json
{
  "schedule_model": "fixed_dates" | "recurring",
  "fixed_dates": [...], // if schedule_model = "fixed_dates"
  "recurring": {...}, // if schedule_model = "recurring"
  "exceptions": [...], // optional
  "overrides": [...], // optional
  "next_occurrence": "ISO 8601" // computed
}
```

**Validation algorithm:**
```
1. Check schedule_model:
   - If missing → REJECT
     - Error: "Event timing must include schedule_model (fixed_dates or recurring)."
   - If not "fixed_dates" or "recurring" → REJECT
     - Error: "Schedule model must be 'fixed_dates' or 'recurring'."
   - If present and valid → CONTINUE

2. If schedule_model = "fixed_dates":
   - Check fixed_dates array:
     - If missing or empty → REJECT
       - Error: "Fixed dates array cannot be empty. Please provide at least one date."
     - If present:
       - Validate each date object:
         - start (ISO 8601) → required
         - end (ISO 8601) → required
         - timezone (IANA) → required
       - If any date invalid → REJECT
         - Error: "Invalid date format. Dates must be in ISO 8601 format with IANA timezone."

3. If schedule_model = "recurring":
   - Check recurring object:
     - recurrence_rule (RRULE) → required
     - start_date (ISO 8601) → required
     - end_date (ISO 8601) → optional
     - timezone (IANA) → required
   - If any field missing → REJECT
     - Error: "Recurring events must include recurrence_rule, start_date, and timezone."

4. Check exceptions (optional):
   - If present, validate each exception:
     - date (ISO 8601) → required
     - reason (string) → optional

5. Check overrides (optional):
   - If present, validate each override:
     - date (ISO 8601) → required
     - start (ISO 8601) → required
     - end (ISO 8601) → required
```

#### 5.1.2 event_capacity Validation

**Required for:** Optional (recommended for SentToReview)

**Structure:**
```json
{
  "group_capacity": number, // optional
  "seats": number, // optional
  "min_participants": number, // optional
  "max_participants": number // optional
}
```

**Validation algorithm:**
```
1. If present:
   - Validate all numeric fields are positive integers
   - If max_participants present AND min_participants present:
     - Check max_participants >= min_participants
     - If not → REJECT
       - Error: "max_participants must be >= min_participants."
   - If seats present AND group_capacity present:
     - Check seats <= group_capacity
     - If not → WARN
       - Note: "Available seats should not exceed group capacity."
```

#### 5.1.3 event_duration Validation

**Required for:** Optional

**Structure:**
```json
{
  "duration_type": "per_occurrence" | "fixed",
  "per_occurrence": {
    "duration_minutes": number
  }, // if duration_type = "per_occurrence"
  "fixed": "string" // if duration_type = "fixed"
}
```

**Validation algorithm:**
```
1. If present:
   - Check duration_type:
     - If missing → REJECT
       - Error: "Event duration must include duration_type (per_occurrence or fixed)."
     - If not "per_occurrence" or "fixed" → REJECT
       - Error: "Duration type must be 'per_occurrence' or 'fixed'."

2. If duration_type = "per_occurrence":
   - Check per_occurrence object:
     - duration_minutes (number) → required, must be positive integer
     - If missing or invalid → REJECT
       - Error: "Per occurrence duration must include duration_minutes (positive integer)."

3. If duration_type = "fixed":
   - Check fixed string:
     - Must be non-empty string
     - If missing or empty → REJECT
       - Error: "Fixed duration must be a non-empty string."
```

#### 5.1.4 event_pricing Validation

**Required for:** Optional

**Structure:**
```json
{
  "pricing_type": "ticket_price" | "donation" | "free",
  "ticket_price": {
    "amount": number,
    "currency": "ISO 4217",
    "price_range": {
      "min": number,
      "max": number
    } // optional
  }, // if pricing_type = "ticket_price"
  "price_range": {...} // if pricing_type = "ticket_price"
}
```

**Validation algorithm:**
```
1. If present:
   - Check pricing_type:
     - If missing → REJECT
       - Error: "Event pricing must include pricing_type (ticket_price, donation, or free)."
     - If not "ticket_price", "donation", or "free" → REJECT
       - Error: "Pricing type must be 'ticket_price', 'donation', or 'free'."

2. If pricing_type = "ticket_price":
   - Check ticket_price object:
     - amount (number) → required, must be positive
     - currency (ISO 4217) → required, must be valid currency code
     - If missing or invalid → REJECT
       - Error: "Ticket price must include amount (positive number) and currency (ISO 4217 code)."
   - Check price_range (optional):
     - If present:
       - min (number) → required, must be positive
       - max (number) → required, must be positive
       - Check max >= min
       - If not → REJECT
         - Error: "Price range max must be >= min."
```

#### 5.1.5 event_cta Validation

**Required for:** Optional (recommended for Approved)

**Structure:**
```json
{
  "event_page_link": "URL",
  "tickets_link": "URL" // optional
}
```

**Validation algorithm:**
```
1. If present:
   - Check event_page_link:
     - If missing → REJECT
       - Error: "Event CTA must include event_page_link."
     - If not valid URL → REJECT
       - Error: "Event page link must be a valid URL."
   - Check tickets_link (optional):
     - If present, must be valid URL
     - If invalid → REJECT
       - Error: "Tickets link must be a valid URL."
```

### 5.2 Service Fields Validation

**If `activity_type = "service"`, validate the following fields:**

#### 5.2.1 service_timing Validation

**Required for:** Draft, SentToReview

**Structure:**
```json
{
  "availability_type": "by_request" | "fixed_windows" | "bookable_slots",
  "availability_windows": [
    {
      "day_of_week": "monday" | "tuesday" | ...,
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "timezone": "IANA"
    }
  ], // if availability_type = "fixed_windows"
  "booking_policy": "string"
}
```

**Validation algorithm:**
```
1. Check availability_type:
   - If missing → REJECT
     - Error: "Service timing must include availability_type (by_request, fixed_windows, or bookable_slots)."
   - If not "by_request", "fixed_windows", or "bookable_slots" → REJECT
     - Error: "Availability type must be 'by_request', 'fixed_windows', or 'bookable_slots'."

2. If availability_type = "fixed_windows":
   - Check availability_windows array:
     - If missing or empty → REJECT
       - Error: "Fixed windows array cannot be empty. Please provide at least one availability window."
     - If present:
       - Validate each window:
         - day_of_week (enum) → required
         - start_time (HH:MM) → required
         - end_time (HH:MM) → required
         - timezone (IANA) → required
       - If any window invalid → REJECT
         - Error: "Invalid availability window format. Windows must include day_of_week, start_time, end_time, and timezone."

3. Check booking_policy:
   - If missing → WARN (recommended)
     - Note: "Booking policy helps users understand how to book this service. Consider adding booking policy."
   - If present, must be non-empty string
```

#### 5.2.2 service_participation Validation

**Required for:** Optional (recommended for SentToReview)

**Structure:**
```json
{
  "session_mode": "one_to_one" | "family" | "small_group",
  "concurrent_clients": number, // default: 1
  "practitioner_to_client_model": "string" // optional
}
```

**Validation algorithm:**
```
1. If present:
   - Check session_mode:
     - If missing → REJECT
       - Error: "Service participation must include session_mode (one_to_one, family, or small_group)."
     - If not "one_to_one", "family", or "small_group" → REJECT
       - Error: "Session mode must be 'one_to_one', 'family', or 'small_group'."
   - Check concurrent_clients:
     - If missing → use default: 1
     - If present, must be positive integer
     - If invalid → REJECT
       - Error: "Concurrent clients must be a positive integer."
   - Check practitioner_to_client_model (optional):
     - If present, must be non-empty string
```

#### 5.2.3 service_duration_options Validation

**Required for:** Optional

**Structure:**
```json
[
  {
    "duration_minutes": number,
    "label": "string" // optional
  }
]
```

**Validation algorithm:**
```
1. If present:
   - Check array is not empty
   - Validate each option:
     - duration_minutes (number) → required, must be positive integer
     - label (string) → optional
     - If any option invalid → REJECT
       - Error: "Service duration options must include duration_minutes (positive integer) for each option."
```

#### 5.2.4 service_pricing_model Validation

**Required for:** Optional

**Structure:**
```json
{
  "model": "per_session" | "per_hour" | "per_package" | "donation" | "free",
  "package_definition": {
    "sessions_count": number,
    "total_price": number,
    "currency": "ISO 4217"
  } // if model = "per_package"
}
```

**Validation algorithm:**
```
1. If present:
   - Check model:
     - If missing → REJECT
       - Error: "Service pricing model must include model (per_session, per_hour, per_package, donation, or free)."
     - If not valid enum value → REJECT
       - Error: "Pricing model must be 'per_session', 'per_hour', 'per_package', 'donation', or 'free'."

2. If model = "per_package":
   - Check package_definition:
     - sessions_count (number) → required, must be positive integer
     - total_price (number) → required, must be positive
     - currency (ISO 4217) → required, must be valid currency code
     - If missing or invalid → REJECT
       - Error: "Package definition must include sessions_count (positive integer), total_price (positive number), and currency (ISO 4217 code)."
```

#### 5.2.5 service_cta Validation

**Required for:** Optional (recommended for Approved)

**Structure:**
```json
{
  "booking_url": "URL", // optional
  "contact_channel": {
    "type": "social_link" | "email" | "phone" | "other",
    "value": "string"
  }, // optional
  "amanita_booking": boolean // default: false
}
```

**Validation algorithm:**
```
1. If present:
   - Check booking_url (optional):
     - If present, must be valid URL
     - If invalid → REJECT
       - Error: "Booking URL must be a valid URL."
   - Check contact_channel (optional):
     - If present:
       - type (enum) → required
       - value (string) → required, must be non-empty
       - If missing or invalid → REJECT
         - Error: "Contact channel must include type and value."
   - Check amanita_booking:
     - If missing → use default: false
     - If present, must be boolean
```

---

## 6. Enum Validation

This section provides detailed validation algorithms for all enum fields in the Activity Data Model.

### 6.1 activity_type Enum Validation

**Enum values:** `"event"` | `"service"`

**Validation algorithm:**
```
1. Check if value is present:
   - If missing → REJECT
     - Error: "Activity type is required. Must be 'event' or 'service'."
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "event" or "service" → REJECT
     - Error: "Activity type must be 'event' or 'service'. Received: [value]."
   - If valid → ACCEPT
```

### 6.2 format Enum Validation

**Enum values:** `"session"` | `"workshop"` | `"ceremony"` | `"class_regular"` | `"class_single"` | `"retreat"` | `"performance"` | `"other"`

**Validation algorithm:**
```
1. Check if value is present:
   - If missing → REJECT (for SentToReview)
     - Error: "Format is required for review submission."
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not in enum list → REJECT
     - Error: "Format must be one of: session, workshop, ceremony, class_regular, class_single, retreat, performance, or other. Received: [value]."
   - If valid → CONTINUE

3. If format = "other":
   - Check format_other_label:
     - If missing → REJECT
       - Error: "If format is 'other', format_other_label is required."
     - If present → ACCEPT
   - If format != "other":
     - format_other_label must be absent
     - If present → WARN
       - Note: "format_other_label should only be present when format = 'other'."
```

### 6.3 delivery_mode Enum Validation

**Enum values:** `"in_person"` | `"online"` | `"hybrid"`

**Validation algorithm:**
```
1. Check if value is present:
   - If missing → REJECT (for SentToReview)
     - Error: "Delivery mode is required for review submission."
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "in_person", "online", or "hybrid" → REJECT
     - Error: "Delivery mode must be 'in_person', 'online', or 'hybrid'. Received: [value]."
   - If valid → ACCEPT

3. If delivery_mode != "online":
   - Check location_info:
     - If missing → REJECT (for SentToReview)
       - Error: "Location information is required for in-person or hybrid activities."
```

### 6.4 age_groups Enum Validation

**Enum values:** `"babies"` | `"toddlers"` | `"primary_schoolers"` | `"teenagers"` | `"youngsters_18_25"` | `"adults"` | `"seniors"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is array:
   - If not array → REJECT
     - Error: "Age groups must be an array of enum values."
   - If array → CONTINUE

3. Check each element:
   - For each age_group in array:
     - If not in enum list → REJECT
       - Error: "Age group must be one of: babies, toddlers, primary_schoolers, teenagers, youngsters_18_25, adults, seniors. Received: [value]."
     - If valid → CONTINUE

4. Check for duplicates:
   - If duplicates present → WARN
     - Note: "Duplicate age groups detected. Consider removing duplicates."
```

### 6.5 parental_accompaniment Enum Validation

**Enum values:** `"allowed"` | `"required"` | `"optional"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "allowed", "required", or "optional" → REJECT
     - Error: "Parental accompaniment must be 'allowed', 'required', or 'optional'. Received: [value]."
   - If valid → ACCEPT
```

### 6.6 language_requirements.mode Enum Validation

**Enum values:** `"irrelevant"` | `"understand_only"` | `"speak_and_understand"` | `"mixed"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not in enum list → REJECT
     - Error: "Language requirements mode must be 'irrelevant', 'understand_only', 'speak_and_understand', or 'mixed'. Received: [value]."
   - If valid → ACCEPT

3. If mode != "irrelevant":
   - Check languages_to_understand or languages_to_speak:
     - If both missing → WARN
       - Note: "Language requirements should include languages_to_understand or languages_to_speak when mode is not 'irrelevant'."
```

### 6.7 event_timing.schedule_model Enum Validation

**Enum values:** `"fixed_dates"` | `"recurring"`

**Validation algorithm:**
```
1. Check if value is present (required for event):
   - If missing → REJECT
     - Error: "Event timing must include schedule_model (fixed_dates or recurring)."
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "fixed_dates" or "recurring" → REJECT
     - Error: "Schedule model must be 'fixed_dates' or 'recurring'. Received: [value]."
   - If valid → ACCEPT
```

### 6.8 service_timing.availability_type Enum Validation

**Enum values:** `"by_request"` | `"fixed_windows"` | `"bookable_slots"`

**Validation algorithm:**
```
1. Check if value is present (required for service):
   - If missing → REJECT
     - Error: "Service timing must include availability_type (by_request, fixed_windows, or bookable_slots)."
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "by_request", "fixed_windows", or "bookable_slots" → REJECT
     - Error: "Availability type must be 'by_request', 'fixed_windows', or 'bookable_slots'. Received: [value]."
   - If valid → ACCEPT
```

### 6.9 service_participation.session_mode Enum Validation

**Enum values:** `"one_to_one"` | `"family"` | `"small_group"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "one_to_one", "family", or "small_group" → REJECT
     - Error: "Session mode must be 'one_to_one', 'family', or 'small_group'. Received: [value]."
   - If valid → ACCEPT
```

### 6.10 event_pricing.pricing_type Enum Validation

**Enum values:** `"ticket_price"` | `"donation"` | `"free"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not "ticket_price", "donation", or "free" → REJECT
     - Error: "Pricing type must be 'ticket_price', 'donation', or 'free'. Received: [value]."
   - If valid → ACCEPT
```

### 6.11 service_pricing_model.model Enum Validation

**Enum values:** `"per_session"` | `"per_hour"` | `"per_package"` | `"donation"` | `"free"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not in enum list → REJECT
     - Error: "Pricing model must be 'per_session', 'per_hour', 'per_package', 'donation', or 'free'. Received: [value]."
   - If valid → ACCEPT
```

### 6.12 service_cta.contact_channel.type Enum Validation

**Enum values:** `"social_link"` | `"email"` | `"phone"` | `"other"`

**Validation algorithm:**
```
1. Check if value is present (optional field):
   - If missing → ACCEPT (optional)
   - If present → CONTINUE

2. Check if value is valid enum:
   - If not in enum list → REJECT
     - Error: "Contact channel type must be 'social_link', 'email', 'phone', or 'other'. Received: [value]."
   - If valid → ACCEPT
```

---

## 7. Missing Data Resolution Policy

When required information is missing:
- Ask only for missing fields.
- Group related questions (e.g. timing/schedule together).
- Do not repeat questions for already provided data.
- Do not assume or fabricate values.

### 7.1 Question Grouping Algorithm

**Algorithm:**
```
1. **Group related fields:**
   - Timing fields: date, time, recurrence, timezone → group together
   - Location fields: city, area, venue, online_platform → group together
   - Pricing fields: pricing_type, amount, currency → group together
   - Contact fields: booking_url, contact_channel → group together

2. **Prioritize questions:**
   - Critical fields (activity_type, title) → ask first
   - Required fields for current status → ask next
   - Optional fields → ask last (if needed)

3. **Avoid repetition:**
   - Check if field already provided
   - If provided → skip question
   - If missing → include in question group
```

### 7.2 Activity Type-Specific Questions

**If `activity_type = "event"` and timing missing:**
- Ask for: specific dates, recurrence pattern, or "TBA" indication
- Group: date, time, recurrence, timezone together
- Question template: "For this event, please provide: [date/time/recurrence/timezone]. If dates are TBA, please indicate."

**If `activity_type = "service"` and timing missing:**
- Ask for: availability type (by_request, fixed_windows, bookable_slots)
- If fixed_windows: ask for availability windows (day_of_week, time ranges)
- Ask for: booking policy (how to book/appoint)
- Question template: "For this service, please provide: [availability_type]. If fixed_windows, please provide availability windows (day_of_week, time ranges). Also, how can users book or make an appointment?"

**Conditional Field Validation:**
- If `activity_type = "event"` → ask ONLY for event-specific fields
- If `activity_type = "service"` → ask ONLY for service-specific fields
- Never ask for both event and service fields simultaneously

### 7.3 Handling User Refusals

**If user refuses to provide optional data:**
- Continue with Draft
- Do not block unnecessarily
- Note: "Optional fields can be added later if needed."

**If user refuses required data:**
- Explain that review or publication cannot proceed
- Specify which status requires the missing field (Draft, SentToReview, Approved)
- Question template: "The field [field_name] is required for [status] status. Without it, the Activity cannot proceed to [status]. Would you like to provide it now, or continue as Draft?"
```

---

## 8. Update vs New Activity Detection

The instruction MUST attempt to determine whether input refers to:
- a **new Activity**, or
- an **update to an existing Activity**.

### 8.1 Detection Algorithm

**Signals for update:**
- Explicit user statements: "update", "change", "edit", "modify", "fix", "correct"
- Repeated links: same canonical_url as existing Activity
- Same title + location + timing: matches existing Activity
- Activity ID mentioned: user references existing Activity

**Detection algorithm:**
```
1. **Check for explicit statements:**
   - If user says "update", "change", "edit" → likely UPDATE
   - If user says "new", "create", "add" → likely NEW
   - If ambiguous → ask clarification

2. **Check for repeated links:**
   - Extract canonical_url from sources
   - If canonical_url matches existing Activity → likely UPDATE
   - If no match → likely NEW

3. **Check for same title + location + timing:**
   - Extract title, location, timing
   - If matches existing Activity → likely UPDATE
   - If no match → likely NEW

4. **Check for Activity ID:**
   - If user mentions activity_id → UPDATE
   - If no ID mentioned → likely NEW

5. **If ambiguity remains:**
   - Ask user: "Is this a new Activity or an update to an existing one?"
   - Wait for clarification before proceeding
```

### 8.2 Output Structure for Update Detection

**If update detected:**
```json
{
  "update_vs_new": "update",
  "existing_activity_hint": {
    "activity_id": "string", // if known
    "title": "string",
    "canonical_url": "string"
  }
}
```

**If new detected:**
```json
{
  "update_vs_new": "new",
  "existing_activity_hint": null
}
```

**If ambiguous:**
```json
{
  "update_vs_new": "ambiguous",
  "clarification_requested": true
}
```

---

## 9. Duplicate Awareness (Preliminary)

If input appears to match an existing Activity:
- flag it as a potential duplicate,
- do NOT merge or resolve it,
- prepare the case for Deduplication Instruction.

### 9.1 Detection Algorithm

**Signals for potential duplicate:**
- Same title + location + timing
- Same canonical_url
- Same activator + similar description
- High similarity score (> 0.8)

**Detection algorithm:**
```
1. **Extract comparison fields:**
   - title
   - location_info (city, area, venue)
   - timing (event_timing or service_timing)
   - canonical_url (if present)
   - activator_reference (if available)

2. **Calculate similarity:**
   - Compare title (exact match or high similarity)
   - Compare location (exact match or same city/area)
   - Compare timing (overlapping dates/times)
   - Compare canonical_url (exact match)
   - Calculate similarity score (0.0-1.0)

3. **If similarity score > 0.8:**
   - Flag as potential duplicate
   - Add to duplicate_hints
   - Do NOT merge or resolve
   - Pass to Deduplication Instruction
```

### 9.2 Output Structure for Duplicate Awareness

**If potential duplicate detected:**
```json
{
  "duplicate_hints": [
    {
      "activity_id": "string",
      "similarity_score": 0.0-1.0,
      "matching_fields": ["title", "location", "timing"],
      "canonical_url": "string"
    }
  ]
}
```

**If no duplicate detected:**
```json
{
  "duplicate_hints": []
}
```

---

## 10. Privacy & Safety Constraints

The instruction MUST:
- avoid extracting or retaining personal data;
- ignore or redact personal identifiers unrelated to the Activity;
- flag sensitive or inappropriate content for Safety & Compliance.

### 10.1 Privacy Constraints

**Personal Data Handling:**
- Activator contact data (allowed): email, phone, social links for booking
- Participant personal data (prohibited): names, emails, phone numbers of participants
- Third-party personal data (prohibited): any PII not related to activator

**Algorithm:**
```
1. **Check for participant personal data:**
   - If detected → redact or ignore
   - Do NOT extract participant names, emails, phone numbers

2. **Check for third-party personal data:**
   - If detected → redact or ignore
   - Do NOT extract unrelated PII

3. **Allow activator contact data:**
   - Extract only if explicitly provided for booking/contact
   - Store in appropriate fields (service_cta.contact_channel, event_cta)
```

### 10.2 Safety & Compliance Integration

**Integration points:**
- Before validation: check raw input for safety violations
- After parsing: check extracted data for safety violations
- After validation: check validated data for safety violations

**Algorithm:**
```
1. **Activate Safety & Compliance checks:**
   - Pass raw input or extracted data to Safety & Compliance
   - Wait for Safety & Compliance result

2. **Process Safety & Compliance result:**
   - If BLOCK → stop validation, return BLOCK result to user
   - If ALLOW → continue validation
   - If FLAG → continue validation, but note flag in output

3. **If BLOCK:**
   - Do NOT proceed with validation
   - Return Safety & Compliance response to user
   - Do NOT attempt to bypass safety rules
```

**Screenshots or documents:**
- are treated as temporary sources;
- their content is extracted, not stored verbatim.

---

## 11. Integration with Other Instructions

### 11.1 Integration with Ingest Deep Parsing

**Activation protocol:**

This integration applies **only for non-dialogue input**.

**Workflow:**
```
1. Base Instruction detects non-dialogue input (screenshot, PDF, link, mixed content)
2. Base Instruction routes to INGEST mode
3. Base Instruction delegates to Ingest Validation Instruction
4. Ingest Validation receives:
   - raw input (screenshot, PDF, link, text, or mixed)
   - input type classification (from Base Instruction)
   - context (if any from previous dialogue)

5. Ingest Validation activates Ingest Deep Parsing:
   - Passes raw input and input type classification
   - Requests structured intermediate representation
   - **MUST wait for deep_parsing_artifact before proceeding**

6. Ingest Deep Parsing:
   - Performs deep parsing according to format-specific algorithms
   - **MUST attempt to extract format and other enums early**
   - If confidence < 0.5 for format → set `format: null` + add to `ambiguities[]` with suggested enum values
   - Produces `deep_parsing_artifact` with:
     * `extracted_fields`
     * `confidence_scores`
     * `ambiguities[]` (including format if low confidence)
     * `conflicts[]`
     * `pii_detected[]`
     * `missing_required_fields[]`
     * `artifact_id` (format: `deep_parsing_<ISO_timestamp>`)
     * `version: "v1"`
   - Returns artifact to Ingest Validation

7. Ingest Validation:
   - Receives `deep_parsing_artifact` from Deep Parsing
   - **MUST NOT ask questions until artifact is received**
   - Validates extracted data according to Activity Data Model
   - Processes confidence scores, ambiguities, missing fields
   - **MUST convert ambiguities to user questions (batch mode)**
   - **MUST request ALL missing required fields in one batch (not one-by-one)**
   - Resolves missing required fields through user dialogue
   - Creates `ingest_validation_report` with:
     * `readiness_level`
     * `missing_required_fields[]`
     * `invalid_fields[]`
     * `stop_the_line.blocked` (true if missing_required_fields[] or invalid_fields[] not empty)
     * `artifact_id` (format: `validation_<ISO_timestamp>`)
     * `version: "v1"`
```

**Note:** This section describes the **workflow** of activation.  
For the **structure** of input data, see Section 2.1.

**Note:** For dialogue input, Ingest Validation works directly without activating Deep Parsing. Validation extracts fields from dialogue text using natural language understanding (see Section 2.2).

**Key difference from Input Contract (Section 2.1):**
- Section 2.1 describes **WHAT** Validation receives (structure of input data)
- Section 11.1 describes **HOW** the handoff works (activation protocol, workflow steps)

**Processing Deep Parsing output:**
```
1. **Check confidence scores:**
   - If confidence < 0.5 for critical field → request clarification
   - If confidence >= 0.5 → use value, but flag for verification if < 0.8

2. **Process ambiguities:**
   - For each ambiguity in metadata.ambiguities:
     - If critical field → request clarification
     - If optional field → use most likely value with low confidence

3. **Process missing required fields:**
   - For each field in metadata.missing_required_fields:
     - Check if required for current validation level
     - If required → request from user
     - If optional → note but do not block

4. **Process conflicts:**
   - For each conflict in metadata.conflicts:
     - Use resolved_value from Deep Parsing
     - Lower confidence score for conflicted field
     - Note conflict in validation metadata
```

**Error handling:**
```
1. **If Deep Parsing returns error:**
   - Do NOT proceed with validation
   - Return error to user
   - Request alternative input

2. **If Deep Parsing returns empty result:**
   - Request clarification from user
   - Ask for more detailed input

3. **If Deep Parsing returns invalid structure:**
   - Attempt to validate what is available
   - Request missing critical fields
```

### 11.2 Integration with Safety & Compliance

**Integration points:**
- Raw Input Check (before parsing)
- Extracted Data Check (after parsing, before validation)
- Validated Data Check (after validation)

**Handoff protocol:**
```
1. **Raw Input Check:**
   - Before activating Deep Parsing
   - Pass raw input to Safety & Compliance
   - If BLOCK → stop, return BLOCK result
   - If ALLOW → continue to Deep Parsing

2. **Extracted Data Check:**
   - After receiving Deep Parsing output
   - Pass extracted_data to Safety & Compliance
   - If BLOCK → stop, return BLOCK result
   - If ALLOW → continue to validation

3. **Validated Data Check:**
   - After validation completes
   - Pass validated_data to Safety & Compliance
   - If BLOCK → stop, return BLOCK result
   - If ALLOW → continue to Normalizer
```

**Processing Safety & Compliance result:**
```
1. **If BLOCK:**
   - Stop validation immediately
   - Return Safety & Compliance response to user
   - Do NOT attempt to bypass or work around

2. **If ALLOW:**
   - Continue with validation
   - No action needed

3. **If FLAG:**
   - Continue with validation
   - Note flag in validation metadata
   - Pass flag to Normalizer
```

### 11.3 Integration with Activity Normalizer

**Handoff protocol:**
```
1. Ingest Validation completes validation
2. Returns validated_data and validation_metadata
3. Activity Normalizer:
   - Receives validated data
   - Normalizes to canonical JSON format
   - Returns normalized data for API Orchestrator
```

**Output structure for Normalizer:**
```json
{
  "validated_data": {
    // All validated fields matching Activity Data Model
  },
  "validation_metadata": {
    "validation_status": "Draft-ready" | "SentToReview-ready" | "Approved-ready",
    "missing_fields": {
      "Draft": ["field1", "field2"],
      "SentToReview": ["field3", "field4"],
      "Approved": ["field5"]
    },
    "ambiguities": [...],
    "duplicate_hints": [...],
    "update_vs_new": "new" | "update" | "ambiguous",
    "safety_flags": [...]
  }
}
```

---

## 12. Output Contract

**For Strict Protocol Mode:**

Ingest Validation MUST produce `ingest_validation_report` as output artifact:

- **When:** After each validation round (may be multiple rounds if user provides fields incrementally)
- **Required fields:** See Section 4.2 (Artifact Creation) for full structure
- **Version:** `v1`
- **Artifact ID:** `validation_<ISO_timestamp>`

**Handoff to next module:**

- **To Safety & Compliance (Point 3: Validated):**
  - Pass `ingest_validation_report`
  - Pass validated_payload (if readiness_level matches target_readiness)

- **To Gate (if SentToReview-ready):**
  - Pass `ingest_validation_report`
  - Pass validated_payload
  - Create `gate_request_package` (see Section 12.1)

- **To Normalizer (if Draft-only):**
  - Pass `ingest_validation_report`
  - Pass validated_payload

**Reference:** Base Instruction Section 1.5 (Rule 1: Mandatory Artifacts)

---

The output of this instruction MUST be:

- a structured intermediate representation of the Activity, containing:
  - validated fields (validated according to Activity Data Model),
  - `activity_type` (determined and validated),
  - conditional fields (event_* OR service_*, never both),
  - identified missing fields (grouped by status requirement),
  - detected ambiguities,
  - detected duplicates (if any),
  - validation status (Draft-ready, SentToReview-ready, Approved-ready).

**Output structure MUST match Activity Data Model:**
- See `GPT UI/docs/activity-data-model.md` for complete schema
- Conditional fields must be validated based on `activity_type`
- All enum values must be validated against canonical values

**Note:** For detailed algorithms on how these metadata fields are populated, see:
- Section 4 (Validation Levels) for `validation_status` and `missing_fields`
- Section 8 (Update vs New Activity Detection) for `existing_activity_hint` and `update_vs_new`
- Section 9 (Duplicate Awareness) for `duplicate_hints`
- Section 10 (Privacy & Safety Constraints) for `safety_flags`
- Section 11.1 (Integration with Ingest Deep Parsing) for `ambiguities`

**Output structure:**
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
    "validation_status": "Draft-ready" | "SentToReview-ready" | "Approved-ready" | "Draft-not-ready" | "SentToReview-not-ready" | "Approved-not-ready",
    "missing_fields": {
      "Draft": ["field1", "field2"],
      "SentToReview": ["field3", "field4"],
      "Approved": ["field5"]
    },
    "ambiguities": [
      {
        "field": "event_timing.date",
        "type": "date",
        "values": ["2025-01-15", "2025-01-20"],
        "resolution_requested": true
      }
    ],
    "duplicate_hints": [
      {
        "activity_id": "string",
        "similarity_score": 0.85,
        "matching_fields": ["title", "location", "timing"]
      }
    ],
    "update_vs_new": "new" | "update" | "ambiguous",
    "existing_activity_hint": {
      "activity_id": "string",
      "title": "string",
      "canonical_url": "string"
    } | null,
    "safety_flags": [
      {
        "category": "string",
        "severity": "CRITICAL" | "HIGH" | "MEDIUM",
        "message": "string"
      }
    ]
  }
}
```

This output is intended solely for:
- Activity Normalizer Instruction (for normalization to canonical format).

---

## 13. Edge Cases & Validation

### 13.1 Activity Type Cannot Be Determined

**Scenario:** Deep Parsing cannot determine activity_type (confidence < 0.5)

**Handling:**

```
1. Do NOT proceed with validation
2. Request clarification from user:
   - "I couldn't determine if this is an event (scheduled occurrence) or a service (available by appointment). Please clarify."
3. Wait for user response
4. Once activity_type determined → proceed with validation
```

### 13.2 Conflicting Conditional Fields

**Scenario:** Both event_* and service_* fields present simultaneously

**Handling:**
```
1. REJECT immediately
2. List all conflicting fields
3. Error: "Event Activities cannot have service-specific fields, and vice versa. Please remove conflicting fields: [list]"
4. Request correction
5. Do NOT proceed until conflict resolved
```

### 13.3 Invalid State Transition Request

**Scenario:** User requests transition to status without required data

**Handling:**
```
1. Check current validation status
2. Check required fields for requested status
3. If missing required fields:
   - Error: "Cannot transition to [status] without required fields: [list]"
   - List missing fields
   - Request missing fields
4. Do NOT proceed until requirements met
```

### 13.4 Partial Data from Deep Parsing

**Scenario:** Deep Parsing returns partial data (some fields extracted, some not)

**Handling:**
```
1. Validate what is available
2. Check missing required fields
3. Request missing required fields from user
4. Continue with partial validation
5. Do NOT block on optional fields
```

### 13.5 Ambiguous Data from Deep Parsing

**Scenario:** Deep Parsing returns data with ambiguities

**Handling:**
```
1. For each ambiguity:
   - If critical field → request clarification
   - If optional field → use most likely value with low confidence
2. Flag ambiguities in validation metadata
3. Continue with validation
4. Request clarification for critical ambiguities
```

### 13.6 Update Request for Non-Existent Activity

**Scenario:** User says "update", but Activity does not exist

**Handling:**
```
1. Detect update intent
2. Check if Activity exists (if possible)
3. If not exists:
   - Clarify: "I couldn't find an existing Activity to update. Would you like to create a new Activity instead?"
4. Wait for user confirmation
5. Proceed based on user response
```

### 13.7 Multiple Potential Duplicates

**Scenario:** Multiple potential duplicates detected

**Handling:**
```
1. Flag all potential duplicates in duplicate_hints
2. Do NOT resolve or merge
3. Pass all duplicates to Deduplication Instruction
4. Note in validation metadata
5. Continue with validation (do not block)
```

### 13.8 Safety & Compliance BLOCK

**Scenario:** Safety & Compliance returns BLOCK

**Handling:**
```
1. Stop validation immediately
2. Do NOT proceed with any validation
3. Return Safety & Compliance response to user
4. Do NOT attempt to bypass or work around
5. Explain why content was blocked
```

---

## 14. Validation Checklist

### 14.1 Pre-Implementation

- [x] Activity Data Model изучен и понят
- [x] Integration с Ingest Deep Parsing проработана
- [x] Integration с Safety & Compliance проработана
- [x] Integration с Activity Normalizer проработана
- [x] Enum values для всех controlled vocabularies определены
- [x] Conditional field rules поняты
- [x] Mutually exclusive field rules поняты
- [x] Field completeness requirements по статусам поняты
- [x] Error message templates подготовлены
- [x] Question templates для missing data resolution подготовлены
- [x] Validation algorithms для всех уровней подготовлены

### 14.2 Post-Implementation Testing

- [ ] Draft validation работает для event
- [ ] Draft validation работает для service
- [ ] SentToReview validation работает для event
- [ ] SentToReview validation работает для service
- [ ] Approved validation работает для event
- [ ] Approved validation работает для service
- [ ] Mutually exclusive fields проверяются корректно
- [ ] Enum validation работает для всех enum fields
- [ ] Missing data resolution работает корректно
- [ ] Update vs new detection работает корректно
- [ ] Duplicate awareness работает корректно
- [ ] Integration с Deep Parsing работает корректно
- [ ] Integration с Safety & Compliance работает корректно
- [ ] Integration с Normalizer работает корректно
- [ ] Edge cases обрабатываются корректно

### 14.3 Quality Criteria

- [x] Все enum values валидируются
- [x] Все conditional fields валидируются корректно
- [x] Все mutually exclusive fields проверяются
- [x] Все error messages понятны и информативны
- [x] Все questions для missing data resolution понятны и не повторяются
- [x] Validation status определяется корректно
- [x] Output structure соответствует Activity Data Model

---

## 15. Example Formulations

### 15.1 Draft Validation Success (Event)

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Yoga Workshop",
    "full_description": "A relaxing yoga workshop for beginners.",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [
        {
          "start": "2025-02-15T10:00:00+02:00",
          "end": "2025-02-15T12:00:00+02:00",
          "timezone": "Europe/Tallinn"
        }
      ]
    }
  },
  "metadata": {
    "confidence_scores": {
      "activity_type": 0.95,
      "title": 0.9,
      "event_timing": 0.85
    }
  }
}
```

**Validation Result:**
```json
{
  "validated_data": {
    "activity_type": "event",
    "title": "Yoga Workshop",
    "full_description": "A relaxing yoga workshop for beginners.",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [...]
    }
  },
  "validation_metadata": {
    "validation_status": "Draft-ready",
    "missing_fields": {
      "Draft": [],
      "SentToReview": ["format", "delivery_mode", "location_info"]
    }
  }
}
```

**Response to user:**
```
✅ Draft validation successful! Your Activity is ready for Draft status.

To submit for review, you'll need:
- Format (session, workshop, ceremony, etc.)
- Delivery mode (in_person, online, or hybrid)
- Location information (if in-person or hybrid)
```

### 15.2 Draft Validation Failure (Missing Title)

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "full_description": "A relaxing yoga workshop for beginners.",
    "event_timing": {...}
  },
  "metadata": {
    "missing_required_fields": ["title"]
  }
}
```

**Validation Result:**
```json
{
  "validated_data": {
    "activity_type": "event",
    "full_description": "A relaxing yoga workshop for beginners.",
    "event_timing": {...}
  },
  "validation_metadata": {
    "validation_status": "Draft-not-ready",
    "missing_fields": {
      "Draft": ["title"]
    }
  }
}
```

**Response to user:**
```
❌ Title is required for Draft status. Please provide a title for this Activity.
```

### 15.3 SentToReview Validation Success (Service)

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "activity_type": "service",
    "title": "Meditation Coaching",
    "full_description": "One-on-one meditation coaching sessions available by appointment.",
    "format": "session",
    "delivery_mode": "online",
    "service_timing": {
      "availability_type": "by_request",
      "booking_policy": "Contact via email or Telegram"
    }
  }
}
```

**Validation Result:**
```json
{
  "validated_data": {
    "activity_type": "service",
    "title": "Meditation Coaching",
    "full_description": "One-on-one meditation coaching sessions available by appointment.",
    "format": "session",
    "delivery_mode": "online",
    "service_timing": {...}
  },
  "validation_metadata": {
    "validation_status": "SentToReview-ready",
    "missing_fields": {
      "Draft": [],
      "SentToReview": []
    }
  }
}
```

**Response to user:**
```
✅ Review validation successful! Your Activity is ready for review submission.
```

### 15.4 Mutually Exclusive Fields Conflict

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Yoga Workshop",
    "event_timing": {...},
    "service_timing": {...} // CONFLICT
  }
}
```

**Validation Result:**
```json
{
  "validated_data": {
    "activity_type": "event",
    "title": "Yoga Workshop",
    "event_timing": {...}
  },
  "validation_metadata": {
    "validation_status": "error",
    "error": "Mutually exclusive fields conflict: Event Activities cannot have service_timing."
  }
}
```

**Response to user:**
```
❌ Error: Event Activities cannot have service-specific fields.

Please remove: service_timing

Event Activities should use: event_timing, event_capacity, event_duration, event_pricing, event_cta
```

### 15.5 Update vs New Detection

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "title": "Yoga Workshop",
    "event_timing": {...}
  },
  "metadata": {
    "sources": {
      "canonical_url": "https://example.com/yoga-workshop"
    }
  }
}
```

**User statement:** "Update the yoga workshop"

**Detection Result:**
```json
{
  "update_vs_new": "update",
  "existing_activity_hint": {
    "canonical_url": "https://example.com/yoga-workshop",
    "title": "Yoga Workshop"
  }
}
```

**Response to user:**
```
I detected this might be an update to an existing Activity (Yoga Workshop).

Is this correct? If yes, I'll update the existing Activity. If no, I'll create a new one.
```

### 15.6 Duplicate Awareness

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "title": "Yoga Workshop",
    "location_info": {
      "city": "Tallinn",
      "venue": "Yoga Studio"
    },
    "event_timing": {
      "fixed_dates": [{"start": "2025-02-15T10:00:00+02:00", ...}]
    }
  }
}
```

**Detection Result:**
```json
{
  "duplicate_hints": [
    {
      "activity_id": "act_123",
      "similarity_score": 0.9,
      "matching_fields": ["title", "location", "timing"]
    }
  ]
}
```

**Response to user:**
```
⚠️ I detected a potential duplicate Activity (similarity: 90%).

Matching fields: title, location, timing

Is this a new Activity or the same one? I'll help you resolve this.
```

### 15.7 Safety & Compliance BLOCK

**Input from Deep Parsing:**
```json
{
  "extracted_data": {
    "title": "Medical Consultation",
    "full_description": "I guarantee to cure all diseases..."
  }
}
```

**Safety & Compliance Result:** BLOCK (Medical claims)

**Validation Result:**
```json
{
  "validation_metadata": {
    "validation_status": "blocked",
    "safety_flags": [
      {
        "category": "medical_claims",
        "severity": "CRITICAL",
        "message": "Medical claims are not allowed."
      }
    ]
  }
}
```

**Response to user:**
```
❌ This content cannot be processed.

**Reason:** Medical or mental health claims are not allowed.

**Guidance:** Please remove any medical claims, guarantees of cure, or therapeutic promises. You can describe the activity format and approach without making health claims.

Please revise your content and try again.
```
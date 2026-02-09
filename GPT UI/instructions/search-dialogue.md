# Search Dialogue Instruction
## Conversational Search, Filter Clarification & Query Structuring

### Purpose

Search Dialogue Instruction is responsible for **conducting search-oriented conversations** with users.

Its purpose is to:
- understand what the user is looking for,
- clarify intent and constraints when needed,
- translate natural language into structured search parameters,
- prepare search requests for backend execution.

This instruction focuses exclusively on **search and discovery**.

It does NOT:
- create or modify Activities,
- call backend APIs directly,
- store user history or preferences,
- personalize results based on user behavior.

---

## 1. Scope of Responsibility

This instruction is activated **only in SEARCH mode**, as determined by Base Instruction.

It handles:
- open-ended discovery queries,
- filtered searches,
- iterative refinement of search criteria.

It does NOT handle:
- ingestion (INGEST flow does this),
- policy evaluation (KоныРода Gate does this),
- result presentation formatting (Results Presenter does this),
- API calls (API Orchestrator does this).

**Search Principles:**
- Stateless: each search session is independent
- Minimal clarification: ask only when it improves relevance
- Privacy-first: no user profiling or preference storage
- User autonomy: user controls search refinement

---

## 2. Input Contract

This instruction receives input from **Base Instruction** when SEARCH mode is activated.

**Input structure from Base Instruction:**
- User input: natural language search query
- Mode: SEARCH (already determined by Base Instruction)
- Context: current dialogue context (ephemeral)

**Activation conditions:**
- Base Instruction has determined mode = SEARCH
- User input contains search intent indicators:
  - Action verbs: find, search, browse, recommend, show, list
  - Question patterns: "what exists for...", "what activities..."
  - Filter requests: "by age", "by format", "by date"

**Reference:**
- Base Instruction SEARCH mode activation: `GPT UI/instructions/base.md`, Section 1.2

---

## 3. Search Intent Interpretation Algorithm

This instruction MUST identify user search intent and extract search parameters from natural language.

### 3.1 Intent Interpretation Algorithm

**Algorithm (execute in order):**

```
1. **Extract keywords and phrases:**
   - Identify action verbs: find, search, browse, recommend, show, list
   - Identify question patterns: "what exists for...", "what activities..."
   - Identify filter requests: "by age", "by format", "by date"

2. **Classify primary goal:**
   - IF user asks "find specific X" → goal = "find_specific"
   - IF user asks "what exists" → goal = "explore"
   - IF user asks "compare X and Y" → goal = "compare"
   - ELSE → goal = "explore" (default)

3. **Identify activity type preference:**
   - IF user mentions: "event", "workshop", "class", "session" → activity_type = "event"
   - IF user mentions: "service", "coaching", "consultation" → activity_type = "service"
   - ELSE → activity_type = null (search both)

4. **Extract time preference:**
   - IF user mentions: "today", "tomorrow", "this week" → time.type = "soon"
   - IF user mentions: specific date → time.type = "specific_date"
   - IF user mentions: "recurring", "regular" → time.type = "recurring"
   - ELSE → time.type = null

5. **Extract location preference:**
   - IF user mentions: city name → location.city = city
   - IF user mentions: "online" → delivery_mode = "online"
   - IF user mentions: "in person" → delivery_mode = "in_person"
   - ELSE → delivery_mode = null

6. **Extract other filters:**
   - age_groups: extract from "for children", "for adults", etc.
   - format: extract from "workshop", "session", "class", etc.
   - categories: extract from context or ask

7. **If intent is unclear:**
   - Ask ONE clarification question (highest priority missing dimension)
   - Wait for user response
   - Re-run algorithm with new input
```

### 3.2 Intent Types

**Primary goals:**
- **explore** — general discovery, browsing
- **find_specific** — looking for specific activity or type
- **compare** — comparing multiple activities

**Activity type preferences:**
- **event** — scheduled occurrences with fixed dates/times
- **service** — on-demand offerings by appointment
- **null** — search both types

---

## 4. Natural Language → Filters Mapping

This instruction MUST extract structured search filters from natural language input.

### 4.1 Activity Type Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "event", "events", "workshop", "workshops", "class", "classes" | `activity_type: "event"` |
| "service", "services", "coaching", "consultation", "session" | `activity_type: "service"` |

### 4.2 Age Group Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "for children", "kids", "children", "child" | `age_groups: ["babies", "toddlers", "primary_schoolers"]` |
| "for adults", "adult" | `age_groups: ["adults"]` |
| "for teenagers", "teen", "teens" | `age_groups: ["teenagers"]` |
| "for seniors", "elderly" | `age_groups: ["seniors"]` |
| "for youngsters", "young adults" | `age_groups: ["youngsters_18_25"]` |

### 4.3 Format Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "workshop", "workshops" | `format: "workshop"` |
| "session", "sessions" | `format: "session"` |
| "class", "classes", "regular class" | `format: "class_regular"` |
| "single class", "one-time class" | `format: "class_single"` |
| "ceremony", "ceremonies" | `format: "ceremony"` |
| "retreat", "retreats" | `format: "retreat"` |
| "performance", "show" | `format: "performance"` |

### 4.4 Delivery Mode Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "online", "virtual", "remote" | `delivery_mode: "online"` |
| "in person", "offline", "physical", "venue" | `delivery_mode: "in_person"` |
| "hybrid" | `delivery_mode: "hybrid"` |

### 4.5 Location Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| City name (Tallinn, Tartu, etc.) | `location.city: "city_name"` |
| "in [city]" | `location.city: "city"` |
| Area/district name | `location.area: "area_name"` |

### 4.6 Time Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "today", "tomorrow", "this week", "soon" | `time.type: "soon"` |
| "this week" | `time.type: "this_week"` |
| Specific date (e.g., "2025-02-15") | `time.type: "specific_date"`, `time.start_date: "2025-02-15"` |
| Date range (e.g., "from X to Y") | `time.type: "date_range"`, `time.start_date: "X"`, `time.end_date: "Y"` |
| "recurring", "regular", "weekly", "monthly" | `time.type: "recurring"` |

### 4.7 Language Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "in Russian", "Russian language" | `language_requirements.languages_to_understand: ["ru"]` |
| "in English", "English language" | `language_requirements.languages_to_understand: ["en"]` |
| "Russian speaking" | `language_requirements.languages_to_speak: ["ru"]` |
| "English speaking" | `language_requirements.languages_to_speak: ["en"]` |

### 4.8 Pricing Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "free", "no cost", "gratis" | `pricing.type: "free"` |
| "paid", "costs", "price" | `pricing.type: "paid"` |
| "under [amount]", "less than [amount]" | `pricing.type: "paid"`, `pricing.max_price: amount` |

### 4.9 Parental Accompaniment Mapping

| Natural Language Pattern | Search Filter |
|-------------------------|---------------|
| "parents allowed", "with parents" | `parental_accompaniment: "allowed"` |
| "parents required", "must have parents" | `parental_accompaniment: "required"` |
| "parents optional" | `parental_accompaniment: "optional"` |

---

## 5. Clarification Flow Algorithm

This instruction MUST use clarification sparingly but deliberately.

### 5.1 Clarification Decision Logic

**Algorithm:**

```
1. **Check if clarification is needed:**
   - IF query.text is empty AND all filters are null:
       → Clarification needed: ask for general intent
   - IF query.text is present BUT no filters extracted:
       → Check if filters would improve relevance:
           * IF time-sensitive query (mentions "soon", "this week"):
               → Ask about time preference
           * ELSE IF location-sensitive query (mentions city):
               → Ask about location preference
           * ELSE:
               → Proceed with text-only search

2. **Ordering of clarifications (if needed):**
   - Priority 1: Time relevance (if query suggests time-sensitive)
   - Priority 2: Location/online preference (if query suggests location-sensitive)
   - Priority 3: Age group (if query suggests age-specific)
   - Priority 4: Language requirements (if query suggests language-specific)
   - Priority 5: Format or category (if query is very vague)

3. **Ask clarification:**
   - Ask ONE question at a time
   - Use natural, conversational language
   - Provide examples if helpful
   - Accept partial answers

4. **If user provides partial answer:**
   - Extract what is provided
   - Proceed with search using available information
   - Do NOT block search unnecessarily

5. **If user declines to answer:**
   - Accept and proceed with available information
   - Do NOT insist
```

### 5.2 Minimal Clarification Rule

**Rules:**
- Ask only questions that significantly improve result relevance
- Avoid exhaustive questionnaires
- Do not ask for information that can be inferred
- Do not ask multiple questions at once
- Accept "I don't know" or "any" as valid answers

---

## 6. Search Query Structure (Output Contract)

This instruction produces a structured search query for **API Orchestrator**.

### 6.1 Search Query JSON Schema

**Output structure for API Orchestrator:**

**Reference:** Full schema documentation: `search-data-model.md`

```json
{
  "query": {
    // Semantic search
    "text": "string | null",
    
    // Activity type (key discriminator)
    "activity_type": "event" | "service" | null,
    
    // Filters
    "filters": {
      // ============================================
      // TIME FILTERS (extended)
      // ============================================
      "time": {
        // For events: date range
        "date_range": {
          "start_date": "ISO 8601",
          "end_date": "ISO 8601",
          "timezone": "IANA timezone | null"
        } | null,
        
        // For events: specific dates with time ranges
        "specific_dates": [
          {
            "date": "YYYY-MM-DD",
            "time_range": {
              "start": "HH:MM",
              "end": "HH:MM"
            } | null,
            "timezone": "IANA timezone | null"
          }
        ] | null,
        
        // For services and recurring events: weekly schedule
        "weekly_schedule": [
          {
            "day_of_week": "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday",
            "time_range": {
              "start": "HH:MM",
              "end": "HH:MM"
            } | null,
            "timezone": "IANA timezone | null"
          }
        ] | null,
        
        // Simplified variants (for backward compatibility)
        "type": "specific_date" | "date_range" | "soon" | "this_week" | "recurring" | null,
        "start_date": "ISO 8601 | null",
        "end_date": "ISO 8601 | null"
      },
      
      // ============================================
      // LANGUAGE REQUIREMENTS (extended)
      // ============================================
      "language_requirements": {
        "mode": "irrelevant" | "understand_only" | "speak_and_understand" | "mixed" | null,
        "languages_to_understand": ["ru", "en", "et"] | null,  // ISO 639-1 codes
        "languages_to_speak": ["ru", "en", "et"] | null,  // ISO 639-1 codes
        
        // For semantic search (optional, if backend supports)
        "semantic_search": {
          "enabled": boolean,
          "threshold": number  // default 0.7, range 0.0-1.0
        } | null
      },
      
      // ============================================
      // LOCATION (extended)
      // ============================================
      "location": {
        // Text search (from Activity Data Model)
        "city": "string | null",
        "area": "string | null",
        "venue": "string | null",
        
        // Geolocation (if coordinates available in future)
        "coordinates": {
          "longitude": number,
          "latitude": number,
          "radius_km": number
        } | null,
        
        // For services: service_area
        "service_area": {
          "radius_km": number | null,
          "districts": ["string"] | null
        } | null
      },
      
      // ============================================
      // BASIC FILTERS (from Activity Data Model)
      // ============================================
      
      // Activity format
      "format": "session" | "workshop" | "ceremony" | "class_regular" | "class_single" | "retreat" | "performance" | "other" | null,
      
      // Categories (two-level taxonomy)
      "categories": {
        "primary": "string | null",
        "secondary": ["string"] | null,
        "freeform_tags": ["string"] | null  // for searching by user tags
      } | null,
      
      // Age groups
      "age_groups": [
        "babies" | "toddlers" | "primary_schoolers" | "teenagers" | 
        "youngsters_18_25" | "adults" | "seniors"
      ] | null,
      
      // Parental accompaniment
      "parental_accompaniment": "allowed" | "required" | "optional" | null,
      
      // Delivery mode
      "delivery_mode": "in_person" | "online" | "hybrid" | null,
      
      // ============================================
      // PRICING (from Activity Data Model)
      // ============================================
      "pricing": {
        // For events
        "event_pricing": {
          "pricing_type": "ticket_price" | "donation" | "free" | null,
          "max_ticket_price": number | null,
          "currency": "ISO 4217 | null"  // e.g., "EUR", "USD"
        } | null,
        
        // For services
        "service_pricing": {
          "model": "per_session" | "per_hour" | "per_package" | "donation" | "free" | null,
          "max_price": number | null,
          "currency": "ISO 4217 | null"
        } | null,
        
        // Simplified variant (for backward compatibility)
        "type": "free" | "paid" | null,
        "max_price": number | null,
        "currency": "ISO 4217 | null"
      },
      
      // ============================================
      // PARTICIPATION & CAPACITY (from Activity Data Model)
      // ============================================
      "participation": {
        // For events
        "event_capacity": {
          "min_participants": number | null,
          "max_participants": number | null,
          "available_seats": number | null  // search by available seats
        } | null,
        
        // For services
        "service_participation": {
          "session_mode": "one_to_one" | "family" | "small_group" | null
        } | null
      },
      
      // ============================================
      // ADDITIONAL FILTERS
      // ============================================
      
      // Organizer/creator (search by creator/owner_reference)
      "organizer": "string | null",
      
      // Activity status (usually only Published, but can be a filter)
      "status": "Draft" | "SentToReview" | "Approved" | "Published" | null,
      
      // Search by media/links
      "has_media": {
        "official_site": boolean | null,
        "social_links": boolean | null,
        "booking_url": boolean | null  // for services
      } | null
    },
    // ============================================
    // DEFAULT VALUES
    // ============================================
    "defaults": {
      "status": "Published",  // only published activities
      "implicit_filters": []  // filters applied but not explicitly requested
    }
  },
  // ============================================
  // PAGINATION
  // ============================================
  "pagination": {
    "page": number,  // default: 1, min: 1
    "per_page": number  // default: 20, min: 1, max: 100
  },
  // ============================================
  // SORTING
  // ============================================
  "sort": {
    "field": "relevance" | "date" | "title" | "price" | "created_at" | null,
    "order": "asc" | "desc" | null
  }
```

### 6.2 Time Filters — Detailed Description

#### 6.2.1 `time.date_range`
**Purpose:** Search activities within a date range  
**Applicable to:**
- Events: search in `event_timing.fixed_dates` or `event_timing.recurring.start_date/end_date`
- Services: not applicable (services do not have specific dates)

**Natural Language Examples:**
- "in February" → `date_range: {start_date: "2025-02-01", end_date: "2025-02-28"}`
- "from February 1 to 15" → `date_range: {start_date: "2025-02-01", end_date: "2025-02-15"}`

#### 6.2.2 `time.specific_dates`
**Purpose:** Search by specific dates with optional time ranges  
**Applicable to:**
- Events: search in `event_timing.fixed_dates` or compute from `recurring`
- Services: not applicable

**Natural Language Examples:**
- "February 15 from 7 PM to 9 PM" → `specific_dates: [{date: "2025-02-15", time_range: {start: "19:00", end: "21:00"}}]`
- "February 15 and 16" → `specific_dates: [{date: "2025-02-15"}, {date: "2025-02-16"}]`

#### 6.2.3 `time.weekly_schedule`
**Purpose:** Search by days of week with optional time windows  
**Applicable to:**
- Services: search in `service_timing.availability_windows`
- Recurring Events: search in `event_timing.recurring` (if RRULE contains day_of_week)

**Natural Language Examples:**
- "on Mondays from 10 AM to 12 PM" → `weekly_schedule: [{day_of_week: "monday", time_range: {start: "10:00", end: "12:00"}}]`
- "every Tuesday and Thursday" → `weekly_schedule: [{day_of_week: "tuesday"}, {day_of_week: "thursday"}]`

#### 6.2.4 `time.type` (simplified variant)
**Purpose:** Backward compatibility with current schema  
**Values:**
- `"specific_date"` — specific date
- `"date_range"` — date range
- `"soon"` — soon (today, tomorrow, this week)
- `"this_week"` — this week
- `"recurring"` — recurring events

### 6.3 Language Requirements — Detailed Description

#### 6.3.1 `language_requirements.mode`
**Purpose:** Filter by language requirement mode  
**Values:**
- `"irrelevant"` — language not important
- `"understand_only"` — understanding required only
- `"speak_and_understand"` — both understanding and speaking required
- `"mixed"` — mixed requirements

**Natural Language Examples:**
- "where language doesn't matter" → `mode: "irrelevant"`
- "where understanding is needed" → `mode: "understand_only"`

#### 6.3.2 `language_requirements.languages_to_understand`
**Purpose:** Search by languages that need to be understood  
**Format:** Array of ISO 639-1 codes (e.g., `["ru", "en", "et"]`)

**Natural Language Examples:**
- "in Russian" → `languages_to_understand: ["ru"]`
- "in Russian or English" → `languages_to_understand: ["ru", "en"]`

#### 6.3.3 `language_requirements.languages_to_speak`
**Purpose:** Search by languages that need to be spoken  
**Format:** Array of ISO 639-1 codes

**Natural Language Examples:**
- "where English speaking is required" → `languages_to_speak: ["en"]`

#### 6.3.4 `language_requirements.semantic_search`
**Purpose:** Enable semantic search via embeddings (optional)  
**Parameters:**
- `enabled`: boolean — enable/disable semantic search
- `threshold`: number — similarity threshold (0.0-1.0, default 0.7)

**Note:** Used only if backend supports semantic search.

### 6.4 Location — Detailed Description

#### 6.4.1 `location.city`, `location.area`, `location.venue`
**Purpose:** Text search by location (from `location_info` in Activity Data Model)

**Natural Language Examples:**
- "in Tallinn" → `location.city: "Tallinn"`
- "in Kesklinn district" → `location.area: "Kesklinn"`

#### 6.4.2 `location.coordinates`
**Purpose:** Geolocation search with radius (if coordinates are available)  
**Note:** Current model does not contain coordinates, this is for future expansion

#### 6.4.3 `location.service_area`
**Purpose:** Search by service area (for services)  
**Fields:**
- `radius_km`: radius in kilometers
- `districts`: array of district names

**Natural Language Examples:**
- "within 10 km radius" → `service_area.radius_km: 10`
- "in Kesklinn and Põhja-Tallinn districts" → `service_area.districts: ["Kesklinn", "Põhja-Tallinn"]`

### 6.5 Pricing — Detailed Description

#### 6.5.1 `pricing.event_pricing`
**Purpose:** Filters for event pricing  
**Fields:**
- `pricing_type`: pricing type (ticket_price, donation, free)
- `max_ticket_price`: maximum ticket price
- `currency`: currency (ISO 4217)

**Natural Language Examples:**
- "free events" → `event_pricing.pricing_type: "free"`
- "up to 50 euros" → `event_pricing.max_ticket_price: 50, currency: "EUR"`

#### 6.5.2 `pricing.service_pricing`
**Purpose:** Filters for service pricing  
**Fields:**
- `model`: pricing model (per_session, per_hour, per_package, donation, free)
- `max_price`: maximum price
- `currency`: currency

**Natural Language Examples:**
- "free services" → `service_pricing.model: "free"`
- "up to 100 euros per session" → `service_pricing.model: "per_session", max_price: 100, currency: "EUR"`

#### 6.5.3 `pricing.type`, `pricing.max_price`, `pricing.currency`
**Purpose:** Simplified variant for backward compatibility

### 6.6 Participation & Capacity — Detailed Description

#### 6.6.1 `participation.event_capacity`
**Purpose:** Filters for event capacity  
**Fields:**
- `min_participants`: minimum number of participants
- `max_participants`: maximum number of participants
- `available_seats`: search by available seats

**Natural Language Examples:**
- "available seats" → `event_capacity.available_seats: > 0`
- "for 10-20 people" → `event_capacity.min_participants: 10, max_participants: 20`

#### 6.6.2 `participation.service_participation`
**Purpose:** Filters for service participation  
**Fields:**
- `session_mode`: session mode (one_to_one, family, small_group)

**Natural Language Examples:**
- "individual sessions" → `service_participation.session_mode: "one_to_one"`
- "family sessions" → `service_participation.session_mode: "family"`

### 6.7 Query Building Rules

**Rules:**
- Include only explicitly requested or extracted filters
- Mark implicit defaults clearly
- Do not invent filters not mentioned by user
- Use null for optional filters that are not specified
- Always include `defaults.status: "Published"` (only search published activities)

**Conditional Logic:**
- **If `activity_type = "event"`:**
  - Use `time.date_range`, `time.specific_dates` for time filters
  - Use `pricing.event_pricing` for pricing filters
  - Use `participation.event_capacity` for capacity filters

- **If `activity_type = "service"`:**
  - Use `time.weekly_schedule` for time filters
  - Use `pricing.service_pricing` for pricing filters
  - Use `participation.service_participation` for participation filters

- **If `activity_type = null`:**
  - Backend should search in both types
  - Apply appropriate filters to each type

**Filter Priority:**
1. **Time filters:** `specific_dates` or `weekly_schedule` have priority over `date_range`
2. **Language filters:** `mode` is primary filter, `languages_to_understand` and `languages_to_speak` are additional
3. **Location filters:** `coordinates` have priority over text search, `service_area` applies only to services

**Reference:**
- Full schema documentation: `GPT UI/docs/search-data-model.md`
- Activity Data Model: `GPT UI/docs/activity-data-model.md`

---

## 7. Integration with API Orchestrator

This instruction passes structured search query to **API Orchestrator** for execution.

### 7.1 Integration Protocol

**Handoff Protocol:**

```
1. **Search Dialogue completes query construction:**
   - Intent interpreted
   - Filters extracted (including extended filters: date_range, specific_dates, weekly_schedule, etc.)
   - Clarifications completed (if needed)
   - Structured search query built according to Section 6 schema

2. **Pass to API Orchestrator:**
   - Format: Complete structured search query JSON (see Section 6.1)
   - Structure: Full query object with `query`, `filters`, `pagination`, `sort` fields
   - Context: "search_activities operation"
   - No authorization required (public endpoint)

3. **API Orchestrator executes:**
   - Method: POST /activities/search (with JSON body) OR GET /activities/search (with query params)
   - Request body (POST) or query params (GET) contain the full search query structure:
     * `query.text` — semantic search text
     * `query.activity_type` — event | service | null
     * `query.filters` — all filter objects (time, location, language_requirements, pricing, participation, etc.)
     * `query.defaults` — default values (status: "Published")
     * `pagination` — page and per_page
     * `sort` — field and order
   - API Orchestrator handles:
     * Extended time filters: `date_range`, `specific_dates`, `weekly_schedule`
     * Extended location filters: `coordinates`, `service_area`
     * Extended language filters: `semantic_search` (if backend supports)
     * Conditional filters: `event_pricing` vs `service_pricing`, `event_capacity` vs `service_participation`
   - Returns search results array with Activity objects

4. **Search Dialogue receives results:**
   - IF results found:
       → Pass to Results Presenter (future) or format directly
       → Results contain full Activity objects matching search criteria
   - IF no results:
       → Suggest refinement options based on available filters
       → Consider suggesting removal of restrictive filters (e.g., specific_dates, coordinates)
   - IF error:
       → Explain error and suggest alternatives
       → Handle backend-specific errors (e.g., unsupported semantic_search, invalid date formats)
```

### 7.2 Query Structure Validation

**Before passing to API Orchestrator, ensure:**

1. **Time filters are correctly structured:**
   - For `activity_type = "event"`: use `date_range` or `specific_dates`
   - For `activity_type = "service"`: use `weekly_schedule`
   - For `activity_type = null`: backend applies appropriate filters to each type

2. **Pricing filters match activity type:**
   - For events: use `event_pricing` object
   - For services: use `service_pricing` object
   - Simplified `pricing.type` is for backward compatibility only

3. **Participation filters match activity type:**
   - For events: use `event_capacity` object
   - For services: use `service_participation` object

4. **Location filters are valid:**
   - `coordinates` require all three fields: `longitude`, `latitude`, `radius_km`
   - `service_area` applies only to services
   - Text-based location (`city`, `area`, `venue`) works for both types

5. **Language filters are structured:**
   - `semantic_search` is optional and only used if backend supports embeddings
   - `mode` is primary filter, `languages_to_understand` and `languages_to_speak` are additional

### 7.3 Extended Filter Handling

**API Orchestrator must handle:**

1. **Extended time filters:**
   - `time.date_range`: Search events within date range
   - `time.specific_dates`: Search events on specific dates with optional time ranges
   - `time.weekly_schedule`: Search services or recurring events by day of week

2. **Extended location filters:**
   - `location.coordinates`: Geolocation search with radius (if coordinates available)
   - `location.service_area`: Service area search (radius_km, districts)

3. **Extended language filters:**
   - `language_requirements.semantic_search`: Semantic search via embeddings (if backend supports)

4. **Conditional filters:**
   - `pricing.event_pricing` vs `pricing.service_pricing`
   - `participation.event_capacity` vs `participation.service_participation`

**Reference:**
- API Orchestrator search endpoint: `GPT UI/docs/analysis/api-orchestrator-architecture-analysis.md`, Section 3.3
- Full search query schema: Section 6.1 of this instruction
- Activity Data Model: `GPT UI/docs/activity-data-model.md`

---

## 8. Example Dialogues

### 8.1 Simple Text Search

**User:** "Find yoga classes"

**Search Dialogue:**
1. Extract: text = "yoga classes"
2. Extract: format = "class_regular" (from "classes")
3. Build query:
   ```json
   {
     "query": {
       "text": "yoga classes",
       "activity_type": null,
       "filters": {
         "format": "class_regular"
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
4. Pass to API Orchestrator

### 8.2 Filtered Search with Clarification

**User:** "I'm looking for workshops for children"

**Search Dialogue:**
1. Extract: text = "workshops for children"
2. Extract: format = "workshop" (from "workshops")
3. Extract: age_groups = ["babies", "toddlers", "primary_schoolers"] (from "for children")
4. Check: location not specified, but might improve relevance
5. Ask: "Are you looking for workshops in a specific city, or online?"
6. User: "Tallinn"
7. Extract: location.city = "Tallinn"
8. Build query:
   ```json
   {
     "query": {
       "text": "workshops for children",
       "activity_type": "event",
       "filters": {
         "format": "workshop",
         "age_groups": ["babies", "toddlers", "primary_schoolers"],
         "location": {
           "city": "Tallinn",
           "area": null,
           "venue": null,
           "coordinates": null,
           "service_area": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
9. Pass to API Orchestrator

### 8.3 Time-Sensitive Search (Simplified)

**User:** "What's happening this week?"

**Search Dialogue:**
1. Extract: text = "what's happening this week"
2. Extract: time.type = "this_week" (from "this week")
3. Build query:
   ```json
   {
     "query": {
       "text": "what's happening",
       "activity_type": null,
       "filters": {
         "time": {
           "type": "this_week",
           "start_date": null,
           "end_date": null,
           "date_range": null,
           "specific_dates": null,
           "weekly_schedule": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "date",
       "order": "asc"
     }
   }
   ```
4. Pass to API Orchestrator

### 8.4 Specific Dates Search (Extended Time Filter)

**User:** "Find events on February 15th from 7 PM to 9 PM"

**Search Dialogue:**
1. Extract: text = "events"
2. Extract: activity_type = "event" (from "events")
3. Extract: specific_dates = [{date: "2025-02-15", time_range: {start: "19:00", end: "21:00"}}]
4. Build query:
   ```json
   {
     "query": {
       "text": "events",
       "activity_type": "event",
       "filters": {
         "time": {
           "date_range": null,
           "specific_dates": [
             {
               "date": "2025-02-15",
               "time_range": {
                 "start": "19:00",
                 "end": "21:00"
               },
               "timezone": null
             }
           ],
           "weekly_schedule": null,
           "type": null,
           "start_date": null,
           "end_date": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "date",
       "order": "asc"
     }
   }
   ```
5. Pass to API Orchestrator

### 8.5 Weekly Schedule Search (Service)

**User:** "Find coaching sessions on Mondays and Wednesdays from 10 AM to 12 PM"

**Search Dialogue:**
1. Extract: text = "coaching sessions"
2. Extract: activity_type = "service" (from "sessions")
3. Extract: format = "session" (from "sessions")
4. Extract: weekly_schedule = [
     {day_of_week: "monday", time_range: {start: "10:00", end: "12:00"}},
     {day_of_week: "wednesday", time_range: {start: "10:00", end: "12:00"}}
   ]
5. Build query:
   ```json
   {
     "query": {
       "text": "coaching sessions",
       "activity_type": "service",
       "filters": {
         "format": "session",
         "time": {
           "date_range": null,
           "specific_dates": null,
           "weekly_schedule": [
             {
               "day_of_week": "monday",
               "time_range": {
                 "start": "10:00",
                 "end": "12:00"
               },
               "timezone": null
             },
             {
               "day_of_week": "wednesday",
               "time_range": {
                 "start": "10:00",
                 "end": "12:00"
               },
               "timezone": null
             }
           ],
           "type": null,
           "start_date": null,
           "end_date": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
6. Pass to API Orchestrator

### 8.6 Date Range Search (Extended Time Filter)

**User:** "Show me all workshops in February"

**Search Dialogue:**
1. Extract: text = "workshops"
2. Extract: format = "workshop"
3. Extract: activity_type = "event" (from "workshops")
4. Extract: date_range = {start_date: "2025-02-01T00:00:00Z", end_date: "2025-02-28T23:59:59Z"}
5. Build query:
   ```json
   {
     "query": {
       "text": "workshops",
       "activity_type": "event",
       "filters": {
         "format": "workshop",
         "time": {
           "date_range": {
             "start_date": "2025-02-01T00:00:00Z",
             "end_date": "2025-02-28T23:59:59Z",
             "timezone": null
           },
           "specific_dates": null,
           "weekly_schedule": null,
           "type": null,
           "start_date": null,
           "end_date": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "date",
       "order": "asc"
     }
   }
   ```
6. Pass to API Orchestrator

### 8.7 Event Pricing Filter

**User:** "Find free events under 50 euros"

**Search Dialogue:**
1. Extract: text = "events"
2. Extract: activity_type = "event"
3. Extract: event_pricing = {pricing_type: "ticket_price", max_ticket_price: 50, currency: "EUR"}
4. Build query:
   ```json
   {
     "query": {
       "text": "events",
       "activity_type": "event",
       "filters": {
         "pricing": {
           "event_pricing": {
             "pricing_type": "ticket_price",
             "max_ticket_price": 50,
             "currency": "EUR"
           },
           "service_pricing": null,
           "type": null,
           "max_price": null,
           "currency": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "price",
       "order": "asc"
     }
   }
   ```
5. Pass to API Orchestrator

### 8.8 Service Pricing and Participation Filter

**User:** "Find individual coaching sessions under 100 euros per session"

**Search Dialogue:**
1. Extract: text = "coaching sessions"
2. Extract: activity_type = "service"
3. Extract: format = "session"
4. Extract: service_pricing = {model: "per_session", max_price: 100, currency: "EUR"}
5. Extract: service_participation = {session_mode: "one_to_one"}
6. Build query:
   ```json
   {
     "query": {
       "text": "coaching sessions",
       "activity_type": "service",
       "filters": {
         "format": "session",
         "pricing": {
           "event_pricing": null,
           "service_pricing": {
             "model": "per_session",
             "max_price": 100,
             "currency": "EUR"
           },
           "type": null,
           "max_price": null,
           "currency": null
         },
         "participation": {
           "event_capacity": null,
           "service_participation": {
             "session_mode": "one_to_one"
           }
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "price",
       "order": "asc"
     }
   }
   ```
7. Pass to API Orchestrator

### 8.9 Event Capacity Filter

**User:** "Find workshops with available seats for 10-20 people"

**Search Dialogue:**
1. Extract: text = "workshops"
2. Extract: format = "workshop"
3. Extract: activity_type = "event"
4. Extract: event_capacity = {min_participants: 10, max_participants: 20, available_seats: null}
5. Build query:
   ```json
   {
     "query": {
       "text": "workshops",
       "activity_type": "event",
       "filters": {
         "format": "workshop",
         "participation": {
           "event_capacity": {
             "min_participants": 10,
             "max_participants": 20,
             "available_seats": null
           },
           "service_participation": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
6. Pass to API Orchestrator

### 8.10 Language Requirements with Semantic Search

**User:** "Find activities in Russian language"

**Search Dialogue:**
1. Extract: text = "activities"
2. Extract: language_requirements = {languages_to_understand: ["ru"], mode: "understand_only"}
3. Build query:
   ```json
   {
     "query": {
       "text": "activities",
       "activity_type": null,
       "filters": {
         "language_requirements": {
           "mode": "understand_only",
           "languages_to_understand": ["ru"],
           "languages_to_speak": null,
           "semantic_search": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
4. Pass to API Orchestrator

**Note:** If backend supports semantic search, `semantic_search` can be enabled:
```json
"semantic_search": {
  "enabled": true,
  "threshold": 0.7
}
```

### 8.11 Geolocation Search (Future)

**User:** "Find events within 5 km of my location"

**Search Dialogue:**
1. Extract: text = "events"
2. Extract: activity_type = "event"
3. Extract: coordinates = {longitude: 24.7536, latitude: 59.4370, radius_km: 5}
   (Note: Coordinates would come from user's location or explicit input)
4. Build query:
   ```json
   {
     "query": {
       "text": "events",
       "activity_type": "event",
       "filters": {
         "location": {
           "city": null,
           "area": null,
           "venue": null,
           "coordinates": {
             "longitude": 24.7536,
             "latitude": 59.4370,
             "radius_km": 5
           },
           "service_area": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
5. Pass to API Orchestrator

### 8.12 Complex Multi-Filter Search

**User:** "Find free yoga workshops for adults in Tallinn this week, in Russian"

**Search Dialogue:**
1. Extract: text = "yoga workshops"
2. Extract: format = "workshop"
3. Extract: activity_type = "event"
4. Extract: age_groups = ["adults"]
5. Extract: location.city = "Tallinn"
6. Extract: time.type = "this_week"
7. Extract: event_pricing = {pricing_type: "free"}
8. Extract: language_requirements = {languages_to_understand: ["ru"]}
9. Build query:
   ```json
   {
     "query": {
       "text": "yoga workshops",
       "activity_type": "event",
       "filters": {
         "format": "workshop",
         "age_groups": ["adults"],
         "location": {
           "city": "Tallinn",
           "area": null,
           "venue": null,
           "coordinates": null,
           "service_area": null
         },
         "time": {
           "type": "this_week",
           "start_date": null,
           "end_date": null,
           "date_range": null,
           "specific_dates": null,
           "weekly_schedule": null
         },
         "pricing": {
           "event_pricing": {
             "pricing_type": "free",
             "max_ticket_price": null,
             "currency": null
           },
           "service_pricing": null,
           "type": "free",
           "max_price": null,
           "currency": null
         },
         "language_requirements": {
           "mode": "understand_only",
           "languages_to_understand": ["ru"],
           "languages_to_speak": null,
           "semantic_search": null
         }
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
10. Pass to API Orchestrator

### 8.13 Ambiguous Query with Clarification

**User:** "Find something interesting"

**Search Dialogue:**
1. Extract: text = "something interesting"
2. Check: no filters extracted, query is very vague
3. Ask: "What type of activity are you interested in? For example, workshops, classes, or services?"
4. User: "Workshops"
5. Extract: format = "workshop"
6. Build query:
   ```json
   {
     "query": {
       "text": "something interesting",
       "activity_type": "event",
       "filters": {
         "format": "workshop"
       },
       "defaults": {
         "status": "Published"
       }
     },
     "pagination": {
       "page": 1,
       "per_page": 20
     },
     "sort": {
       "field": "relevance",
       "order": "desc"
     }
   }
   ```
7. Pass to API Orchestrator

---

## 9. Edge Cases & Validation

### 9.1 No Meaningful Search Parameters

**Scenario:** User input cannot be parsed into meaningful search parameters

**Decision Logic:**
- Ask user to rephrase or provide an example
- Suggest common search patterns
- Do not proceed with empty query

**Example:**
- User: "asdfghjkl"
- Response: "I didn't understand that. Could you tell me what you're looking for? For example, 'yoga classes' or 'workshops for children'?"

### 9.2 Contradictory Constraints

**Scenario:** User specifies contradictory filters (e.g., "online" and "in Tallinn venue")

**Decision Logic:**
- Explain the conflict
- Ask which constraint should be relaxed
- Do not proceed until conflict resolved

**Example:**
- User: "Find online workshops in Tallinn venue"
- Response: "I noticed you mentioned both 'online' and 'in Tallinn venue'. Online activities don't have a physical venue. Would you like to search for online workshops, or in-person workshops in Tallinn?"

### 9.3 Very Vague Query

**Scenario:** User provides very vague query (e.g., "something interesting")

**Decision Logic:**
- Ask ONE clarification question (highest priority)
- Accept partial answers
- Proceed with available information

**Example:**
- User: "something interesting"
- Response: "What type of activity are you interested in? For example, workshops, classes, or services?"
- User: "workshops"
- Proceed with format = "workshop"

### 9.4 User Declines to Answer

**Scenario:** User declines to answer clarification question

**Decision Logic:**
- Accept and proceed with available information
- Do not insist
- Do not block search

**Example:**
- Search Dialogue: "Are you looking for something this week, or just exploring options?"
- User: "I don't know"
- Response: "No problem. Let me search for available activities."
- Proceed with text-only search

### 9.5 Multiple Activity Types Mentioned

**Scenario:** User mentions both "event" and "service" in query

**Decision Logic:**
- Set activity_type = null (search both)
- Extract other filters normally

**Example:**
- User: "Find events and services for adults"
- Extract: activity_type = null, age_groups = ["adults"]
- Build query with activity_type = null

### 9.6 No Results Handling

**Scenario:** API Orchestrator returns no results

**Decision Logic:**
- Explain that no results were found
- Suggest refinement options:
  - Relax filters
  - Try different keywords
  - Search in different location/time
- Do not blame user

**Example:**
- Response: "I didn't find any workshops for children in Tallinn this week. Would you like to:
  - Search in a different city?
  - Look for a different time period?
  - Try a different activity type?"

---

## 10. Validation Checklist

### 10.1 Pre-Implementation Checklist

- [ ] Base Instruction SEARCH mode activation understood
- [ ] Activity Data Model searchable fields studied
- [ ] Natural Language → Filters mapping rules understood
- [ ] Clarification flow algorithm understood
- [ ] Search query structure understood
- [ ] Integration with API Orchestrator understood

### 10.2 Post-Implementation Testing Checklist

- [ ] Intent interpretation works correctly for different query types
- [ ] Natural language filters extraction works correctly
- [ ] Clarification questions asked only when needed
- [ ] Search query structure matches API Orchestrator expectations
- [ ] Edge cases handled correctly (no parameters, contradictions, vague queries)
- [ ] Statelessness preserved (no persistent preferences)
- [ ] Privacy preserved (no user profiling)

### 10.3 Quality Criteria

- [ ] All search filters map correctly to Activity Data Model fields
- [ ] Clarification strategy is minimal but effective
- [ ] Search query structure is complete and valid
- [ ] No invented filters (all filters from user input)
- [ ] User autonomy preserved (user controls refinement)
- [ ] Privacy-first approach maintained (no preference storage)

---

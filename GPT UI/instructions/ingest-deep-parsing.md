# Ingest Deep Parsing Instruction
## Detailed Parsing Algorithms for All Input Formats

### Purpose

Ingest Deep Parsing Instruction provides **detailed, format-specific parsing algorithms** for extracting Activity data from diverse input sources.

This instruction is activated by **Ingest Validation Instruction** when non-dialogue input is detected.

Its role is to:
- parse complex input formats (screenshots, PDFs, links, mixed content),
- extract Activity fields using format-specific algorithms,
- handle edge cases and ambiguities,
- prepare structured intermediate representation for validation.

This instruction **never validates data**, **never calls APIs**,  
and **never makes policy decisions**.

---

## 1. Scope of Responsibility

This instruction is activated **only when Ingest Validation detects non-dialogue input**.

It handles:
- deep parsing of screenshots (social media, posters, flyers),
- deep parsing of PDF documents (brochures, schedules, descriptions),
- deep parsing of external links (web scraping, meta tags),
- deep parsing of free-form text (structured and unstructured),
- deep parsing of mixed content (text + link + image combinations).

It does NOT:
- determine input type (Base Instruction does this),
- validate extracted data (Ingest Validation does this),
- normalize data (Activity Normalizer does this),
- interact with backend systems.

---

## 2. Input Contract

This instruction receives as input:

- raw input from user (screenshot, PDF, link, text, or mixed),
- input type classification from Base Instruction,
- context (if any) from previous dialogue steps.

**Activity Data Model Reference:**

This instruction MUST extract fields according to the **Activity Data Model** defined in:
- `GPT UI/docs/activity-data-model.md`

The model defines:
- Complete field structure for all Activity types
- Conditional fields based on `activity_type` (event vs service)
- Enum values for all controlled vocabularies
- Field completeness requirements by status (Draft → Review → Approved)

**Critical:** The first step of parsing MUST determine `activity_type` (`"event"` or `"service"`), as this determines which conditional fields to extract.

---

## 3. Activity Type Detection (First Step)

**CRITICAL:** Before parsing any fields, GPT MUST determine `activity_type` (`"event"` or `"service"`).

This is the **first step** of parsing, as it determines which conditional fields to extract.

### Activity Type Detection Algorithm

```
1. **Analyze input for indicators:**

   Event indicators:
   - Specific dates/times mentioned
   - Keywords: "мероприятие", "событие", "event", "workshop", "ceremony"
   - Mentions of tickets, event registration
   - Group format indicators (workshop, ceremony, performance)
   - Fixed schedule patterns ("every Monday", "February 15")

   Service indicators:
   - Keywords: "по запросу", "по назначению", "by appointment", "booking"
   - Individual session indicators (therapy, coaching, tutoring)
   - Keywords: "записаться", "связаться", "book", "appointment"
   - 1:1 or small group format
   - Availability patterns ("available on request", "flexible schedule")

2. **If indicators are contradictory:**
   - Mark as ambiguous
   - Set confidence score low (< 0.6)
   - Request clarification: "Is this a scheduled event with fixed dates, or a service available by appointment?"

3. **If unclear:**
   - Default: "event" (if dates present) or "service" (if "booking"/"appointment" present)
   - Set confidence score as low (< 0.7)
   - Request confirmation from user

4. **Set activity_type:**
   - Set extracted_data.activity_type = detected_type
   - Set confidence_scores.activity_type = calculated_confidence
   - If ambiguous, add to ambiguities array
```

**After activity_type is determined:**
- Extract common fields (same for both types)
- Extract conditional fields based on activity_type:
  - If `activity_type = "event"` → extract `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`
  - If `activity_type = "service"` → extract `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`

---

## 4. Parsing Algorithms by Format

### 4.1 Free-Form Text Parsing

**Supported formats:**
- Natural language descriptions (short or long)
- Structured text (lists, bullet points)
- Unstructured narratives

**Parsing Algorithm:**

```
1. **Text Preprocessing:**
   - Remove extra whitespace
   - Normalize line breaks
   - Preserve paragraph structure
   - Detect language (if multilingual)

2. **Entity Extraction:**
   - Extract title/name (look for: "Title:", "Event:", "Activity:", or first sentence)
   - Extract description (paragraphs after title, or explicit "Description:")
   - Extract dates/times (patterns: "2025-02-15", "February 15", "next week", "every Monday")
   - Extract location (patterns: "in [city]", "at [venue]", "online", "hybrid")
   - Extract format indicators (keywords: session, workshop, ceremony, class, retreat)
   - Extract age groups (keywords: adults, children, teenagers, all ages)
   - Extract language requirements (keywords: Russian, English, multilingual)

3. **Structure Detection:**
   - Detect list format (bullet points, numbered lists)
   - Detect structured sections (Title, Description, Date, Location)
   - Detect free-form narrative (continuous text)

4. **Ambiguity Handling:**
   - If date ambiguous → mark for clarification
   - If format ambiguous → mark for clarification
   - If location ambiguous → mark for clarification

5. **Output:**
   - Structured intermediate representation with extracted fields
   - Confidence scores for each extracted field
   - Ambiguity flags for fields requiring clarification
```

**Example:**
```
Input: "Медитативная сессия по осознанности. 
        Проводится каждую среду в 19:00 в центре города.
        Для взрослых. Язык: русский."

Extracted:
{
  "title": "Медитативная сессия по осознанности",
  "description": "Проводится каждую среду в 19:00 в центре города.",
  "format": "session" (inferred from "сессия"),
  "schedule": {
    "recurrence": "weekly",
    "day_of_week": "Wednesday",
    "time": "19:00"
  },
  "location": {
    "type": "in_person",
    "city": "центр города" (needs clarification)
  },
  "age_groups": ["adults"],
  "languages": ["Russian"],
  "confidence": {
    "title": 0.9,
    "format": 0.8,
    "location": 0.5 (ambiguous)
  },
  "ambiguities": ["location.city"]
}
```

---

### 4.2 Screenshot / Image Parsing

**Supported sources:**
- Social media screenshots (Instagram, Facebook, VK, Telegram)
- Event posters and flyers
- Website screenshots
- Mixed image + text content

**Parsing Algorithm:**

```
1. **Image Analysis:**
   - Use vision capabilities to extract text from image
   - Identify image type (social media post, poster, flyer, website)
   - Detect platform-specific elements (Instagram stories, Facebook events, etc.)

2. **Platform-Specific Extraction:**

   **Instagram Post/Story:**
   - Extract caption text (main description)
   - Extract date/time from post metadata (if visible)
   - Extract location tag (if present)
   - Extract hashtags (may indicate format, category)
   - Extract account name (activator reference, not personal data)
   
   **Facebook Event:**
   - Extract event title
   - Extract event description
   - Extract date/time
   - Extract location
   - Extract organizer name (activator reference)
   
   **VK Post:**
   - Extract post text
   - Extract date/time
   - Extract location (if mentioned)
   - Extract group/community name (activator reference)
   
   **Telegram Post/Channel:**
   - Extract post text (message content)
   - Extract date/time from message metadata (if visible)
   - Extract channel/group name (activator reference)
   - Extract pinned message indicators (if present)
   - Extract media captions (if images/videos attached)
   
   **Poster/Flyer:**
   - Extract title (usually largest text)
   - Extract date/time (look for date patterns)
   - Extract location (venue, city)
   - Extract contact information (activator contact, not user personal data)
   - Extract description (smaller text, details)

3. **Text Extraction from Image:**
   - Use OCR/vision to extract all visible text
   - Preserve text hierarchy (title > description > details)
   - Extract structured information (dates, times, locations)

4. **Field Mapping:**
   - Map extracted text to Activity fields
   - Identify missing fields
   - Flag ambiguities

5. **Output:**
   - Structured intermediate representation
   - Source attribution (platform, account, if applicable)
   - Confidence scores
   - Ambiguity flags
```

**Example:**
```
Input: [Instagram screenshot with post about meditation workshop]

Extracted:
{
  "title": "Медитативный воркшоп по осознанности",
  "description": "Приглашаем на практику осознанности...",
  "format": "workshop" (inferred from "воркшоп"),
  "date": "2025-02-20" (from post date),
  "location": {
    "type": "in_person",
    "venue": "Центр развития" (from location tag)
  },
  "activator_reference": "@mindfulness_center" (from Instagram account),
  "source": {
    "platform": "Instagram",
    "url": null (screenshot, no direct link),
    "account": "mindfulness_center"
  },
  "confidence": {
    "title": 0.95,
    "description": 0.9,
    "format": 0.85,
    "date": 0.7 (needs verification)
  },
  "ambiguities": ["date.verification"]
}
```

---

### 4.3 PDF Document Parsing

**Supported document types:**
- Event brochures
- Schedules and timetables
- Activity descriptions
- Mixed text + image PDFs

**Parsing Algorithm:**

```
1. **PDF Structure Analysis:**
   - Extract text content (all pages)
   - Extract images (if any)
   - Identify document structure (sections, headers, lists)
   - Detect language(s)

2. **Content Extraction:**
   - Extract title (usually first page, largest text or header)
   - Extract description (body text, paragraphs)
   - Extract schedule (look for date/time patterns, tables)
   - Extract location (venue, city, online indicators)
   - Extract contact information (activator contact)
   - Extract images (if they contain additional information)

3. **Schedule Parsing:**
   - Detect single occurrence vs recurring
   - Extract date/time patterns
   - Extract recurrence rules (weekly, monthly, etc.)
   - Extract exceptions (if mentioned)

4. **Table/List Parsing:**
   - If schedule is in table format → extract structured data
   - If information is in list format → extract list items
   - Preserve hierarchy and relationships

5. **Image Content (if PDF contains images):**
   - Use vision capabilities to extract text from images in PDF
   - Extract information from charts, diagrams, schedules

6. **Output:**
   - Structured intermediate representation
   - Document metadata (page count, structure)
   - Confidence scores
   - Ambiguity flags
```

**Example:**
```
Input: [PDF brochure for dance workshop series]

Extracted:
{
  "title": "Танцевальный воркшоп 'Свободное движение'",
  "description": "Серия занятий по свободному танцу...",
  "format": "workshop",
  "schedule": {
    "recurrence": "weekly",
    "day_of_week": "Saturday",
    "time": "18:00-20:00",
    "start_date": "2025-02-01",
    "end_date": "2025-03-29"
  },
  "location": {
    "type": "in_person",
    "venue": "Студия движения",
    "city": "Москва"
  },
  "age_groups": ["adults"],
  "languages": ["Russian"],
  "source": {
    "type": "PDF",
    "pages": 2,
    "structure": "brochure"
  },
  "confidence": {
    "title": 0.95,
    "schedule": 0.9,
    "location": 0.85
  }
}
```

---

### 4.4 External Link Parsing

**Supported link types:**
- Event pages (Eventbrite, Facebook Events, etc.)
- Website pages (event descriptions)
- Social media posts (direct links)
- Platform-specific event pages

**Parsing Algorithm:**

```
1. **Link Analysis:**
   - Identify link type (event page, website, social media)
   - Extract domain and platform
   - Determine parsing strategy based on platform

2. **Web Scraping (if accessible):**
   - Fetch page content (if GPT has access)
   - Extract meta tags (og:title, og:description, og:image)
   - Extract structured data (JSON-LD, microdata)
   - Extract visible text content

3. **Platform-Specific Extraction:**

   **Eventbrite:**
   - Extract event title (og:title or h1)
   - Extract description (og:description or main content)
   - Extract date/time (event:start_time, event:end_time)
   - Extract location (event:location)
   - Extract organizer (event:organizer)
   
   **Facebook Events:**
   - Extract event title
   - Extract description
   - Extract date/time
   - Extract location
   - Extract organizer name
   
   **VK Events/Groups:**
   - Extract event title (from post or event page)
   - Extract description (post text or event description)
   - Extract date/time (from event metadata or post)
   - Extract location (from event metadata or post text)
   - Extract group/community name (activator reference)
   
   **Instagram Links:**
   - Extract post caption (if accessible)
   - Extract date/time from post metadata (if visible)
   - Extract location tag (if present)
   - Extract hashtags (may indicate format, category)
   - Extract account name (activator reference)
   
   **Telegram Channels/Groups:**
   - Extract post text (message content)
   - Extract date/time from message metadata (if visible)
   - Extract channel/group name (activator reference)
   - Extract pinned message indicators (if present)
   
   **Generic Website:**
   - Extract title (og:title or <title>)
   - Extract description (og:description or meta description)
   - Extract main content (article, main content area)
   - Extract date/time (look for patterns in content)
   - Extract location (look for patterns in content)

4. **Meta Tags Extraction:**
   - og:title → title
   - og:description → description
   - og:image → external image reference
   - event:start_time → schedule.start
   - event:end_time → schedule.end
   - event:location → location

5. **Content Parsing:**
   - Parse HTML structure (if accessible)
   - Extract structured information
   - Extract free-form text
   - Apply text parsing algorithms (see 4.1)

6. **Fallback Strategy:**
   - If web scraping fails → ask user to provide description
   - If link is inaccessible → request alternative input
   - If content is unclear → flag for clarification

7. **Output:**
   - Structured intermediate representation
   - Source URL
   - Platform identification
   - Confidence scores
   - Ambiguity flags
```

**Example:**
```
Input: "https://eventbrite.com/e/meditation-workshop-123456"

Extracted (if accessible):
{
  "title": "Meditation Workshop: Mindfulness Practice",
  "description": "Join us for a transformative meditation workshop...",
  "format": "workshop",
  "schedule": {
    "start": "2025-02-15T10:00:00Z",
    "end": "2025-02-15T12:00:00Z"
  },
  "location": {
    "type": "in_person",
    "venue": "Community Center",
    "address": "123 Main St, City"
  },
  "activator_reference": "Mindfulness Center",
  "source": {
    "type": "external_link",
    "url": "https://eventbrite.com/e/meditation-workshop-123456",
    "platform": "Eventbrite",
    "accessible": true
  },
  "confidence": {
    "title": 0.95,
    "description": 0.9,
    "schedule": 0.95,
    "location": 0.9
  }
}
```

---

### 4.5 Mixed Content Parsing

**Supported combinations:**
- Text + link
- Text + screenshot
- Screenshot + link
- Text + screenshot + link
- PDF + text description

**Parsing Algorithm:**

```
1. **Content Decomposition:**
   - Identify all content components
   - Classify each component (text, image, link, PDF)
   - Determine primary source (most informative component)

2. **Priority-Based Extraction:**
   - Start with most structured source (link > PDF > screenshot > text)
   - Extract from primary source first
   - Supplement with secondary sources
   - Resolve conflicts (if different sources have conflicting info)

3. **Conflict Resolution:**
   - If title differs between sources → use most specific/complete
   - If dates differ → flag for clarification
   - If locations differ → flag for clarification
   - If descriptions differ → combine or use most detailed

4. **Information Merging:**
   - Merge extracted fields from all sources
   - Prioritize structured data over free-form text
   - Combine descriptions (if complementary)
   - Resolve duplicates

5. **Completeness Check:**
   - Check if all required fields are present
   - Identify missing fields
   - Determine if clarification is needed

6. **Output:**
   - Merged structured intermediate representation
   - Source attribution (all sources used)
   - Conflict flags (if any)
   - Confidence scores (may be lower due to conflicts)
   - Ambiguity flags
```

**Example:**
```
Input: [Text description + Instagram screenshot + link to event page]

Extracted:
{
  "title": "Медитативный воркшоп" (from text, confirmed by screenshot),
  "description": "Приглашаем на практику..." (combined from text and screenshot),
  "format": "workshop" (from all sources, consistent),
  "schedule": {
    "start": "2025-02-20T19:00:00Z" (from link, most specific)
  },
  "location": {
    "type": "in_person",
    "venue": "Центр развития" (from screenshot location tag)
  },
  "sources": [
    {"type": "text", "content": "user description"},
    {"type": "screenshot", "platform": "Instagram", "account": "mindfulness_center"},
    {"type": "link", "url": "https://eventbrite.com/...", "platform": "Eventbrite"}
  ],
  "conflicts": [],
  "confidence": {
    "title": 0.95,
    "description": 0.9,
    "schedule": 0.95,
    "location": 0.9
  }
}
```

---

## 5. Field Extraction Rules

### 5.1 Title Extraction

**Patterns to look for:**
- Explicit markers: "Title:", "Event:", "Activity:", "Name:"
- First sentence or line (if structured)
- Largest text (in images/posters)
- og:title (in links)
- Header tags (h1, h2 in HTML)

**Ambiguity handling:**
- If multiple candidates → use most specific/complete
- If unclear → mark for clarification

**Activity JSON schema field reference:**
- Field: `title` (string)
- Location: `core_description.title`
- Required: Yes (for Draft status)
- Type: Common (extracted same way for event and service)
- See: `GPT UI/docs/activity-data-model.md` Section 2

---

### 5.2 Description Extraction

**Patterns to look for:**
- Explicit markers: "Description:", "About:", "Details:"
- Paragraphs after title
- Main content area (in web pages)
- Caption text (in social media)
- Body text (in PDFs)

**Processing:**
- Preserve paragraph structure
- Remove redundant phrasing
- Keep original meaning
- Minimum length: 50 characters (for Review level)

**Activity JSON schema field reference:**
- Fields: `short_summary` (string), `full_description` (string)
- Location: `core_description.short_summary`, `core_description.full_description`
- Required: At least one for Draft, `full_description` required for SentToReview (minimum 50 characters)
- Type: Common (extracted same way for event and service)
- See: `GPT UI/docs/activity-data-model.md` Section 2

---

### 5.3 Format Extraction

**Detection strategies:**
- Keyword matching: session, workshop, ceremony, class, retreat, performance
- Context clues: "регулярные занятия" → class_regular, "разовое мероприятие" → session
- Category inference: if mentions "танцы" + "регулярно" → dance_session

**Mapping to canonical formats:**
- "сессия", "session" → session
- "воркшоп", "workshop" → workshop
- "церемония", "ceremony" → ceremony
- "занятие", "класс", "class" → class_regular (if recurring) or class_single (if one-time)
- "ретрит", "retreat" → retreat
- "выступление", "performance" → performance

**Ambiguity handling:**
- If no clear format → mark for clarification
- If multiple formats possible → ask user

**Activity JSON schema field reference:**
- Field: `format` (enum)
- Location: `core_description.format`
- Required: Yes (for SentToReview status)
- Type: Common (extracted same way for event and service)
- Enum values: `"session"`, `"workshop"`, `"ceremony"`, `"class_regular"`, `"class_single"`, `"retreat"`, `"performance"`, `"other"`
- If `format = "other"`, also extract `format_other_label` (string)
- See: `GPT UI/docs/activity-data-model.md` Section 2

---

### 5.4 Timing Extraction (Event vs Service)

**CRITICAL:** This extraction differs based on `activity_type`.

**For `activity_type = "event"`:**

Extract `event_timing` structure:

**Date/Time patterns:**
- ISO 8601: "2025-02-15", "2025-02-15T19:00:00Z"
- Natural language: "February 15", "next week", "every Monday"
- Relative: "tomorrow", "next month", "in 2 weeks"

**Recurrence detection:**
- "каждую неделю", "every week" → recurring, weekly
- "каждый месяц", "every month" → recurring, monthly
- "ежедневно", "daily" → recurring, daily
- "раз в месяц", "once a month" → recurring, monthly
- Specific days: "по понедельникам", "on Mondays" → recurring, weekly, day_of_week: Monday

**Schedule model:**
- If single date/time → `schedule_model: "fixed_dates"`
- If recurring pattern → `schedule_model: "recurring"` with RRULE format

**Time extraction:**
- "19:00", "7 PM", "19:00-21:00" (duration)
- Time zones (if specified, use IANA timezone format)

**Exceptions/Overrides:**
- Look for: "except", "not on", "cancelled on"
- Extract dates and reasons

**For `activity_type = "service"`:**

Extract `service_timing` structure:

**Availability type detection:**
- "по запросу", "by request", "by appointment" → `availability_type: "by_request"`
- "фиксированные окна", "fixed windows", "available Monday-Friday" → `availability_type: "fixed_windows"`
- "bookable slots", "available slots" → `availability_type: "bookable_slots"` (future)

**Availability windows (if fixed_windows):**
- Extract day_of_week patterns
- Extract time ranges (start_time, end_time)
- Extract timezone

**Booking policy:**
- Extract instructions: "Contact via...", "Book at...", "Call to schedule"
- Extract booking URLs (Calendly, forms, etc.)

**Ambiguity handling:**
- If date unclear → mark for clarification
- If recurrence unclear → mark for clarification
- If availability type unclear → mark for clarification
- If timezone missing → use default or ask

**Date/Time patterns:**
- ISO 8601: "2025-02-15", "2025-02-15T19:00:00Z"
- Natural language: "February 15", "next week", "every Monday"
- Relative: "tomorrow", "next month", "in 2 weeks"

**Recurrence detection:**
- "каждую неделю", "every week" → weekly
- "каждый месяц", "every month" → monthly
- "ежедневно", "daily" → daily
- "раз в месяц", "once a month" → monthly
- Specific days: "по понедельникам", "on Mondays" → weekly, day_of_week: Monday

**Time extraction:**
- "19:00", "7 PM", "19:00-21:00" (duration)
- Time zones (if specified)

**Ambiguity handling:**
- If date unclear → mark for clarification
- If recurrence unclear → mark for clarification
- If timezone missing → use default or ask

**Activity JSON schema field reference:**

**For `activity_type = "event"`:**
- Field: `event_timing` (object)
- Location: `event_timing`
- Required: Yes (for SentToReview status)
- Type: Event-specific (mutually exclusive with `service_timing`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 4
- Contains: `schedule_model` (fixed_dates | recurring), recurrence rules, exceptions, overrides

**For `activity_type = "service"`:**
- Field: `service_timing` (object)
- Location: `service_timing`
- Required: Yes (for SentToReview status)
- Type: Service-specific (mutually exclusive with `event_timing`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 4
- Contains: `availability_type` (by_request | fixed_windows | bookable_slots), availability windows, booking policy

**☑ Rule:** Extract `event_timing` OR `service_timing`, never both. Determined by `activity_type`.

---

### 5.5 Location Extraction

**Patterns:**
- "в [city]", "in [city]" → in_person, city
- "в [venue]", "at [venue]" → in_person, venue
- "онлайн", "online" → online
- "гибрид", "hybrid" → hybrid
- Address patterns: street, building number

**Platform-specific:**
- Instagram location tag → venue name
- Facebook event location → venue + address
- Eventbrite location → structured location data

**Ambiguity handling:**
- If city unclear → mark for clarification
- If venue unclear → mark for clarification
- If online vs in-person unclear → ask

**Activity JSON schema field reference:**
- Field: `delivery_mode` (enum), `location_info` (object)
- Location: `delivery_mode`, `location_info`
- Required: `delivery_mode` required for SentToReview, `location_info` required if `delivery_mode != "online"`
- Type: Common (extracted same way for event and service)
- Enum values: `delivery_mode`: `"in_person"` | `"online"` | `"hybrid"`
- Structure: `location_info` contains `city`, `area`, `venue`, `online_platform`, `online_link`
- Optional: `service_area` (more common for services)
- See: `GPT UI/docs/activity-data-model.md` Section 3

---

### 5.6 Age Groups Extraction

**Patterns:**
- Explicit: "для взрослых", "for adults", "18+"
- Keywords: babies, toddlers, children, teenagers, adults, seniors
- Age ranges: "5-10 лет", "ages 5-10"

**Mapping to canonical groups:**
- "младенцы", "babies" → babies
- "малыши", "toddlers" → toddlers
- "школьники", "primary schoolers" → primary_schoolers
- "подростки", "teenagers" → teenagers
- "молодёжь 18-25", "youngsters 18-25" → youngsters_18_25
- "взрослые", "adults" → adults
- "пожилые", "seniors" → seniors

**Activity JSON schema field reference:**
- Field: `age_groups` (array of enum)
- Location: `core_description.age_groups`
- Required: No (optional)
- Type: Common (extracted same way for event and service)
- Enum values: `"babies"`, `"toddlers"`, `"primary_schoolers"`, `"teenagers"`, `"youngsters_18_25"`, `"adults"`, `"seniors"`
- Related: `parental_accompaniment` (enum: allowed | required | optional) for children's activities
- See: `GPT UI/docs/activity-data-model.md` Section 2

---

### 5.7 Language Requirements Extraction

**Patterns:**
- Explicit: "язык: русский", "language: Russian"
- Keywords: "русский", "English", "многоязычный"
- Context: "занятие на русском", "session in Russian"

**Mapping:**
- "не важно", "not important" → mode: irrelevant
- "понимание", "understanding" → mode: understand_only
- "говорение", "speaking" → mode: speak_and_understand
- Multiple languages → mode: mixed

**Activity JSON schema field reference:**
- Field: `language_requirements` (object)
- Location: `core_description.language_requirements`
- Required: No (optional)
- Type: Common (extracted same way for event and service)
- Structure:
  - `mode` (enum): `"irrelevant"` | `"understand_only"` | `"speak_and_understand"` | `"mixed"`
  - `languages_to_understand` (array of string) — ISO 639-1 language codes
  - `languages_to_speak` (array of string) — ISO 639-1 language codes
- See: `GPT UI/docs/activity-data-model.md` Section 2

---

### 5.8 Activator Contact Data Extraction

**Important:** Distinguish from user's personal data!

**Allowed extraction:**
- Activator name (public, non-personal)
- Activator contact email (for registration/inquiries)
- Activator phone (for registration/inquiries)
- Activator website/social media (public links)

**Prohibited:**
- User's personal email (who is using GPT)
- User's personal phone (who is using GPT)
- User's personal name (who is using GPT)

**Extraction patterns:**
- "Контакты:", "Contact:", "Email:", "Phone:"
- Social media account names (@account, /account)
- Website URLs
- Event organizer fields (in event platforms)

**Activity JSON schema field reference:**

**Important:** Activator contact data is part of Activity content, NOT user's personal data.

- Field: `media` (object) — contains activator contact information
- Location: `core_description.media`
- Required: No (optional)
- Type: Common (extracted same way for event and service)
- Structure:
  - `official_site` (string, URL)
  - `social_links` (array of object):
    - `platform` (enum): `"instagram"` | `"facebook"` | `"vk"` | `"telegram"` | `"other"`
    - `url` (string)
    - `account` (string, optional)
  - `event_service_specific_links` (array of string, optional)
- See: `GPT UI/docs/activity-data-model.md` Section 2

**Prohibited:** Do NOT extract user's personal data (who is using GPT). Only extract activator contact data (public, non-personal).

---

### 5.9 Categories Extraction

**Detection strategies:**
- Primary category: look for explicit category mentions, taxonomy keywords
- Secondary categories: look for multiple category mentions, related keywords
- Freeform tags: extract hashtags, keywords, user-defined tags

**Patterns to look for:**
- Explicit markers: "Category:", "Type:", "Tags:"
- Hashtags in social media (#meditation, #wellness)
- Keywords in description (yoga, therapy, coaching, dance)
- Taxonomy inference from format and description

**Mapping to canonical categories:**
- Use Activity Data Model taxonomy structure
- Map keywords to primary category
- Extract secondary categories from context
- Preserve freeform tags as-is

**Activity JSON schema field reference:**
- Field: `categories` (object)
- Location: `core_description.categories`
- Required: No (optional)
- Type: Common (extracted same way for event and service)
- Structure:
  - `primary` (object) — primary category
  - `secondary` (array) — secondary categories
  - `freeform_user_tags` (array, optional) — user-defined tags
- See: `GPT UI/docs/activity-data-model.md` Section 2

**Ambiguity handling:**
- If no clear category → mark for clarification
- If multiple primary candidates → use most specific
- If unclear → extract as freeform tags

---

### 5.10 Capacity/Participation Extraction

**CRITICAL:** This extraction differs based on `activity_type`.

**For `activity_type = "event"`:**

Extract `event_capacity` structure:

**Patterns to look for:**
- "до 20 человек", "up to 20 people" → max_participants: 20
- "15 мест", "15 seats" → seats: 15
- "минимум 5", "minimum 5" → min_participants: 5
- "группа до 20", "group of up to 20" → group_capacity: 20, max_participants: 20

**Extraction algorithm:**
```
1. Look for capacity keywords:
   - "мест", "seats", "участников", "participants"
   - "до", "up to", "максимум", "maximum"
   - "минимум", "minimum", "от", "from"

2. Extract numbers:
   - Extract numeric values near capacity keywords
   - Determine which field (seats, min_participants, max_participants, group_capacity)

3. Set confidence:
   - If explicit → high confidence (0.9+)
   - If inferred → medium confidence (0.6-0.8)
   - If unclear → mark for clarification
```

**For `activity_type = "service"`:**

Extract `service_participation` structure:

**Patterns to look for:**
- "индивидуально", "one-to-one", "1:1" → session_mode: "one_to_one"
- "семейные сессии", "family sessions" → session_mode: "family"
- "малая группа", "small group" → session_mode: "small_group"
- "одновременно 2 клиента", "2 concurrent clients" → concurrent_clients: 2

**Extraction algorithm:**
```
1. Look for session mode keywords:
   - "индивидуально", "one-to-one", "1:1" → one_to_one
   - "семья", "family" → family
   - "группа", "group" → small_group

2. Extract concurrent clients:
   - Look for "одновременно", "concurrent", "at the same time"
   - Extract number

3. Extract practitioner model:
   - Look for "один практик", "one practitioner", "team"
   - Extract description
```

**Activity JSON schema field reference:**

**For `activity_type = "event"`:**
- Field: `event_capacity` (object)
- Location: `event_capacity`
- Required: No (optional)
- Type: Event-specific (mutually exclusive with `service_participation`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 5
- Contains: `group_capacity`, `seats`, `min_participants`, `max_participants`

**For `activity_type = "service"`:**
- Field: `service_participation` (object)
- Location: `service_participation`
- Required: No (optional)
- Type: Service-specific (mutually exclusive with `event_capacity`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 5
- Contains: `session_mode`, `concurrent_clients`, `practitioner_to_client_model`

**☑ Rule:** Extract `event_capacity` OR `service_participation`, never both. Determined by `activity_type`.

---

### 5.11 Duration Extraction

**CRITICAL:** This extraction differs based on `activity_type`.

**For `activity_type = "event"`:**

Extract `event_duration` structure:

**Patterns to look for:**
- "2 часа", "2 hours" → duration in hours
- "19:00-21:00" → duration from time range
- "с 19:00 до 21:00", "from 7 PM to 9 PM" → duration from time range
- "фиксированная длительность", "fixed duration" → duration_type: "fixed"

**Extraction algorithm:**
```
1. Determine duration_type:
   - If single duration mentioned → duration_type: "per_occurrence"
   - If "фиксированная", "fixed" → duration_type: "fixed"

2. Extract duration:
   - From time range: calculate difference
   - From explicit mention: extract number + unit
   - Convert to minutes or ISO 8601 duration format

3. Set confidence:
   - If explicit → high confidence (0.9+)
   - If calculated from time range → medium confidence (0.7-0.9)
   - If unclear → mark for clarification
```

**For `activity_type = "service"`:**

Extract `service_duration_options` structure:

**Patterns to look for:**
- "30 минут", "60 минут", "90 минут" → duration options
- "Standard 30 min, Extended 60 min" → multiple options with labels
- "сессии 30/60/90 минут" → multiple options

**Extraction algorithm:**
```
1. Look for duration mentions:
   - Extract all duration values (30, 60, 90 minutes)
   - Extract labels if present ("Standard", "Extended")

2. Structure as array:
   - Each option: {duration_minutes: number, label: string (optional)}

3. Set confidence:
   - If explicit → high confidence (0.9+)
   - If inferred → medium confidence (0.6-0.8)
```

**Activity JSON schema field reference:**

**For `activity_type = "event"`:**
- Field: `event_duration` (object)
- Location: `event_duration`
- Required: No (optional)
- Type: Event-specific (mutually exclusive with `service_duration_options`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 6
- Contains: `duration_type`, `per_occurrence`, `fixed`

**For `activity_type = "service"`:**
- Field: `service_duration_options` (array)
- Location: `service_duration_options`
- Required: No (optional)
- Type: Service-specific (mutually exclusive with `event_duration`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 6
- Contains: array of {duration_minutes, label}

**☑ Rule:** Extract `event_duration` OR `service_duration_options`, never both. Determined by `activity_type`.

---

### 5.12 Pricing Extraction

**CRITICAL:** This extraction differs based on `activity_type`.

**For `activity_type = "event"`:**

Extract `event_pricing` structure:

**Patterns to look for:**
- "бесплатно", "free" → pricing_type: "free"
- "пожертвование", "donation" → pricing_type: "donation"
- "1000 руб", "1000 RUB" → pricing_type: "ticket_price", ticket_price: {amount: 1000, currency: "RUB"}
- "от 500 до 1000", "from 500 to 1000" → pricing_type: "ticket_price", price_range: {min: 500, max: 1000}

**Extraction algorithm:**
```
1. Determine pricing_type:
   - If "бесплатно", "free" → pricing_type: "free"
   - If "пожертвование", "donation" → pricing_type: "donation"
   - If price mentioned → pricing_type: "ticket_price"

2. Extract price values:
   - Extract amount and currency
   - If range → extract min and max
   - Convert currency codes to ISO 4217

3. Set confidence:
   - If explicit → high confidence (0.9+)
   - If currency unclear → medium confidence (0.6-0.8)
   - If price unclear → mark for clarification
```

**For `activity_type = "service"`:**

Extract `service_pricing_model` structure:

**Patterns to look for:**
- "за сессию", "per session" → model: "per_session"
- "за час", "per hour", "почасовая" → model: "per_hour"
- "пакет 5 сессий", "package of 5 sessions" → model: "per_package"
- "пожертвование", "donation" → model: "donation"
- "бесплатно", "free" → model: "free"

**Extraction algorithm:**
```
1. Determine model:
   - Look for pricing model keywords
   - Extract model type

2. Extract package definition (if per_package):
   - Extract sessions_count
   - Extract total_price
   - Extract currency

3. Set confidence:
   - If explicit → high confidence (0.9+)
   - If inferred → medium confidence (0.6-0.8)
```

**Activity JSON schema field reference:**

**For `activity_type = "event"`:**
- Field: `event_pricing` (object)
- Location: `event_pricing`
- Required: No (optional)
- Type: Event-specific (mutually exclusive with `service_pricing_model`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 6
- Contains: `pricing_type`, `ticket_price`, `price_range`

**For `activity_type = "service"`:**
- Field: `service_pricing_model` (object)
- Location: `service_pricing_model`
- Required: No (optional)
- Type: Service-specific (mutually exclusive with `event_pricing`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 6
- Contains: `model`, `package_definition`

**☑ Rule:** Extract `event_pricing` OR `service_pricing_model`, never both. Determined by `activity_type`.

---

### 5.13 CTA/Booking Extraction

**CRITICAL:** This extraction differs based on `activity_type`.

**For `activity_type = "event"`:**

Extract `event_cta` structure:

**Patterns to look for:**
- Event page URLs: "https://eventbrite.com/...", "https://facebook.com/events/..."
- Tickets links: "купить билеты", "buy tickets", "tickets: https://..."
- Registration links: "регистрация", "register", "sign up"

**Extraction algorithm:**
```
1. Extract event_page_link:
   - Look for main event URL
   - Extract from links, meta tags, or text

2. Extract tickets_link:
   - Look for tickets/registration URLs
   - Extract from links or text mentions

3. Set confidence:
   - If explicit URL → high confidence (0.9+)
   - If mentioned but no URL → mark for clarification
```

**For `activity_type = "service"`:**

Extract `service_cta` structure:

**Patterns to look for:**
- Booking URLs: "https://calendly.com/...", "book at https://..."
- Contact channels: "связаться", "contact", "email:", "phone:"
- Amanita booking: "через Amanita", "via Amanita" → amanita_booking: true

**Extraction algorithm:**
```
1. Extract booking_url:
   - Look for booking/calendar URLs
   - Extract from links or text

2. Extract contact_channel:
   - Look for contact information
   - Determine type (email, phone, social_link)
   - Extract value

3. Determine amanita_booking:
   - If "через Amanita", "via Amanita" → true
   - Otherwise → false (default)
```

**Activity JSON schema field reference:**

**For `activity_type = "event"`:**
- Field: `event_cta` (object)
- Location: `event_cta`
- Required: No (optional)
- Type: Event-specific (mutually exclusive with `service_cta`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 7
- Contains: `event_page_link`, `tickets_link`

**For `activity_type = "service"`:**
- Field: `service_cta` (object)
- Location: `service_cta`
- Required: No (optional)
- Type: Service-specific (mutually exclusive with `event_cta`)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 7
- Contains: `booking_url`, `contact_channel`, `amanita_booking`

**☑ Rule:** Extract `event_cta` OR `service_cta`, never both. Determined by `activity_type`.

---

### 5.14 Source & Provenance Extraction

**Extraction algorithm:**

```
1. Determine source_type:
   - If manual text input → source_type: "manual"
   - If link provided → source_type: "link"
   - If screenshot provided → source_type: "screenshot"
   - If PDF provided → source_type: "pdf"

2. Extract canonical_url:
   - If link → use link as canonical_url
   - If screenshot from social media → extract post URL if available
   - If PDF → extract source URL if mentioned

3. Extract raw_asset_ref (if applicable):
   - Reference to original file/asset
   - TTL reference for temporary storage

4. Generate dedup_hints (if applicable):
   - Extract possible duplicate indicators
   - Extract update_vs_new hints
```

**Activity JSON schema field reference:**
- Field: `sources` (object)
- Location: `sources`
- Required: Yes (always present)
- Type: Common (extracted same way for event and service)
- Structure: See `GPT UI/docs/activity-data-model.md` Section 8
- Contains: `canonical_url`, `source_type`, `raw_asset_ref`, `dedup_hints`

---

## 6. Confidence Scoring

### 6.1 Confidence Scoring Algorithm

GPT MUST assign confidence scores to each extracted field.

**Confidence Score Range:**
- 0.0 - 1.0 (0.0 = no confidence, 1.0 = absolute confidence)

**Factors affecting confidence:**

1. **Source quality:**
   - Structured data (JSON, meta tags) → +0.2
   - Semi-structured (tables, lists) → +0.1
   - Free-form text → baseline (0.0)
   - Low-quality image → -0.2

2. **Explicitness:**
   - Explicit field markers ("Title:", "Date:") → +0.3
   - Implicit extraction (inferred from context) → baseline (0.0)
   - Ambiguous context → -0.2

3. **Format consistency:**
   - Consistent across multiple sources → +0.2
   - Conflicting sources → -0.3
   - Single source → baseline (0.0)

4. **Field type:**
   - Simple fields (title, format) → baseline confidence easier
   - Complex fields (timing, pricing) → lower baseline confidence

**Confidence thresholds:**

- **High confidence (0.8-1.0):** Use value as-is, no clarification needed
- **Medium confidence (0.5-0.79):** Use value, but flag for verification
- **Low confidence (0.0-0.49):** Mark for clarification, do not use value

**Algorithm:**

```
For each extracted field:
1. Start with baseline confidence (0.5 for explicit, 0.3 for inferred)
2. Apply source quality modifier
3. Apply explicitness modifier
4. Apply format consistency modifier
5. Apply field type modifier
6. Clamp to [0.0, 1.0]
7. Set confidence_scores[field_name] = calculated_confidence
```

**Example:**

```
Field: title
- Source: Explicit "Title:" marker → +0.3
- Format: Structured text → +0.1
- Consistency: Single source → baseline
- Field type: Simple → baseline
- Final confidence: 0.5 + 0.3 + 0.1 = 0.9 (high confidence)

Field: event_timing
- Source: Inferred from text → baseline (0.3)
- Format: Free-form text → baseline
- Consistency: Single source → baseline
- Field type: Complex → -0.1
- Final confidence: 0.3 - 0.1 = 0.2 (low confidence, mark for clarification)
```

---

## 7. Ambiguity Handling

### 7.1 Ambiguity Detection

**Types of ambiguities:**
- Date ambiguity (multiple possible dates)
- Format ambiguity (could be session or workshop)
- Location ambiguity (city unclear, venue unclear)
- Schedule ambiguity (recurrence unclear)
- activity_type ambiguity (could be event or service)
- Pricing ambiguity (unclear currency, unclear pricing model)

**Detection algorithm:**

```
For each extracted field:
1. Check for multiple possible values
2. Check for unclear context
3. Check for conflicting information
4. If ambiguous → add to ambiguities array
5. Set confidence score low (< 0.5)
```

### 7.2 Ambiguity Resolution

**Resolution strategies:**

1. **Request clarification:**
   - If critical field (title, activity_type) → always request
   - If optional field → request only if needed for completeness

2. **Use defaults (with low confidence):**
   - Only for non-critical optional fields
   - Always flag as ambiguous

3. **Use most likely value:**
   - Only if confidence > 0.6
   - Always flag for verification

**Priority:**
- Critical ambiguities (activity_type, title) → highest priority
- Required field ambiguities → high priority
- Optional field ambiguities → low priority

---

## 8. Error Handling

### 8.1 Parsing Errors

**Error types:**
- Image cannot be read (blurry, corrupted)
- PDF cannot be parsed (encrypted, corrupted)
- Link is inaccessible (404, requires auth, blocked)
- Text is too ambiguous (cannot extract meaningful data)

**Fallback strategies:**

```
1. **Image cannot be read:**
   → Request alternative input (text description, higher quality image)
   → Provide partial extraction if any text is readable
   → Flag low confidence scores

2. **PDF cannot be parsed:**
   → Request text description or alternative format
   → If partially readable → extract what is possible
   → Flag missing fields

3. **Link is inaccessible:**
   → Request description or screenshot
   → Explain limitation to user
   → Do NOT attempt to bypass restrictions

4. **Text is too ambiguous:**
   → Request clarification
   → Provide partial extraction
   → Flag all ambiguous fields
```

**Error message templates:**

**1. Image cannot be read:**
```
"I was unable to read the image you provided. The image appears to be blurry, corrupted, or in an unsupported format.

I was able to extract the following information (if any):
[list of extracted fields with low confidence scores]

To proceed, please provide:
- A higher quality image, or
- A text description of the activity details

If you have the original source (event page, social media post), you can also share a direct link instead."
```

**2. PDF cannot be parsed:**
```
"I was unable to parse the PDF document you provided. The document may be encrypted, corrupted, or in an unsupported format.

I was able to extract the following information (if any):
[list of extracted fields]

To proceed, please provide:
- A text description of the activity details, or
- The same information in another format (screenshot, link, or text)

If the PDF contains important details, you can copy and paste the text content directly."
```

**3. Link is inaccessible:**
```
"I was unable to access the link you provided. The link may be:
- Temporarily unavailable (404 error)
- Requiring authentication or login
- Blocked or restricted in my access

I cannot bypass these restrictions or access private content.

To proceed, please provide:
- A screenshot of the event page, or
- A text description of the activity details, or
- A different link if available

If the link requires login, you can share the public information about the activity instead."
```

**4. Text is too ambiguous:**
```
"I was unable to extract clear information from the text you provided. The description is too ambiguous or lacks specific details needed to create an Activity.

I was able to extract the following information (if any):
[list of extracted fields with confidence scores]

To proceed, please provide clarification on:
[list of ambiguous fields]

For example:
- If the activity type is unclear: "Is this a scheduled event with fixed dates, or a service available by appointment?"
- If the date is unclear: "What is the specific date and time for this activity?"
- If the location is unclear: "Where will this activity take place? (city, venue, or online)"

You can also provide a more detailed description or share additional sources (links, screenshots) that contain the missing information."
```

### 8.2 Graceful Degradation

**Always provide partial extraction:**
- Even if incomplete, extract what is possible
- Always flag what is missing
- Always suggest alternative input methods
- Never fail completely without output

**Partial extraction message template:**
```
"I was able to extract some information from your input, but some fields are missing or unclear:

Extracted fields:
[list of successfully extracted fields with confidence scores]

Missing or unclear fields:
[list of missing/ambiguous fields]

To complete the Activity creation, please provide:
[specific guidance on what is needed]

Alternative input methods you can try:
- Share a direct link to the event page
- Provide a screenshot with clearer text
- Copy and paste the text content directly
- Provide a more detailed description"
```

---

## 9. Output Contract

### 9.1 Output Structure

**Output structure MUST match Activity JSON schema:**

The output structure MUST follow the Activity Data Model defined in `GPT UI/docs/activity-data-model.md`.

**Output structure:**

```json
{
  "extracted_data": {
    // Section 0: Identity & Lifecycle (parsing does NOT set these, but may infer activity_type)
    "activity_type": "event" | "service",  // MUST be determined first
    // "activity_id", "status", "versioning", "creator/owner_reference", "timestamps" — NOT set by parsing
    
    // Section 1: Core Description (common fields)
    "title": "...",
    "short_summary": "...",  // optional
    "full_description": "...",
    "format": "session" | "workshop" | "ceremony" | "class_regular" | "class_single" | "retreat" | "performance" | "other",  // enum
    "format_other_label": "...",  // if format = "other"
    "categories": {
      "primary": {...},  // level 1 category
      "secondary": [...],  // level 2 categories
      "freeform_user_tags": [...]  // optional, unmapped user terms
    },
    "age_groups": ["babies" | "toddlers" | "primary_schoolers" | "teenagers" | "youngsters_18_25" | "adults" | "seniors"],  // array of enum
    "parental_accompaniment": "allowed" | "required" | "optional",  // optional, for children's activities
    "language_requirements": {
      "mode": "irrelevant" | "understand_only" | "speak_and_understand" | "mixed",
      "languages_to_understand": ["ru", "en", ...],  // ISO 639-1 language codes
      "languages_to_speak": ["ru", "en", ...]  // ISO 639-1 language codes
    },
    "media": {
      "official_site": "...",  // URL
      "social_links": [
        {
          "platform": "instagram" | "facebook" | "vk" | "telegram" | "other",
          "url": "...",
          "account": "..."  // optional
        }
      ],
      "event_service_specific_links": [...]  // optional, type-specific links
    },
    "policy_notes": "...",  // optional, disclaimers/restrictions (no clinical content)
    
    // Section 2: Delivery & Location (common fields)
    "delivery_mode": "in_person" | "online" | "hybrid",
    "location_info": {
      "city": "...",  // optional
      "area": "...",  // optional
      "venue": "...",  // optional, applicable for in-person
      "online_platform": "...",  // optional, platform name for online
      "online_link": "..."  // optional, URL, applicable for online/hybrid
    },
    "service_area": {  // optional, more common for services
      "radius": 10,  // number, radius in km
      "districts": [...],  // array of string
      "travel_notes": "..."  // optional
    },
    
    // Section 3: Timing (CONDITIONAL — depends on activity_type)
    // IF activity_type = "event":
    "event_timing": {
      "schedule_model": "fixed_dates" | "recurring",
      "fixed_dates": [  // conditional, if schedule_model = "fixed_dates"
        {
          "start": "2025-02-15T19:00:00Z",  // ISO 8601
          "end": "2025-02-15T21:00:00Z",  // ISO 8601
          "timezone": "Europe/Tallinn"  // IANA timezone
        }
      ],
      "recurring": {  // conditional, if schedule_model = "recurring"
        "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",  // RRULE format
        "start_date": "2025-02-01",  // ISO 8601
        "end_date": "2025-03-31",  // ISO 8601, optional
        "timezone": "Europe/Tallinn"  // IANA timezone
      },
      "exceptions": [  // optional
        {
          "date": "2025-02-15",  // ISO 8601
          "reason": "..."  // optional
        }
      ],
      "overrides": [  // optional
        {
          "date": "2025-02-15",  // ISO 8601
          "start": "2025-02-15T20:00:00Z",  // ISO 8601
          "end": "2025-02-15T22:00:00Z"  // ISO 8601
        }
      ]
    },
    // IF activity_type = "service":
    "service_timing": {
      "availability_type": "by_request" | "fixed_windows" | "bookable_slots",
      "availability_windows": [  // conditional, if availability_type = "fixed_windows"
        {
          "day_of_week": "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday",
          "start_time": "09:00",  // HH:MM format
          "end_time": "17:00",  // HH:MM format
          "timezone": "Europe/Tallinn"  // IANA timezone
        }
      ],
      "booking_policy": "..."  // how to book/appoint
    },
    
    // Section 4: Participation & Capacity (CONDITIONAL — depends on activity_type)
    // IF activity_type = "event":
    "event_capacity": {
      "group_capacity": 20,  // optional, total seats/participants
      "seats": 15,  // optional, available seats
      "min_participants": 5,  // optional
      "max_participants": 20  // optional
    },
    // IF activity_type = "service":
    "service_participation": {
      "session_mode": "one_to_one" | "family" | "small_group",
      "concurrent_clients": 1,  // number, default: 1
      "practitioner_to_client_model": "..."  // optional, description (no personalization)
    },
    
    // Section 5: Duration & Pricing (CONDITIONAL — depends on activity_type)
    // IF activity_type = "event":
    "event_duration": {
      "duration_type": "per_occurrence" | "fixed",
      "per_occurrence": {  // conditional, if duration_type = "per_occurrence"
        "duration_minutes": 120  // number, duration per occurrence
      },
      "fixed": "..."  // conditional, if duration_type = "fixed", fixed duration description
    },
    "event_pricing": {
      "pricing_type": "ticket_price" | "donation" | "free",
      "ticket_price": {  // conditional, if pricing_type = "ticket_price"
        "amount": 1000,  // number
        "currency": "EUR",  // ISO 4217
        "price_range": {  // optional
          "min": 500,  // number
          "max": 1500  // number
        }
      }
    },
    // IF activity_type = "service":
    "service_duration_options": [
      {
        "duration_minutes": 30,  // number, e.g., 30, 60, 90, custom
        "label": "Standard"  // optional, e.g., "Standard", "Extended"
      }
    ],
    "service_pricing_model": {
      "model": "per_session" | "per_hour" | "per_package" | "donation" | "free",
      "package_definition": {  // optional, if model = "per_package"
        "sessions_count": 5,  // number
        "total_price": 500,  // number
        "currency": "EUR"  // ISO 4217
      }
    },
    
    // Section 6: Booking / CTA (CONDITIONAL — depends on activity_type)
    // IF activity_type = "event":
    "event_cta": {
      "event_page_link": "...",  // URL
      "tickets_link": "..."  // optional, URL
    },
    // IF activity_type = "service":
    "service_cta": {
      "booking_url": "...",  // optional, URL (Calendly/site/form)
      "contact_channel": {  // optional
        "type": "social_link" | "email" | "phone" | "other",
        "value": "..."
      },
      "amanita_booking": false  // boolean, default: false, "Amanita booking (future)"
    },
    
    // Section 7: Source & Provenance (common for all)
    "sources": {
      "canonical_url": "...",  // optional, URL
      "source_type": "manual" | "link" | "screenshot" | "pdf",
      "raw_asset_ref": "...",  // optional, TTL reference to raw asset
      "dedup_hints": {  // optional
        "possible_duplicates": [...],  // array of string, activity IDs
        "update_vs_new": "update" | "new"  // optional enum
      }
    }
    
    // Section 8: Review Metadata — NOT set by parsing
  },
  "metadata": {
    "source_type": "screenshot" | "pdf" | "link" | "text" | "mixed",
    "sources": [
      {"type": "text", "content": "..."},
      {"type": "screenshot", "platform": "Instagram", "account": "..."},
      {"type": "link", "url": "...", "platform": "Eventbrite"}
    ],
    "confidence_scores": {
      "activity_type": 0.9,
      "title": 0.95,
      "format": 0.85,
      "event_timing": 0.7,
      // ... confidence for each extracted field (0.0 - 1.0)
    },
    "ambiguities": [
      "location.city",  // needs clarification
      "date.verification",  // needs verification
      "format"  // could be session or workshop
    ],
    "missing_required_fields": [
      "full_description",  // required for SentToReview
      "event_timing"  // required for event type
    ],
    "conflicts": []  // if mixed content has conflicting information
  }
}
```

**Critical rules:**

- `activity_type` MUST be determined first (before extracting conditional fields)
- Extract `event_timing` OR `service_timing` (never both)
- Extract `event_capacity` OR `service_participation` (never both)
- Extract `event_duration`/`event_pricing` OR `service_duration_options`/`service_pricing_model` (never both)
- Extract `event_cta` OR `service_cta` (never both)
- All conditional fields depend on `activity_type`
- Fields marked as "NOT set by parsing" must NOT be included in output

**Reference:** See `GPT UI/docs/activity-data-model.md` for complete schema definition.

**This output is intended for:**
- Ingest Validation Instruction (for validation and missing data resolution)

---

## 10. Edge Cases

### 10.1 Incomplete Screenshots

**Scenario:** Screenshot shows only part of information (cut off, cropped)

**Handling:**
- Extract what is visible
- Flag missing information
- Request additional input or clarification

---

### 10.2 Multiple Activities Detected

**Scenario:** Input contains multiple Activities (multiple screenshots, multiple files, multiple links, or multi-page PDF with multiple events)

**Handling:**
```
IF multiple Activities detected:
   → STOP parsing immediately
   → Return error flag: "multiple_activities_detected"
   → DO NOT extract any Activity data
   → DO NOT attempt to process the first one
   → Return to Ingest Validation with error
```

**Detection criteria:**
- Multiple screenshots/images (2+ images) that appear to be different events
- Multiple PDF files (2+ PDFs)
- Multiple links (2+ URLs) that appear to be different events
- Single PDF with multiple distinct Activities (different titles, dates, locations)
- Mixed content (text + multiple images) representing different Activities

**Note:** This instruction detects multiple Activities during parsing, but Base Instruction should detect and reject multiple Activities BEFORE parsing begins. This edge case is a fallback if detection at Base Instruction level fails.

---

### 10.3 Broken or Inaccessible Links

**Scenario:** Link returns 404, requires authentication, or is blocked

**Handling:**
- Request alternative input (description, screenshot)
- Do NOT attempt to bypass restrictions
- Explain limitation to user

---

### 10.4 Low-Quality Images

**Scenario:** Screenshot is blurry, low resolution, or unreadable

**Handling:**
- Attempt extraction with best effort
- Flag low confidence scores
- Request higher quality image or alternative input

---

### 10.5 Multilingual Content

**Scenario:** Input contains multiple languages

**Handling:**
- Extract in all languages present
- Preserve original language
- Map to canonical language codes
- Flag if language requirements are unclear

---

### 10.6 Conflicting Information Between Sources

**Scenario:** Mixed content contains conflicting information (different titles, dates, locations)

**Handling:**
```
1. Identify conflicts:
   - Compare extracted fields from all sources
   - Flag conflicting values

2. Conflict resolution:
   - Use most structured source (link > PDF > screenshot > text)
   - Use most recent source (if timestamps available)
   - Use most complete source
   - Flag conflicts in metadata.conflicts

3. Output:
   - Use resolved value (with conflict flag)
   - Include all conflicting values in metadata
   - Lower confidence scores for conflicted fields
```

---

### 10.7 Encrypted or Password-Protected PDFs

**Scenario:** PDF document requires a password or is encrypted and cannot be parsed

**Handling:**
- Do NOT attempt to bypass password protection
- Request alternative input (unencrypted PDF, screenshot, or text description)
- Explain limitation to user: "The PDF is password-protected. Please provide an unencrypted version or share the content in another format."
- Flag in metadata: `parsing_error: "encrypted_pdf"`

---

### 10.8 Unsupported File Formats

**Scenario:** Input file format is not supported (e.g., .docx, .xlsx, .zip, executable files)

**Handling:**
- Identify unsupported format
- Request alternative input in supported formats (PDF, image, text, link)
- Explain supported formats to user: "I can parse PDFs, images (screenshots), text, and links. Please convert your file to one of these formats."
- Flag in metadata: `parsing_error: "unsupported_format"`

---

### 10.9 Timezone Ambiguity

**Scenario:** Date/time information is present but timezone is missing or ambiguous

**Handling:**
```
1. Detect timezone ambiguity:
   - Date/time present but no timezone specified
   - Multiple timezones mentioned (conflicting)
   - Timezone abbreviation unclear (e.g., "EST" could be Eastern Standard Time or Eastern Summer Time)

2. Resolution strategy:
   - If location is known → infer timezone from location
   - If location unknown → use default timezone (UTC or user's inferred timezone)
   - Flag as ambiguous in metadata.ambiguities
   - Lower confidence score for timing fields

3. Output:
   - Use inferred/default timezone
   - Flag in metadata: "timezone_inferred" or "timezone_ambiguous"
   - Request confirmation if confidence is low
```

---

### 10.10 Activity Type Cannot Be Determined

**Scenario:** After analyzing all indicators, `activity_type` cannot be determined with sufficient confidence

**Handling:**
```
1. If confidence score < 0.5 after all analysis:
   - Mark activity_type as ambiguous
   - Set confidence_scores.activity_type = low_value (< 0.5)
   - Add to metadata.ambiguities: "activity_type"

2. Request clarification:
   - Ask user: "Is this a scheduled event with fixed dates, or a service available by appointment?"
   - Provide examples to help user understand the distinction

3. Do NOT proceed with extraction:
   - Wait for user clarification
   - Do NOT extract conditional fields until activity_type is determined
   - Return to Ingest Validation with ambiguity flag

4. If user provides clarification:
   - Set activity_type based on user response
   - Proceed with conditional field extraction
   - Update confidence score based on user confirmation
```

---

## 11. Integration with Other Instructions

### 11.1 Input from Ingest Validation

**Handoff protocol:**

```
1. Ingest Validation receives non-dialogue input from Base Instruction
2. Ingest Validation activates Ingest Deep Parsing
3. Passes:
   - raw input (screenshot, PDF, link, text, or mixed)
   - input type classification (from Base Instruction)
   - context (if any from previous dialogue)

4. Ingest Deep Parsing:
   - Performs deep parsing
   - Returns structured intermediate representation
   - Returns to Ingest Validation
```

**Context passing:**
- Current mode (INGEST)
- Input type classification
- Previous dialogue context (if applicable)
- Activity status (if updating existing Activity)

---

### 11.2 Output to Ingest Validation

**Handoff protocol:**

```
1. Ingest Deep Parsing completes extraction
2. Returns structured intermediate representation:
   - extracted_data (with all extracted fields)
   - metadata (confidence_scores, ambiguities, missing_required_fields, conflicts)

3. Ingest Validation:
   - Validates extracted data
   - Checks completeness
   - Resolves missing required fields
   - Handles ambiguities
```

**Output structure:**
- MUST match Activity JSON schema
- MUST include confidence scores
- MUST flag ambiguities
- MUST identify missing required fields

---

### 11.3 No Direct Integration

This instruction does NOT interact with:
- Activity Normalizer (receives already validated data)
- API Orchestrator (does not call backend)
- KоныРода Gate (does not make policy decisions)
- Safety & Compliance (handled by Ingest Validation)

---

## 12. Platform-Specific Parsing

### 12.1 Instagram Parsing

**Supported content types:**
- Posts (single image, carousel)
- Stories
- Reels

**Post parsing algorithm:**

```
1. Extract caption text:
   - Main description in caption
   - Hashtags (may indicate categories, format)
   - Mentions (@account)

2. Extract metadata:
   - Post date/time (if visible)
   - Location tag (if present)
   - Account name (activator reference)

3. Extract image content:
   - Use vision to extract text from image
   - Extract structured information (dates, times, locations)

4. Map to Activity fields:
   - Caption → description
   - Hashtags → categories, freeform_user_tags
   - Location tag → location_info
   - Account → activator_reference
```

**Story parsing algorithm:**

```
1. Extract story content:
   - Text overlays (main description)
   - Stickers (location, poll, question)
   - Story highlights (if visible)
   - Account name (activator reference)

2. Extract metadata:
   - Story timestamp (if visible, usually 24-hour expiration)
   - Location sticker → location_info
   - Mention stickers → activator_reference

3. Extract image/video content:
   - Use vision to extract text from story image/video
   - Extract structured information (dates, times, locations)
   - Note: Stories are ephemeral (24 hours), may be screenshots

4. Map to Activity fields:
   - Text overlay → description
   - Location sticker → location_info
   - Account → activator_reference
   - Note: Story content may be less structured than posts
```

**Reel parsing algorithm:**

```
1. Extract reel content:
   - Caption text (description)
   - Hashtags (may indicate categories, format)
   - Mentions (@account)
   - Audio track information (if relevant)

2. Extract metadata:
   - Reel date/time (if visible)
   - Location tag (if present)
   - Account name (activator reference)
   - Video duration (if visible)

3. Extract video content:
   - Use vision to extract text from video frames
   - Extract structured information (dates, times, locations)
   - Note: Reels may have text overlays in video

4. Map to Activity fields:
   - Caption → description
   - Hashtags → categories, freeform_user_tags
   - Location tag → location_info
   - Account → activator_reference
   - Video duration → event_duration or service_duration_options (if applicable)
```

---

### 12.2 Facebook Parsing

**Supported content types:**
- Events (event pages, event posts)
- Posts (regular posts, group posts)
- Groups (group announcements, group events)

**Event parsing algorithm:**

```
1. Extract event information:
   - Event title
   - Event description
   - Event date/time
   - Event location (venue, address)
   - Event organizer (page/group name)

2. Extract metadata:
   - Event page URL
   - Event cover image (if present)
   - Event category/tags
   - RSVP information (if visible)

3. Extract structured data:
   - Date/time → event_timing
   - Location → location_info
   - Organizer → activator_reference
   - Category → categories

4. Map to Activity fields:
   - Event title → title
   - Event description → description
   - Event date/time → event_timing
   - Event location → location_info
   - Organizer → activator_reference
```

**Post parsing algorithm:**

```
1. Extract post content:
   - Post text (main description)
   - Post images/videos
   - Post date/time
   - Post author (page/group/account)

2. Extract metadata:
   - Post URL
   - Location tag (if present)
   - Mentions/tags
   - Reactions/comments count (if relevant)

3. Extract image/video content:
   - Use vision to extract text from images/videos
   - Extract structured information (dates, times, locations)

4. Map to Activity fields:
   - Post text → description
   - Location tag → location_info
   - Author → activator_reference
   - Post date/time → event_timing (if event-related)
```

---

### 12.3 VK Parsing

**Supported content types:**
- Posts (wall posts, group posts)
- Events (VK events, event posts)
- Groups (group announcements, group events)

**Post parsing algorithm:**

```
1. Extract post content:
   - Post text (main description)
   - Post attachments (images, videos, links)
   - Post date/time
   - Post author (user/group name)

2. Extract metadata:
   - Post URL
   - Location (if geotagged)
   - Hashtags (if present)
   - Mentions (@username)

3. Extract attachments:
   - Use vision to extract text from images/videos
   - Extract structured information from links
   - Extract dates, times, locations

4. Map to Activity fields:
   - Post text → description
   - Location → location_info
   - Author → activator_reference
   - Hashtags → categories, freeform_user_tags
   - Post date/time → event_timing (if event-related)
```

**Event parsing algorithm:**

```
1. Extract event information:
   - Event title
   - Event description
   - Event date/time
   - Event location (venue, address)
   - Event organizer (group/user name)

2. Extract metadata:
   - Event page URL
   - Event cover image (if present)
   - Event category
   - RSVP/attendance information

3. Extract structured data:
   - Date/time → event_timing
   - Location → location_info
   - Organizer → activator_reference
   - Category → categories

4. Map to Activity fields:
   - Event title → title
   - Event description → description
   - Event date/time → event_timing
   - Event location → location_info
   - Organizer → activator_reference
```

---

### 12.4 Telegram Parsing

**Supported content types:**
- Channels (channel posts, announcements)
- Groups (group messages, group announcements)
- Posts (forwarded messages, shared content)

**Channel parsing algorithm:**

```
1. Extract channel content:
   - Post text (main description)
   - Post media (images, videos, documents)
   - Post date/time
   - Channel name (activator reference)

2. Extract metadata:
   - Channel username/ID
   - Post link (if available)
   - Media captions
   - Forwarded from (if applicable)

3. Extract media content:
   - Use vision to extract text from images/videos
   - Extract structured information from documents (PDFs)
   - Extract dates, times, locations

4. Map to Activity fields:
   - Post text → description
   - Channel name → activator_reference
   - Media captions → description (supplement)
   - Post date/time → event_timing (if event-related)
```

**Group parsing algorithm:**

```
1. Extract group content:
   - Message text (main description)
   - Message media (images, videos, documents)
   - Message date/time
   - Group name (activator reference)

2. Extract metadata:
   - Group username/ID
   - Message link (if available)
   - Media captions
   - Sender information (if visible)

3. Extract media content:
   - Use vision to extract text from images/videos
   - Extract structured information from documents
   - Extract dates, times, locations

4. Map to Activity fields:
   - Message text → description
   - Group name → activator_reference
   - Media captions → description (supplement)
   - Message date/time → event_timing (if event-related)
```

---

### 12.5 Eventbrite Parsing

**Supported content types:**
- Event pages (event listings, event details)

**Event page parsing algorithm:**

```
1. Extract event information:
   - Event title
   - Event description
   - Event date/time (start, end, timezone)
   - Event location (venue name, address, city)
   - Event organizer (organizer name)

2. Extract metadata:
   - Event page URL
   - Event image (if present)
   - Event category/tags
   - Ticket pricing information
   - Event capacity/availability

3. Extract structured data:
   - Date/time → event_timing (with timezone)
   - Location → location_info (structured address)
   - Organizer → activator_reference
   - Category → categories
   - Pricing → event_pricing
   - Capacity → event_capacity

4. Map to Activity fields:
   - Event title → title
   - Event description → description
   - Event date/time → event_timing
   - Event location → location_info
   - Organizer → activator_reference
   - Category → categories
   - Pricing → event_pricing
   - Capacity → event_capacity
   - Event URL → event_cta.event_page_link
```

---

### 12.6 Other Platforms Parsing

**Supported content types:**
- Generic event/service pages
- Generic social media posts
- Generic websites

**Generic parsing algorithm:**

```
1. Extract content:
   - Page/post title
   - Page/post description
   - Date/time information (if present)
   - Location information (if present)
   - Contact information (if present)

2. Extract metadata:
   - Source URL
   - Platform type (if identifiable)
   - Page/post author (if visible)
   - Media content (images, videos)

3. Extract structured data:
   - Use generic field extraction rules (Section 5)
   - Apply activity_type detection (Section 3)
   - Extract all available fields

4. Map to Activity fields:
   - Apply standard field mapping (Section 5)
   - Use confidence scoring (Section 6)
   - Flag ambiguities (Section 7)
   - Note: Lower confidence scores expected for generic parsing
```

---

## 13. Advanced Parsing Techniques

### 13.1 OCR Techniques for Images

**When to use:**
- Screenshots with text
- Posters and flyers
- Images with structured information

**Techniques:**
- Use GPT vision capabilities for text extraction
- Preserve text hierarchy (title > description > details)
- Extract structured information (dates, times, locations)
- Handle multilingual content

**Confidence scoring:**
- High-quality image → high confidence
- Low-quality image → low confidence, request alternative

---

### 13.2 PDF Parsing Techniques

**When to use:**
- PDF documents (brochures, schedules, event descriptions)
- Multi-page PDFs with structured content
- PDFs with embedded images and text

**Techniques:**
- Extract text content from PDF structure
- Parse tables and lists for structured data (schedules, pricing)
- Extract images and use OCR for image content
- Preserve document hierarchy (headings, sections, lists)
- Handle multi-page documents (merge content across pages)
- Extract metadata (title, author, creation date)

**Confidence scoring:**
- Well-structured PDF with clear text → high confidence
- Scanned PDF (image-based) → medium confidence, use OCR
- Encrypted/password-protected PDF → low confidence, request alternative
- Corrupted or unreadable PDF → low confidence, request alternative

---

### 13.3 Web Scraping Techniques

**When to use:**
- External links to event pages
- Website pages with event/service information
- Social media post links
- Event platform pages (Eventbrite, Facebook Events, etc.)

**Techniques:**
- Extract meta tags (og:title, og:description, og:image)
- Extract structured data (JSON-LD, microdata)
- Parse HTML content for text and structured information
- Extract dates/times from various formats
- Extract location information (address, venue, coordinates)
- Handle platform-specific structures (Eventbrite, Facebook Events, etc.)
- Fallback to text extraction if structured data unavailable

**Confidence scoring:**
- Structured data (JSON-LD, microdata) present → high confidence
- Meta tags present → medium-high confidence
- HTML parsing only → medium confidence
- Inaccessible or blocked link → low confidence, request alternative
- Authentication required → low confidence, request alternative

---

### 13.4 NLP Techniques

**When to use:**
- Free-form text descriptions
- Unstructured narrative text
- Text with ambiguous or implicit information
- Multilingual content

**Techniques:**
- Entity extraction (dates, times, locations, names)
- Named entity recognition (NER) for structured information
- Sentiment analysis (if relevant for context)
- Language detection and handling
- Text classification (event vs service indicators)
- Relationship extraction (dates → events, locations → venues)
- Coreference resolution (pronouns, references)

**Confidence scoring:**
- Explicit information (clear dates, locations) → high confidence
- Implicit information (inferred from context) → medium confidence
- Ambiguous text (multiple interpretations) → low confidence, flag for clarification
- Multilingual content with mixed languages → medium confidence

---

### 13.5 Advanced Confidence Scoring

**When to use:**
- Combining multiple sources of information
- Resolving conflicts between sources
- Calculating overall extraction confidence
- Determining field-level confidence scores

**Techniques:**
- Source quality weighting (structured > semi-structured > unstructured)
- Cross-validation between sources (if multiple sources available)
- Field-specific confidence factors (explicit vs inferred)
- Temporal confidence (recent information > old information)
- Completeness scoring (all required fields present vs missing)
- Conflict resolution confidence (agreement between sources → higher confidence)

**Confidence scoring:**
- Multiple sources agree → high confidence
- Single source, high quality → medium-high confidence
- Single source, low quality → medium confidence
- Conflicting sources → low confidence, flag conflicts
- Missing critical fields → low confidence, flag missing fields

---

## 14. Validation Checklist

### 14.1 Pre-Implementation

- [x] Activity Type Detection algorithm detailed
- [x] All 5 format parsing algorithms documented
- [x] All 14 field extraction rules documented
- [x] Confidence scoring algorithm defined
- [x] Ambiguity handling algorithms detailed
- [x] Error handling strategies documented
- [x] Output contract matches Activity JSON schema
- [x] All 10 edge cases documented
- [x] Integration points defined
- [x] Platform-specific parsing documented (6 platforms)
- [x] Advanced parsing techniques documented

### 14.2 Post-Implementation Testing

- [ ] Test Activity Type Detection (event vs service)
- [ ] Test all 5 format parsing algorithms
- [ ] Test all 14 field extraction rules
- [ ] Test confidence scoring
- [ ] Test ambiguity handling
- [ ] Test error handling (all error types)
- [ ] Test output structure (matches schema)
- [ ] Test all 10 edge cases
- [ ] Test integration with Ingest Validation
- [ ] Test platform-specific parsing (all platforms)

### 14.3 Quality Criteria

- [x] Detailed: specific algorithms for each format
- [x] Format-specific: different algorithms for different sources
- [x] Reliable: error handling and fallback strategies
- [x] Measurable: confidence scores for all fields
- [x] Integrated: clear activation and handoff points

---

## 15. Example Formulations

### 15.1 Free-Form Text Example

**Input:**
```
"Mindfulness Meditation Session
Every Wednesday at 7:00 PM
Location: City Center, Room 101
For adults. Language: English and Russian.
Contact: mindfulness@example.com"
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Mindfulness Meditation Session",
    "full_description": "Every Wednesday at 7:00 PM. Location: City Center, Room 101. For adults. Language: English and Russian.",
    "format": "session",
    "event_timing": {
      "schedule_model": "recurring",
      "recurring": {
        "recurrence_rule": "FREQ=WEEKLY;BYDAY=WE",
        "start_date": "2025-01-01",
        "timezone": "UTC"
      }
    },
    "location_info": {
      "venue": "City Center, Room 101",
      "city": null
    },
    "age_groups": ["adults"],
    "language_requirements": {
      "mode": "mixed",
      "languages_to_understand": ["en", "ru"]
    },
    "delivery_mode": "in_person"
  },
  "metadata": {
    "source_type": "text",
    "confidence_scores": {
      "activity_type": 0.9,
      "title": 0.95,
      "event_timing": 0.85,
      "location_info": 0.8
    },
    "ambiguities": [],
    "missing_required_fields": []
  }
}
```

---

### 15.2 Screenshot Example

**Input:**
```
[Screenshot of Instagram post showing meditation workshop announcement]
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Meditation Workshop: Mindfulness Practice",
    "full_description": "Join us for a transformative meditation workshop focused on mindfulness and inner peace...",
    "format": "workshop",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [
        {
          "start": "2025-02-20T19:00:00Z",
          "end": "2025-02-20T21:00:00Z",
          "timezone": "Europe/Tallinn"
        }
      ]
    },
    "location_info": {
      "venue": "Wellness Center",
      "city": "Tallinn"
    },
    "categories": {
      "primary": {"name": "Wellness", "level": 1},
      "secondary": [{"name": "Meditation", "level": 2}]
    },
    "age_groups": ["adults"],
    "delivery_mode": "in_person"
  },
  "metadata": {
    "source_type": "screenshot",
    "sources": [
      {
        "type": "screenshot",
        "platform": "Instagram",
        "account": "mindfulness_center"
      }
    ],
    "confidence_scores": {
      "activity_type": 0.95,
      "title": 0.9,
      "event_timing": 0.7,
      "location_info": 0.85
    },
    "ambiguities": ["event_timing.date.verification"],
    "missing_required_fields": []
  }
}
```

---

### 15.3 PDF Example

**Input:**
```
[PDF document: 2-page brochure for dance workshop series]
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Dance Workshop: Free Movement",
    "full_description": "A series of classes on free dance and movement expression...",
    "format": "workshop",
    "event_timing": {
      "schedule_model": "recurring",
      "recurring": {
        "recurrence_rule": "FREQ=WEEKLY;BYDAY=SA",
        "start_date": "2025-02-01",
        "end_date": "2025-03-29",
        "timezone": "Europe/Moscow"
      }
    },
    "event_duration": {
      "duration_type": "per_occurrence",
      "per_occurrence": {
        "duration_minutes": 120
      }
    },
    "event_capacity": {
      "max_participants": 20
    },
    "location_info": {
      "venue": "Movement Studio",
      "city": "Moscow"
    },
    "age_groups": ["adults"],
    "delivery_mode": "in_person"
  },
  "metadata": {
    "source_type": "pdf",
    "sources": [
      {
        "type": "pdf",
        "pages": 2,
        "structure": "brochure"
      }
    ],
    "confidence_scores": {
      "activity_type": 0.95,
      "title": 0.95,
      "event_timing": 0.9,
      "location_info": 0.85
    },
    "ambiguities": [],
    "missing_required_fields": []
  }
}
```

---

### 15.4 Link Example

**Input:**
```
"https://eventbrite.com/e/meditation-workshop-123456"
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Meditation Workshop: Mindfulness Practice",
    "full_description": "Join us for a transformative meditation workshop focused on mindfulness and inner peace...",
    "format": "workshop",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [
        {
          "start": "2025-02-15T10:00:00Z",
          "end": "2025-02-15T12:00:00Z",
          "timezone": "UTC"
        }
      ]
    },
    "event_pricing": {
      "pricing_type": "ticket_price",
      "ticket_price": {
        "amount": 50,
        "currency": "EUR"
      }
    },
    "event_capacity": {
      "max_participants": 30,
      "seats": 25
    },
    "location_info": {
      "venue": "Community Center",
      "address": "123 Main St",
      "city": "Tallinn"
    },
    "event_cta": {
      "event_page_link": "https://eventbrite.com/e/meditation-workshop-123456",
      "tickets_link": "https://eventbrite.com/e/meditation-workshop-123456/tickets"
    },
    "categories": {
      "primary": {"name": "Wellness", "level": 1},
      "secondary": [{"name": "Meditation", "level": 2}]
    },
    "age_groups": ["adults"],
    "delivery_mode": "in_person"
  },
  "metadata": {
    "source_type": "link",
    "sources": [
      {
        "type": "link",
        "url": "https://eventbrite.com/e/meditation-workshop-123456",
        "platform": "Eventbrite"
      }
    ],
    "confidence_scores": {
      "activity_type": 0.95,
      "title": 0.95,
      "event_timing": 0.95,
      "event_pricing": 0.9,
      "location_info": 0.9
    },
    "ambiguities": [],
    "missing_required_fields": []
  }
}
```

---

### 15.5 Mixed Content Example

**Input:**
```
[Text description + Instagram screenshot + link to event page]
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Yoga Retreat Weekend",
    "full_description": "Join us for a transformative weekend yoga retreat in the mountains...",
    "format": "retreat",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [
        {
          "start": "2025-03-15T09:00:00Z",
          "end": "2025-03-17T17:00:00Z",
          "timezone": "Europe/Tallinn"
        }
      ]
    },
    "event_pricing": {
      "pricing_type": "ticket_price",
      "ticket_price": {
        "amount": 300,
        "currency": "EUR"
      }
    },
    "location_info": {
      "venue": "Mountain Retreat Center",
      "city": "Lahemaa"
    },
    "categories": {
      "primary": {"name": "Wellness", "level": 1},
      "secondary": [{"name": "Yoga", "level": 2}]
    },
    "age_groups": ["adults"],
    "delivery_mode": "in_person",
    "event_cta": {
      "event_page_link": "https://example.com/yoga-retreat"
    }
  },
  "metadata": {
    "source_type": "mixed",
    "sources": [
      {"type": "text", "content": "Yoga Retreat Weekend..."},
      {"type": "screenshot", "platform": "Instagram", "account": "yoga_center"},
      {"type": "link", "url": "https://example.com/yoga-retreat", "platform": "Generic Website"}
    ],
    "confidence_scores": {
      "activity_type": 0.95,
      "title": 0.95,
      "event_timing": 0.9,
      "event_pricing": 0.85,
      "location_info": 0.9
    },
    "ambiguities": [],
    "missing_required_fields": [],
    "conflicts": []
  }
}
```

---

### 15.6 Ambiguity Handling Example

**Input:**
```
"Workshop next week. Location: city center. Time: evening."
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": "event",
    "title": "Workshop",
    "full_description": "Workshop next week. Location: city center. Time: evening.",
    "format": "workshop",
    "event_timing": {
      "schedule_model": "fixed_dates",
      "fixed_dates": [
        {
          "start": "2025-01-20T18:00:00Z",
          "end": "2025-01-20T20:00:00Z",
          "timezone": "UTC"
        }
      ]
    },
    "location_info": {
      "city": "city center"
    },
    "delivery_mode": "in_person"
  },
  "metadata": {
    "source_type": "text",
    "confidence_scores": {
      "activity_type": 0.7,
      "title": 0.5,
      "event_timing": 0.4,
      "location_info": 0.3
    },
    "ambiguities": [
      "title",
      "event_timing.date",
      "event_timing.time",
      "location_info.city",
      "location_info.venue"
    ],
    "missing_required_fields": [
      "full_description",
      "format"
    ]
  }
}
```

**Response to user:**
```
I've extracted some information from your input, but several details need clarification:

1. **Title**: Could you provide the full title of the workshop?
2. **Date**: "next week" is ambiguous. What is the exact date?
3. **Time**: "evening" is vague. What is the specific start time?
4. **Location**: "city center" needs more details. What is the exact venue or address?
5. **Description**: Could you provide a more detailed description of the workshop?

Please provide these details so I can create a complete Activity entry.
```

---

### 15.7 Error Handling Example

**Input:**
```
[Encrypted PDF document that cannot be parsed]
```

**Extracted:**
```json
{
  "extracted_data": {
    "activity_type": null
  },
  "metadata": {
    "source_type": "pdf",
    "confidence_scores": {},
    "ambiguities": [],
    "missing_required_fields": [
      "activity_type",
      "title",
      "full_description"
    ],
    "parsing_errors": [
      {
        "error_type": "encrypted_pdf",
        "message": "The PDF is password-protected and cannot be parsed.",
        "severity": "high"
      }
    ]
  }
}
```

**Response to user:**
```
I encountered an issue while processing your PDF:

**Error**: The PDF is password-protected and cannot be parsed.

**What you can do:**
- Provide an unencrypted version of the PDF
- Share the content as a screenshot
- Copy and paste the text content directly
- Provide a more detailed description

I cannot bypass password protection for security reasons. Please provide the content in one of the alternative formats listed above.
```

---

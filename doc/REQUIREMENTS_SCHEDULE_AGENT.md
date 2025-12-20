# Schedule Agent Requirements

**Author:** isms01  
**Created:** 2025-12-20  
**Status:** Draft v1.0

---

## 1. Overview

Schedule Agent is the first practical agent in the Agent Organization. It connects to Google Calendar and helps users manage their schedules through natural language.

**Core Principle:** The agent is a team member, not just a tool. It always explains what it's doing and asks for user confirmation before any action.

---

## 2. Features

### 2.1 Add Events

- Add events to Google Calendar via natural language
- Check events before and after the new event
- Detect conflicts and suggest alternatives
- Show travel time issues if applicable


### 2.2 Delete Events

- Delete events from Google Calendar
- Show clear target when input is ambiguous
- Notify impact of deletion


### 2.3 User Confirmation (Most Important)

- **Always confirm before any action**
- Show what, when, and why clearly
- Allow cancel at any time

---

## 3. User Flow

### 3.1 Add Event (Normal)

```
User: "Meeting with Tanaka tomorrow at 2pm for 1 hour"

Agent: [Checks calendar]
       - 1pm-2pm: Lunch (OK)
       - 3pm-4pm: Free (OK)

Agent: "I'll add this event. OK?"
       
       📅 2025-12-21
       ⏰ 2:00 PM - 3:00 PM
       📝 Meeting with Tanaka
       
       ✅ No conflicts
       
       [Yes] [No] [Change time]

User: "Yes"

Agent: ✅ Added to calendar
```


### 3.2 Add Event (Conflict)

```
User: "Meeting with Sato tomorrow at 2pm"

Agent: [Checks calendar]
       - 2pm-3:30pm: Existing meeting (CONFLICT!)

Agent: "⚠️ Conflict detected"
       
       2:00-3:30 PM already has "Weekly standup"
       
       💡 Suggestions:
       1. 4:00 PM - 5:00 PM (free)
       2. 1:00 PM - 2:00 PM (after lunch)
       3. Move existing event
       
       Which one?
```


### 3.3 Delete Event

```
User: "Cancel tomorrow's meeting"

Agent: [Searches calendar]

Agent: "Delete this event?"
       
       🗑️ Target:
       📅 2025-12-21 2:00-3:00 PM
       📝 Meeting with Tanaka
       
       ⚠️ This cannot be undone
       
       [Delete] [Cancel]

User: "Delete"

Agent: ✅ Deleted
```

---

## 4. Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Agent | LangGraph |
| Calendar | Google Calendar API |
| Auth | OAuth 2.0 |

---

## 5. Implementation Phases

| Phase | What | Time |
|-------|------|------|
| 1 | Google Calendar connection + read events | 1 week |
| 2 | Add events + confirmation flow | 1 week |
| 3 | Conflict detection + suggestions | 1 week |
| 4 | Delete events + error handling | 1 week |

---

## 6. Success Criteria

- Zero actions without user confirmation
- All known conflict patterns covered by unit tests
- Zero false negatives in test cases
- Clear and simple user interaction

> Note: Removed "Conflict detection rate > 95%" — unmeasurable KPIs should not be included.

---

## 7. Next Steps

1. Set up Google Calendar API credentials
2. Build basic read/write prototype
3. Implement confirmation flow
4. Write test cases
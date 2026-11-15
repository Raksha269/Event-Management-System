# Local organizer: user-performed NVDA observations

Tester: Raksha269, using the isolated PR #39 checkout at localhost:8765 with `.accessibility/test.sqlite3` and in-memory email. Synthetic account: `a11y_organizer`. Earlier session metadata: NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit), Windows 11 Home Single Language 26H2 (26300.9974). Per-step timestamp, zoom, viewport dimensions and local Git revision were not separately captured.

## Organizer dashboard

After failed login attempts, a read-only local check confirmed active status, correct test-password hash, organizer role, verified email and no lock. The user subsequently reset this synthetic local account's password and failure counters, and a local `authenticate` call returned True. The user then logged in successfully; the application redirected to registration (the known login redirect), after which manual navigation to http://localhost:8765/events/ loaded `Organizer Dashboard | Gather`.

A supplied screenshot shows the authenticated organizer's empty dashboard and `No events created yet`. Later speech contains named links `gather.`, `Discover Events`, `My Events`, `My Profile`, `+ Create New Event` and `+ Create Your First Event`. Attempts to inspect headings also invoked Edge caret browsing and changed Elements List categories. No organizer heading level or complete no-trap traversal is established from those attempts. Browser/Elements List controls are excluded from application-control results.

## Event creation default form

URL: http://localhost:8765/events/create/ . Relevant user-supplied speech, with wrapping normalized:

```text
Create New Event | Gather
Discover Events link
My Events visited link
My Profile link
Log out button
Back to Organizer Dashboard visited link
form landmark
Event Title * edit e.g., Tech Innovations Summit 2026 blank
Description edit multi line Detailed description of the event... blank
Category * edit selected General
Venue * edit required has auto complete e.g., Bangalore International Exhibition Centre blank
Date & Time * date edit required invalid entry
Day Date & Time * spin button 0
Show local date and time picker Date & Time * menu button subMenu
Event Capacity (Max Attendees) * spin button required editable selected 100
Base Ticket Price (₹) * spin button required editable selected 0.00
Create Event (Save as Draft) button
Cancel visited link
```

An additional generic `clickable button` was reported without an identified source; it is not counted as a verified named application control. The supplied speech supports accessible names/roles for the listed controls, not successful operation of every control. The initial empty date was announced invalid. Event Title includes a visual/announced asterisk but was not announced required; the error test below did not produce a title error. Required-state consistency is a review finding, not a passed requirement.

## Invalid default-form submission

The user followed the instruction to leave defaults unchanged and activate Create Event. Supplied speech:

```text
Loading complete
Create New Event | Gather document
main landmark
form landmark
alert
Please correct the following errors heading level 2
list
level 1 list item 1 of 2
Venue: This field is required. link same page
list item 2 of 2 level 1
Date: This field is required. link same page
```

This supports automatic error-summary announcement for missing Venue and Date. It does not independently establish the exact focused DOM node or database row counts. A successful event creation was not evidenced. No production service was used.

## Subsequent error-link and field speech

Following instructions to activate each summary link and report the focused control with NVDA+Tab, the user supplied:

```text
Venue: This field is required. same page link
Venue * edit required invalid entry This field is required. e.g., Bangalore International Exhibition Centre blank

Date: This field is required. same page link
Date & Time * date edit required invalid entry This field is required.
Day Date & Time * spin button 0 This field is required.
```

These user-supplied speech sequences support Venue and Date summary links reaching their corresponding controls and exposing the required/invalid states and associated required-field descriptions. They also capture the native date control's Day subcontrol speech. This does not establish all date-picker interactions or validation of populated values.

## Event-form zoom and keyboard observation

After instructions to set Edge zoom to 200%, scroll through the local event form and use Tab/Shift+Tab, the user supplied further control speech and explicitly reported no overlapping text, missing controls, horizontal scrolling or keyboard trap at 200%. This is a user-reported layout/traversal result, not an independently reproduced or screenshot-measured 200% check. The speech includes the date edit/Day spin button/date-picker menu, capacity, price, submit, Cancel and form fields; the generic `clickable button` / `button` lines remain unidentified and are not counted as named application controls. No complete per-control reverse sequence or viewport dimensions were supplied. The result applies to this invalid event-form state, not the entire organizer workflow.

## Populated local draft and capacity error

The user attempted a synthetic event creation and supplied speech showing `Capacity: Capacity must be greater than zero` in the error summary, followed by capacity field speech `required invalid entry editable Capacity must be greater than zero 0`. After changing capacity, submission returned to Organizer Dashboard. A supplied screenshot shows a success banner, one `Accessibility Test Event` card in Draft status, category Workshop, local test hall and 0/10 capacity. It also shows Tickets (0). This supports local draft creation and the capacity validation/correction sequence, not publication or registration success.

The screenshot displays 14 November 2030, 4:53 p.m. The suggested test value had been 15 January 2030, 10:00; the reason for the different saved date has not been established. Do not assert the originally suggested date was entered successfully or conclude a date-picker defect from the difference alone.

## Populated organizer card traversal

The user supplied the following forward/reverse speech sequence on localhost:

```text
Accessibility Test Event link heading level 2
View link
Edit link
Tickets (0) link
Report link
Publish button
Report link
Tickets (0) link
Edit link
View link
Accessibility Test Event link heading level 2
+ Create New Event visited link
Log out button
My Profile link
My Events visited same page link
Discover Events link
```

This supports named card controls and traversal in both directions through this segment. It is not evidence that each action was activated, every interaction is free of traps, or that names remain distinguishable with multiple event cards. Unrelated browser/tab speech was excluded. No populated-card 200% zoom result was supplied at this point.

These are user-performed reports/transcripts, not independent NVDA reproduction. Still pending: complete control interactions (including native date picker), populated-card zoom observations, ticket tiers, publication/edit/reporting and other agreed flows, manual contrast and independent/review evidence. #36, #37 and parent #9 remain open.

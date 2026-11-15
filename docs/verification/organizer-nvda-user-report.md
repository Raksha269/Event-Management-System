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

These are user-performed reports/transcripts, not independent NVDA reproduction. Still pending: organizer 200% zoom observations, complete forward/reverse keyboard interactions, populated organizer workflows, ticket tiers, publication/edit/reporting and other agreed flows, manual contrast and independent/review evidence. #36, #37 and parent #9 remain open.

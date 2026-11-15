# Local mock payment and ticket: user-performed observations

Tester: Raksha269. Synthetic account: a11y_attendee. Isolated localhost:8765 instance using `.accessibility/test.sqlite3` and in-memory email, on the PR #39 branch. Session environment previously supplied: NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit), Windows 11 Home Single Language 26H2 (26300.9974). Per-step exact execution times, local source revision and viewport/zoom were not captured.

## Free-event payment finding

The first fixture, Accessibility Test Event, was intentionally configured at ₹0.00 based on assistant guidance. After Pay Now attempts, user speech/screenshot still shows Pending and Pay Now. A screenshot shows a red banner whose text is obscured by Speech Viewer; the exact error wording is not evidenced. Source inspection of `mock_payment_gateway` confirms `amount <= 0` returns failure. This fixture cannot validate the positive-payment path. Do not mark the free registration confirmed or attribute the failure to NVDA. Free-event confirmation behavior requires separate product review.

## Separate ₹1 fixture and control ambiguity

To preserve the free-event finding, the user created a separate synthetic fixture through an asserted local-SQLite shell command: Local Paid Accessibility Test, event 2, published status, future date, capacity 10, event price ₹1.00 and General tier ₹1.00/quantity 10. This is test setup, not UI creation/publication evidence. The user output confirms `http://localhost:8765/events/2/`. Subsequent speech still shows General Admission selected; use of the named General tier is not established.

The registration dashboard contained multiple Pay Now buttons with the same spoken name. Supplied speech shows an attempt on the earlier Accessibility Test Event rather than the paid fixture. The user was guided to locate the correct event heading before activating its button. This is a contextual-disambiguation usability/accessibility finding; distinct event-specific button names and retesting remain follow-up work, not completed fixes.

## Positive mock payment result

The supplied speech after selecting the correct card includes:

```text
Local Paid Accessibility Test heading level 2 visited link
Pay Now button
Loading page
Loading complete
My Registrations | Gather
Confirmed link View Ticket
```

A supplied screenshot at `/events/my-registrations/` shows Welcome, a11y_attendee, the Local Paid Accessibility Test card, quantity 1, General Admission, Confirmed and View Ticket. The green banner is partly obscured. This supports a successful local mock payment/confirmation and named ticket link, not automatic full success-message announcement or real gateway integration. No real payment details were used. Database payment amounts were not independently inspected during this guided step.

## Ticket details and QR alternative

Following View Ticket loaded `http://localhost:8765/events/registrations/2/ticket/`. A supplied screenshot shows the synthetic event, Confirmed, attendee, date, Local Test Hall, quantity 1, General Admission and a QR image. Initial Tab speech exposes Back to My Registrations and navigation, plus an unidentified generic button; the latter is not counted as a named application control.

After instructions to use browse-mode reading and graphic navigation, the user supplied text containing:

```text
Local Paid Accessibility Test
Present this ticket at the event entrance.
Ticket Code: [synthetic ticket code]
QR code for ticket [same synthetic ticket code]
Your Ticket QR Code
Ticket Type: General Admission
Quantity: 1
Local Test Hall
Dec 15, 2026, 11:43 a.m.
Attendee: a11y_attendee
```

The synthetic UUID is replaced with a placeholder here; labels/values are grouped for readability rather than asserted as the original reading order. The raw user text repeated some values and read others out of label/value order. This supports access to those textual ticket details and a QR alternative identifying the ticket code. It does not establish visual/reading-order correctness, successful QR scanning/check-in, every graphic-navigation step, or actual typed-password masking.

This is user-performed evidence, not independent NVDA reproduction. Ticket/populated-dashboard 200% layout, full keyboard interaction, manual contrast, refund/cancellation and other agreed cases remain pending. #36, #37 and parent #9 remain open for remaining scope, findings and evidence review.

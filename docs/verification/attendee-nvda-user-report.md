# Local attendee empty dashboard: user-performed checks

Tester: Raksha269. URL: http://localhost:8765/events/my-registrations/ . The user created the synthetic local account `a11y_attendee` in `.accessibility/test.sqlite3`, with in-memory email, and logged in. A supplied screenshot shows that username in the navigation and the empty-registration message. This is the user's isolated PR #39 checkout, not Render.

Environment supplied earlier in the session: NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit), Windows 11 Home Single Language 26H2 (26300.9974). Exact test time, viewport dimensions and local revision were not separately captured.

The screenshot's Speech Viewer text includes `main landmark heading level 1 My Registrations`. Subsequent supplied speech includes named `gather.`, `Discover Events` and `My Profile` links and `Log out button`. The user was instructed to traverse forwards/backwards with Tab/Shift+Tab and subsequently reported no keyboard trap. The transcript does not provide a complete per-control traversal or separately establish the Explore Events control's announcement.

The supplied transcript shows browser zoom stepping through several levels before returning to `Zoom 200%` / `Zoomed out, 200 percent`. The user then confirmed no overlapping text, missing controls or horizontal scrolling on the webpage at 200%. That layout result is user-reported; no 200%-zoom screenshot or measured viewport width was supplied. Browser toolbar/menu controls in the transcript are not counted as application controls.

Scope: authenticated attendee dashboard with zero registrations. It does not verify populated registrations, payment, tickets, cancellation/refund, profile actions, other authenticated pages, full keyboard operability, manual contrast, or all reflow criteria. The original screenshot shows the empty state at an unrecorded zoom level. No production account or production data was used. These are user-performed observations, not independently reproduced NVDA speech.

Login usability finding: a successful login led to Create Account before the user navigated manually to My Registrations. Source inspection confirms `login_view` redirects successful logins to `register` and does not honor the requested dashboard destination. The authenticated dashboard subsequently loaded. Do not misclassify that intermediate page as an authentication failure; the redirect remains a separate usability finding, not fixed by this evidence update.

## Subsequent populated local registration

An initial event-detail transcript still contained organizer-only Edit Event/Manage Tickets/Unpublish actions and was not counted as attendee evidence. The user subsequently logged in as attendee; a screenshot at `localhost:8765/events/1/` shows `Welcome, a11y_attendee`. Before submission, speech captures `Select Ticket Type combo box General Admission collapsed`, `Quantity spin button required editable selected 1` and `Register Now button`, with organizer actions absent.

The user activated Register Now once on this synthetic local event. The supplied screenshot shows a green result banner (partly obscured), total capacity 10 and `9 Spots Available`. The selected control still announces General Admission; do not infer that the named `general` ticket tier was selected. Its relationship to the configured tier is not established by this check. No production registration was created.

Manual navigation to `http://localhost:8765/events/my-registrations/` then produced:

```text
My Registrations | Gather
My Registrations heading level 1
View and manage your event registrations.
Discover Events visited link
Accessibility Test Event visited link heading level 2
Pay Now button
```

This supports a populated local attendee registration card and named payment action, not completed payment or ticket issuance. An additional generic `clickable button` remains unidentified. No populated-dashboard zoom/reverse traversal or automatic full success-message speech is established by this extract. Payment/ticket/refund behavior and other agreed checks remain pending.

#36, #37 and parent #9 remain open for the remaining agreed workflow scope and evidence review.

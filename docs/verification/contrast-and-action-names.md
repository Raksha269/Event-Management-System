# Sampled contrast and repeated action names

This is a source-palette calculation and scoped local browser check, not a complete manual contrast audit or user NVDA retest of the changes below.

## Solid-color palette calculations

Ratios use sRGB channels linearized at 0.04045, relative luminance coefficients 0.2126/0.7152/0.0722, and `(lighter + 0.05) / (darker + 0.05)`. Values are rounded for reporting; thresholds are 4.5:1 for normal text and 3:1 for necessary control boundaries. These samples assume the stated opaque foreground/background pairs, not arbitrary composited/hover/disabled states.

| Sample | Foreground / background | Ratio | Result/action |
| --- | --- | ---: | --- |
| Previous shared form-control boundary | #e1e8f2 / white | 1.233 | Below 3:1; replace control boundary color |
| Previous registration input boundary | #cbd5e1 / white | 1.485 | Below 3:1; replace control boundary color |
| New input boundary | #64748b / white | 4.759 | Exceeds 3:1 in this pair |
| New input boundary against page background | #64748b / #f3f6fb | 4.393 | Exceeds 3:1 in this pair |
| Blue primary button text / focus indicator | white / #2563eb (or inverse) | 5.169 | Exceeds sampled text/indicator thresholds |
| Blue focus indicator against page background | #2563eb / #f3f6fb | 4.771 | Exceeds 3:1 in this pair |
| Previous error alert text | #dc2626 / #fee2e2 | 3.953 | Below 4.5:1; darken shared danger color |
| New error alert text | #b91c1c / #fee2e2 | 5.296 | Exceeds 4.5:1 in this pair |
| Shared muted text on white | #475569 / white | 7.578 | Exceeds 4.5:1 |
| Confirmed badge | #15803d / #dcfce7 | 4.567 | Exceeds 4.5:1 |
| Pending badge | #b45309 / #fef3c7 | 4.510 | Exceeds 4.5:1 narrowly; do not round a failing ratio upward |
| Discovery category badge | #0369a1 / #e0f2fe | 5.171 | Exceeds 4.5:1 |

Shared `.form-control` and registration inputs now use a distinct darker control-border variable, preserving decorative card borders. Their focus outline now uses the darker blue. Shared danger text is darkened. This does not establish all UI/text/placeholder/focus contrasts, every inline style, browser rendering or WCAG conformance.

## Repeated attendee actions

The guided user test selected the wrong event's Pay Now button when multiple cards had the same name. The attendee template now exposes `Pay Now for <event title>` and `View Ticket for <event title>` as accessible names while retaining the visible action text. A local render check using three distinct synthetic pending-event cards verified three distinct Pay Now names. Duplicate event titles can still produce duplicate names; not all repeated actions across the application have been audited.

After guided git pull and server restart, the user supplied NVDA speech on local My Registrations containing `View Ticket for Local Paid Accessibility Test visited link` and `Pay Now for Accessibility Test Event button`, with both event headings also present. This is a user-performed retest confirming event-specific names for those two controls, not independent reproduction or evidence for every repeated action. Additional generic `clickable button` / `button` speech remained unidentified and is not attributed to an application defect or counted as a verified named control. No new payment or ticket activation was requested in this naming retest.

## Verification and boundaries

The focused three-test module passes; log: `contrast-label-tests.txt`. The eight-page local headless Chromium/axe check was rerun; see `accessibility/contrast-browser-results.json` and `contrast-template-manifest.json`. It reports no tagged axe violations and no horizontal overflow at 360/768/1440 px for the sampled default states. Axe incomplete checks are retained and are not passes. Browser/version, time and base revision are in the JSON; the manifest identifies the modified template contents. `contrast-*-360.png` files capture selected new styles; the earlier evidence files are preserved separately.

This rerun's local attendee fixture contains three synthetic pending registrations to exercise repeated names; it is distinct from the user's free/pending and paid/confirmed fixtures. The local organizer still has three synthetic events. Invalid registration/event-form submissions were also rechecked by script for summary focus and resolving description IDs. No production traffic/data, real screen reader, full manual UI contrast audit or live deployment retest was involved. #36/#37 and parent #9 remain open for remaining scope and review.

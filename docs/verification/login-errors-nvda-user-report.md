# Local login: NVDA invalid-credentials check

Tester: Raksha269, performing guided verification on the isolated PR #39 checkout at http://localhost:8765/accounts/login/ . The local instance uses `.accessibility/test.sqlite3` and in-memory email. The guided test supplied the synthetic username `a11y_nonexistent_user` and a local-only test password, not a production account.

Environment supplied earlier in this session: NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit), Windows 11 Home Single Language 26H2 (26300.9974). Exact execution time, viewport, zoom and local revision were not separately captured for this step.

## Observations supplied by the user

After activating Log in, the initial Speech Viewer text included:

```text
Log in button
Loading page
Loading complete
Login | Gather
alert
list
list item 1 of 1 level 1
```

The initial message text was truncated in the supplied extract. After being asked to read the visible message, the user supplied:

```text
Please enter a correct username and password. Note that both fields may be case-sensitive.
Please enter a correct username and password. Note that both fields may be case-sensitive.
```

This supports an announced alert after invalid credentials and user-performed screen-reader access to the full generic error message. The full message was captured during the follow-up read, so do not assert it was automatically spoken in full immediately after submission. Several additional `button Log in` announcements occurred during attempts to read the message; these do not establish the automatic post-submit focus destination. That destination was not reported.

Repeated UI speech and unrelated Speech Viewer controls are omitted; no password content is retained. This is user-performed supporting evidence, not independent NVDA reproduction. It does not establish successful login, lockout behavior, field-specific focus transfer, other errors, or production behavior. The empty-registration check is documented separately. #36, #37 and parent #9 remain open for the remaining agreed verification and review.

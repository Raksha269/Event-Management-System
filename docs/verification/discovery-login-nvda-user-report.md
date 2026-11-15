# Discovery and login: user-reported NVDA checks

Tester: Raksha269. This records the user's subsequent confirmation in the guided verification conversation, not an independently reproduced test.

## Reported scope

- Discover Events: https://event-management-system-cqxx.onrender.com/events/discover/
- Login: https://event-management-system-cqxx.onrender.com/accounts/login/

The user confirmed using NVDA with Tab and Shift+Tab on both pages, hearing meaningful control announcements, and encountering no keyboard traps or other problems during those checks. A complete per-control speech transcript and video were not supplied. Do not infer particular control announcements, visible-focus results or successful actions from this general confirmation.

## Subsequent heading-list evidence

The user subsequently supplied screenshots during guided NVDA Elements List checks:

- Discovery: Headings was selected and the list/Speech Viewer exposed `Discover Upcoming Events` and `No events found`. This supports heading discoverability for the empty discovery state. The screenshot was taken with ChatGPT visible behind the NVDA dialog; the preceding screenshot showed the Elements List opened on Discovery. It is not independent reproduction or evidence of populated cards.
- Login: the URL bar showed `/accounts/login/`, Headings was selected, and Speech Viewer showed `Elements List` followed by `Welcome back`. This supports discoverability of the login heading.

The screenshots were reviewed in this conversation; image files have not been copied into this repository. No HTML heading level is inferred from the dialog's tree-position announcement `level 0`. These results supersede the earlier absence of heading-discoverability evidence, not the absence of exact per-control speech or a full hierarchy audit.

The preceding registration check recorded NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit) and Windows 11 Home Single Language 26H2 (26300.9974). These are context from that session; the user did not separately record environment versions, execution time, viewport or zoom for each additional page. No recording is available, as clarified by the user.

## Evidence boundary and follow-up

This is user-performed supporting evidence for limited guest-page screen-reader/keyboard operation, not a full accessibility pass. Exact per-control announcements remain undocumented for these pages. Populated discovery layouts, form submission/error announcements, authenticated workflows and contrast are not established by these observations. A separate user-reported zoom check is recorded in `zoom-user-report.md`. No successful login, production submission or database mutation is claimed. Preserve remaining checks as pending until separately evidenced and reviewed.

Issue #36, #37 and parent #9 remain open; uptime observation is separate. For a reproducible per-control result, record a fresh Speech Viewer extract with page-specific environment metadata, steps and outcomes. A video is not asserted as a requirement unless the agreed evaluation criteria require it.

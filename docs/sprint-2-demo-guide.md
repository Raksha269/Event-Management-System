# Sprint 2 working-product video guide

Target duration: 2 minutes. Use synthetic local data and accounts. This is a product demonstration, not proof of every acceptance criterion.

## Prepare before recording

1. Keep the local server running and confirm the selected commit/version.
2. Use a published synthetic event with a paid mock ticket tier and a confirmed synthetic registration with View Ticket available. Preserve existing verification fixtures; create a separate demo event if needed.
3. Prepare organizer, attendee and administrator sessions in separate browser profiles so switching roles does not interrupt the recording. Never display passwords, session cookies, personal notifications or terminal secrets.
4. Close unrelated tabs and notifications. Reset browser zoom for a readable recording; keep NVDA audio only if it is part of the intended demonstration.
5. Rehearse the exact sequence. Use OBS Studio or a screen recorder that captures the browser. Play a short test recording to verify sound and text readability.

## Suggested 2-minute sequence and narration

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:10 | Product home/discovery | “Gather is our Event Management System. Sprint 2 focuses on the completed workflows, administrator tools and verification.” |
| 0:10–0:35 | Organizer dashboard, event edit and Manage Tickets | “Organizers manage their own events, ticket prices and quantities. The dashboard shows publication state and capacity.” Show saved synthetic data; avoid slow account entry. |
| 0:35–1:05 | Attendee discovery, event details, My Registrations and confirmed View Ticket | “Attendees discover events and register. Our mock payment workflow confirms the registration and generates a QR ticket.” Use a pre-confirmed example if payment was not performed on camera; say it is already confirmed. |
| 1:05–1:30 | User Administration and Security Alerts | “Administrators filter users and manage security alerts. Actions are restricted by role.” Show controls and resolved/active synthetic alerts without changing real accounts. |
| 1:30–1:45 | Narrow viewport or invalid-form error summary | “We verified responsive layouts, keyboard navigation and NVDA announcements for the documented flows.” Show one concise example. |
| 1:45–2:00 | Successful CI summary, then product | “Django and PostgreSQL checks passed for the recorded commit. The accepted NFR scope and limitations are documented; monthly availability is not claimed.” |

If showing all this makes the product unreadable or rushed, keep the CI explanation for the live presentation and give those seconds to product actions. Show Render deployment only when you can demonstrate its actual configuration; do not label local execution as CD.

## Save and hand off

- Suggested filename: `sprint-2-demo.mp4`.
- Watch the entire recording and check the duration, audio, readability and absence of private information.
- The evaluation checklist asks for the video uploaded to the repository. Use `docs/videos/` if the file fits GitHub limits; for a large file, confirm whether an accessible release attachment or externally hosted link meets the evaluator’s requirement.
- Record the final location in README and `docs/finalization.md`. Do not upload credentials or private account information.
- This guide does not create or upload a video. Sprint 1’s separate 1-minute recording is also required by the checklist.

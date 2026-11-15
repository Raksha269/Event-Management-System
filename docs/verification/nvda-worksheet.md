# Windows / NVDA screen-reader worksheet (#36)

Status: PARTIAL EVIDENCE EXISTS IN LINKED USER-PERFORMED REPORTS; this worksheet has not been independently executed by the reviewer. Owner: Raksha269. Do not copy expected names into actual-announcement columns without hearing them. For the wider outstanding workflow matrix, see [Issue #36/#37 follow-up](accessibility/issue-36-37-followup-2026-11-15.md).

1. On Windows, start NVDA (install from https://www.nvaccess.org/download/ if needed). Open NVDA's menu with NVDA+N; record Help → About version. NVDA normally uses Insert or Caps Lock as its modifier, depending on keyboard configuration.
2. Record Windows version (`winver`) and browser version (Chrome/Edge Help → About, or the product version on `chrome://version` / `edge://version`). Do not post profile paths or account details.
3. In NVDA's menu, enable Tools → Speech Viewer. This displays actual NVDA speech and can be used to copy the announcements. Record date, page URL and viewport/zoom.
4. Open https://event-management-system-cqxx.onrender.com/accounts/register/ at 100% zoom. Do not submit or create a live account. Press Tab through the controls. Use NVDA+Tab to report the currently focused object when needed. If speech is not heard, record that and troubleshoot rather than mark a pass.
5. For each control, copy the actual Speech Viewer text and record whether the accessible name, role and state make sense. Password input must not expose typed characters; only use synthetic values and do not include passwords in screenshots or transcripts. Empty field focus alone does not verify masking of typed content.

Environment: Windows version ___; NVDA version ___; browser/version ___; date/time/timezone ___; exact URL ___; tester ___; zoom ___; keyboard layout/NVDA modifier ___ .

| Step/control | Expected check (not an observed announcement) | Actual words heard | Result/defect |
| --- | --- | --- | --- |
| gather. | Meaningful link name/role | PENDING | PENDING |
| Discover Events | Link name/role | PENDING | PENDING |
| Navigation Sign in | Link name/role | PENDING | PENDING |
| Navigation Create account | Link name/role | PENDING | PENDING |
| Username | Name, editable role, required state | PENDING | PENDING |
| Email address | Name and editable role; record actual required/optional state | PENDING | PENDING |
| Password | Name, protected/password state, required state | PENDING | PENDING |
| Confirm password | Name, protected/password state, required state | PENDING | PENDING |
| Create account | Button name/role | PENDING | PENDING |
| Footer Sign in | Link name/role | PENDING | PENDING |
| Reverse navigation | Shift+Tab returns in usable order without a trap | PENDING | PENDING |
| Page structure | NVDA browse-mode heading navigation (H) finds Create your account, level 1 | PENDING | PENDING |

Record link/button activation only on safe navigation links; never activate the live submit button. For validation/error focus, invalid descriptions, authentication and other state changes, use isolated staging with synthetic accounts and record its distinct URL. Test the patched error summary only after the PR is available in that staging environment. Do not attribute local patches to the deployed Render site.

Attach a redacted speech transcript or short recording, list any defects and retest them. Mark other public/authenticated workflows pending until separately tested. A registration-only pass does not close #36 or #9 if the agreed scope includes other workflows.

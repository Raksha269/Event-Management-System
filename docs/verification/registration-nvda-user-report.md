# Registration: user-performed NVDA spot check

Evidence supplied in this conversation by Raksha269 on 15 November 2026. Exact execution time, viewport and zoom were not recorded. This test was guided remotely; the assistant did not run NVDA on the user's computer or independently reproduce its speech.

## Environment and scope

- URL: https://event-management-system-cqxx.onrender.com/accounts/register/
- Windows 11 Home Single Language, version 26H2, OS build 26300.9974 (user screenshot).
- NVDA 2026.3.1, build 2026.3.1.58288 (user supplied).
- Microsoft Edge 157.0.4341.46, Official build, 64-bit (user supplied).
- Method: user navigated the public registration page with NVDA running and supplied Speech Viewer text and a screenshot. The user was instructed to Tab through controls without activating submit. No completed registration or form-submission outcome is evidenced.

## Relevant actual Speech Viewer text

The extract below preserves the relevant user-supplied words, with line wrapping normalized. Duplicate copies, unrelated desktop/ChatGPT/Snipping Tool output, notifications and a personal autofill identifier are excluded.

```text
Create Account | Gather document
visited same page link Create account
Create Account | Gather document
main landmark
form landmark
Username edit required has auto complete Choose a username blank
Suggestion available
Email address edit you@example.com blank
has auto complete
Suggestion available
Password edit protected required blank
has auto complete
Suggestion available
Confirm password edit protected required blank
has auto complete
Create account button
Sign in visited link
clickable button
clickable button
```

## Interpretation and limits

The supplied transcript supports named editable fields for Username and Email address, named protected editable fields for Password and Confirm password, required-state announcements for Username and both password fields, a named Create account button and a Sign in link. Email was not announced as required. Page title, main and form landmarks were announced.

The two generic `clickable button` announcements are retained as observations. Their source controls are not identified; do not attribute them to the page or browser chrome, or count them as confirmed accessible named controls. Follow up by focusing each source and recording NVDA+Tab output and the visibly focused element.

This does not verify typed-password masking, required-email correctness, activation behavior, server validation/error announcements, heading navigation, reverse traversal/no traps, zoom/reflow, contrast, other public pages or authenticated workflows. It does not verify the local error-summary fixes in PR #39 on the deployed site. The transcript is scoped supporting evidence for #36, not full screen-reader or WCAG completion. #36 and parent #9 remain open pending the agreed scope and evidence review; uptime observation is separate and remains pending.

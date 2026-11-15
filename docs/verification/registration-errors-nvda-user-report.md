# Local registration: NVDA empty-submission error check

Tester: Raksha269, performing a guided check on the separate local checkout of PR #39. URL supplied for this test: http://localhost:8765/accounts/register/ . Local SQLite database: `.accessibility/test.sqlite3`; in-memory email backend. The user supplied terminal output confirming that configuration, confirmed the page loaded, then supplied the following Speech Viewer text after activating the form's Create account button with required fields empty.

Environment previously supplied for this guided session: NVDA 2026.3.1 (2026.3.1.58288), Edge 157.0.4341.46 (64-bit), Windows 11 Home Single Language 26H2 (26300.9974). The exact local Git revision, execution timestamp, viewport and zoom were not separately captured. This is user-performed speech evidence, not an assistant-operated or independently reproduced NVDA test.

## Relevant supplied speech

```text
Confirm password edit protected required blank
Create account button
Loading page
Loading complete
Create Account | Gather document
main landmark
form landmark
alert
Please correct the following errors heading level 2
list
level 1 list item 1 of 3
Username: This field is required. link same page
list item 2 of 3 level 1
Password: This field is required. link same page
list item 3 of 3 level 1
Confirm password: This field is required. link same page
```

Line wrapping is normalized and duplicated trailing speech/unrelated Speech Viewer UI is omitted. The transcript supports automatic error-summary announcement after submission, including its heading and three linked required-field errors. Email has no required-field error in this result; do not infer that it was validated as required.

## Subsequent error-link and field-level speech

The user followed the guided steps to activate each summary error link and report the focused control with NVDA+Tab. Relevant supplied excerpts:

```text
Username: This field is required. same page link
Username edit required invalid entry Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only. This field is required. Choose a username blank

Password: This field is required. same page link
Password edit protected required invalid entry This field is required. blank

Confirm password: This field is required. same page link
Confirm password edit protected required invalid entry This field is required. blank
```

These user-supplied speech observations support each of the three error links reaching its corresponding editable field, announcing invalid/required states and the associated required-field error; both password fields also announce protected state. The username includes its help text. Unrelated app output and repeated attempts focusing Username were excluded. These observations are limited to empty required-field validation and are not independently reproduced NVDA results.

They do not establish invalid-email or password-mismatch behavior, typed-password masking, successful registration, other form errors, or a production deployment result. Local browser automation separately verified error-summary focus/description IDs; keep that method distinct from these NVDA results. #36, #37 and parent #9 remain open for remaining agreed checks and review.

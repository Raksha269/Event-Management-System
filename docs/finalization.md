# Finalization and freeze preparation

Status: DOCUMENTATION AND SPRINT 1 VIDEO MERGED VIA PR #52; SPRINT 2 DRIVE LINK RECORDED. NOT AN OFFICIAL FREEZE OR RELEASE.

## Verified candidate baseline

- Source main commit: `3d7cf6ec7d9fd2b7462c95ceeae3eeb684e5f013`.
- Before this documentation PR, the read-only repository review found zero open issues and zero open pull requests.
- Django CI passed: https://github.com/Raksha269/Event-Management-System/actions/runs/43981722417
- PostgreSQL NFR verification passed: https://github.com/Raksha269/Event-Management-System/actions/runs/43981722463
- Issue #9 and #38 owner acceptance and #37 verification are linked in the updated reports.

This baseline precedes these local documentation changes. The final freeze must identify the commit after the documentation review and merge.

## Required before declaring the freeze

- [ ] Review and merge the final documentation updates; verify the resulting commit’s CI.
- [x] Add the supplied [Sprint 1 video](videos/sprint-1-demo.mp4) (98.7 seconds; the owner accepts the supplied duration).
- [x] Link the owner-supplied [Sprint 2 product video on Google Drive](https://drive.google.com/file/d/18mJD9VhMXXAD3nwdCQmB9pH4GEFNrY8B/view?usp=sharing); owner accepts the supplied duration.
- [ ] Record both video locations and verify that evaluators can open them.
- [ ] Confirm the SRS, Test Plan and SAD sections, diagrams, traceability and deviations against the evaluation checklist. Their detailed PDF contents were not re-audited in this finalization pass.
- [ ] Confirm all board items have story points, individual assignees and Sprint 1/2 assignments. Private board field completeness was not verified in this pass.
- [ ] Confirm required owner reviews and individual PR contributions against the checklist.
- [ ] Record team agreement to stop development and the exact final commit.
- [ ] Optionally create a final tag/release, for example `v1.0-final`, at that commit. A tag is a useful baseline marker, not an explicit checklist requirement.

The supplied Sprint 1 recording is included unchanged. The supplied Sprint 2 file exceeded the workspace transfer limit of 32 MiB and could not be downloaded or committed. The owner subsequently supplied the Google Drive link above. Its duration and content have not been independently verified. The workspace link check returned HTTP 401, so anonymous playback remains unconfirmed; check it in a signed-out/private browser. External hosting acceptance against the checklist’s repository-upload wording remains to be confirmed.

## Freeze notice template (publish only after the checks above)

> Sprint 2 development is frozen at commit `<final SHA>` (tag `<tag, if used>`). The final documentation, test evidence and permitted scope deviations are linked in the repository. Sprint 1 video: `<link>`. Sprint 2 video: `<link>`. Further changes require an agreed correction and a new identified baseline.

Archiving the repository is not required by the checklist. PR #52 merged the documentation and Sprint 1 recording. The subsequent owner-requested direct documentation update records duration acceptance. Neither update changes repository settings, creates a release or declares a final freeze.

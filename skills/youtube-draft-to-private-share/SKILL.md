---
name: youtube-draft-to-private-share
description: Run or maintain the local Playwright automation that changes YouTube Studio draft videos to private and shares them with a fixed list of Google accounts. Use when the user asks to execute, debug, or update the YouTube draft privacy/share automation in this repository.
---

# YouTube Draft To Private Share

Use this repository's `youtube_draft_to_unlisted.py` script.

## Commands

Run all drafts:

```bash
python3 youtube_draft_to_unlisted.py
```

Run one draft only:

```bash
python3 youtube_draft_to_unlisted.py --test
```

Repair one already-private video whose share emails may not have been saved:

```bash
python3 youtube_draft_to_unlisted.py --include-private --test
```

Skip the account-confirmation Enter prompt only when the user explicitly wants unattended execution:

```bash
python3 youtube_draft_to_unlisted.py --skip-confirm
```

## Expected Workflow

1. Launch Chrome using the repository-local `chrome_profile/` session.
2. Open YouTube Studio.
3. Wait for the user to confirm the correct YouTube account in Terminal.
4. Detect `ytcp-video-row` rows whose text contains `ドラフト`; with `--include-private`, also process rows containing `非公開`.
5. Open `ドラフトを編集`.
6. Move to `公開設定`.
7. Select `非公開`.
8. Open the private-share dialog.
9. Add these Google accounts:
   - `toruy56@gmail.com`
   - `mei1218y@gmail.com`
   - `m.reveson.mi@gmail.com`
   - `rihoho1020@gmail.com`
   - `memory.yoshie55@gmail.com`
10. Save.
11. Return to the content list and confirm the row is `非公開` and no longer `ドラフト`.

## Maintenance Notes

- Prefer `--test` after selector changes.
- Do not commit `chrome_profile/`.
- YouTube Studio selectors change often. Keep selectors as ordered fallback lists rather than relying on one selector.

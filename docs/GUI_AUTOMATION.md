# GUI Automation Module (Playwright)

`gui_automation` now uses Playwright as the browser engine for Gmail GUI scenarios.

## Install

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Gmail Setup (Persistent Profile)

1. Set profile directory:
```bash
export RPA_PLAYWRIGHT_USER_DATA_DIR=./.playwright/gmail-profile
```
2. Run workflow with `open_browser` and login manually once.
3. Next runs reuse saved session/cookies.

## Environment Variables

- `RPA_GUI_WORKFLOW_DIR`
- `RPA_GUI_LOG_LEVEL`
- `RPA_GUI_BROWSER_HEADLESS`
- `RPA_GUI_TIMEOUT`
- `RPA_PLAYWRIGHT_USER_DATA_DIR`
- `RPA_PLAYWRIGHT_CHANNEL`
- `RPA_PLAYWRIGHT_BROWSER` (`chromium|firefox|webkit`)
- `RPA_GUI_DOWNLOADS_DIR`
- `RPA_GMAIL_BASE_URL`

## Supported Actions

### `open_browser`
Open Playwright persistent browser context.

Params:
- `url` (optional)
- `headless` (optional)
- `user_data_dir` (optional)
- `downloads_dir` (optional)
- `timeout` (optional)

### `click`
Click any CSS locator.

Params:
- `locator` (required)
- `timeout` (optional)

### `type`
Type text into locator or keyboard.

Params:
- `text` (required)
- `locator` (optional)
- `timeout` (optional)

### `screenshot`
Save page screenshot to `logs/<workflow_name>/`.

Params:
- `name` (optional)

### `click_email`
Find and open Gmail email using search query.

Params:
- `from_sender` (optional)
- `subject` (optional)
- `unread_only` (optional, default `true`)
- `search_query` (optional, overrides generated query)
- `timeout` (optional)
- `retries` (optional)

### `download_attachments`
Download Gmail attachments from opened email.

Params:
- `download_dir` (optional)
- `pattern` (optional, default `*`)
- `timeout` (optional)
- `max_files` (optional)

### `send_email_gmail`
Compose and send/draft Gmail email in browser.

Params:
- `to` (required, string or list)
- `subject` (optional)
- `body` (optional)
- `cc` (optional)
- `bcc` (optional)
- `attachments` (optional list)
- `send` (optional, default `true`)
- `save_draft` (optional)

### `close_application`
Close Playwright context and browser.

## Examples

- Download unread attachments: [docs/examples/gui_workflows/gmail_to_word.yaml](/mnt/c/Users/arthu/source/rpa/docs/examples/gui_workflows/gmail_to_word.yaml)
- Send Gmail message: [docs/examples/gui_workflows/gmail_send_email.yaml](/mnt/c/Users/arthu/source/rpa/docs/examples/gui_workflows/gmail_send_email.yaml)


### `route_and_send_from_tables`
Classify OCR table rows and send emails to recipients from SQLite.

Required table columns after OCR:
- `тема`
- `текст письма`

Routing/classification:
- First sentence is extracted from `текст письма`
- Classifier input: `<subject> [SEP] <first_sentence>`
- Predicted topics: `cybersecurity`, `data_ai`, `infrastructure`, `programming`
- Recipients query: `SELECT email FROM emails WHERE topic = ?`

Params:
- `source_result` (optional, default `robot_result`)
- `db_path` (optional, default `data/sqlite.db` or `RPA_EMAIL_DB_PATH`)
- `model_dir` (optional, default `data/rubert_it_classifier` or `RPA_TOPIC_MODEL_DIR`)
- `send` (optional, default `false`)
- `max_rows` (optional)
- `stop_on_error` (optional, default `false`)

Safety note:
- Start with `send: false` to create drafts and verify routing before production sending.

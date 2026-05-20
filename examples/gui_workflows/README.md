# RPA Workflow Examples

This directory contains example YAML workflows for the GUI automation module.

## Available Workflows

### 1. `gmail_to_word.yaml` - Basic Email to Report
**Complexity:** ⭐⭐ Medium

**Flow:**
```
Gmail Inbox → Find Email → Download Images → TableRobot → Word → Save
```

**Key steps:**
- Open Gmail
- Click on email from specific sender
- Download table images
- Process with TableRobot
- Insert report into Word
- Save document

**Best for:** First-time users, simple email-to-report workflows

**Requirements:**
- Gmail account
- Images in email attachments
- Word template with `<!-- REPORT_HERE -->` placeholder

---

### 2. `outlook_to_word.yaml` - Outlook Email to Report
**Complexity:** ⭐⭐ Medium

**Flow:**
```
Outlook Inbox → Find Email → Download Images → TableRobot → Word → Save
```

**Key differences from Gmail:**
- Outlook Web Access (OWA) instead of Gmail
- Find email by subject
- Same analysis and reporting flow

**Best for:** Enterprise environments using Microsoft 365

**Requirements:**
- Microsoft 365 account with OWA access
- Email with subject "Table Data"
- Images attached to email

---

### 3. `complete_workflow.yaml` - Full Example with All Features
**Complexity:** ⭐⭐⭐ Advanced

**Flow:**
```
Gmail → Find Email → Screenshots → Download → TableRobot → 
Open Word → Insert Multiple Sections → Save → Screenshots
```

**Features demonstrated:**
- Multiple screenshots at each phase
- Phase markers for organization
- Variable interpolation in text
- Multiple text insertions
- Error context preservation

**Best for:** Production workflows, debugging, comprehensive examples

---

## How to Use

### 1. Run a Workflow

```bash
# Edit the workflow path in gui_workflow_example.py
python examples/gui_workflow_example.py
```

### 2. Create Your Own Workflow

Copy one of the examples and modify:

```yaml
name: "My Custom Workflow"
description: "My workflow description"

config:
  timeout: 60
  browser_headless: false

steps:
  - id: "step_1"
    name: "Description"
    action: "action_name"
    params:
      param1: value1
      param2: value2
```

### 3. Available Actions

See `docs/GUI_AUTOMATION.md` for complete action reference:
- `open_browser` - Open URL
- `click` - Click element
- `click_email` - Click email in inbox
- `type` - Type text
- `wait` - Wait seconds
- `screenshot` - Take screenshot
- `download_attachments` - Download email attachments
- `process_with_robot` - Analyze tables
- `open_word` - Open Word document
- `insert_text` - Insert text in document
- `find_and_replace` - Find and replace text
- `save_document` - Save document
- `close_application` - Close app

---

## Configuration Tips

### Using Image Locators

For reliable automation, use image-based locators:

```yaml
- id: "click_button"
  name: "Click specific button"
  action: "click"
  params:
    locator: "image:references/my_button.png"
```

**To create reference images:**
1. Take screenshot of the element
2. Crop to the element only
3. Save as PNG in `references/` directory
4. Reference in workflow as `image:references/element.png`

### Using Text Locators

For text-based elements:

```yaml
locator: "text:Send Email"
```

### Variable Interpolation

Store analysis results and use in text:

```yaml
- id: "store_result"
  action: "process_with_robot"
  params:
    store_result: "analysis"

- id: "use_result"
  action: "insert_text"
  params:
    text: "Report: ${analysis.report}"
```

---

## Debugging

### Check Logs

All execution is logged to `logs/workflow.log`:

```
[INFO] 2026-01-15 10:30:45 - Starting workflow
[INFO] 2026-01-15 10:30:50 - Step 1 completed
[ERROR] 2026-01-15 10:31:00 - Step 2 failed: Element not found
```

### Error Artifacts

On error, find debugging files in `logs/[workflow_name]/errors/`:
- `step_X_error.png` - Screenshot at failure
- `step_X_error.log` - Detailed error info

### Screenshots

Each workflow generates screenshots in `logs/[workflow_name]/`:
```
logs/
├── workflow.log
└── Gmail Tables to Word Report/
    ├── gmail_open_screenshot.png
    ├── email_screenshot.png
    ├── report_completed.png
    └── errors/
        └── step_2_error.png  (if error occurred)
```

---

## Troubleshooting

### Element Not Found

1. Check that reference image exists and is correct
2. Verify element is visible on screen
3. Take screenshot and review UI state
4. Update reference image if needed

### Attachments Not Downloading

1. Verify email has attachments
2. Check file pattern matches (*.png, *.jpg)
3. Ensure download directory exists
4. Check Gmail/Outlook attachment permissions

### TableRobot Returns No Tables

1. Verify images are valid (PNG/JPG format)
2. Check images contain actual tables
3. Review OCR sidecar logs
4. Ensure OCR service is running

### Word Document Not Opening

1. Verify file path is correct and file exists
2. Check file format is .docx
3. Ensure Word is installed
4. Close other instances of the file

---

## Best Practices

1. **Use screenshots**: Add screenshots at key points for debugging
2. **Clear naming**: Use descriptive step names
3. **Error handling**: Plan for missing elements gracefully
4. **Timeouts**: Adjust wait times for your network
5. **Testing**: Test with small data first
6. **Version control**: Keep workflows in git
7. **Documentation**: Add comments in YAML explaining complex sections

---

## Next Steps

- Modify examples for your use case
- Create reference images for your UI
- Set up environment variables
- Test with real email accounts
- Monitor `logs/` for issues
- Extend with custom actions if needed

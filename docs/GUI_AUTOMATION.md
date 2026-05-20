# GUI Automation Module

The `gui_automation` module extends RPA Table Robot with enterprise-grade GUI automation capabilities using **Robocorp RPA Framework**. It enables non-developers to configure complex workflows via YAML files that interact with web and desktop applications.

## Features

- **Vision-based interaction**: Find and click UI elements by image or text, not fragile selectors
- **YAML-driven workflows**: Configure complex RPA processes without writing Python code
- **Sequential execution**: Steps execute one after another with clear error handling
- **Structured logging**: Comprehensive logs with screenshots on errors
- **TableRobot integration**: Seamlessly process tables and generate reports
- **Error handling**: Stop-on-error with detailed diagnostics

## Installation

No additional setup required - `robocorp-rpa-framework` is included in project dependencies.

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Create a Workflow YAML File

```yaml
# workflows/my_workflow.yaml
name: "Email Tables to Report"
description: "Collect tables from email and insert into Word"

config:
  timeout: 60
  browser_headless: false

steps:
  - id: "step_1"
    name: "Open Gmail"
    action: "open_browser"
    params:
      url: "https://mail.google.com"

  - id: "step_2"
    name: "Process tables"
    action: "process_with_robot"
    params:
      image_dir: "./temp_images"
      output_dir: "./output"
      store_result: "robot_result"

  - id: "step_3"
    name: "Close browser"
    action: "close_application"
    params:
      app: "current"
```

### 2. Run the Workflow

```bash
# Using the example script
python examples/gui_workflow_example.py

# Or programmatically
from pathlib import Path
from rpa_table_robot.gui_automation import WorkflowEngine, load_workflow_from_yaml

workflow = load_workflow_from_yaml(Path("workflows/my_workflow.yaml"))
engine = WorkflowEngine()
context = engine.execute_sync(workflow)

print(context.robot_result.report)
```

## Workflow Schema

### Top-level Structure

```yaml
name: string                    # Required: workflow name
description: string             # Optional: workflow description

config:                         # Optional: global settings
  timeout: float               # Step timeout in seconds (default: 30)
  browser_headless: bool       # Browser headless mode (default: false)

steps:                         # Required: list of steps
  - id: string
    name: string
    action: string
    params: dict
```

### Step Schema

```yaml
- id: string                   # Required: unique step identifier
  name: string                 # Required: display name
  action: string               # Required: action type
  params:                       # Required: action parameters (dict)
    key1: value1
    key2: value2
```

## Available Actions

### `open_browser`
Open a URL in a web browser.

**Parameters:**
- `url` (required): URL to open
- `headless` (optional): Browser headless mode (default: false)

**Example:**
```yaml
- id: "open_gmail"
  name: "Open Gmail"
  action: "open_browser"
  params:
    url: "https://mail.google.com"
    headless: false
```

### `click`
Click on a UI element identified by locator.

**Parameters:**
- `locator` (required): Element locator
  - Image: `image:references/button.png`
  - Text: `text:Button Text`

**Example:**
```yaml
- id: "click_send"
  name: "Click Send Button"
  action: "click"
  params:
    locator: "image:references/gmail/send_button.png"
```

### `type`
Type text into focused input field.

**Parameters:**
- `text` (required): Text to type

**Example:**
```yaml
- id: "enter_email"
  name: "Enter Email"
  action: "type"
  params:
    text: "user@example.com"
```

### `wait`
Wait for specified seconds.

**Parameters:**
- `seconds` (required): Seconds to wait

**Example:**
```yaml
- id: "wait_load"
  name: "Wait for page load"
  action: "wait"
  params:
    seconds: 3
```

### `screenshot`
Take a screenshot for debugging.

**Parameters:**
- `name` (optional): Screenshot identifier

**Example:**
```yaml
- id: "capture"
  name: "Take screenshot"
  action: "screenshot"
  params:
    name: "inbox_state"
```

### `process_with_robot`
Process images with TableRobot to recognize tables.

**Parameters:**
- `image_dir` (required): Directory containing images
- `output_dir` (required): Directory for output artifacts
- `store_result` (optional): Variable name for result (default: "robot_result")

**Example:**
```yaml
- id: "process"
  name: "Process tables"
  action: "process_with_robot"
  params:
    image_dir: "./temp_images"
    output_dir: "./output"
    store_result: "analysis"
```

### `click_email`
Click on specific email in inbox.

**Parameters:**
- `from_sender` (optional): Sender email or name
- `subject` (optional): Email subject to find
- `locator` (optional): Direct locator (image: or text:)

**Example:**
```yaml
- id: "open_email"
  name: "Open email from sender"
  action: "click_email"
  params:
    from_sender: "data.team@example.com"
```

### `download_attachments`
Download email attachments to local directory.

**Parameters:**
- `download_dir` (required): Directory to save attachments
- `pattern` (optional): File pattern to match (default: *)
- `timeout` (optional): Wait timeout in seconds (default: 30)

**Example:**
```yaml
- id: "get_attachments"
  name: "Download table images"
  action: "download_attachments"
  params:
    download_dir: "./temp_images"
    pattern: "*.png"
    timeout: 30
```

### `open_word`
Open a Word document file.

**Parameters:**
- `path` (required): Path to .docx file

**Example:**
```yaml
- id: "open_report"
  name: "Open Word report"
  action: "open_word"
  params:
    path: "C:\\reports\\template.docx"
```

### `find_and_replace`
Find text in open document and replace it.

**Parameters:**
- `search` (required): Text to search for
- `replace` (required): Replacement text (supports `${variable}` interpolation)

**Example:**
```yaml
- id: "insert_analysis"
  name: "Insert report"
  action: "find_and_replace"
  params:
    search: "<!-- REPORT_HERE -->"
    replace: "${table_analysis.report}"
```

### `insert_text`
Insert text into open document at cursor position.

**Parameters:**
- `text` (required): Text to insert (supports `${variable}` interpolation)
- `search_for` (optional): Text to find and position before insertion

**Example:**
```yaml
- id: "add_text"
  name: "Add analysis text"
  action: "insert_text"
  params:
    search_for: "Analysis:"
    text: "${analysis.report}"
```

### `save_document`
Save active document (Word, etc.).

**Parameters:**
- `wait_before_save` (optional): Seconds to wait before saving (default: 1)

**Example:**
```yaml
- id: "save"
  name: "Save document"
  action: "save_document"
  params:
    wait_before_save: 1
```

## Locators

Locators identify UI elements for interaction.

### Image Locator
Find and click element by image matching.

```yaml
locator: "image:references/button.png"
```

**To create reference images:**
1. Take screenshot of the element you want to interact with
2. Save to `references/` directory with descriptive name
3. Reference in workflow: `image:references/element_name.png`

**Tips:**
- Use high-contrast elements for better matching
- Include sufficient context but avoid changing backgrounds
- Test on target system first

### Text Locator
Find element by visible text.

```yaml
locator: "text:Click me"
```

## Variables and Context

Access results from previous steps and set variables.

### Store Results
Store step results for later use:

```yaml
- id: "process"
  action: "process_with_robot"
  params:
    store_result: "my_result"

# Later steps can access it
- id: "use_result"
  name: "Use stored result"
  action: "screenshot"  # Any action using context
```

### Access Variables
Variables accessible in context:
- `workflow_name`: Name of current workflow
- Custom variables set via `store_result`

## Environment Variables

Configure via `.env` file:

```bash
# Workflow settings
RPA_GUI_WORKFLOW_DIR=./workflows
RPA_GUI_LOG_LEVEL=INFO
RPA_GUI_BROWSER_HEADLESS=false
RPA_GUI_TIMEOUT=30

# Email credentials
GMAIL_USER=your-email@gmail.com
GMAIL_PASS=your-app-password

# File paths
REPORT_OUTPUT_PATH=C:\\reports\\report.docx
```

## Error Handling

Workflows stop immediately on error. Errors are logged with:
- Error screenshots saved to `logs/[workflow_name]/errors/`
- Detailed error logs in `logs/[workflow_name]/errors/step_X_error.log`
- Context and variable state preserved

**Example error artifacts:**
```
logs/
├── workflow.log                 # Main workflow log
└── Email Tables to Report/
    ├── errors/
    │   ├── step_2_error.png     # Error screenshot
    │   └── step_2_error.log     # Error details
    └── ...
```

## Logging

All workflow execution is logged to:
- **Console**: Real-time progress (level: configured log level)
- **File**: `logs/workflow.log` - Complete execution history

Log format: `[LEVEL] timestamp - module - function - message`

## Examples

### Gmail to Word Report

See `examples/gui_workflows/gmail_to_word.yaml`

**Workflow steps:**
1. Open Gmail inbox
2. Click on email from specific sender
3. Download table images from attachments
4. Process with TableRobot
5. Close Gmail
6. Open Word report template
7. Insert analysis report
8. Save document

### Outlook to Word Report

See `examples/gui_workflows/outlook_to_word.yaml`

**Workflow steps:**
1. Open Outlook Web Access
2. Click on email with subject "Table Data"
3. Download table images
4. Analyze with TableRobot
5. Open Word template
6. Insert report
7. Save and close

### Complete End-to-End Workflow

See `examples/gui_workflows/complete_workflow.yaml`

**Advanced example showing:**
- Three workflow phases with clear documentation
- Email finding and image downloading
- Table analysis and storage
- Variable interpolation in text
- Multiple insertions in single document
- Screenshots at each phase for debugging

Run any example:
```bash
python examples/gui_workflow_example.py
```

Edit the file path in `gui_workflow_example.py` to run different workflows.

## Troubleshooting

### Element Not Found
- Verify image locator file exists
- Check that reference image matches current UI
- Use `screenshot` action to debug UI state

### Browser Won't Open
- Ensure Chrome/Chromium browser installed
- Check RPA Framework installation
- Review `logs/workflow.log` for detailed error

### TableRobot Returns No Tables
- Verify images exist in specified directory
- Check image format (PNG, JPG supported)
- Review `logs/workflow.log` for OCR service errors

### Workflow Stops Without Error
- Check log level - may be suppressing messages
- Verify all action parameters are valid
- Ensure referenced files and directories exist

## Advanced Usage

### Custom Actions

Create custom actions by extending the `Action` class:

```python
from rpa_table_robot.gui_automation.builtin_actions import Action, ACTION_REGISTRY

class MyCustomAction(Action):
    async def execute(self, params, context):
        # Your implementation
        return result

# Register action
ACTION_REGISTRY["my_action"] = MyCustomAction
```

### Programmatic Workflow Creation

```python
from rpa_table_robot.gui_automation import (
    WorkflowEngine,
    Workflow,
    WorkflowStep,
    WorkflowConfig,
)

workflow = Workflow(
    name="My Workflow",
    config=WorkflowConfig(timeout=60),
    steps=[
        WorkflowStep(
            id="step1",
            name="Open Browser",
            action="open_browser",
            params={"url": "https://example.com"}
        ),
    ]
)

engine = WorkflowEngine()
context = engine.execute_sync(workflow)
```

## Integration with TableRobot

The `process_with_robot` action automatically:
1. Reads images from specified directory
2. Calls `TableRobot.process_images()`
3. Stores result in context for later use
4. Makes report and tables accessible

The existing `TableRobot` module is not modified - GUI automation simply orchestrates its execution.

## Performance Notes

- **Sequential execution**: Steps run one after another, not in parallel
- **Timeouts**: Each step has a global timeout (configurable)
- **Memory**: Screenshots kept in memory - clear old logs periodically
- **OCR Service**: Ensure Docker OCR sidecar is running for table recognition

## Support

For issues:
1. Check `logs/workflow.log` for execution details
2. Review error screenshots in `logs/[workflow_name]/errors/`
3. Verify all locators and file paths exist
4. Check `.env` configuration

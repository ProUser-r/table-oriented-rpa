"""Example: Running a GUI automation workflow."""

from pathlib import Path

from rpa_table_robot.gui_automation import GUIAutomationConfig, WorkflowEngine, load_workflow_from_yaml


def main():
    workflow_path = Path("docs/examples/gui_workflows/gmail_to_word_copy.yaml")
    config = GUIAutomationConfig.from_env()
    workflow = load_workflow_from_yaml(workflow_path)
    engine = WorkflowEngine(config)
    context = engine.execute_sync(workflow)
    print(f"Workflow: {workflow.name}")
    print(f"Screenshots: {len(context.screenshots)}")


if __name__ == "__main__":
    main()

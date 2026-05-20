"""Example: Running a GUI automation workflow."""

from pathlib import Path

from rpa_table_robot.gui_automation import (
    GUIAutomationConfig,
    WorkflowEngine,
    load_workflow_from_yaml,
)


def main():
    """Run example workflow."""
    workflow_path = Path("examples/gui_workflows/gmail_to_word.yaml")

    print(f"\n{'='*60}")
    print("RPA Table Robot - GUI Automation Workflow")
    print(f"{'='*60}\n")

    try:
        config = GUIAutomationConfig.from_env()
        config.validate()
        print(f"✓ Configuration loaded successfully")
        print(f"  - Workflow dir: {config.workflow_dir}")
        print(f"  - Log level: {config.log_level}")
        print(f"  - Browser headless: {config.browser_headless}\n")

        print(f"Loading workflow: {workflow_path}")
        workflow = load_workflow_from_yaml(workflow_path)

        print(f"✓ Workflow loaded: {workflow.name}")
        print(f"  - Description: {workflow.description}")
        print(f"  - Steps: {len(workflow.steps)}\n")

        engine = WorkflowEngine(config)

        print("Starting workflow execution...\n")
        context = engine.execute_sync(workflow)

        print(f"\n{'='*60}")
        print("Workflow Completed Successfully!")
        print(f"{'='*60}")

        if context.robot_result:
            print(f"\nResults:")
            print(f"  - Tables recognized: {len(context.robot_result.tables)}")
            print(f"  - Report generated: {bool(context.robot_result.report)}")
            if context.robot_result.artifacts:
                print(f"  - Artifacts saved to: {context.robot_result.artifacts.output_dir}")

        print(f"  - Screenshots captured: {len(context.screenshots)}")
        print(f"\nExecution finished. Check logs/ directory for details.")

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Workflow Failed!")
        print(f"{'='*60}")
        print(f"\nError: {str(e)}")
        print(f"\nCheck logs/ directory for error details and screenshots.")
        raise


if __name__ == "__main__":
    main()

import os
from pathlib import Path

import pytest

from ragbits.core.sources.asana import AsanaSource


@pytest.fixture(autouse=True)
def setup_local_storage_dir(tmp_path: Path):
    """Set up a temporary local storage directory for tests."""
    original_local_storage_dir = os.environ.get("LOCAL_STORAGE_DIR")
    os.environ["LOCAL_STORAGE_DIR"] = str(tmp_path)
    yield
    if original_local_storage_dir is not None:
        os.environ["LOCAL_STORAGE_DIR"] = original_local_storage_dir
    else:
        del os.environ["LOCAL_STORAGE_DIR"]


class TestAsanaSource:
    """Test cases for AsanaSource with real API calls."""

    def test_set_access_token(self):
        """Test setting access token."""
        AsanaSource.set_access_token("test_token")
        assert AsanaSource._asana_access_token == "test_token"

    def test_set_fields(self):
        """Test setting fields."""
        test_fields = ["name", "notes", "completed"]
        AsanaSource.set_fields(test_fields)
        assert AsanaSource._asana_fields == test_fields

    @pytest.mark.asyncio
    async def test_real_fetch_debug(self):
        """
        Real test that fetches actual Asana tasks and shows debug output.
        This test will be skipped if ASANA_TOKEN or ASANA_PROJECT_ID is not set.
        """
        # Get ASANA_TOKEN and ASANA_PROJECT_ID from environment variables
        asana_token = os.environ.get('ASANA_TOKEN')
        asana_project_id = os.environ.get('ASANA_PROJECT_ID')
        
        if not asana_token:
            pytest.skip(
                "ASANA_TOKEN environment variable not set. Please set it:\n"
                "export ASANA_TOKEN='your_token_here'"
            )
        
        if not asana_project_id:
            pytest.skip(
                "ASANA_PROJECT_ID environment variable not set. Please set it:\n"
                "export ASANA_PROJECT_ID='your_project_id_here'"
            )
        
        print(f"\nDebugging AsanaSource fetch with real API...")
        print(f"Found ASANA_TOKEN: {asana_token[:10]}...")
        print(f"Using project ID: {asana_project_id}")
        
        # Set up the Asana source exactly like in our implementation
        AsanaSource.set_access_token(asana_token)
        
        # Set fields to include assignee and other important fields
        assignee_fields = [
            "name", "notes", "assignee", "assignee.name", "completed", 
            "created_at", "modified_at", "due_on", "start_on", "projects", 
            "projects.name", "tags", "tags.name", "custom_fields", 
            "custom_fields.name", "custom_fields.display_value", 
            "dependencies", "dependencies.name", "num_subtasks", "permalink_url"
        ]
        AsanaSource.set_fields(assignee_fields)
        
        source = AsanaSource(project_id=asana_project_id)
        
        print(f"Requested fields: {AsanaSource._asana_fields}")
        
        try:
            print("\nTesting _get_client()...")
            client = AsanaSource._get_client()
            print(f"Client created: {type(client)}")
            
            print("\nTesting _get_tasks_api()...")
            tasks_api = AsanaSource._get_tasks_api()
            print(f"Tasks API created: {type(tasks_api)}")
            
            print("\nTesting get_tasks() with exact same parameters...")
            # Use the exact same parameters as in the fetch method
            tasks = list(tasks_api.get_tasks(
                opts={
                    "project": source.project_id,
                    "opt_fields": ",".join(AsanaSource._asana_fields)
                }
            ))
            
            print(f"Found {len(tasks)} tasks using AsanaSource methods!")
            
            # Show first few tasks
            for i, task in enumerate(tasks[:3]):
                task_name = task.get('name', 'Unnamed Task')
                print(f"  {i+1}. {task_name}")
            
            # Debug the first task structure
            if tasks:
                print(f"\nDebugging first task structure:")
                task = tasks[0]
                print(f"Type: {type(task)}")
                print(f"Task data: {task}")
                print(f"Keys: {list(task.keys()) if isinstance(task, dict) else 'Not a dict'}")
                print(f"Name value: {task.get('name', 'NOT_FOUND')}")
                print(f"GID value: {task.get('gid', 'NOT_FOUND')}")
                print(f"Completed value: {task.get('completed', 'NOT_FOUND')}")
                print(f"Notes value: {task.get('notes', 'NOT_FOUND')}")
                print(f"Created at value: {task.get('created_at', 'NOT_FOUND')}")
                print(f"Modified at value: {task.get('modified_at', 'NOT_FOUND')}")
                print(f"Assignee value: {task.get('assignee', 'NOT_FOUND')}")
                if task.get('assignee'):
                    print(f"Assignee name: {task.get('assignee', {}).get('name', 'NOT_FOUND')}")
                print(f"Projects value: {task.get('projects', 'NOT_FOUND')}")
                print(f"Tags value: {task.get('tags', 'NOT_FOUND')}")
            
            print("\nTesting actual fetch() method...")
            result = await source.fetch()
            
            print(f"Fetch completed successfully!")
            print(f"Result path: {result}")
            print(f"Path exists: {result.exists()}")
            print(f"Path name: {result.name}")
            
            # Check that task files were created in the asana_tasks subdirectory
            asana_tasks_dir = result / "asana_tasks"
            task_files = list(asana_tasks_dir.glob("*.txt")) if asana_tasks_dir.exists() else []
            print(f"Task files created: {len(task_files)}")
            
            # Show content of first task file
            if task_files:
                print(f"\nContent of task file ({task_files[0].name}):")
                content = task_files[0].read_text()
                print("=" * 50)
                print(content)
                print("=" * 50)
                
                # Verify the content has expected structure
                assert "ASANA TASK INFORMATION" in content
                assert "Task ID:" in content
                assert "Name:" in content
                print("Task file content structure looks correct!")
            else:
                print(f"No task files found in {asana_tasks_dir}")
                if asana_tasks_dir.exists():
                    print(f"Directory contents: {list(asana_tasks_dir.iterdir())}")
                else:
                    print(f"asana_tasks directory does not exist in {result}")
                    print(f"Result directory contents: {list(result.iterdir())}")
            
            # Basic assertions
            assert isinstance(result, Path)
            assert result.exists()
            # The result should contain an asana_tasks subdirectory
            asana_tasks_dir = result / "asana_tasks"
            assert asana_tasks_dir.exists(), f"asana_tasks directory not found in {result}"
            assert len(task_files) > 0, f"No task files found in {result}"
            
        except Exception as e:
            print(f"Error during fetch: {e}")
            import traceback
            traceback.print_exc()
            raise


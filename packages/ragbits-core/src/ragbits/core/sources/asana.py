from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
from typing import Any, ClassVar, List, Union, Optional
from typing_extensions import Self
from collections.abc import Iterable
from io import TextIOWrapper 

from ragbits.core.audit.traces import trace, traceable
from ragbits.core.sources.base import Source, get_local_storage_dir
from ragbits.core.sources.exceptions import SourceConnectionError, SourceError
from ragbits.core.utils.decorators import requires_dependencies

with suppress(ImportError):
    from asana import ApiClient, Configuration, TasksApi, ProjectsApi, WorkspacesApi
    from asana.rest import ApiException

_OPT_FIELDS = [
    "actual_time_minutes",
    "approval_status",
    "assignee",
    "assignee.name",
    "assignee_section",
    "assignee_section.name",
    "assignee_status",
    "completed",
    "completed_at",
    "completed_by",
    "completed_by.name",
    "created_at",
    "created_by",
    "custom_fields",
    "custom_fields.asana_created_field",
    "custom_fields.created_by",
    "custom_fields.created_by.name",
    "custom_fields.currency_code",
    "custom_fields.custom_label",
    "custom_fields.custom_label_position",
    "custom_fields.date_value",
    "custom_fields.date_value.date",
    "custom_fields.date_value.date_time",
    "custom_fields.description",
    "custom_fields.display_value",
    "custom_fields.enabled",
    "custom_fields.enum_options",
    "custom_fields.enum_options.color",
    "custom_fields.enum_options.enabled",
    "custom_fields.enum_options.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.color",
    "custom_fields.enum_value.enabled",
    "custom_fields.enum_value.name",
    "custom_fields.format",
    "custom_fields.has_notifications_enabled",
    "custom_fields.is_formula_field",
    "custom_fields.is_global_to_workspace",
    "custom_fields.is_value_read_only",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.color",
    "custom_fields.multi_enum_values.enabled",
    "custom_fields.multi_enum_values.name",
    "custom_fields.name",
    "custom_fields.number_value",
    "custom_fields.people_value",
    "custom_fields.people_value.name",
    "custom_fields.precision",
    "custom_fields.resource_subtype",
    "custom_fields.text_value",
    "custom_fields.type",
    "dependencies",
    "dependents",
    "due_at",
    "due_on",
    "external",
    "external.data",
    "followers",
    "followers.name",
    "hearted",
    "hearts",
    "hearts.user",
    "hearts.user.name",
    "html_notes",
    "is_rendered_as_separator",
    "liked",
    "likes",
    "likes.user",
    "likes.user.name",
    "memberships",
    "memberships.project",
    "memberships.project.name",
    "memberships.section",
    "memberships.section.name",
    "modified_at",
    "name",
    "notes",
    "num_hearts",
    "num_likes",
    "num_subtasks",
    "offset",
    "parent",
    "parent.created_by",
    "parent.name",
    "parent.resource_subtype",
    "path",
    "permalink_url",
    "projects",
    "projects.name",
    "resource_subtype",
    "start_at",
    "start_on",
    "tags",
    "tags.name",
    "uri",
    "workspace",
    "workspace.name",
]

_SIMPLE_OPT_FIELDS = [
    "name", 
    "notes",
    "assignee",
    "assignee.name",
    "completed",
    "created_at",
    "modified_at",
    "due_on",
    "start_on",
    "start_at",
    "tags",
    "tags.name",
    "projects",
    "projects.name",
    "custom_fields",
    "custom_fields.name",
    "custom_fields.display_value",
    "custom_fields.text_value",
    "dependencies",
    "dependencies.name",
    "num_subtasks",
    "permalink_url",
    "uri",
    "workspace",
    "workspace.name"
]

_COMPLEX_OPT_FIELDS = [field for field in _OPT_FIELDS if field not in _SIMPLE_OPT_FIELDS]

class AsanaSource(Source):
    """
    Source for data stored in the Asana.
    """

    _asana_client: ClassVar["ApiClient" | None] = None
    _asana_access_token: ClassVar[str | None] = None
    _asana_tasks_api: ClassVar["TasksApi" | None] = None
    _asana_configuration: ClassVar["Configuration" | None] = None
    _asana_configuration_settings: ClassVar[dict[str, Any] | None] = None
    _asana_fields: ClassVar[List[str] | None] = _SIMPLE_OPT_FIELDS

    project_id: str

    protocol: ClassVar[str] = "asana"

    @property
    def id(self) -> str:
        """Get the source identifier."""
        return f"asana://{self.project_id}"

    @classmethod
    @requires_dependencies(["asana"], "asana")
    async def list_sources(cls, workspace_id: str | None = None, *args: Any, **kwargs: Any) -> Iterable[Self]:
        """
        List all Asana projects as sources.
        
        Args:
            workspace_id: Optional workspace ID. If not provided, will use the first available workspace.
            
        Returns:
            Iterable of AsanaSource instances for each project.
        """
        # Get workspace if not provided
        if not workspace_id:
            workspaces_api = WorkspacesApi(cls._get_client())
            workspaces = list(workspaces_api.get_workspaces({}))
            if not workspaces:
                return []
            workspace_id = workspaces[0]['gid']
        
        # Get all projects from the workspace
        projects_api = ProjectsApi(cls._get_client())
        projects = list(projects_api.get_projects({"workspace": workspace_id}))
        
        # Convert projects to AsanaSource instances
        sources = []
        for project in projects:
            sources.append(cls(project_id=project['gid']))
        
        return sources

    @classmethod
    async def from_uri(cls, path: str) -> Iterable[Self]:
        """
        Create Source instances from a URI path.
        
        Expected format: asana://project_id
        """
        if not path.startswith("asana://"):
            raise ValueError(f"Invalid Asana URI: {path}. Expected format: asana://project_id")
        
        project_id = path[8:]  # Remove "asana://" prefix
        if not project_id:
            raise ValueError("Project ID is required in Asana URI")
        
        return [cls(project_id=project_id)]

    @classmethod
    def set_access_token(cls, access_token: str) -> None:
        """
        Set the access token for the Asana client.
        """
        cls._asana_access_token = access_token

    @classmethod
    def set_fields(cls, fields: List[str]) -> None: 
        """sets the return fields from asana that provide task info"""
        cls._asana_fields = fields

    @classmethod
    @requires_dependencies(["asana"], "asana")
    def _get_client(cls) -> "ApiClient":
        """
        Get the Asana client.
        """
        if cls._asana_client is None:
            configuration = Configuration()
            configuration.access_token = cls._asana_access_token
            cls._asana_client = ApiClient(configuration)
        return cls._asana_client

    @classmethod
    @requires_dependencies(["asana"], "asana")
    def _get_tasks_api(cls) -> "TasksApi":
        """
        Get the Asana tasks API.
        """
        if cls._asana_tasks_api is None:
            cls._asana_tasks_api = TasksApi(cls._asana_client)
        return cls._asana_tasks_api

    def _set_configuration_settings(cls, settings: dict[str, Any]) -> None:
        """
        Set the Asana configuration settings.
        """
        cls._asana_configuration_settings = settings

    @classmethod
    @requires_dependencies(["asana"], "asana")
    def _get_configuration(cls) -> "Configuration":
        """
        Get the Asana configuration.
        """
        if cls._asana_configuration is None:
            try:
                cls._asana_configuration = Configuration() # need this to be empty first 
                for entry, value in cls._asana_configuration_settings.items():
                    setattr(cls._asana_configuration, entry, value)
            except Exception as e:
                raise Exception(f"Error setting Asana configuration settings: {e}")
        return cls._asana_configuration

    @traceable
    @requires_dependencies(["asana"], "asana")
    async def fetch(self) -> Path:
        """
        Fetch the Asana source and dump tasks to text files.
        
        Returns:
            The local path to the directory containing the dumped task files.
            
        Raises:
            SourceConnectionError: If there is an error connecting to Asana API.
            SourceError: If an error occurs during task fetching or file writing.
        """
        local_dir = get_local_storage_dir()
        file_local_dir = local_dir
        file_local_dir.mkdir(parents=True, exist_ok=True)

        with trace(project_id=self.project_id) as outputs:
            try:
                # Filter tasks by project ID
                tasks = list(self._get_tasks_api().get_tasks(
                    opts={
                        "project": self.project_id,
                        "opt_fields": ",".join(self._asana_fields)
                    }
                ))
                
                # Dump tasks to text files
                self._dump_tasks_to_files(tasks, file_local_dir)
                
                outputs.path = file_local_dir
                return file_local_dir
                
            except ApiException as e:
                with trace("asana_api_error") as error_outputs:
                    error_outputs.error = f"Asana API error: {e}"
                raise SourceConnectionError() from e
            except Exception as e:
                with trace("asana_fetch_error") as error_outputs:
                    error_outputs.error = f"Error fetching Asana tasks: {e}"
                raise SourceError(f"Error fetching Asana tasks: {e}") from e

    @staticmethod
    def _write_task_information(f: TextIOWrapper, task: Any) -> None: 
        """
        Write task information to a file.

        Handles basic info and just writes to a file. 
        """
        f.write(f"ASANA TASK INFORMATION\n")
        # Basic task information
        f.write(f"Task ID: {task.get('gid', 'N/A')}\n")
        f.write(f"Name: {task.get('name', 'N/A')}\n")
        f.write(f"Notes: {task.get('notes', 'N/A')}\n")
        f.write(f"Status: {'Completed' if task.get('completed', False) else 'Incomplete'}\n")
        f.write(f"Created: {task.get('created_at', 'N/A')}\n")
        f.write(f"Modified: {task.get('modified_at', 'N/A')}\n")
        f.write(f"Due Date: {task.get('due_on', 'N/A')}\n")
        f.write(f"Start Date: {task.get('start_on', 'N/A')}\n")

        # Assignee information
        assignee = task.get('assignee')
        if assignee:
            f.write(f"Assignee: {assignee.get('name', 'N/A')}\n")
        else:
            f.write("Assignee: Unassigned\n")
        
        # Project information
        projects = task.get('projects', [])
        if projects:
            f.write(f"Projects: {', '.join([p.get('name', 'N/A') for p in projects])}\n")
        else:
            f.write("Projects: None\n")
        
        # Tags
        tags = task.get('tags', [])
        if tags:
            f.write(f"Tags: {', '.join([tag.get('name', 'N/A') for tag in tags])}\n")
        else:
            f.write("Tags: None\n")
        
        # Custom fields
        custom_fields = task.get('custom_fields', [])
        if custom_fields:
            f.write(f"\nCUSTOM FIELDS:\n")
            for field in custom_fields:
                field_name = field.get('name', 'Unknown Field')
                field_value = field.get('display_value', field.get('text_value', 'N/A'))
                f.write(f"{field_name}: {field_value}\n")

        # Dependencies
        dependencies = task.get('dependencies', [])
        if dependencies:
            f.write(f"\nDEPENDENCIES:\n")
            for dep in dependencies:
                dep_name = dep.get('name', 'Unknown Task')
                f.write(f"- {dep_name}\n")
        
        # Subtasks count
        num_subtasks = task.get('num_subtasks', 0)
        f.write(f"\nSubtasks: {num_subtasks}\n")
        
        # Permalink
        permalink = task.get('permalink_url')
        if permalink:
            f.write(f"Permalink: {permalink}\n")


    def _dump_tasks_to_files(self, tasks: Iterable[Any], output_dir: Path) -> None:
        """
        Dump tasks and their information to local text files.
        
        Args:
            tasks: Iterable of Asana task objects
            output_dir: Directory to save the text files
        """
        tasks_dir = output_dir / "asana_tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        
        with trace(project_id=self.project_id) as outputs:
            for i, task in enumerate(tasks):
                # Create a safe filename from task name or use index
                task_name = task.get('name', f'task_{i}')
                safe_filename = "".join(c for c in task_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_filename = safe_filename.replace(' ', '_')[:50]  # Limit length
                
                if not safe_filename:
                    safe_filename = f"task_{i}"
                
                task_file = tasks_dir / f"{safe_filename}_{i}.txt"
                
                # Write task information to file
                with open(task_file, 'w', encoding='utf-8') as f:
                    self._write_task_information(f, task)
            
            outputs.path = tasks_dir
            outputs.message = f"Wrote {len(list(tasks))} tasks to {tasks_dir}"
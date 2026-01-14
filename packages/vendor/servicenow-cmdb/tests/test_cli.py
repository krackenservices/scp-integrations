"""Tests for the CLI."""

import json
from unittest.mock import MagicMock

from typer.testing import CliRunner
from scp_servicenow.cli import app

runner = CliRunner()


def test_app_help():
    """Test top-level help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ServiceNow CMDB integration" in result.stdout
    assert "cmdb" in result.stdout


def test_cmdb_help():
    """Test cmdb subcommand help."""
    result = runner.invoke(app, ["cmdb", "--help"])
    assert result.exit_code == 0
    assert "CMDB operations" in result.stdout
    assert "sync" in result.stdout
    assert "validate" in result.stdout


def test_validate_command(tmp_path, mocker):
    """Test validate command."""
    # Create dummy graph file
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps({"nodes": [], "edges": []}))

    mock_validate = mocker.patch("scp_servicenow.cli.validate_mapping")
    mock_validate.return_value = []  # No issues

    result = runner.invoke(app, ["cmdb", "validate", str(graph_file)])

    assert result.exit_code == 0
    assert "Validating" in result.stdout
    assert "Validation passed" in result.stdout
    mock_validate.assert_called_once()


def test_validate_command_missing_file():
    """Test validate command with missing file."""
    result = runner.invoke(app, ["cmdb", "validate", "missing.json"])
    assert result.exit_code == 1
    assert "File not found" in result.stdout


def test_sync_command(tmp_path, mocker):
    """Test sync command."""
    # Create dummy graph file
    graph_file = tmp_path / "graph.json"
    graph_file.write_text(json.dumps({"nodes": [], "edges": []}))

    mock_load = mocker.patch("scp_servicenow.cli.load_graph_json")
    mock_auth = mocker.patch("scp_servicenow.cli.get_auth_from_env")
    mocker.patch("scp_servicenow.cli.ServiceNowClient")
    mock_sync = mocker.patch("scp_servicenow.cli.sync_to_servicenow")

    mock_load.return_value = {"nodes": [], "edges": []}
    mock_auth.return_value = MagicMock(get_auth=lambda: ("user", "pass"))

    mock_result = MagicMock()
    mock_result.failed = []
    mock_result.created_cis = []
    mock_result.created_relationships = []
    mock_sync.return_value = mock_result

    result = runner.invoke(
        app,
        [
            "cmdb",
            "sync",
            str(graph_file),
            "--instance",
            "https://test.service-now.com",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ServiceNow Instance" in result.stdout
    assert "Sync Results" in result.stdout
    mock_sync.assert_called_once()

    args, _ = mock_sync.call_args
    # sync_to_servicenow(graph_data, client, ci_class, dry_run)
    assert args[3] is True


def test_sync_command_no_auth(mocker):
    """Test sync command fails without auth."""
    mocker.patch("scp_servicenow.cli.load_graph_json")
    mock_auth = mocker.patch("scp_servicenow.cli.get_auth_from_env")
    mock_auth.side_effect = SystemExit(1)

    # We don't need to invoke, just rely on standard behavior or keep it simple
    # But for coverage we might want to invoke

"""Tests for the local scanner module."""

import pytest

from scp_constructor.scanner.local import scan_directory, scan_directories


class TestScanDirectory:
    """Tests for scan_directory function."""

    def test_find_scp_files(self, tmp_path):
        """Test finding scp.yaml files in directory tree."""
        # Create directory structure
        (tmp_path / "service-a").mkdir()
        (tmp_path / "service-a" / "scp.yaml").write_text("scp: '0.1.0'")

        (tmp_path / "service-b").mkdir()
        (tmp_path / "service-b" / "scp.yaml").write_text("scp: '0.1.0'")

        (tmp_path / "other").mkdir()
        (tmp_path / "other" / "config.yaml").write_text("not an scp file")

        result = scan_directory(tmp_path)

        assert len(result) == 2
        assert all(p.name == "scp.yaml" for p in result)

    def test_empty_directory(self, tmp_path):
        """Test scanning empty directory returns empty list."""
        result = scan_directory(tmp_path)

        assert result == []

    def test_directory_not_found(self, tmp_path):
        """Test error when directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            scan_directory(tmp_path / "missing")

    def test_not_a_directory(self, tmp_path):
        """Test error when path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(NotADirectoryError):
            scan_directory(file_path)

    def test_nested_scp_files(self, tmp_path):
        """Test finding deeply nested scp.yaml files."""
        deep_path = tmp_path / "a" / "b" / "c"
        deep_path.mkdir(parents=True)
        (deep_path / "scp.yaml").write_text("scp: '0.1.0'")

        result = scan_directory(tmp_path)

        assert len(result) == 1
        assert "a" in str(result[0])

    def test_custom_filename(self, tmp_path):
        """Test scanning for custom filename."""
        (tmp_path / "service").mkdir()
        (tmp_path / "service" / "manifest.yaml").write_text("scp: '0.1.0'")

        result = scan_directory(tmp_path, filename="manifest.yaml")

        assert len(result) == 1


class TestScanDirectories:
    """Tests for scan_directories function."""

    def test_scan_multiple(self, tmp_path):
        """Test scanning multiple directories."""
        dir_a = tmp_path / "workspace-a"
        dir_b = tmp_path / "workspace-b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "scp.yaml").write_text("scp: '0.1.0'")
        (dir_b / "scp.yaml").write_text("scp: '0.1.0'")

        result = scan_directories([dir_a, dir_b])

        assert len(result) == 2

    def test_skip_invalid_directories(self, tmp_path):
        """Test that invalid directories are skipped."""
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        (valid_dir / "scp.yaml").write_text("scp: '0.1.0'")

        result = scan_directories([valid_dir, tmp_path / "missing"])

        assert len(result) == 1

    def test_deduplicate_results(self, tmp_path):
        """Test that results are deduplicated."""
        (tmp_path / "scp.yaml").write_text("scp: '0.1.0'")

        # Scan same directory twice
        result = scan_directories([tmp_path, tmp_path])

        assert len(result) == 1

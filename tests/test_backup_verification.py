"""
Tests for Backup Restore Verification (M2)
"""
import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestBackupRestoreVerifier:
    """Test suite for backup restore verification"""
    
    @pytest.fixture
    def temp_backup_file(self):
        """Create temporary backup file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write("-- Test backup file\n")
            f.write("CREATE TABLE test (id INTEGER);\n")
            path = Path(f.name)
        
        yield path
        
        # Cleanup
        if path.exists():
            path.unlink()
    
    @pytest.fixture
    def temp_empty_backup(self):
        """Create empty backup file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            path = Path(f.name)
        
        yield path
        
        if path.exists():
            path.unlink()
    
    def test_verify_backup_file_exists(self, temp_backup_file):
        """Test backup file validation"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier(str(temp_backup_file))
        
        # Should pass validation
        assert verifier.verify_backup_file_exists() is True
        assert len(verifier.errors) == 0
    
    def test_verify_backup_file_not_found(self):
        """Test validation fails for non-existent file"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier("nonexistent.sql")
        
        # Should fail validation
        assert verifier.verify_backup_file_exists() is False
        assert len(verifier.errors) > 0
        assert "not found" in verifier.errors[0].lower()
    
    def test_verify_empty_backup_file(self, temp_empty_backup):
        """Test validation fails for empty file"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier(str(temp_empty_backup))
        
        # Should fail validation
        assert verifier.verify_backup_file_exists() is False
        assert any("empty" in error.lower() for error in verifier.errors)
    
    @patch('subprocess.run')
    def test_cleanup_existing_container(self, mock_run):
        """Test cleanup of existing container"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock container exists
        mock_run.return_value = Mock(stdout="container_id\n", returncode=0)
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.cleanup_existing_container()
        
        assert result is True
        # Should call docker rm
        calls = [str(call) for call in mock_run.call_args_list]
        assert any('rm' in str(call) for call in calls)
    
    @patch('subprocess.run')
    def test_start_postgres_container(self, mock_run):
        """Test starting PostgreSQL container"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock successful container start and pg_isready
        mock_run.side_effect = [
            Mock(returncode=0),  # docker run
            Mock(returncode=0),  # pg_isready
        ]
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.start_postgres_container()
        
        assert result is True
    
    @patch('subprocess.run')
    def test_start_postgres_timeout(self, mock_run):
        """Test PostgreSQL readiness timeout"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock container start but never becomes ready
        mock_run.side_effect = [
            Mock(returncode=0),  # docker run
        ] + [Mock(returncode=1)] * 30  # pg_isready fails
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.start_postgres_container()
        
        assert result is False
        assert any("failed to become ready" in error.lower() for error in verifier.errors)
    
    @patch('subprocess.run')
    def test_restore_backup(self, mock_run, temp_backup_file):
        """Test backup restore process"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock successful restore steps
        mock_run.side_effect = [
            Mock(returncode=0),  # docker cp
            Mock(returncode=0),  # create database
            Mock(returncode=0, stderr=""),  # psql restore
        ]
        
        verifier = BackupRestoreVerifier(str(temp_backup_file))
        result = verifier.restore_backup()
        
        assert result is True
    
    @patch('subprocess.run')
    def test_restore_backup_with_warnings(self, mock_run, temp_backup_file):
        """Test restore with non-fatal warnings"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock restore with warnings
        mock_run.side_effect = [
            Mock(returncode=0),  # docker cp
            Mock(returncode=0),  # create database
            Mock(returncode=1, stderr="WARNING: role already exists\n"),  # psql with warnings
        ]
        
        verifier = BackupRestoreVerifier(str(temp_backup_file))
        result = verifier.restore_backup()
        
        # Should still pass (warnings are OK)
        assert result is True
    
    @patch('subprocess.run')
    def test_restore_backup_fatal_error(self, mock_run, temp_backup_file):
        """Test restore with fatal error"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock fatal error
        mock_run.side_effect = [
            Mock(returncode=0),  # docker cp
            Mock(returncode=0),  # create database
            Mock(returncode=1, stderr="FATAL: could not connect to database\n"),
        ]
        
        verifier = BackupRestoreVerifier(str(temp_backup_file))
        result = verifier.restore_backup()
        
        assert result is False
        assert len(verifier.errors) > 0
    
    @patch('subprocess.run')
    def test_run_verification_query_success(self, mock_run):
        """Test running verification query successfully"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock successful query
        mock_run.return_value = Mock(
            returncode=0,
            stdout="  42  \n"
        )
        
        verifier = BackupRestoreVerifier("test.sql")
        success, result = verifier.run_verification_query("test", "SELECT COUNT(*) FROM test;")
        
        assert success is True
        assert result.strip() == "42"
    
    @patch('subprocess.run')
    def test_run_verification_query_failure(self, mock_run):
        """Test verification query failure"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock query failure
        mock_run.side_effect = subprocess.CalledProcessError(1, 'psql')
        
        verifier = BackupRestoreVerifier("test.sql")
        success, result = verifier.run_verification_query("test", "SELECT * FROM nonexistent;")
        
        assert success is False
    
    @patch('subprocess.run')
    def test_verify_schema(self, mock_run):
        """Test schema verification"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock all schema checks pass
        mock_run.return_value = Mock(returncode=0, stdout="  t  \n")
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.verify_schema()
        
        assert result is True
        assert len(verifier.results) > 0
        assert all(verifier.results.values())
    
    @patch('subprocess.run')
    def test_verify_schema_missing_table(self, mock_run):
        """Test schema verification with missing table"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock some checks pass, one fails
        responses = [Mock(returncode=0, stdout="  t  \n")] * 5 + \
                   [Mock(returncode=0, stdout="  f  \n")]  # One table missing
        
        mock_run.side_effect = responses
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.verify_schema()
        
        assert result is False
        assert len(verifier.errors) > 0
    
    @patch('subprocess.run')
    def test_verify_data_integrity(self, mock_run):
        """Test data integrity verification"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock count queries
        mock_run.return_value = Mock(returncode=0, stdout="  42  \n")
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.verify_data_integrity()
        
        assert result is True
        assert len(verifier.results) > 0
    
    @patch('subprocess.run')
    def test_verify_data_integrity_invalid_count(self, mock_run):
        """Test data integrity with invalid count"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock invalid result
        mock_run.return_value = Mock(returncode=0, stdout="  invalid  \n")
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.verify_data_integrity()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_verify_migrations(self, mock_run):
        """Test migration verification"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Mock migration version query
        mock_run.return_value = Mock(returncode=0, stdout="  0607bc5b8541  \n")
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.verify_migrations()
        
        assert result is True
        assert verifier.results.get("Migration version exists") is True
    
    @patch('subprocess.run')
    def test_cleanup_container(self, mock_run):
        """Test container cleanup"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        mock_run.return_value = Mock(returncode=0)
        
        verifier = BackupRestoreVerifier("test.sql")
        result = verifier.cleanup_container()
        
        assert result is True
    
    @patch('subprocess.run')
    def test_cleanup_container_skipped(self, mock_run):
        """Test cleanup is skipped when disabled"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier("test.sql", cleanup=False)
        result = verifier.cleanup_container()
        
        # Should skip cleanup
        assert result is True
        mock_run.assert_not_called()
    
    def test_get_exit_code_all_passed(self):
        """Test exit code when all checks pass"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier("test.sql")
        verifier.results = {"check1": True, "check2": True}
        
        assert verifier.get_exit_code() == 0
    
    def test_get_exit_code_some_failed(self):
        """Test exit code when some checks fail"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier("test.sql")
        verifier.results = {"check1": True, "check2": False}
        
        assert verifier.get_exit_code() == 1
    
    def test_get_exit_code_no_tests(self):
        """Test exit code when no tests were run"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        verifier = BackupRestoreVerifier("test.sql")
        verifier.results = {}
        
        assert verifier.get_exit_code() == 2


class TestBackupUtilities:
    """Test utility functions"""
    
    def test_find_latest_backup(self, tmp_path):
        """Test finding latest backup file"""
        from infra.scripts.verify_backup_restore import find_latest_backup
        import time
        
        # Create backup directory
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        # Create multiple backup files
        backup1 = backup_dir / "backup1.sql"
        backup1.write_text("backup1")
        time.sleep(0.1)
        
        backup2 = backup_dir / "backup2.sql"
        backup2.write_text("backup2")
        time.sleep(0.1)
        
        backup3 = backup_dir / "backup3.sql"
        backup3.write_text("backup3")
        
        # Find latest
        latest = find_latest_backup(str(backup_dir))
        
        assert latest is not None
        assert latest.name == "backup3.sql"
    
    def test_find_latest_backup_empty_dir(self, tmp_path):
        """Test find latest with no backups"""
        from infra.scripts.verify_backup_restore import find_latest_backup
        
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        latest = find_latest_backup(str(backup_dir))
        
        assert latest is None
    
    def test_find_latest_backup_nonexistent_dir(self):
        """Test find latest with nonexistent directory"""
        from infra.scripts.verify_backup_restore import find_latest_backup
        
        latest = find_latest_backup("/nonexistent/dir")
        
        assert latest is None


class TestIntegration:
    """Integration tests (require Docker)"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        subprocess.run(["which", "docker"], capture_output=True).returncode != 0,
        reason="Docker not available"
    )
    def test_full_verification_workflow(self, tmp_path):
        """Test complete verification workflow"""
        from infra.scripts.verify_backup_restore import BackupRestoreVerifier
        
        # Create minimal backup file
        backup_file = tmp_path / "test_backup.sql"
        backup_file.write_text("""
            -- Test backup
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255)
            );
            
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255)
            );
            
            CREATE TABLE IF NOT EXISTS content_jobs (
                id SERIAL PRIMARY KEY,
                topic VARCHAR(500)
            );
            
            CREATE TABLE IF NOT EXISTS content_artifacts (
                id SERIAL PRIMARY KEY,
                artifact_type VARCHAR(50)
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                plan VARCHAR(50)
            );
            
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) PRIMARY KEY
            );
            
            INSERT INTO alembic_version (version_num) VALUES ('0607bc5b8541');
        """)
        
        # Run verification
        verifier = BackupRestoreVerifier(
            str(backup_file),
            cleanup=True
        )
        
        # This will actually run the verification
        result = verifier.run_verification()
        
        # Should pass all checks
        assert result is True
        assert verifier.get_exit_code() == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


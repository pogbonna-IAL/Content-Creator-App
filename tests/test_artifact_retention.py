"""
Tests for artifact retention service (M1)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

class TestArtifactRetentionService:
    """Test ArtifactRetentionService"""
    
    def test_compute_retention_days(self):
        """Test retention days calculation for each plan"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        # Test each plan
        assert service.compute_retention_days('free') == 30
        assert service.compute_retention_days('basic') == 90
        assert service.compute_retention_days('pro') == 365
        assert service.compute_retention_days('enterprise') == -1  # Unlimited
        
        # Test case insensitive
        assert service.compute_retention_days('FREE') == 30
        assert service.compute_retention_days('Pro') == 365
        
        # Test default (unknown plan)
        assert service.compute_retention_days('unknown') == 30  # Defaults to free
    
    def test_compute_cutoff_date(self):
        """Test cutoff date computation"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        # Test free plan (30 days)
        cutoff = service.compute_cutoff_date('free')
        assert cutoff is not None
        expected = datetime.utcnow() - timedelta(days=30)
        assert abs((cutoff - expected).total_seconds()) < 60  # Within 1 minute
        
        # Test enterprise (unlimited)
        cutoff = service.compute_cutoff_date('enterprise')
        assert cutoff is None  # No cutoff for unlimited retention
    
    def test_dry_run_mode(self):
        """Test that dry-run mode prevents actual deletions"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=True)
        
        assert service.dry_run is True
        
        # Verify dry_run flag is respected
        mock_artifact = Mock()
        mock_artifact.id = 123
        mock_artifact.storage_key = "test_key"
        
        with patch('content_creation_crew.services.artifact_retention_service.get_storage_provider') as mock_storage:
            mock_provider = Mock()
            mock_provider.get.return_value = b"test_data"
            mock_provider.delete.return_value = True
            mock_storage.return_value = mock_provider
            
            # Delete in dry-run mode
            success, bytes_deleted = service.delete_artifact_files(mock_artifact)
            
            # Should report success but not actually call delete
            assert success is True
            mock_provider.delete.assert_not_called()
    
    def test_delete_artifact_files_success(self):
        """Test successful artifact file deletion"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        mock_artifact = Mock()
        mock_artifact.id = 123
        mock_artifact.storage_key = "voiceovers/test.wav"
        
        with patch('content_creation_crew.services.artifact_retention_service.get_storage_provider') as mock_storage:
            mock_provider = Mock()
            mock_provider.get.return_value = b"test_audio_data"  # 15 bytes
            mock_provider.delete.return_value = True
            mock_storage.return_value = mock_provider
            
            success, bytes_deleted = service.delete_artifact_files(mock_artifact)
            
            assert success is True
            assert bytes_deleted == 15
            mock_provider.delete.assert_called_once_with("voiceovers/test.wav")
    
    def test_delete_artifact_files_no_storage_key(self):
        """Test artifact deletion with no storage key"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        mock_artifact = Mock()
        mock_artifact.id = 123
        mock_artifact.storage_key = None
        
        success, bytes_deleted = service.delete_artifact_files(mock_artifact)
        
        assert success is True
        assert bytes_deleted == 0
    
    def test_delete_artifact_records(self):
        """Test artifact record deletion"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        # Create mock artifacts
        mock_artifacts = [Mock(id=i) for i in range(3)]
        
        # Delete records
        deleted, failed = service.delete_artifact_records(mock_artifacts)
        
        assert deleted == 3
        assert failed == 0
        assert mock_db.delete.call_count == 3
        assert mock_db.flush.call_count == 3
    
    def test_delete_artifact_records_with_failure(self):
        """Test artifact record deletion with partial failure"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        mock_db.delete.side_effect = [None, Exception("DB error"), None]
        
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        mock_artifacts = [Mock(id=i) for i in range(3)]
        
        deleted, failed = service.delete_artifact_records(mock_artifacts)
        
        assert deleted == 2  # First and third succeeded
        assert failed == 1  # Second failed
    
    def test_cleanup_expired_artifacts_unlimited_retention(self):
        """Test that enterprise plans skip cleanup"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        # Run cleanup for enterprise plan
        stats = service.cleanup_expired_artifacts(
            org_id=1,
            plan='enterprise',
            gdpr_override=False
        )
        
        # Should skip cleanup
        assert stats['retention_days'] == -1
        assert stats['artifacts_found'] == 0
        assert stats['artifacts_deleted'] == 0
    
    def test_cleanup_expired_artifacts_gdpr_override(self):
        """Test GDPR override deletes all artifacts regardless of age"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=True)  # Dry-run for test
        
        # Mock expired artifacts query
        mock_artifacts = [Mock(id=i, storage_key=f"key_{i}") for i in range(5)]
        
        with patch.object(service, 'list_expired_artifacts', return_value=mock_artifacts):
            with patch.object(service, 'delete_artifact_files', return_value=(True, 1024)):
                with patch.object(service, 'delete_artifact_records', return_value=(5, 0)):
                    stats = service.cleanup_expired_artifacts(
                        org_id=1,
                        plan='enterprise',  # Enterprise with GDPR override
                        gdpr_override=True
                    )
                    
                    # Should delete even with unlimited retention
                    assert stats['gdpr_override'] is True
                    assert stats['artifacts_found'] == 5
                    assert stats['artifacts_deleted'] == 5
    
    def test_list_expired_artifacts(self):
        """Test listing expired artifacts"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=False)
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Mock query chain
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [Mock(id=1), Mock(id=2)]
        
        mock_db.query.return_value = mock_query
        
        artifacts = service.list_expired_artifacts(cutoff_date, org_id=None, plan='free')
        
        assert len(artifacts) == 2
    
    def test_cleanup_all_organizations(self):
        """Test cleanup for all organizations"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=True)
        
        # Mock organizations
        mock_orgs = [Mock(id=1), Mock(id=2)]
        mock_db.query.return_value.all.return_value = mock_orgs
        
        # Mock subscriptions
        mock_sub = Mock(plan='pro')
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sub
        
        # Mock cleanup for each org
        with patch.object(service, 'cleanup_expired_artifacts') as mock_cleanup:
            mock_cleanup.return_value = {
                'artifacts_found': 5,
                'artifacts_deleted': 5,
                'artifacts_failed': 0,
                'bytes_freed': 1024000
            }
            
            stats = service.cleanup_all_organizations()
            
            assert stats['total_orgs'] == 2
            assert stats['total_artifacts_deleted'] == 10  # 5 per org
            assert stats['total_bytes_freed'] == 2048000  # 1024000 * 2
            assert mock_cleanup.call_count == 2


class TestRetentionConfiguration:
    """Test retention configuration"""
    
    def test_retention_config_loaded(self):
        """Test that retention config is loaded from environment"""
        from content_creation_crew.config import config
        
        # Verify config values exist
        assert hasattr(config, 'RETENTION_DAYS_FREE')
        assert hasattr(config, 'RETENTION_DAYS_BASIC')
        assert hasattr(config, 'RETENTION_DAYS_PRO')
        assert hasattr(config, 'RETENTION_DAYS_ENTERPRISE')
        assert hasattr(config, 'RETENTION_DRY_RUN')
    
    def test_dry_run_config(self):
        """Test dry-run mode from config"""
        from content_creation_crew.services.artifact_retention_service import get_retention_service
        
        mock_db = Mock()
        
        # Normal mode
        service = get_retention_service(mock_db, dry_run=False)
        # Dry-run flag depends on config.RETENTION_DRY_RUN
        
        # Explicit dry-run
        service = get_retention_service(mock_db, dry_run=True)
        assert service.dry_run is True


class TestRetentionScheduledJob:
    """Test retention cleanup scheduled job"""
    
    def test_retention_cleanup_job_exists(self):
        """Test that retention cleanup job function exists"""
        from content_creation_crew.services.scheduled_jobs import run_retention_cleanup_job
        
        assert callable(run_retention_cleanup_job)
    
    def test_retention_job_registered(self):
        """Test that retention job is registered in scheduler"""
        from content_creation_crew.services.scheduled_jobs import start_scheduler, get_scheduler
        
        # This would require full scheduler setup
        # For now, verify job is exported
        from content_creation_crew.services import scheduled_jobs
        
        assert 'run_retention_cleanup_job' in scheduled_jobs.__all__


class TestRetentionMetrics:
    """Test retention metrics integration"""
    
    def test_retention_metrics_recorded(self):
        """Test that retention metrics are recorded"""
        from content_creation_crew.services.metrics import RetentionMetrics, get_metrics_collector
        
        collector = get_metrics_collector()
        
        # Record some retention deletions
        RetentionMetrics.record_delete('free', 10, 5242880)  # 5MB
        
        # Verify counters
        deletes = collector.get_counter("retention_deletes_total", {"plan": "free"})
        assert deletes >= 10.0
        
        bytes_freed = collector.get_counter("retention_bytes_freed_total", {"plan": "free"})
        assert bytes_freed >= 5242880.0


class TestRetentionIntegration:
    """Integration tests for retention system"""
    
    @pytest.mark.asyncio
    async def test_retention_service_idempotent(self):
        """Test that retention cleanup is idempotent"""
        from content_creation_crew.services.artifact_retention_service import ArtifactRetentionService
        
        mock_db = Mock()
        service = ArtifactRetentionService(mock_db, dry_run=True)
        
        # Run cleanup twice with same data
        with patch.object(service, 'list_expired_artifacts', return_value=[]):
            stats1 = service.cleanup_expired_artifacts(1, 'free', gdpr_override=False)
            stats2 = service.cleanup_expired_artifacts(1, 'free', gdpr_override=False)
            
            # Should produce same results
            assert stats1['artifacts_found'] == stats2['artifacts_found']
            assert stats1['artifacts_deleted'] == stats2['artifacts_deleted']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


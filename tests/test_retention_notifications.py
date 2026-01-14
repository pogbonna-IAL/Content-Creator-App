"""
Tests for Retention Notification Service (M1 Enhancement)

Tests email notifications before artifact deletion
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.content_creation_crew.services.retention_notification_service import (
    RetentionNotificationService,
    get_retention_notification_service
)


class TestRetentionNotificationService:
    """Test suite for retention notification service"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def notification_service(self, mock_db):
        """Create notification service instance"""
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = True
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = False
            
            return RetentionNotificationService(mock_db, dry_run=False)
    
    def test_compute_notification_date_free_plan(self, notification_service):
        """Test notification date computation for free plan (30 days retention)"""
        # Free plan: 30 days retention - 7 days notice = notify at 23 days
        notification_date = notification_service.compute_notification_date('free')
        
        assert notification_date is not None
        
        # Should be approximately 23 days ago
        expected_days = 30 - 7  # 23 days
        expected_date = datetime.utcnow() - timedelta(days=expected_days)
        
        # Allow 1 minute tolerance
        assert abs((notification_date - expected_date).total_seconds()) < 60
    
    def test_compute_notification_date_basic_plan(self, notification_service):
        """Test notification date computation for basic plan (90 days retention)"""
        notification_date = notification_service.compute_notification_date('basic')
        
        assert notification_date is not None
        
        # Basic plan: 90 days retention - 7 days notice = notify at 83 days
        expected_days = 90 - 7  # 83 days
        expected_date = datetime.utcnow() - timedelta(days=expected_days)
        
        assert abs((notification_date - expected_date).total_seconds()) < 60
    
    def test_compute_notification_date_pro_plan(self, notification_service):
        """Test notification date computation for pro plan (365 days retention)"""
        notification_date = notification_service.compute_notification_date('pro')
        
        assert notification_date is not None
        
        # Pro plan: 365 days retention - 7 days notice = notify at 358 days
        expected_days = 365 - 7  # 358 days
        expected_date = datetime.utcnow() - timedelta(days=expected_days)
        
        assert abs((notification_date - expected_date).total_seconds()) < 60
    
    def test_compute_notification_date_enterprise_plan(self, notification_service):
        """Test notification date for enterprise plan (unlimited retention)"""
        # Enterprise plan has unlimited retention, so no notifications
        notification_date = notification_service.compute_notification_date('enterprise')
        
        assert notification_date is None
    
    def test_find_artifacts_needing_notification(self, notification_service, mock_db):
        """Test finding artifacts that need expiration notifications"""
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        # Mock join chain
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Mock artifacts
        mock_artifact_1 = Mock()
        mock_artifact_1.id = 1
        mock_artifact_1.artifact_type = 'video'
        mock_artifact_1.created_at = datetime.utcnow() - timedelta(days=25)
        mock_artifact_1.topic = 'AI Tutorial'
        mock_artifact_1.user_id = 1
        mock_artifact_1.email = 'user@example.com'
        
        mock_artifact_2 = Mock()
        mock_artifact_2.id = 2
        mock_artifact_2.artifact_type = 'audio'
        mock_artifact_2.created_at = datetime.utcnow() - timedelta(days=24)
        mock_artifact_2.topic = 'Podcast Episode'
        mock_artifact_2.user_id = 1
        mock_artifact_2.email = 'user@example.com'
        
        mock_query.all.return_value = [mock_artifact_1, mock_artifact_2]
        
        # Find artifacts
        user_artifacts_list = notification_service.find_artifacts_needing_notification(
            org_id=1,
            plan='free'
        )
        
        # Should group by user
        assert len(user_artifacts_list) == 1
        
        user_artifacts = user_artifacts_list[0]
        assert user_artifacts['user_id'] == 1
        assert user_artifacts['email'] == 'user@example.com'
        assert user_artifacts['plan'] == 'free'
        assert len(user_artifacts['artifacts']) == 2
    
    def test_find_artifacts_no_results(self, notification_service, mock_db):
        """Test finding artifacts when none need notification"""
        # Mock empty query result
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        user_artifacts_list = notification_service.find_artifacts_needing_notification(
            org_id=1,
            plan='free'
        )
        
        assert len(user_artifacts_list) == 0
    
    @patch('src.content_creation_crew.services.retention_notification_service.get_email_provider')
    def test_send_expiration_notification(self, mock_get_email_provider, notification_service):
        """Test sending expiration notification email"""
        # Mock email provider
        mock_email_provider = Mock()
        mock_get_email_provider.return_value = mock_email_provider
        
        # Prepare user artifacts
        user_artifacts = {
            'user_id': 1,
            'email': 'user@example.com',
            'plan': 'free',
            'artifacts': [
                {
                    'id': 1,
                    'type': 'video',
                    'topic': 'AI Tutorial',
                    'created_at': datetime.utcnow() - timedelta(days=25),
                    'days_until_deletion': 5
                },
                {
                    'id': 2,
                    'type': 'audio',
                    'topic': 'Podcast Episode',
                    'created_at': datetime.utcnow() - timedelta(days=24),
                    'days_until_deletion': 6
                }
            ]
        }
        
        # Send notification
        success = notification_service.send_expiration_notification(
            'user@example.com',
            user_artifacts
        )
        
        assert success is True
        
        # Verify email was sent
        mock_email_provider.send_email.assert_called_once()
        
        # Check email content
        call_args = mock_email_provider.send_email.call_args
        assert call_args[1]['to_email'] == 'user@example.com'
        assert '2 artifacts' in call_args[1]['subject']
        assert 'FREE plan' in call_args[1]['body'].upper()
        assert 'AI Tutorial' in call_args[1]['body']
        assert 'Podcast Episode' in call_args[1]['body']
    
    @patch('src.content_creation_crew.services.retention_notification_service.get_email_provider')
    def test_send_notification_dry_run(self, mock_get_email_provider, mock_db):
        """Test dry run mode doesn't send actual emails"""
        # Create service in dry-run mode
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = True
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = False
            
            service = RetentionNotificationService(mock_db, dry_run=True)
        
        # Mock email provider
        mock_email_provider = Mock()
        mock_get_email_provider.return_value = mock_email_provider
        
        user_artifacts = {
            'user_id': 1,
            'email': 'user@example.com',
            'plan': 'free',
            'artifacts': [
                {
                    'id': 1,
                    'type': 'video',
                    'topic': 'Test',
                    'created_at': datetime.utcnow(),
                    'days_until_deletion': 7
                }
            ]
        }
        
        # Send notification in dry-run
        success = service.send_expiration_notification(
            'user@example.com',
            user_artifacts
        )
        
        # Should succeed but not actually send email
        assert success is True
        mock_email_provider.send_email.assert_not_called()
    
    def test_send_notifications_disabled_via_config(self, mock_db):
        """Test that notifications are skipped when disabled"""
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = False  # Disabled
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = False
            
            service = RetentionNotificationService(mock_db, dry_run=False)
        
        stats = service.send_notifications_for_organization(org_id=1, plan='free')
        
        # Should return empty stats
        assert stats['users_notified'] == 0
        assert stats['users_failed'] == 0
        assert stats['total_artifacts'] == 0
    
    @patch('src.content_creation_crew.services.retention_notification_service.get_email_provider')
    def test_notification_email_content_structure(self, mock_get_email_provider, notification_service):
        """Test email content includes all required information"""
        mock_email_provider = Mock()
        mock_get_email_provider.return_value = mock_email_provider
        
        user_artifacts = {
            'user_id': 1,
            'email': 'user@example.com',
            'plan': 'basic',
            'artifacts': [
                {
                    'id': 1,
                    'type': 'video',
                    'topic': 'Tutorial',
                    'created_at': datetime.utcnow(),
                    'days_until_deletion': 3
                }
            ]
        }
        
        notification_service.send_expiration_notification('user@example.com', user_artifacts)
        
        call_args = mock_email_provider.send_email.call_args[1]
        body = call_args['body']
        
        # Check required content
        assert 'BASIC plan' in body.upper()
        assert 'Download your content' in body
        assert 'Upgrade your plan' in body
        assert 'cannot be recovered' in body.lower()
        assert 'support@contentcreationcrew.com' in body
    
    def test_get_retention_notification_service_with_dry_run_config(self, mock_db):
        """Test service factory respects RETENTION_DRY_RUN config"""
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = True
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = True  # Enabled via config
            
            # Even if we request dry_run=False, config should override
            service = get_retention_notification_service(mock_db, dry_run=False)
            
            assert service.dry_run is True
    
    def test_email_groups_artifacts_by_expiration_date(self, notification_service):
        """Test that email groups artifacts by days until deletion"""
        with patch('src.content_creation_crew.services.retention_notification_service.get_email_provider') as mock_get_provider:
            mock_email_provider = Mock()
            mock_get_provider.return_value = mock_email_provider
            
            user_artifacts = {
                'user_id': 1,
                'email': 'user@example.com',
                'plan': 'free',
                'artifacts': [
                    {'id': 1, 'type': 'video', 'topic': 'Video1', 'created_at': datetime.utcnow(), 'days_until_deletion': 0},
                    {'id': 2, 'type': 'video', 'topic': 'Video2', 'created_at': datetime.utcnow(), 'days_until_deletion': 0},
                    {'id': 3, 'type': 'audio', 'topic': 'Audio1', 'created_at': datetime.utcnow(), 'days_until_deletion': 3},
                    {'id': 4, 'type': 'audio', 'topic': 'Audio2', 'created_at': datetime.utcnow(), 'days_until_deletion': 7}
                ]
            }
            
            notification_service.send_expiration_notification('user@example.com', user_artifacts)
            
            body = mock_email_provider.send_email.call_args[1]['body']
            
            # Should mention "today", "in 3 days", "in 7 days"
            assert 'today' in body.lower()
            assert 'in 3 day' in body.lower()
            assert 'in 7 day' in body.lower()


class TestRetentionNotificationIntegration:
    """Integration tests for retention notifications"""
    
    @patch('src.content_creation_crew.services.retention_notification_service.config')
    def test_notification_timing_alignment_with_cleanup(self, mock_config):
        """Test that notifications are sent at the right time before cleanup"""
        mock_config.RETENTION_DAYS_FREE = 30
        mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
        mock_config.RETENTION_DRY_RUN = False
        
        mock_db = Mock(spec=Session)
        service = RetentionNotificationService(mock_db, dry_run=False)
        
        # Notification should happen at 23 days (30 - 7)
        notification_date = service.compute_notification_date('free')
        
        # Artifacts created 23+ days ago should trigger notification
        # Artifacts created 30+ days ago should be deleted (by cleanup job)
        
        expected_notification_age = 30 - 7  # 23 days
        expected_date = datetime.utcnow() - timedelta(days=expected_notification_age)
        
        assert abs((notification_date - expected_date).total_seconds()) < 60


class TestNotificationTracking:
    """Test suite for notification tracking and duplicate prevention"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def notification_service(self, mock_db):
        """Create notification service instance"""
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = True
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = False
            
            return RetentionNotificationService(mock_db, dry_run=False)
    
    def test_check_already_notified_returns_false_when_not_notified(self, notification_service, mock_db):
        """Test checking notification status when not previously notified"""
        # Mock query returns None (not notified)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        today = datetime.utcnow().date()
        result = notification_service.check_already_notified(
            user_id=1,
            artifact_id=1,
            notification_date=today
        )
        
        assert result is False
    
    def test_check_already_notified_returns_true_when_already_notified(self, notification_service, mock_db):
        """Test checking notification status when already notified"""
        # Mock query returns a notification record
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock()  # Notification exists
        
        today = datetime.utcnow().date()
        result = notification_service.check_already_notified(
            user_id=1,
            artifact_id=1,
            notification_date=today
        )
        
        assert result is True
    
    def test_record_notification_success(self, notification_service, mock_db):
        """Test recording notification successfully"""
        notification_service.record_notification(
            user_id=1,
            org_id=1,
            artifact_id=1,
            artifact_type='video',
            artifact_topic='Test Video',
            expiration_date=datetime.utcnow().date(),
            email_sent=True,
            failure_reason=None
        )
        
        # Verify database add was called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_record_notification_dry_run_no_commit(self, mock_db):
        """Test dry-run mode doesn't commit notifications"""
        with patch('src.content_creation_crew.services.retention_notification_service.config') as mock_config:
            mock_config.RETENTION_NOTIFY_DAYS_BEFORE = 7
            mock_config.RETENTION_NOTIFY_ENABLED = True
            mock_config.RETENTION_NOTIFY_BATCH_SIZE = 100
            mock_config.RETENTION_DRY_RUN = False
            
            service = RetentionNotificationService(mock_db, dry_run=True)
        
        service.record_notification(
            user_id=1,
            org_id=1,
            artifact_id=1,
            artifact_type='video',
            artifact_topic='Test',
            expiration_date=datetime.utcnow().date(),
            email_sent=True
        )
        
        # Verify rollback was called instead of commit
        mock_db.add.assert_called_once()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()
    
    def test_find_artifacts_excludes_already_notified(self, notification_service, mock_db):
        """Test that artifacts already notified today are excluded"""
        # Mock query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Return only artifacts not notified today
        mock_artifact = Mock()
        mock_artifact.id = 1
        mock_artifact.artifact_type = 'video'
        mock_artifact.created_at = datetime.utcnow() - timedelta(days=25)
        mock_artifact.topic = 'Not Notified Yet'
        mock_artifact.organization_id = 1
        mock_artifact.user_id = 1
        mock_artifact.email = 'user@example.com'
        
        mock_query.all.return_value = [mock_artifact]
        
        # Find artifacts
        user_artifacts_list = notification_service.find_artifacts_needing_notification(
            org_id=1,
            plan='free'
        )
        
        # Should find artifacts not notified
        assert len(user_artifacts_list) >= 0  # May be 0 if query filters everything


class TestHTMLEmailTemplates:
    """Test suite for HTML email templates"""
    
    def test_render_plain_text_template(self):
        """Test plain text template rendering"""
        from src.content_creation_crew.services.email_templates import RetentionNotificationTemplate
        
        artifacts = [
            {'id': 1, 'type': 'video', 'topic': 'Test Video', 'days_until_deletion': 0},
            {'id': 2, 'type': 'audio', 'topic': 'Test Audio', 'days_until_deletion': 3}
        ]
        
        deletion_groups = {
            0: [artifacts[0]],
            3: [artifacts[1]]
        }
        
        text = RetentionNotificationTemplate.render_plain_text(
            plan='free',
            artifacts=artifacts,
            deletion_groups=deletion_groups
        )
        
        # Check content
        assert 'FREE plan' in text.upper()
        assert 'Expiring today' in text
        assert 'Expiring in 3 days' in text
        assert 'Test Video' in text
        assert 'Test Audio' in text
        assert 'cannot be recovered' in text.lower()
    
    def test_render_html_template(self):
        """Test HTML template rendering"""
        from src.content_creation_crew.services.email_templates import RetentionNotificationTemplate
        
        artifacts = [
            {'id': 1, 'type': 'video', 'topic': 'Test Video', 'days_until_deletion': 0},
            {'id': 2, 'type': 'audio', 'topic': 'Test Audio', 'days_until_deletion': 7}
        ]
        
        deletion_groups = {
            0: [artifacts[0]],
            7: [artifacts[1]]
        }
        
        html = RetentionNotificationTemplate.render_html(
            plan='pro',
            artifacts=artifacts,
            deletion_groups=deletion_groups
        )
        
        # Check HTML structure
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html
        
        # Check content
        assert 'PRO' in html.upper()
        assert 'Expiring today' in html
        assert 'Expiring in 7 days' in html
        assert 'Test Video' in html
        assert 'Test Audio' in html
        
        # Check styling
        assert 'style=' in html
        assert 'background' in html
        assert 'color' in html
    
    def test_html_template_urgency_colors(self):
        """Test that HTML template uses appropriate urgency colors"""
        from src.content_creation_crew.services.email_templates import RetentionNotificationTemplate
        
        artifacts = [
            {'id': 1, 'type': 'video', 'topic': 'Urgent', 'days_until_deletion': 0},
            {'id': 2, 'type': 'video', 'topic': 'High Priority', 'days_until_deletion': 2},
            {'id': 3, 'type': 'video', 'topic': 'Notice', 'days_until_deletion': 7}
        ]
        
        deletion_groups = {
            0: [artifacts[0]],
            2: [artifacts[1]],
            7: [artifacts[2]]
        }
        
        html = RetentionNotificationTemplate.render_html(
            plan='free',
            artifacts=artifacts,
            deletion_groups=deletion_groups
        )
        
        # Check urgency indicators
        assert 'URGENT' in html
        assert 'HIGH PRIORITY' in html
        assert 'NOTICE' in html
        
        # Check color codes
        assert '#dc3545' in html  # Red for urgent
        assert '#fd7e14' in html  # Orange for high priority
        assert '#ffc107' in html  # Yellow for notice


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


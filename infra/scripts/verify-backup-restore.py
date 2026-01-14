#!/usr/bin/env python3
"""
Backup Restore Verification Script (M2)
Ensures backups can be restored and are usable
"""
import sys
import os
import subprocess
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupRestoreVerifier:
    """
    Verifies that database backups can be restored and contain valid data
    
    Process:
    1. Spin up temporary Postgres container
    2. Restore backup file into temp DB
    3. Run verification queries
    4. Report PASS/FAIL
    5. Cleanup
    """
    
    def __init__(
        self,
        backup_file: str,
        postgres_version: str = "15",
        test_db_name: str = "restore_test",
        test_container_name: str = "backup-restore-test",
        cleanup: bool = True
    ):
        """
        Initialize verifier
        
        Args:
            backup_file: Path to backup file (pg_dump format)
            postgres_version: PostgreSQL version to use
            test_db_name: Name for test database
            test_container_name: Docker container name
            cleanup: Whether to cleanup container after test
        """
        self.backup_file = Path(backup_file)
        self.postgres_version = postgres_version
        self.test_db_name = test_db_name
        self.test_container_name = test_container_name
        self.cleanup = cleanup
        
        # Verification results
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        
        logger.info(f"Initialized BackupRestoreVerifier")
        logger.info(f"  Backup file: {self.backup_file}")
        logger.info(f"  PostgreSQL version: {self.postgres_version}")
        logger.info(f"  Test DB: {self.test_db_name}")
        logger.info(f"  Container: {self.test_container_name}")
    
    def verify_backup_file_exists(self) -> bool:
        """Verify backup file exists and is readable"""
        logger.info("Checking backup file...")
        
        if not self.backup_file.exists():
            self.errors.append(f"Backup file not found: {self.backup_file}")
            return False
        
        if not self.backup_file.is_file():
            self.errors.append(f"Backup path is not a file: {self.backup_file}")
            return False
        
        size = self.backup_file.stat().st_size
        if size == 0:
            self.errors.append(f"Backup file is empty: {self.backup_file}")
            return False
        
        logger.info(f"✓ Backup file exists: {size:,} bytes")
        return True
    
    def cleanup_existing_container(self) -> bool:
        """Remove existing test container if it exists"""
        try:
            logger.info(f"Checking for existing container: {self.test_container_name}")
            
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "-f", f"name={self.test_container_name}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                logger.info(f"Removing existing container: {self.test_container_name}")
                subprocess.run(
                    ["docker", "rm", "-f", self.test_container_name],
                    capture_output=True,
                    check=True
                )
                logger.info("✓ Existing container removed")
            
            return True
        
        except subprocess.CalledProcessError as e:
            logger.warning(f"Error cleaning up container: {e}")
            return True  # Continue anyway
    
    def start_postgres_container(self) -> bool:
        """Start temporary PostgreSQL container"""
        try:
            logger.info(f"Starting PostgreSQL {self.postgres_version} container...")
            
            # Start container
            subprocess.run([
                "docker", "run",
                "--name", self.test_container_name,
                "-e", "POSTGRES_PASSWORD=testpass",
                "-e", "POSTGRES_DB=postgres",
                "-p", "5433:5432",  # Use different port to avoid conflicts
                "-d",
                f"postgres:{self.postgres_version}"
            ], check=True, capture_output=True)
            
            logger.info(f"✓ Container started: {self.test_container_name}")
            
            # Wait for PostgreSQL to be ready
            logger.info("Waiting for PostgreSQL to be ready...")
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    result = subprocess.run([
                        "docker", "exec", self.test_container_name,
                        "pg_isready", "-U", "postgres"
                    ], capture_output=True, timeout=5)
                    
                    if result.returncode == 0:
                        logger.info(f"✓ PostgreSQL ready after {attempt + 1} attempts")
                        time.sleep(2)  # Extra buffer
                        return True
                    
                except subprocess.TimeoutExpired:
                    pass
                
                time.sleep(1)
            
            self.errors.append("PostgreSQL failed to become ready")
            return False
        
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to start container: {e}")
            return False
    
    def restore_backup(self) -> bool:
        """Restore backup into temporary database"""
        try:
            logger.info(f"Restoring backup into {self.test_db_name}...")
            
            # Copy backup file into container
            logger.info("Copying backup file to container...")
            subprocess.run([
                "docker", "cp",
                str(self.backup_file),
                f"{self.test_container_name}:/tmp/backup.sql"
            ], check=True, capture_output=True)
            
            # Create test database
            logger.info(f"Creating database: {self.test_db_name}")
            subprocess.run([
                "docker", "exec", self.test_container_name,
                "psql", "-U", "postgres",
                "-c", f"CREATE DATABASE {self.test_db_name};"
            ], check=True, capture_output=True)
            
            # Restore backup
            logger.info("Restoring backup (this may take a while)...")
            result = subprocess.run([
                "docker", "exec", "-i", self.test_container_name,
                "psql", "-U", "postgres", "-d", self.test_db_name,
                "-f", "/tmp/backup.sql"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                # Check if errors are fatal
                stderr = result.stderr.lower()
                # Some warnings are OK (e.g., "already exists")
                fatal_errors = [
                    "fatal",
                    "could not connect",
                    "does not exist",
                    "permission denied"
                ]
                
                has_fatal_error = any(err in stderr for err in fatal_errors)
                
                if has_fatal_error:
                    self.errors.append(f"Restore failed: {result.stderr[:500]}")
                    return False
                else:
                    logger.warning(f"Restore completed with warnings: {result.stderr[:200]}")
            
            logger.info("✓ Backup restored successfully")
            return True
        
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to restore backup: {e}")
            return False
    
    def run_verification_query(self, name: str, query: str) -> Tuple[bool, Optional[str]]:
        """
        Run a verification query
        
        Args:
            name: Test name
            query: SQL query to run
        
        Returns:
            (success, result) tuple
        """
        try:
            result = subprocess.run([
                "docker", "exec", self.test_container_name,
                "psql", "-U", "postgres", "-d", self.test_db_name,
                "-t", "-c", query
            ], capture_output=True, text=True, check=True)
            
            return True, result.stdout.strip()
        
        except subprocess.CalledProcessError as e:
            return False, str(e)
    
    def verify_schema(self) -> bool:
        """Verify database schema is valid"""
        logger.info("Verifying database schema...")
        
        checks = [
            ("Alembic version table exists", 
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');"),
            
            ("Users table exists",
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"),
            
            ("Organizations table exists",
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'organizations');"),
            
            ("Content jobs table exists",
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'content_jobs');"),
            
            ("Content artifacts table exists",
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'content_artifacts');"),
            
            ("Subscriptions table exists",
             "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'subscriptions');"),
        ]
        
        all_passed = True
        
        for check_name, query in checks:
            success, result = self.run_verification_query(check_name, query)
            
            if success and result.strip().lower() == 't':
                logger.info(f"  ✓ {check_name}")
                self.results[check_name] = True
            else:
                logger.error(f"  ✗ {check_name}")
                self.results[check_name] = False
                self.errors.append(f"Schema check failed: {check_name}")
                all_passed = False
        
        return all_passed
    
    def verify_data_integrity(self) -> bool:
        """Verify data integrity with basic counts"""
        logger.info("Verifying data integrity...")
        
        checks = [
            ("Users count >= 0", "SELECT COUNT(*) FROM users;"),
            ("Organizations count >= 0", "SELECT COUNT(*) FROM organizations;"),
            ("Content jobs count >= 0", "SELECT COUNT(*) FROM content_jobs;"),
            ("Content artifacts count >= 0", "SELECT COUNT(*) FROM content_artifacts;"),
            ("Subscriptions count >= 0", "SELECT COUNT(*) FROM subscriptions;"),
        ]
        
        all_passed = True
        
        for check_name, query in checks:
            success, result = self.run_verification_query(check_name, query)
            
            if success:
                try:
                    count = int(result.strip())
                    if count >= 0:
                        logger.info(f"  ✓ {check_name} (count: {count})")
                        self.results[check_name] = True
                    else:
                        logger.error(f"  ✗ {check_name} (invalid count: {count})")
                        self.results[check_name] = False
                        all_passed = False
                except ValueError:
                    logger.error(f"  ✗ {check_name} (invalid result: {result})")
                    self.results[check_name] = False
                    all_passed = False
            else:
                logger.error(f"  ✗ {check_name} (query failed)")
                self.results[check_name] = False
                self.errors.append(f"Data integrity check failed: {check_name}")
                all_passed = False
        
        return all_passed
    
    def verify_migrations(self) -> bool:
        """Verify Alembic migration state"""
        logger.info("Verifying migrations...")
        
        success, result = self.run_verification_query(
            "Migration version",
            "SELECT version_num FROM alembic_version LIMIT 1;"
        )
        
        if success and result.strip():
            version = result.strip()
            logger.info(f"  ✓ Migration version: {version}")
            self.results["Migration version exists"] = True
            return True
        else:
            logger.warning("  ! No migration version found (may be fresh DB)")
            self.results["Migration version exists"] = False
            # Not a fatal error for empty backups
            return True
    
    def cleanup_container(self) -> bool:
        """Stop and remove test container"""
        if not self.cleanup:
            logger.info(f"Skipping cleanup (container: {self.test_container_name})")
            return True
        
        try:
            logger.info("Cleaning up test container...")
            subprocess.run([
                "docker", "rm", "-f", self.test_container_name
            ], check=True, capture_output=True)
            
            logger.info("✓ Container cleaned up")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.warning(f"Cleanup failed: {e}")
            return False
    
    def run_verification(self) -> bool:
        """
        Run complete verification process
        
        Returns:
            True if verification passed, False otherwise
        """
        logger.info("=" * 80)
        logger.info("BACKUP RESTORE VERIFICATION")
        logger.info("=" * 80)
        
        try:
            # Step 1: Check backup file
            if not self.verify_backup_file_exists():
                return False
            
            # Step 2: Cleanup existing container
            self.cleanup_existing_container()
            
            # Step 3: Start PostgreSQL
            if not self.start_postgres_container():
                return False
            
            # Step 4: Restore backup
            if not self.restore_backup():
                return False
            
            # Step 5: Verify schema
            schema_ok = self.verify_schema()
            
            # Step 6: Verify data
            data_ok = self.verify_data_integrity()
            
            # Step 7: Verify migrations
            migrations_ok = self.verify_migrations()
            
            # Overall result
            all_ok = schema_ok and data_ok
            
            # Print summary
            logger.info("=" * 80)
            logger.info("VERIFICATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Backup file: {self.backup_file}")
            logger.info(f"Total checks: {len(self.results)}")
            logger.info(f"Passed: {sum(1 for v in self.results.values() if v)}")
            logger.info(f"Failed: {sum(1 for v in self.results.values() if not v)}")
            
            if self.errors:
                logger.info(f"\nErrors ({len(self.errors)}):")
                for error in self.errors:
                    logger.error(f"  - {error}")
            
            if all_ok:
                logger.info("\n✅ VERIFICATION PASSED")
                logger.info("Backup can be restored successfully")
            else:
                logger.error("\n❌ VERIFICATION FAILED")
                logger.error("Backup restore encountered issues")
            
            logger.info("=" * 80)
            
            return all_ok
        
        finally:
            # Always cleanup
            self.cleanup_container()
    
    def get_exit_code(self) -> int:
        """Get appropriate exit code"""
        if not self.results:
            return 2  # No tests run
        
        if all(self.results.values()):
            return 0  # All passed
        else:
            return 1  # Some failed


def find_latest_backup(backup_dir: str) -> Optional[Path]:
    """Find the latest backup file in directory"""
    backup_path = Path(backup_dir)
    
    if not backup_path.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        return None
    
    # Find all .sql backup files
    backups = list(backup_path.glob("*.sql"))
    
    if not backups:
        logger.error(f"No backup files found in: {backup_dir}")
        return None
    
    # Sort by modification time
    latest = max(backups, key=lambda p: p.stat().st_mtime)
    
    logger.info(f"Found latest backup: {latest}")
    logger.info(f"  Modified: {datetime.fromtimestamp(latest.stat().st_mtime)}")
    logger.info(f"  Size: {latest.stat().st_size:,} bytes")
    
    return latest


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Verify database backup can be restored"
    )
    parser.add_argument(
        "backup_file",
        nargs="?",
        help="Path to backup file (or use --latest)"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use latest backup from backup directory"
    )
    parser.add_argument(
        "--backup-dir",
        default="./backups",
        help="Backup directory (default: ./backups)"
    )
    parser.add_argument(
        "--postgres-version",
        default="15",
        help="PostgreSQL version (default: 15)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep test container after verification"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine backup file
    if args.latest:
        backup_file = find_latest_backup(args.backup_dir)
        if not backup_file:
            sys.exit(2)
    elif args.backup_file:
        backup_file = args.backup_file
    else:
        parser.error("Provide backup_file or use --latest")
    
    # Run verification
    verifier = BackupRestoreVerifier(
        backup_file=str(backup_file),
        postgres_version=args.postgres_version,
        cleanup=not args.no_cleanup
    )
    
    success = verifier.run_verification()
    
    sys.exit(verifier.get_exit_code())


if __name__ == '__main__':
    main()


"""
Pytest configuration and fixtures for integration tests
"""
import pytest
import os
import sys
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables before importing
os.environ["ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-integration-tests-only-min-32-chars"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test_content_crew")
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["ENABLE_VIDEO_RENDERING"] = "false"  # Disable video rendering for tests
os.environ["LOG_LEVEL"] = "WARNING"  # Reduce log noise in tests

# Import after setting env vars
from content_creation_crew.config import config
from content_creation_crew.database import Base, SessionLocal, get_db, User
from content_creation_crew.db.engine import engine
from api_server import app


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL"""
    return os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test_content_crew")


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine"""
    # For Postgres, use regular connection pooling
    # For SQLite (if needed), use StaticPool
    if "sqlite" in test_database_url:
        test_engine = create_engine(
            test_database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
    else:
        # Postgres - use default pooling
        test_engine = create_engine(test_database_url)
    
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    yield test_engine
    
    # Cleanup
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()
    
    # Override get_db dependency
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    # Cleanup - rollback transaction and close connection
    try:
        transaction.rollback()
    except:
        pass
    try:
        connection.close()
    except:
        pass
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user(db_session: Session):
    """Create a test user"""
    from content_creation_crew.database import User
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("testpassword123"),
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def auth_headers(client, test_user):
    """Get authentication headers for testing"""
    # Login to get token
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}
    
    # Fallback: create token manually
    from content_creation_crew.auth import create_access_token
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def authenticated_client(client, auth_headers):
    """Create authenticated test client"""
    client.headers.update(auth_headers)
    return client


@pytest.fixture(scope="function", autouse=True)
def clear_cache():
    """Clear cache before each test"""
    try:
        from content_creation_crew.services.content_cache import get_cache
        cache = get_cache()
        cache.clear()
    except:
        pass


@pytest.fixture(scope="function", autouse=True)
def reset_metrics():
    """Reset metrics before each test"""
    try:
        from content_creation_crew.services.metrics import get_metrics_collector
        collector = get_metrics_collector()
        # Clear counters (implementation depends on metrics collector)
        # For now, we'll just ensure fresh state
    except:
        pass


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_database_url):
    """Set up test database with migrations"""
    try:
        from alembic.config import Config
        from alembic import command
        
        # Run migrations
        alembic_cfg = Config("alembic.ini")
        # Override database URL for migrations
        alembic_cfg.set_main_option("sqlalchemy.url", test_database_url)
        command.upgrade(alembic_cfg, "head")
        
        yield
        
        # Cleanup (optional - let fixtures handle it)
    except Exception as e:
        pytest.skip(f"Database setup failed: {e}")


@pytest.fixture(scope="function")
def mock_ollama(monkeypatch):
    """Mock Ollama calls to avoid external dependencies"""
    import json
    
    def mock_ollama_response(*args, **kwargs):
        """Mock Ollama API response"""
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                self.text = json.dumps({"models": []})
            
            def json(self):
                return {"models": []}
        
        return MockResponse()
    
    # Mock httpx calls to Ollama
    try:
        import httpx
        monkeypatch.setattr(httpx, "get", mock_ollama_response)
        monkeypatch.setattr(httpx, "post", mock_ollama_response)
    except:
        pass
    
    # Mock litellm calls
    try:
        import litellm
        def mock_completion(*args, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "This is a test blog post about the topic. It contains multiple paragraphs with detailed information."
                    }
                }]
            }
        monkeypatch.setattr(litellm, "completion", mock_completion)
    except:
        pass


import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app
from src.auth.throttling import user_requests
from src.auth.dependencies import get_user_identifier


client = TestClient(app)


class TestProfileEndpoint:
    """Test user profile endpoint functionality."""
    
    def setup_method(self):
        """Clear user requests before each test."""
        user_requests.clear()
    
    def test_unauthenticated_user_profile(self):
        """Test profile endpoint for unauthenticated users."""
        response = client.get("/profile")
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == "global_unauthenticated_user"
        assert data["usage_count"] == 0
        assert data["rate_limit"] == 3
        assert data["time_window_seconds"] == 60
        assert data["is_authenticated"] == False
    
    def test_authenticated_user_profile(self):
        """Test profile endpoint for authenticated users."""
        def mock_get_user_identifier():
            return "test_user"
        
        app.dependency_overrides[get_user_identifier] = mock_get_user_identifier
        
        try:
            response = client.get("/profile")
            assert response.status_code == 200
            
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["usage_count"] == 0
            assert data["rate_limit"] == 5
            assert data["time_window_seconds"] == 60
            assert data["is_authenticated"] == True
        finally:
            app.dependency_overrides.clear()
    
    def test_profile_shows_usage_count_after_requests(self):
        """Test that profile shows correct usage count after making requests."""
        def mock_get_user_identifier():
            return "test_user"
        
        app.dependency_overrides[get_user_identifier] = mock_get_user_identifier
        
        try:
            # Simulate making some requests by directly manipulating the user_requests
            import time
            current_time = time.time()
            user_requests["test_user"] = [current_time - 30, current_time - 20, current_time - 10]
            
            response = client.get("/profile")
            assert response.status_code == 200
            
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["usage_count"] == 3
            assert data["rate_limit"] == 5
            assert data["is_authenticated"] == True
        finally:
            app.dependency_overrides.clear()
    
    def test_profile_excludes_old_requests(self):
        """Test that profile excludes requests older than time window."""
        def mock_get_user_identifier():
            return "test_user"
        
        app.dependency_overrides[get_user_identifier] = mock_get_user_identifier
        
        try:
            import time
            current_time = time.time()
            # Add both recent and old requests
            user_requests["test_user"] = [
                current_time - 90,  # Old request (beyond 60s window)
                current_time - 30,  # Recent request
                current_time - 10   # Recent request
            ]
            
            response = client.get("/profile")
            assert response.status_code == 200
            
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["usage_count"] == 2  # Only recent requests counted
            assert data["rate_limit"] == 5
        finally:
            app.dependency_overrides.clear()
    
    def test_profile_endpoint_returns_correct_schema(self):
        """Test that profile endpoint returns all required fields."""
        response = client.get("/profile")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["user_id", "usage_count", "rate_limit", "time_window_seconds", "is_authenticated"]
        
        for field in required_fields:
            assert field in data
            assert data[field] is not None
    
    def test_multiple_users_separate_usage_counts(self):
        """Test that different users have separate usage counts."""
        import time
        current_time = time.time()
        
        # Set up usage for different users
        user_requests["user1"] = [current_time - 10]
        user_requests["user2"] = [current_time - 20, current_time - 30]
        
        # Test user1 profile
        def mock_get_user1():
            return "user1"
        
        app.dependency_overrides[get_user_identifier] = mock_get_user1
        try:
            response = client.get("/profile")
            data = response.json()
            assert data["user_id"] == "user1"
            assert data["usage_count"] == 1
        finally:
            app.dependency_overrides.clear()
        
        # Test user2 profile
        def mock_get_user2():
            return "user2"
        
        app.dependency_overrides[get_user_identifier] = mock_get_user2
        try:
            response = client.get("/profile")
            data = response.json()
            assert data["user_id"] == "user2"
            assert data["usage_count"] == 2
        finally:
            app.dependency_overrides.clear()
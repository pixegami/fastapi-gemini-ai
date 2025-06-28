import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.main import app, ChatRequest


client = TestClient(app)


class TestChatRequestValidation:
    """Test prompt length validation for ChatRequest model."""
    
    def test_valid_prompt(self):
        """Test that valid prompts are accepted."""
        valid_prompt = "Hello AI, how are you today?"
        request = ChatRequest(prompt=valid_prompt)
        assert request.prompt == valid_prompt
    
    def test_empty_prompt_raises_validation_error(self):
        """Test that empty prompts raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt="")
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "string_too_short"
        assert error["loc"] == ("prompt",)
    
    def test_prompt_too_long_raises_validation_error(self):
        """Test that prompts exceeding max length raise ValidationError."""
        long_prompt = "x" * 5001  # 5001 characters, exceeds limit of 5000
        
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(prompt=long_prompt)
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "string_too_long"
        assert error["loc"] == ("prompt",)
    
    def test_prompt_at_max_length_is_valid(self):
        """Test that prompts at exactly max length are valid."""
        max_length_prompt = "x" * 5000  # Exactly 5000 characters
        request = ChatRequest(prompt=max_length_prompt)
        assert request.prompt == max_length_prompt
        assert len(request.prompt) == 5000
    
    def test_prompt_at_min_length_is_valid(self):
        """Test that prompts at exactly min length are valid."""
        min_length_prompt = "x"  # Exactly 1 character
        request = ChatRequest(prompt=min_length_prompt)
        assert request.prompt == min_length_prompt
        assert len(request.prompt) == 1


class TestChatEndpointValidation:
    """Test prompt validation through the API endpoint."""
    
    def test_api_rejects_empty_prompt(self):
        """Test that API rejects empty prompts with 422 status."""
        response = client.post("/chat", json={"prompt": ""})
        assert response.status_code == 422
        
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "string_too_short"
        assert error_detail["loc"] == ["body", "prompt"]
    
    def test_api_rejects_prompt_too_long(self):
        """Test that API rejects prompts that are too long with 422 status."""
        long_prompt = "x" * 5001
        response = client.post("/chat", json={"prompt": long_prompt})
        assert response.status_code == 422
        
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "string_too_long"
        assert error_detail["loc"] == ["body", "prompt"]
    
    def test_api_accepts_valid_prompt_length(self):
        """Test that API accepts prompts within valid length range."""
        valid_prompt = "Tell me a short joke"
        
        # Note: This test will fail without proper GEMINI_API_KEY and rate limit handling
        # In a real test environment, you'd mock the AI platform or use test fixtures
        response = client.post("/chat", json={"prompt": valid_prompt})
        
        # We expect either 200 (success) or 500 (missing API key/rate limit)
        # but NOT 422 (validation error)
        assert response.status_code != 422
    
    def test_api_rejects_missing_prompt(self):
        """Test that API rejects requests without prompt field."""
        response = client.post("/chat", json={})
        assert response.status_code == 422
        
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "missing"
        assert error_detail["loc"] == ["body", "prompt"]
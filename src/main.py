import os
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field
from .ai.gemini import Gemini
from .auth.dependencies import get_user_identifier
from .auth.throttling import apply_rate_limit, get_user_usage_stats


# --- App Initialization ---
app = FastAPI()


# --- AI Configuration ---
def load_system_prompt():
    try:
        with open("src/prompts/system_prompt.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


system_prompt = load_system_prompt()
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

ai_platform = Gemini(api_key=gemini_api_key, system_prompt=system_prompt)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000, description="User prompt for the AI")


class ChatResponse(BaseModel):
    response: str


class UserProfileResponse(BaseModel):
    user_id: str
    usage_count: int
    rate_limit: int
    time_window_seconds: int
    is_authenticated: bool


# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_id: str = Depends(get_user_identifier)):
    apply_rate_limit(user_id)
    response_text = ai_platform.chat(request.prompt)
    return ChatResponse(response=response_text)


@app.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str = Depends(get_user_identifier)):
    usage_stats = get_user_usage_stats(user_id)
    return UserProfileResponse(**usage_stats)


@app.get("/")
async def root():
    return {"message": "API is running"}

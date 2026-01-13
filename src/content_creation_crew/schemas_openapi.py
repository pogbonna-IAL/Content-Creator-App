"""
OpenAPI schema definitions with examples for Content Creation Crew API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ContentArtifactExample(BaseModel):
    """Content artifact schema with example"""
    id: int = Field(..., description="Artifact ID", example=1)
    job_id: int = Field(..., description="Job ID", example=123)
    type: str = Field(..., description="Artifact type: blog, social, audio, video, voiceover_audio, final_video", example="blog")
    content_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured content data (JSON)",
        example={
            "title": "Introduction to AI",
            "content": "Artificial Intelligence is transforming...",
            "word_count": 500,
            "reading_time_minutes": 2
        }
    )
    content_text: Optional[str] = Field(
        None,
        description="Plain text content",
        example="Artificial Intelligence is transforming the way we work and live..."
    )
    prompt_version: Optional[str] = Field(None, description="Prompt version used", example="v1.0")
    model_used: Optional[str] = Field(None, description="LLM model used", example="ollama/llama3.1:8b")
    created_at: datetime = Field(..., description="Creation timestamp", example="2026-01-13T10:30:00Z")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "job_id": 123,
                "type": "blog",
                "content_json": {
                    "title": "Introduction to AI",
                    "content": "Artificial Intelligence is transforming the way we work and live...",
                    "word_count": 500,
                    "reading_time_minutes": 2
                },
                "content_text": "Artificial Intelligence is transforming the way we work and live...",
                "prompt_version": "v1.0",
                "model_used": "ollama/llama3.1:8b",
                "created_at": "2026-01-13T10:30:00Z"
            }
        }


class ContentJobExample(BaseModel):
    """Content job schema with example"""
    id: int = Field(..., description="Job ID", example=123)
    topic: str = Field(..., description="Content topic", example="Introduction to AI")
    formats_requested: List[str] = Field(..., description="Requested content types", example=["blog", "social"])
    status: str = Field(..., description="Job status: pending, running, completed, failed, cancelled", example="completed")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key", example="abc123")
    created_at: datetime = Field(..., description="Creation timestamp", example="2026-01-13T10:30:00Z")
    started_at: Optional[datetime] = Field(None, description="Start timestamp", example="2026-01-13T10:30:05Z")
    finished_at: Optional[datetime] = Field(None, description="Completion timestamp", example="2026-01-13T10:35:00Z")
    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of artifacts",
        example=[
            {
                "id": 1,
                "type": "blog",
                "content_json": {"title": "Introduction to AI", "word_count": 500},
                "created_at": "2026-01-13T10:35:00Z"
            }
        ]
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "topic": "Introduction to AI",
                "formats_requested": ["blog", "social"],
                "status": "completed",
                "idempotency_key": "abc123",
                "created_at": "2026-01-13T10:30:00Z",
                "started_at": "2026-01-13T10:30:05Z",
                "finished_at": "2026-01-13T10:35:00Z",
                "artifacts": [
                    {
                        "id": 1,
                        "type": "blog",
                        "content_json": {
                            "title": "Introduction to AI",
                            "word_count": 500
                        },
                        "created_at": "2026-01-13T10:35:00Z"
                    }
                ]
            }
        }


class ErrorResponseExample(BaseModel):
    """Error response schema with example"""
    code: str = Field(..., description="Error code", example="VALIDATION_ERROR")
    message: str = Field(..., description="Human-readable error message", example="Validation error: topic: field required")
    status_code: int = Field(..., description="HTTP status code", example=422)
    request_id: Optional[str] = Field(None, description="Request ID for correlation", example="550e8400-e29b-41d4-a716-446655440000")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details",
        example={
            "errors": [
                {
                    "loc": ["body", "topic"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Validation error: topic: field required",
                "status_code": 422,
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "details": {
                    "errors": [
                        {
                            "loc": ["body", "topic"],
                            "msg": "field required",
                            "type": "value_error.missing"
                        }
                    ]
                }
            }
        }


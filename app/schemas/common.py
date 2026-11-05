# ==============================================================================
# Standard API Response Schemas
# Path: app/schemas/common.py
# Purpose: Defines unified JSON response structures across all endpoints
#          to provide consistent payload formats for frontend consumers (Laravel/Vue.js).
# ==============================================================================

# Generic & TypeVar: Python typing utilities to implement generic data models
# Optional: Indicates that a field can hold a value of type T or be None
from typing import Generic, TypeVar, Optional, Any

# BaseModel: Pydantic base class for data validation and schema declaration
from pydantic import BaseModel

# Generic type variable T representing any payload data structure
T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Standard Envelope Response Pattern.
    Every endpoint returns JSON structured as:
    {
       "success": true,
       "message": "Operation completed successfully",
       "data": { ... payload of type T ... },
       "error": null
    }
    """
    # success: Boolean flag indicating if the operation succeeded (True) or failed (False)
    success: bool
    
    # message: Human-readable status message for logging and UI notifications
    message: str = "Operation completed successfully"
    
    # data: Actual payload data of generic type T (or None on failure)
    data: Optional[T] = None
    
    # error: Error message or code if failure occurred (or None on success)
    error: Optional[str] = None

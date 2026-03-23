"""Common schemas for API responses"""
from typing import Generic, List, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    data: List[T]
    meta: PaginationMeta


def create_paginated_response(
    items: List[T],
    page: int,
    page_size: int,
    total: int,
) -> PaginatedResponse[T]:
    """Create a paginated response"""
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )

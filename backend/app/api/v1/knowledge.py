from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeCategory,
    ErrorResponse,
)
from app.services.knowledge import KnowledgeService, get_knowledge_service
from typing import List


router = APIRouter()


@router.post(
    "/knowledge",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_document(
    document: KnowledgeDocumentCreate,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        db_doc = await knowledge_service.create_document(document)
        return KnowledgeDocumentResponse.model_validate(db_doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}",
        )


@router.get(
    "/knowledge/categories",
    response_model=List[KnowledgeCategory],
)
async def get_categories(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    return await knowledge_service.get_categories()


@router.get(
    "/knowledge/{doc_id}",
    response_model=KnowledgeDocumentResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_document(
    doc_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    doc = await knowledge_service.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return KnowledgeDocumentResponse.model_validate(doc)


@router.put(
    "/knowledge/{doc_id}",
    response_model=KnowledgeDocumentResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def update_document(
    doc_id: str,
    update: KnowledgeDocumentUpdate,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    doc = await knowledge_service.update_document(doc_id, update)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return KnowledgeDocumentResponse.model_validate(doc)


@router.delete(
    "/knowledge/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def delete_document(
    doc_id: str,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    success = await knowledge_service.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.post(
    "/knowledge/search",
    response_model=KnowledgeSearchResult,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    try:
        documents = await knowledge_service.search_documents(request)
        total = await knowledge_service.count_documents(request)

        return KnowledgeSearchResult(
            documents=[KnowledgeDocumentResponse.model_validate(d) for d in documents],
            query=request.query,
            language=request.language,
            total_results=total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )
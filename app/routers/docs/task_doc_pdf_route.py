from fastapi import APIRouter
from app.services.docs.task_doc_pdf_service import get_task_doc_by_id, compare_documents
from fastapi.responses import HTMLResponse,JSONResponse

router = APIRouter(prefix="/docs", tags=["Docs APIs"])



@router.get("/{task_doc_id}")
async def fetch_task_doc(task_doc_id: int):
    return await get_task_doc_by_id(task_doc_id)


@router.get("/compare_docs/{task_doc_id}", response_class=HTMLResponse)
async def compare_docs_html(task_doc_id: int):
    result = await compare_documents(task_doc_id)
    # Since response_class is HTMLResponse, return the diff_html directly if that's the intent
    # If you want JSON, change response_class to JSONResponse
    return result["data"] if result["status_code"] == 200 else JSONResponse(
        status_code=result["status_code"],
        content={"message": result["message"], "data": result["data"]}
 
   )
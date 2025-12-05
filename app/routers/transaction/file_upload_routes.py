from typing import List
from fastapi import APIRouter, UploadFile, File

from app.services.transaction.file_upload_service import save_uploaded_files, get_uploaded_file

# Add prefix and tags like your transaction router
router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])

# Upload multiple files
@router.post("/UploadFilesFromEditor")
async def upload_files_api(files: List[UploadFile] = File(...)):
    return await save_uploaded_files(files)


# Get a single file
@router.get("/GetEditorUploadedFile/{file_name}")
async def get_file_api(file_name: str):
    return await get_uploaded_file(file_name)
import os
import logging
from datetime import datetime
from typing import List
from fastapi import UploadFile, HTTPException
from starlette.responses import FileResponse

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

EDITOR_UPLOAD_DIR = "editor_uploaded_files"


async def save_uploaded_files(files: List[UploadFile]):
    saved_files = []

    # Create folder if not exists
    if not os.path.exists(EDITOR_UPLOAD_DIR):
        os.makedirs(EDITOR_UPLOAD_DIR, exist_ok=True)
        logger.info(f"Created upload directory: {EDITOR_UPLOAD_DIR}")

    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(EDITOR_UPLOAD_DIR, filename)

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        saved_files.append(os.path.abspath(file_path))
        logger.info(f"File uploaded: {filename}, size={len(content)} bytes")

    return {
        "status": "success",
        "uploaded_files": saved_files
    }


async def get_uploaded_file(file_name: str):
    file_path = os.path.join(EDITOR_UPLOAD_DIR, file_name)

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_name}")
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"File retrieved: {file_name}")
    return FileResponse(file_path, filename=file_name)

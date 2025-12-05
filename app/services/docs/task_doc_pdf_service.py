from diff_match_patch import diff_match_patch
from sqlalchemy import select

from app.db import task_docs_table
from app.db.database import database


async def get_task_doc_by_id(task_doc_id: int):
    try:
        query = select(
            task_docs_table.c.task_doc_id,
            task_docs_table.c.document_json
        ).where(task_docs_table.c.task_doc_id == task_doc_id)

        record = await database.fetch_one(query)

        if not record:
            return {
                "status_code": 404,
                "message": "Task document not found",
                "data": None
            }

        return {
            "status_code": 200,
            "message": "Task document fetched successfully",
            "data": dict(record)
        }

    except Exception as e:
        return {
            "status_code": 500,
            "message": f"Internal server error: {str(e)}",
            "data": None
        }


async def compare_documents(task_doc_id: int):
    try:
        # 1️⃣ Fetch current doc
        current_stmt = select(task_docs_table).where(
            task_docs_table.c.task_doc_id == task_doc_id
        )
        current_doc = await database.fetch_one(current_stmt)

        if not current_doc:
            return {
                "status_code": 404,
                "message": "Task document not found",
                "data": None
            }

        project_task_id = current_doc["project_task_id"]
        current_version = current_doc["doc_version"]

        # 2️⃣ Fetch previous version from same project_task_id
        prev_stmt = (
            select(task_docs_table)
            .where(task_docs_table.c.project_task_id == project_task_id)
            .where(task_docs_table.c.doc_version < current_version)
            .order_by(task_docs_table.c.doc_version.desc())
            .limit(1)
        )
        prev_doc = await database.fetch_one(prev_stmt)

        # ✅ NEW CHANGE HERE ✅
        if not prev_doc:
            return {
                "status_code": 200,
                "message": "Only one version exists — nothing to compare",
                "data": current_doc["document_json"] or ""
            }

        old_html = prev_doc["document_json"] or ""
        new_html = current_doc["document_json"] or ""

        # 3️⃣ Validate
        if not isinstance(old_html, str) or not isinstance(new_html, str):
            return {
                "status_code": 400,
                "message": "HTML content invalid",
                "data": None
            }

        if not old_html.strip() or not new_html.strip():
            return {
                "status_code": 400,
                "message": "One or both documents empty",
                "data": None
            }

        # 4️⃣ Diff
        dmp = diff_match_patch()
        diffs = dmp.diff_main(old_html, new_html)
        dmp.diff_cleanupSemantic(diffs)

        diff_html = "".join(
            f"<del style='background:#ffe6e6;color:red'>{text}</del>" if op == -1 else
            f"<ins style='background:#e6ffe6;color:green'>{text}</ins>" if op == 1 else
            text
            for op, text in diffs
        )

        return {
            "status_code": 200,
            "message": "Documents compared successfully",
            "data": diff_html
        }

    except Exception as e:
        return {
            "status_code": 500,
            "message": f"An error occurred: {str(e)}",
            "data": None
        }
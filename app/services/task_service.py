import logging
from fastapi import status
from fastapi.responses import JSONResponse
from app.db.database import database
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.schemas.task_schema import TaskResponse, TaskCreateRequest, TaskUpdateRequest, TaskDeleteRequest
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)

async def get_all_tasks():
    try:
        logger.info("Start to fetch all sdlc tasks.")
        query = select(sdlc_tasks_table).where(sdlc_tasks_table.c.is_active == True).order_by(sdlc_tasks_table.c.order_id.asc())
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active tasks found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No tasks found",
                    "data": []
                }
            )

        result = [TaskResponse(**row) for row in rows]

        logger.info("tasks fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "tasks fetched successfully",
                "data": [r.dict() for r in result]
            }
        )
    except Exception as e:
        logger.error(f"Internal server error while fetching tasks: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def create_task(payload: TaskCreateRequest):
    try:
        logger.info("Start to create sdlc task.")

        # 1. Validation: task name required
        if not payload.task_name or payload.task_name.strip() == "":
            logger.warning("task name is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "task name is required",
                    "data": []
                }
            )

        # 2. Check if task exists (case-insensitive)
        query = select(sdlc_tasks_table).where(
            func.lower(sdlc_tasks_table.c.task_name) == payload.task_name.lower()
        )
        existing_task = await database.fetch_one(query)

        if existing_task:
            if existing_task.is_active:
                logger.warning(f"task '{payload.task_name}' already exists and is active.")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"task '{payload.task_name}' already exists",
                        "data": []
                    }
                )
            else:
                # Activate the inactive task
                update_query = (
                    sdlc_tasks_table.update()
                    .where(sdlc_tasks_table.c.task_id == existing_task.task_id)
                    .values(is_active=True)
                )
                await database.execute(update_query)
                logger.info(f"Inactive task '{payload.task_name}' activated with ID {existing_task.task_id}.")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": f"task '{payload.task_name}' activated successfully",
                        "data": {
                            "task_id": existing_task.task_id,
                            "task_name": payload.task_name
                        }
                    }
                )

        # 3. Check duplicate order_id for active tasks
        order_conflict_query = select(sdlc_tasks_table).where(
            and_(
                sdlc_tasks_table.c.order_id == payload.order_id,
                sdlc_tasks_table.c.is_active == True
            )
        )
        conflict_order = await database.fetch_one(order_conflict_query)
        if conflict_order:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"order_id '{payload.order_id}' already exists for another task",
                    "data": []
                }
            )

        # 4. Insert new task
        insert_query = sdlc_tasks_table.insert().values(
            task_name=payload.task_name,
            order_id=payload.order_id,
            is_active=payload.is_active
        )
        new_task_id = await database.execute(insert_query)

        logger.info(f"task '{payload.task_name}' created successfully with ID {new_task_id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "task created successfully",
                "data": {
                    "task_id": new_task_id,
                    "task_name": payload.task_name,
                    "order_id": payload.order_id
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while creating task: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def update_task(payload: TaskUpdateRequest):
    try:
        logger.info("Start to update task")

        # 1. Validation
        if not payload.task_id:
            logger.warning("task ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "task ID is required",
                    "data": []
                }
            )

        if not payload.task_name or payload.task_name.strip() == "":
            logger.warning("task name is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "task name is required",
                    "data": []
                }
            )

        # 2. Check if task exists by ID
        query = select(sdlc_tasks_table).where(sdlc_tasks_table.c.task_id == payload.task_id)
        existing_task = await database.fetch_one(query)

        if not existing_task:
            logger.warning(f"task ID {payload.task_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "task not found",
                    "data": []
                }
            )

        # 3. Check if new task name already exists for another task
        conflict_query = select(sdlc_tasks_table).where(
            and_(
                func.lower(sdlc_tasks_table.c.task_name) == payload.task_name.lower(),
                sdlc_tasks_table.c.task_id != payload.task_id,
                sdlc_tasks_table.c.is_active == True
            )
        )
        conflict_task = await database.fetch_one(conflict_query)
        if conflict_task:
            logger.warning(f"task name '{payload.task_name}' already exists for another task.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"task name '{payload.task_name}' already exists",
                    "data": []
                }
            )

        # 4. Check if order_id already exists for another task
        order_conflict_query = select(sdlc_tasks_table).where(
            and_(
                sdlc_tasks_table.c.order_id == payload.order_id,
                sdlc_tasks_table.c.task_id != payload.task_id,
                sdlc_tasks_table.c.is_active == True
            )
        )
        conflict_order = await database.fetch_one(order_conflict_query)
        if conflict_order:
            logger.warning(f"order_id '{payload.order_id}' already exists for another task.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"order_id '{payload.order_id}' already exists for another task",
                    "data": []
                }
            )

        # 5. Update task name and order_id
        update_query = (
            sdlc_tasks_table.update()
            .where(sdlc_tasks_table.c.task_id == payload.task_id)
            .values(task_name=payload.task_name, order_id=payload.order_id)
        )
        await database.execute(update_query)

        logger.info(f"task ID {payload.task_id} updated successfully to '{payload.task_name}' with order_id {payload.order_id}.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "task updated successfully",
                "data": {
                    "task_id": payload.task_id,
                    "task_name": payload.task_name,
                    "order_id": payload.order_id
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while updating sdlc task: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )


async def delete_task(payload: TaskDeleteRequest):
    try:
        logger.info(f"Start to delete task")

        # 1. Validation
        if not payload.task_id:
            logger.warning("task ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "task ID is required",
                    "data": []
                }
            )

        # 2. Check if task exists
        query = select(sdlc_tasks_table).where(sdlc_tasks_table.c.task_id == payload.task_id)
        existing_task = await database.fetch_one(query)

        if not existing_task:
            logger.warning(f"task ID {payload.task_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "task not found",
                    "data": []
                }
            )

        # 3. Check if already inactive
        if not existing_task.is_active:
            logger.warning(f"task ID {payload.task_id} is already inactive.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "task is already inactive",
                    "data": []
                }
            )

        # 3.1 New condition: Check if task_id is present in sdlc_phase_tasks_mapping
        mapping_query = select(sdlc_phase_tasks_mapping_table).where(
            sdlc_phase_tasks_mapping_table.c.task_id == payload.task_id
        )
        mapping_exists = await database.fetch_one(mapping_query)

        if mapping_exists:
            logger.warning(f"Task ID {payload.task_id} is mapped in sdlc_phase_tasks_mapping, cannot inactivate.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "Task is mapped to a phase and cannot be inactivated",
                    "data": []
                }
            )

        # 4. Update task to inactive
        update_query = (
            sdlc_tasks_table.update()
            .where(sdlc_tasks_table.c.task_id == payload.task_id)
            .values(is_active=False)
        )
        await database.execute(update_query)

        logger.info(f"task ID {payload.task_id} marked as inactive successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "task inactivated successfully",
                "data": {
                    "task_id": payload.task_id,
                    "is_active": False
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while inactivating task: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )


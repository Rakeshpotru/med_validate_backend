from collections import defaultdict
from sqlalchemy import select,insert,update,func
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import status
from datetime import datetime

from app.db import project_phases_list_table, sdlc_phases_table, sdlc_tasks_table
from app.db.database import database

from app.db.transaction.projects import projects
from app.db.transaction.comment_replies import comment_replies_table
from app.db.transaction.project_comments import project_comments_table
from app.db.transaction.project_task_users import project_task_users_table
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.docs.task_docs import task_docs_table
from app.schemas.transaction.project_comments_schema import ProjectCommentCreateRequest, CommentReplyCreateRequest,CommentUpdateRequest, ReplyUpdateRequest, RevertBackRequest
import logging

from app.db.transaction.users import users  # Import the Table, not the module

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def create_project_comment(data: ProjectCommentCreateRequest):
    try:
        logger.info(f"Creating comment for project_task_id={data.project_task_id}")

        # Fetch project_id and project_phase_id from project_task_id
        join_query = (
            select(
                project_phases_list_table.c.project_id,
                project_tasks_list_table.c.project_phase_id
            )
            .select_from(
                project_tasks_list_table.join(
                    project_phases_list_table,
                    project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id
                )
            )
            .where(project_tasks_list_table.c.project_task_id == data.project_task_id)
        )
        task_phase = await database.fetch_one(join_query)

        if not task_phase:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=jsonable_encoder({
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"Task {data.project_task_id} not found",
                    "data": None,
                }),
            )

        project_id = task_phase.project_id
        project_phase_id = task_phase.project_phase_id

        logger.info(
            f"Resolved project_id={project_id}, project_phase_id={project_phase_id} "
            f"for project_task_id={data.project_task_id}"
        )
        is_direct_comment = getattr(data, "is_direct_comment", True)

        # Insert comment
        insert_query = (
            insert(project_comments_table)
            .values(
                project_id=project_id,
                project_phase_id=project_phase_id,
                project_task_id=data.project_task_id,
                description=data.description,
                commented_by=data.commented_by,
                comment_date=datetime.utcnow(),
                is_resolved=False,
                is_direct_comment=data.is_direct_comment
            )
            .returning(*project_comments_table.c)
        )

        new_comment = await database.fetch_one(insert_query)
        if not new_comment:
            logger.warning(f"Failed to create comment for task_id={data.project_task_id}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=jsonable_encoder({
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Failed to create comment",
                    "data": None,
                }),
            )

        logger.info(f"Comment created successfully with comment_id={new_comment['comment_id']}")

        # # Update current task
        # update_current_task = (
        #     update(project_tasks_list_table)
        #     .where(project_tasks_list_table.c.project_task_id == data.project_task_id)
        #     .values(task_status_id=4, task_users_submitted=0)
        # )
        # await database.execute(update_current_task)

        # # Handle previous task
        # previous_task_query = (
        #     select(project_tasks_list_table.c.project_task_id)
        #     .where(project_tasks_list_table.c.project_task_id == data.project_task_id - 1)
        # )
        # previous_task = await database.fetch_one(previous_task_query)

        # if previous_task and previous_task.project_task_id != data.project_task_id:
        #     update_previous_task = (
        #         update(project_tasks_list_table)
        #         .where(project_tasks_list_table.c.project_task_id == previous_task.project_task_id)
        #         .values(task_status_id=5, task_users_submitted=0)
        #     )
        #     await database.execute(update_previous_task)

        #     reset_prev_task_users = (
        #         update(project_task_users_table)
        #         .where(project_task_users_table.c.project_task_id == previous_task.project_task_id)
        #         .values(submitted=False)
        #     )
        #     await database.execute(reset_prev_task_users)

        # # Reset submitted flag for current task users
        # reset_current_task_users = (
        #     update(project_task_users_table)
        #     .where(project_task_users_table.c.project_task_id == data.project_task_id)
        #     .values(submitted=False)
        # )
        # await database.execute(reset_current_task_users)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=jsonable_encoder({
                "status_code": status.HTTP_201_CREATED,
                "message": "Comment created successfully and task statuses updated",
                "data": dict(new_comment),
            }),
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in create_project_comment: {error_msg}", exc_info=True)

        if "foreign key constraint" in error_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Invalid project_task_id",
                    "details": error_msg,
                    "data": None,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "details": error_msg,
                "data": None,
            },
        )

# async def get_comments_by_task(task_id: int):
#     try:
#         logger.info(f"Fetching phase_id for task_id={task_id}")

#         # 1. Find the phase_id for this task
#         phase_query = select(project_tasks_list_table.c.project_phase_id).where(
#             project_tasks_list_table.c.project_task_id == task_id
#         ).limit(1)

#         phase_row = await database.fetch_one(phase_query)
#         if not phase_row:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content=jsonable_encoder({
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": f"No phase found for task {task_id}",
#                     "data": [],
#                 }),
#             )

#         phase_id = phase_row["project_phase_id"]
#         logger.info(f"Found phase_id={phase_id} for task_id={task_id}")

#         # 2. Fetch all comments under this phase
#         query = (
#             select(
#                 project_comments_table.c.comment_id,
#                 project_comments_table.c.description,
#                 project_comments_table.c.commented_by,
#                 project_comments_table.c.comment_date,
#                 project_comments_table.c.is_resolved,
#                 project_comments_table.c.resolved_by,
#                 project_comments_table.c.resolved_date,
#                 project_comments_table.c.project_task_id,
#                 users.c.user_name.label("commented_by_name"),
#             )
#             .join(users, users.c.user_id == project_comments_table.c.commented_by)
#             .where(project_comments_table.c.project_phase_id == phase_id)
#             .order_by(project_comments_table.c.comment_date.asc())
#         )

#         comments = await database.fetch_all(query)
#         if not comments:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content=jsonable_encoder({
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": f"No comments found for phase {phase_id}",
#                     "data": [],
#                 }),
#             )

#         # 3. Attach replies
#         results = []
#         for comment in comments:
#             comment_dict = dict(comment)

#             reply_query = (
#                 select(
#                     comment_replies_table.c.reply_id,
#                     comment_replies_table.c.reply_description,
#                     comment_replies_table.c.replied_by,
#                     comment_replies_table.c.replied_date,
#                     users.c.user_name.label("replied_by_name"),
#                 )
#                 .join(users, users.c.user_id == comment_replies_table.c.replied_by)
#                 .where(comment_replies_table.c.comment_id == comment["comment_id"])
#                 .order_by(comment_replies_table.c.replied_date.asc())
#             )
#             replies = await database.fetch_all(reply_query)
#             comment_dict["replies"] = [dict(r) for r in replies]

#             results.append(comment_dict)
#             logger.info(f"Comment {comment['comment_id']} has {len(replies)} replies")

#         # 4. Return all phase comments
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content=jsonable_encoder({
#                 "status_code": status.HTTP_200_OK,
#                 "message": f"Comments and replies fetched successfully for phase {phase_id} (from task {task_id})",
#                 "data": results,
#             }),
#         )

#     except Exception as e:
#         logger.exception(f"Error while fetching comments for task_id={task_id}: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": "Internal server error",
#                 "data": None,
#             },
#         )


async def get_comments_by_task(task_id: int):
    try:
        logger.info(f"Fetching phase_id for task_id={task_id}")

        # 1. Get phase_id for given task
        phase_query = (
            select(project_tasks_list_table.c.project_phase_id)
            .where(project_tasks_list_table.c.project_task_id == task_id)
            .limit(1)
        )
        phase_row = await database.fetch_one(phase_query)
        if not phase_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=jsonable_encoder({
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No phase found for task {task_id}",
                    "data": [],
                }),
            )

        phase_id = phase_row["project_phase_id"]
        logger.info(f"Found phase_id={phase_id} for task_id={task_id}")

        # 2. Fetch all comments for this phase
        comment_query = (
            select(
                project_comments_table.c.comment_id,
                project_comments_table.c.description,
                project_comments_table.c.commented_by,
                project_comments_table.c.comment_date,
                project_comments_table.c.is_resolved,
                project_comments_table.c.resolved_by,
                project_comments_table.c.resolved_date,
                project_comments_table.c.project_task_id,
                project_comments_table.c.is_direct_comment,
                users.c.user_name.label("commented_by_name"),
                project_tasks_list_table.c.task_status_id
            )
            .join(users, users.c.user_id == project_comments_table.c.commented_by)
            .join(project_tasks_list_table, project_tasks_list_table.c.project_task_id == task_id)
            .where(project_comments_table.c.project_phase_id == phase_id)
            .order_by(project_comments_table.c.comment_date.asc())
        )
        comments = await database.fetch_all(comment_query)

        if not comments:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=jsonable_encoder({
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No comments found for phase {phase_id}",
                    "data": [],
                }),
            )

        comment_ids = [c["comment_id"] for c in comments]

        # 3. Fetch all replies for these comment_ids in a single query
        reply_query = (
            select(
                comment_replies_table.c.reply_id,
                comment_replies_table.c.reply_description,
                comment_replies_table.c.replied_by,
                comment_replies_table.c.replied_date,
                comment_replies_table.c.comment_id,
                users.c.user_name.label("replied_by_name"),
            )
            .join(users, users.c.user_id == comment_replies_table.c.replied_by)
            .where(comment_replies_table.c.comment_id.in_(comment_ids))
            .order_by(comment_replies_table.c.replied_date.asc())
        )
        replies = await database.fetch_all(reply_query)

        # 4. Group replies by comment_id
        replies_by_comment = {}
        for r in replies:
            r_dict = dict(r)
            replies_by_comment.setdefault(r_dict["comment_id"], []).append(r_dict)

        # 5. Combine comments with their replies
        results = []
        for comment in comments:
            c_dict = dict(comment)
            c_dict["replies"] = replies_by_comment.get(comment["comment_id"], [])
            results.append(c_dict)

        logger.info(f"Fetched {len(results)} comments and {len(replies)} replies for phase_id={phase_id}")

        # 6. Return response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": f"Comments and replies fetched successfully for phase {phase_id} (from task {task_id})",
                "data": results,
            }),
        )

    except Exception as e:
        logger.exception(f"Error while fetching comments for task_id={task_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )


async def create_comment_reply(db, reply: CommentReplyCreateRequest):
    try:
        replied_date = datetime.utcnow()
        logger.info(f"Creating reply for comment_id={reply.comment_id} by user={reply.replied_by}")

        # 1. Insert into comment_replies
        insert_stmt = (
            insert(comment_replies_table)
            .values(
                comment_id=reply.comment_id,
                reply_description=reply.reply_description,
                replied_by=reply.replied_by,
                replied_date=replied_date,
            )
            .returning(
                comment_replies_table.c.reply_id,
                comment_replies_table.c.comment_id,
                comment_replies_table.c.reply_description,
                comment_replies_table.c.replied_by,
                comment_replies_table.c.replied_date,
            )
        )

        new_reply = await db.fetch_one(insert_stmt)
        if not new_reply:
            logger.error("Failed to insert comment reply")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Failed to insert comment reply",
                    "data": None
                }
            )

        logger.info(f"Reply inserted successfully with reply_id={new_reply['reply_id']}")

        # 2. Update project_comments → mark as resolved
        update_stmt = (
            update(project_comments_table)
            .where(project_comments_table.c.comment_id == reply.comment_id)
            .values(is_resolved=True)
        )
        await db.execute(update_stmt)
        logger.info(f"Updated project_comments -> is_resolved=True for comment_id={reply.comment_id}")

        # 3. Return success response
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": f"Reply added and comment {reply.comment_id} marked as resolved",
                "data": jsonable_encoder(dict(new_reply))   # datetime safe
            }
        )

    except Exception as e:
        logger.exception(f"Error while creating comment reply: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"An error occurred: {str(e)}",
                "data": None
            }
        )


async def resolve_comment_service(comment_id: int, user_id: int):
    try:
        logger.info(f"Resolving comment_id={comment_id} by user_id={user_id}")

        # Fetch the comment
        query = select(project_comments_table).where(project_comments_table.c.comment_id == comment_id)
        comment = await database.fetch_one(query)

        if not comment:
            logger.warning(f"Comment not found: comment_id={comment_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": 404,
                    "message": "Comment not found",
                    "data": {"comment_id": comment_id}
                }
            )

        # If already resolved, return existing info
        if comment.is_resolved:
            logger.info(f"Comment already resolved: comment_id={comment_id}, resolved_by={comment.resolved_by}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": 200,
                    "message": "Comment already resolved",
                    "data": {
                        "comment_id": comment.comment_id,
                        "is_resolved": True,
                        "resolved_by": comment.resolved_by,
                        "resolved_date": comment.resolved_date.isoformat() if comment.resolved_date else None
                    }
                }
            )

        # Update to resolved
        resolved_date = datetime.utcnow()
        update_stmt = (
            update(project_comments_table)
            .where(project_comments_table.c.comment_id == comment_id)
            .values(
                is_resolved=True,
                resolved_by=user_id,
                resolved_date=resolved_date
            )
        )
        await database.execute(update_stmt)
        logger.info(f"Comment resolved successfully: comment_id={comment_id}, resolved_by={user_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "Comment resolved successfully",
                "data": {
                    "comment_id": comment_id,
                    "is_resolved": True,
                    "resolved_by": user_id,
                    "resolved_date": resolved_date.isoformat()
                }
            }
        )

    except Exception as e:
        logger.exception(f"Error while resolving comment_id={comment_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": 500,
                "message": f"An error occurred: {str(e)}",
                "data": {"comment_id": comment_id}
            }
        )


async def get_user_comments_service(user_id: int, project_id: int = None):
    try:
        logger.info(f"Fetching comments for user_id={user_id}, project_id={project_id}")

        # Subquery 1: fetch all project_task_ids for this user
        user_task_ids_subq = (
            select(project_task_users_table.c.project_task_id)
            .distinct()
            .where(project_task_users_table.c.user_id == user_id)
        )
        # Subquery 2: fetch distinct phases from those tasks
        user_phase_ids_subq = (
            select(project_tasks_list_table.c.project_phase_id)
            .distinct()
            .where(project_tasks_list_table.c.project_task_id.in_(user_task_ids_subq))
        )
        # Step 1: Fetch all comments for this user (and project if given)
        query = (
            select(
                project_comments_table.c.comment_id,
                project_comments_table.c.description,
                project_comments_table.c.commented_by,
                project_comments_table.c.comment_date,
                project_comments_table.c.is_resolved,
                project_comments_table.c.resolved_by,
                project_comments_table.c.resolved_date,
                project_comments_table.c.project_id,
                project_comments_table.c.is_direct_comment,
                projects.c.project_name.label("project_name"),
                sdlc_phases_table.c.phase_id.label("sdlc_phase_id"),
                project_phases_list_table.c.project_phase_id.label("project_phase_id"),
                sdlc_tasks_table.c.task_id.label("sdlc_task_id"),
                project_tasks_list_table.c.project_task_id.label("project_task_id"),
                project_tasks_list_table.c.task_order_id,
                project_tasks_list_table.c.task_status_id,
                sdlc_phases_table.c.phase_name,
                sdlc_tasks_table.c.task_name,
                users.c.user_name.label("commented_by_name"),
            )
            .join(project_phases_list_table, project_comments_table.c.project_phase_id == project_phases_list_table.c.project_phase_id)
            .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
            .join(project_tasks_list_table, project_comments_table.c.project_task_id == project_tasks_list_table.c.project_task_id)
            .join(sdlc_tasks_table, project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id)
            .join(users, users.c.user_id == project_comments_table.c.commented_by)
            .join(projects, projects.c.project_id == project_comments_table.c.project_id)
            .where(project_phases_list_table.c.project_phase_id.in_(user_phase_ids_subq))
            .order_by(
                sdlc_phases_table.c.order_id,
                sdlc_tasks_table.c.order_id,
                project_comments_table.c.comment_date,
            )
        )

        if project_id is not None and project_id != 0:
            query = query.where(project_comments_table.c.project_id == project_id)

        comments = await database.fetch_all(query)
        if not comments:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=jsonable_encoder({
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No comments found",
                    "data": [],
                }),
            )

        # Step 2: Fetch all replies for these comments in one query
        comment_ids = [c["comment_id"] for c in comments]
        if comment_ids:
            reply_query = (
                select(
                    comment_replies_table.c.reply_id,
                    comment_replies_table.c.comment_id,
                    comment_replies_table.c.reply_description,
                    comment_replies_table.c.replied_by,
                    comment_replies_table.c.replied_date,
                    users.c.user_name.label("replied_by_name"),
                )
                .join(users, users.c.user_id == comment_replies_table.c.replied_by, isouter=True)
                .join(project_comments_table, project_comments_table.c.comment_id == comment_replies_table.c.comment_id)
                .where(comment_replies_table.c.comment_id.in_(comment_ids))
            )

            if project_id is not None and project_id != 0:
                reply_query = reply_query.where(project_comments_table.c.project_id == project_id)

            reply_query = reply_query.order_by(comment_replies_table.c.replied_date.asc())
            all_replies = await database.fetch_all(reply_query)
        else:
            all_replies = []

        # Step 3: Group replies by comment_id
        replies_map = defaultdict(list)
        for r in all_replies:
            replies_map[r["comment_id"]].append(dict(r))

        # Step 4: Build nested project -> phases -> comments -> replies
        projects_data = {}
        for comment in comments:
            c = dict(comment)
            c["replies_count"] = len(replies_map.get(c["comment_id"], []))  # Add replies_count to each comment
            c["replies"] = replies_map.get(c["comment_id"], [])

            project_key = c["project_id"]
            phase_key = c["project_phase_id"]

            if project_key not in projects_data:
                projects_data[project_key] = {"project_id": project_key, "project_name": c["project_name"], "phases": {}}

            if phase_key not in projects_data[project_key]["phases"]:
                projects_data[project_key]["phases"][phase_key] = {
                    "project_phase_id": phase_key,
                    "sdlc_phase_id": c["sdlc_phase_id"],
                    "phase_name": c["phase_name"],
                    "comment_count": 0,  # Initialize comment_count
                    "comments": []
                }

            # Remove redundant fields
            c.pop("phase_name", None)
            c.pop("project_id", None)

            projects_data[project_key]["phases"][phase_key]["comments"].append(c)
            projects_data[project_key]["phases"][phase_key]["comment_count"] += 1  # Increment comment_count

        # Convert phases dict to list
        final_result = []
        for project in projects_data.values():
            project["phases"] = list(project["phases"].values())
            final_result.append(project)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Comments and replies fetched successfully",
                "data": final_result,
            }),
        )

    except Exception as e:
        logger.exception(f"Error fetching comments: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )



async def update_project_comment(data: CommentUpdateRequest):
    try:
        logger.info(f"Updating comment_id={data.comment_id} with data={data.dict()}")

        # Step 1: Check if comment exists
        check_query = select(project_comments_table).where(project_comments_table.c.comment_id == data.comment_id)
        existing_comment = await database.fetch_one(check_query)

        if not existing_comment:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Comment not found",
                    "data": None,
                },
            )

        # Step 2: Update the comment
        now = datetime.utcnow()
        update_query = (
            update(project_comments_table)
            .where(project_comments_table.c.comment_id == data.comment_id)
            .values(
                description=data.description,
                updated_by=data.updated_by,
                update_date=now
            )
        )
        await database.execute(update_query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Comment updated successfully",
                "data": {
                    "comment_id": data.comment_id,
                    "description": data.description,
                    "updated_by": data.updated_by,
                    "update_date": now
                }
            }),
        )

    except Exception as e:
        logger.exception(f"Error updating comment: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )


async def update_comment_reply(data: ReplyUpdateRequest):
    try:
        logger.info(f"Updating reply_id={data.reply_id} with data={data.dict()}")

        # Step 1: Check if reply exists
        check_query = select(comment_replies_table).where(comment_replies_table.c.reply_id == data.reply_id)
        existing_reply = await database.fetch_one(check_query)

        if not existing_reply:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Reply not found",
                    "data": None,
                },
            )

        # Step 2: Update the reply
        now = datetime.utcnow()
        update_query = (
            update(comment_replies_table)
            .where(comment_replies_table.c.reply_id == data.reply_id)
            .values(
                reply_description=data.reply_description,
                updated_by=data.updated_by,
                update_date=now
            )
        )
        await database.execute(update_query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Reply updated successfully",
                "data": {
                    "reply_id": data.reply_id,
                    "reply_description": data.reply_description,
                    "updated_by": data.updated_by,
                    "update_date": now
                }
            }),
        )

    except Exception as e:
        logger.exception(f"Error updating reply: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )
        
        
    
# revert back to previous task.
# async def revert_back_to_previous_task(data: RevertBackRequest):
#     try:
#         logger.info(f"Reverting task_id={data.task_id}")

#         # Check if task exists
#         task_query = select(project_tasks_list_table.c.project_task_id).where(
#             project_tasks_list_table.c.project_task_id == data.task_id
#         )
#         task = await database.fetch_one(task_query)
#         if not task:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={"message": f"Task {data.task_id} not found", "data": None},
#             )
            
        
#         unresolved_comments_query = (
#             select(func.count(project_comments_table.c.comment_id))
#             .where(
#                 project_comments_table.c.project_task_id == data.task_id,
#                 project_comments_table.c.is_resolved == False,
#             )
#         )
#         unresolved_count = await database.fetch_val(unresolved_comments_query)

#         if unresolved_count == 0:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "message": "Mention The reason in comments to revert back the task.",
#                     "reason": "Check the comments for this task phase",
#                     "unresolved_comments": unresolved_count,
#                     "data": None,
#                 },
#             )

#         # Update current task status
#         update_current_task = (
#             update(project_tasks_list_table)
#             .where(project_tasks_list_table.c.project_task_id == data.task_id)
#             .values(task_status_id=4, task_users_submitted=0)
#         )
#         await database.execute(update_current_task)

#         # Reset submitted flag for current task users
#         reset_current_task_users = (
#             update(project_task_users_table)
#             .where(project_task_users_table.c.project_task_id == data.task_id)
#             .values(submitted=False)
#         )
#         await database.execute(reset_current_task_users)

        # # Handle previous task (optional, depending on your logic)
        # previous_task_query = (
        #     select(project_tasks_list_table.c.project_task_id)
        #     .where(project_tasks_list_table.c.project_task_id == data.task_id - 1)
        # )
        # previous_task = await database.fetch_one(previous_task_query)

        # if previous_task:
        #     update_previous_task = (
        #         update(project_tasks_list_table)
        #         .where(project_tasks_list_table.c.project_task_id == previous_task.project_task_id)
        #         .values(task_status_id=5, task_users_submitted=0)
        #     )
        #     await database.execute(update_previous_task)

        #     reset_prev_task_users = (
        #         update(project_task_users_table)
        #         .where(project_task_users_table.c.project_task_id == previous_task.project_task_id)
        #         .values(submitted=False)
        #     )
        #     await database.execute(reset_prev_task_users)

        # logger.info(f"Task {data.task_id} reverted successfully")

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={"message": "Task reverted successfully", "data": {"task_id": data.task_id}},
#         )

#     except Exception as e:
#         logger.error(f"Error in revert_task: {e}", exc_info=True)
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"message": "Internal server error", "details": str(e), "data": None},
#         )


# async def revert_back_to_previous_task(db, data):
#     """
#     Revert a task back to previous task:
#     - validate task exists
#     - check unresolved comments (if your policy requires it)
#     - prepare the base content (copy from phase-latest if exists, else empty)
#     - handle legacy docs for this task (doc_version IS NULL) -> convert to version 1 (and mark not latest)
#     - compute new_version = max(doc_version for this task) + 1
#     - mark all docs in phase is_latest = False
#     - insert new doc row with new_version and is_latest = True
#     - update task statuses and users as required (existing logic preserved)
#     """
#     try:
#         logger.info(f"Reverting task_id={data.task_id}")

#         # Validate task existence + get phase
#         task_q = select(project_tasks_list_table.c.project_task_id, project_tasks_list_table.c.project_phase_id).where(
#             project_tasks_list_table.c.project_task_id == data.task_id
#         )
#         task_row = await db.fetch_one(task_q)
#         if not task_row:
#             return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": f"Task {data.task_id} not found", "data": None})

#         project_phase_id = task_row["project_phase_id"]

#         # optional: unresolved comments check (as in your earlier logic)
#         unresolved_q = (
#             select(func.count(project_comments_table.c.comment_id).label("cnt"))
#             .where(project_comments_table.c.project_task_id == data.task_id)
#             .where(project_comments_table.c.is_resolved == False)
#         )
#         unresolved_count_row = await db.fetch_one(unresolved_q)
#         unresolved_cnt = int(unresolved_count_row["cnt"]) if unresolved_count_row and unresolved_count_row["cnt"] is not None else 0

#         if unresolved_cnt == 0:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={"message": "Mention the reason in comments to revert back the task.", "reason": "Check comments for this task", "unresolved_comments": unresolved_cnt, "data": None}
#             )

#         # Update current task status (your existing logic)
#         update_current = (
#             update(project_tasks_list_table)
#             .where(project_tasks_list_table.c.project_task_id == data.task_id)
#             .values(task_status_id=4, task_users_submitted=0)
#         )
#         await db.execute(update_current)

#         # Reset submitted flags for current task users
#         reset_current_users = (
#             update(project_task_users_table)
#             .where(project_task_users_table.c.project_task_id == data.task_id)
#             .values(submitted=False)
#         )
#         await db.execute(reset_current_users)

#         # Optionally update previous task (task_id - 1)
#         prev_task_q = select(project_tasks_list_table.c.project_task_id).where(
#             project_tasks_list_table.c.project_task_id == data.task_id - 1
#         )
#         prev_task = await db.fetch_one(prev_task_q)
#         if prev_task:
#             update_prev = (
#                 update(project_tasks_list_table)
#                 .where(project_tasks_list_table.c.project_task_id == prev_task.project_task_id)
#                 .values(task_status_id=5, task_users_submitted=0)
#             )
#             await db.execute(update_prev)

#             reset_prev_users = (
#                 update(project_task_users_table)
#                 .where(project_task_users_table.c.project_task_id == prev_task.project_task_id)
#                 .values(submitted=False)
#             )
#             await db.execute(reset_prev_users)

#         # -------------------------
#         # Prepare document versioning for revert
#         # -------------------------
#         # Base content = current phase latest document (if any)
#         latest_phase_q = (
#             select(task_docs_table)
#             .where(task_docs_table.c.project_phase_id == project_phase_id)
#             .where(task_docs_table.c.is_latest == True)
#             .order_by(task_docs_table.c.task_doc_id.desc())
#             .limit(1)
#         )
#         latest_phase_doc = await db.fetch_one(latest_phase_q)
#         base_content = latest_phase_doc["document_json"] if latest_phase_doc else ""

#         # Convert legacy doc for this task (doc_version IS NULL) to version 1 (and mark not latest)
#         legacy_task_doc_q = (
#             select(task_docs_table)
#             .where(task_docs_table.c.project_task_id == data.task_id)
#             .where(task_docs_table.c.doc_version.is_(None))
#             .order_by(task_docs_table.c.task_doc_id.desc())
#             .limit(1)
#         )
#         legacy_task_doc = await db.fetch_one(legacy_task_doc_q)
#         if legacy_task_doc:
#             upd_legacy = (
#                 update(task_docs_table)
#                 .where(task_docs_table.c.task_doc_id == legacy_task_doc["task_doc_id"])
#                 .values(doc_version=1, is_latest=False, updated_by=getattr(data, "user_id", None) or getattr(data, "updated_by", None), updated_date=datetime.utcnow())
#             )
#             await db.execute(upd_legacy)
#             logger.info(f"Converted legacy doc {legacy_task_doc['task_doc_id']} to version 1 for task {data.task_id}")

#         # compute new_version = max(doc_version for this task) + 1
#         max_ver_q = (
#             select(func.coalesce(func.max(task_docs_table.c.doc_version), 0).label("maxv"))
#             .where(task_docs_table.c.project_task_id == data.task_id)
#         )
#         max_ver_row = await db.fetch_one(max_ver_q)
#         max_ver = int(max_ver_row["maxv"]) if max_ver_row and max_ver_row["maxv"] is not None else 0
#         new_version = max_ver + 1

#         # reset all docs in this phase to not latest
#         reset_phase_q = (
#             update(task_docs_table)
#             .where(task_docs_table.c.project_phase_id == project_phase_id)
#             .values(is_latest=False)
#         )
#         await db.execute(reset_phase_q)

#         # fetch project_id for insert (optional)
#         proj_q = select(project_phases_list_table.c.project_id).where(project_phases_list_table.c.project_phase_id == project_phase_id)
#         proj_row = await db.fetch_one(proj_q)
#         project_id = proj_row["project_id"] if proj_row else None

#         # insert new version copy for this revert action
#         new_insert = (
#             insert(task_docs_table)
#             .values(
#                 project_task_id=data.task_id,
#                 project_id=project_id,
#                 project_phase_id=project_phase_id,
#                 document_json=base_content,
#                 is_latest=True,
#                 doc_version=new_version,
#                 created_by=getattr(data, "user_id", None) or getattr(data, "updated_by", None),
#                 created_date=datetime.utcnow()
#             )
#         )
#         await db.execute(new_insert)

#         logger.info(f"Revert created new version {new_version} for task {data.task_id} in phase {project_phase_id}")

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={"message": "Task reverted successfully", "data": {"task_id": data.task_id, "new_doc_version": new_version}},
#         )

#     except Exception as e:
#         logger.error(f"Error in revert_back_to_previous_task: {e}", exc_info=True)
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"message": "Internal server error", "details": str(e), "data": None},
#         )


async def revert_back_to_previous_task(db, data: RevertBackRequest):
    try:
        logger.info(f"Reverting task_id={data.task_id}")

        # ---------------------------------------------
        # 1. Fetch task & phase
        # ---------------------------------------------
        task_row = await db.fetch_one(
            select(
                project_tasks_list_table.c.project_task_id,
                project_tasks_list_table.c.project_phase_id
            ).where(project_tasks_list_table.c.project_task_id == data.task_id)
        )

        if not task_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"Task {data.task_id} not found", "data": None},
            )

        project_phase_id = task_row["project_phase_id"]

        # ---------------------------------------------
        # 2. Validate unresolved comments
        # ---------------------------------------------
        unresolved_count = await db.fetch_val(
            select(func.count(project_comments_table.c.comment_id)).where(
                project_comments_table.c.project_task_id == data.task_id,
                project_comments_table.c.is_resolved == False
            )
        )

        if unresolved_count == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Mention a comment before reverting the task.",
                    "data": None,
                },
            )

        # ---------------------------------------------
        # 3. Update current task status
        # ---------------------------------------------
        await db.execute(
            update(project_tasks_list_table)
            .where(project_tasks_list_table.c.project_task_id == data.task_id)
            .values(task_status_id=4, task_users_submitted=0)
        )

        await db.execute(
            update(project_task_users_table)
            .where(project_task_users_table.c.project_task_id == data.task_id)
            .values(submitted=False)
        )

        # ---------------------------------------------
        # 4. VERSIONING LOGIC (simple + correct)
        # ---------------------------------------------

        # (A) Find max version FOR THIS TASK
        max_version = await db.fetch_val(
            select(func.coalesce(func.max(task_docs_table.c.doc_version), 0)).where(
                task_docs_table.c.project_task_id == data.task_id
            )
        )
        new_version = max_version + 1

        # (B) Only one latest per phase → Set all phase docs to not latest
        await db.execute(
            update(task_docs_table)
            .where(task_docs_table.c.project_phase_id == project_phase_id)
            .values(is_latest=False)
        )

        # (C) Fetch project_id for insert
        project_id = await db.fetch_val(
            select(project_phases_list_table.c.project_id).where(
                project_phases_list_table.c.project_phase_id == project_phase_id
            )
        )

        # (D) Insert new version for this task
        await db.execute(
            insert(task_docs_table).values(
                project_task_id=data.task_id,
                project_phase_id=project_phase_id,
                project_id=project_id,
                document_json=data.document_json,   # from request
                doc_version=new_version,
                is_latest=True,
                created_by=None,
                submitted_by=None,
                created_date=datetime.utcnow(),
            )
        )

        logger.info(
            f"[REVERT] Created new doc version {new_version} for task {data.task_id} (phase {project_phase_id})"
        )
        
        # ------------------------------------------------------------
        # Activate Previous Task (task_id - 1) when current task reverts
        # ------------------------------------------------------------
        prev_task_query = select(project_tasks_list_table.c.project_task_id).where(
            project_tasks_list_table.c.project_task_id == data.task_id - 1
        )

        prev_task = await database.fetch_one(prev_task_query)

        if prev_task:
            prev_task_id = prev_task["project_task_id"]

            # Activate previous task
            await database.execute(
                update(project_tasks_list_table)
                .where(project_tasks_list_table.c.project_task_id == prev_task_id)
                .values(
                    task_status_id=5,             # or 1 (if "Active" = 1)
                    task_users_submitted=0,
                    updated_date=datetime.utcnow()
                )
            )

            # Reset submitted users for previous task
            await database.execute(
                update(project_task_users_table)
                .where(project_task_users_table.c.project_task_id == prev_task_id)
                .values(submitted=False)
            )

            logger.info(f"Previous task {prev_task_id} reactivated due to revert on {data.task_id}")
        else:
            logger.info(f"No previous task found for revert of {data.task_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Task reverted successfully",
                "data": {
                    "task_id": data.task_id,
                    "new_doc_version": float(new_version)
                },
            },
        )

    except Exception as e:
        logger.error(f"Error in revert_back_to_previous_task: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Internal server error",
                "details": str(e),
                "data": None,
            },
        )

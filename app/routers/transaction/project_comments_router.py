from fastapi import APIRouter
from app.db.database import database
from app.schemas.transaction.project_comments_schema import ProjectCommentCreateRequest, ProjectCommentResponse, \
    CommentReplyResponse, CommentReplyCreateRequest, CommentResolveResponse, CommentUpdateRequest, ReplyUpdateRequest, RevertBackRequest
from app.services.transaction.project_comments_service import create_project_comment, \
    create_comment_reply, resolve_comment_service, get_comments_by_task, get_user_comments_service, revert_back_to_previous_task, \
    update_project_comment, update_comment_reply

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])


@router.post("/CreateProjectComment", response_model=ProjectCommentResponse)
async def create_project_comment_api(data: ProjectCommentCreateRequest):
    return await create_project_comment(data)

@router.get("/GetCommentsByTask/{task_id}")
async def get_comments_by_task_api(task_id: int):
    return await get_comments_by_task(task_id)


@router.post("/AddCommentReply", response_model=CommentReplyResponse)
async def add_comment_reply_api(reply: CommentReplyCreateRequest):
    # here we pass `database` instead of `db` from Depends
    async with database.transaction():
        return await create_comment_reply(database, reply)


@router.put("/ResolveComment/{comment_id}/{user_id}", response_model=CommentResolveResponse)
async def resolve_comment(comment_id: int, user_id: int):
    return await resolve_comment_service(comment_id, user_id)


@router.get("/comments/{user_id}")
async def fetch_user_comments(user_id: int, project_id: int):
    return await get_user_comments_service(user_id=user_id, project_id=project_id)


@router.put("/comment/edit")
async def edit_comment(request: CommentUpdateRequest):
    return await update_project_comment(data=request)

@router.put("/reply/edit")
async def edit_reply(request: ReplyUpdateRequest):
    return await update_comment_reply(data=request)

@router.post("/task/revert")
async def revert_prev_task(request: RevertBackRequest):
    return await revert_back_to_previous_task(database,data=request)

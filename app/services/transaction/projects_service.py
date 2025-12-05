from app.db.database import database

async def fetch_project_users(project_id: int):
    query = """
        SELECT
            u.user_id,
            u.user_name,
            u.email,
            r.role_id,
            r.role_name
        FROM ai_verify_transaction.projects_user_mapping pum
        JOIN ai_verify_transaction.users u
              ON pum.user_id = u.user_id
        LEFT JOIN ai_verify_transaction.user_role_mapping urm
              ON u.user_id = urm.user_id
        LEFT JOIN ai_verify_master.user_roles r
              ON r.role_id = urm.role_id
        WHERE pum.project_id = :project_id
          AND pum.is_active = TRUE
          AND u.is_active = TRUE
          AND (urm.is_active = TRUE OR urm.is_active IS NULL)
        ORDER BY u.user_id;
    """

    rows = await database.fetch_all(query=query, values={"project_id": project_id})
    return [dict(row) for row in rows]

--CREATE OR REPLACE FUNCTION ai_verify_transaction.get_all_projects(p_user_id INT)
--RETURNS JSON AS $$
--DECLARE
--    result JSON;
--BEGIN
--    WITH base_projects AS (
--        SELECT
--            p.project_id,
--            p.project_name,
--            p.project_description,
--            p.start_date,
--            p.end_date,
--            p.created_date,
--            p.status_id,
--            p.risk_assessment_id,
--            s.status_name,
--            r.risk_assessment_name
--        FROM ai_verify_transaction.projects p
--        JOIN ai_verify_master.status s ON p.status_id = s.status_id
--        JOIN ai_verify_master.risk_assessments r ON p.risk_assessment_id = r.risk_assessment_id
--        WHERE p.is_active = TRUE
--          AND (
--                p_user_id = 0 OR
--                p.project_id IN (
--                    SELECT project_id
--                    FROM ai_verify_transaction.projects_user_mapping
--                    WHERE user_id = p_user_id AND is_active = TRUE
--                )
--              )
--    ),
--
--    users_per_project AS (
--        SELECT
--            pum.project_id,
--            json_agg(json_build_object(
--                'user_id', u.user_id,
--                'user_name', u.user_name,
--                'user_image', u.image_url
--            )) AS users
--        FROM ai_verify_transaction.projects_user_mapping pum
--        JOIN ai_verify_transaction.users u ON u.user_id = pum.user_id
--        WHERE pum.project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY pum.project_id
--    ),
--
--    comments_count AS (
--        SELECT project_id, COUNT(*) AS comments_count
--        FROM ai_verify_transaction.project_comments
--        WHERE project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY project_id
--    ),
--
--    incidents_count AS (
--        SELECT project_id, COUNT(*) AS incident_count
--        FROM ai_verify_transaction.incident_reports
--        WHERE project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY project_id
--    ),
--
--   phases_per_project AS (
--    SELECT
--        ppl.project_id,
--        json_agg(
--            json_build_object(
--                'phase_id', sp.phase_id,
--                'phase_code', sp.phase_code
--            )
--            ORDER BY sp.order_id
--        ) AS phases
--    FROM ai_verify_transaction.project_phases_list ppl
--    JOIN ai_verify_master.sdlc_phases sp
--      ON sp.phase_id = ppl.phase_id
--    WHERE ppl.project_id IN (SELECT project_id FROM base_projects)
--    GROUP BY ppl.project_id
--),
--
--    task_completion AS (
--        SELECT
--            ppl.project_id,
--            COUNT(*) AS total,
--            COUNT(*) FILTER (WHERE ptl.task_status_id = 3) AS completed
--        FROM ai_verify_transaction.project_tasks_list ptl
--        JOIN ai_verify_transaction.project_phases_list ppl
--            ON ptl.project_phase_id = ppl.project_phase_id
--        WHERE ppl.project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY ppl.project_id
--    ),
--
--    files_count AS (
--        SELECT project_id, COUNT(*) AS files_count
--        FROM ai_verify_transaction.project_files
--        WHERE project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY project_id
--    ),
--
--    task_docs_count AS (
--        SELECT project_id, COUNT(*) AS task_docs_count
--        FROM ai_verify_docs.task_docs
--        WHERE project_id IN (SELECT project_id FROM base_projects)
--        GROUP BY project_id
--    )
--
--    SELECT json_agg(
--        json_build_object(
--            'project_id', bp.project_id,
--            'project_name', bp.project_name,
--            'project_description', bp.project_description,
--            'start_date', bp.start_date,
--            'end_date', bp.end_date,
--            'created_date', bp.created_date,
--            'status_id', bp.status_id,
--            'risk_assessment_id', bp.risk_assessment_id,
--            'status_name', bp.status_name,
--            'risk_assessment_name', bp.risk_assessment_name,
--            'users', coalesce(u.users, '[]'::json),
--            'phases', coalesce(ph.phases, '[]'::json),
--            'comments_count', coalesce(c.comments_count, 0),
--            'incident_count', coalesce(i.incident_count, 0),
--            'completed_percentage',
--                CASE WHEN tc.total > 0 THEN ROUND(tc.completed * 100.0 / tc.total, 2) ELSE 0 END,
--            'files_count', coalesce(f.files_count, 0) + coalesce(td.task_docs_count, 0)
--        )
--    ) INTO result
--    FROM base_projects bp
--    LEFT JOIN users_per_project u ON bp.project_id = u.project_id
--    LEFT JOIN comments_count c ON bp.project_id = c.project_id
--    LEFT JOIN incidents_count i ON bp.project_id = i.project_id
--    LEFT JOIN phases_per_project ph ON bp.project_id = ph.project_id
--    LEFT JOIN task_completion tc ON bp.project_id = tc.project_id
--    LEFT JOIN files_count f ON bp.project_id = f.project_id
--    LEFT JOIN task_docs_count td ON bp.project_id = td.project_id;
--
--    RETURN COALESCE(result, '[]'::json);
--END;
--$$ LANGUAGE plpgsql;

-------------updated function before project active checking the CR file is_verified condition also
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_all_projects(
	p_user_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    result JSON;
    project_exists BOOLEAN;
BEGIN
    -- -- Step 0: Check if any project starts today and is not started yet
    -- SELECT EXISTS (
    --     SELECT 1
    --     FROM ai_verify_transaction.projects
    --     WHERE start_date <= CURRENT_DATE
    --       AND status_id = 8
    --       AND is_active = TRUE
    -- ) INTO project_exists;

    -- -- Step 1: Update statuses only if such projects exist
    -- IF project_exists THEN
    --     -- Step 1.1: Identify projects to update
    --     CREATE TEMP TABLE tmp_projects_to_update AS
    --     SELECT project_id
    --     FROM ai_verify_transaction.projects
    --     WHERE start_date = CURRENT_DATE
    --       AND status_id = 8
    --       AND is_active = TRUE;
	-- Step 0: Check if any project starts today and is not started yet
    SELECT EXISTS (
    SELECT 1
    FROM ai_verify_transaction.projects p
    JOIN (
        -- Get only latest change request per project
        SELECT cr1.project_id
        FROM ai_verify_transaction.change_request cr1
        JOIN (
            SELECT project_id, MAX(change_request_id) AS latest_id
            FROM ai_verify_transaction.change_request
            GROUP BY project_id
        ) cr2 ON cr1.project_id = cr2.project_id AND cr1.change_request_id = cr2.latest_id
        WHERE cr1.is_verified = TRUE
    ) cr ON p.project_id = cr.project_id
    WHERE p.start_date <= CURRENT_DATE
      AND p.status_id = 8
      AND p.is_active = TRUE
) INTO project_exists;


    -- Step 1: Update statuses only if such projects exist
    IF project_exists THEN
    CREATE TEMP TABLE tmp_projects_to_update AS
    SELECT p.project_id
    FROM ai_verify_transaction.projects p
    JOIN (
        -- Get latest change request for each project, only if it's verified
        SELECT cr1.project_id
        FROM ai_verify_transaction.change_request cr1
        JOIN (
            SELECT project_id, MAX(change_request_id) AS latest_id
            FROM ai_verify_transaction.change_request
            GROUP BY project_id
        ) cr2 ON cr1.project_id = cr2.project_id AND cr1.change_request_id = cr2.latest_id
        WHERE cr1.is_verified = TRUE
    ) cr ON p.project_id = cr.project_id
    WHERE p.start_date <= CURRENT_DATE
      AND p.status_id = 8
      AND p.is_active = TRUE;

        -- Step 1.2: Identify first phase for each project
        CREATE TEMP TABLE tmp_first_phases AS
        SELECT DISTINCT ON (ppl.project_id)
            ppl.project_id,
            ppl.project_phase_id
        FROM ai_verify_transaction.project_phases_list ppl
        JOIN tmp_projects_to_update ptu ON ppl.project_id = ptu.project_id
        ORDER BY ppl.project_id, ppl.phase_order_id;

        -- Step 1.3: Identify first task in each first phase
        CREATE TEMP TABLE tmp_first_tasks AS
        SELECT DISTINCT ON (ptl.project_phase_id)
            ptl.project_phase_id,
            ptl.project_task_id
        FROM ai_verify_transaction.project_tasks_list ptl
        JOIN tmp_first_phases fp ON ptl.project_phase_id = fp.project_phase_id
        ORDER BY ptl.project_phase_id, ptl.project_task_id;

        -- Step 1.4: Update project statuses
        UPDATE ai_verify_transaction.projects
        SET status_id = 1
        WHERE project_id IN (SELECT project_id FROM tmp_projects_to_update);

        -- Step 1.5: Update first phase statuses
        UPDATE ai_verify_transaction.project_phases_list
        SET status_id = 1
        WHERE project_phase_id IN (SELECT project_phase_id FROM tmp_first_phases);

        -- Step 1.6: Update first task statuses
        UPDATE ai_verify_transaction.project_tasks_list
        SET task_status_id = 1
        WHERE project_task_id IN (SELECT project_task_id FROM tmp_first_tasks);

        -- Cleanup temporary tables
        DROP TABLE IF EXISTS tmp_projects_to_update;
        DROP TABLE IF EXISTS tmp_first_phases;
        DROP TABLE IF EXISTS tmp_first_tasks;

        RAISE NOTICE 'Updated project, phase, and task statuses for today''s projects.';
    END IF;

    -- Step 2: Fetch all projects and return as JSON
    WITH base_projects AS (
        SELECT
            p.project_id,
            p.project_name,
            p.project_description,
            p.start_date,
            p.end_date,
            p.created_date,
            p.status_id,
            p.risk_assessment_id,
            s.status_name,
            r.risk_assessment_name
        FROM ai_verify_transaction.projects p
        JOIN ai_verify_master.status s ON p.status_id = s.status_id
        JOIN ai_verify_master.risk_assessments r ON p.risk_assessment_id = r.risk_assessment_id
        WHERE p.is_active = TRUE
          AND (
                p_user_id = 0 OR
                p.project_id IN (
                    SELECT project_id
                    FROM ai_verify_transaction.projects_user_mapping
                    WHERE user_id = p_user_id AND is_active = TRUE
                )
              )
    ),
    users_per_project AS (
        SELECT
            pum.project_id,
            json_agg(json_build_object(
                'user_id', u.user_id,
                'user_name', u.user_name,
                'user_image', u.image_url
            )) AS users
        FROM ai_verify_transaction.projects_user_mapping pum
        JOIN ai_verify_transaction.users u ON u.user_id = pum.user_id
        WHERE pum.project_id IN (SELECT project_id FROM base_projects)
        GROUP BY pum.project_id
    ),
    comments_count AS (
        SELECT project_id, COUNT(*) AS comments_count
        FROM ai_verify_transaction.project_comments
        WHERE project_id IN (SELECT project_id FROM base_projects)
        GROUP BY project_id
    ),
    incidents_count AS (
        SELECT project_id, COUNT(*) AS incident_count
        FROM ai_verify_transaction.incident_reports
        WHERE project_id IN (SELECT project_id FROM base_projects)
        GROUP BY project_id
    ),
    phases_per_project AS (
        SELECT
            ppl.project_id,
            json_agg(
                json_build_object(
                    'phase_id', sp.phase_id,
                    'phase_code', sp.phase_code
                )
                ORDER BY sp.order_id
            ) AS phases
        FROM ai_verify_transaction.project_phases_list ppl
        JOIN ai_verify_master.sdlc_phases sp
          ON sp.phase_id = ppl.phase_id
        WHERE ppl.project_id IN (SELECT project_id FROM base_projects)
        GROUP BY ppl.project_id
    ),
    task_completion AS (
        SELECT
            ppl.project_id,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE ptl.task_status_id = 3) AS completed
        FROM ai_verify_transaction.project_tasks_list ptl
        JOIN ai_verify_transaction.project_phases_list ppl
            ON ptl.project_phase_id = ppl.project_phase_id
        WHERE ppl.project_id IN (SELECT project_id FROM base_projects)
        GROUP BY ppl.project_id
    ),
    files_count AS (
        SELECT project_id, COUNT(*) AS files_count
        FROM ai_verify_transaction.project_files
        WHERE project_id IN (SELECT project_id FROM base_projects)
        GROUP BY project_id
    ),
    task_docs_count AS (
        SELECT project_id, COUNT(*) AS task_docs_count
        FROM ai_verify_docs.task_docs
        WHERE project_id IN (SELECT project_id FROM base_projects)
        GROUP BY project_id
    )
    SELECT json_agg(
        json_build_object(
            'project_id', bp.project_id,
            'project_name', bp.project_name,
            'project_description', bp.project_description,
            'start_date', bp.start_date,
            'end_date', bp.end_date,
            'created_date', bp.created_date,
            'status_id', bp.status_id,
            'risk_assessment_id', bp.risk_assessment_id,
            'status_name', bp.status_name,
            'risk_assessment_name', bp.risk_assessment_name,
            'users', coalesce(u.users, '[]'::json),
            'phases', coalesce(ph.phases, '[]'::json),
            'comments_count', coalesce(c.comments_count, 0),
            'incident_count', coalesce(i.incident_count, 0),
            'completed_percentage',
                CASE WHEN tc.total > 0 THEN ROUND(tc.completed * 100.0 / tc.total, 2) ELSE 0 END,
            'files_count', coalesce(f.files_count, 0) + coalesce(td.task_docs_count, 0)
        )
    ) INTO result
    FROM base_projects bp
    LEFT JOIN users_per_project u ON bp.project_id = u.project_id
    LEFT JOIN comments_count c ON bp.project_id = c.project_id
    LEFT JOIN incidents_count i ON bp.project_id = i.project_id
    LEFT JOIN phases_per_project ph ON bp.project_id = ph.project_id
    LEFT JOIN task_completion tc ON bp.project_id = tc.project_id
    LEFT JOIN files_count f ON bp.project_id = f.project_id
    LEFT JOIN task_docs_count td ON bp.project_id = td.project_id;

    RETURN COALESCE(result, '[]'::json);
END;
$BODY$;







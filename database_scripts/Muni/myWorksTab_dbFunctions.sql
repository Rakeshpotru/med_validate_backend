--get projects function for myWorks tab
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_projects_by_user_for_myworks(
	p_user_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    projects_json JSON;
BEGIN
    WITH user_projects AS (
        SELECT p.project_id, p.project_name, p.start_date, p.end_date
        FROM ai_verify_transaction.projects p
        JOIN ai_verify_transaction.projects_user_mapping m ON p.project_id = m.project_id
        WHERE m.user_id = p_user_id
          AND m.is_active = true
          AND p.is_active = true
    ),
    project_users AS (
        SELECT m.project_id,
               json_agg(json_build_object(
                   'user_id', u.user_id,
                   'user_name', u.user_name,
                   'user_image', u.image_url
               )) as users
        FROM ai_verify_transaction.projects_user_mapping m
        JOIN ai_verify_transaction.users u ON m.user_id = u.user_id
        WHERE m.project_id IN (SELECT project_id FROM user_projects)
          AND m.is_active = true
          AND u.is_active = true
        GROUP BY m.project_id
    ),
    project_task_counts AS (
        SELECT ph.project_id,
               count(t.project_task_id) as total_tasks,
               count(CASE WHEN t.task_status_id = 3 THEN t.project_task_id END) as completed_tasks
        FROM ai_verify_transaction.project_phases_list ph
        LEFT JOIN ai_verify_transaction.project_tasks_list t ON ph.project_phase_id = t.project_phase_id
        WHERE ph.project_id IN (SELECT project_id FROM user_projects)
        GROUP BY ph.project_id
    )
    SELECT COALESCE(json_agg(json_build_object(
        'project_id', up.project_id,
        'project_name', up.project_name,
        'start_date', up.start_date,
        'end_date', up.end_date,
        'left_days', CASE WHEN up.end_date IS NULL THEN NULL
                          ELSE GREATEST(0, (up.end_date::date - CURRENT_DATE)::int) END,
        'completed_percentage', CASE WHEN COALESCE(ptc.total_tasks, 0) = 0
                                    THEN 0
                                    ELSE ROUND((COALESCE(ptc.completed_tasks, 0)::numeric / COALESCE(ptc.total_tasks, 0)) * 100) END,
        'users', COALESCE(pu.users, '[]'::json)
    )), '[]'::json) INTO projects_json
    FROM user_projects up
    LEFT JOIN project_users pu ON up.project_id = pu.project_id
    LEFT JOIN project_task_counts ptc ON up.project_id = ptc.project_id;

    RETURN projects_json;
END;
$BODY$;

ALTER FUNCTION ai_verify_transaction.get_projects_by_user_for_myworks(integer)
    OWNER TO postgres;



--get tasks function for myWorks tab
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_user_tasks_for_myworks4(p_user_id INTEGER, p_project_id INTEGER)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_project_count INTEGER;
    v_phase_count INTEGER;
    v_task_count INTEGER;
    v_data JSON;
BEGIN
    -- Validate user_id
    IF p_user_id IS NULL OR p_user_id <= 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'Invalid user_id provided',
            'data', json_build_array()
        );
    END IF;

    -- Step 1: Check for active projects
    SELECT COUNT(*) INTO v_project_count
    FROM ai_verify_transaction.projects pr
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_project_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No matching projects found',
            'data', json_build_array()
        );
    END IF;

    -- Step 2: Check for phases
    SELECT COUNT(*) INTO v_phase_count
    FROM ai_verify_transaction.project_phases_list ppl
    JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_phase_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No phases found for the selected project(s)',
            'data', json_build_array()
        );
    END IF;

    -- Step 3: Check for tasks
    SELECT COUNT(*) INTO v_task_count
    FROM ai_verify_transaction.project_tasks_list ptl
    JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
    JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE ptu.user_id = p_user_id
      AND ptu.user_is_active = true
      AND pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_task_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No tasks found for the selected project(s) and user',
            'data', json_build_array()
        );
    END IF;

    -- Step 4: Fetch detailed tasks and build nested JSON
    WITH user_tasks AS (
        SELECT
            sp.phase_id,
            sp.phase_name,
            ppl.phase_order_id,
            ppl.project_id,
            pr.project_name,
            ptl.project_task_id,
            ptl.task_id,
            st.task_name,
            st.task_description,
            ptl.task_start_date,
            ptl.task_end_date,
            ptl.task_status_id,
            COALESCE(s.status_name, NULL) AS task_status_name,
            ptl.task_order_id,
            (SELECT COUNT(ir.incident_report_id)
             FROM ai_verify_transaction.incident_reports ir
             WHERE ir.task_id = ptl.project_task_id) AS incident_reports_count,
            (SELECT COUNT(pc.comment_id)
             FROM ai_verify_transaction.project_comments pc
             WHERE pc.project_task_id = ptl.project_task_id) AS task_comments_count,
            (SELECT COUNT(td.task_doc_id)
             FROM ai_verify_docs.task_docs td
             WHERE td.project_task_id = ptl.project_task_id) AS task_docs_count,
            CASE
                WHEN ptl.task_end_date IS NOT NULL THEN
                    GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (ptl.task_end_date - CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) / 86400))
                ELSE NULL
            END AS left_days,
            (SELECT json_agg(json_build_object(
                'user_id', u.user_id,
                'user_name', u.user_name,
                'user_image', COALESCE(u.image_url, NULL)
            ))
             FROM ai_verify_transaction.users u
             JOIN ai_verify_transaction.project_task_users ptu2 ON u.user_id = ptu2.user_id
             WHERE ptu2.project_task_id = ptl.project_task_id
               AND ptu2.user_is_active = true) AS users
        FROM ai_verify_transaction.project_tasks_list ptl
        JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
        JOIN ai_verify_master.sdlc_tasks st ON ptl.task_id = st.task_id
        JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
        JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
        JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
        JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
        LEFT JOIN ai_verify_master.status s ON ptl.task_status_id = s.status_id
        WHERE ptu.user_id = p_user_id
          AND ptu.user_is_active = true
          AND pum.user_id = p_user_id
          AND pum.is_active = true
          AND pr.is_active = true
          AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id)
    ),
    phase_tasks AS (
        SELECT
            phase_id,
            phase_name,
            phase_order_id,
            json_agg(json_build_object(
                'task_id', task_id,
                'project_task_id', project_task_id,
                'task_name', task_name,
                'task_description', task_description,
                'project_id', project_id,
                'project_name', COALESCE(project_name, ' '),
                'task_start_date', to_json(task_start_date),
                'task_end_date', to_json(task_end_date),
                'left_days', left_days,
                'task_status_id', task_status_id,
                'task_status_name', task_status_name,
                'task_order_id', task_order_id,
                'incident_reports_count', incident_reports_count,
                'task_comments_count', task_comments_count,
                'task_docs_count', task_docs_count,
                'users', COALESCE(users, json_build_array())
            ) ORDER BY task_order_id) AS tasks
        FROM user_tasks
        GROUP BY phase_id, phase_name, phase_order_id
    )
    SELECT json_agg(json_build_object(
        'phase_id', phase_id,
        'phase_name', phase_name,
        'tasks', tasks
    ) ORDER BY phase_order_id) INTO v_data
    FROM phase_tasks;

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Tasks fetched successfully',
        'data', v_data
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status_code', 500,
            'message', 'Internal server error: ' || SQLERRM,
            'data', json_build_array()
        );
END;
$$;
--**************************************************************************************************************
-----------------------tasks 88 is existing function duplicate phases--------------------------------------
-----------------------tasks 99 is updated function without duplicate phases-------------------------------
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_user_tasks_for_myworks88(
	p_user_id integer,
	p_project_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_project_count INTEGER;
    v_phase_count INTEGER;
    v_task_count INTEGER;
    v_data JSON;
BEGIN
    -- Validate user_id
    IF p_user_id IS NULL OR p_user_id <= 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'Invalid user_id provided',
            'data', json_build_array()
        );
    END IF;

    -- Step 1: Check for active projects
    SELECT COUNT(*) INTO v_project_count
    FROM ai_verify_transaction.projects pr
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_project_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No matching projects found',
            'data', json_build_array()
        );
    END IF;

    -- Step 2: Check for phases
    SELECT COUNT(*) INTO v_phase_count
    FROM ai_verify_transaction.project_phases_list ppl
    JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_phase_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No phases found for the selected project(s)',
            'data', json_build_array()
        );
    END IF;

    -- Step 3: Check for tasks
    SELECT COUNT(*) INTO v_task_count
    FROM ai_verify_transaction.project_tasks_list ptl
    JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
    JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE ptu.user_id = p_user_id
      AND ptu.user_is_active = true
      AND pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_task_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No tasks found for the selected project(s) and user',
            'data', json_build_array()
        );
    END IF;

    -- Step 4: Fetch detailed tasks and build nested JSON
    WITH user_tasks AS (
        SELECT
            sp.phase_id,
            sp.phase_name,
            ppl.phase_order_id,
            ppl.project_id,
            pr.project_name,
            ptl.project_task_id,
            ptl.task_id,
            st.task_name,
            st.task_description,
            ptl.task_start_date,
            ptl.task_end_date,
            ptl.task_status_id,
            COALESCE(s.status_name, NULL) AS task_status_name,
            ptl.task_order_id,
            (SELECT COUNT(ir.incident_report_id)
             FROM ai_verify_transaction.incident_reports ir
             WHERE ir.task_id = ptl.project_task_id) AS incident_reports_count,
            (SELECT COUNT(pc.comment_id)
             FROM ai_verify_transaction.project_comments pc
             WHERE pc.project_task_id = ptl.project_task_id) AS task_comments_count,
            (SELECT COUNT(td.task_doc_id)
             FROM ai_verify_docs.task_docs td
             WHERE td.project_task_id = ptl.project_task_id) AS task_docs_count,
            CASE
                WHEN ptl.task_end_date IS NOT NULL THEN
                    GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (ptl.task_end_date - CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) / 86400))
                ELSE NULL
            END AS left_days,
            (SELECT json_agg(json_build_object(
                'user_id', u.user_id,
                'user_name', u.user_name,
                'user_image', COALESCE(u.image_url, NULL)
            ))
             FROM ai_verify_transaction.users u
             JOIN ai_verify_transaction.project_task_users ptu2 ON u.user_id = ptu2.user_id
             WHERE ptu2.project_task_id = ptl.project_task_id
               AND ptu2.user_is_active = true) AS users
        FROM ai_verify_transaction.project_tasks_list ptl
        JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
        JOIN ai_verify_master.sdlc_tasks st ON ptl.task_id = st.task_id
        JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
        JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
        JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
        JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
        LEFT JOIN ai_verify_master.status s ON ptl.task_status_id = s.status_id
        WHERE ptu.user_id = p_user_id
          AND ptu.user_is_active = true
          AND pum.user_id = p_user_id
          AND pum.is_active = true
          AND pr.is_active = true
          AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id)
    ),
    phase_tasks AS (
        SELECT
            phase_id,
            phase_name,
            phase_order_id,
            json_agg(json_build_object(
                'task_id', task_id,
                'project_task_id', project_task_id,
                'task_name', task_name,
                'task_description', task_description,
                'project_id', project_id,
                'project_name', COALESCE(project_name, ' '),
                'task_start_date', to_json(task_start_date),
                'task_end_date', to_json(task_end_date),
                'left_days', left_days,
                'task_status_id', task_status_id,
                'task_status_name', task_status_name,
				'task_order_id', task_order_id,
                'incident_reports_count', incident_reports_count,
                'task_comments_count', task_comments_count,
                'task_docs_count', task_docs_count,
                'users', COALESCE(users, json_build_array())
            ) ORDER BY task_order_id) AS tasks
        FROM user_tasks
        GROUP BY phase_id, phase_name, phase_order_id
    )
    SELECT json_agg(json_build_object(
        'phase_id', phase_id,
        'phase_name', phase_name,
        'tasks', tasks
    ) ORDER BY phase_order_id) INTO v_data
    FROM phase_tasks;

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Tasks fetched successfully',
        'data', v_data
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status_code', 500,
            'message', 'Internal server error: ' || SQLERRM,
            'data', json_build_array()
        );
END;
$BODY$;

-----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_user_tasks_for_myworks99(
	p_user_id integer,
	p_project_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_project_count INTEGER;
    v_phase_count INTEGER;
    v_task_count INTEGER;
    v_data JSON;
BEGIN
    -- Validate user_id
    IF p_user_id IS NULL OR p_user_id <= 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'Invalid user_id provided',
            'data', json_build_array()
        );
    END IF;

    -- Step 1: Check for active projects
    SELECT COUNT(*) INTO v_project_count
    FROM ai_verify_transaction.projects pr
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_project_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No matching projects found',
            'data', json_build_array()
        );
    END IF;

    -- Step 2: Check for phases
    SELECT COUNT(*) INTO v_phase_count
    FROM ai_verify_transaction.project_phases_list ppl
    JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_phase_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No phases found for the selected project(s)',
            'data', json_build_array()
        );
    END IF;

    -- Step 3: Check for tasks
    SELECT COUNT(*) INTO v_task_count
    FROM ai_verify_transaction.project_tasks_list ptl
    JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
    JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
    JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
    JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
    WHERE ptu.user_id = p_user_id
      AND ptu.user_is_active = true
      AND pum.user_id = p_user_id
      AND pum.is_active = true
      AND pr.is_active = true
      AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id);

    IF v_task_count = 0 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'No tasks found for the selected project(s) and user',
            'data', json_build_array()
        );
    END IF;

    -- Step 4: Fetch detailed tasks and build nested JSON
    WITH user_tasks AS (
        SELECT
            sp.phase_id,
            sp.phase_name,
            ppl.phase_order_id,
            ppl.project_id,
            pr.project_name,
            ptl.project_task_id,
            ptl.task_id,
            st.task_name,
            st.task_description,
            ptl.task_start_date,
            ptl.task_end_date,
            ptl.task_status_id,
            COALESCE(s.status_name, NULL) AS task_status_name,
            ptl.task_order_id,
            (SELECT COUNT(ir.incident_report_id)
             FROM ai_verify_transaction.incident_reports ir
             WHERE ir.task_id = ptl.project_task_id) AS incident_reports_count,
            (SELECT COUNT(pc.comment_id)
             FROM ai_verify_transaction.project_comments pc
             WHERE pc.project_task_id = ptl.project_task_id) AS task_comments_count,
            (SELECT COUNT(td.task_doc_id)
             FROM ai_verify_docs.task_docs td
             WHERE td.project_task_id = ptl.project_task_id) AS task_docs_count,
            CASE
                WHEN ptl.task_end_date IS NOT NULL THEN
                    GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (ptl.task_end_date - CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) / 86400))
                ELSE NULL
            END AS left_days,
            (SELECT json_agg(json_build_object(
                'user_id', u.user_id,
                'user_name', u.user_name,
                'user_image', COALESCE(u.image_url, NULL)
            ))
             FROM ai_verify_transaction.users u
             JOIN ai_verify_transaction.project_task_users ptu2 ON u.user_id = ptu2.user_id
             WHERE ptu2.project_task_id = ptl.project_task_id
               AND ptu2.user_is_active = true) AS users
        FROM ai_verify_transaction.project_tasks_list ptl
        JOIN ai_verify_transaction.project_task_users ptu ON ptl.project_task_id = ptu.project_task_id
        JOIN ai_verify_master.sdlc_tasks st ON ptl.task_id = st.task_id
        JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
        JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
        JOIN ai_verify_transaction.projects pr ON ppl.project_id = pr.project_id
        JOIN ai_verify_transaction.projects_user_mapping pum ON pr.project_id = pum.project_id
        LEFT JOIN ai_verify_master.status s ON ptl.task_status_id = s.status_id
        WHERE ptu.user_id = p_user_id
          AND ptu.user_is_active = true
          AND pum.user_id = p_user_id
          AND pum.is_active = true
          AND pr.is_active = true
          AND (p_project_id IS NULL OR p_project_id = 0 OR pr.project_id = p_project_id)
    ),

    -- ✅ FIX: merge all project tasks for same phase_id (avoid duplicates)
    phase_tasks AS (
        SELECT
            phase_id,
            phase_name,
            MIN(phase_order_id) AS phase_order_id,
            json_agg(
                json_build_object(
                    'task_id', task_id,
                    'project_task_id', project_task_id,
                    'task_name', task_name,
                    'task_description', task_description,
                    'project_id', project_id,
                    'project_name', COALESCE(project_name, ' '),
                    'task_start_date', to_json(task_start_date),
                    'task_end_date', to_json(task_end_date),
                    'left_days', left_days,
                    'task_status_id', task_status_id,
                    'task_status_name', task_status_name,
                    'task_order_id', task_order_id,
                    'incident_reports_count', incident_reports_count,
                    'task_comments_count', task_comments_count,
                    'task_docs_count', task_docs_count,
                    'users', COALESCE(users, json_build_array())
                ) ORDER BY task_order_id
            ) AS tasks
        FROM user_tasks
        GROUP BY phase_id, phase_name
    )

    SELECT json_agg(json_build_object(
        'phase_id', phase_id,
        'phase_name', phase_name,
        'tasks', tasks
    ) ORDER BY phase_order_id)
    INTO v_data
    FROM phase_tasks;

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Tasks fetched successfully',
        'data', v_data
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status_code', 500,
            'message', 'Internal server error: ' || SQLERRM,
            'data', json_build_array()
        );
END;
$BODY$;

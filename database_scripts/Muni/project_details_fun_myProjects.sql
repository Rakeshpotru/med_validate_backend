--get project details by project id db function for my projects tab

CREATE OR REPLACE FUNCTION ai_verify_transaction.get_project_details_v3(
	p_project_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
    SET search_path=ai_verify_transaction, ai_verify_master, ai_verify_docs
AS $BODY$
DECLARE
    project_rec RECORD;
    phase_rec RECORD;
    task_rec RECORD;
    proj_user_rec RECORD;
    phase_user_rec RECORD;
    task_user_rec RECORD;
    file_rec RECORD;
    doc_rec RECORD;
    users_json JSON[];
    phase_users_json JSON[];
    task_users_json JSON[];
    files_json JSON[];
    task_docs_json JSON[];
    tasks_json JSON[];
    phases_json JSON[];
    phase_json JSON;
    task_json JSON;
    completed_percentage INTEGER := 0;
    total_tasks INTEGER := 0;
    completed_tasks INTEGER := 0;
BEGIN
    -- Validation
    IF p_project_id IS NULL OR p_project_id <= 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'Bad Request: Missing or invalid project_id',
            'data', NULL
        );
    END IF;

    -- Fetch Project Details
    SELECT
        p.project_id,
        p.project_name,
        p.project_description,
        p.risk_assessment_id,
        COALESCE(ra.risk_assessment_name, NULL) AS risk_assessment_name,
		p.equipment_id,
        COALESCE(eq.equipment_name, NULL) AS equipment_name,
        p.start_date,
        p.end_date,
        p.status_id AS project_status_id,
        s.status_name AS project_status_name,
        CASE
            WHEN p.end_date IS NOT NULL THEN (p.end_date::date - CURRENT_DATE)::INTEGER
            ELSE NULL
        END AS left_days
    INTO project_rec
    FROM ai_verify_transaction.projects p
    LEFT JOIN ai_verify_master.risk_assessments ra ON p.risk_assessment_id = ra.risk_assessment_id
	LEFT JOIN ai_verify_master.equipment_list eq ON p.equipment_id = eq.equipment_id
    LEFT JOIN ai_verify_master.status s ON p.status_id = s.status_id
    WHERE p.project_id = p_project_id AND p.is_active = TRUE;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Project not found',
            'data', NULL
        );
    END IF;

    -- Fetch Project Users
    users_json := ARRAY[]::JSON[];
    FOR proj_user_rec IN
        SELECT
            u.user_id,
            u.user_name,
            u.image_url
        FROM ai_verify_transaction.users u
        JOIN ai_verify_transaction.projects_user_mapping pum ON pum.user_id = u.user_id
        WHERE pum.project_id = p_project_id
            AND u.is_active = TRUE
            AND pum.is_active = TRUE
    LOOP
        users_json := users_json || to_json(json_build_object(
            'user_id', proj_user_rec.user_id,
            'user_name', proj_user_rec.user_name,
            'image_url', proj_user_rec.image_url
        ));
    END LOOP;

    -- Fetch Project Files
    files_json := ARRAY[]::JSON[];
    FOR file_rec IN
        SELECT
            pf.project_file_id,
            pf.file_name
        FROM ai_verify_transaction.project_files pf
        WHERE pf.project_id = p_project_id
		AND pf.is_active = TRUE
    LOOP
        files_json := files_json || to_json(json_build_object(
            'project_file_id', file_rec.project_file_id,
            'file_name', file_rec.file_name
        ));
    END LOOP;

    -- Compute Total and Completed Tasks Count
    SELECT
        COUNT(ptl.project_task_id) AS total,
        COUNT(CASE WHEN ptl.task_status_id = 3 THEN 1 END) AS completed
    INTO total_tasks, completed_tasks
    FROM ai_verify_transaction.project_tasks_list ptl
    JOIN ai_verify_transaction.project_phases_list ppl ON ptl.project_phase_id = ppl.project_phase_id
    WHERE ppl.project_id = p_project_id;

    completed_percentage := CASE
        WHEN total_tasks > 0 THEN ROUND((completed_tasks::NUMERIC / total_tasks) * 100)
        ELSE 0
    END;

    -- Fetch Phases
    phases_json := ARRAY[]::JSON[];
    FOR phase_rec IN
        SELECT
            ppl.project_phase_id,
            ppl.phase_id,
            COALESCE(sp.phase_name, NULL) AS phase_name,
            ppl.status_id AS phase_status_id,
            COALESCE(st.status_name, NULL) AS phase_status_name
        FROM ai_verify_transaction.project_phases_list ppl
        LEFT JOIN ai_verify_master.sdlc_phases sp ON ppl.phase_id = sp.phase_id
        LEFT JOIN ai_verify_master.status st ON ppl.status_id = st.status_id
        WHERE ppl.project_id = p_project_id
        ORDER BY ppl.phase_order_id
    LOOP
        -- Fetch Phase Users
        phase_users_json := ARRAY[]::JSON[];
        FOR phase_user_rec IN
            SELECT
                u.user_id,
                u.user_name,
                u.image_url
            FROM ai_verify_transaction.users u
            JOIN ai_verify_transaction.project_phase_users ppu ON ppu.user_id = u.user_id
            WHERE ppu.project_phase_id = phase_rec.project_phase_id
                AND u.is_active = TRUE
                AND ppu.user_is_active = TRUE
        LOOP
            phase_users_json := phase_users_json || to_json(json_build_object(
                'user_id', phase_user_rec.user_id,
                'user_name', phase_user_rec.user_name,
                'image_url', phase_user_rec.image_url
            ));
        END LOOP;

        -- Fetch Tasks for Phase
        tasks_json := ARRAY[]::JSON[];
        FOR task_rec IN
            SELECT
                ptl.project_task_id,
                ptl.task_id,
				ptl.task_order_id,
                COALESCE(stask.task_name, NULL) AS task_name,
                ptl.task_status_id,
                COALESCE(sts.status_name, NULL) AS task_status_name
            FROM ai_verify_transaction.project_tasks_list ptl
            LEFT JOIN ai_verify_master.sdlc_tasks stask ON ptl.task_id = stask.task_id
            LEFT JOIN ai_verify_master.status sts ON ptl.task_status_id = sts.status_id
            WHERE ptl.project_phase_id = phase_rec.project_phase_id
            ORDER BY ptl.task_order_id
        LOOP
            -- Fetch Task Users
            task_users_json := ARRAY[]::JSON[];
            FOR task_user_rec IN
                SELECT
                    u.user_id,
                    u.user_name,
                    u.image_url
                FROM ai_verify_transaction.users u
                JOIN ai_verify_transaction.project_task_users ptu ON ptu.user_id = u.user_id
                WHERE ptu.project_task_id = task_rec.project_task_id
                    AND u.is_active = TRUE
                    AND ptu.user_is_active = TRUE
            LOOP
                task_users_json := task_users_json || to_json(json_build_object(
                    'user_id', task_user_rec.user_id,
                    'user_name', task_user_rec.user_name,
                    'image_url', task_user_rec.image_url
                ));
            END LOOP;

            tasks_json := tasks_json || to_json(json_build_object(
                'project_task_id', task_rec.project_task_id,
                'task_id', task_rec.task_id,
				'task_order_id', task_rec.task_order_id,
                'task_name', task_rec.task_name,
                'task_status_id', task_rec.task_status_id,
                'task_status_name', task_rec.task_status_name,
                'task_users', to_json(task_users_json)
            ));
        END LOOP;

        -- Fetch Task Docs for Phase
        task_docs_json := ARRAY[]::JSON[];
        FOR doc_rec IN
            SELECT
                td.task_doc_id,
                td.doc_version,
                COALESCE(stask.task_name, NULL) AS task_name
            FROM ai_verify_docs.task_docs td
            JOIN ai_verify_transaction.project_tasks_list ptl ON td.project_task_id = ptl.project_task_id
            JOIN ai_verify_master.sdlc_tasks stask ON ptl.task_id = stask.task_id
            WHERE td.project_phase_id = phase_rec.project_phase_id
                AND td.doc_version IS NOT NULL
        LOOP
            task_docs_json := task_docs_json || to_json(json_build_object(
                'task_doc_id', doc_rec.task_doc_id,
                'doc_version', phase_rec.phase_name || '_' || doc_rec.task_name || '_v' || doc_rec.doc_version
            ));
        END LOOP;

        -- Build Phase JSON
        phase_json := json_build_object(
            'project_phase_id', phase_rec.project_phase_id,
            'phase_id', phase_rec.phase_id,
            'phase_name', phase_rec.phase_name,
            'phase_status_id', phase_rec.phase_status_id,
            'phase_status_name', phase_rec.phase_status_name,
            'phase_users', to_json(phase_users_json),
            'tasks', to_json(tasks_json),
            'task_docs', to_json(task_docs_json)
        );

        phases_json := phases_json || phase_json;
    END LOOP;

    -- Build Project Data JSON
    RETURN json_build_object(
        'status_code', 200,
        'message', 'Project details fetched successfully',
        'data', json_build_object(
            'project_id', project_rec.project_id,
            'project_name', project_rec.project_name,
            'project_description', project_rec.project_description,
            'risk_assessment_id', project_rec.risk_assessment_id,
            'risk_assessment_name', project_rec.risk_assessment_name,
			'equipment_id', project_rec.equipment_id,
            'equipment_name', project_rec.equipment_name,
            'start_date', project_rec.start_date,
            'end_date', project_rec.end_date,
            'left_days', project_rec.left_days,
            'project_status_id', project_rec.project_status_id,
            'project_status_name', project_rec.project_status_name,
            'completed_percentage', completed_percentage,
            'users', to_json(users_json),
            'phases', to_json(phases_json),
            'project_files', to_json(files_json)
        )
    );

EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'status_code', 500,
        'message', 'Internal server error',
        'data', NULL
    );
END;
$BODY$;



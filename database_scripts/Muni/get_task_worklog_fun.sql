--get project task work log details by project task id database function
CREATE OR REPLACE FUNCTION ai_verify_transaction.get_task_work_log_details_by_project_task_id(
	p_project_task_id integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    project_task_record RECORD;
    task_name TEXT;
    status_name TEXT;
    project_name TEXT;
    phase_name TEXT;
    users_json JSON;
    work_logs_json JSON;
    phase_data RECORD;
    response_data JSON;
BEGIN
    -- 1️⃣ Validate project_task_id
    SELECT * INTO project_task_record
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_task_id = p_project_task_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Project task not found',
            'data', json_build_array()
        );
    END IF;

    -- 2️⃣ Task info
    SELECT st.task_name INTO task_name
    FROM ai_verify_master.sdlc_tasks st
    WHERE st.task_id = project_task_record.task_id;

    -- 3️⃣ Status info
    SELECT s.status_name INTO status_name
    FROM ai_verify_master.status s
    WHERE s.status_id = project_task_record.task_status_id;

    -- 4️⃣ Phase and project info
    SELECT * INTO phase_data
    FROM ai_verify_transaction.project_phases_list ppl
    WHERE ppl.project_phase_id = project_task_record.project_phase_id;

    IF phase_data.project_id IS NOT NULL THEN
        SELECT p.project_name INTO project_name
        FROM ai_verify_transaction.projects p
        WHERE p.project_id = phase_data.project_id;

        SELECT sp.phase_name INTO phase_name
        FROM ai_verify_master.sdlc_phases sp
        WHERE sp.phase_id = phase_data.phase_id;
    END IF;

    -- 5️⃣ Users mapped to this task
    SELECT json_agg(
        json_build_object(
            'user_id', u.user_id,
            'user_name', u.user_name,
			'image_url', u.image_url
        )
    )
    INTO users_json
    FROM ai_verify_transaction.project_task_users ptu
    JOIN ai_verify_transaction.users u ON u.user_id = ptu.user_id
    WHERE ptu.project_task_id = p_project_task_id
	AND ptu.user_is_active = true;

    IF users_json IS NULL THEN
        users_json := '[]'::json;
    END IF;

    -- 6️⃣ Task work logs
    SELECT json_agg(
        json_build_object(
            'task_work_log_id', twl.task_work_log_id,
            'user_id', twl.user_id,
            'user_name', u.user_name,
			'image_url',u.image_url,
            'remarks', twl.remarks,
            'created_date', to_char(twl.created_date, 'YYYY-MM-DD"T"HH24:MI:SS')
        ) ORDER BY twl.task_work_log_id ASC
    )
    INTO work_logs_json
    FROM ai_verify_transaction.task_work_log twl
    JOIN ai_verify_transaction.users u ON u.user_id = twl.user_id
    WHERE twl.project_task_id = p_project_task_id;

    IF work_logs_json IS NULL THEN
        work_logs_json := '[]'::json;
    END IF;

    -- 7️⃣ Combine all data
    response_data := json_build_object(
        'project_task_id', project_task_record.project_task_id,
        'task_id', project_task_record.task_id,
        'task_name', task_name,
        'task_status_id', project_task_record.task_status_id,
        'status_name', status_name,
        'project_phase_id', project_task_record.project_phase_id,
        'project_id', phase_data.project_id,
        'phase_id', phase_data.phase_id,
        'project_name', project_name,
        'phase_name', phase_name,
        'users', users_json,
        'work_logs', work_logs_json
    );

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Task work log details fetched successfully',
        'data', response_data
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'status_code', 500,
            'message', 'Internal server error',
            'data', json_build_array()
        );
END;
$BODY$;


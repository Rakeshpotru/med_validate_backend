-- Muni --  16-09-2025 --

INSERT INTO ai_verify_master.user_roles (role_name, is_active) VALUES
('Admin', true),
('Validator', true),
('Viewer', true),
('Manager', true),
('General Manager', true),
( 'Author', true),
( 'Reviewer', true),
( 'Executor', true),
( 'Sign off', true),
( 'Business Owner', true),
( 'System Owner', true),
( 'QA', true);


INSERT INTO ai_verify_transaction.users (user_name, email, password) VALUES
( 'Babjee', 'uchadmin@gmail.com', 'qwerty@123'),
( 'Phani G', 'phani@gmail.com', 'qwerty@123'),
( 'Mounika M', 'mounika@gmail.com', 'qwerty@123'),
( 'Madhav V', 'madhav@gmail.com', 'qwerty@123'),
( 'Rakesh Potru', 'rakesh@gmail.com', 'qwerty@123'),
('Muni P', 'muni@gmail.com', 'qwerty@123'),
('Sushma A', 'sushma@gmail.com', 'qwerty@123'),
('Sanath K', 'sanath@gmail.com', 'qwerty@123'),
('Bhavana A', 'bhavana@gmail.com', 'qwerty@123'),
( 'Sowjanya N', 'sowjanya@gmail.com', 'qwerty@123'),
('Prabhu K', 'prabhu@gmail.com', 'qwerty@123'),
('Vasanthi VK', 'vasanthi@gmail.com', 'qwerty@123'),
('Vinay A', 'vinay@gmail.com', 'qwerty@123'),
('Prudhvi N', 'prudhvi@gmail.com', 'qwerty@123');

INSERT INTO ai_verify_transaction.user_role_mapping (user_id, role_id) VALUES
(1, 1),   -- Babjee -> Admin
(2, 6),   -- Phani G -> Author
(3, 6),   -- Mounika M -> Author
(4, 7),   -- Madhav V -> Reviewer
(5, 8),   -- Rakesh Potru -> Executor
(6, 8),   -- Muni P -> Executor
(7, 7),   -- Sushma A -> Reviewer
(8, 6),   -- Sanath K -> Author
(9, 7),   -- Bhavana A -> Reviewer
(10, 9),  -- Sowjanya N -> Sign off
(11, 9),  -- Prabhu K -> Sign off
(12, 9),  -- Vasanthi VK -> Sign off
(13, 1),  -- Vinay A -> Admin
(14, 2);

INSERT INTO ai_verify_master.status (status_name) VALUES
( 'Active'),
( 'On Hold'),
( 'Completed'),
( 'Pending'),
( 'Reverted'),
( 'Approved'),
( 'Closed'),
( 'Not Yet Started'),
( 'Incident Resolved'),
( 'Incident Reported'),
( 'Stuck');

--***************************************************************************************
--task document submit poc function
CREATE OR REPLACE FUNCTION ai_verify_draft.poc_project_task_submit_v3(
	p_task_id integer,
	p_document character varying,
	p_task_status integer,
	p_updated_by integer)
    RETURNS text
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_current_status INT;
    v_user_name VARCHAR;
    v_role_id INT;
    v_next_task_id INT;
    v_phase_id INT;
    v_all_tasks_completed BOOLEAN;
	v_task_users_count INTEGER;
	v_task_users_submitted INTEGER;
	v_doc_version double precision;
	v_task_doc_exist INTEGER;
	v_user_submitted BOOLEAN;
	v_project_id INT;
	v_next_phase_id INT;
	v_first_task_id INT;
	v_rows_updated INT;
	v_unresolved_comments INT;
BEGIN

    -- Get current task status and phase ID
    SELECT status_id, project_phase_id, task_users_count, COALESCE(task_users_submitted, 0)
    INTO v_current_status, v_phase_id, v_task_users_count, v_task_users_submitted
    FROM ai_verify_draft.project_tasks
    WHERE project_task_id = p_task_id;

    IF NOT FOUND THEN
        RAISE NOTICE 'Task ID: % not found in project_tasks', p_task_id;
        RETURN 'Error: Task not found';
    END IF;

	RAISE NOTICE 'Fetched task details - Task ID: %, Status: %, Phase ID: %, Users Count: %, Submitted Count: %',
		p_task_id, v_current_status, v_phase_id, v_task_users_count, v_task_users_submitted;

-- Get project ID
	SELECT project_id
	INTO v_project_id
	FROM ai_verify_draft.project_phases
	WHERE project_phase_id = v_phase_id;

	RAISE NOTICE 'Fetched Project ID: % for Phase ID: %', v_project_id, v_phase_id;

	-- task document version fetch for current task
	SELECT COALESCE(doc_version, 0.0)
	INTO v_doc_version
	FROM ai_verify_draft.project_task_documents
	WHERE project_task_id = p_task_id;

	RAISE NOTICE 'Fetched doc version: % for Task ID: %', v_doc_version, p_task_id;

	-- Check unresolved comments for current phase OR next task
	SELECT COUNT(*)
	INTO v_unresolved_comments
	FROM ai_verify_draft.project_task_comments PTC
	JOIN ai_verify_draft.project_tasks PT
	  ON PT.project_task_id = PTC.project_task_id
	WHERE PTC.task_comment_status = 1
	  AND (
	        PT.project_phase_id = v_phase_id  -- any task in current phase
	        OR PT.project_task_id = p_task_id + 1  -- immediate next task
	      );
	RAISE NOTICE 'Fetched v_unresolved_comments: %', v_unresolved_comments;

	IF v_unresolved_comments > 0 THEN
	    RETURN 'You have Comments to resolve before submitting task';
	END IF;


    -- Get user name and role of the updated_by user
    SELECT u.user_name, urm.role_id
    INTO v_user_name, v_role_id
    FROM ai_verify_draft.users u
    JOIN ai_verify_draft.user_role_mapping urm ON u.user_id = urm.user_id
    WHERE u.user_id = p_updated_by
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE NOTICE 'User ID: % not found or has no role', p_updated_by;
        RETURN 'Error: User not found or has no role';
    END IF;

	RAISE NOTICE 'Fetched user details - User Name: %, Role ID: % for User ID: %',
		v_user_name, v_role_id, p_updated_by;

    -- If the status is same as provided status, return message
    IF v_current_status = p_task_status THEN
        RAISE NOTICE 'Status unchanged - Current Status: % matches Input Status: %',
			v_current_status, p_task_status;
        RETURN 'Task submitted by: ' || v_user_name;
    ELSE
		RAISE NOTICE 'Status changed - Current Status: % differs from Input Status: %',
			v_current_status, p_task_status;
    END IF;

    -- Check if user already submitted
    SELECT submitted INTO v_user_submitted
    FROM ai_verify_draft.project_task_users
    WHERE project_task_id = p_task_id AND user_id = p_updated_by;

    IF NOT FOUND THEN
        RAISE NOTICE 'User ID: % not assigned to Task ID: %', p_updated_by, p_task_id;
        RETURN 'Error: User not assigned to this task';
    END IF;

    IF v_user_submitted THEN
        RAISE NOTICE 'User already submitted - User ID: % for Task ID: %',
			p_updated_by, p_task_id;
        RETURN 'You have already submitted this task.';
    ELSE
		RAISE NOTICE 'User has not submitted yet - User ID: % for Task ID: %',
			p_updated_by, p_task_id;
    END IF;

    -- Increment submitted count once
    v_task_users_submitted := v_task_users_submitted + 1;
	RAISE NOTICE 'Incremented submitted count to: % for Task ID: %',
		v_task_users_submitted, p_task_id;

    -- Step 1: Check if doc exists
    SELECT COUNT(*)
    INTO v_task_doc_exist
    FROM ai_verify_draft.project_task_documents
    WHERE project_task_id = p_task_id;

    IF v_task_doc_exist = 0 THEN
        RAISE NOTICE 'No document exists for Task ID: %, inserting new doc with version 1.0',
			p_task_id;
        -- Insert first doc as version 1.0
        INSERT INTO ai_verify_draft.project_task_documents (
            project_task_id,project_phase_id,project_id, document, doc_version, created_by, submitted_by, updated_date
        ) VALUES (
            p_task_id,v_phase_id, v_project_id, p_document, 1.0, p_updated_by, p_updated_by, NOW()
        );
    ELSE
        IF v_doc_version = 0.0 OR v_doc_version IS NULL THEN
            RAISE NOTICE 'Document exists with version 0.0 or NULL for Task ID: %, updating to version 1.0',
				p_task_id;
            -- Update doc_version to 1.0 if 0.0 or NULL
            UPDATE ai_verify_draft.project_task_documents
            SET doc_version = 1.0,
				document = p_document,
                updated_by = p_updated_by,
                submitted_by = p_updated_by,
                updated_date = NOW()
            WHERE project_task_id = p_task_id;
        ELSE
            RAISE NOTICE 'Document exists with version % for Task ID: %, inserting new row with version 1.0',
				v_doc_version, p_task_id;
            -- Insert new row with version 1.0
            INSERT INTO ai_verify_draft.project_task_documents (
                project_task_id,project_phase_id,project_id, document, doc_version, created_by, submitted_by, created_date
            ) VALUES (
                p_task_id,v_phase_id, v_project_id, p_document, 1.0, p_updated_by, p_updated_by, NOW()
            );
        END IF;
    END IF;

    -- Mark user as submitted
    UPDATE ai_verify_draft.project_task_users
    SET submitted = TRUE
    WHERE project_task_id = p_task_id
      AND user_id = p_updated_by
	RETURNING 1 INTO v_rows_updated;

    IF v_rows_updated = 1 THEN
        RAISE NOTICE 'Successfully marked user as submitted - User ID: % for Task ID: %',
			p_updated_by, p_task_id;
    ELSE
        RAISE NOTICE 'Failed to update project_task_users - No rows updated for User ID: % and Task ID: %',
			p_updated_by, p_task_id;
        RETURN 'Error: Failed to mark user as submitted';
    END IF;

    -- Update project_tasks submission count
    UPDATE ai_verify_draft.project_tasks
    SET task_users_submitted = v_task_users_submitted,
        updated_by = p_updated_by,
        updated_date = NOW()
    WHERE project_task_id = p_task_id;
	-- RETURNING task_users_submitted INTO v_task_users_submitted;
	RAISE NOTICE 'Updated project tasks - Submission Count: % for Task ID: %',
		v_task_users_submitted, p_task_id;

    -- Case: all users not yet done
    IF v_task_users_submitted < v_task_users_count THEN
        RAISE NOTICE 'Not all users submitted - Submitted: % of % for Task ID: %',
			v_task_users_submitted, v_task_users_count, p_task_id;
        RETURN 'Submission saved. Waiting for other users';
    ELSE
		RAISE NOTICE 'All users submitted - Submitted: % of % for Task ID: %',
			v_task_users_submitted, v_task_users_count, p_task_id;
    END IF;

    -- Case: all users submitted → finalize current task
    UPDATE ai_verify_draft.project_tasks
    SET status_id = p_task_status,
        updated_by = p_updated_by,
        updated_date = NOW()
    WHERE project_task_id = p_task_id;
	RAISE NOTICE 'Finalized current task - Status set to: % for Task ID: %',
		p_task_status, p_task_id;

    -- Activate next task (if applicable)
    SELECT project_task_id
    INTO v_next_task_id
    FROM ai_verify_draft.project_tasks
    WHERE project_phase_id = v_phase_id
      AND status_id = 8  -- assuming 0 = "Pending"
      AND project_task_id > p_task_id  -- Ensure it's a subsequent task
    ORDER BY project_task_id ASC
    LIMIT 1;

    IF v_next_task_id IS NOT NULL THEN
        RAISE NOTICE 'Found next task - Task ID: % for Phase ID: %',
			v_next_task_id, v_phase_id;
        UPDATE ai_verify_draft.project_tasks
        SET status_id = 1,  -- Active
            updated_by = p_updated_by,
            updated_date = NOW()
        WHERE project_task_id = v_next_task_id;
		RAISE NOTICE 'Activated next task - Task ID: % set to Active (status_id = 1)',
			v_next_task_id;
    ELSE
		RAISE NOTICE 'No next task found for Phase ID: %', v_phase_id;
    END IF;

    -- If all tasks in phase are done → close phase and activate next phase
    SELECT NOT EXISTS (
        SELECT 1
        FROM ai_verify_draft.project_tasks
        WHERE project_phase_id = v_phase_id
          AND status_id != 3  -- assuming 3 = "Completed"
    )
    INTO v_all_tasks_completed;

    IF v_all_tasks_completed THEN
        RAISE NOTICE 'All tasks completed for Phase ID: %, closing phase', v_phase_id;
        UPDATE ai_verify_draft.project_phases
        SET status_id = 7, -- Closed
            updated_by = p_updated_by,
            updated_date = NOW()
        WHERE project_phase_id = v_phase_id;



        -- Activate next phase (if applicable)
        SELECT project_phase_id
        INTO v_next_phase_id
        FROM ai_verify_draft.project_phases
        WHERE project_id = v_project_id
          AND status_id = 8  -- assuming 0 = "Pending"
          AND project_phase_id > v_phase_id  -- Ensure it's a subsequent phase
        ORDER BY project_phase_id ASC
        LIMIT 1;

        IF v_next_phase_id IS NOT NULL THEN
            RAISE NOTICE 'Activating next phase - Phase ID: %', v_next_phase_id;
            UPDATE ai_verify_draft.project_phases
            SET status_id = 1,  -- Active
                updated_by = p_updated_by,
                updated_date = NOW()
            WHERE project_phase_id = v_next_phase_id;

            -- Activate first task in next phase
            SELECT project_task_id
            INTO v_first_task_id
            FROM ai_verify_draft.project_tasks
            WHERE project_phase_id = v_next_phase_id
              AND status_id = 8
            ORDER BY project_task_id ASC
            LIMIT 1;

            IF v_first_task_id IS NOT NULL THEN
                RAISE NOTICE 'Activating first task in next phase - Task ID: %', v_first_task_id;
                UPDATE ai_verify_draft.project_tasks
                SET status_id = 1,
                    updated_by = p_updated_by,
                    updated_date = NOW()
                WHERE project_task_id = v_first_task_id;
            ELSE
				RAISE NOTICE 'No tasks found in next phase - Phase ID: %', v_next_phase_id;
            END IF;
        ELSE
			update ai_verify_draft.projects
			set status_id = 3
			where project_id = v_project_id;
			RAISE NOTICE 'No next phase found for Project ID: %', v_project_id;
        END IF;
    ELSE
		RAISE NOTICE 'Not all tasks completed for Phase ID: %', v_phase_id;
    END IF;

    RETURN 'Task fully submitted and status updated';
END;
$BODY$;
---------------------
--task document submit dev function
CREATE OR REPLACE FUNCTION ai_verify_transaction.submit_project_task_document(
	p_project_task_id integer,
	p_document_json text,
	p_task_status_id integer,
	p_updated_by integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_task_status_id INTEGER;
    v_project_phase_id INTEGER;
    v_task_users_count INTEGER;
    v_task_users_submitted INTEGER;
    v_project_id INTEGER;
    v_unresolved_comments INTEGER;
    v_user_name VARCHAR;
    v_role_id INTEGER;
    v_user_submitted BOOLEAN;
    v_doc_version NUMERIC(10, 2);
    v_task_doc_id INTEGER;
    v_rows_updated INTEGER;
    v_next_task_id INTEGER;
    v_pending_tasks INTEGER;
    v_next_phase_id INTEGER;
    v_first_task_id INTEGER;
BEGIN
    -- Validate input parameters
    IF p_project_task_id IS NULL OR p_document_json IS NULL OR p_task_status_id IS NULL OR p_updated_by IS NULL THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'All parameters are required',
            'data', NULL
        );
    END IF;

    -- Get current task details
    SELECT task_status_id, project_phase_id, task_users_count, task_users_submitted
    INTO v_task_status_id, v_project_phase_id, v_task_users_count, v_task_users_submitted
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_task_id = p_project_task_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Task not found',
            'data', NULL
        );
    END IF;

    v_task_users_submitted := COALESCE(v_task_users_submitted, 0);

    -- Get project ID
    SELECT project_id
    INTO v_project_id
    FROM ai_verify_transaction.project_phases_list
    WHERE project_phase_id = v_project_phase_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Project phase not found',
            'data', NULL
        );
    END IF;

    -- Check unresolved comments
    SELECT COUNT(*)
    INTO v_unresolved_comments
    FROM ai_verify_transaction.project_comments pc
    JOIN ai_verify_transaction.project_tasks_list ptl ON pc.project_task_id = ptl.project_task_id
    WHERE pc.is_resolved = FALSE
    AND (ptl.project_phase_id = v_project_phase_id OR ptl.project_task_id = p_project_task_id + 1);

    IF v_unresolved_comments > 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'You have comments to resolve before submitting task',
            'data', NULL
        );
    END IF;

    -- Verify user and role
    SELECT u.user_name, urm.role_id
    INTO v_user_name, v_role_id
    FROM ai_verify_master.users u
    JOIN ai_verify_master.user_role_mapping urm ON u.user_id = urm.user_id
    WHERE u.user_id = p_updated_by;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'User not found or has no role',
            'data', NULL
        );
    END IF;

    -- Check if task status is unchanged
    IF v_task_status_id = p_task_status_id THEN
        RETURN json_build_object(
            'status_code', 200,
            'message', 'Task submitted by: ' || v_user_name,
            'data', json_build_object()
        );
    END IF;

    -- Check if user is assigned and hasn't submitted
    SELECT submitted
    INTO v_user_submitted
    FROM ai_verify_transaction.project_task_users
    WHERE project_task_id = p_project_task_id AND user_id = p_updated_by;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 403,
            'message', 'User not assigned to this task',
            'data', NULL
        );
    END IF;

    IF v_user_submitted THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'You have already submitted this task',
            'data', NULL
        );
    END IF;

    -- Check if document exists
    SELECT doc_version
    INTO v_doc_version
    FROM ai_verify_docs.task_docs
    WHERE project_task_id = p_project_task_id AND is_latest = TRUE;

    IF NOT FOUND THEN
        -- Insert first document
        INSERT INTO ai_verify_docs.task_docs (
            project_task_id, project_phase_id, project_id, document_json,
            doc_version, created_by, submitted_by, created_date, is_latest
        )
        VALUES (
            p_project_task_id, v_project_phase_id, v_project_id, p_document_json,
            1.0, p_updated_by, p_updated_by, CURRENT_TIMESTAMP, TRUE
        )
        RETURNING task_doc_id INTO v_task_doc_id;
    ELSE
        IF v_doc_version IS NULL OR v_doc_version = 0.0 THEN
            -- Update document to version 1.0
            UPDATE ai_verify_docs.task_docs
            SET doc_version = 1.0,
                document_json = p_document_json,
                updated_by = p_updated_by,
                submitted_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_task_id = p_project_task_id AND is_latest = TRUE
            RETURNING task_doc_id INTO v_task_doc_id;
        ELSE
            -- Insert new document with incremented version
            UPDATE ai_verify_docs.task_docs
            SET is_latest = FALSE
            WHERE project_task_id = p_project_task_id;

            INSERT INTO ai_verify_docs.task_docs (
                project_task_id, project_phase_id, project_id, document_json,
                doc_version, created_by, submitted_by, created_date, is_latest
            )
            VALUES (
                p_project_task_id, v_project_phase_id, v_project_id, p_document_json,
                v_doc_version + 1, p_updated_by, p_updated_by, CURRENT_TIMESTAMP, TRUE
            )
            RETURNING task_doc_id INTO v_task_doc_id;
        END IF;
    END IF;

    -- Mark user as submitted
    UPDATE ai_verify_transaction.project_task_users
    SET submitted = TRUE
    WHERE project_task_id = p_project_task_id AND user_id = p_updated_by
    RETURNING 1 INTO v_rows_updated;

    IF v_rows_updated != 1 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'User-task mapping not found or update not applied',
            'data', NULL
        );
    END IF;

    -- Update task submission count
    v_task_users_submitted := v_task_users_submitted + 1;

    UPDATE ai_verify_transaction.project_tasks_list
    SET task_users_submitted = v_task_users_submitted,
        updated_by = p_updated_by,
        updated_date = CURRENT_TIMESTAMP
    WHERE project_task_id = p_project_task_id;

    -- Check if all users have submitted
    IF v_task_users_submitted < v_task_users_count THEN
        RETURN json_build_object(
            'status_code', 200,
            'message', 'Submission saved. Waiting for other users',
            'data', json_build_object(
                'task_doc_id', v_task_doc_id,
                'doc_version', CASE WHEN v_doc_version IS NULL OR v_doc_version = 0.0 THEN 1.0 ELSE v_doc_version + 1 END
            )
        );
    END IF;

    -- All users submitted, finalize task
    UPDATE ai_verify_transaction.project_tasks_list
    SET task_status_id = p_task_status_id,
        updated_by = p_updated_by,
        updated_date = CURRENT_TIMESTAMP
    WHERE project_task_id = p_project_task_id;

    -- Activate next task
    SELECT project_task_id
    INTO v_next_task_id
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_phase_id = v_project_phase_id
    AND task_status_id = 8  -- Pending
    AND project_task_id > p_project_task_id
    ORDER BY project_task_id ASC
    LIMIT 1;

    IF v_next_task_id IS NOT NULL THEN
        UPDATE ai_verify_transaction.project_tasks_list
        SET task_status_id = 1,  -- Active
            updated_by = p_updated_by,
            updated_date = CURRENT_TIMESTAMP
        WHERE project_task_id = v_next_task_id;
    END IF;

    -- Check if all tasks in phase are completed
    SELECT COUNT(*)
    INTO v_pending_tasks
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_phase_id = v_project_phase_id
    AND task_status_id != 3;  -- Completed

    IF v_pending_tasks = 0 THEN
        -- Close current phase
        UPDATE ai_verify_transaction.project_phases_list
        SET status_id = 7,  -- Closed
            updated_by = p_updated_by,
            updated_date = CURRENT_TIMESTAMP
        WHERE project_phase_id = v_project_phase_id;

        -- Activate next phase
        SELECT project_phase_id
        INTO v_next_phase_id
        FROM ai_verify_transaction.project_phases_list
        WHERE project_id = v_project_id
        AND status_id = 8  -- Pending
        AND project_phase_id > v_project_phase_id
        ORDER BY project_phase_id ASC
        LIMIT 1;

        IF v_next_phase_id IS NOT NULL THEN
            UPDATE ai_verify_transaction.project_phases_list
            SET status_id = 1,  -- Active
                updated_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_phase_id = v_next_phase_id;

            -- Activate first task in next phase
            SELECT project_task_id
            INTO v_first_task_id
            FROM ai_verify_transaction.project_tasks_list
            WHERE project_phase_id = v_next_phase_id
            AND task_status_id = 8
            ORDER BY project_task_id ASC
            LIMIT 1;

            IF v_first_task_id IS NOT NULL THEN
                UPDATE ai_verify_transaction.project_tasks_list
                SET task_status_id = 1,
                    updated_by = p_updated_by,
                    updated_date = CURRENT_TIMESTAMP
                WHERE project_task_id = v_first_task_id;
            END IF;
        ELSE
            -- No next phase, mark project as completed
            UPDATE ai_verify_transaction.projects
            SET status_id = 3,  -- Completed
                updated_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_id = v_project_id;
        END IF;
    END IF;

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Task fully submitted and status updated',
        'data', json_build_object(
            'task_doc_id', v_task_doc_id,
            'doc_version', CASE WHEN v_doc_version IS NULL OR v_doc_version = 0.0 THEN 1.0 ELSE v_doc_version + 1 END
        )
    );

EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'status_code', 500,
        'message', 'Internal Server Error: ' || SQLERRM,
        'data', NULL
    );
END;
$BODY$;
-----------------------------
--task document submit dev v2 function
CREATE OR REPLACE FUNCTION ai_verify_transaction.submit_project_task_document_v2(
	p_project_task_id integer,
	p_document_json text,
	p_task_status_id integer,
	p_updated_by integer)
    RETURNS json
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
DECLARE
    v_task_status_id INTEGER;
    v_project_phase_id INTEGER;
    v_task_users_count INTEGER;
    v_task_users_submitted INTEGER;
    v_project_id INTEGER;
    v_unresolved_comments INTEGER;
    v_user_name VARCHAR;
    v_role_id INTEGER;
    v_user_submitted BOOLEAN;
    v_doc_version NUMERIC(10, 2);
    v_task_doc_id INTEGER;
    v_rows_updated INTEGER;
    v_next_task_id INTEGER;
    v_pending_tasks INTEGER;
    v_next_phase_id INTEGER;
    v_first_task_id INTEGER;
BEGIN
    -- Validate input parameters
    IF p_project_task_id IS NULL OR p_document_json IS NULL OR p_task_status_id IS NULL OR p_updated_by IS NULL THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'All parameters are required',
            'data', NULL
        );
    END IF;

    -- Get current task details
    SELECT task_status_id, project_phase_id, task_users_count, task_users_submitted
    INTO v_task_status_id, v_project_phase_id, v_task_users_count, v_task_users_submitted
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_task_id = p_project_task_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Task not found',
            'data', NULL
        );
    END IF;

    v_task_users_submitted := COALESCE(v_task_users_submitted, 0);

    -- Get project ID
    SELECT project_id
    INTO v_project_id
    FROM ai_verify_transaction.project_phases_list
    WHERE project_phase_id = v_project_phase_id;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'Project phase not found',
            'data', NULL
        );
    END IF;

    -- Check unresolved comments
    SELECT COUNT(*)
    INTO v_unresolved_comments
    FROM ai_verify_transaction.project_comments pc
    JOIN ai_verify_transaction.project_tasks_list ptl ON pc.project_task_id = ptl.project_task_id
    WHERE pc.is_resolved = FALSE
    AND (ptl.project_phase_id = v_project_phase_id OR ptl.project_task_id = p_project_task_id + 1);

    IF v_unresolved_comments > 0 THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'You have comments to resolve before submitting task',
            'data', NULL
        );
    END IF;

    -- Verify user and role
    SELECT u.user_name, urm.role_id
    INTO v_user_name, v_role_id
    FROM ai_verify_transaction.users u
    JOIN ai_verify_transaction.user_role_mapping urm ON u.user_id = urm.user_id
    WHERE u.user_id = p_updated_by;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'User not found or has no role',
            'data', NULL
        );
    END IF;

    -- Check if task status is unchanged
    IF v_task_status_id = p_task_status_id THEN
        RETURN json_build_object(
            'status_code', 200,
            'message', 'Task submitted by: ' || v_user_name,
            'data', json_build_object()
        );
    END IF;

    -- Check if user is assigned and hasn't submitted
    SELECT submitted
    INTO v_user_submitted
    FROM ai_verify_transaction.project_task_users
    WHERE project_task_id = p_project_task_id AND user_id = p_updated_by;

    IF NOT FOUND THEN
        RETURN json_build_object(
            'status_code', 403,
            'message', 'User not assigned to this task',
            'data', NULL
        );
    END IF;

    IF v_user_submitted THEN
        RETURN json_build_object(
            'status_code', 400,
            'message', 'You have already submitted this task',
            'data', NULL
        );
    END IF;

    -- Check if document exists
    SELECT doc_version
    INTO v_doc_version
    FROM ai_verify_docs.task_docs
    WHERE project_task_id = p_project_task_id AND is_latest = TRUE;

    IF NOT FOUND THEN
        -- Insert first document
        INSERT INTO ai_verify_docs.task_docs (
            project_task_id, project_phase_id, project_id, document_json,
            doc_version, created_by, submitted_by, created_date, is_latest
        )
        VALUES (
            p_project_task_id, v_project_phase_id, v_project_id, p_document_json,
            1.0, p_updated_by, p_updated_by, CURRENT_TIMESTAMP, TRUE
        )
        RETURNING task_doc_id INTO v_task_doc_id;
    ELSE
        IF v_doc_version IS NULL OR v_doc_version = 0.0 THEN
            -- Update document to version 1.0
            UPDATE ai_verify_docs.task_docs
            SET doc_version = 1.0,
                document_json = p_document_json,
                updated_by = p_updated_by,
                submitted_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_task_id = p_project_task_id AND is_latest = TRUE
            RETURNING task_doc_id INTO v_task_doc_id;
        ELSE
            -- Insert new document with incremented version
            UPDATE ai_verify_docs.task_docs
            SET is_latest = FALSE
            WHERE project_task_id = p_project_task_id;

            INSERT INTO ai_verify_docs.task_docs (
                project_task_id, project_phase_id, project_id, document_json,
                doc_version, created_by, submitted_by, created_date, is_latest
            )
            VALUES (
                p_project_task_id, v_project_phase_id, v_project_id, p_document_json,
                v_doc_version + 1, p_updated_by, p_updated_by, CURRENT_TIMESTAMP, TRUE
            )
            RETURNING task_doc_id INTO v_task_doc_id;
        END IF;
    END IF;

    -- Mark user as submitted
    UPDATE ai_verify_transaction.project_task_users
    SET submitted = TRUE
    WHERE project_task_id = p_project_task_id AND user_id = p_updated_by
    RETURNING 1 INTO v_rows_updated;

    IF v_rows_updated != 1 THEN
        RETURN json_build_object(
            'status_code', 404,
            'message', 'User-task mapping not found or update not applied',
            'data', NULL
        );
    END IF;

    -- Update task submission count
    v_task_users_submitted := v_task_users_submitted + 1;

    UPDATE ai_verify_transaction.project_tasks_list
    SET task_users_submitted = v_task_users_submitted,
        updated_by = p_updated_by,
        updated_date = CURRENT_TIMESTAMP
    WHERE project_task_id = p_project_task_id;

    -- Check if all users have submitted
    IF v_task_users_submitted < v_task_users_count THEN
        RETURN json_build_object(
            'status_code', 200,
            'message', 'Submission saved. Waiting for other users',
            'data', json_build_object(
                'task_doc_id', v_task_doc_id,
                'doc_version', CASE WHEN v_doc_version IS NULL OR v_doc_version = 0.0 THEN 1.0 ELSE v_doc_version + 1 END
            )
        );
    END IF;

    -- All users submitted, finalize task
    UPDATE ai_verify_transaction.project_tasks_list
    SET task_status_id = p_task_status_id,
        updated_by = p_updated_by,
        updated_date = CURRENT_TIMESTAMP
    WHERE project_task_id = p_project_task_id;

    -- Activate next task
    SELECT project_task_id
    INTO v_next_task_id
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_phase_id = v_project_phase_id
    AND task_status_id in (8,4)  -- Pending
    AND project_task_id > p_project_task_id
    ORDER BY project_task_id ASC
    LIMIT 1;

    IF v_next_task_id IS NOT NULL THEN
        UPDATE ai_verify_transaction.project_tasks_list
        SET task_status_id = 1,  -- Active
            updated_by = p_updated_by,
            updated_date = CURRENT_TIMESTAMP
        WHERE project_task_id = v_next_task_id;
    END IF;

    -- Check if all tasks in phase are completed
    SELECT COUNT(*)
    INTO v_pending_tasks
    FROM ai_verify_transaction.project_tasks_list
    WHERE project_phase_id = v_project_phase_id
    AND task_status_id != 3;  -- Completed

    IF v_pending_tasks = 0 THEN
        -- Close current phase
        UPDATE ai_verify_transaction.project_phases_list
        SET status_id = 7,  -- Closed
            updated_by = p_updated_by,
            updated_date = CURRENT_TIMESTAMP
        WHERE project_phase_id = v_project_phase_id;

        -- Activate next phase
        SELECT project_phase_id
        INTO v_next_phase_id
        FROM ai_verify_transaction.project_phases_list
        WHERE project_id = v_project_id
        AND status_id = 8  -- Pending
        AND project_phase_id > v_project_phase_id
        ORDER BY project_phase_id ASC
        LIMIT 1;

        IF v_next_phase_id IS NOT NULL THEN
            UPDATE ai_verify_transaction.project_phases_list
            SET status_id = 1,  -- Active
                updated_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_phase_id = v_next_phase_id;

            -- Activate first task in next phase
            SELECT project_task_id
            INTO v_first_task_id
            FROM ai_verify_transaction.project_tasks_list
            WHERE project_phase_id = v_next_phase_id
            AND task_status_id = 8
            ORDER BY project_task_id ASC
            LIMIT 1;

            IF v_first_task_id IS NOT NULL THEN
                UPDATE ai_verify_transaction.project_tasks_list
                SET task_status_id = 1,
                    updated_by = p_updated_by,
                    updated_date = CURRENT_TIMESTAMP
                WHERE project_task_id = v_first_task_id;
            END IF;
        ELSE
            -- No next phase, mark project as completed
            UPDATE ai_verify_transaction.projects
            SET status_id = 3,  -- Completed
                updated_by = p_updated_by,
                updated_date = CURRENT_TIMESTAMP
            WHERE project_id = v_project_id;
        END IF;
    END IF;

    RETURN json_build_object(
        'status_code', 200,
        'message', 'Task fully submitted and status updated',
        'data', json_build_object(
            'task_doc_id', v_task_doc_id,
            'doc_version', CASE WHEN v_doc_version IS NULL OR v_doc_version = 0.0 THEN 1.0 ELSE v_doc_version + 1 END
        )
    );

EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'status_code', 500,
        'message', 'Internal Server Error: ' || SQLERRM,
        'data', NULL
    );
END;
$BODY$;
-------
SELECT ai_verify_transaction.submit_project_task_document_v2(
    p_project_task_id => 11,
    p_document_json => 'something for testing',
    p_task_status_id => 3,
    p_updated_by => 3
);
-------


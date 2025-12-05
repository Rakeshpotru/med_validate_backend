-- COmments table changes (added new column to seperate direct comments and inline comments)

-- Table: ai_verify_transaction.project_comments

-- DROP TABLE IF EXISTS ai_verify_transaction.project_comments;

CREATE TABLE IF NOT EXISTS ai_verify_transaction.project_comments
(
    comment_id integer NOT NULL DEFAULT nextval('ai_verify_transaction.project_comments_comment_id_seq'::regclass),
    project_id integer,
    project_phase_id integer,
    project_task_id integer,
    description character varying COLLATE pg_catalog."default",
    commented_by integer,
    comment_date timestamp with time zone,
    is_resolved boolean,
    resolved_by integer,
    resolved_date timestamp with time zone,
    updated_by integer,
    update_date timestamp without time zone,
    is_direct_comment boolean DEFAULT true,
    CONSTRAINT project_comments_pkey PRIMARY KEY (comment_id),
    CONSTRAINT project_comments_project_id_fkey FOREIGN KEY (project_id)
        REFERENCES ai_verify_transaction.projects (project_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT project_comments_project_phase_id_fkey FOREIGN KEY (project_phase_id)
        REFERENCES ai_verify_transaction.project_phases_list (project_phase_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT project_comments_project_task_id_fkey FOREIGN KEY (project_task_id)
        REFERENCES ai_verify_transaction.project_tasks_list (project_task_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS ai_verify_transaction.project_comments
    OWNER to postgres;
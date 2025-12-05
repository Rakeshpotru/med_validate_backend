-- 16-09-2025
--master data script

INSERT INTO ai_verify_master.equipment_list (
    equipment_name,
    is_ai_verified,
    created_by,
    created_date,
    updated_by,
    updated_date,
    is_active
) VALUES
('Analytical Balance', FALSE, 1, now(), NULL, NULL, TRUE),
('HPLC System', FALSE, 1, now(), NULL, NULL, TRUE),
('UV-Vis Spectrophotometer', FALSE, 1, now(), NULL, NULL, TRUE),
('Incubator', FALSE, 1, now(), NULL, NULL, TRUE),
('Conductivity Meter', FALSE, 1, now(), NULL, NULL, TRUE),
('TOC Analyzer', FALSE, 1, now(), NULL, NULL, TRUE),
('Water Purification System', FALSE, 1, now(), NULL, NULL, TRUE),
('Fume Hood / Laminar Flow Cabinet', FALSE, 1, now(), NULL, NULL, TRUE),
('Sonicator / Ultrasonic Bath', FALSE, 1, now(), NULL, NULL, TRUE),
('Dissolution Test Apparatus', FALSE, 1, now(), NULL, NULL, TRUE),
('Karl Fischer Titrator', FALSE, 1, now(), NULL, NULL, TRUE),
('Moisture Analyzer', FALSE, 1, now(), NULL, NULL, TRUE),
('Thermal Cycler / PCR Machine', FALSE, 1, now(), NULL, NULL, TRUE),
('Environmental Chamber', FALSE, 1, now(), NULL, NULL, TRUE),
('COD Analyzer', FALSE, 1, now(), NULL, NULL, TRUE),
('Viscometer', FALSE, 1, now(), NULL, NULL, TRUE),
('Melting Point Apparatus', FALSE, 1, now(), NULL, NULL, TRUE),
('Microscope', TRUE, 1, now(), NULL, NULL, TRUE);




================================================================




INSERT INTO  ai_verify_master.risk_assessments(
    risk_assessment_name,
    is_active
) VALUES
('Low',TRUE),
('Medium',TRUE),
('High',TRUE);




========================================================


INSERT INTO ai_verify_master.sdlc_phases (
    phase_name,
    is_active,
    order_id
) VALUES
('User Requirements Specification (URS)', TRUE, 1),
('Functional Requirements Specification (FRS)', TRUE, 2),
('Design Qualification (DQ)', TRUE, 3),
('Installation Qualification (IQ)', TRUE, 4),
('Operational Qualification (OQ)', TRUE, 5),
('Performance Qualification (PQ)', TRUE, 6),
('Risk Assessment / FMEA', TRUE, 7),
('Validation Plan', TRUE, 8),
('Calibration Certificates', TRUE, 9),
('User Manual', TRUE, 10),
('Standard Operating Procedures (SOP)', TRUE, 11),
('Test Scripts & Traceability Matrix', TRUE, 12);


====================================================
INSERT INTO ai_verify_master.sdlc_tasks (
    task_name,
    is_active,
    order_id
) VALUES
('draft', TRUE, 1),
('review', TRUE, 2),
('signoff', TRUE, 3),
('dryrun', TRUE, 4),
('pre approval', TRUE, 5),
('execution', TRUE, 6),
('post approval', TRUE, 7);



=================================================



INSERT INTO ai_verify_master.risk_sdlcphase_mapping (
    risk_assessment_id,
    phase_id,
    is_active
) VALUES
(1, 1, TRUE),
(1, 3, TRUE),

(2, 1, TRUE),
(2, 2, TRUE),
(2, 3, TRUE),
(2, 4, TRUE),

(3, 1, TRUE),
(3, 2, TRUE),
(3, 3, TRUE),
(3, 4, TRUE),
(3, 5, TRUE),
(3, 6, TRUE);


=========================================================



INSERT INTO ai_verify_master.user_roles (role_name, is_active) VALUES
('Admin', true),
('Validator', true),
('Viewer', true),
('Manager', true),
('General Manager', true),
( 'Author', true),
( 'Reviewer', true),
( 'Executor', true),
( 'Sign off', true);


=================================================

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



==========================================================



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
( 'Incident Reported');


===============================================================

INSERT INTO ai_verify_transaction.user_role_mapping (user_id, role_id) VALUES
(1, 1),   -- Babjee -> Admin
(2, 6),   -- Phani G -> Author (matches existing pattern)
(3, 6),   -- Mounika M -> Author (matches existing pattern)
(4, 7),   -- Madhav V -> Reviewer (matches existing pattern)
(5, 8),   -- Rakesh Potru -> Executor (matches existing pattern)
(6, 8),   -- Muni P -> Executor (matches existing pattern)
(7, 7),   -- Sushma A -> Reviewer (matches existing pattern)
(8, 6),   -- Sanath K -> Author (matches existing pattern)
(9, 7),   -- Bhavana A -> Reviewer (matches existing pattern)
(10, 9),  -- Sowjanya N -> Sign off (matches existing pattern)
(11, 9),  -- Prabhu K -> Sign off (matches existing pattern)
(12, 9),  -- Vasanthi VK -> Sign off (matches existing pattern)
(13, 1),  -- Vinay A -> Admin (cycle back)
(14, 2);




=================================================

INSERT INTO ai_verify_master.sdlc_phase_tasks_mapping (phase_id, task_id, is_active) VALUES
(1, 1, TRUE),
(1, 2, TRUE),
(1, 3, TRUE),
(2, 1, TRUE),
(2, 2, TRUE),
(2, 3, TRUE),
(3, 1, TRUE),
(3, 2, TRUE),
(3, 3, TRUE),
(3, 4, TRUE),
(3, 5, TRUE),
(3, 6, TRUE),
(3, 7, TRUE);

=============================
-- date :30-1-2025 created user_image_history table

CREATE TABLE ai_verify_transaction.user_image_history (
    image_history_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES ai_verify_transaction.users(user_id),
    image_url VARCHAR NOT NULL,
    image_changed_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(100)
);

-- begin;
--     UPDATE users set districts = (SELECT array_agg(id) FROM locations WHERE name = initcap(username) AND type_id=3)::INT[]
--     WHERE username IN (select lower(name) from locations where type_id = 3);
-- end;
--
BEGIN;
    INSERT INTO permissions(name, codename, sys_module)
    VALUES
        ('Can approve report', 'can_approve_report', 'Approve'),
        ('Can cancel report', 'can_cancel_report', 'Approve'),
        ('Can change report', 'can_change_report', 'Approve'),
        ('Can download reports', 'can_download_report', 'Approve'),
        ('Can view CARAMAL reports', 'can_view_caramal_reports', 'Caramal'),
        ('Can change anonymous report', 'can_change_anonymous_report', 'Hotline'),
        ('Can view anonymous report', 'can_view_anonymous_report', 'Hotline'),
        ('Can change profile', 'can_change_profile', 'Users'),
        ('Can send SMS', 'can_send_sms', 'All'),
        ('Can send bulk SMS', 'can_send_bulk_sms', 'All'),
        ('Can view facilities', 'can_view_facilities', 'Facilities'),
        ('Can view reporters', 'can_view_reporters', 'Reporters'),
        ('Can add reporter', 'can_add_reporter', 'Reporters'),
        ('Can change reporter', 'can_change_reporter', 'Reporters'),
        ('Can delete reporter', 'can_delete_reporter', 'Reporters'),
        ('Can sync reporter', 'can_sync_reporter', 'Reporters'),
        ('Can creats poll', 'can_create_poll', 'Polls'),
        ('Can change poll', 'can_change_poll', 'Polls'),
        ('Can delete poll', 'can_delete_poll', 'Polls'),
        ('Can download poll reponses', 'can_download_poll_responses', 'Polls'),
        ('Can start poll', 'can_start_poll', 'Polls'),
        ('Can stop poll', 'can_stop_poll', 'Polls'),
        ('Can view polls', 'can_view_polls', 'Polls'),
        ('Can add report', 'can_add_report', 'Data Entry'),
        ('Can manage dhis 2 integration', 'can_manage_dhis2_integration', 'Integration'),
        ('Can resend request', 'can_resend_request', 'Integration'),
        ('Can cancel request', 'can_cancel_request', 'Integration'),
        ('Can delete request', 'can_delete_request', 'Integration'),
        ('Can add dispatcher2 server', 'can_add_dispatcher2_server', 'Integration'),
        ('Can change dispatcher2 server', 'can_change_dispatcher2_server', 'Integration'),
        ('Can delete dispatcher2 server', 'can_delete_dispatcher2_server', 'Integration'),
        ('Can add indicator', 'can_add_indicator', 'Integration'),
        ('Can change indicator', 'can_change_indicator', 'Integration'),
        ('Can delete indicator', 'can_delete_indicator', 'Integration');
END;

BEGIN;
    INSERT INTO user_roles (name, descr)
        VALUES
        ('MoH Call Center User', 'For the MoH call center users'),
        ('Data Managers', 'For user that do data entry'),
        ('Facility User', 'For facility level users');
    -- Assuming Administrators user_role has id 1
    INSERT INTO user_role_permissions(user_role, permission_id) SELECT 1, id FROM permissions;
    -- Assuming 'District User' user_role has id 1
    INSERT INTO user_role_permissions(user_role, permission_id)
        SELECT 2, id FROM permissions WHERE sys_module IN ('Approve', 'Reporters', 'Hotline', 'All', 'Data Entry');
END;

begin;
    UPDATE users set districts = (SELECT array_agg(id) FROM locations WHERE name = initcap(username) AND type_id=3)::INT[]
    WHERE username IN (select lower(name) from locations where type_id = 3);
end;

BEGIN;
    INSERT INTO permissions(name, codename, sys_module)
    VALUES
        ('Add Reporter', 'can_add_reporter', 'Reporters'),
        ('Edit Reporter', 'can_edit_reporter', 'Reporters'),
        ('Delete Reporter', 'can_delete_reporter', 'Reporters'),
        ('SMS Reporter', 'can_sms_reporter', 'Reporters'),
        ('Send Poll', 'can_send_poll', 'Reporter'),

        ('Approve Reports', 'can_approve_reports', 'Reports'),
        ('Add Report', 'can_add_report', 'Reports'),
        ('Edit Report', 'can_edit_report', 'Reports'),
        ('Delete Report', 'can_delete_report', 'Reports'),

        ('Resend Reports', 'can_resend_report', 'Reports'),
        ('Edit Anonymous Report', 'can_edit_anonymous_report', 'Hotline'),
        ('', '', ''),
END;

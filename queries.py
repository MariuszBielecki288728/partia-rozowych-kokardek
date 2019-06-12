ADD_MEMBER = """
INSERT INTO member (id, password, last_act_time)
    VALUES (
        %(member_id)s,
        crypt(%(password)s, gen_salt('bf')),
        to_timestamp(%(timestamp)s)
    );
"""

ADD_LEADER = """
INSERT INTO leader VALUES (%(member_id)s);
"""

VALIDATE_PASSWORD = """
SELECT password = crypt(%(password)s, password) FROM member 
WHERE member.id = %(member_id)s;
"""

FIND_MEMBER = """
SELECT * FROM member WHERE member.id = %(member_id)s ;
"""

FIND_PROJECT = """
SELECT authority_id FROM project
where id = %(project_id)s ;
"""

ADD_AUTHORITY = """
INSERT INTO authority VALUES (%(authority_id)s);
"""

ADD_PROJECT = """
INSERT INTO project VALUES (%(project_id)s, %(authority_id)s);
"""

ADD_ACTION = """
INSERT INTO action VALUES (
    %(action_id)s,
    %(owner_id)s,
    %(is_support)s,
    %(project_id)s
);
"""

VALIDATE_ACTIVE_STATUS = """
SELECT to_timestamp(%(current_timestamp)s) - last_act_time < interval '1 YEAR'
FROM member WHERE member.id = %(member_id)s;
"""

UPDATE_MEMBER_LAST_ACT = """
UPDATE member SET last_act_time = to_timestamp(%(timestamp)s) 
WHERE member.id = %(member_id)s;
"""
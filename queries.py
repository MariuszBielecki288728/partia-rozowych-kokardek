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
ADD_VOTE = """
INSERT INTO member_votes_for VALUES (%(member_id)s, %(action_id)s, %(value)s);
UPDATE member SET {0} = {0} + 1
  WHERE member.id=(SELECT owner_id FROM action WHERE action.id=%(action_id)s);
"""

SELECT_ACTIONS = """
SELECT action.id, case when support then 'support' else 'protest' end as type,
       project_id, authority_id,
       (SELECT COUNT(*)
           FROM member_votes_for
           WHERE member_votes_for.action_id = action.id AND value = 1),
       (SELECT COUNT(*)
           FROM member_votes_for
           WHERE member_votes_for.action_id = action.id AND value = -1)
FROM action JOIN project ON (action.project_id=project.id)
{} {}
ORDER BY action.id;
"""

SELECT_PROJECTS = """
SELECT project.id, authority_id
FROM project
{}
ORDER BY project.id;
"""

FIND_LEADER = """
SELECT * FROM leader
WHERE member_id = %(member_id)s;
"""

SELECT_VOTES = """
SELECT member.id,
       (SELECT COUNT(*) FROM member_votes_for
            JOIN action ON (action.id=action_id)
            JOIN project ON (project.id=project_id)
                WHERE {0} AND value = 1),
       (SELECT COUNT(*) FROM member_votes_for
            JOIN action ON (action.id=action_id)
            JOIN project ON (project.id=project_id)
                WHERE {0} AND value = -1)
FROM member
ORDER BY member.id;
"""

SELECT_TROLLS = """
SELECT member.id,
       upvoted_count,
       downvoted_count,
       (case when (to_timestamp(%(current_timestamp)s) - last_act_time
                   < interval '1 YEAR')
             then 'true' else 'false' end) as active_status
FROM member
WHERE downvoted_count > upvoted_count
ORDER BY
    downvoted_count - upvoted_count DESC,
    member.id ASC;
"""

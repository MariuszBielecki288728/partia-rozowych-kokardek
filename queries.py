ADD_MEMBER = """
INSERT INTO member (member_id, password, last_act_time)
    VALUES (
        %(member_id)s,
        crypt(%(password)s, gen_salt('bf')),
        to_timestamp(%(timestamp)s)
    )
"""
ADD_LEADER = """
INSERT INTO leader VALUES (%(member_id)s)
"""

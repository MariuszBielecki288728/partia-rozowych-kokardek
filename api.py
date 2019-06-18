import json
import sys
import psycopg2
import typing

from queries import queries


class API:
    """
    Api for database system
    """
    def __init__(self, init_mode: bool):
        self.init_mode = init_mode

    def call(self, api_call: dict) -> dict:
        """
        Call corresponding method with name and arguments passed in api_call
        dict with following structure:
        {function_name: [arg1, ...]}
        """
        try:
            [(function, kwargs)] = api_call.items()
            data = getattr(self, function)(**kwargs)
        except Exception as e:
            self.conn.rollback()
            return self._error(str(e))
        else:
            self.conn.commit()
            return self._success(data)

    @staticmethod
    def _success(data: typing.Optional[list] = None) -> dict:
        if data is None:
            return {"status": "OK"}
        else:
            return {"status": "OK", "data": data}

    @staticmethod
    def _error(debug: str) -> dict:
        return {"status": "Error", "debug": debug}

    def open(self, database: str, login: str, password: str):
        """
        Open connection to given database.

        If application is running in init mode
        then create all needed database objects
        (e.g. tables, functions)
        """
        self.conn = psycopg2.connect(dbname=database,
                                     user=login,
                                     password=password)
        if not self.init_mode:
            return
        self._prepare_database()

    def _prepare_database(self):
        with self.conn.cursor() as cursor:
            with open("queries/drop.pgsql", "r") as f:
                cursor.execute(f.read())
            with open("queries/prepare_database.pgsql", "r") as f:
                cursor.execute(f.read())

    def leader(self, timestamp: int, password: str, member: int):
        """
        Add leader to database, if member is existing member, then
        validate his password, else create new one with given password

        this function can be called only in init mode
        """
        if not self.init_mode:
            raise Exception("unauthorized leader call."
                            " Application is running in non-init mode")
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_MEMBER,
                {
                    "member_id": member,
                    "password": password,
                    "timestamp": timestamp
                },
            )
            cursor.execute(queries.ADD_LEADER, {"member_id": member})
        return None

    def support(self, timestamp, member, password,
                action, project, authority=None):
        """
        Create support proposal for action, 
        authorized by member as in the leader function.
        """
        self._action(timestamp, member, password,
                     action, project, authority,
                     is_support=True)
        return None

    def protest(self, timestamp, member, password,
                action, project, authority=None):
        """
        Create protest proposal for action, 
        authorized by member as in the leader function.
        """
        self._action(timestamp, member, password,
                     action, project, authority,
                     is_support=False,)
        return None

    def _action(self, timestamp: int, member: int, password: str,
                action: int, project: int, authority: typing.Optional[int],
                is_support: bool):

        self._handle_member(member, password, timestamp)

        result = self._search_for_project(project)
        if not result and not authority:
            raise Exception("Authority not provided")
        authority = result or authority

        if not result:
            self._add_authority(authority)
            self._add_project(project, authority)
        self._add_action(action, member, is_support, project)

    def _handle_member(self, member: int, password: str,
                       timestamp: int, should_be_leader: bool = False):
        if self._is_member(member):
            if not self._is_member_active(member, timestamp):
                raise Exception(f"member {member} is frozen")

            if not self._validate(member, password):
                raise Exception(f"password authorization failed for {member}")

            if not self._is_member_leader(member) and should_be_leader:
                raise Exception(f"member {member} shoud be leader")

            self._update_member_last_act(member, timestamp)
        else:
            if should_be_leader:
                raise Exception(f"leader with id {member} doesn't exist")
            self._add_member(timestamp, member, password)

    def _is_member(self, member: int) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.FIND_MEMBER, {"member_id": member})
            return bool(cursor.fetchall())

    def _is_member_active(self, member: int, timestamp: str) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.VALIDATE_ACTIVE_STATUS,
                {
                    "member_id": member,
                    "current_timestamp": timestamp
                },
            )
            return bool(cursor.fetchone()[0])

    def _update_member_last_act(self, member: int, timestamp: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.UPDATE_MEMBER_LAST_ACT,
                {
                    "member_id": member,
                    "timestamp": timestamp
                },
            )

    def _validate(self, member: int, password: str) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.VALIDATE_PASSWORD,
                           {
                               "password": password,
                               "member_id": member
                           })
            (result) = cursor.fetchone()
        return bool(result[0])

    def _is_member_leader(self, member: int):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.FIND_LEADER,
                           {
                               "member_id": member
                           })
            return bool(cursor.fetchone())

    def _add_member(self, timestamp: int, member: int, password: str):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_MEMBER,
                {
                    "member_id": member,
                    "password": password,
                    "timestamp": timestamp
                },
            )

    def _search_for_project(self, project: int) -> typing.Optional[int]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.FIND_PROJECT, {"project_id": project})
            result = cursor.fetchmany()
            if result:
                return result[0][0]
            else:
                return None

    def _add_action(self, action: int, member: int,
                    is_support: bool, project: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_ACTION,
                {
                    "action_id": action,
                    "owner_id": member,
                    "is_support": is_support,
                    "project_id": project,
                },
            )

    def _add_authority(self, authority: int):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_AUTHORITY, {"authority_id": authority})

    def _add_project(self, project: int, authority: int):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_PROJECT, {
                "project_id": project,
                "authority_id": authority
            })

    def upvote(self, timestamp: int, member: int,
               password: str, action: int):
        """
        Add vote for an action on behalf of member
        authorized as in the leader function
        """
        self._vote(timestamp, member, password, action, 1)
        return None

    def downvote(self, timestamp: int, member: int,
                 password: str, action: int):
        """
        Add vote against an action on behalf of member
        authorized as in the leader function
        """
        self._vote(timestamp, member, password, action, -1)
        return None

    def _vote(self, timestamp: int, member: int,
              password: str, action: int, value: int):
        self._handle_member(member, password, timestamp)
        count_name = {-1: "downvoted_count", 1: "upvoted_count"}
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_VOTE.format(count_name[value]), {
                "member_id": member,
                "action_id": action,
                "value": value
            })

    def actions(self, timestamp: int, member: int, password: str,
                type: str = None, project: int = None,
                authority: int = None) -> list:
        """
        Get votes.

        Can be filtered by type and by project or authority
        """
        if project and authority:
            raise Exception(
                "project and authority arguments can't be used together")
        self._handle_member(member, password, timestamp, should_be_leader=True)

        conds = " AND ".join(
            cond for cond, provided in
                [("support = %(is_support)s", type),
                 ("project_id = %(project_id)s", project),
                 ("authority_id = %(authority_id)s", authority)] if provided)

        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.SELECT_ACTIONS.format("WHERE" if conds else '', conds),
                {
                    "is_support": type == "support",
                    "project_id": project,
                    "authority_id": authority
                }
            )
            return list(map(list, cursor))

    def projects(self, timestamp: int, member: int,
                 password: str, authority: int = None) -> list:
        """
        Get projects.

        Can be filtered by authority
        """
        self._handle_member(member, password, timestamp, should_be_leader=True)

        cond = "WHERE authority_id=%(authority_id)s" if authority else ''
        with self.conn.cursor() as cursor:
            cursor.execute(queries.SELECT_PROJECTS.format(cond),
                           {
                               "authority_id": authority
                           })
            return list(map(list, cursor))

    def votes(self, timestamp: int, member: int, password: str,
              action: int = None, project: int = None) -> list:
        """
        Get votes.

        Can be filtered by action or by project
        """
        if action and project:
            raise Exception(
                "action and project arguments can't be used together")
        self._handle_member(member, password, timestamp, should_be_leader=True)

        conds = " AND ".join(
            cond for cond, provided in
                [("project_id = %(project_id)s", project),
                 ("action_id = %(action_id)s", action),
                 ("member_id = member.id", True)] if provided)

        with self.conn.cursor() as cursor:
            cursor.execute(queries.SELECT_VOTES.format(conds),
                           {
                               "project_id": project,
                               "action_id": action
                           })
            return list(map(list, cursor))

    def trolls(self, timestamp: int) -> list:
        """
        Get ranking of trolls.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(queries.SELECT_TROLLS,
                           {
                               "current_timestamp": timestamp
                           })
            return list(map(list, cursor))

    def close(self):
        """
        close connection to database
        """
        self.conn.close()
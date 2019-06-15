CREATE TABLE member (
  id int PRIMARY KEY,
  password text NOT NULL,
  upvoted_count int DEFAULT 0,
  downvoted_count int DEFAULT 0,
  last_act_time timestamp NOT NULL
);

CREATE TABLE leader (
  member_id int PRIMARY KEY,
  CONSTRAINT leader_id_member_id_fkey FOREIGN KEY (member_id)
    REFERENCES member (id)
);

CREATE TABLE authority (
  id int PRIMARY KEY
);


CREATE TABLE project (
  id int PRIMARY KEY,
  authority_id int NOT NULL,
  CONSTRAINT authority_id_fkey FOREIGN KEY (authority_id)
    REFERENCES authority (id)
);

CREATE TABLE action (
  id int PRIMARY KEY,
  owner_id int NOT NULL,
  support boolean NOT NULL,
  project_id int NOT NULL,
  CONSTRAINT owner_id_member_id_fkey FOREIGN KEY (owner_id)
      REFERENCES member (id),
  CONSTRAINT project_id_fkey FOREIGN KEY (project_id)
      REFERENCES project (id)
);

CREATE TABLE member_votes_for (
  member_id int,
  action_id int,
  value int CHECK (value = -1 OR value = 1),
  PRIMARY KEY (member_id, action_id),
  CONSTRAINT member_id_fk FOREIGN KEY (member_id)
      REFERENCES member (id),
  CONSTRAINT action_id_fkey FOREIGN KEY (action_id)
      REFERENCES action (id)
);

CREATE TABLE all_id (
  id int PRIMARY KEY
);


CREATE OR REPLACE FUNCTION all_id_trigger_function()
  RETURNS trigger AS
$BODY$
BEGIN
  INSERT INTO all_id VALUES (NEW.id);
  RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER all_id_trigger AFTER INSERT
   ON member
   FOR EACH ROW
   EXECUTE PROCEDURE all_id_trigger_function();

CREATE TRIGGER all_id_trigger AFTER INSERT
   ON action
   FOR EACH ROW
   EXECUTE PROCEDURE all_id_trigger_function();

CREATE TRIGGER all_id_trigger AFTER INSERT
   ON authority
   FOR EACH ROW
   EXECUTE PROCEDURE all_id_trigger_function();

CREATE TRIGGER all_id_trigger AFTER INSERT
   ON project
   FOR EACH ROW
   EXECUTE PROCEDURE all_id_trigger_function();



CREATE ROLE app WITH encrypted password 'qwerty';
ALTER ROLE app WITH LOGIN;
GRANT CONNECT ON DATABASE student TO app;

GRANT INSERT, UPDATE, SELECT ON member, leader, authority, project, action, member_votes_for, all_id TO app;

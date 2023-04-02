-- Table: public.competitions

-- DROP TABLE IF EXISTS public.competitions;

CREATE TABLE IF NOT EXISTS public.competitions
(
    c_id integer NOT NULL DEFAULT 'nextval('competitions_c_id_seq'::regclass)',
    title character varying COLLATE pg_catalog."default" NOT NULL,
    query_type character varying COLLATE pg_catalog."default" NOT NULL,
    description character varying COLLATE pg_catalog."default" NOT NULL,
    schema character varying COLLATE pg_catalog."default" NOT NULL,
    solution character varying COLLATE pg_catalog."default" NOT NULL,
    host_user_id integer NOT NULL DEFAULT 'nextval('competitions_host_user_id_seq'::regclass)',
    due_date timestamp without time zone NOT NULL,
    metric integer NOT NULL,
    CONSTRAINT competitions_pkey PRIMARY KEY (c_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.competitions
    OWNER to postgres;

-- Table: public.users

-- DROP TABLE IF EXISTS public.users;

CREATE TABLE IF NOT EXISTS public.users
(
    user_id integer NOT NULL DEFAULT 'nextval('users_user_id_seq'::regclass)',
    email character varying COLLATE pg_catalog."default" NOT NULL,
    username character varying COLLATE pg_catalog."default" NOT NULL,
    password character varying COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT users_pkey PRIMARY KEY (user_id, email, username),
    CONSTRAINT users_user_id_key UNIQUE (user_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.users
    OWNER to postgres;
    
-- Table: public.submissions

-- DROP TABLE IF EXISTS public.submissions;

CREATE TABLE IF NOT EXISTS public.submissions
(
    c_id integer NOT NULL DEFAULT 'nextval('submissions_c_id_seq'::regclass)',
    user_id integer NOT NULL DEFAULT 'nextval('submissions_user_id_seq'::regclass)',
    attempt_number integer NOT NULL,
    submission character varying COLLATE pg_catalog."default" NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    planning_time double precision NOT NULL,
    execution_time double precision NOT NULL,
    total_time double precision NOT NULL,
    query_complexity double precision NOT NULL,
    CONSTRAINT submissions_pkey PRIMARY KEY (c_id, user_id, attempt_number),
    CONSTRAINT submissions_c_id_fkey FOREIGN KEY (c_id)
        REFERENCES public.competitions (c_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT submissions_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (user_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.submissions
    OWNER to postgres;
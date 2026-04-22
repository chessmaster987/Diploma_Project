--
-- PostgreSQL database dump
--

-- Dumped from database version 15.0
-- Dumped by pg_dump version 15.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: attendance_info(date, date, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.attendance_info(start_date date, end_date date, user_login character varying) RETURNS TABLE(attendance_id integer, student_login character varying, date_and_time timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
		attendance.attendance_number as attendance_id,
		attendance.login as student_login,
		attendance.timestamp as date_and_time
    FROM
        attendance
	WHERE 
		attendance.login = user_login AND
        DATE(attendance.timestamp) >= start_date AND
        DATE(attendance.timestamp) <= end_date
	--GROUP BY
    --   attendance.attendance_number;
	ORDER BY
        attendance.timestamp;
END;
$$;


ALTER FUNCTION public.attendance_info(start_date date, end_date date, user_login character varying) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: attendance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attendance (
    attendance_number integer NOT NULL,
    login character varying(30),
    "timestamp" timestamp without time zone
);


ALTER TABLE public.attendance OWNER TO postgres;

--
-- Name: attendance_attendance_number_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attendance_attendance_number_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.attendance_attendance_number_seq OWNER TO postgres;

--
-- Name: attendance_attendance_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attendance_attendance_number_seq OWNED BY public.attendance.attendance_number;


--
-- Name: classes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classes (
    class_number integer NOT NULL,
    class_name character varying(20) NOT NULL
);


ALTER TABLE public.classes OWNER TO postgres;

--
-- Name: classes_class_number_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classes_class_number_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.classes_class_number_seq OWNER TO postgres;

--
-- Name: classes_class_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classes_class_number_seq OWNED BY public.classes.class_number;


--
-- Name: login; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.login (
    login_number integer NOT NULL,
    username character varying(30) NOT NULL,
    password character varying(30) NOT NULL,
    role character varying(30) NOT NULL
);


ALTER TABLE public.login OWNER TO postgres;

--
-- Name: login_login_number_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.login_login_number_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.login_login_number_seq OWNER TO postgres;

--
-- Name: login_login_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.login_login_number_seq OWNED BY public.login.login_number;


--
-- Name: student; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student (
    login character varying(30) NOT NULL,
    full_name character varying(30) NOT NULL,
    class_number integer NOT NULL,
    year_of_grade integer NOT NULL,
    CONSTRAINT check_year_of_grade CHECK (((year_of_grade >= 1) AND (year_of_grade <= 6))),
    CONSTRAINT student_full_name_check CHECK (((full_name)::text ~ '^[a-zA-Zа-яА-Я\s]'::text))
);


ALTER TABLE public.student OWNER TO postgres;

--
-- Name: attendance attendance_number; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance ALTER COLUMN attendance_number SET DEFAULT nextval('public.attendance_attendance_number_seq'::regclass);


--
-- Name: classes class_number; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes ALTER COLUMN class_number SET DEFAULT nextval('public.classes_class_number_seq'::regclass);


--
-- Name: login login_number; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.login ALTER COLUMN login_number SET DEFAULT nextval('public.login_login_number_seq'::regclass);


--
-- Name: attendance attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_pkey PRIMARY KEY (attendance_number);


--
-- Name: classes classes_class_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_class_name_key UNIQUE (class_name);


--
-- Name: classes classes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_pkey PRIMARY KEY (class_number);


--
-- Name: login login_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT login_pkey PRIMARY KEY (login_number);


--
-- Name: login login_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT login_username_key UNIQUE (username);


--
-- Name: student student_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student
    ADD CONSTRAINT student_pkey PRIMARY KEY (login);


--
-- Name: attendance attendance_login_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attendance
    ADD CONSTRAINT attendance_login_fkey FOREIGN KEY (login) REFERENCES public.student(login) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: student student_class_number_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student
    ADD CONSTRAINT student_class_number_fkey FOREIGN KEY (class_number) REFERENCES public.classes(class_number) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--


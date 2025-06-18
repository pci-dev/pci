--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    email character varying(512),
    password character varying(512),
    first_name character varying(128),
    last_name character varying(128),
    orcid character varying(16),
    no_orcid boolean DEFAULT false NOT NULL,
    uploaded_picture character varying(512),
    picture_data bytea,
    laboratory character varying(512),
    institution character varying(512),
    city character varying(512),
    country character varying(512),
    thematics character varying(1024) DEFAULT '||'::character varying,
    cv text,
    keywords character varying(1024),
    email_options character varying(1024) DEFAULT '|Email to reviewers|Email to authors|'::character varying,
    website character varying(4096),
    alerts character varying(512) DEFAULT 'Weekly'::character varying,
    last_alert timestamp without time zone,
    registration_datetime timestamp without time zone DEFAULT statement_timestamp(),
    deleted boolean DEFAULT false NOT NULL,
    ethical_code_approved boolean DEFAULT false NOT NULL,
    recover_email character varying(512),
    recover_email_key character varying(512),
    new_article_cache jsonb,
    user_title character varying(10) DEFAULT ''::character varying
    reset_password_key character varying(512),

    sso_id character varying(512),
    action_token character varying(512),
    last_password_change timestamp without time zone
);


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;

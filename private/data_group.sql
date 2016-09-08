--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.14
-- Dumped by pg_dump version 9.3.14
-- Started on 2016-09-08 15:16:34 CEST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- TOC entry 2144 (class 0 OID 87778616)
-- Dependencies: 177
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: piry
--

INSERT INTO auth_group (id, role, description) VALUES (2, 'recommender', '');
INSERT INTO auth_group (id, role, description) VALUES (3, 'manager', '');
INSERT INTO auth_group (id, role, description) VALUES (4, 'administrator', '');
INSERT INTO auth_group (id, role, description) VALUES (5, 'developper', '');


--
-- TOC entry 2149 (class 0 OID 0)
-- Dependencies: 176
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: piry
--

SELECT pg_catalog.setval('auth_group_id_seq', 7, true);


-- Completed on 2016-09-08 15:16:34 CEST

--
-- PostgreSQL database dump complete
--


--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.14
-- Dumped by pg_dump version 9.3.14
-- Started on 2016-09-08 15:13:00 CEST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- TOC entry 2146 (class 0 OID 87782589)
-- Dependencies: 198
-- Data for Name: t_status_article; Type: TABLE DATA; Schema: public; Owner: piry
--

INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (1, 'Cancelled', 'default', NULL);
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (2, 'Recommended', 'success', NULL);
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (5, 'Pre-recommended', 'good', NULL);
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (3, 'Under consideration', 'info', NULL);
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (6, 'Rejected', 'default', NULL);
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (4, 'Awaiting revision', 'warning', '');
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (9, 'Awaiting consideration', 'warning', 'Submitted by a user and approaved by managing board. Waiting for a recommender.');
INSERT INTO t_status_article (id, status, color_class, explaination) VALUES (8, 'Pending', 'danger', 'Submitted by a user and waiting for managing board approval');


--
-- TOC entry 2151 (class 0 OID 0)
-- Dependencies: 197
-- Name: t_status_article_id_seq; Type: SEQUENCE SET; Schema: public; Owner: piry
--

SELECT pg_catalog.setval('t_status_article_id_seq', 9, true);


-- Completed on 2016-09-08 15:13:00 CEST

--
-- PostgreSQL database dump complete
--


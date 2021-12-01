--
-- PostgreSQL database dump
--

-- Dumped from database version 10.17 (Ubuntu 10.17-1.pgdg18.04+1)
-- Dumped by pg_dump version 10.17 (Ubuntu 10.17-1.pgdg18.04+1)

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
-- Data for Name: t_status_article; Type: TABLE DATA; Schema: public; Owner: pci_admin
--

COPY public.t_status_article (id, status, color_class, explaination, priority_level) FROM stdin;
1	Cancelled	default	Request cancelled by the author	C
2	Recommended	success	This article is recommended by PCi. The review process is publicly available.	C
3	Under consideration	info	Accepted by a Recommender	B
5	Pre-recommended	good	Recommended by the Recommender; awaiting confirmation by Managing board	A
6	Rejected	default	This article have been rejected by the recommendation board.	C
8	Pending	danger	Submitted by a user and waiting for managing board approval	A
9	Awaiting consideration	warning	Submitted by a user and approaved by managing board. Waiting for a recommender.	A
4	Awaiting revision	warning	A revision was requested to the authors.	B
10	Not considered	default	No recommender considered this article in due time.	C
11	Pre-rejected	warning	Rejected by the Recommender; awaiting confirmation by Managing board	A
12	Pre-revision	warning	Revision asked by the recommender; awaiting confirmation by Managing board	A
13	Scheduled submission pending	danger	Scheduled submission waiting for Managing board approval	A
14	Scheduled submission under consideration	info	Scheduled submission accepted by Recommender	A
15	Pending-survey	good	Submitted by user; awaiting survey submission	A
\.


--
-- Name: t_status_article_id_seq; Type: SEQUENCE SET; Schema: public; Owner: pci_admin
--

SELECT pg_catalog.setval('public.t_status_article_id_seq', 12, true);


--
-- PostgreSQL database dump complete
--


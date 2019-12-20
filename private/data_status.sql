
--
-- TOC entry 3115 (class 0 OID 18963)
-- Dependencies: 247
-- Data for Name: t_status_article; Type: TABLE DATA; Schema: public; Owner: piry
--

TRUNCATE public.t_status_article;
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (5, 'Pre-recommended', 'good', '', 'A');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (8, 'Pending', 'danger', '', 'A');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (9, 'Awaiting consideration', 'warning', '', 'A');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (3, 'Under consideration', 'info', '', 'B');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (4, 'Awaiting revision', 'warning', '', 'B');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (1, 'Cancelled', 'default', '', 'C');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (2, 'Recommended', 'success', '', 'C');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (6, 'Rejected', 'default', '', 'C');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (10, 'Not considered', 'default', '', 'C');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (35, 'Pre-rejected', 'default', 'Rejected by the Recommender; awaiting confirmation by Managing board', 'A');
INSERT INTO public.t_status_article (id, status, color_class, explaination, priority_level) VALUES (36, 'Pre-revision', 'warning', 'Revision asked by the recommender; awaiting confirmation by Managing board', 'A');


--
-- TOC entry 3123 (class 0 OID 0)
-- Dependencies: 248
-- Name: t_status_article_id_seq; Type: SEQUENCE SET; Schema: public; Owner: piry
--

SELECT pg_catalog.setval('public.t_status_article_id_seq', 40, true);


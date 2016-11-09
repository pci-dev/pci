# -*- coding: utf-8 -*-

import re
import copy
import datetime
from dateutil.relativedelta import *

from gluon.contrib.markdown import WIKI
from common import *
from helper import *


# frequently used constants
csv = False # no export allowed
expClass = None #dict(csv_with_hidden_cols=False, csv=False, html=False, tsv_with_hidden_cols=False, json=False, xml=False)
trgmLimit = myconf.take('config.trgm_limit') or 0.4




@auth.requires(auth.has_membership(role='recommender'))
def new_submission():
	myText = DIV(
				getText(request, auth, db, '#NewRecommendationInfo'),
				DIV(
					A(current.T("Recommend a postprint"), 
						_title=T('published articles'),
						_href=URL('recommender', 'direct_submission', user_signature=True), 
						_class="btn btn-info pci-panelButton"),
					_style='margin-top:16px; text-align:center;',
				)
				
			)
	response.view='default/info.html'
	return dict(
		myText = myText,
	)





@auth.requires(auth.has_membership(role='recommender'))
def search_reviewers():
	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_reviewers = temp_db.define_table('qy_reviewers',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		Field('first_name', type='string', length=128, label=T('First name')),
		Field('last_name', type='string', length=128, label=T('Last name')),
		Field('email', type='string', length=512, label=T('email')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
		Field('city', type='string', label=T('City')),
		Field('country', type='string', label=T('Country')),
		Field('laboratory', type='string', label=T('Laboratory')),
		Field('institution', type='string', label=T('Institution')),
		Field('thematics', type='list:string', label=T('Thematic fields')),
		Field('roles', type='string', length=1024, label=T('Roles')),
	)
	temp_db.qy_reviewers.email.represent = lambda text, row: A(text, _href='mailto:'+text)
	myVars = request.vars
	qyKw = ''
	qyTF = []
	excludeList = []
	myGoal = '4review' # default
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (myVar == 'myGoal'):
			myGoal = myValue
		elif (myVar == 'exclude'):
			excludeList = map(int, myValue.split(','))
		elif (re.match('^qy_', myVar) and myValue=='on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars, allowBlank=True)
	filtered = db.executesql('SELECT * FROM search_reviewers(%s, %s, %s);', placeholders=[qyTF, qyKwArr, excludeList], as_dict=True)
	for fr in filtered:
		qy_reviewers.insert(**fr)
			
	temp_db.qy_reviewers._id.readable = False
	temp_db.qy_reviewers.uploaded_picture.readable = False
	links = []
	if 'recommId' in request.vars:
		recommId = request.vars['recommId']
		links.append(  dict(header=T('Days since last recommendation'), body=lambda row: db.v_last_recommendation[row.id].days_since_last_recommendation)  )
		if myGoal == '4review':
			links.append(  dict(header=T('Select'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommId, myGoal)) )
			#myTitle = T('Search for reviewers')
			myTitle=getTitle(request, auth, db, '#RecommenderSearchReviewersTitle')
			myText=getText(request, auth, db, '#RecommenderSearchReviewersText')
			myHelp=getHelp(request, auth, db, '#RecommenderSearchReviewers')
		elif myGoal == '4press':
			links.append(  dict(header=T('Propose contribution'), body=lambda row: mkSuggestReviewToButton(auth, db, row, recommId, myGoal))  )
			#myTitle = T('Search for collaborators')
			myTitle=getTitle(request, auth, db, '#RecommenderSearchCollaboratorsTitle')
			myText=getText(request, auth, db, '#RecommenderSearchCollaboratorsText')
			myHelp=getHelp(request, auth, db, '#RecommenderSearchCollaborators')
	temp_db.qy_reviewers.num.readble=False
	temp_db.qy_reviewers.score.readble=False
	grid = SQLFORM.grid( qy_reviewers
		,editable = False,deletable = False,create = False,details=False,searchable=False
		,maxtextlength=250,paginate=100
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_reviewers.num, temp_db.qy_reviewers.score, temp_db.qy_reviewers.uploaded_picture, temp_db.qy_reviewers.first_name, temp_db.qy_reviewers.last_name, temp_db.qy_reviewers.email, temp_db.qy_reviewers.laboratory, temp_db.qy_reviewers.institution, temp_db.qy_reviewers.city, temp_db.qy_reviewers.country, temp_db.qy_reviewers.thematics]
		,links=links
		,orderby=temp_db.qy_reviewers.num
		,args=request.args
	)
	response.view='default/myLayout.html'
	return dict(
				myHelp=myHelp,
				myTitle=myTitle,
				myText=myText,
				#myBackButton=mkBackButton(),
				searchForm=searchForm, 
				grid=grid, 
			 )



def mkViewEditArticleRecommenderButton(auth, db, row):
	return A(SPAN(current.T('View'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='article_details', vars=dict(articleId=row.id), user_signature=True), _class='button', _title=current.T('View and accept or decline recommendation'))


@auth.requires(auth.has_membership(role='recommender'))
def my_awaiting_articles():
	query = ( 
				(db.t_articles.status == 'Awaiting consideration')
			  & (db.t_articles._id == db.t_suggested_recommenders.article_id) 
			  & (db.t_suggested_recommenders.suggested_recommender_id == auth.user_id)
		)
	db.t_articles.user_id.writable = False
	#db.t_articles.doi.represent = lambda text, row: mkDOI(text)
	db.t_articles.auto_nb_recommendations.readable = False
	#db.t_articles.status.readable = False
	db.t_articles.status.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	if len(request.args) == 0: # we are in grid
		#db.t_articles.doi.readable = False
		#db.t_articles.authors.readable = False
		#db.t_articles.title.readable = False
		db.t_articles.upload_timestamp.represent = lambda t, row: mkLastChange(t)
		db.t_articles.last_status_change.represent = lambda t, row: mkLastChange(t)
		db.t_articles._id.readable = True
		db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		db.t_articles._id.label = T('Article')
		db.t_articles.abstract.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	else: # we are in grid's form
		db.t_articles._id.readable = False
		db.t_articles.abstract.represent=lambda text, row: WIKI(text)
	grid = SQLFORM.grid( query
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[db.t_articles._id, db.t_articles.abstract, db.t_articles.thematics, db.t_articles.keywords, db.t_articles.user_id, db.t_articles.upload_timestamp, db.t_articles.last_status_change, db.t_articles.auto_nb_recommendations, db.t_articles.status]
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T(''), body=lambda row: mkViewEditArticleRecommenderButton(auth, db, row)),
		]
		,orderby=~db.t_articles.upload_timestamp
	)
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#RecommenderSuggestedArticles'),
				myText=getText(request, auth, db, '#RecommenderSuggestedArticlesText'),
				myTitle=getTitle(request, auth, db, '#RecommenderSuggestedArticlesTitle'),
				grid=grid, 
			)



# Common function for articles needing attention
@auth.requires(auth.has_membership(role='recommender'))
def _awaiting_articles(myVars):
	# We use a trick (memory table) for builing a grid from executeSql ; see: http://stackoverflow.com/questions/33674532/web2py-sqlform-grid-with-executesql
	temp_db = DAL('sqlite:memory')
	qy_art = temp_db.define_table('qy_art',
		Field('id', type='integer'),
		Field('num', type='integer'),
		Field('score', type='double', label=T('Score'), default=0),
		Field('title', type='text', label=T('Title')),
		Field('authors', type='text', label=T('Authors')),
		Field('article_source', type='string', label=T('Source')),
		Field('doi', type='string', label=T('DOI')),
		Field('abstract', type='text', label=T('Abstract')),
		Field('upload_timestamp', type='datetime', default=request.now, label=T('Submission date/time')),
		Field('thematics', type='string', length=1024, label=T('Thematic fields')),
		Field('keywords', type='text', label=T('Keywords')),
		Field('auto_nb_recommendations', type='integer', label=T('Rounds of reviews'), default=0),
		Field('status', type='string', length=50, default='Pending', label=T('Status')),
		Field('last_status_change', type='datetime', default=request.now, label=T('Last status change')),
		Field('uploaded_picture', type='upload', uploadfield='picture_data', label=T('Picture')),
	)
	myVars = request.vars
	qyKw = ''
	qyTF = []
	for myVar in myVars:
		if isinstance(myVars[myVar], list):
			myValue = (myVars[myVar])[1]
		else:
			myValue = myVars[myVar]
		if (myVar == 'qyKeywords'):
			qyKw = myValue
		elif (re.match('^qy_', myVar) and myValue=='on'):
			qyTF.append(re.sub(r'^qy_', '', myVar))
	qyKwArr = qyKw.split(' ')
	searchForm =  mkSearchForm(auth, db, myVars, allowBlank=True)
	filtered = db.executesql('SELECT * FROM search_articles(%s, %s, %s, %s, %s);', placeholders=[qyTF, qyKwArr, 'Awaiting consideration', trgmLimit, True], as_dict=True)
	for fr in filtered:
		qy_art.insert(**fr)
	
	temp_db.qy_art.auto_nb_recommendations.readable = False
	temp_db.qy_art.uploaded_picture.represent = lambda text,row: (IMG(_src=URL('default', 'download', args=text), _width=100)) if (text is not None and text != '') else ('')
	if len(request.args)==0: # in grid
		temp_db.qy_art._id.readable = True
		temp_db.qy_art._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
		temp_db.qy_art._id.label = T('Article')
		temp_db.qy_art.title.readable = False
		temp_db.qy_art.authors.readable = False
		#temp_db.qy_art.status.readable = False
		temp_db.qy_art.article_source.readable = False
		temp_db.qy_art.upload_timestamp.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.last_status_change.represent = lambda t, row: mkLastChange(t)
		temp_db.qy_art.abstract.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		temp_db.qy_art.status.represent = lambda text, row: mkStatusDiv(auth, db, row.status)
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
	else:
		temp_db.qy_art._id.readable = False
		temp_db.qy_art.num.readable = False
		temp_db.qy_art.score.readable = False
		temp_db.qy_art.doi.represent = lambda text, row: mkDOI(text)
		temp_db.qy_art.abstract.represent = lambda text, row: WIKI(text or '')
		
	grid = SQLFORM.grid(temp_db.qy_art
		,searchable=False,editable=False,deletable=False,create=False,details=False
		,maxtextlength=250,paginate=10
		,csv=csv,exportclasses=expClass
		,fields=[temp_db.qy_art.num, temp_db.qy_art.score, temp_db.qy_art.uploaded_picture, temp_db.qy_art._id, temp_db.qy_art.title, temp_db.qy_art.authors, temp_db.qy_art.article_source, temp_db.qy_art.abstract, temp_db.qy_art.thematics, temp_db.qy_art.keywords, temp_db.qy_art.upload_timestamp, temp_db.qy_art.last_status_change, temp_db.qy_art.status, temp_db.qy_art.auto_nb_recommendations]
		,links=[
			dict(header=T('Suggested recommenders'), body=lambda row: (db.v_suggested_recommenders[row.id]).suggested_recommenders),
			dict(header=T(''), body=lambda row: mkViewEditArticleRecommenderButton(auth, db, row)),
		]
		,orderby=temp_db.qy_art.num
	)
	response.view='default/myLayout.html'
	return dict(
				#myTitle=T('Articles requiring a recommender'), 
				myTitle=getTitle(request, auth, db, '#RecommenderAwaitingArticlesTitle'),
				myText=getText(request, auth, db, '#RecommenderAwaitingArticlesText'),
				searchForm=searchForm, 
				grid=grid, 
			)



@auth.requires(auth.has_membership(role='recommender'))
def fields_awaiting_articles():
	resu = _awaiting_articles(request.vars)
	resu['myHelp'] = getHelp(request, auth, db, '#RecommenderArticlesAwaitingRecommendation:InMyFields')
	resu['myText'] = getText(request, auth, db, '#RecommenderArticlesAwaitingRecommendationText:InMyFields')
	return resu



@auth.requires(auth.has_membership(role='recommender'))
def all_awaiting_articles():
	myVars = request.vars
	for thema in db().select(db.t_thematics.ALL, orderby=db.t_thematics.keyword):
		myVars['qy_'+thema.keyword] = 'on'
	resu = _awaiting_articles(myVars)
	resu['myHelp'] = getHelp(request, auth, db, '#RecommenderArticlesAwaitingRecommendation:All')
	resu['myText'] = getText(request, auth, db, '#RecommenderArticlesAwaitingRecommendationText:All')
	return resu




@auth.requires(auth.has_membership(role='recommender'))
def article_details():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	amIAllowed = db( (db.t_recommendations.article_id == articleId) ).count() == 0
	if not(amIAllowed):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		if printable:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
				DIV(
					DIV(I(myconf.take('app.longname')+': ')+T(art.status), _class='pci-ArticleText printable'),
					_class='pci-ArticleHeaderIn printable'
				))
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html' #OK
		else:
			myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
				DIV(
					DIV(I(myconf.take('app.longname'))+BR()+T(art.status), _class='pci-ArticleText'),
					_class='pci-ArticleHeaderIn'
				))
			myUpperBtn = A(SPAN(T('Printable page'), _class='pci-ArticleTopButton buttontext btn btn-info'), 
				_href=URL(c="user", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderArticlesRequiringRecommender'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)



@auth.requires(auth.has_membership(role='recommender'))
def accept_new_article_to_recommend():
	myTitle = getTitle(request, auth, db, '#AcceptPreprintInfoTitle')
	myText = DIV(
			getText(request, auth, db, '#AcceptPreprintInfoText'),
			DIV(
				A(current.T("Yes, I will consider this preprint for recommendation"), 
					_href=URL('recommender', 'do_accept_new_article_to_recommend', vars=request.vars, user_signature=True), 
					_class="btn btn-success pci-panelButton"),
				_style='margin-top:16px; text-align:center;',
			)
		)
	response.view='default/info.html' #OK
	return dict(
		myText=myText,
		myTitle=myTitle,
	)



@auth.requires(auth.has_membership(role='recommender'))
def do_accept_new_article_to_recommend():
	articleId = request.vars['articleId']
	article = db.t_articles[articleId]
	if article.status == 'Awaiting consideration':
		recommId = db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=article.doi)
		article.status = 'Under consideration'
		article.update_record()
		#redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))
		redirect(URL('reviewers', vars=dict(recommId=recommId), user_signature=True)) #TODO #WARNING # basculer sur add reviewer
	else:
		session.flash = T('Article no more available', lazy=False)
		redirect('my_awaiting_articles')




@auth.requires(auth.has_membership(role='recommender'))
def recommend_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		recomm.is_closed=True
		recomm.recommendation_state = 'Recommended'
		recomm.update_record()
		art = db.t_articles[recomm.article_id]
		art.status = 'Pre-recommended'
		art.update_record()
		#db.commit()
		redirect(URL(c='recommender', f='recommendations', vars=dict(articleId=recomm.article_id), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def reject_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		recomm.is_closed=True
		recomm.recommendation_state = 'Rejected'
		recomm.update_record()
		art = db.t_articles[recomm.article_id]
		art.status = 'Rejected'
		art.update_record()
		db.commit()
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def revise_article():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		# Do not close recommendation due to reply
		art = db.t_articles[recomm.article_id]
		art.status = 'Awaiting revision'
		art.update_record()
		recomm.recommendation_state = 'Awaiting revision'
		recomm.update_record()
		db.commit()
		redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def decline_new_article_to_recommend():
	articleId = request.vars['articleId']
	if articleId is not None:
		#NOTE: No security hole as only logged user can be deleted
		db(db.t_suggested_recommenders.article_id == articleId and db.t_suggested_recommenders.suggested_recommender_id == auth.user_id).delete()
	redirect(URL('my_awaiting_articles', user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def suggest_review_to():
	reviewerId = request.vars['reviewerId']
	if reviewerId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		db.t_reviews.update_or_insert(recommendation_id=recommId, reviewer_id=reviewerId)
		redirect(URL('reviewers', vars=dict(recommId=recommId), user_signature=True))



@auth.requires(auth.has_membership(role='recommender'))
def suggest_collaboration_to():
	reviewerId = request.vars['reviewerId']
	if reviewerId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		db.t_press_reviews.update_or_insert(recommendation_id=recommId, contributor_id=reviewerId)
		redirect(URL('my_recommendations', vars=dict(pressReviews=True), user_signature=True))



def mkViewEditRecommendationsRecommenderButton(auth, db, row):
	return A(SPAN(current.T('Check & Edit'), _class='buttontext btn btn-default pci-button'), _target="_blank", _href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.article_id), user_signature=True), _class='button', _title=current.T('View and/or edit article'))

@auth.requires(auth.has_membership(role='recommender'))
def my_recommendations():
	isPress = ( ('pressReviews' in request.vars) and (request.vars['pressReviews']=='True') )
	if isPress:
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == True)
			)
		#myTitle = T('Your recommendations of reviewed articles')
		myTitle=getTitle(request, auth, db, '#RecommenderMyRecommendationsPostprintTitle')
		myText=getText(request, auth, db, '#RecommenderMyRecommendationsPostprintText')
		fields = [db.t_articles.uploaded_picture, db.t_recommendations._id, db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed]#, db.t_recommendations.recommendation_title]#, db.t_recommendations.recommendation_comments]
		links = [
				dict(header=T('Co-recommenders'), body=lambda row: mkSollicitedPress(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''),             body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
	else:
		query = ( (db.t_recommendations.recommender_id == auth.user_id) 
				& (db.t_recommendations.article_id == db.t_articles.id) 
				& (db.t_articles.already_published == False)
				#& (db.t_recommendations.is_closed == False)
			)
		#myTitle = T('Your recommendations of prereview articles')
		myTitle=getTitle(request, auth, db, '#RecommenderMyRecommendationsPreprintTitle')
		myText=getText(request, auth, db, '#RecommenderMyRecommendationsPreprintText')
		fields = [db.t_articles.uploaded_picture, db.t_recommendations._id, db.t_recommendations.article_id, db.t_articles.status, db.t_recommendations.doi, db.t_recommendations.recommendation_timestamp, db.t_recommendations.last_change, db.t_recommendations.is_closed]#, db.t_recommendations.recommendation_title]#, db.t_recommendations.recommendation_comments]
		links = [
				dict(header=T('Sollicited reviewers'), body=lambda row: mkSollicitedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Declined reviews'),   body=lambda row:   mkDeclinedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Ongoing reviews'),    body=lambda row:    mkOngoingRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T('Terminated reviews'),     body=lambda row:     mkClosedRev(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''),                   body=lambda row: mkViewEditRecommendationsRecommenderButton(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
			]
		
	db.t_recommendations.recommender_id.writable = False
	db.t_recommendations.doi.writable = False
	db.t_recommendations.article_id.readable = False
	db.t_recommendations.article_id.writable = False
	db.t_recommendations._id.readable = True
	db.t_recommendations._id.label = T('Recommendation')
	db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	#db.t_recommendations.is_press_review.writable = False
	#db.t_recommendations.is_press_review.readable = False
	#db.t_recommendations.reply.writable = False
	#db.t_recommendations.reply.readable=False
	db.t_recommendations.is_closed.readable = False
	db.t_recommendations.is_closed.writable = False
	db.t_recommendations.recommendation_timestamp.label = T('Last change')
	db.t_recommendations.recommendation_timestamp.represent = lambda text, row: mkLastChange(row.t_recommendations.recommendation_timestamp) if 't_recommendations' in row else mkElapsed(row.recommendation_timestamp)
	db.t_recommendations.article_id.represent = lambda aid, row: mkArticleCellNoRecomm(auth, db, db.t_articles[aid])
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	db.t_recommendations.doi.readable=False
	db.t_recommendations.last_change.readable=False
	db.t_recommendations.recommendation_comments.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
	grid = SQLFORM.grid( query
		,searchable=False, create=False, deletable=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=fields
		,links=links
		,orderby=~db.t_recommendations.last_change
	)
	response.view='default/myLayout.html'
	return dict(
				#myBackButton=mkBackButton(), 
				myHelp = getHelp(request, auth, db, '#RecommenderMyRecommendations'),
				myTitle=myTitle, 
				myText=myText,
				grid=grid, 
			 )


@auth.requires(auth.has_membership(role='recommender'))
def process_opinion():
	if 'recommender_opinion' in request.vars and 'recommId' in request.vars:
		ro = request.vars['recommender_opinion']
		rId = request.vars['recommId']
		if ro == 'do_recommend': 
			redirect(URL(c='recommender', f='recommend_article', vars=dict(recommId=rId), user_signature=True))
		elif ro == 'do_revise': 
			redirect(URL(c='recommender', f='revise_article', vars=dict(recommId=rId), user_signature=True))
		elif ro == 'do_reject': 
			redirect(URL(c='recommender', f='reject_article', vars=dict(recommId=rId), user_signature=True))
	redirect(URL('my_recommendations', vars=dict(pressReviews=False), user_signature=True))




@auth.requires(auth.has_membership(role='recommender'))
def direct_submission():
	db.t_articles.user_id.default = None
	db.t_articles.user_id.writable = False
	db.t_articles.status.default = 'Under consideration'
	db.t_articles.status.writable = False
	db.t_articles.already_published.readable = False
	db.t_articles.already_published.writable = False
	db.t_articles.already_published.default = True
	myScript = """jQuery(document).ready(function(){
					
					if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
						jQuery('#t_articles_uploaded_picture').prop('disabled', false);
					} else {
						jQuery('#t_articles_uploaded_picture').prop('disabled', true);
					}
					jQuery('#t_articles_picture_rights_ok').change(function(){
								if(jQuery('#t_articles_picture_rights_ok').prop('checked')) {
									jQuery('#t_articles_uploaded_picture').prop('disabled', false);
								} else {
									jQuery('#t_articles_uploaded_picture').prop('disabled', true);
									jQuery('#t_articles_uploaded_picture').val('');
								}
					});
				});
	"""
	fields = ['title', 'authors', 'article_source', 'doi', 'picture_rights_ok', 'uploaded_picture', 'abstract', 'thematics', 'keywords', 'picture_data']
	form = SQLFORM( db.t_articles, fields=fields, keepvalues=True )
	if form.process().accepted:
		articleId=form.vars.id
		recommId = db.t_recommendations.insert(article_id=articleId, recommender_id=auth.user_id, doi=form.vars.doi, recommendation_state='Recommended')
		redirect(URL(f='add_contributor', vars=dict(recommId=recommId), user_signature=True))
	response.view='default/myLayout.html'
	return dict(
				myHelp=getHelp(request, auth, db, '#RecommenderDirectSubmission'),
				#myBackButton=mkBackButton(),
				myTitle=getTitle(request, auth, db, '#RecommenderDirectSubmissionTitle'),
				myText=getText(request, auth, db, '#RecommenderDirectSubmissionText'),
				form=form, 
				myFinalScript = SCRIPT(myScript),
			 )



@auth.requires(auth.has_membership(role='recommender'))
def recommendations():
	printable = 'printable' in request.vars
	articleId = request.vars['articleId']
	art = db.t_articles[articleId]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable'))
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	amIAllowed = db(
					(
						(db.t_recommendations.recommender_id == auth.user_id)
					  | ( (db.t_press_reviews.contributor_id == auth.user_id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id) )
					)
				  & (db.t_recommendations.article_id == articleId) 
			).count() > 0
	if not(amIAllowed):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		if printable:
			if art.status == 'Recommended':
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
						DIV(
							DIV(T('Recommended article'), _class='pci-ArticleText'),
							_class='pci-ArticleHeaderIn recommended printable'
						))
			else:
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/background.png')),
					DIV(
						DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn printable'
					))
			myUpperBtn = ''
			response.view='default/recommended_article_printable.html' #OK
		else:
			if art.status == 'Recommended':
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
					DIV(
						DIV(T('Recommended article'), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn recommended'
					))
			else:
				myTitle=DIV(IMG(_src=URL(r=request,c='static',f='images/small-background.png')),
					DIV(
						DIV(mkStatusBigDiv(auth, db, art.status), _class='pci-ArticleText'),
						_class='pci-ArticleHeaderIn'
					))
			myUpperBtn = A(SPAN(T('Printable page'), _class='buttontext btn btn-info'), 
				_href=URL(c="recommender", f='recommendations', vars=dict(articleId=articleId, printable=True), user_signature=True),
				_class='button')
			response.view='default/recommended_articles.html' #OK
		
		myContents = mkFeaturedArticle(auth, db, art, printable, quiet=False)
		myContents.append(HR())
		
		response.title = (art.title or myconf.take('app.longname'))
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderOtherRecommendations'),
					myCloseButton=mkCloseButton(),
					myUpperBtn=myUpperBtn,
					statusTitle=myTitle,
					myContents=myContents,
				)



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reopen_review(ids):
	if auth.has_membership(role='manager'):
		for myId in ids:
			rev = db.t_reviews[myId]
			if rev.review_state != 'Under consideration':
				rev.review_state = 'Under consideration'
				rev.update_record()
	elif auth.has_membership(role='recommender'):
		for myId in ids:
			rev = db.t_reviews[myId]
			recomm = db.t_recommendations[rev.recommendation_id]
			if (recomm.recommender_id == auth.user_id) and not(rev.review_state == 'Under consideration'):
				rev.review_state = 'Under consideration'
				rev.update_record()
			




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviews():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if recomm == None:
		raise HTTP(404, "404: "+T('Unavailable'))
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		#myContents = mkRecommendationFormat(auth, db, recomm)
		db.t_reviews._id.readable = False
		db.t_reviews.recommendation_id.default = recommId
		db.t_reviews.recommendation_id.writable = False
		db.t_reviews.recommendation_id.readable = False
		db.t_reviews.reviewer_id.writable = False
		db.t_reviews.reviewer_id.default = auth.user_id
		db.t_reviews.reviewer_id.represent = lambda text,row: mkUserWithMail(auth, db, row.reviewer_id) if row else ''
		db.t_reviews.anonymously.default = True
		db.t_reviews.anonymously.writable = auth.has_membership(role='manager')
		db.t_reviews.review.writable = auth.has_membership(role='manager')
		db.t_reviews.review_state.writable = auth.has_membership(role='manager')
		db.t_reviews.review_state.represent = lambda text,row: mkReviewStateDiv(auth, db, text)
		
		if len(request.args)==0 or (len(request.args)==1 and request.args[0]=='auth_user'): # grid view
			selectable = [(T('Re-open selected reviews'), lambda ids: [reopen_review(ids)], 'class1')]
			db.t_reviews.review.represent = lambda text, row: DIV(WIKI(text or ''), _class='pci-div4wiki')
		else: # form view
			selectable = None
			db.t_reviews.review.represent = lambda text, row: WIKI(text or '')
		
		query = (db.t_reviews.recommendation_id == recommId)
		grid = SQLFORM.grid( query
			,details=True
			,editable=lambda row: auth.has_membership(role='manager') or (row.review_state!='Terminated' and row.reviewer_id is None)
			,deletable=auth.has_membership(role='manager')
			,create=False
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_reviews.recommendation_id, db.t_reviews.reviewer_id, db.t_reviews.anonymously, db.t_reviews.review, db.t_reviews.review_state]
			,selectable=selectable
		)
		
		# This script renames the "Add record" button
		myScript = SCRIPT("""$(function() { 
						$('span').filter(function(i) {
								return $(this).attr("title") ? $(this).attr("title").indexOf('"""+T("Add record to database")+"""') != -1 : false;
							})
							.each(function(i) {
								$(this).text('"""+T("Add a review")+"""').attr("title", '"""+T("Add a new review from scratch")+"""');
							});
						})""",
						_type='text/javascript')
		
		response.view='default/myLayout.html'
		return dict(
				myHelp = getHelp(request, auth, db, '#RecommenderArticleReviews'),
				myText=getText(request, auth, db, '#RecommenderArticleReviewsText'),
				myTitle=getTitle(request, auth, db, '#RecommenderArticleReviewsTitle'),
				#myBackButton=mkBackButton(),
				#content=myContents, 
				grid=grid, 
				myFinalScript=myScript,
			  )




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def add_recommender_as_reviewer():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		db.t_reviews.validate_and_insert(recommendation_id=recommId, reviewer_id=recomm.recommender_id, no_conflict_of_interest=recomm.no_conflict_of_interest, review_state='Under consideration')
	redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def del_reviewer():
	reviewId = request.vars['reviewId']
	if reviewId:
		if db( (db.t_reviews.id==reviewId) & (db.t_recommendations.id==db.t_reviews.recommendation_id) & (db.t_recommendations.recommender_id==auth.user_id) ).count() > 0:
			db( (db.t_reviews.id==reviewId) ).delete()
	redirect(request.env.http_referer)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def reviewers():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		reviewersListSel = db( (db.t_reviews.recommendation_id==recommId) & (db.t_reviews.reviewer_id==db.auth_user.id) ).select(db.t_reviews.id, db.t_reviews.review_state, db.auth_user.id)
		reviewersList = []
		reviewersIds = [auth.user_id]
		selfFlag = False
		for con in reviewersListSel:
			if recomm.recommender_id == con.auth_user.id: selfFlag=True
			reviewersIds.append(con.auth_user.id)
			reviewersList.append(LI(mkUser(auth, db, con.auth_user.id),
									A('X', _href=URL(c='recommender', f='del_reviewer', vars=dict(reviewId=con.t_reviews.id)), 
									   _title=T('Delete'), _style='margin-left:8px;')
									if con.t_reviews.review_state=='Pending' else '',
								))
		excludeList = ','.join(map(str,reviewersIds))
		if len(reviewersList)>0:
			myContents = DIV(
				LABEL(T('Reviewers sollicited:')),
				UL(reviewersList)
			)
			txtbtn = current.T('Search for another reviewer?')
		else:
			myContents = ''
			txtbtn = current.T('Search for a reviewer?')
		#myContents = DIV(
			#LABEL(T('Current reviewers:')),
			#UL(reviewersList),
		#)
		#db.t_reviews._id.readable = False
		#db.t_reviews.recommendation_id.default = recommId
		#db.t_reviews.recommendation_id.writable = False
		#db.t_reviews.recommendation_id.readable = False
		#db.t_reviews.review.writable = False
		#db.t_reviews.review.readable = False
		#db.t_reviews.anonymously.writable = False
		#db.t_reviews.anonymously.readable = False
		#db.t_reviews.last_change.writable = False
		#db.t_reviews.last_change.readable = False
		#db.t_reviews.no_conflict_of_interest.writable = False
		#db.t_reviews.no_conflict_of_interest.readable = False
		#db.t_reviews.reviewer_id.writable = True
		#db.t_reviews.reviewer_id.represent = lambda text,row: mkUserWithMail(auth, db, row.reviewer_id) if row else ''
		#db.t_reviews.review_state.writable = False
		#db.t_reviews.review_state.readable = False
		myUpperBtn = DIV(
							A(SPAN(txtbtn, _class='buttontext btn btn-info'), 
								_href=URL(c='recommender', f='search_reviewers', vars=dict(recommId=recommId, myGoal='4review', exclude=excludeList), user_signature=True)),
							A(SPAN(current.T('Add yourself as a reviewer')), _class='buttontext btn btn-info'+(' disabled' if selfFlag else ''), 
										_href=URL(c='recommender', f='add_recommender_as_reviewer', vars=dict(recommId=recommId), user_signature=True)),
							A(SPAN(current.T('Template email for contacting external reviewers'), _class='buttontext btn btn-info'), 
										_href=URL(c='recommender', f='email_for_reviewer', vars=dict(recommId=recommId), user_signature=True)),
							_style='margin-top:8px; margin-bottom:16px; text-align:left;'
						)
		#alreadyRev = db(db.t_reviews.recommendation_id==recommId)._select(db.t_reviews.reviewer_id)
		#otherRevQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user.registration_key=='') & (~db.auth_user.id.belongs(alreadyRev)) )
		#db.t_reviews.reviewer_id.requires = IS_IN_DB(otherRevQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		#form = SQLFORM(db.t_reviews)
		#if form.process().accepted:
			#redirect(URL(c='recommender', f='reviewers', vars=dict(recommId=recomm.id), user_signature=True))
		myAcceptBtn = DIV(
							A(SPAN(T('Done'), _class='buttontext btn btn-success'), 
								_href=URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=False))),
							_style='margin-top:16px; text-align:center;'
						)
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderAddReviewers'),
					myText=getText(request, auth, db, '#RecommenderAddReviewersText'),
					myTitle=getTitle(request, auth, db, '#RecommenderAddReviewersTitle'),
					myAcceptBtn=myAcceptBtn,
					content=myContents, 
					form='', 
					myUpperBtn = myUpperBtn,
				)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_reviewer():
	response.view='default/info.html' #OK
	return dict(
		message=T("Template email for registration and review"),
		#panel=mkPanel(myconf, auth),
		myText=getText(request, auth, db, '#TemplateEmailForReviewInfo'),
		myBackButton=mkBackButton(),
	)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def email_for_author():
	response.view='default/info.html' #OK
	return dict(
		message=T("Template email for author"),
		#panel=mkPanel(myconf, auth),
		myText=getText(request, auth, db, '#TemplateEmailForAuthorInfo'),
		myBackButton=mkBackButton(),
	)


@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def del_contributor():
	pressId = request.vars['pressId']
	if pressId:
		if db( (db.t_press_reviews.id==pressId) & (db.t_recommendations.id==db.t_press_reviews.recommendation_id) & (db.t_recommendations.recommender_id==auth.user_id) ).count() > 0:
			db( (db.t_press_reviews.id==pressId) ).delete()
	redirect(request.env.http_referer)



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def add_contributor():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		contributorsListSel = db( (db.t_press_reviews.recommendation_id==recommId) & (db.t_press_reviews.contributor_id==db.auth_user.id) ).select(db.t_press_reviews.id, db.auth_user.id)
		contributorsList = []
		for con in contributorsListSel:
			contributorsList.append(LI(mkUserWithMail(auth, db, con.auth_user.id),
									A('X', 
									   _href=URL(c='recommender', f='del_contributor', vars=dict(pressId=con.t_press_reviews.id)), 
									   _title=T('Delete'), _style='margin-left:8px;'),
									))
		myContents = DIV(
			LABEL(T('Co-recommenders:')),
			UL(contributorsList),
		)
		db.t_press_reviews._id.readable = False
		db.t_press_reviews.recommendation_id.default = recommId
		db.t_press_reviews.recommendation_id.writable = False
		db.t_press_reviews.recommendation_id.readable = False
		db.t_press_reviews.contributor_id.writable = True
		db.t_press_reviews.contributor_id.label = T('Select a co-recommender')
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		alreadyCo = db(db.t_press_reviews.recommendation_id==recommId)._select(db.t_press_reviews.contributor_id)
		otherContribsQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender') & (~db.auth_user.id.belongs(alreadyCo)) )
		db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		form = SQLFORM(db.t_press_reviews)
		form.element(_type='submit')['_value'] = T("Add")
		if form.process().accepted:
			redirect(URL(c='recommender', f='add_contributor', vars=dict(recommId=recomm.id), user_signature=True))
		myAcceptBtn = DIV(
							A(SPAN(current.T('Write or edit recommendation'), _class='buttontext btn btn-info'), 
										_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recommId), user_signature=True)),
							A(SPAN(current.T('Add a co-recommender later'), _class='buttontext btn btn-info'), 
										_href=URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=True), user_signature=True)),
							A(SPAN(current.T('Done'), _class='buttontext btn btn-success'+(' disabled'if not(len(recomm.recommendation_comments)>50 and len(contributorsList)>0) else '')), 
										_href=URL(c='recommender', f='recommendations', vars=dict(articleId=recomm.article_id), user_signature=True), 
										_title=current.T('Click here to check the final recommendation of this article')),
							_style='margin-top:16px; text-align:center;'
						)
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderAddContributor'),
					myText=getText(request, auth, db, '#RecommenderAddContributorText'),
					myTitle=getTitle(request, auth, db, '#RecommenderAddContributorTitle'),
					content=myContents, 
					form=form, 
					myAcceptBtn = myAcceptBtn,
				)



@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def contributions():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		myContents = mkRecommendationFormat(auth, db, recomm)
		query = (db.t_press_reviews.recommendation_id == recommId)
		db.t_press_reviews._id.readable = False
		db.t_press_reviews.recommendation_id.default = recommId
		db.t_press_reviews.recommendation_id.writable = False
		db.t_press_reviews.recommendation_id.readable = False
		db.t_press_reviews.contributor_id.writable = True
		db.t_press_reviews.contributor_id.represent = lambda text,row: mkUserWithMail(auth, db, row.contributor_id) if row else ''
		alreadyCo = db(db.t_press_reviews.recommendation_id==recommId)._select(db.t_press_reviews.contributor_id)
		otherContribsQy = db((db.auth_user._id!=auth.user_id) & (db.auth_user._id==db.auth_membership.user_id) & (db.auth_membership.group_id==db.auth_group._id) & (db.auth_group.role=='recommender') & (~db.auth_user.id.belongs(alreadyCo)) )
		db.t_press_reviews.contributor_id.requires = IS_IN_DB(otherContribsQy, db.auth_user.id, '%(last_name)s, %(first_name)s')
		grid = SQLFORM.grid( query
			,details=False
			,editable=False
			,deletable=True
			,create=True
			,searchable=False
			,maxtextlength = 250,paginate=100
			,csv = csv, exportclasses = expClass
			,fields=[db.t_press_reviews.recommendation_id, db.t_press_reviews.contributor_id]
		)
		#myAcceptBtn = DIV(
							#A(SPAN(current.T('Write recommendation now'), _class='buttontext btn btn-info'), 
								#_href=URL(c='recommender', f='edit_recommendation', vars=dict(recommId=recommId), user_signature=True)),
							#A(SPAN(current.T('Later'), _class='buttontext btn btn-info'), 
										#_href=URL(c='recommender', f='my_recommendations', user_signature=True)),
							#_style='margin-top:16px; text-align:center;'
						#)
		# This script renames the "Add record" button
		myScript = SCRIPT("""$(function() { 
						$('span').filter(function(i) {
								return $(this).attr("title") ? $(this).attr("title").indexOf('"""+T("Add record to database")+"""') != -1 : false;
							})
							.each(function(i) {
								$(this).text('"""+T("Add a contributor")+"""').attr("title", '"""+T("Add a new contributor to this recommendation")+"""');
							});
						})""",
						_type='text/javascript')
		response.view='default/myLayout.html'
		return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderContributionsToPressReviews'),
					myText=getText(request, auth, db, '#RecommenderContributionsToPressReviewsText'),
					myTitle=getTitle(request, auth, db, '#RecommenderContributionsToPressReviewsTitle'),
					contents=myContents, 
					grid=grid, 
					#myAcceptBtn = myAcceptBtn,
					myFinalScript=myScript,
				)




@auth.requires(auth.has_membership(role='recommender') or auth.has_membership(role='manager'))
def edit_recommendation():
	recommId = request.vars['recommId']
	recomm = db.t_recommendations[recommId]
	art = db.t_articles[recomm.article_id]
	if (recomm.recommender_id != auth.user_id) and not(auth.has_membership(role='manager')):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	elif art.status not in ('Under consideration', 'Pre-recommended'):
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		nbCoRecomm = db(db.t_press_reviews.recommendation_id == recommId).count()
		buttons = [
					INPUT(_type='Submit', _name='save',      _class='btn btn-info', _value='Save'),
					INPUT(_type='Submit', _name='terminate', _class='btn btn-success', _value='Save & terminate') if (nbCoRecomm>0) else '',
				]
		form = SQLFORM(db.t_recommendations
					,record=recomm
					,deletable=False
					,fields=['recommendation_title', 'no_conflict_of_interest', 'recommendation_comments']
					,showid=False
					,buttons=buttons
				)
		if form.process().accepted:
			if form.vars.save:
				session.flash = T('Recommendation saved', lazy=False)
				redirect(URL(f='recommendations', vars=dict(articleId=art.id), user_signature=True))
			elif form.vars.terminate:
				session.flash = T('Recommendation saved and terminated', lazy=False)
				redirect(URL(c='recommender', f='my_recommendations', user_signature=True))
		elif form.errors:
			response.flash = T('Form has errors', lazy=False)
		myScript = """jQuery(document).ready(function(){
						if(jQuery('#t_recommendations_no_conflict_of_interest').prop('checked')) {
							jQuery(':submit').prop('disabled', false);
						} else {
							jQuery(':submit').prop('disabled', true);
						}
						jQuery('#t_recommendations_no_conflict_of_interest').change(function(){
									if(jQuery('#t_recommendations_no_conflict_of_interest').prop('checked')) {
										jQuery(':submit').prop('disabled', false);
									} else {
										jQuery(':submit').prop('disabled', true);
									}
						});
					});
		"""
		response.view='default/myLayout.html'
		return dict(
					form = form,
					myText=getText(request, auth, db, '#RecommenderEditRecommendationText'),
					myHelp=getHelp(request, auth, db, '#RecommenderEditRecommendation'),
					myTitle=getTitle(request, auth, db, '#RecommenderEditRecommendationTitle'),
					#myBackButton = mkBackButton(),
					myFinalScript = SCRIPT(myScript),
				)



@auth.requires(auth.has_membership(role='recommender'))
def my_press_reviews():
	query = (
			  (db.t_press_reviews.contributor_id == auth.user_id) 
			& (db.t_press_reviews.recommendation_id==db.t_recommendations.id) 
			& (db.t_recommendations.article_id==db.t_articles.id)
			)
	db.t_press_reviews.contributor_id.writable = False
	db.t_press_reviews.recommendation_id.writable = False
	db.t_articles._id.readable = False
	#db.t_articles._id.represent = lambda text, row: mkRepresentArticleLight(auth, db, text)
	#db.t_articles._id.label = T('Article')
	db.t_recommendations._id.label = T('Recommendation')
	db.t_recommendations._id.represent = lambda rId, row: mkRepresentRecommendationLight(auth, db, rId)
	db.t_articles.status.writable = False
	db.t_articles.status.represent = lambda text, row: mkStatusDiv(auth, db, text)
	#db.t_press_reviews.recommendation_id.represent = lambda text,row: mkRecommendation4PressReviewFormat(auth, db, row)
	db.t_press_reviews._id.readable = False
	#db.t_press_reviews.contribution_state.represent = lambda state,row: mkContributionStateDiv(auth, db, state)
	db.t_recommendations.recommender_id.represent = lambda uid,row: mkUserWithMail(auth, db, uid)
	db.t_recommendations.article_id.readable = False
	grid = SQLFORM.grid( query
		,searchable=False, deletable=False, create=False, editable=False, details=False
		,maxtextlength=500,paginate=10
		,csv=csv, exportclasses=expClass
		,fields=[db.t_articles.uploaded_picture, db.t_recommendations._id, db.t_articles._id, db.t_articles.status, db.t_recommendations.article_id, db.t_recommendations.recommender_id]
		,links=[
				dict(header=T('Other contributors'), body=lambda row: mkOtherContributors(auth, db, row.t_recommendations if 't_recommendations' in row else row)),
				dict(header=T(''), 
						body=lambda row: A(SPAN(current.T('View'), _class='buttontext btn btn-default pci-button'), 
										_href=URL(c='recommender', f='recommendations', vars=dict(articleId=row.t_articles.id), user_signature=True), 
										_target="_blank", 
										_class='button', 
										_title=current.T('View this co-recommendation')
										)
					),
				]
		,orderby=~db.t_press_reviews.id
	)
	myContents = ''
	response.view='default/myLayout.html'
	return dict(
					myHelp = getHelp(request, auth, db, '#RecommenderMyPressReviews'),
					myText=getText(request, auth, db, '#RecommenderMyPressReviewsText'),
					myTitle=getTitle(request, auth, db, '#RecommenderMyPressReviewsTitle'),
					#myBackButton=mkBackButton(), 
					contents=myContents, 
					grid=grid, 
			 )




@auth.requires(auth.has_membership(role='recommender'))
def do_cancel_press_review():
	recommId = request.vars['recommId']
	if recommId is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	recomm = db.t_recommendations[recommId]
	if recomm is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	art = db.t_articles[recomm.article_id]
	if art is None:
		raise HTTP(404, "404: "+T('Unavailable')) # Forbidden access
	# NOTE: security hole possible by changing manually articleId value: Enforced checkings below.
	if recomm.recommender_id != auth.user_id:
		session.flash = auth.not_authorized()
		redirect(request.env.http_referer)
	else:
		art.status = 'Cancelled'
		art.update_record()
		redirect(URL(c='recommender', f='my_recommendations', vars=dict(pressReviews=True), user_signature=True))



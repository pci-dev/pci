import pytz, datetime
import decimal
from gluon.storage import Storage
from gluon.html import TAG, XmlComponent, xmlescape
from gluon.languages import lazyT
#import gluon.contrib.rss2 as rss2
import my_rss2 as rss2
from gluon.serializers import safe_encode
from xml.etree.ElementTree import Element, SubElement, tostring

def rss(feed):
	if not 'entries' in feed and 'items' in feed:
		feed['entries'] = feed['items']

	def safestr(obj, key, default=''):
		return safe_encode(obj.get(key,''))

	#local = pytz.timezone ("Europe/Paris")
	#local_dt = local.localize(datetime.datetime.now(), is_dst=None)
	#now = local_dt.astimezone (pytz.utc)
	now = datetime.datetime.utcnow()
	img = rss2.Image(url=feed.get('image'), title=safestr(feed,'title'), link=safestr(feed,'link'))
	link = safestr(feed,'link')
	#thisLink=feed.get('thisLink', link)
	
	rss = rss2.RSS2(title=safestr(feed,'title'),
					link=safestr(feed,'link'),
					#thisLink=feed.get('thisLink', link),
					description=safestr(feed,'description'),
					#lastBuildDate=feed.get('created_on', now),
					#pubDate=feed.get('pubDate', now),
					pubDate=feed.get('created_on', now),
					managingEditor=safestr(feed,'managingEditor'),
					image=img,
					items=[rss2.RSSItem(
						guid=safestr(entry,'guid'),
						title=safestr(entry,'title','(notitle)'),
						link=safestr(entry,'link'),
						description=safestr(entry,'description'),
						pubDate=entry.get('created_on', now)
					) for entry in feed.get('entries', [])]
				)
	
	return rss.to_xml(encoding='utf-8')

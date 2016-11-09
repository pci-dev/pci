# -*- coding: utf-8 -*-

from gluon.contrib.appconfig import AppConfig
myconf = AppConfig(reload=True)

dbHelp = DAL('sqlite://help.sqlite', pool_size=50, lazy_tables=True)

dbHelp.define_table('help_texts',
	Field('id', type='id'),
	Field('hashtag', type='string', length=128, label=T('Hashtag'), default='#'),
	Field('language', type='string', length=10, label=T('Language'), default='default'),
	Field('contents', type='text', label=T('Contents')),
	migrate=True,
)
dbHelp.executesql('CREATE INDEX IF NOT EXISTS help_idx ON help_texts (hashtag, language);')

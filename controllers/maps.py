# -*- coding: utf-8 -*-
# apt-get install python-matplotlib python-matplotlib-data python-cartopy
# pip install matplotlib  geopandas

import cartopy
cartopy.config['data_dir'] = '../maps'
from cartopy.io import shapereader
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
#from matplotlib.offsetbox import AnchoredText
import geopandas

trCountries = ('Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada', 'Cape Verde', 'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica', "Côte d'Ivoire", 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 'Denmark', 'Djibouti', 'Dominica', 'Dominican Republic', 'East Timor', 'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hong Kong', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'North Korea','South Korea', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'FYROM', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia and Montenegro', 'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Swaziland', 'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States of America', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe')

def recommenders_map():
	# Get recommenders distinct countries
	count = db.auth_user.id.count()
	pays = db( (db.auth_group.role=='recommender') & (db.auth_membership.group_id==db.auth_group.id) & (db.auth_user.id==db.auth_membership.user_id) & (db.auth_user.country != None) ).select(db.auth_user.country, count, groupby=db.auth_user.country)

	fig = plt.figure(figsize=(7,5))
	#ax = plt.axes(projection=ccrs.PlateCarree())
	ax = plt.axes(projection=ccrs.Robinson())
	#ax.set_extent([-180, 100, -80, 80])
	ax.set_global()
	
	# Create a feature for States/Admin 1 regions at 1:50m from Natural Earth
	countries = cfeature.NaturalEarthFeature(
		category='cultural',
		name='admin_0_countries',
		scale='110m',
		facecolor='none')
	#ax.add_feature(cfeature.LAND)
	#ax.add_feature(cfeature.COASTLINE)
	ax.add_feature(countries, edgecolor='gray', linewidth=0.2)
	#ax.add_feature(countries)
	
	shpfilename = shapereader.natural_earth('110m', 'cultural', 'admin_0_countries')
	df = geopandas.read_file(shpfilename)
	#print(df['ADMIN'])
	
	for p in pays:
		countryName = p['auth_user.country']
		poly = df.loc[df['ADMIN'] == countryName]['geometry'].values
		if poly:
			ax.add_geometries(poly, crs=ccrs.PlateCarree(), facecolor=(0.9,0.5,0.5), edgecolor='none')
		else:
			print('WARNING *** Missing geometry for: %s' % countryName)
	
	directory = os.path.join(request.folder, 'static', 'images')
	#if not os.path.exists(directory): os.makedirs(directory)
	imgFilename = os.path.join(directory, 'recommendersMap.png')
	if os.path.isfile(imgFilename): os.remove(imgFilename)
	imgLink = os.path.join('..', 'static', 'images', 'recommendersMap.png')
	grid = DIV(IMG(_src=imgLink, _class='pci-mapImg'), _class='pci-mapDiv')
	
	fig.savefig(imgFilename, dpi=200, bbox_inches='tight')
	
	
	response.view='default/myLayout.html'
	return dict( grid=grid, 
			myTitle=getTitle(request, auth, db, '#RecMapTextTitle'),
			myText=getText(request, auth, db, '#RecMapTextText'),
			myHelp=getHelp(request, auth, db, '#RecMapHelpTexts'),
		 )




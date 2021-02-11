import pandas as pd
import numpy as np
import json


states = """DC	District of Columbia
AL	Alabama
AK	Alaska
AZ	Arizona
AR	Arkansas
CA	California
CO	Colorado
CT	Connecticut
DE	Delaware
FL	Florida
GA	Georgia
HI	Hawaii
ID	Idaho
IL	Illinois
IN	Indiana
IA	Iowa
KS	Kansas
KY	Kentucky
LA	Louisiana
ME	Maine
MD	Maryland
MA	Massachusetts
MI	Michigan
MN	Minnesota
MS	Mississippi
MO	Missouri
MT	Montana
NE	Nebraska
NV	Nevada
NH	New Hampshire
NJ	New Jersey
NM	New Mexico
NY	New York
NC	North Carolina
ND	North Dakota
OH	Ohio
OK	Oklahoma
OR	Oregon
PA	Pennsylvania
RI	Rhode Island
SC	South Carolina
SD	South Dakota
TN	Tennessee
TX	Texas
UT	Utah
VT	Vermont
VA	Virginia
WA	Washington
WV	West Virginia
WI	Wisconsin
WY	Wyoming""".replace('\t',' ').split('\n')
state_abbrs, state_names = zip(*[(s[:2], s[3:]) for s in states])


########################
# Population data
########################

selected_vars = ['CTYNAME', 'STNAME', 'YEAR', 'AGEGRP',
                 'TOT_POP', 'WA_MALE', 'WA_FEMALE',
                 'BAC_MALE', 'BAC_FEMALE', 'AAC_MALE',
                 'AAC_FEMALE', 'H_MALE', 'H_FEMALE']
age_dict = {0:0, 1:2.5, 2:7.5, 3:12.5, 4:17.5, 5:22.5, 6:27.5, 7:32.5, 
            8:37.5, 9:42.5, 10:47.5, 11:52.5, 12:57.5, 13:62.5, 14:67.5, 
            15:72.5, 16:77.5, 17:82.5, 18:90}

#read in data and select 2020 and all (non-total) age groups
popl = pd.read_csv('source_data/Population_2020only.csv', usecols=selected_vars, encoding='latin-1')
popl = popl[ (popl['YEAR'] == 12) & (popl['AGEGRP'] > 0) ]

#combine male and female demographics
for key in ('WA', 'BAC', 'AAC', 'H'):
    popl[key] = popl.pop(key+'_MALE') + popl.pop(key+'_FEMALE')
#rename column labels for convenience and uniformity
popl.columns = ['state', 'county', 'year', 'age', 'popl', 
               'white_popl', 'black_popl', 'asian_popl', 'hispanic_popl']
#map the original AGE_GRP column to actual ages
popl['age'].replace(age_dict, inplace=True)
#replace state names with two letter abbr
popl['state'].replace(dict(zip(state_names, state_abbrs)), inplace=True)
#adjust a few county names that differ between datasets
popl['county'].replace('LaSalle Parish', 'La Salle Parish', inplace=True)
popl['county'].replace('Doña Ana County', 'Dona Ana County', inplace=True)
popl['county'].replace('Petersburg Borough', 'Petersburg Census Area', inplace=True)
#popl['county'].replace('Oglala Lakota County', 'Shannon County', inplace=True)
#popl['county'].replace('Kusilvak Census Area', 'Wade Hampton Census Area', inplace=True)

#extract average ages for each demographic, then remove the (latent) age axis
avgd_labels = ['avg_age', 'avg_age_white', 'avg_age_black', 'avg_age_asian', 'avg_age_hispanic']
popl_labels = ['popl', 'white_popl', 'black_popl', 'asian_popl', 'hispanic_popl']
pop_grp = popl.groupby(['state', 'county'], as_index=True)
popl[avgd_labels] = popl[['age']].values * popl[popl_labels] / pop_grp[popl_labels].transform('sum')

#change the table name, since it will accumulate other columns further down
data = pop_grp.sum().drop(columns=['year', 'age'])
#convert racial populations to fractions
data[popl_labels[1:]] /= data[['popl']].values
#relabel the racial percentage columns
popl_prcnt_labels = ['popl', 'prcnt_white', 'prcnt_black', 'prcnt_asian', 'prcnt_hispanic']
data.columns = popl_prcnt_labels + data.columns.tolist()[5:]

#conserves memory
del popl


########################
# FIPS codes
########################

#read in the data file that maps counties/cities to their FIPS codes
fips = pd.read_csv('source_data/FIPS.csv', dtype=str)[['state', 'state_code', 'county_code', 'county']]
fips['fips'] = (fips['state_code'] + fips['county_code']).astype(int)
fips.set_index('fips', inplace=True)
fips.loc[[2270, 46113]] = [('AK', '02', '158', 'Kusilvak Census Area'),
                           ('SD', '46', '102', 'Oglala Lakota County')]
fips.reset_index(inplace=True)
fips['fips'].replace({2270:2158, 46113:46102}, inplace=True)
fips.set_index(['state', 'county'], inplace=True)

#merge the fips codes into the data/popl table
data = data.join(fips[['fips']])
data.reset_index(inplace=True)
data.set_index('fips', inplace=True)
#data.iloc[np.where(data.isna())[0]]

#drops the row for Kalawao County, HI (popl: ~82) to avoid problems with other tables
data.drop(index=15005, inplace=True)


########################
# Land area/Popl density
########################

#read in land area data; 'LND110210D' is the most recent and relevant column to use
lnd = pd.read_excel('source_data/LandArea.xls', usecols=['STCOU', 'LND110210D'])
lnd.columns = ['fips', 'land_area']
#update outdated FIPS codes
lnd['fips'].loc[lnd['fips'].isin([2270, 46113])] = (2158, 46102)

#add land area and population density metrics to the data table
data = data.join(lnd.set_index('fips'))
data['popl_density'] = np.log10(data['popl'] / data['land_area'])


########################
# Unemployment data
########################

#read in the employment data
empl = pd.read_csv('source_data/employment_data_10-19_thru_11-2020_edited_header.txt', delimiter='|',
                    dtype={'StFIPS':str, 'CtyFIPS':str})
empl.columns = empl.columns.to_series().apply(lambda x: x.strip())

#produce numeric FIPS code and unemployment rate columns
empl['unempl_rate'] = pd.to_numeric(empl['Unemployment_rate'], errors='coerce')
empl['fips'] = (empl.pop('StFIPS').str.strip() + empl.pop('CtyFIPS').str.strip()).astype(int)
empl.set_index('fips', inplace=True)

#calculate the average unemployment rate between Apr-2020 and Nov-2020, a timeframe 
#that covers the COVID 19 pandemic up to the lastest employment data.
mean_mask = empl['Period'].isin(['   Mar-20  ', '   Apr-20  ', '   May-20  ', 
                                 '   Jun-20  ', '   Jul-20  ', '   Aug-20  ', 
                                 '   Sep-20  ', '   Oct-20  ', ' Nov-20(p) '])
unempl_rate = empl.loc[mean_mask].groupby(['fips'], as_index=True).mean()

#calculate the change in unemployment rate between the same two months a year apart
diff_mask1 = empl['Period'] == '   Oct-20  '
diff_mask2 = empl['Period'] == '   Oct-19  '
unempl_diff = empl['unempl_rate'][diff_mask1] - empl['unempl_rate'][diff_mask2]

#add the unemployment data to the full features dataset
unempl = unempl_rate.join(unempl_diff, how='outer', rsuffix='_chng')
data = data.join(unempl[['unempl_rate', 'unempl_rate_chng']])


########################
# Income data
########################

#read income data and rename columns
incm = pd.read_excel('source_data/IncomePoverty.xls', header=3, dtype=str,
                     usecols=['State FIPS Code', 'County FIPS Code', 'Postal Code',
                     'Name', 'Poverty Estimate, All Ages', 'Median Household Income'])
incm.columns = ['state_fips', 'county_fips', 'state', 'county', 'n_poverty', 'med_income']

#index the income table by FIPS codes
incm.set_index((incm.pop('state_fips') + incm.pop('county_fips')).astype(int), inplace=True)
#scale income to units of thousands of dollars
incm['med_income'] = pd.to_numeric(incm['med_income'], errors='coerce') / 1e3

#merge income data to the full dataset
data = data.join(incm[['n_poverty', 'med_income']])
#calculate the percentage in poverty (by county)
data['prcnt_poverty'] = pd.to_numeric(data.pop('n_poverty'), errors='coerce') / data['popl']


########################
# GDP data
########################

#read in the gdp dataset and change data to float type
gdp = pd.read_csv('source_data/GDP_2001_2019.csv', encoding='latin-1', skipfooter=4, 
                  usecols=['GeoFIPS', 'GeoName', 'LineCode', '2018', '2019'])
gdp[['2018', '2019']] = gdp[['2018', '2019']].replace({'(NA)':'NaN', '(NM)':'NaN'}).astype(float)

#select the standard GDP measure (i.e., not 'Real GDP' or 'Quantity Index')
gdp = gdp[gdp.pop('LineCode') == 3]
#convert the '2018' column to give the percent change in gdp from 2018 to 2019
gdp['prcnt_chng_gdp'] = (gdp['2019'] - gdp['2018']) / gdp.pop('2018')
#change the gpd units to dollars (not thousands of dollars)
gdp['gdp'] = gdp.pop('2019') * 1e3
#clean up the fips codes column
gdp['FIPS'] = gdp.pop('GeoFIPS').str.replace('"','').astype(int)

#separate the state abbrv into a new column, drop rows with no state/county pair 
gdp[['county', 'state']] = gdp.pop('GeoName').str.rsplit(', ', 1, expand=True)
gdp['state'] = gdp['state'].str[:2]
gdp.dropna(inplace=True)

#a set of manual county/city name edits needed for the next lines to work
gdp['county'] = gdp['county'].str.replace('\(Independent City\)', 'city')
gdp['county'] = gdp['county'].str.replace('Fairfax City', 'Fairfax')
gdp['county'] = gdp['county'].str.replace('Kalawao', 'Kalawao County')
gdp['county'] = gdp['county'].str.replace('Petersburg Borough', 'Petersburg Census Area')

#splits merged counties and cities onto separate rows
gdp['county'].loc[gdp['county'].str.contains(r'\+\s(?!Kalawao)')] += ' city'
gdp['county'] = gdp['county'].str.split(r' \+ ')
gdp = gdp.explode('county')
gdp['county'].loc[gdp['county'].str.contains(r',')] += ' city'
gdp['county'] = gdp['county'].str.split(', ')
gdp = gdp.explode('county')
gdp['county'].loc[~gdp['county'].str.contains(r'city|County|Borough|Area|Parish|Municipality')] += ' County'
# gdp = gdp[ gdp['state'].str.contains(r'\*') ]

#corrects the FIPS codes for the newly separated county/city groups
tdata = data[['state', 'county']].reset_index()
gdp.set_index(['state', 'county'], inplace=True)
gdp = tdata.join(gdp, on=['state', 'county'], how='right')
gdp['fips'].fillna(gdp['FIPS'], inplace=True)
gdp.set_index(gdp.pop('fips').astype(int), inplace=True)

def adjust_gdp(x):
    x['gdp'] *= x['popl'] / x['popl'].sum()
    return x

#adds the GDP columns to the data table and converts GPD to per capita
data = data.join(gdp.drop(columns=['state', 'county']))
data = data.groupby('FIPS').apply(adjust_gdp).drop(columns='FIPS')
data['per_capita_gdp'] = data.pop('gdp') / data['popl']


########################
# Education data
########################

edu = pd.read_csv('source_data/ACSST5Y2019.S1501_metadata_2021-01-22T053218.csv', skiprows=[1])
edu[['meas', 'metric', 'category', 'class', 'info']] = edu['id'].str.split('!!', expand=True)
edu = edu[(edu['meas']=='Estimate') & 
        (edu['metric']=='Total') &
        (edu['category']=='AGE BY EDUCATIONAL ATTAINMENT') & 
        ((edu['info']=="Bachelor's degree or higher") | 
        (edu['info']=="High school graduate (includes equivalency)") |
        edu['info'].isna())]
edu.drop(columns=['id', 'meas', 'metric', 'category'], inplace=True)

edu = pd.read_csv('source_data/ACSST5Y2019.S1501_data_with_overlays_2021-01-22T053218.csv', skiprows=[1], 
                  usecols=['GEO_ID', 'S1501_C01_001E', 'S1501_C01_003E', 'S1501_C01_005E',
                           'S1501_C01_006E', 'S1501_C01_009E', 'S1501_C01_015E'])
edu.columns = ['fips', 1, 3, 5, 6, 9, 15]
edu['fips'] = edu['fips'].str.split('US').str[-1].astype(int)
edu.set_index('fips', inplace=True)

edu_popl = edu[1] + edu[6]
edu['high_sch_grad_rate'] = pd.to_numeric((edu[3] + edu[9])  / edu_popl, errors='coerce')
edu['college_grad_rate']  = pd.to_numeric((edu[5] + edu[15]) / edu_popl, errors='coerce')

data = data.join(edu[['high_sch_grad_rate', 'college_grad_rate']])


########################
# Political gov. data
########################

legis = pd.read_excel('source_data/US_Legis_Control_2020_April 1.xls')
legis.at[53, ['legis_control', 'state_control']] = ['null', 'null']
party2binary = {'Dem': 1, 'Rep': 0, 'Divided': 2, 'null': 2}

for col in ['legis_control', 'gov_party', 'state_control']:
    legis[col] = legis[col].str.strip().replace(party2binary)
legis = legis.set_index('state').dropna().astype(int)
legis.columns = ['dem_legis', 'dem_gov', 'dem_state']

data = data.join(legis, on='state')


########################
# Election data
########################

def get_election_margin(race):
    if race['race_id'][2:6] != '-G-P':
        return []
    
    state_records = []
    for county in race['counties']:
        state_records.append({'fips': county['fips'],
                              #'state': race['state_id'],
                              #'county': county['name'].lower().replace(' ', '-'),
                              'biden_margin_2020': county.get('margin2020', np.nan)})
    return state_records


with open('source_data/2020presidential_race.json') as f_handle:
    election_json = json.load(f_handle)

vote_records = []
for race in election_json['data']['races']:
    vote_records += get_election_margin(race)

#the Alaskan election district FIPS codes don't line up with the Alaskan Boroughs, so these 
#five lines add election data manually estimated for each of the five most populated regions
vote_records += [{'fips': '02020', 'biden_margin_2020':   3.13}, 
                 {'fips': '02090', 'biden_margin_2020': -14.76}, 
                 {'fips': '02122', 'biden_margin_2020': -28.41}, 
                 {'fips': '02170', 'biden_margin_2020': -46.57},
                 {'fips': '02110', 'biden_margin_2020':  41.76}]

election_data = pd.DataFrame.from_records(vote_records)
election_data['fips'] = election_data['fips'].astype(int)
election_data.set_index('fips', inplace=True)

data = data.join(election_data)

#set the election margin to zero (close enough) for remaining Alaskan Boroughs
na_idx = np.where(data['biden_margin_2020'].isna())[0]
data['biden_margin_2020'].iloc[na_idx] = 0


########################
# Regional IDs
########################

def get_state_region(abbr):
    if abbr in ('AK', 'CA', 'HI', 'OR', 'WA'):
        region = 'West'
    elif abbr in ('AZ', 'CO', 'ID', 'NM', 'NV', 'UT'):
        region = 'Southwest'
    elif abbr in ('KS', 'MT', 'ND', 'NE', 'SD', 'WY'):
        region = 'Central'
    elif abbr in ('KY', 'IA', 'IL', 'IN', 'MI', 'MN', 'MO', 'OH', 'WI'):
        region = 'Midwest'
    elif abbr in ('AL', 'AR', 'GA', 'FL', 'LA', 'MI', 'MS', 'NC', 'OK', 'SC', 'TN', 'TX'):
        region = 'Southeast'
    elif abbr in ('CT', 'DC', 'DE', 'MA', 'ME', 'MD', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VA', 'VT', 'WV'):
        region = 'Northeast'
    else:
        raise Exception('The state {} was not recognized'.format(abbr))
    return region

#add custom geographic region labels...these represent a rough summary of climate 
#and commerce by state, though perhaps this isn't granular enough to be meaningful...
data['region'] = data['state'].apply(get_state_region)


########################
# Temperature data
########################

tmax_state_codes = """01	AL
02	AZ
03	AR
04	CA
05	CO
06	CT
07	DE
08	FL
09	GA
10	ID
11	IL
12	IN
13	IA
14	KS
15	KY
16	LA
17	ME
18	MD
19	MA
20	MI
21	MN
22	MS
23	MO
24	MT
25	NE
26	NV
27	NH
28	NJ
29	NM
30	NY
31	NC
32	ND
33	OH
34	OK
35	OR
36	PA
37	RI
38	SC
39	SD
40	TN
41	TX
42	UT
43	VT
44	VA
45	WA
46	WV
47	WI
48	WY""".split()

#map state codes from the tmax dataset to FIPS codes
tmax_state_codes = pd.DataFrame({'state':tmax_state_codes[1::2], 
                                 'state_code':tmax_state_codes[::2]})
tmax_state_codes.set_index('state', inplace=True)
tmax_state_codes = fips[['fips']].join(tmax_state_codes, on='state').dropna()
tmax_state_codes['state_fips'] = tmax_state_codes.pop('fips').astype(str).str[:-3].astype(int)
tmax_state_codes.reset_index(drop=True, inplace=True)
tmax_state_codes = tmax_state_codes.set_index('state_code').drop_duplicates()


#load tmax data for contiguous 48 states, select only data for 2020
tmax = pd.read_csv('source_data/climdiv-tmaxcy-v1.0.0-20210106.dat', dtype=str, delim_whitespace=True)
fips_yr_code = tmax.pop('fips_yr_code')
tmax = tmax[fips_yr_code.str[7:11]=='2020']

#extract FIPS codes to use as the table index
state_fips = fips_yr_code.str[:2].to_frame().join(tmax_state_codes, on='fips_yr_code')
state_fips = state_fips.fillna(99).astype(int).astype(str)
tmax['fips'] = (state_fips['state_fips'] + fips_yr_code.str[2:5]).astype(int)

#index by FIPS, set temperature variable name and dtype
tmax = tmax.set_index('fips').astype('float').mean(axis=1).to_frame('tmax_avg')

#load tmax data for AK, DC, and HI and index by FIPS
ak_tmax = pd.read_csv('source_data/climate_AK-DC-HI_tmax_avg_2020.csv', skiprows=6, 
                      usecols=['Location ID', 'Value'])
ak_tmax['fips'] = ak_tmax.pop('Location ID').str.replace('AK-', '02')
ak_tmax['fips'] = ak_tmax['fips'].str.replace('DC-', '11').astype(int)
ak_tmax.set_index('fips', inplace=True)

#join the AK data to the CONUS data
tmax = tmax.join(ak_tmax, how='outer')
tmax = tmax['tmax_avg'].fillna(tmax.pop('Value'))

#add temperature data to the features table and fill NaNs with state average temperatures
data = data.join(tmax)
state_mean_temps = data.groupby('state')['tmax_avg'].transform('mean')
data['tmax_avg'] = data['tmax_avg'].fillna(state_mean_temps)


########################
# COVID 19 data
########################

#read in the COVID 19 case and death data and join the two datasets
c19_deaths = pd.read_csv('source_data/covid_deaths_usafacts.csv').dropna().set_index(['State','County Name'])
c19_cases = pd.read_csv('source_data/covid_confirmed_usafacts.csv').dropna().set_index(['State','County Name'])
c19 = pd.concat([c19_deaths, c19_cases], axis=1, keys=['deaths','cases'], names=['metric', 'date'])

#set FIPS codes as index and make the date a data column
c19['fips'] = c19.loc(axis=1)['deaths','countyFips'].astype(int)
c19.reset_index(drop=True, inplace=True)
c19.drop(columns=['stateFips', 'countyFips'], level=1, inplace=True)
c19.dropna(inplace=True)
c19 = c19.set_index('fips').stack(1).reset_index('date')

#count all the cases observed in three time bins (bin_1 < Jun 7 -- Oct 01 < bin_3),
#roughly matching the three peaks in the data.
c19['cases_period'] = 1
c19['cases_period'].loc[c19['date'] > '2020-06-07'] += 1
c19['cases_period'].loc[c19['date'] > '2020-10-01'] += 1
c19_l = c19.groupby(['fips', 'cases_period'], as_index=True)['cases'].last().unstack()
first_col = c19_l[1]
c19_l = c19_l.diff(axis=1)
c19_l[1] = first_col
c19_l['cases_tot'] = c19_l.sum(axis=1)

#count all the deaths observed in three time bins shifted by three weeks following the case
#bins (i.e., the commonly stated 'average' time it takes to turn a case into a fatality)
c19['deaths_period'] = 1
c19['deaths_period'].loc[c19['date'] > '2020-06-30'] += 1
c19['deaths_period'].loc[c19['date'] > '2020-10-22'] += 1
c19_r = c19.groupby(['fips', 'deaths_period'], as_index=True)['deaths'].last().unstack()
first_col = c19_r[1]
c19_r = c19_r.diff(axis=1)
c19_r[1] = first_col
c19_r['deaths_tot'] = c19_r.sum(axis=1)

#merge the cases and deaths data together again and rename the columns
c19 = c19_l.join(c19_r, rsuffix='dth')
c19.columns = ['cases_prcnt_1', 'cases_prcnt_2', 'cases_prcnt_3', 'cases_prcnt_tot',
               'deaths_prcnt_1', 'deaths_prcnt_2', 'deaths_prcnt_3', 'deaths_prcnt_tot']

#add the COVID 19 data to the features table and convert the case and death numbers to
#percentages as their column names suggest
data = data.join(c19)
data[c19.columns.to_list()] /= data[['popl']].values


########################
# Save the data
########################

if __name__=='__main__':
    data.to_csv('county_covid_and_demo_data.csv')

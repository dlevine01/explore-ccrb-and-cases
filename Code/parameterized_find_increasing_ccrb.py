
import pandas as pd
import geopandas as gpd
import altair as alt
import streamlit as st

st.set_page_config(
    layout='wide'
)

FADO_TYPES = (
        'Abuse of Authority', 
        'Discourtesy', 
        'Offensive Language', 
        'Force',
        'Untruthful Statement'
    )

PRECINCTS = ['1', '5', '6', '7', '9', '10', '13', '14', '17', '18', '19', '20', '22',
       '23', '24', '25', '26', '28', '30', '32', '33', '34', '40', '41', '42',
       '43', '44', '45', '46', '47', '48', '49', '50', '52', '60', '61', '62',
       '63', '66', '67', '68', '69', '70', '71', '72', '73', '75', '76', '77',
       '78', '79', '81', '83', '84', '88', '90', '94', '100', '101', '102',
       '103', '104', '105', '106', '107', '108', '109', '110', '111', '112',
       '113', '114', '115', '120', '121', '122', '123']



@st.cache_data(show_spinner='Loading CCRB records...')
def load_ccrb():

    ccrb_allegations = pd.read_csv(
        'https://data.cityofnewyork.us/api/views/6xgr-kwjq/rows.csv?accessType=DOWNLOAD',
        dtype={'Tax ID':str},
        parse_dates=['As Of Date']
        )

    ccrb_complaints = pd.read_csv(
        'https://data.cityofnewyork.us/api/views/2mby-ccnw/rows.csv?accessType=DOWNLOAD',
        dtype={'Tax ID':str},
        parse_dates=['Incident Date', 'CCRB Received Date','Close Date']
    )

    ccrb_complaints['Incident Date'] = pd.to_datetime(ccrb_complaints['Incident Date'], errors='coerce')
    
    ccrb_allegations = ccrb_allegations.merge(
        ccrb_complaints.drop(columns='As Of Date'), 
        on='Complaint Id'
    )

    ccrb_allegations = (
        ccrb_allegations
        .assign(
            command_normalized = (
                ccrb_allegations['Officer Command At Incident']
                .str.upper()
                .str.replace('(?<=\d) *TH','',regex=True)
                .str.replace('(?<=\d) *ND','',regex=True)
                .str.replace('(?<=\d) *RD','',regex=True)
                .str.replace('PCT[\. ]*','',regex=True)
                .str.replace('CMD','')
                .str.replace('PRECINCT','')
                .str.replace('PRE','')
                .str.replace('DET(ECTIVE)*','',regex=True)
                .str.replace('COMMAND','')
                .str.replace('SQUAD','')
                .str.replace('MTS','14')
                .str.replace('MIDTOWN SOUTH','14')
                .str.replace('MTN','18')
                .str.replace('MIDTOWN NORTH','18')
                .str.replace('CPK','22')
                .str.replace('POLICE SERVICE AREA','PSA')
                .str.replace('E.S.U.','E S U')
                .str.replace('NARC BBX','NARCBBX')
                .str.replace('NARCOTICS BOROUGH BRONX','NARCBBX')
                .str.replace('NARCBBN DIVISION','NARCBBN')
                .str.replace('BROOKLYN NORTH NARCOTICS','NARCBBN')
                .str.replace('NARCOTICS BOROUGH BROOKLYN NORTH','NARCBBN')
                .str.replace('BNNARC','NARCBBN')
                .str.replace('NARCBNN','NARCBBN')
                .str.replace('BROOKLYN SOUTH NARCOTICS','NARCBBS')
                .str.replace('NARC BBS','NARCBBS')
                .str.replace('NARCOTICS BOROUGH BROOKLYN SOUTH','NARCBBS')
                .str.replace('NARCOTICS BORO BROOKLYN SOUTH','NARCBBS')
                .str.replace('BROOKLYN SOUTH NARCOTICS DISTRICT','NARCBBS')
                .str.replace('NARCOTICS BORO STATEN ISLAND','NARCBSI')
                .str.replace('NARCOTICS BOROUGH STATEN ISLAND','NARCBSI')
                .str.replace('QS NARC','NARCBQS')
                .str.replace('MANHATTAN SOUTH NARCOTICS DISTRICT','NARCBMS')
                .str.replace('NARCOTICS BORO MANHATTAN NORTH','NARCBMN')
                .str.replace('WARRANT SECTION','WARRSEC')
                .str.replace('QS GANG','GANG QS')
                .str.replace('MANHATTAN GANG','GANG M')
                .str.replace('GANG MANHATTAN','GANG M')
                .str.replace('QUEENS GANG','GANG Q')
                .str.replace('STATEN ISLAND GANGS DIVISION','GANG SI')
                .str.replace('GANG  BROOKLYN SOUTH', 'GANG BS')
                .str.replace('BROOKLYN SOUTH GANG','GANG BS')
                .str.replace('BROOKLYN SOUTH GANG UNIT','GANG BS')
                .str.replace('BN GANG UNIT','GANG BN')
                .mask(lambda a: a == 'UNIDENTIFIED')
                .mask(lambda a: a == 'UNKNOWN')
                .str.strip()
                # .str.replace(' ','')
                .apply(pd.to_numeric, errors = 'ignore')
                .astype(str)
            )
        )
    )

    ccrb_allegations['CCRB disposition substantiated'] = ccrb_allegations['CCRB Allegation Disposition'].str.contains('Substantiated')

    return ccrb_allegations

@st.cache_data(show_spinner='Loading precincts map...')
def load_precincts():

    return (
        alt.Data(
            url='https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Police_Precincts/FeatureServer/0/query?where=1=1&outFields=Precinct&outSR=4326&f=pgeojson',
            format=alt.DataFormat(property='features')
        )
    )

#     precincts = (
#         gpd.read_file('https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Police_Precincts/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=pgeojson')
#         .set_index('Precinct')
#         .drop(columns=['OBJECTID','Shape__Area','Shape__Length'])
#     )

#     assert precincts.is_valid.all()

#     return precincts
    
@st.cache_data(show_spinner='Loading officers roster...')
def load_officers_by_command():
    roster = pd.read_csv(
        'https://data.cityofnewyork.us/api/views/2fir-qns4/rows.csv?date=20231205&accessType=DOWNLOAD',
        parse_dates=['Last Reported Active Date'],
        true_values=['Yes'],
        false_values=['No'],
        dtype={'Tax ID':str}
    )

    roster = (
        roster
        .assign(
            command_normalized = (
                ccrb_allegations['Officer Command At Incident']
                .str.upper()
                .str.replace('(?<=\d) *TH','',regex=True)
                .str.replace('(?<=\d) *ND','',regex=True)
                .str.replace('(?<=\d) *RD','',regex=True)
                .str.replace('PCT[\. ]*','',regex=True)
                .str.replace('CMD','')
                .str.replace('PRECINCT','')
                .str.replace('PRE','')
                .str.replace('DET(ECTIVE)*','',regex=True)
                .str.replace('COMMAND','')
                .str.replace('SQUAD','')
                .str.replace('MTS','14')
                .str.replace('MIDTOWN SOUTH','14')
                .str.replace('MTN','18')
                .str.replace('MIDTOWN NORTH','18')
                .str.replace('CPK','22')
                .str.replace('POLICE SERVICE AREA','PSA')
                .str.replace('E.S.U.','E S U')
                .str.replace('NARC BBX','NARCBBX')
                .str.replace('NARCOTICS BOROUGH BRONX','NARCBBX')
                .str.replace('NARCBBN DIVISION','NARCBBN')
                .str.replace('BROOKLYN NORTH NARCOTICS','NARCBBN')
                .str.replace('NARCOTICS BOROUGH BROOKLYN NORTH','NARCBBN')
                .str.replace('BNNARC','NARCBBN')
                .str.replace('NARCBNN','NARCBBN')
                .str.replace('BROOKLYN SOUTH NARCOTICS','NARCBBS')
                .str.replace('NARC BBS','NARCBBS')
                .str.replace('NARCOTICS BOROUGH BROOKLYN SOUTH','NARCBBS')
                .str.replace('NARCOTICS BORO BROOKLYN SOUTH','NARCBBS')
                .str.replace('BROOKLYN SOUTH NARCOTICS DISTRICT','NARCBBS')
                .str.replace('NARCOTICS BORO STATEN ISLAND','NARCBSI')
                .str.replace('NARCOTICS BOROUGH STATEN ISLAND','NARCBSI')
                .str.replace('QS NARC','NARCBQS')
                .str.replace('MANHATTAN SOUTH NARCOTICS DISTRICT','NARCBMS')
                .str.replace('NARCOTICS BORO MANHATTAN NORTH','NARCBMN')
                .str.replace('WARRANT SECTION','WARRSEC')
                .str.replace('QS GANG','GANG QS')
                .str.replace('MANHATTAN GANG','GANG M')
                .str.replace('GANG MANHATTAN','GANG M')
                .str.replace('QUEENS GANG','GANG Q')
                .str.replace('STATEN ISLAND GANGS DIVISION','GANG SI')
                .str.replace('GANG  BROOKLYN SOUTH', 'GANG BS')
                .str.replace('BROOKLYN SOUTH GANG','GANG BS')
                .str.replace('BROOKLYN SOUTH GANG UNIT','GANG BS')
                .str.replace('BN GANG UNIT','GANG BN')
                .mask(lambda a: a == 'UNIDENTIFIED')
                .mask(lambda a: a == 'UNKNOWN')
                .str.strip()
                # .str.replace(' ','')
                .apply(pd.to_numeric, errors = 'ignore')
                .astype(str)
            )
        )
    )
        
    active_officers_by_command = (
        roster
        [
            roster['Active Per Last Reported Status']
        ]
        .groupby('command_normalized')
        ['Tax ID']
        .nunique()
    )

    return active_officers_by_command

@st.cache_data(show_spinner='Loading crime rates...')
def load_index_crimes():
    return (
        pd.read_csv(
            'Data/Processed Data/index_crimes_by_precinct_2023.csv',
            dtype={'precinct':str}
        )
        .rename(columns={'precinct':'command_normalized'})
        .set_index('command_normalized')
        ['index_crimes_2023']
    )

@st.cache_data(show_spinner='Loading cases...')
def load_cases():
    return pd.read_parquet('Data/Processed Data/cases_dates_locations.parquet')


ccrb_allegations = load_ccrb()
precincts = load_precincts()
active_officers_by_command = (
    load_officers_by_command()
    .reindex(
        ccrb_allegations
        ['command_normalized']
        .dropna()
        .drop_duplicates()
        .values
    )
)
index_crimes = load_index_crimes()
cases = load_cases()

## layout

## options sidebar

with st.sidebar:

    ## select options

    st.markdown('''
    ### CCRB complaints options
    ''')
    
    fado_types_selected = st.multiselect(
        label='FADO types:',
        options=FADO_TYPES,
        default=FADO_TYPES
    )

    substantiated_only_selected = st.toggle(
        label='Substantiated complaints only',
        value=False
    )

    normalize_by_selected = st.radio(
        label='Normalize by:',
        options=(
            'None',
            'Currently active officers',
            'Index crimes'
        )
    )

    reference_start_year, reference_end_year = st.slider(
        label='Reference years (annual mean):',
        min_value=2000,
        max_value=2023,
        value=(2014,2020)
    )

    focus_start_year, focus_end_year = st.slider(
        label='Focus years (annual mean):',
        min_value=2000,
        max_value=2023,
        value=(2021,2023)
    )

    minimum_instances_threshold = st.slider(
        label='Hide precincts/commands without this many complaints in at least one year of either period',
        min_value=0,
        max_value=25,
        value=3
    )

    geographic_precincts_only_selector = st.toggle(
        label='Show geographic precincts only (exclude other commands e.g. Narcotics)',
        value=False
    )

    st.markdown('''
    ### Cases/litigation options
    ''')

    ## case selection options

    with_settlement_only_selected = st.toggle(
        label='With settlement payment only',
        value=False
    )

    # case types filter

    case_summary_selected = st.radio(
        label='Summarize cases by:',
        options=(
            'Count of cases',
            'Settlement grand total',
            'Median settlement'
        ),
        horizontal=True
    )


ccrb_column, cases_column = st.columns(2, gap='large')

with ccrb_column:
  
    ## filter and summarize data

    fado_type_filter = (
        ccrb_allegations
        ['FADO Type']
        .isin(fado_types_selected)
    )

    substantiated_filter = (
        ccrb_allegations['CCRB disposition substantiated'] 
        if substantiated_only_selected 
        else 
        [True] * len(ccrb_allegations)
    )

    normalizer = (
        active_officers_by_command if normalize_by_selected == 'Currently active officers' 
        else index_crimes if normalize_by_selected == 'Index crimes'
        else 1
    )

    count_by_year_by_command = (
        ccrb_allegations
        [
            fado_type_filter
            &
            substantiated_filter
        ]
        .assign(
            incident_year = lambda row: row['Incident Date'].dt.year
        )
        .groupby([
            'incident_year',
            'command_normalized'
        ])
        ['Complaint Id']
        .nunique()
        .rename('count_complaints')
    )

    st.dataframe(count_by_year_by_command)

    st.dataframe(normalizer)

    st.write(normalizer.index.dtypes)

    st.dataframe(
        count_by_year_by_command
        .div(normalizer)
    )

    normalized_by_year_by_command = (
        count_by_year_by_command
        .div(normalizer)
    )

    st.dataframe(normalized_by_year_by_command)

    change_by_precinct = (
        (
            normalized_by_year_by_command
            .loc[reference_start_year:reference_end_year]
            .groupby('command_normalized')
            .mean()
            .rename('reference_years')
            .to_frame()
        ).join(
            normalized_by_year_by_command
            .loc[focus_start_year:focus_end_year]
            .groupby('command_normalized')
            .mean()
            .rename('focus_years')
        )
        .fillna(0)
        .assign(
            pct_change = lambda row: row.pct_change(axis=1)['focus_years'],
        )
        .dropna(subset='pct_change')
        .sort_values('pct_change',ascending=False)
    )

    if geographic_precincts_only_selector:
        change_by_precinct = (
            change_by_precinct
            .loc[PRECINCTS]
            .sort_values('pct_change',ascending=False)
        )

    change_by_precinct_filtered_to_more_than_threshold_instances = (
        change_by_precinct
        [
            (
                count_by_year_by_command
                .loc[reference_start_year:reference_end_year]
                .groupby('command_normalized')
                .max()
                .ge(minimum_instances_threshold)
            ) & (
                count_by_year_by_command
                .loc[focus_start_year:focus_end_year]
                .groupby('command_normalized')
                .max()
                .ge(minimum_instances_threshold)
            )
        ]
    )

    complaints_title = f"""
    ###### {'Substantiated' if substantiated_only_selected else 'All'} complaints of type(s) {', '.join(fado_types_selected)} {', per '+ normalize_by_selected if normalize_by_selected != 'None' else ''}\n
    ###### Comparing years {reference_start_year}-{reference_end_year} to {focus_start_year}-{focus_end_year}\n
    {'Showing only geographic precincts' if geographic_precincts_only_selector > 0 else ''}\n
    {'Showing precincts/commands with at least ' + str(minimum_instances_threshold) + ' complaints in at least one year of each period' if minimum_instances_threshold > 0 else ''}
    """

    st.markdown(complaints_title)

    st.dataframe(
        change_by_precinct_filtered_to_more_than_threshold_instances
        .reset_index()
        .rename(columns={
            'command_normalized':'Precinct/command',
            'reference_years':'Reference years (annual mean)',
            'focus_years':'Focus years (annual mean)',
            'pct_change':'Pct change'
        })
        .set_index('Precinct/command')
        .style.format({
            'Reference years (annual mean)':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.1f}',
            'Focus years (annual mean)':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.1f}',
            'Pct change':'{:.0%}'
        })
    )

    complaints_map = (
        alt.Chart(precincts)
        .mark_geoshape(
            color='white',
            stroke='lightgrey'
        )
    ) + (
        alt.Chart(
            precincts
        )
        .transform_calculate(
            command_normalized = 'toString(datum.properties.Precinct)'
        )
        .transform_lookup(
            lookup='command_normalized',
            from_=alt.LookupData(
                data=change_by_precinct_filtered_to_more_than_threshold_instances.reset_index(),
                key='command_normalized',
                fields=['pct_change']
            )
        )
        .mark_geoshape()
        .encode(
            color=alt.Color(
                'pct_change:Q',
                title='Pct change',
                scale=alt.Scale(scheme='purpleorange', domainMid=0),
                legend=alt.Legend(
                    format='.0%'
                )
            ),
            tooltip=[
                alt.Tooltip(
                    'command_normalized:N',
                    title='Precinct'
                ),
                alt.Tooltip(
                    'pct_change:Q',
                    title='Pct change',
                    format='.0%'
                )
            ]
        ).project(
            type='mercator'
        )
    )

    st.altair_chart(complaints_map)

    top_10_precincts = (
        change_by_precinct_filtered_to_more_than_threshold_instances
        .head(10)
        .index
    )


    top_10_trend_line_chart = (
        normalized_by_year_by_command
        .loc[reference_start_year:focus_end_year,top_10_precincts]
        .reset_index()
        .where(lambda row: row['command_normalized'] != 'nan').dropna()
        # .dropna(subset='command_normalized')
        .pipe(alt.Chart)
        .mark_line(
            point='transparent'
        )
        .encode(
            x=alt.X(
                'incident_year:Q',
                title='Incident year',
                axis=alt.Axis(
                    format='.0f',
                    tickMinStep=1
                )
            ),
            y=alt.Y(
                'count_complaints:Q',
                title='Complaints'
            ),
            color=alt.Color(
                'command_normalized:N',
                title='Precinct/command'
            ),
            tooltip=[
                alt.Tooltip(
                    'command_normalized',
                    title='Precinct/command'
                ),
                alt.Tooltip(
                    'count_complaints',
                    title='Complaints'
                )
            ]
        )
    )

    ranges = pd.DataFrame({
        'start':[reference_start_year, focus_start_year],
        'end':[reference_end_year, focus_end_year],
        'range':['Reference years','Focus years']
    })

    shading = (
            alt.Chart(ranges)
            .mark_rect(
                opacity=0.1
            )
            .encode(
                x='start:Q',
                x2='end:Q',
                y=alt.value(0),
                y2=alt.value(250),
                color=alt.Color(
                    'range',
                    # legend=None
                ),
                tooltip=alt.value(None)
            )
        )

    # st.altair_chart(top_10_trend_line_chart)

    st.altair_chart(
        (top_10_trend_line_chart + shading)
        .resolve_scale(
            color='independent'    
        ),
        use_container_width=True
    )

with cases_column:

    ## summarize cases

    if with_settlement_only_selected:
        cases_subset = (
            cases
            [
                cases['Total City Payout AMT'] > 0
            ]
        )

    else:
        cases_subset = cases.copy(deep=True)


    if case_summary_selected == 'Count of cases':

        cases_summary = (
            cases_subset
            .groupby('command_normalized')
            .size()
            .sort_values(ascending=False)
            .rename(case_summary_selected)
        )

    elif case_summary_selected == 'Settlement grand total':

        cases_summary = (
            cases_subset
            .groupby('command_normalized')
            ['Total City Payout AMT']
            .sum()
            .sort_values(ascending=False)
            .rename(case_summary_selected)
        )

    elif case_summary_selected == 'Median settlement':

        cases_summary = (
            cases_subset
            .groupby('command_normalized')
            ['Total City Payout AMT']
            .median()
            .sort_values(ascending=False)
            .rename(case_summary_selected)
        )

    complaints_title = f"""
    ###### {case_summary_selected} by precinct
    {'Showing only cases with settlement payment' if with_settlement_only_selected else ''}\n
    """

    st.markdown(complaints_title)

    st.dataframe(
        cases_summary
        .reset_index()
        .rename(columns={
            'command_normalized':'Precinct/command',
        })
        .set_index('Precinct/command')
        .style.format({
            'Count of cases':'{:,.0f}',
            'Settlement grand total':'$ {:,.2f}',
            'Median settlement':'$ {:,.2f}'
        })
    )

    cases_map = (
        alt.Chart(precincts)
        .mark_geoshape(
            color='white',
            stroke='lightgrey'
        )
    ) + (
        alt.Chart(
            precincts
        )
        .transform_calculate(
            command_normalized = 'toString(datum.properties.Precinct)'
        )
        .transform_lookup(
            lookup='command_normalized',
            from_=alt.LookupData(
                data=cases_summary.reset_index(),
                key='command_normalized',
                fields=[case_summary_selected]
            )
        )
        .mark_geoshape()
        .encode(
            color=alt.Color(
                f'{case_summary_selected}:Q',
                title=case_summary_selected,
                scale=alt.Scale(scheme='purplered'),
                # legend=alt.Legend(
                #     format='.0%'
                # )
            ),
            tooltip=[
                alt.Tooltip(
                    'command_normalized:N',
                    title='Precinct'
                ),
                alt.Tooltip(
                    f'{case_summary_selected}:Q',
                    # title='Pct change',
                    # format='.0%'
                )
            ]
        ).project(
            type='mercator'
        )
    )

    st.altair_chart(cases_map)


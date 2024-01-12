
import pandas as pd
# import geopandas as gpd
import altair as alt
import streamlit as st

# from io import BytesIO
# import xlsxwriter

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

with st.expander(label='Set options',expanded=True):

    ## select options

    st.write("##### Normalize")

    normalize_by_selected = st.radio(
        label='Normalize by:',
        options=(
            'None',
            'Currently active officers',
            'Index crimes'
        ),
        horizontal=True
    )

    st.write("##### CCRB complaints options")
    
    fado_types_selected = st.multiselect(
        label='FADO types:',
        options=FADO_TYPES,
        default=FADO_TYPES
    )

    substantiated_only_selected = st.toggle(
        label='Substantiated complaints only',
        value=False
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

    st.write("##### Cases/litigation options")

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


normalized_by_year_by_command = (
    count_by_year_by_command
    .div(normalizer)
    .rename('count_complaints')
)

average_complaints = (
    normalized_by_year_by_command
    .unstack()
    .mean(
        axis=1, 
        skipna=True
    )
    .rename('count_complaints')
)

median_complaints = (
    normalized_by_year_by_command
    .median(axis=0, skipna=True)
)

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

change_by_precinct_filtered__labeled = (
    change_by_precinct_filtered_to_more_than_threshold_instances
    .reset_index()
    .rename(columns={
        'command_normalized':'Precinct/command',
        'reference_years':'Reference years (annual mean)',
        'focus_years':'Focus years (annual mean)',
        'pct_change':'Pct change'
    })
    .set_index('Precinct/command')
)

top_10_precincts = (
    change_by_precinct_filtered_to_more_than_threshold_instances
    .head(10)
    .index
)

precincts_ranks = (
    normalized_by_year_by_command
    .unstack()
    .drop(columns='nan')
    .rank(
        axis=1,
        method='min',
        ascending=False
    )
    .stack()
    .rename('rank')
)

complaints_params = (
    f"{'Substantiated' if substantiated_only_selected else 'All'} complaints of type(s): {', '.join(fado_types_selected)}",
    f"{'per '+ normalize_by_selected if normalize_by_selected != 'None' else ''}",
    f"Comparing years {reference_start_year}-{reference_end_year} to {focus_start_year}-{focus_end_year}",
    f"{'Showing only geographic precincts' if geographic_precincts_only_selector > 0 else ''}",
    f"{'Showing precincts/commands with at least ' + str(minimum_instances_threshold) + ' complaints in at least one year of each period' if minimum_instances_threshold > 0 else ''}" 
)

complaints_title = '\n\n'.join(complaints_params)

ranges = pd.DataFrame({
    'start':[reference_start_year, focus_start_year],
    'end':[reference_end_year, focus_end_year],
    'range':['Reference years','Focus years']
})

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
        .div(normalizer)
        .sort_values(ascending=False)
        .rename(case_summary_selected)
    )

elif case_summary_selected == 'Settlement grand total':

    cases_summary = (
        cases_subset
        .groupby('command_normalized')
        ['Total City Payout AMT']
        .sum()
        .div(normalizer)
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

cases_params = (
    f"{case_summary_selected} by precinct",
    f"{'per '+ normalize_by_selected if normalize_by_selected != 'None' else ''}",
    f"{'Showing only cases with settlement payment' if with_settlement_only_selected else ''}"
)

cases_title = '\n\n'.join(cases_params)


## build visuals

# highlight = alt.selection_point(
#     on='click', 
#     fields=['command_normalized'], 
#     # nearest=True,
#     empty=False
# )

# complaints_map_base = (
#     alt.Chart(
#         precincts
#     )
#     .transform_calculate(
#         command_normalized = 'toString(datum.properties.Precinct)'
#     )
#     .transform_lookup(
#         lookup='command_normalized',
#         from_=alt.LookupData(
#             data=change_by_precinct_filtered_to_more_than_threshold_instances.reset_index(),
#             key='command_normalized',
#             fields=['pct_change']
#         )
#     )
#     .mark_geoshape()
#     .encode(
#         color=alt.Color(
#             'pct_change:Q',
#             title='Pct change',
#             scale=alt.Scale(scheme='purpleorange', domainMid=0),
#             legend=alt.Legend(
#                 format='.0%'
#             )
#         ),
#         # stroke=alt.condition(
#         #     highlight, 
#         #     alt.value('black'), 
#         #     alt.value(None)
#         # ),
#         # strokeWidth=alt.condition(
#         #     highlight, 
#         #     alt.value(3), 
#         #     alt.value(0.5)
#         # )
#     )
#     .project('mercator')
#     # .add_params(highlight)
# )

# complaints_map_fill = (
#     complaints_map_base
#     .mark_geoshape()
#     .encode(
#         color=alt.Color(
#             'pct_change:Q',
#             title='Pct change',
#             scale=alt.Scale(scheme='purpleorange', domainMid=0),
#             legend=alt.Legend(
#                 format='.0%'
#             )
#         )
#     )
# )

# complaints_map_outline = (
#     complaints_map_base
#     # .mark_geoshape(
#     #     fill=None,
#     #     opacity=1
#     # )
#     .encode(
#         stroke=alt.condition(
#             highlight, 
#             alt.value('black'), 
#             alt.value(None)
#         ),
#         strokeWidth=alt.condition(
#             highlight, 
#             alt.value(3), 
#             alt.value(0.5)
#         )
#     )
# )

# complaints_map = complaints_map_base


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

top_10_trend_line_chart = (
    normalized_by_year_by_command
    .loc[reference_start_year:focus_end_year,top_10_precincts]
    .reset_index()
    .where(lambda row: row['command_normalized'] != 'nan').dropna()
    # .dropna(subset='command_normalized')
    .pipe(alt.Chart, title='Annual measure')
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
            title='Precinct/command',
            legend=alt.Legend(columns=2)
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

average_trend_chart = (
    average_complaints
    .loc[reference_start_year:focus_end_year]
    .reset_index()
    .assign(
        Average = 'Average'
    )
    .pipe(alt.Chart)
    .mark_line(
        strokeWidth=4,
        color='grey',
        strokeDash=(4,3)
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
        color='Average'
    )
)

precincts_rank_chart =(
    precincts_ranks
    .loc[reference_start_year:focus_end_year,top_10_precincts]
    .reset_index()
    .pipe(alt.Chart, title='Annual rank')
    .mark_line(
        point=True
    )
    .encode(
        x=alt.X(
            'incident_year:Q',
            title='Incident year',
            axis=alt.Axis(
                format='.0f',
                tickMinStep=1
            ),
        ),
        y=alt.Y(
            'rank',
            scale=alt.Scale(
                reverse=True
            ),
        ),
        color=alt.Color(
            'command_normalized',
            legend=alt.Legend(columns=2)
        ),
        tooltip=[
            'command_normalized',
            'rank'
        ]
    )
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


## layout and place elements



# titles/params
with st.container():
    
    ccrb_title_col, cases_title_col = st.columns(2, gap='small')

    with ccrb_title_col:
        st.write(complaints_title)
    
    with cases_title_col:
        st.write(cases_title)

# tables and data
with st.container():
    
    ccrb_table_col, cases_table_col = st.columns(2, gap='small')

    with ccrb_table_col:
        st.dataframe(
            change_by_precinct_filtered__labeled
            .style.format({
                'Reference years (annual mean)':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.1f}',
                'Focus years (annual mean)':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.1f}',
                'Pct change':'{:.0%}'
            })
        )

        st.altair_chart(complaints_map)

        st.altair_chart(
            (top_10_trend_line_chart + shading + average_trend_chart)
            .resolve_scale(
                color='independent'    
            ),
            use_container_width=True
        )
        
        st.altair_chart(
            (precincts_rank_chart + shading)
            .resolve_scale(
                color='independent'    
            ),
            use_container_width=True
        )

    with cases_table_col:
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

        st.altair_chart(cases_map)

# download buttons
with st.container():
    
    ccrb_download_col, cases_download_col = st.columns(2,gap='small')

    with ccrb_download_col:

        complaints_pct_change_output = (
            pd.concat([
                pd.Series(
                    complaints_params,
                    name='params'
                ),
                (
                    change_by_precinct_filtered__labeled
                    .reset_index()
                )
            ],axis=1)
        )

        st.download_button(
            label='Download complaints pct change',
            data=complaints_pct_change_output.to_csv(index=False),
            file_name='complaints_pct_change.csv',
            mime='text/csv'
        )

        complaints_annual_detail_output = (
            pd.concat([
                pd.Series(
                    complaints_params,
                    name='params'
                ),
                (
                    normalized_by_year_by_command
                    .rename_axis(index=['Year','Precinct/command'])
                    .unstack('Year')
                    .reset_index()
                )
            ],axis=1)
        )

        st.download_button(
            label='Download complaints by precinct by year',
            data=(
                complaints_annual_detail_output
                .to_csv(index=False)
            ),
            file_name='complaints_by_precinct_by_year.csv',
            mime='text/csv'
        )


        # output = BytesIO()
        # # workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # with pd.ExcelWriter(path=output, mode='w') as writer:

        #     # parameters_sheet = workbook.add_worksheet(name='parameters')
        #     # parameters_sheet.write('A1', complaints_title)

        #     (
        #         change_by_precinct_filtered__labeled
        #         .to_excel(
        #             writer,
        #             sheet_name='pct_change'
        #         )
        #     )

        #     (
        #         normalized_by_year_by_command
        #         .unstack()
        #         .to_excel(
        #             writer,
        #             sheet_name='by_precinct_by_year'
        #         )
        #     )


        #     st.download_button(
        #         label="Download Excel workbook",
        #         data=output.getvalue(),
        #         file_name="workbook.xlsx",
        #         mime="application/vnd.ms-excel"
        #     )


        # st.download_button(
        #     label='Download pct change',
        #     data=(
        #             pd.concat([
        #             pd.DataFrame({'Parameters':complaints_params}),
        #             change_by_precinct_filtered__labeled.reset_index()
        #         ])
        #         .to_csv(index=False)
        #     ),
        #     file_name='complaints_pct_change.csv',
        #     mime='text/csv'
        # )

        # st.download_button(
        #     label='Download annual detail',
        #     data=(
        #             pd.concat([
        #             pd.DataFrame({'Parameters':complaints_params}),
        #             (
        #                 normalized_by_year_by_command
        #                 .rename_axis(index=['Year','Precinct/command'])
        #                 .unstack()
        #             )
        #         ])
        #         .to_csv()
        #     ),
        #     file_name='complaints_by_precinct_by_year.csv',
        #     mime='text/csv'
        # )
    
    with cases_download_col:


        cases_output = pd.concat([
            pd.Series(
                cases_params,
                name='params'
            ),
            (
                cases_summary
                .reset_index()
                .rename(columns={
                    'command_normalized':'Precinct/command',
                })
            )
        ],axis=1)

        
        st.download_button(
            label='Download cases summary',
            data = cases_output.to_csv(index=False),
            file_name='cases_summary.csv',
            mime='txt/csv'
        )

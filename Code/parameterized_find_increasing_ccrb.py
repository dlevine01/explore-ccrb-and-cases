
import pandas as pd
import geopandas as gpd
import altair as alt
import streamlit as st

FADO_TYPES = (
        'Abuse of Authority', 
        'Discourtesy', 
        'Offensive Language', 
        'Force',
        'Untruthful Statement'
    )

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
                .mask(lambda a: a == 'UNIDENTIFIED')
                .mask(lambda a: a == 'UNKNOWN')
                .str.strip()
                .apply(pd.to_numeric, errors = 'ignore')
            )
        )
    )

    ccrb_allegations['CCRB disposition substantiated'] = ccrb_allegations['CCRB Allegation Disposition'].str.contains('Substantiated')

    return ccrb_allegations

# @st.cache_data(show_spinner='Loading precincts map...')
# def load_precincts():
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
                .mask(lambda a: a == 'UNIDENTIFIED')
                .mask(lambda a: a == 'UNKNOWN')
                .str.strip()
                .apply(pd.to_numeric, errors = 'ignore')
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
       pd.read_csv('Data/Processed Data/index_crimes_by_precinct_2023.csv')
        .rename(columns={'precinct':'command_normalized'})
        .set_index('command_normalized')
        ['index_crimes_2023']
    )

ccrb_allegations = load_ccrb()
# precincts = load_precincts()
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

## select options

fado_types_selected = st.multiselect(
    label='FADO types:',
    options=FADO_TYPES,
    default=FADO_TYPES
)

substantiated_only_selected = st.toggle(
    label='Substantiated only:',
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
    label='Reference years:',
    min_value=2000,
    max_value=2023,
    value=(2015,2021)
)

focus_start_year, focus_end_year = st.slider(
    label='Focus years:',
    min_value=2000,
    max_value=2023,
    value=(2022,2023)
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

subset_aggregation = (
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
    .div(normalizer)
)

change_by_precinct = (
    (
        subset_aggregation
        .loc[reference_start_year:reference_end_year]
        .groupby('command_normalized')
        .mean()
        .rename('reference_years')
        .to_frame()
    ).join(
        subset_aggregation
        .loc[focus_start_year:focus_end_year]
        .groupby('command_normalized')
        .mean()
        .rename('focus_years')
    )
    .fillna(0)
    .assign(
        pct_change = lambda row: row.pct_change(axis=1)['focus_years'],
    )
    .sort_values('pct_change',ascending=False)
)

st.dataframe(
    change_by_precinct
    .style.format({
        'reference_years':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.0f}',
        'focus_years':'{:.3f}' if isinstance(normalizer, pd.Series) else '{:.0f}',
        'pct_change':'{:.0%}'
    })
)

simple_map = (
    change_by_precinct
    .reset_index()
    .pipe(alt.Chart)
    .mark_geoshape()
    .transform_lookup(
        lookup='command_normalized',
        from_=alt.LookupData(
            data=alt.Data(
                url='https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Police_Precincts/FeatureServer/0/query?where=1=1&outFields=Precinct&outSR=4326&f=pgeojson',
                format=alt.DataFormat(property='features')
            ),
            key='properties.Precinct',
            fields=['type','geometry'])
    ).encode(
        color=alt.Color(
            'pct_change:Q',
            scale=alt.Scale(scheme='purpleorange', domainMid=0),
            legend=alt.Legend(
                format='.0%'
            )
        ),
        tooltip=[
            'command_normalized:N',
            alt.Tooltip(
                'pct_change:Q',
                format='.0%'
            )
        ]
    ).project(
        type='mercator'
    )
)

st.altair_chart(simple_map)



import pandas as pd
import numpy as np
import streamlit as st
from numpy import float64
import matplotlib.pyplot as plt
import httpx
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo
#from streamlit_folium import st_folium

@st.cache_data
def load_stations():
    stationen = pd.read_csv('https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting/ogd-local-forecasting_meta_point.csv', encoding='latin-1', sep=';')
    print(f'Die möglichen Orte wurden geladen. Es stehen {len(stationen)} Stationen zur Auswahl.')
    return stationen

@st.cache_data
def load_metadata():
    STAC_BASE_URL  = "https://data.geo.admin.ch/api/stac/v1"
    collection  = "ch.meteoschweiz.ogd-local-forecasting"
    # die Metadaten zeigen die Abkürzungen der Messdaten wie etwa Wind und die entsprechenden Einheiten
    url_metadata   = (
    f"https://data.geo.admin.ch/{collection}/"
    "ogd-local-forecasting_meta_parameters.csv")

def wide_space_default():
    st.set_page_config(layout='wide')
wide_space_default()

st.title('Wetto-App')
st.write('STAC API-Test')
    
# --- session state init ---
if "applied" not in st.session_state:
    st.session_state.applied = False

stationen = load_stations()
orte = sorted(set(stationen.point_name.tolist()))

with st.form("filter_form"):
    selected_station = st.multiselect(
            "Messstation auswählen",
            orte)
    submitted = st.form_submit_button("Ort auswählen")
    
if submitted:
    st.session_state.applied = True
    st.session_state.selected_station = selected_station
    
    st.write('Ausgewählter Ort: ', selected_station)
    submitted = st.form_submit_button("Anwenden")
    

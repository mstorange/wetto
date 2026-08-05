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
    # auswählbar sind nur jene, die auch Stationen sind! Aadorf bspw. daher nicht
    stationen = stationen[stationen['point_type_de']=='Station'].reset_index(drop=True)
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
    resp = httpx.get(url_metadata, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    meta_df = pd.read_csv(StringIO(resp.content.decode("latin-1")), sep=";")
    print(f'{len(meta_df)} Parameter, die Wetter beschreiben wurden via meta_df geladen.')
    return meta_df

@st.cache_data
def get_download_links():
    STAC_BASE_URL  = "https://data.geo.admin.ch/api/stac/v1"
    collection  = "ch.meteoschweiz.ogd-local-forecasting"
    LOCAL_TZ = ZoneInfo("Europe/Zurich")
    today_id = f"{datetime.now(LOCAL_TZ).strftime('%Y%m%d')}-ch"
    item_url = f"{STAC_BASE_URL}/collections/{collection}/items/{today_id}"
    with httpx.Client() as client:
        item = client.get(item_url)
        item.raise_for_status()
        stac_item = item.json()
    assets = stac_item['assets']
    print(f'Für die von uns ausgewählten Parameter wurden {len(assets)} Datensatz-Links gefunden, über welche die Daten dann heruntergeladen werden können.')
    #print(assets)
    return assets

@st.cache_data
def build_data_dict(all_params, assets):
    param_urls = {} # hier in diesem dict haben wir dann parameter_shortname: downloadlink
    for param in all_params:
        for key, asset in assets.items():
            if param in key: # falls die character sequence in dem key (param shortname) drin ist...
                param_urls[param] = asset['href'] # hier ergänzen wir den obigen dict um den shortname (key) und den Downloadlink (href) als value, nimmt den aktuellsten Datensatz, weil dieser zuoberst sein sollte
                break
    print(f"\n{len(param_urls)}/{len(all_params)} parameters matched to asset URLs")
    print('Das ist nun der param_urls dict: ', param_urls)
    return param_urls

@st.cache_data
def download_raw_data(param_urls):
    raw_data = {}
    with httpx.Client(timeout=30.0) as client:
        for param, url in param_urls.items():
            resp = client.get(url)
            if resp.status_code == 200:
                raw_data[param] = resp.content # zu dem raw_data dict dazufügen
            else:
                print(f'HTTP response code {resp.status_code} for {param}')
    print(f"✓ Es wurden {len(raw_data)}/{len(param_urls)} Datensätze für die ausgewählten Parameter heruntergeladen.")
    return raw_data
    

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
    ort = st.selectbox(
            "Messstation auswählen",
            orte)
    submitted = st.form_submit_button("Ort auswählen")
    
if submitted:
    st.session_state.applied = True
    st.session_state.ort = ort

    st.write('Ausgewählter Ort: ', ort)

    # Parameter laden
    meta_df = load_metadata()
    st.write('Folgende Parameter sind in den Daten verfügbar:')
    st.write(meta_df)
    #print(meta_df)


    # wir brauchen nun die point_id und die point_type_id
    st.write(f'Variable st.sessions_state.ort is of type {type(st.session_state.ort)} and returns {st.session_state.ort}.')
    #st.write(stationen)
    point_id = stationen[(stationen['point_name']==st.session_state.ort)&(stationen['point_type_de']=='Station')]['point_id'].values[0]
    st.write('point_id: ', point_id)
    point_type_id = stationen[(stationen['point_name']==st.session_state.ort)&(stationen['point_type_de']=='Station')]['point_type_id'].values[0]
    st.write('point_type_id: ', point_type_id)

    # wir bauen nun dicts, um vom shortname auf die normalen Namen, die Unit und die Parameter-Kurzbeschreibung zuzugreifen
    param_unit = dict(zip(meta_df["parameter_shortname"], meta_df["parameter_unit"]))
    param_group = dict(zip(meta_df["parameter_shortname"], meta_df["parameter_group_de"]))
    params_dict = dict(zip(meta_df['parameter_shortname'], meta_df['parameter_description_de']))

    # nun definieren wir, welche Parameter wir brauchen wollen
    lang = 'de'
    selected_params = ['rka150p0', 'rre150h0', 'rreq10h0', 'rreq90h0', 'sre000h0', 'tre200pn', 'tre200px', 'treq10h0', 'treq90h0','tre200h0']
    print('Folgende Parameter wurden ausgewählt und können dann analysiert bzw. dargestellt werden: ', [param_group[i] for i in selected_params])

    # nun holen wir uns den dict, welcher die Download-Links der Datensätze enthält (assets)
    assets = get_download_links()

    # wenn wir dann die variable ort brauchen, müssen wir sie wohl via st.session_state.ort aufrufen
    param_urls = build_data_dict(selected_params, assets)
    #st.write('param_urls dict: ', param_urls)

    # jetzt effektiv die Datensätze runterladen
    st.write('Jetzt muesch chli Geduld ha (ca. 30 sek), bis ich all das Dategschmäus abeglade han...')
    raw_data = download_raw_data(param_urls)
    st.write('Folgende Daten haben wir nun heruntergeladen: ', [params_dict[i] for i in raw_data.keys()])

    # nun bauen wir aus den heruntergeladenen Daten ein df, welches alle Daten beinhaltet
    ersterparam = list(raw_data.keys())[0]
    df_example = pd.read_csv(StringIO(raw_data[ersterparam].decode("latin-1")), sep=";", parse_dates=["Date"])
    df_example = df_example[(df_example['point_id'] == int(point_id)) & (df_example['point_type_id'] == int(point_type_id))]
    df_example = df_example.drop(columns=[ersterparam])

    for param in raw_data.keys(): # hier fügen wir nun alle Daten dem df_example dazu
    # print(param)
        df = pd.read_csv(StringIO(raw_data[param].decode("latin-1")), sep=";", parse_dates=["Date"])
        df = df[(df['point_id'] == int(point_id)) & (df['point_type_id'] == int(point_type_id))].reset_index(drop=True)
        df_example = df_example.merge(df, on=["Date", "point_id", "point_type_id"], how="outer")

    # wir ersetzen die Spaltennamen durch die ganzen Namen der Parameter statt die kryptischen shortnames
    for col in df_example.columns:
        if col in ['point_id', 'point_type_id', 'Date']:
            continue
        else:
            # print(col)
            df_example = df_example.rename(columns={col:params_dict[col]})

    # insights
    st.write(f'Wir haben folgende Werte {df_example.columns} von heute bis {df_example['Date'].max()}')
    st.write(df_example)

    # nun wollen wir in Worten wiedergeben, wie das Wetter morgen wird
    tmrw = datetime.today().date()+timedelta(days=1)
    tmrw = tmrw.strftime(format='%Y-%m-%d %H:%M:%S')

    df_morgen = df_example[df_example['Date']==tmrw].reset_index(drop=True)
    st.write(df_morgen)

    n = df_morgen['Niederschlag; Tagessumme 00:00 - 24:00 Lokalzeit'][0]
    t_max = df_morgen['Lufttemperatur 2 m über Boden; Tagesmaximum 00:00 - 24:00 Lokalzeit'][0]
    t_min = df_morgen['Lufttemperatur 2 m über Boden; Tagesminimum 00:00 - 24:00 Lokalzeit'][0]

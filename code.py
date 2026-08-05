import pandas as pd
import numpy as np
import streamlit as st
from numpy import float64 
import matplotlib.pyplot as plt
import httpx
from io import StringIO
from datetime import datetime, timedelta
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

@st.cache_data
def echo_temp(t_max): #t_max ist die Tagesmaxtemp und n der Niederschlag
    if t_max < 0:
        t = 'wirds morn arschchalt und '
    elif t_max < 10:
        t = 'wirds morn nöd über 10° C und '
    elif t_max < 20:
        t = 'wirds morn temperaturmässig nöd über 20°C und '
    elif t_max < 25:
        t = 'wirds morn richtig schön agnehm warm und '
    elif t_max < 30:
        t = 'chunnsch morn scho recht ischs Schwitze (max. unter 30°C) und '
    else:
        t = 'wirds morn e Affehitz und '
    return t # als string

@st.cache_data
def echo_perc(n):
    if n == 0:
        m = 'es regnet kein Tropfe.'
    elif n < 5:
        m = 'es regnet fast gar nöd.'
    elif n < 20:
        m = 'es chönnt di schono verregne.'
    elif n < 40:
        m = 'regetechnisch gohts huere ab.'
    else:
        m = 'es seicht wie wahnsinnig.'
    return m




def wide_space_default():
    st.set_page_config(layout='wide')
wide_space_default()

st.header('Wetto-App :sunglasses:')
st.write('Duesch enart eifach une din Ort uswähle und denn bestätige und nocher spuckts une d Prognose für morn und d Grafike für die nöchste 10 Täg use')
    
# --- session state init ---
if "applied" not in st.session_state:
    st.session_state.applied = False

stationen = load_stations()
orte = sorted(set(stationen.point_name.tolist()))

with st.form("filter_form"):
    ort = st.selectbox(
            "Messstation uswähle",
            orte)
    submitted = st.form_submit_button("Ort bestätige")
    
if submitted:
    st.session_state.applied = True
    st.session_state.ort = ort

    st.write('Du hesch de Ort usgwählt: ', ort)

    # Parameter laden
    meta_df = load_metadata()
    #st.write('Folgende Parameter sind in den Daten verfügbar:')
    #st.write(meta_df)
    #print(meta_df)


    # wir brauchen nun die point_id und die point_type_id
    #st.write(f'Variable st.sessions_state.ort is of type {type(st.session_state.ort)} and returns {st.session_state.ort}.')
    #st.write(stationen)
    point_id = stationen[(stationen['point_name']==st.session_state.ort)&(stationen['point_type_de']=='Station')]['point_id'].values[0]
    #st.write('point_id: ', point_id)
    point_type_id = stationen[(stationen['point_name']==st.session_state.ort)&(stationen['point_type_de']=='Station')]['point_type_id'].values[0]
    #st.write('point_type_id: ', point_type_id)

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
    st.write('Jetzt muesch chli Geduld ha (bis ca. 30 sek), bis ich all das Dategschmäus abeglade han...')
    raw_data = download_raw_data(param_urls)
    #st.write('Folgende Daten haben wir nun heruntergeladen: ', [params_dict[i] for i in raw_data.keys()])

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
    #st.write(f'Wir haben folgende Werte {df_example.columns} von heute bis {df_example['Date'].max()}')
    st.write(f'Jetzt hani d Wettodate vo hüt bis und mit {df_example['Date'].max().strftime(format='%d.%m.')} abeglade. Quelle: MeteoSchweiz')
    #st.write(df_example)

    # nun wollen wir in Worten wiedergeben, wie das Wetter morgen wird
    tmrw = datetime.today().date()+timedelta(days=1)
    tmrw = tmrw.strftime(format='%Y-%m-%d %H:%M:%S')

    df_morgen = df_example[df_example['Date']==tmrw].reset_index(drop=True)
    #st.write(df_morgen)

    n = df_morgen['Niederschlag; Tagessumme 00:00 - 24:00 Lokalzeit'][0]
    t_max = df_morgen['Lufttemperatur 2 m über Boden; Tagesmaximum 00:00 - 24:00 Lokalzeit'][0]
    t_min = df_morgen['Lufttemperatur 2 m über Boden; Tagesminimum 00:00 - 24:00 Lokalzeit'][0]

    
    # jetzt als Worte das morgige Wetter wiedergeben
    tempstring = echo_temp(t_max)
    percstring = echo_perc(n)
    st.subheader('Das isch d Prognose für morn:')
    st.write(f'In {st.session_state.ort} {tempstring}{percstring} Une gsehsch no d Wert als Grafik, falls di da interessiert :)')


    #plt.style.use('_mpl-gallery')
    plt.style.use('dark_background')
    x = df_example['Date']
    mittel = df_example['Sonnenscheindauer; Stundensumme']
    fig, ax = plt.subplots(figsize=(10,5))
    ax.bar(x, mittel, linewidth=0.2, color='yellow', width=1/24, label='Sunneschii (in Minute pro Stund)', edgecolor='black')
    plt.legend()
    plt.xticks(rotation=45)
    plt.title(f'Sunneschiiprognose (min/h) in {ort}')
    st.pyplot(fig)

    
    plt.style.use('dark_background')
    nmin = df_example['Niederschlag; Stundensumme, 10% Quantil']
    nmax = df_example['Niederschlag; Stundensumme, 90% Quantil']
    mittel = df_example['Niederschlag; Stundensumme']
    
    fig, ax = plt.subplots(figsize=(10,5))
    ax.bar(x, nmax, alpha = 1, linewidth = 0, color='#77b4f2', width=1/24, label='Niederschlag: Unsicherheit')
    ax.bar(x, mittel, linewidth=2, color='#208af5', width=1/24, label='Niederschlag: Stundesumme in mm')
    ax.set(xlim=(x.min(), x.max()),
           ylim=(round(nmin.min()-1,0), round(nmax.max()+1,0)), yticks=np.arange(round(nmin.min()-1,0), round(nmax.max()+1,0)))
    plt.legend()
    if 5 >= nmin.min() and 5 <= nmax.max():
           ax.text(x=x[0]+timedelta(hours=1), y=4.8, s='-- bis 5 mm gilt als wenig Rege', fontdict={'style':'italic'})
           plt.axhline(y=5, color='blue', linestyle='-')
    plt.xticks(rotation=45)
    plt.title(f'Niederschlagsprognose (in mm/h) in {ort}')
    st.pyplot(fig)


    #plt.style.use('_mpl-gallery')
    plt.style.use('dark_background')
    tmin = df_example['Lufttemperatur 2 m über Boden; Stundenmittel, 10% Quantil']
    tmax = df_example['Lufttemperatur 2 m über Boden; Stundenmittel, 90% Quantil']
    mittel = df_example['Lufttemperatur 2 m über Boden; Stundenmittel']
    
    fig, ax = plt.subplots(figsize=(10,5))
    ax.fill_between(x, tmin, tmax, alpha = 0.5, linewidth = 0, color='#f2e1e5', label='Temperatur: Stundenmittel')
    ax.plot(x, mittel, linewidth=2, color='#eb889c', label='Temperatur: Unsicherheit')
    ax.set(xlim=(x.min(), x.max()),
           ylim=(round(tmin.min()-1,0), round(tmax.max()+1,0)), yticks=np.arange(round(tmin.min()-1,0), round(tmax.max()+1,0), step=2))
    plt.xticks(rotation=45)
    plt.axhline(y=30, color='darkred', linestyle='-')
    plt.axhline(y=0, color='black', linestyle='-')
    ax.text(x=x[0]+timedelta(hours=1), y=30, s='-- ab do ischss sauheiss', fontdict={'style':'italic'})
    plt.legend()
    plt.title(f'Temperaturverlauf (in °C) in {ort}')
    st.pyplot(fig)

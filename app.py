"""
Sécurité Cycliste Montréal — Application d'aide à la décision
Auteurs : Laurie-Anne Duclos, Mathieu Couturier, Alexis Desjardins
Génie des Opérations et Logistique | 2025-2026
"""

import os
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
from shapely.geometry import Point
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import warnings
warnings.filterwarnings("ignore")

# ── Tentative import streamlit-plotly-events ────────────────────────────────
try:
    from streamlit_plotly_events import plotly_events
    HAS_EVENTS = True
except ImportError:
    HAS_EVENTS = False

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sécurité Cycliste — Montréal",
    layout="wide",
    initial_sidebar_state="expanded",
)

URL_RESEAU = (
    "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536"
    "/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"
)
URL_ACCIDENTS = (
    "https://donnees.montreal.ca/dataset/53d2e586-6d7f-4eae-9a7d-4d23b774051b"
    "/resource/92716a61-6834-454b-974d-4d57a9d00921/download/collisions_routieres.csv"
)
URL_COMPTEURS = (
    "https://donnees.montreal.ca/dataset/f170fecc-18db-44bc-b48d-01d01374c653"
    "/resource/66966141-6101-4433-a267-3312f2c83693/download/comptage_velo_2025.csv"
)
URL_BIXI_STATIONS = "https://gbfs.velobixi.com/gbfs/2-2/fr/station_information.json"
URL_BIXI_STATUS   = "https://gbfs.velobixi.com/gbfs/2-2/fr/station_status.json"

SEUIL_M = 15

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #1C2833;
}
section[data-testid="stSidebar"] {
    background: #1A2533;
    border-right: none;
}
section[data-testid="stSidebar"] * { color: #ECF0F1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.12) !important; }

.page-header {
    border-left: 4px solid #1A5276;
    padding: 10px 0 10px 18px;
    margin-bottom: 28px;
}
/* PAGE 1 FIX: grand titre agrandi */
.page-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 36px; font-weight: 400;
    color: #1A2533; margin: 0 0 4px 0;
}
/* PAGE 1 FIX: sous-titre réduit */
.page-header p { font-size: 13px; color: #9DAAB2; margin: 0; }

.kpi-row { display: flex; gap: 16px; margin-bottom: 24px; }
.kpi-card {
    flex: 1; background: white;
    border: 1px solid #E5E8EC; border-radius: 8px;
    padding: 18px 22px; border-top: 3px solid #1A5276;
}
.kpi-card.rouge  { border-top-color: #C0392B; }
.kpi-card.vert   { border-top-color: #1E8449; }
.kpi-card.jaune  { border-top-color: #D4AC0D; }
.kpi-card.bleu   { border-top-color: #2471A3; }
.kpi-card.violet { border-top-color: #7D3C98; }
.kpi-value { font-size: 30px; font-weight: 600; color: #1A2533; line-height: 1; }
.kpi-unit  { font-size: 14px; font-weight: 400; color: #7F8C8D; margin-left: 3px; }
.kpi-label { font-size: 12px; color: #7F8C8D; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }

/* PAGE 1 & 2 FIX: sous-titres gris pâle agrandis */
.section-title {
    font-size: 15px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #566573; margin: 32px 0 12px 0;
    padding-bottom: 8px; border-bottom: 1px solid #E5E8EC;
}

.reco-card {
    background: white; border: 1px solid #E5E8EC;
    border-radius: 8px; padding: 22px 26px;
    margin-bottom: 16px; border-left: 4px solid #1A5276;
}
.reco-card.rouge  { border-left-color: #C0392B; }
.reco-card.jaune  { border-left-color: #D4AC0D; }
.reco-card.navy   { border-left-color: #1A5276; }
.reco-title { font-size: 16px; font-weight: 600; color: #1A2533; margin-bottom: 8px; }
.reco-body  { font-size: 14px; color: #566573; line-height: 1.7; margin-bottom: 10px; }
.reco-meta  { font-size: 11px; color: #AAB7B8; font-style: italic; }

.hyp-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.hyp-table th { background: #1A2533; color: white; padding: 10px 16px; text-align: left; font-weight: 500; }
.hyp-table td { padding: 10px 16px; border-bottom: 1px solid #EBF0F1; }
.hyp-table tr:last-child td { border-bottom: none; }
.hyp-table tr:nth-child(even) td { background: #F8F9FA; }
.hyp-id { font-weight: 700; color: #1A5276; }

.priority-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.priority-table th { background: #1A2533; color: white; padding: 10px 14px; text-align: left; font-weight: 500; }
.priority-table td { padding: 9px 14px; border-bottom: 1px solid #EBF0F1; }
.priority-table tr:nth-child(even) td { background: #F8F9FA; }
.priority-table .score { font-weight: 700; color: #1A5276; }
.priority-table .rank  { font-weight: 700; color: #1A5276; }

.sidebar-brand { padding: 0 0 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
.sidebar-brand h2 { font-family: 'DM Serif Display', serif; font-size: 18px; font-weight: 400; color: white !important; margin: 0 0 4px 0; }
.sidebar-brand p  { font-size: 11px; color: rgba(255,255,255,0.5) !important; margin: 0; text-transform: uppercase; letter-spacing: 0.08em; }

.block-container { padding-top: 28px; padding-bottom: 40px; }

.bixi-live-dot {
    display: inline-block; width: 8px; height: 8px;
    background: #1E8449; border-radius: 50%;
    margin-right: 6px; animation: pulse 2s infinite;
}
@keyframes pulse { 0%{opacity:1} 50%{opacity:0.3} 100%{opacity:1} }

/* Badge filtre */
.filter-badge {
    display: inline-block;
    background: #1A5276; color: white;
    font-size: 11px; padding: 2px 10px;
    border-radius: 12px; margin-right: 6px;
    font-weight: 500;
}
.filter-badge.jaune { background: #D4AC0D; }

/* Tooltip KPI card */
.kpi-card-wrapper { position: relative; }
.kpi-tooltip {
    display: none;
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #1A2533;
    color: white;
    font-size: 12px;
    padding: 8px 12px;
    border-radius: 6px;
    white-space: nowrap;
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    max-width: 260px;
    white-space: normal;
    text-align: center;
    line-height: 1.5;
}
.kpi-card-wrapper:hover .kpi-tooltip { display: block; }

/* ── Fond blanc global ── */
[data-testid="stAppViewContainer"] { background: #ffffff; }

[data-testid="stMainBlockContainer"] { position: relative; }

/* Overlay blanc plein écran */
[data-testid="stMainBlockContainer"][aria-busy="true"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: #ffffff;
    z-index: 9998;
}
/* Spinner centré */
[data-testid="stMainBlockContainer"][aria-busy="true"]::after {
    content: "";
    position: fixed;
    top: 50%;
    left: 50%;
    width: 44px; height: 44px;
    margin: -22px 0 0 -22px;
    border: 3px solid #E5E8EC;
    border-top-color: #1A5276;
    border-radius: 50%;
    animation: spin-page 0.7s linear infinite;
    z-index: 9999;
}
@keyframes spin-page { to { transform: rotate(360deg); } }

[data-stale="true"] { opacity: 0 !important; pointer-events: none !important; }

.element-container iframe { background: #ffffff !important; border: none !important; }

[data-testid="stSkeleton"] { background: #f0f2f6 !important; opacity: 0 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
PREPROCESSED = os.path.exists("data/accidents_classes.parquet")

@st.cache_data(show_spinner=False)
def load_reseau():
    if os.path.exists("data/reseau_cyclable.geojson"):
        return gpd.read_file("data/reseau_cyclable.geojson")
    return gpd.read_file(URL_RESEAU)

@st.cache_data(show_spinner=False)
def load_bixi_csv():
    return load_bixi_live()

@st.cache_data(show_spinner=False, ttl=300)
def load_bixi_live():
    try:
        r_info   = requests.get(URL_BIXI_STATIONS, timeout=10).json()
        r_status = requests.get(URL_BIXI_STATUS,   timeout=10).json()
        stations = pd.DataFrame(r_info["data"]["stations"])
        status   = pd.DataFrame(r_status["data"]["stations"])
        df = stations.merge(status, on="station_id", how="inner")
        df = df.rename(columns={
            "name": "station",
            "num_bikes_available": "velos_disponibles",
            "num_docks_available": "bornes_libres",
        })
        df = df[df["lat"].between(45.4, 45.7) & df["lon"].between(-74.0, -73.4)]
        return df[["station", "lat", "lon", "velos_disponibles", "bornes_libres"]].dropna()
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def load_accidents():
    if os.path.exists("data/accidents_classes.parquet"):
        df = pd.read_parquet("data/accidents_classes.parquet")
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["lon"], df["lat"]),
            crs="EPSG:4326"
        ).to_crs("EPSG:32618")
        if "GRAVITE" in gdf.columns:
            gdf = _normalise_gravite(gdf)
        return gdf

    gdf_r = load_reseau()
    df_c  = pd.read_csv(URL_ACCIDENTS, low_memory=False)
    df_2021 = df_c[
        (df_c["AN"] == 2021) &
        (df_c["NB_VICTIMES_VELO"] > 0) &
        df_c["LOC_LAT"].notna() &
        df_c["LOC_LONG"].notna()
    ].copy()

    df_2021 = df_2021.reset_index(drop=True)

    gdf_acc   = gpd.GeoDataFrame(
        df_2021,
        geometry=gpd.points_from_xy(df_2021["LOC_LONG"], df_2021["LOC_LAT"]),
        crs="EPSG:4326"
    )
    gdf_acc_m = gdf_acc.to_crs("EPSG:32618")
    gdf_r_m   = gdf_r.to_crs("EPSG:32618")

    gdf_joined = gpd.sjoin_nearest(
        gdf_acc_m,
        gdf_r_m[["geometry", "TYPE_VOIE_DESC", "NOM_ARR_VILLE_DESC"]],
        how="left",
        distance_col="dist_piste_m",
    )

    gdf_joined = gdf_joined[~gdf_joined.index.duplicated(keep="first")].copy()

    gdf_joined["classification"] = gdf_joined["dist_piste_m"].apply(
        lambda d: "Sur piste" if d <= SEUIL_M else "Hors piste"
    )
    gdf_joined = _normalise_gravite(gdf_joined)
    return gdf_joined


def _normalise_gravite(gdf):
    mapping = {
        "Mortel":                                           "Mortel",
        "Blessé grave":                                     "Blessé grave",
        "Blessé léger":                                     "Blessé léger",
        "Dommages matériels seulement":                     "Dommages matériels seulement",
        "Dommages matériels inférieurs au seuil de rapportage": "Dommages matériels seulement",
        "1": "Mortel",         1: "Mortel",
        "2": "Blessé grave",   2: "Blessé grave",
        "3": "Blessé léger",   3: "Blessé léger",
        "4": "Dommages matériels seulement", 4: "Dommages matériels seulement",
        "Blesse grave":                    "Blessé grave",
        "Blesse leger":                    "Blessé léger",
        "Blesse léger":                    "Blessé léger",
        "Blessé leger":                    "Blessé léger",
        "Dommages materiels seulement":    "Dommages matériels seulement",
        "Dommages materiels inferieurs au seuil de rapportage": "Dommages matériels seulement",
        "Dommages matériels":              "Dommages matériels seulement",
        "Dom. matériels":                  "Dommages matériels seulement",
        "Dom. materiels":                  "Dommages matériels seulement",
        "Mortel(le)": "Mortel",
        "Grave":      "Blessé grave",
        "Léger":      "Blessé léger",
        "Leger":      "Blessé léger",
        "DMS":        "Dommages matériels seulement",
    }
    gdf = gdf.copy()
    gdf["GRAVITE"] = gdf["GRAVITE"].map(
        lambda v: mapping.get(v, mapping.get(str(v).strip(), "Dommages matériels seulement"))
    )
    return gdf

@st.cache_data(show_spinner=False)
def load_compteurs():
    if os.path.exists("data/compteurs_agg.parquet"):
        return pd.read_parquet("data/compteurs_agg.parquet")
    df = pd.read_csv(URL_COMPTEURS, low_memory=False)
    df = df.dropna(subset=["latitude", "longitude", "vitesseMoyenne"])
    df = df[
        df["latitude"].between(45.4, 45.7) &
        df["longitude"].between(-74.0, -73.4) &
        (df["vitesseMoyenne"] > 0)
    ].copy()
    agg = {"vitesseMoyenne": "mean"}
    if "volume" in df.columns:
        agg["volume"] = "mean"
    return df.groupby(["latitude", "longitude"]).agg(agg).reset_index()

@st.cache_data(show_spinner=False)
def load_zones_rouges():
    if os.path.exists("data/zones_rouges.parquet"):
        return pd.read_parquet("data/zones_rouges.parquet")
    gdf = load_accidents().to_crs("EPSG:4326")
    acc_hors = gdf[gdf["classification"] == "Hors piste"].copy()
    acc_hors["lat_grid"] = (acc_hors.geometry.y * 50).round() / 50
    acc_hors["lon_grid"] = (acc_hors.geometry.x * 50).round() / 50
    zones = acc_hors.groupby(["lat_grid", "lon_grid"]).agg(
        nb_accidents=("GRAVITE", "count"),
        nb_graves=("GRAVITE", lambda x: x.isin(["Mortel", "Blessé grave"]).sum())
    ).reset_index()
    return zones[zones["nb_accidents"] >= 2].sort_values("nb_accidents", ascending=False)

@st.cache_data(show_spinner=False)
def load_top3(_bixi_live):
    if os.path.exists("data/top3_zones.parquet"):
        return pd.read_parquet("data/top3_zones.parquet")
    zones = load_zones_rouges()
    if _bixi_live is None or len(_bixi_live) == 0:
        _bixi_live = pd.DataFrame({"station": [], "lat": [], "lon": [], "velos_disponibles": []})
    bixi_gdf  = gpd.GeoDataFrame(
        _bixi_live,
        geometry=gpd.points_from_xy(_bixi_live["lon"], _bixi_live["lat"]),
        crs="EPSG:4326"
    ).to_crs("EPSG:32618")
    zones_gdf = gpd.GeoDataFrame(
        zones,
        geometry=gpd.points_from_xy(zones["lon_grid"], zones["lat_grid"]),
        crs="EPSG:4326"
    ).to_crs("EPSG:32618")
    bixi_gdf["passages"] = bixi_gdf.get("velos_disponibles", 0)
    merged = gpd.sjoin_nearest(
        zones_gdf,
        bixi_gdf[["geometry", "passages", "station"]],
        how="left", distance_col="dist_bixi_m"
    )
    merged["passages"] = merged["passages"].fillna(0)
    max_p = max(merged["passages"].max(), 1)
    merged["score"] = (
        merged["nb_accidents"] * 2 +
        merged["nb_graves"] * 5 +
        (merged["passages"] / max_p * 3)
    ).round(2)
    return merged.sort_values("score", ascending=False).head(3).reset_index(drop=True)


# ─────────────────────────────────────────────
# HELPERS CARTE
# ─────────────────────────────────────────────
def style_reseau(feature):
    t = feature["properties"].get("TYPE_VOIE_DESC", "")
    if "Réseau express vélo" in t: return {"color": "#C0392B", "weight": 3,   "opacity": 0.85}
    if "Piste cyclable"      in t: return {"color": "#1E8449", "weight": 2,   "opacity": 0.75}
    if "Bande cyclable"      in t: return {"color": "#2471A3", "weight": 1.5, "opacity": 0.65}
    if "Chaussée désignée"  in t: return {"color": "#1A5276", "weight": 1,   "opacity": 0.55}
    return {"color": "#AAB7B8", "weight": 0.8, "opacity": 0.3}

def style_reseau_fond(feature):
    t = feature["properties"].get("TYPE_VOIE_DESC", "")
    if "Réseau express vélo" in t: return {"color": "#C0392B", "weight": 2,   "opacity": 0.5}
    if "Piste cyclable"      in t: return {"color": "#1E8449", "weight": 1.5, "opacity": 0.4}
    if "Bande cyclable"      in t: return {"color": "#2471A3", "weight": 1,   "opacity": 0.3}
    return {"color": "#BDC3C7", "weight": 0.7, "opacity": 0.2}

def make_legende(items, titre="Légende"):
    rows = "".join(f"""
    <div style="display:flex;align-items:center;margin:5px 0;">
      <div style="width:20px;height:3px;background:{c};border-radius:2px;
                  margin-right:10px;flex-shrink:0;"></div>
      <span style="font-size:12px;color:#2C3E50;">{l}</span>
    </div>""" for c, l in items)
    return f"""
    <div style="position:fixed;bottom:28px;left:28px;min-width:200px;
    background:rgba(255,255,255,0.97);border-radius:8px;
    box-shadow:0 2px 16px rgba(0,0,0,0.14);
    font-family:sans-serif;z-index:9999;padding:14px 18px;">
      <div style="font-size:12px;font-weight:600;text-transform:uppercase;
                  letter-spacing:0.08em;color:#566573;margin-bottom:10px;">{titre}</div>
      {rows}
    </div>"""

def make_base_map(zoom=12):
    m = folium.Map(
        location=[45.5088, -73.5878],
        zoom_start=zoom,
        tiles=None,
    )
    folium.TileLayer(
        tiles="cartodbpositron",
        name="Fond de carte",
        control=False,
        attr="© CartoDB",
    ).add_to(m)
    return m

def render_map(m, height=480):
    html = m._repr_html_()
    components.html(html, height=height, scrolling=False)

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_family="DM Sans",
    font_size=12,
    margin=dict(t=10, b=10, l=0, r=0),
)


# ─────────────────────────────────────────────
# CHARGEMENT PRINCIPAL
# ─────────────────────────────────────────────
spinner_msg = (
    "Chargement depuis data/ (pré-traité)..."
    if os.path.exists("data/accidents_classes.parquet")
    else "Calcul en cours (première fois, ~1 min)..."
)

with st.spinner(spinner_msg):
    gdf_reseau     = load_reseau()
    df_bixi_csv    = load_bixi_csv()
    df_cpt_agg     = load_compteurs()
    bixi_live      = load_bixi_live()
    gdf_joined     = load_accidents()
    gdf_joined_wgs = gdf_joined.to_crs("EPSG:4326")
    zones_rouges   = load_zones_rouges()
    top3           = load_top3(bixi_live)

counts  = gdf_joined["classification"].value_counts()
total   = counts.sum()
acc_sur = counts.get("Sur piste",  0)
acc_hor = counts.get("Hors piste", 0)
pct_hor = acc_hor / total * 100 if total > 0 else 0

q25_vit   = df_cpt_agg["vitesseMoyenne"].quantile(0.25)
sous_util = df_cpt_agg[df_cpt_agg["vitesseMoyenne"] <= q25_vit].copy()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <h2>Sécurité Cycliste</h2>
      <p>École de technologie supérieure 2025-2026</p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Réseau et Cadrage", "Analyse de Sécurité", "Déplacements Bixi", "Aide à la Décision"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    with st.expander("ⓘ  Hypothèses du projet"):
        st.markdown("""
**H1** — Analyse centrée sur les usagers Bixi  
*Les données Bixi sont géolocalisées et représentatives du cyclisme urbain montréalais*

**H2** — Zone d'étude : réseau Bixi de Montréal  
*L'analyse couvre les secteurs à forte densité cycliste, à l'intérieur de l'île*

**H3** — Données d'accidents de 2021  
*L'année 2021 est utilisée car ses données de collisions sont complètes et validées*

**H4** — Un accident est « sur piste » s'il se produit à moins de 15 mètres d'une piste cyclable  
*Cette distance tient compte des imprécisions GPS des appareils de mesure*

**H5** — Les trajets calculés suivent le réseau cyclable (OpenStreetMap)  
*L'itinéraire le plus court est calculé sur les rues et pistes réservées aux vélos*

**H6** — Les 100 trajets Bixi les plus fréquents sont analysés  
*Cela représente les corridors principaux empruntés par les cyclistes*

**H7** — Pondération des rues candidates : 60 % achalandage + 40 % longueur  
*On priorise les rues à fort trafic cycliste ET suffisamment longues pour justifier des travaux*

---
**Sources :** SAAQ 2021 · Ville de Montréal · Bixi GBFS · OpenStreetMap
        """)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:rgba(255,255,255,0.35);line-height:2.2;">
      Laurie-Anne Duclos<br>
      Mathieu Couturier<br>
      Alexis Desjardins<br><br>
      Génie des Opérations<br>et Logistique<br><br>
      SAAQ 2021 · Bixi · Données MTL
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DÉTECTION CHANGEMENT DE PAGE → page blanche
# ─────────────────────────────────────────────
if "page_precedente" not in st.session_state:
    st.session_state["page_precedente"] = page

page_changed = st.session_state["page_precedente"] != page
st.session_state["page_precedente"] = page

st.markdown(
    f'<div id="page-token" data-page="{page}" style="display:none;"></div>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════
# PAGE 1 — RÉSEAU ET CADRAGE
# ═══════════════════════════════════════════════
if page == "Réseau et Cadrage":
  with st.spinner("Chargement de la page…"):

    st.markdown("""
    <div class="page-header">
      <h1>Réseau cyclable de Montréal</h1>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Hypothèses de travail</div>', unsafe_allow_html=True)
    st.markdown("""
    <table class="hyp-table">
      <thead><tr><th>Réf.</th><th>Hypothèse</th><th>Justification</th></tr></thead>
      <tbody>
        <tr><td class="hyp-id">H1</td>
            <td>Analyse centrée sur les usagers Bixi</td>
            <td>Les données Bixi sont géolocalisées et représentatives du cyclisme urbain montréalais</td></tr>
        <tr><td class="hyp-id">H2</td>
            <td>Zone d'étude : réseau Bixi de Montréal</td>
            <td>Couvre les secteurs à forte densité cycliste, à l'intérieur de l'île</td></tr>
        <tr><td class="hyp-id">H3</td>
            <td>Données d'accidents de 2021</td>
            <td>L'année 2021 est utilisée car ses données de collisions sont complètes et validées</td></tr>
        <tr><td class="hyp-id">H4</td>
            <td>Un accident est « sur piste » s'il se produit à moins de 15 m d'une piste cyclable</td>
            <td>Cette distance tient compte des imprécisions GPS des appareils de mesure</td></tr>
        <tr><td class="hyp-id">H5</td>
            <td>Les trajets calculés suivent le réseau cyclable (OpenStreetMap)</td>
            <td>L'itinéraire le plus court est calculé sur les rues et pistes réservées aux vélos</td></tr>
        <tr><td class="hyp-id">H6</td>
            <td>Les 100 trajets Bixi les plus fréquents sont analysés</td>
            <td>Cela représente les corridors principaux empruntés par les cyclistes</td></tr>
        <tr><td class="hyp-id">H7</td>
            <td>Pondération des rues candidates : 60 % achalandage + 40 % longueur</td>
            <td>On priorise les rues à fort trafic cycliste ET suffisamment longues pour justifier des travaux</td></tr>
      </tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Aperçu du réseau</div>', unsafe_allow_html=True)

    # PAGE 1 FIX: note explicative sur la différence piste vs bande
    st.markdown("""
    <div style="background:#EBF5FB;border-left:3px solid #2471A3;border-radius:0 6px 6px 0;
    padding:12px 16px;margin-bottom:18px;font-size:13px;color:#1A2533;line-height:1.7;">
      <b>ℹ️ Note :</b> Le réseau cyclable total inclut plusieurs types d'infrastructures qui se distinguent par leur niveau de protection.
      Une <b>piste cyclable</b> est une voie <em>séparée physiquement</em> de la circulation automobile (trottoir, bollards, surélévation).
      Une <b>bande cyclable</b> est une voie <em>marquée au sol</em> sur la chaussée, sans séparation physique.
      D'autres types (chaussée désignée, voie partagée) s'ajoutent pour former le total du réseau.
      La somme des km de pistes et de bandes est donc inférieure au total du réseau.
    </div>
    """, unsafe_allow_html=True)

    try:
        gdf_m = gdf_reseau.to_crs("EPSG:32618")
        gdf_reseau["longueur_m"] = gdf_m.geometry.length
        lon_total   = gdf_reseau["longueur_m"].sum() / 1000
        lon_piste   = gdf_reseau[
            gdf_reseau["TYPE_VOIE_DESC"].str.contains("Piste cyclable", na=False) &
            ~gdf_reseau["TYPE_VOIE_DESC"].str.contains("express", case=False, na=False)
        ]["longueur_m"].sum() / 1000
        lon_bande   = gdf_reseau[
            gdf_reseau["TYPE_VOIE_DESC"].str.contains("Bande", na=False)
        ]["longueur_m"].sum() / 1000
    except Exception:
        lon_total = lon_piste = lon_bande = None

    col1, col2, col3 = st.columns(3)
    with col1:
        v = f"{lon_total:.0f}" if lon_total else str(len(gdf_reseau))
        u = "km total" if lon_total else "tronçons"
        # PAGE 1 FIX: couleur violet pour ne pas confondre avec les couleurs de la carte
        st.markdown(
            f'<div class="kpi-card-wrapper">'
            f'<div class="kpi-card violet"><div class="kpi-value">{v}<span class="kpi-unit">{u}</span></div>'
            f'<div class="kpi-label">Réseau cyclable</div></div>'
            f'<div class="kpi-tooltip">Total de tous les types de voies cyclables combinés : pistes, bandes, chaussées désignées et voies partagées.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        v = f"{lon_piste:.0f}" if lon_piste else "—"
        st.markdown(
            f'<div class="kpi-card-wrapper">'
            f'<div class="kpi-card vert"><div class="kpi-value">{v}<span class="kpi-unit">km</span></div>'
            f'<div class="kpi-label">Pistes cyclables</div></div>'
            f'<div class="kpi-tooltip">Voies séparées physiquement de la circulation (trottoir surélevé, bollards, séparateurs). Niveau de protection le plus élevé.</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col3:
        v = f"{lon_bande:.0f}" if lon_bande else "—"
        st.markdown(
            f'<div class="kpi-card-wrapper">'
            f'<div class="kpi-card bleu"><div class="kpi-value">{v}<span class="kpi-unit">km</span></div>'
            f'<div class="kpi-label">Bandes cyclables</div></div>'
            f'<div class="kpi-tooltip">Voies marquées au sol sur la chaussée, sans séparation physique avec les voitures. Protection moindre qu\'une piste.</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Carte du réseau cyclable</div>', unsafe_allow_html=True)

    m1 = make_base_map()
    folium.GeoJson(
        gdf_reseau, name="Réseau cyclable de Montréal",
        style_function=style_reseau,
        tooltip=folium.GeoJsonTooltip(
            fields=["NOM_ARR_VILLE_DESC", "TYPE_VOIE_DESC", "SAISONS4"],
            aliases=["Arrondissement :", "Type :", "4 saisons :"],
        ),
    ).add_to(m1)
    m1.get_root().html.add_child(folium.Element(make_legende([
        ("#C0392B", "Réseau express vélo (REV)"),
        ("#1E8449", "Piste cyclable"),
        ("#2471A3", "Bande cyclable"),
        ("#1A5276", "Chaussée désignée"),
        ("#AAB7B8", "Autre"),
    ], "Type de voie")))
    render_map(m1, height=540)


# ═══════════════════════════════════════════════
# PAGE 2 — ANALYSE DE SÉCURITÉ
# ═══════════════════════════════════════════════
elif page == "Analyse de Sécurité":
  with st.spinner("Chargement de la page…"):

    for key in ["p2_arrondissement", "p2_gravite", "p2_classif",
                "p2_last_donut", "p2_last_grav", "p2_last_arr"]:
        if key not in st.session_state:
            st.session_state[key] = None

    st.markdown("""
    <div class="page-header">
      <h1>Analyse de sécurité — Accidents vélo 2021</h1>
    </div>
    """, unsafe_allow_html=True)

    filtres_actifs = {
        k: v for k, v in {
            "Arrondissement": st.session_state["p2_arrondissement"],
            "Gravité":        st.session_state["p2_gravite"],
            "Classification": st.session_state["p2_classif"],
        }.items() if v is not None
    }

    col_f1, col_f2 = st.columns([9, 1])
    with col_f1:
        if filtres_actifs:
            pills = " ".join(
                f'<span class="filter-badge">{k} : {v}</span>'
                for k, v in filtres_actifs.items()
            )
            st.markdown(
                f'<div style="padding:6px 0;">'
                f'<span style="font-size:12px;color:#7F8C8D;margin-right:8px;">Filtres actifs :</span>'
                f'{pills}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="padding:6px 0;font-size:12px;color:#AAB7B8;">'
                'Aucun filtre actif — cliquez sur un graphique pour filtrer</div>',
                unsafe_allow_html=True
            )
    with col_f2:
        if filtres_actifs:
            if st.button("✕ Reset", key="p2_reset", type="secondary"):
                st.session_state["p2_arrondissement"] = None
                st.session_state["p2_gravite"]        = None
                st.session_state["p2_classif"]        = None
                st.session_state["p2_last_donut"]     = None
                st.session_state["p2_last_grav"]      = None
                st.session_state["p2_last_arr"]       = None
                st.rerun()

    if not HAS_EVENTS:
        st.warning(
            "**Filtrage par clic désactivé.** "
            "Installez `streamlit-plotly-events` pour activer le clic sur les graphiques : "
            "`pip install streamlit-plotly-events`. "
            "En attendant, utilisez les filtres manuels ci-dessous."
        )
        col_sel1, col_sel2, col_sel3 = st.columns(3)
        with col_sel1:
            arrs = ["(Tous)"] + sorted(
                gdf_joined["NOM_ARR_VILLE_DESC"].dropna().unique().tolist()
            )
            cur_arr = st.session_state["p2_arrondissement"] or "(Tous)"
            sel_arr = st.selectbox("Arrondissement", arrs,
                                   index=arrs.index(cur_arr) if cur_arr in arrs else 0,
                                   key="sel_arr_fb")
            st.session_state["p2_arrondissement"] = None if sel_arr == "(Tous)" else sel_arr
        with col_sel2:
            gravs_options = ["(Tous)", "Dommages matériels seulement",
                             "Blessé léger", "Blessé grave", "Mortel"]
            cur_grav = st.session_state["p2_gravite"] or "(Tous)"
            sel_grav = st.selectbox("Gravité", gravs_options,
                                    index=gravs_options.index(cur_grav) if cur_grav in gravs_options else 0,
                                    key="sel_grav_fb")
            st.session_state["p2_gravite"] = None if sel_grav == "(Tous)" else sel_grav
        with col_sel3:
            classifs = ["(Tous)", "Sur piste", "Hors piste"]
            cur_cl = st.session_state["p2_classif"] or "(Tous)"
            sel_cl = st.selectbox("Classification", classifs,
                                  index=classifs.index(cur_cl) if cur_cl in classifs else 0,
                                  key="sel_cl_fb")
            st.session_state["p2_classif"] = None if sel_cl == "(Tous)" else sel_cl

    grav_map_inv = {
        "Blessé léger":  "Blessé léger",
        "Blessé grave":  "Blessé grave",
        "Mortel":        "Mortel",
    }

    gdf_base     = gdf_joined.copy()
    gdf_base_wgs = gdf_joined_wgs.copy()

    df_f     = gdf_base.copy()
    df_f_wgs = gdf_base_wgs.copy()

    if st.session_state["p2_arrondissement"]:
        mask = df_f["NOM_ARR_VILLE_DESC"] == st.session_state["p2_arrondissement"]
        df_f     = df_f[mask]
        df_f_wgs = df_f_wgs[mask]

    if st.session_state["p2_gravite"]:
        grav_long = grav_map_inv.get(
            st.session_state["p2_gravite"],
            st.session_state["p2_gravite"]
        )
        mask2 = df_f["GRAVITE"] == grav_long
        df_f     = df_f[mask2]
        df_f_wgs = df_f_wgs[mask2]

    if st.session_state["p2_classif"]:
        mask3 = df_f["classification"] == st.session_state["p2_classif"]
        df_f     = df_f[mask3]
        df_f_wgs = df_f_wgs[mask3]

    n_total   = len(df_f)
    counts_f  = df_f["classification"].value_counts()
    n_sur     = counts_f.get("Sur piste",  0)
    n_hor     = counts_f.get("Hors piste", 0)
    # PAGE 2 FIX: "Hors réseau cyclable" au lieu de "Hors infrastructure"
    pct_hor_f = n_hor / n_total * 100 if n_total > 0 else 0
    is_filtered = bool(filtres_actifs)
    badge = (
        ' <span style="font-size:10px;background:#D4AC0D;color:white;'
        'padding:1px 6px;border-radius:8px;vertical-align:middle;">filtré</span>'
        if is_filtered else ""
    )

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card rouge">
        <div class="kpi-value">{n_hor:,}</div>
        <div class="kpi-label">Accidents hors piste{badge}</div>
      </div>
      <div class="kpi-card jaune">
        <div class="kpi-value">{n_sur:,}</div>
        <div class="kpi-label">Accidents sur piste{badge}</div>
      </div>
      <div class="kpi-card bleu">
        <div class="kpi-value">{pct_hor_f:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">Hors réseau cyclable{badge}</div>
      </div>
      <div class="kpi-card bleu">
        <div class="kpi-value">{n_total:,}</div>
        <div class="kpi-label">Total accidents{badge}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # PAGE 2 FIX: titre de carte sans le nombre d'accidents
    st.markdown(
        '<div class="section-title">Carte des accidents — Sur piste vs Hors piste</div>',
        unsafe_allow_html=True
    )

    m2 = make_base_map()
    folium.GeoJson(gdf_reseau, name="Réseau cyclable", style_function=style_reseau_fond, control=False).add_to(m2)

    fg_sur = folium.FeatureGroup(name="✅ Accidents sur piste",  show=True)
    fg_hor = folium.FeatureGroup(name="⚠️ Accidents hors piste", show=True)
    # Page 2 FIX: orange pour "sur piste" (plus neutre que vert qui suggère "sécuritaire")
    couleurs_acc = {"Sur piste": "#E67E22", "Hors piste": "#C0392B"}

    MAX_PTS = 2000
    df_map = df_f_wgs.copy()
    if len(df_map) > MAX_PTS:
        df_map = df_map.sample(MAX_PTS, random_state=42)
        st.caption(
            f"⚠️ Carte : {MAX_PTS} points affichés sur {len(df_f_wgs):,} "
            f"(échantillon aléatoire représentatif)"
        )

    for _, row in df_map.iterrows():
        cl = row["classification"]
        popup_txt = (
            f"<b>Gravité :</b> {row.get('GRAVITE','?')}<br>"
            f"<b>Arrondissement :</b> {row.get('NOM_ARR_VILLE_DESC','?')}<br>"
            f"<b>Type voie :</b> {row.get('TYPE_VOIE_DESC','?')}<br>"
            f"<b>Distance piste :</b> {row['dist_piste_m']:.0f} m"
        )
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=5, color=couleurs_acc[cl],
            fill=True, fill_opacity=0.65, weight=0.5,
            popup=folium.Popup(popup_txt, max_width=240),
            tooltip=(
                f"{cl} — {row.get('GRAVITE','?')} "
                f"— {row.get('NOM_ARR_VILLE_DESC','?')}"
            ),
        ).add_to(fg_sur if cl == "Sur piste" else fg_hor)

    fg_sur.add_to(m2)
    fg_hor.add_to(m2)
    folium.LayerControl(position="topright", collapsed=True).add_to(m2)
    m2.get_root().html.add_child(folium.Element(make_legende([
        ("#E67E22", f"Sur piste — {n_sur} ({100 - pct_hor_f:.1f}%)"),
        ("#C0392B", f"Hors piste — {n_hor} ({pct_hor_f:.1f}%)"),
    ], "Accidents vélo 2021")))
    render_map(m2, height=480)

    col_b, col_d = st.columns(2)

    with col_b:
        st.markdown(
            '<div class="section-title">Gravité des accidents'
            ' <span style="font-size:10px;color:#AAB7B8;font-weight:400;">'
            '— cliquez pour filtrer</span></div>',
            unsafe_allow_html=True
        )

        ordre_gravite = ["Blessé léger", "Blessé grave", "Mortel"]

        rows_grav = []
        for gravite_long in ordre_gravite:
            for classif in ["Sur piste", "Hors piste"]:
                n = int(((df_f["GRAVITE"] == gravite_long) & (df_f["classification"] == classif)).sum())
                rows_grav.append({"Gravité": gravite_long, "Classification": classif, "Accidents": n})

        gravite_df = pd.DataFrame(rows_grav)
        sel_grav_court = st.session_state["p2_gravite"]

        fig_grav = go.Figure()
        # PAGE 2 FIX: deux bleus distincts (foncé/pâle) — neutres, sans connotation carte
        couleurs_classif = {"Sur piste": "#2471A3", "Hors piste": "#85C1E9"}

        for classif in ["Hors piste", "Sur piste"]:
            sub = gravite_df[gravite_df["Classification"] == classif]
            opacities = [
                1.0 if (sel_grav_court is None or lbl == sel_grav_court) else 0.2
                for lbl in sub["Gravité"]
            ]
            fig_grav.add_trace(go.Bar(
                name=classif,
                x=sub["Gravité"].tolist(),
                y=sub["Accidents"].tolist(),
                marker_color=couleurs_classif[classif],
                marker_opacity=opacities,
                text=sub["Accidents"].tolist(),
                textposition="outside",
                textfont=dict(size=11, color="#566573", family="'DM Sans', sans-serif"),
                cliponaxis=False,
                hovertemplate="%{x} — " + classif + "<br><b>%{y}</b> accidents<extra></extra>",
            ))

        y_max = max(gravite_df["Accidents"].max(), 1)
        fig_grav.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="'DM Sans', sans-serif", size=11, color="#566573"),
            height=400,
            margin=dict(t=20, b=70, l=50, r=20),
            barmode="group",
            bargap=0.28,
            bargroupgap=0.06,
            legend=dict(
                orientation="h", y=-0.18, x=0,
                font=dict(family="'DM Sans', sans-serif", size=11, color="#566573"),
                bgcolor="rgba(0,0,0,0)",
            ),
            yaxis=dict(
                showgrid=True, gridcolor="#E5E8EC",
                zeroline=False,
                title=dict(
                    text="Nombre d'accidents",
                    font=dict(size=11, family="'DM Sans', sans-serif", color="#7F8C8D"),
                ),
                tickfont=dict(size=11, family="'DM Sans', sans-serif", color="#7F8C8D"),
                range=[0, y_max * 1.22],
            ),
            xaxis=dict(
                title="",
                tickfont=dict(size=12, family="'DM Sans', sans-serif", color="#1A2533"),
                tickangle=0,
                showgrid=False,
                categoryorder="array",
                categoryarray=ordre_gravite,
            ),
            clickmode="event",
        )

        if HAS_EVENTS:
            clicked_grav = plotly_events(
                fig_grav, click_event=True,
                key="bar_gravite", override_height=420
            )
            if clicked_grav and clicked_grav != st.session_state["p2_last_grav"]:
                st.session_state["p2_last_grav"] = clicked_grav
                pt       = clicked_grav[0]
                new_grav = pt.get("x")
                if new_grav:
                    if st.session_state["p2_gravite"] == new_grav:
                        st.session_state["p2_gravite"] = None
                    else:
                        st.session_state["p2_gravite"] = new_grav
                    st.rerun()
        else:
            st.plotly_chart(fig_grav, use_container_width=True)

    with col_d:
        st.markdown(
            '<div class="section-title">Top 10 arrondissements'
            ' <span style="font-size:10px;color:#AAB7B8;font-weight:400;">'
            '— cliquez pour filtrer</span></div>',
            unsafe_allow_html=True
        )

        df_arr_base = gdf_base.copy()
        if st.session_state["p2_gravite"]:
            grav_long_arr = grav_map_inv.get(
                st.session_state["p2_gravite"],
                st.session_state["p2_gravite"]
            )
            df_arr_base = df_arr_base[df_arr_base["GRAVITE"] == grav_long_arr]
        if st.session_state["p2_classif"]:
            df_arr_base = df_arr_base[
                df_arr_base["classification"] == st.session_state["p2_classif"]
            ]

        arr_series = (
            df_arr_base["NOM_ARR_VILLE_DESC"]
            .dropna()
            .value_counts()
        )
        arr_counts = (
            arr_series
            .head(10)
            .reset_index()
        )
        arr_counts.columns = ["Arrondissement", "Accidents"]
        arr_counts = arr_counts.sort_values("Accidents", ascending=True)

        sel_arr = st.session_state["p2_arrondissement"]
        # PAGE 2 FIX: couleur neutre (bleu ardoise) au lieu de rouge pour le diagramme à barres
        bar_colors = [
            "#1A5276" if r["Arrondissement"] == sel_arr else "#2E4057"
            for _, r in arr_counts.iterrows()
        ]
        bar_opacity = [
            1.0 if (sel_arr is None or r["Arrondissement"] == sel_arr) else 0.28
            for _, r in arr_counts.iterrows()
        ]

        x_max = int(arr_counts["Accidents"].max()) if len(arr_counts) > 0 else 10

        fig_arr = go.Figure(go.Bar(
            x=arr_counts["Accidents"].tolist(),
            y=arr_counts["Arrondissement"].tolist(),
            orientation="h",
            marker_color=bar_colors,
            marker_opacity=bar_opacity,
            text=arr_counts["Accidents"].tolist(),
            textposition="outside",
            textfont=dict(size=11, color="#566573", family="'DM Sans', sans-serif"),
            hovertemplate="%{y}<br><b>%{x}</b> accidents<extra></extra>",
            cliponaxis=False,
        ))
        fig_arr.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="'DM Sans', sans-serif", size=11, color="#566573"),
            height=400,
            margin=dict(t=10, b=70, l=10, r=80),
            xaxis=dict(
                showgrid=True,
                gridcolor="#E5E8EC",
                zeroline=False,
                title=dict(
                    text="Nombre d'accidents",
                    font=dict(size=11, family="'DM Sans', sans-serif", color="#7F8C8D"),
                    standoff=15,
                ),
                tickfont=dict(size=11, family="'DM Sans', sans-serif", color="#7F8C8D"),
                range=[0, x_max * 1.22],
            ),
            yaxis=dict(
                title="",
                tickfont=dict(size=11, family="'DM Sans', sans-serif", color="#1A2533"),
                automargin=True,
                showgrid=False,
            ),
            clickmode="event",
            bargap=0.2,
        )

        if HAS_EVENTS:
            clicked_arr = plotly_events(
                fig_arr, click_event=True,
                key="bar_arr", override_height=420
            )
            if clicked_arr and clicked_arr != st.session_state["p2_last_arr"]:
                st.session_state["p2_last_arr"] = clicked_arr
                pt      = clicked_arr[0]
                new_arr = pt.get("y")
                if new_arr:
                    if st.session_state["p2_arrondissement"] == new_arr:
                        st.session_state["p2_arrondissement"] = None
                    else:
                        st.session_state["p2_arrondissement"] = new_arr
                    st.rerun()
        else:
            st.plotly_chart(fig_arr, use_container_width=True)

    st.markdown(
        '<div class="section-title">Carte de chaleur — Vitesse moyenne des compteurs</div>',
        unsafe_allow_html=True
    )
    m3 = make_base_map(zoom=13)
    folium.GeoJson(gdf_reseau, name="Réseau cyclable", style_function=style_reseau_fond, control=False).add_to(m3)
    vit_col = "vitesseMoyenne"

    fg_heat = folium.FeatureGroup(name="🌡️ Carte de chaleur — vitesse", show=True)
    HeatMap(
        df_cpt_agg[["latitude", "longitude", vit_col]].values.tolist(),
        min_opacity=0.35, radius=22, blur=16,
        gradient={0.0: "#2471A3", 0.4: "#1E8449", 0.7: "#D4AC0D", 1.0: "#C0392B"},
    ).add_to(fg_heat)
    fg_heat.add_to(m3)
    vit_min, vit_max = df_cpt_agg[vit_col].min(), df_cpt_agg[vit_col].max()

    def coul_vit(v):
        r = (v - vit_min) / (vit_max - vit_min) if vit_max > vit_min else 0.5
        return "#2471A3" if r < 0.33 else ("#D4AC0D" if r < 0.66 else "#C0392B")

    fg_cpt = folium.FeatureGroup(name="📍 Compteurs cyclistes", show=True)
    for _, row in df_cpt_agg.iterrows():
        vol_txt = (
            f"{row['volume']:.0f}"
            if "volume" in row and not np.isnan(row.get("volume", float("nan")))
            else "—"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=7, color="white", weight=1.5,
            fill=True, fill_color=coul_vit(row[vit_col]), fill_opacity=0.9,
            popup=folium.Popup(
                f"<b>Vitesse moy :</b> {row[vit_col]:.1f} km/h<br>"
                f"<b>Volume moy :</b> {vol_txt}",
                max_width=180
            ),
            tooltip=f"{row[vit_col]:.1f} km/h",
        ).add_to(fg_cpt)
    fg_cpt.add_to(m3)
    folium.LayerControl(position="topright", collapsed=True).add_to(m3)
    m3.get_root().html.add_child(folium.Element(f"""
    <div style="position:fixed;bottom:28px;left:28px;width:210px;
    background:rgba(255,255,255,0.97);border-radius:8px;
    box-shadow:0 2px 16px rgba(0,0,0,0.14);font-family:sans-serif;z-index:9999;padding:14px 18px;">
      <div style="font-size:12px;font-weight:600;text-transform:uppercase;
      letter-spacing:0.08em;color:#566573;margin-bottom:10px;">Vitesse cycliste (km/h)</div>
      <div style="background:linear-gradient(to right,#2471A3,#1E8449,#D4AC0D,#C0392B);
      height:8px;border-radius:4px;margin-bottom:5px;"></div>
      <div style="display:flex;justify-content:space-between;font-size:10px;color:#7F8C8D;">
        <span>{vit_min:.1f}</span>
        <span>{(vit_min + vit_max) / 2:.1f}</span>
        <span>{vit_max:.1f} km/h</span>
      </div>
      <div style="font-size:10px;color:#AAB7B8;margin-top:8px;">
        {len(df_cpt_agg)} compteurs — cliquer pour détail</div>
    </div>"""))
    render_map(m3, height=460)


# ═══════════════════════════════════════════════
# PAGE 3 — DÉPLACEMENTS BIXI
# ═══════════════════════════════════════════════
elif page == "Déplacements Bixi":
  with st.spinner("Chargement de la page…"):
    from page3_bixi_trajets import render_page3
    render_page3()


# ═══════════════════════════════════════════════
# PAGE 4 — AIDE À LA DÉCISION
# ═══════════════════════════════════════════════
elif page == "Aide à la Décision":
  with st.spinner("Chargement de la page…"):

    st.markdown("""
    <div class="page-header">
      <h1>Aide à la décision</h1>
    </div>
    """, unsafe_allow_html=True)

    try:
        df_trajets_p3 = pd.read_csv("page3_resultats_trajets.csv")
        has_trajets_p3 = True
        nb_trajets_p3  = len(df_trajets_p3)
    except FileNotFoundError:
        has_trajets_p3 = False
        nb_trajets_p3  = 0

    try:
        df_rues_candidates = pd.read_csv("page3_rues_candidates.csv")
        has_rues = not df_rues_candidates.empty
    except FileNotFoundError:
        has_rues = False
        df_rues_candidates = pd.DataFrame()

    @st.cache_data(show_spinner=False)
    def reverse_geocode(lat, lon):
        try:
            url = (
                f"https://nominatim.openstreetmap.org/reverse"
                f"?lat={lat}&lon={lon}&format=json&zoom=16"
            )
            r = requests.get(
                url,
                headers={"User-Agent": "securite-cycliste-mtl"},
                timeout=8
            )
            data = r.json()
            addr = data.get("address", {})
            rue  = (addr.get("road") or addr.get("pedestrian") or
                    addr.get("path") or "Rue inconnue")
            qrt  = (addr.get("quarter") or addr.get("suburb") or
                    addr.get("neighbourhood") or "")
            return rue, qrt
        except Exception:
            return "Rue inconnue", ""

    st.markdown("""
    <div style="background:#EBF2FA;border-left:4px solid #1A5276;border-radius:0 8px 8px 0;
    padding:14px 20px;margin:24px 0 20px 0;">
      <div style="font-size:16px;font-weight:600;color:#1A2533;margin-bottom:4px;">
        Volet 1 — Sécurité des cyclistes
      </div>
      <div style="font-size:13px;color:#7F8C8D;">
        Interventions prioritaires basées sur les collisions SAAQ 2021 · Sur piste et hors piste
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ZONES À RISQUE SUR PISTE ────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Zones à risque sur piste existante</div>',
        unsafe_allow_html=True
    )

    nb_mortels_sur = int(gdf_joined[
        (gdf_joined["classification"] == "Sur piste") &
        (gdf_joined["GRAVITE"] == "Mortel")
    ].shape[0])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="kpi-card rouge"><div class="kpi-value">{acc_sur:,}</div><div class="kpi-label">Accidents sur piste</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card rouge"><div class="kpi-value">{nb_mortels_sur}</div><div class="kpi-label">Dont mortels</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Recommandation 1 — Top 5 intersections réelles à auditer
    # On groupe par cellule géographique fine (≈50 m) pour identifier des points physiques distincts,
    # puis on géocode chaque centroïde pour obtenir l'adresse. On déduplique par adresse pour éviter
    # que la même intersection apparaisse deux fois à cause d'un léger décalage GPS.
    gdf_sur_wgs = gdf_joined_wgs[gdf_joined_wgs["classification"] == "Sur piste"].copy()

    # Grille fine ~50 m (0.0005° ≈ 45 m à cette latitude)
    gdf_sur_wgs["lat_g"] = (gdf_sur_wgs.geometry.y / 0.0005).round() * 0.0005
    gdf_sur_wgs["lon_g"] = (gdf_sur_wgs.geometry.x / 0.0005).round() * 0.0005

    clusters = (
        gdf_sur_wgs.groupby(["lat_g", "lon_g"])
        .agg(
            nb=("GRAVITE", "count"),
            graves=("GRAVITE", lambda x: x.isin(["Mortel", "Blessé grave"]).sum()),
            score_=("GRAVITE", lambda x: x.isin(["Mortel", "Blessé grave"]).sum() * 3 + len(x))
        )
        .reset_index()
        .sort_values("score_", ascending=False)
        .head(20)   # on en prend 20 pour pouvoir dédupliquer après géocodage
        .reset_index(drop=True)
    )

    # Géocodage + déduplication par adresse (évite doublons rue Rachel × 2 clusters voisins)
    seen_adresses = set()
    top5_rows_clean = []
    for _, row_t in clusters.iterrows():
        rue_t, qrt_t = reverse_geocode(row_t["lat_g"], row_t["lon_g"])
        cle = rue_t.strip().lower()
        if cle in seen_adresses or rue_t == "Rue inconnue":
            continue
        seen_adresses.add(cle)
        top5_rows_clean.append((rue_t, qrt_t, int(row_t["nb"]), int(row_t["graves"]), row_t["lat_g"], row_t["lon_g"]))
        if len(top5_rows_clean) == 5:
            break

    top5_html_rows = ""
    for idx_t, (rue_t, qrt_t, nb_t, grav_t, _, _) in enumerate(top5_rows_clean):
        lieu = rue_t + (f", {qrt_t}" if qrt_t else "")
        grave_txt = f' · <span style="color:#C0392B;font-weight:600;">{grav_t} grave{"s" if grav_t > 1 else ""}</span>' if grav_t > 0 else ""
        top5_html_rows += (
            f'<tr><td style="padding:6px 10px;font-weight:600;color:#1A5276;">#{idx_t+1}</td>'
            f'<td style="padding:6px 10px;">{lieu}</td>'
            f'<td style="padding:6px 10px;text-align:center;">{nb_t}{grave_txt}</td></tr>'
        )

    st.markdown(f"""
    <div class="reco-card" style="border-left-color:#1A5276;">
      <div class="reco-title">Recommandation 1 — Auditer les intersections à haute sinistralité sur piste</div>
      <div class="reco-body">
        Malgré la présence d'une piste cyclable, <b>{acc_sur:,} accidents</b> se sont produits
        à moins de 15 m d'une infrastructure. Ce phénomène s'explique principalement par des
        <b>conflits aux intersections</b> : virages non protégés, angles morts pour les camions,
        feux non adaptés aux cyclistes. La recommandation est d'effectuer un audit terrain
        des 5 secteurs d'intersection ci-dessous (chaque entrée est un point géographique distinct),
        puis d'y installer des <b>avances cyclistes</b>,
        des <b>sas vélo</b> aux feux rouges et des <b>déflecteurs physiques</b>.<br><br>
        <b>Top 5 secteurs à auditer en priorité :</b><br>
        <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:13px;">
          <thead>
            <tr style="background:#F0F3F6;">
              <th style="padding:6px 10px;text-align:left;color:#7F8C8D;font-weight:600;">Rang</th>
              <th style="padding:6px 10px;text-align:left;color:#7F8C8D;font-weight:600;">Secteur (rue la plus proche)</th>
              <th style="padding:6px 10px;text-align:center;color:#7F8C8D;font-weight:600;">Accidents</th>
            </tr>
          </thead>
          <tbody>{top5_html_rows}</tbody>
        </table>
      </div>
      <div class="reco-meta">Source : Collisions SAAQ 2021 — accidents à ≤ 15 m d'une piste · clusters ~50 m · géocodage Nominatim · dédupliqués par adresse</div>
    </div>
    """, unsafe_allow_html=True)

    actions_sec = [
        "Séparateurs physiques + signalisation renforcée",
        "Bande cyclable protégée + avance cycliste aux feux",
        "Zone de circulation apaisée (30 km/h) + marquage prioritaire",
    ]
    top3_rues_sec = []
    for _, row in top3.iterrows():
        rue, qrt = reverse_geocode(row["lat_grid"], row["lon_grid"])
        top3_rues_sec.append((rue, qrt, row))

    # PAGE 4 FIX: toutes les recommandations en navy — couleur neutre, pas de connotation bon/mauvais
    couleurs_rec = ["navy", "navy", "navy"]
    for i, (rue, qrt, row) in enumerate(top3_rues_sec):
        stn = row.get("station", "—")
        if isinstance(stn, float):
            stn = "—"
        st.markdown(f"""
        <div class="reco-card {couleurs_rec[i]}">
          <div class="reco-title">Recommandation {i+2} — {rue} {f"({qrt})" if qrt else ""}</div>
          <div class="reco-body">
            <b>{row['nb_accidents']} accidents</b> hors réseau cyclable dans ce secteur,
            dont <b style="color:#C0392B">{row['nb_graves']} graves ou mortels</b>.
            Station Bixi à proximité : <b>{stn}</b> — confirme un fort flux cycliste non protégé.<br><br>
            <b>Action recommandée :</b> {actions_sec[i]}
          </div>
          <div class="reco-meta">Score composite : {row['score']} · SAAQ 2021 + Bixi live</div>
        </div>
        """, unsafe_allow_html=True)

    # ── CARTE POINTS NOIRS ───────────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Carte — Points noirs de sécurité</div>',
        unsafe_allow_html=True
    )
    # PAGE 4 FIX: note explicative reliant les recommandations à la carte
    st.markdown("""
    <p style="font-size:13px;color:#566573;margin-bottom:12px;">
      Les marqueurs numérotés correspondent aux <b>Recommandations 2, 3 et 4</b> ci-dessus
      (zones hors réseau cyclable à fort achalandage Bixi).
      Les couleurs des marqueurs suivent le même ordre de priorité : 
      <span style="color:#C0392B;font-weight:600;">■ Rouge = Recommandation 2</span> (priorité 1),
      <span style="color:#E67E22;font-weight:600;">■ Orange = Recommandation 3</span>,
      <span style="color:#1A5276;font-weight:600;">■ Bleu = Recommandation 4</span>.
    </p>
    """, unsafe_allow_html=True)

    m_sec = make_base_map()
    folium.GeoJson(gdf_reseau, name="Réseau cyclable", style_function=style_reseau_fond, control=False).add_to(m_sec)

    fg_sur_acc  = folium.FeatureGroup(name="🟠 Accidents sur piste",       show=True)
    fg_hor_acc  = folium.FeatureGroup(name="🔴 Accidents hors piste",      show=True)
    fg_top3_sec = folium.FeatureGroup(name="📍 Recommandations 2, 3 et 4", show=True)

    for _, row in gdf_joined_wgs.iterrows():
        cl   = row["classification"]
        coul = "#E74C3C" if cl == "Hors piste" else "#E67E22"
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4, color=coul, fill=True, fill_opacity=0.5, weight=0,
            tooltip=f"{cl} — {row.get('GRAVITE','?')}",
        ).add_to(fg_hor_acc if cl == "Hors piste" else fg_sur_acc)

    # PAGE 4 FIX: cohérence des couleurs rouge/orange/bleu avec les reco cards
    icones_sec_couleurs = ["red", "orange", "blue"]
    for i, (rue, qrt, row) in enumerate(top3_rues_sec):
        stn = row.get("station", "—")
        if isinstance(stn, float):
            stn = "—"
        qrt_span = (
            f'<br><span style="color:#7F8C8D;font-size:11px">{qrt}</span>'
            if qrt else ''
        )
        popup_html = (
            f"<div style='font-family:sans-serif;font-size:13px;min-width:220px;'>"
            f"<b style='color:#C0392B'>Recommandation {i+2}</b><br>"
            f"<b>{rue}</b> {qrt_span}<br><br>"
            f"<b>{row['nb_accidents']}</b> accidents · "
            f"<b style='color:#C0392B'>{row['nb_graves']} graves</b><br>"
            f"Station Bixi : {stn}<br>"
            f"<hr style='margin:6px 0;border:none;border-top:1px solid #eee;'>"
            f"<span style='color:#1A5276;font-size:12px'>➤ {actions_sec[i]}</span></div>"
        )
        folium.Marker(
            location=[row["lat_grid"], row["lon_grid"]],
            icon=folium.Icon(
                color=icones_sec_couleurs[i], icon="warning-sign", prefix="glyphicon"
            ),
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"Recommandation {i+2} — {rue} · {row['nb_accidents']} accidents",
        ).add_to(fg_top3_sec)

    fg_hor_acc.add_to(m_sec)
    fg_sur_acc.add_to(m_sec)
    fg_top3_sec.add_to(m_sec)
    folium.LayerControl(position="topright", collapsed=True).add_to(m_sec)
    m_sec.get_root().html.add_child(folium.Element(make_legende([
        ("#E74C3C", "Accident hors piste"),
        ("#E67E22", "Accident sur piste"),
        ("#C0392B", "Recommandation 2 (priorité 1)"),
        ("#E67E22", "Recommandation 3"),
        ("#1A5276", "Recommandation 4"),
    ], "Sécurité cycliste")))
    render_map(m_sec, height=500)

    # ── VOLET 2 — NOUVELLES INFRASTRUCTURES ─────────────────────────────────
    st.markdown("""
    <div style="background:#EBF2FA;border-left:4px solid #1A5276;border-radius:0 8px 8px 0;
    padding:14px 20px;margin:40px 0 20px 0;">
      <div style="font-size:16px;font-weight:600;color:#1A2533;margin-bottom:4px;">
        Volet 2 — Nouvelles infrastructures cyclables
      </div>
      <div style="font-size:13px;color:#7F8C8D;">
        Corridors Bixi à fort achalandage sans protection · Rues candidates à une nouvelle piste
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not has_rues:
        st.info(
            "💡 Naviguez d'abord vers **Déplacements Bixi** pour lancer l'analyse de routing. "
            "Les recommandations apparaîtront ici automatiquement."
        )
    else:
        top3_rues_infra    = df_rues_candidates.head(3)
        types_action_infra = [
            "Piste cyclable bidirectionnelle protégée physiquement (REV ou piste séparée)",
            "Bande cyclable avec séparateurs ou surélévation aux intersections",
            "Chaussée désignée avec signalisation renforcée + priorité cycliste aux feux",
        ]
        rangs = ["Priorité 1", "Priorité 2", "Priorité 3"]

        for i, (_, row) in enumerate(top3_rues_infra.iterrows()):
            st.markdown(f"""
            <div class="reco-card navy">
              <div class="reco-title">{rangs[i]} — {row['nom_rue']}</div>
              <div class="reco-body">
                <b>{int(row['passages_bixi']):,} passages Bixi</b> empruntent ce corridor
                sans protection cyclable, sur <b>{row['longueur_totale_m']:.0f} m</b>
                de voie exposée ({row['nb_troncons']} segments).
                La longueur justifie un aménagement structurant qui profitera à l'ensemble
                du corridor, pas seulement à un tronçon isolé.<br><br>
                <b>Action recommandée :</b> {types_action_infra[i]}
              </div>
              <div class="reco-meta">
                Score : {row['score']:.1f} · Bixi Top {nb_trajets_p3} Origine-Destination + OSMnx routing
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(
            '<div class="section-title">Top 10 rues candidates — Détail complet</div>',
            unsafe_allow_html=True
        )
        df_display = df_rues_candidates.head(10).copy().reset_index(drop=True)
        df_display.index = range(1, len(df_display) + 1)
        df_display.columns = ["Rue", "Passages Bixi", "Longueur exposée (m)", "Tronçons", "Score"]
        st.dataframe(
            df_display.style.format({
                "Longueur exposée (m)": "{:,.0f}",
                "Passages Bixi": "{:,}",
                "Score": "{:.1f}"
            }),
            use_container_width=True, height=380,
            column_config={
                "Rue": st.column_config.TextColumn(
                    "Rue",
                    help="Nom de la rue (OpenStreetMap) empruntée sans protection cyclable"
                ),
                "Passages Bixi": st.column_config.NumberColumn(
                    "Passages Bixi",
                    help="Nombre total de passages Bixi enregistrés sur ce corridor sans infrastructure cyclable"
                ),
                "Longueur exposée (m)": st.column_config.NumberColumn(
                    "Longueur exposée (m)",
                    help="Distance cumulée (en mètres) sans piste ni bande protégée sur cette rue"
                ),
                "Tronçons": st.column_config.NumberColumn(
                    "Tronçons",
                    help="Nombre de segments de rue distincts sans protection (graphe OSMnx)"
                ),
                "Score": st.column_config.NumberColumn(
                    "Score",
                    help="Score de priorité composite : 60 % passages Bixi normalisés + 40 % longueur exposée normalisée (sur 100)"
                ),
            }
        )

        st.markdown(
            '<div class="section-title">Carte — Top 3 corridors à prioriser pour une nouvelle piste</div>',
            unsafe_allow_html=True
        )

        try:
            import ast
            df_edges_map = pd.read_parquet("data/edges_routes.parquet")
            has_edges = True
        except Exception:
            has_edges = False

        m_infra = make_base_map()
        folium.GeoJson(gdf_reseau, name="Réseau cyclable", style_function=style_reseau_fond, control=False).add_to(m_infra)

        couleurs_infra = ["#1A5276", "#117A65", "#6C3483"]
        top3_noms = list(top3_rues_infra["nom_rue"])

        rangs_map = ["Priorité 1", "Priorité 2", "Priorité 3"]

        if has_edges:
            for rank, nom_rue in enumerate(top3_noms):
                fg_rue   = folium.FeatureGroup(name=f"{rangs_map[rank]} — {nom_rue}", show=True)
                edges_rue = df_edges_map[
                    (~df_edges_map["protege"]) & (df_edges_map["nom_rue"] == nom_rue)
                ]
                max_occ = max(df_edges_map["occurrences"].max(), 1)
                for _, erow in edges_rue.iterrows():
                    try:
                        coords = ast.literal_eval(erow["coords_json"])
                        latlon = [(lat, lon) for lon, lat in coords]
                        weight = 4 + (erow["occurrences"] / max_occ) * 5
                        folium.PolyLine(
                            latlon,
                            color=couleurs_infra[rank],
                            weight=weight, opacity=0.85,
                            tooltip=f"{rangs_map[rank]} — {nom_rue} · {int(erow['occurrences'])} passages Bixi",
                        ).add_to(fg_rue)
                    except Exception:
                        continue
                fg_rue.add_to(m_infra)

        for rank, (_, row) in enumerate(top3_rues_infra.iterrows()):
            if has_edges:
                edges_rue = df_edges_map[df_edges_map["nom_rue"] == row["nom_rue"]]
                if len(edges_rue) > 0:
                    try:
                        mid_idx = len(edges_rue) // 2
                        coords  = ast.literal_eval(edges_rue.iloc[mid_idx]["coords_json"])
                        lon_c, lat_c = coords[len(coords) // 2]
                    except Exception:
                        lat_c, lon_c = 45.5088, -73.5878
                else:
                    lat_c, lon_c = 45.5088, -73.5878
            else:
                lat_c, lon_c = 45.5088, -73.5878

            popup_html = (
                f"<div style='font-family:sans-serif;font-size:13px;min-width:230px;'>"
                f"<b style='color:{couleurs_infra[rank]}'>{rangs_map[rank]} — {row['nom_rue']}</b><br><br>"
                f"Passages Bixi : <b>{int(row['passages_bixi']):,}</b><br>"
                f"Longueur exposée : <b>{row['longueur_totale_m']:.0f} m</b><br>"
                f"Score : <b>{row['score']:.1f}</b><br>"
                f"<hr style='margin:8px 0;border:none;border-top:1px solid #eee;'>"
                f"<span style='color:#1A5276;font-size:12px'>➤ {types_action_infra[rank]}</span></div>"
            )
            folium.Marker(
                location=[lat_c, lon_c],
                icon=folium.Icon(
                    color=["blue", "darkblue", "cadetblue"][rank],
                    icon="road", prefix="glyphicon"
                ),
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"{rangs_map[rank]} — {row['nom_rue']}",
            ).add_to(m_infra)

        folium.LayerControl(position="topright", collapsed=True).add_to(m_infra)
        legende_items = [(couleurs_infra[i], f"{rangs_map[i]} — {top3_noms[i]}") for i in range(len(top3_noms))]
        legende_items.append(("#AAB7B8", "Réseau existant (fond)"))
        m_infra.get_root().html.add_child(
            folium.Element(make_legende(legende_items, "Corridors prioritaires"))
        )
        render_map(m_infra, height=520)

    st.markdown("""
    <div style="margin-top:32px;background:#F4F6F7;border-radius:6px;
    padding:14px 18px;font-size:12px;color:#566573;line-height:1.8;border:1px solid #E5E8EC;">
      <b>Note méthodologique :</b>
      Classification sur/hors piste : seuil 15 m via sjoin_nearest (EPSG:32618) · SAAQ 2021.
      Zones prioritaires hors piste : score = accidents × 2 + graves × 5 + passages Bixi normalisés × 3.
      Rues candidates : routing Dijkstra OSMnx sur Top 100 O-D Bixi · score = 60 % volume + 40 % longueur exposée.
      Géocodage inverse : API Nominatim (OpenStreetMap).
      <b>Validation terrain recommandée avant tout investissement.</b>
    </div>
    """, unsafe_allow_html=True)
"""
PAGE 3 — Déplacements Bixi & Analyse des tronçons sans infrastructure cyclable
Auteurs : Laurie-Anne Duclos, Mathieu Couturier, Alexis Desjardins

LOGIQUE :
1. Top N paires Origine-Destination Bixi les plus fréquentes (CSV déjà agrégé)
2. Routing OSMnx sur le graphe cyclable de Montréal pour chaque trajet
3. Pour chaque edge traversé : est-il protégé via jointure spatiale (GeoJSON officiel MTL) + tags OSM ?
4. On agrège par nom de rue (OSM) → total de passages Bixi hors infrastructure
5. On garde les rues longues (> 800 m cumulés) avec beaucoup de passages
6. Carte interactive : rues colorées par statut, épaisseur = volume Bixi
   → Tableau : top 10 rues candidates
   → Carte   : top 3 rues candidates seulement (les plus longues / fréquentées)
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point
from streamlit_folium import st_folium
import warnings
warnings.filterwarnings("ignore")

# ─── Constantes ─────────────────────────────────────────────────────────────

MONTREAL_BBOX = (45.41, -73.98, 45.70, -73.47)   # south, west, north, east
TOP_OD_PAIRS  = 5      # Mettre 100 en production, 5 pour les tests rapides
MIN_RUE_M     = 800    # Longueur minimale (m) pour apparaître dans les recommandations
MIN_PASSAGES  = 5      # Passages Bixi min pour être candidate
BUFFER_M      = 15     # Buffer (mètres) pour la jointure spatiale réseau officiel ↔ OSMnx

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_family="DM Sans",
    font_size=12,
    margin=dict(t=10, b=10, l=0, r=0),
)

# ─── CSS ────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #1C2833; }
    .page-header { border-left: 4px solid #1A5276; padding: 10px 0 10px 18px; margin-bottom: 28px; }
    .page-header h1 { font-family: 'DM Serif Display', serif; font-size: 36px; font-weight: 400; color: #1A2533; margin: 0 0 4px 0; }
    .page-header p { font-size: 13px; color: #9DAAB2; margin: 0; }
    .section-title { font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
        color: #566573; margin: 32px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #E5E8EC; }
    .kpi-row { display: flex; gap: 16px; margin-bottom: 24px; }
    .kpi-card { flex: 1; background: white; border: 1px solid #E5E8EC; border-radius: 8px;
        padding: 18px 22px; border-top: 3px solid #1A5276; }
    .kpi-card.rouge { border-top-color: #C0392B; }
    .kpi-card.vert  { border-top-color: #1E8449; }
    .kpi-card.jaune { border-top-color: #D4AC0D; }
    .kpi-card.bleu  { border-top-color: #2471A3; }
    .kpi-value { font-size: 30px; font-weight: 600; color: #1A2533; line-height: 1; }
    .kpi-unit  { font-size: 14px; font-weight: 400; color: #7F8C8D; margin-left: 3px; }
    .kpi-label { font-size: 12px; color: #7F8C8D; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }
    .reco-card { background: white; border: 1px solid #E5E8EC; border-radius: 8px; padding: 22px 26px;
        margin-bottom: 16px; border-left: 4px solid #1A5276; }
    .reco-card.rouge { border-left-color: #C0392B; }
    .reco-card.jaune { border-left-color: #D4AC0D; }
    .reco-title { font-size: 16px; font-weight: 600; color: #1A2533; margin-bottom: 8px; }
    .reco-body  { font-size: 14px; color: #566573; line-height: 1.7; margin-bottom: 10px; }
    .reco-meta  { font-size: 11px; color: #AAB7B8; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)


# ─── Chargement du graphe OSMnx ─────────────────────────────────────────────

@st.cache_resource(show_spinner="Chargement du graphe OSMnx...")
def load_graph():
    import os
    if os.path.exists("data/graph_montreal_bike.graphml"):
        return ox.load_graphml("data/graph_montreal_bike.graphml")
    ox_ver = tuple(int(x) for x in ox.__version__.split(".")[:2])
    try:
        if ox_ver >= (2, 0):
            G = ox.graph_from_bbox(
                bbox=(-73.98, 45.41, -73.47, 45.70),
                network_type="bike", retain_all=False, simplify=True
            )
        else:
            G = ox.graph_from_bbox(
                north=45.70, south=45.41, east=-73.47, west=-73.98,
                network_type="bike", retain_all=False, simplify=True
            )
    except Exception:
        G = ox.graph_from_place(
            "Montreal, Quebec, Canada",
            network_type="bike", retain_all=False, simplify=True
        )
    os.makedirs("data", exist_ok=True)
    ox.save_graphml(G, "data/graph_montreal_bike.graphml")
    return G


@st.cache_resource(show_spinner="Extraction des edges OSMnx...")
def get_edges_gdf(_G):
    nodes, edges = ox.graph_to_gdfs(_G)
    return nodes, edges


# ─── Chargement des données sources ─────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_bixi():
    df = pd.read_csv("bixi.csv")
    cols = df.columns.tolist()
    rename = {}
    if cols[0] != "STARTSTATIONNAME":
        rename[cols[0]] = "STARTSTATIONNAME"
    if cols[1] != "ENDSTATIONNAME":
        rename[cols[1]] = "ENDSTATIONNAME"
    if rename:
        df = df.rename(columns=rename)
    return df


@st.cache_data(show_spinner=False)
def load_reseau():
    URL = (
        "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536"
        "/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"
    )
    return gpd.read_file(URL)


# ─── Top O-D ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Calcul du Top Origine-Destination...")
def compute_top_od(_df, n=TOP_OD_PAIRS):
    needed = [
        "STARTSTATIONNAME", "ENDSTATIONNAME",
        "STARTSTATIONLATITUDE", "STARTSTATIONLONGITUDE",
        "ENDSTATIONLATITUDE", "ENDSTATIONLONGITUDE",
        "occurrences",
    ]
    df = _df.dropna(subset=needed).copy()
    df = df[df["STARTSTATIONNAME"] != df["ENDSTATIONNAME"]]
    df = df.sort_values("occurrences", ascending=False).head(n).reset_index(drop=True)
    return df


# ─── Jointure spatiale : réseau officiel → set d'edges protégés ──────────────

@st.cache_data(show_spinner="Jointure spatiale réseau officiel ↔ OSMnx (filtre angulaire)...")
def build_protected_set(_gdf_reseau, _edges_gdf, buffer_m=BUFFER_M):
    MAX_ANGLE_DEG = 35

    gdf_prot = _gdf_reseau[
        (_gdf_reseau["PROTEGE_4S"] == "Oui") |
        (_gdf_reseau["TYPE_VOIE_DESC"].str.contains("Piste cyclable", case=False, na=False))
    ].copy()

    st.write(f"🛡️ {len(gdf_prot)} tronçons protégés dans le réseau officiel MTL")

    gdf_prot_proj = gdf_prot.to_crs(epsg=32188)
    edges_proj    = _edges_gdf.to_crs(epsg=32188)

    def get_line_bearing(geom):
        coords = list(geom.coords)
        x0, y0 = coords[0]
        x1, y1 = coords[-1]
        return np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180

    def angle_diff(a1, a2):
        diff = abs(a1 - a2) % 180
        return min(diff, 180 - diff)

    from shapely.strtree import STRtree
    prot_geoms    = list(gdf_prot_proj.geometry)
    prot_tree     = STRtree(prot_geoms)
    prot_bearings = [get_line_bearing(g) for g in prot_geoms]
    prot_buffer_union = gdf_prot_proj.geometry.buffer(buffer_m).unary_union

    protected_set = set()
    candidates = edges_proj[edges_proj.geometry.intersects(prot_buffer_union)]

    for (u, v, _), edge_row in candidates.iterrows():
        edge_geom    = edge_row.geometry
        edge_bearing = get_line_bearing(edge_geom)
        nearby_idxs  = prot_tree.query(edge_geom.buffer(buffer_m))

        for idx in nearby_idxs:
            prot_geom = prot_geoms[idx]
            if edge_geom.distance(prot_geom) > buffer_m:
                continue
            if angle_diff(edge_bearing, prot_bearings[idx]) <= MAX_ANGLE_DEG:
                protected_set.add((u, v))
                break

    st.write(
        f"✅ {len(protected_set)} edges OSMnx protégés après filtre angulaire "
        f"(buffer={buffer_m}m, angle≤{MAX_ANGLE_DEG}°)"
    )
    return protected_set


# ─── Classification d'un edge ────────────────────────────────────────────────

def is_protected(edge_data: dict, u: int, v: int, protected_set: set) -> bool:
    if (u, v) in protected_set or (v, u) in protected_set:
        return True

    PROTECTED_VALUES = {
        "track", "opposite_track",
        "buffered_lane", "protected_lane",
        "segregated", "crossing",
        "lane", "shared_lane", "opposite_lane",
    }

    hw = edge_data.get("highway", "")
    if isinstance(hw, list):
        hw = hw[0]
    if hw == "cycleway":
        return True

    for key in ["cycleway", "cycleway:right", "cycleway:left", "cycleway:both"]:
        val = edge_data.get(key, "")
        if isinstance(val, list):
            val = val[0]
        if val in PROTECTED_VALUES:
            return True

    return False


# ─── Routing principal ────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Calcul des routes OSMnx...")
def route_top_od(_G, _od_df, _protected_set):
    records_edges   = []
    records_trajets = []

    for idx, row in _od_df.iterrows():
        try:
            orig = ox.distance.nearest_nodes(
                _G, X=row["STARTSTATIONLONGITUDE"], Y=row["STARTSTATIONLATITUDE"]
            )
            dest = ox.distance.nearest_nodes(
                _G, X=row["ENDSTATIONLONGITUDE"], Y=row["ENDSTATIONLATITUDE"]
            )

            if orig == dest:
                continue

            path = nx.shortest_path(_G, orig, dest, weight="length")

            dist_total    = 0
            dist_protegee = 0

            for u, v in zip(path[:-1], path[1:]):
                edge_data = min(
                    _G[u][v].values(),
                    key=lambda d: d.get("length", 9999)
                )
                length = edge_data.get("length", 0)
                prot   = is_protected(edge_data, u, v, _protected_set)

                name = edge_data.get("name", "Rue inconnue")
                if isinstance(name, list):
                    name = name[0]

                dist_total    += length
                dist_protegee += length if prot else 0

                if "geometry" in edge_data:
                    geom = edge_data["geometry"]
                else:
                    n_u = _G.nodes[u]
                    n_v = _G.nodes[v]
                    geom = LineString([(n_u["x"], n_u["y"]), (n_v["x"], n_v["y"])])

                records_edges.append({
                    "u":           u,
                    "v":           v,
                    "nom_rue":     name,
                    "protege":     prot,
                    "length_m":    length,
                    "occurrences": row["occurrences"],
                    "depart":      row["STARTSTATIONNAME"],
                    "arrivee":     row["ENDSTATIONNAME"],
                    "geometry":    geom,
                })

            pct_protege = (dist_protegee / dist_total * 100) if dist_total > 0 else 0
            records_trajets.append({
                "Départ":           row["STARTSTATIONNAME"],
                "Arrivée":          row["ENDSTATIONNAME"],
                "Occurrences":      row["occurrences"],
                "Dist. réseau (m)": round(dist_total),
                "% sur piste":      round(pct_protege, 1),
            })

        except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
            st.warning(f"⚠️ Trajet {idx} ({row['STARTSTATIONNAME']} → {row['ENDSTATIONNAME']}) : {e}")
            continue
        except Exception as e:
            st.warning(f"⚠️ Erreur inattendue trajet {idx} : {e}")
            continue

    df_edges   = pd.DataFrame(records_edges)
    df_trajets = pd.DataFrame(records_trajets)
    return df_edges, df_trajets


# ─── Analyse des rues candidates ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def analyse_rues_candidates(_df_edges):
    hors = _df_edges[~_df_edges["protege"]].copy()
    if hors.empty:
        return pd.DataFrame()

    agg = (
        hors.groupby("nom_rue")
            .agg(
                passages_bixi     =("occurrences", "sum"),
                longueur_totale_m =("length_m",    "sum"),
                nb_troncons       =("length_m",    "count"),
            )
            .reset_index()
    )
    agg = agg[
        (agg["longueur_totale_m"] >= MIN_RUE_M) &
        (agg["passages_bixi"]     >= MIN_PASSAGES)
    ].copy()

    max_p = agg["passages_bixi"].max()
    max_l = agg["longueur_totale_m"].max()
    agg["score"] = (
        (agg["passages_bixi"]     / max_p * 0.6) +
        (agg["longueur_totale_m"] / max_l * 0.4)
    ).round(4) * 100

    return agg.sort_values("score", ascending=False).head(10).reset_index(drop=True)


# ─── Construction de la carte Folium ─────────────────────────────────────────

def build_map_trajets(df_edges: pd.DataFrame, gdf_reseau, rues_candidates: pd.DataFrame):
    m = folium.Map(location=[45.5088, -73.5878], zoom_start=13, tiles="cartodbpositron")

    def style_fond(feature):
        t = feature["properties"].get("TYPE_VOIE_DESC", "")
        if "express" in t.lower():  return {"color": "#C0392B", "weight": 2,   "opacity": 0.35}
        if "Piste"   in t:          return {"color": "#1E8449", "weight": 1.5, "opacity": 0.3}
        if "Bande"   in t:          return {"color": "#2471A3", "weight": 1,   "opacity": 0.25}
        return {"color": "#BDC3C7", "weight": 0.6, "opacity": 0.15}

    folium.GeoJson(
        gdf_reseau,
        style_function=style_fond,
        name="Réseau officiel (fond)"
    ).add_to(m)

    if df_edges.empty:
        st.warning("Aucun edge routé disponible.")
        return m

    max_occ = max(df_edges["occurrences"].max(), 1)

    fg_prot  = folium.FeatureGroup(name="Segments protégés (sur piste)",      show=True)
    fg_nprot = folium.FeatureGroup(name="Segments non protégés (hors piste)", show=True)
    fg_top   = folium.FeatureGroup(name="Top 3 rues candidates (recommandées)", show=True)

    for _, row in df_edges.iterrows():
        geom = row["geometry"]
        if geom is None:
            continue
        coords = [(lat, lon) for lon, lat in geom.coords]
        weight = 1.5 + (row["occurrences"] / max_occ) * 5
        color  = "#1E8449" if row["protege"] else "#C0392B"
        stat   = "Protégé" if row["protege"] else "Non protégé"
        tip    = (
            f"{row['nom_rue']} — {stat}<br>"
            f"{row['occurrences']} passages Bixi · {row['length_m']:.0f} m"
        )
        fg = fg_prot if row["protege"] else fg_nprot
        folium.PolyLine(coords, color=color, weight=weight, opacity=0.65, tooltip=tip).add_to(fg)

    if not rues_candidates.empty:
        top3_noms       = set(rues_candidates.head(3)["nom_rue"])
        candidats_edges = df_edges[
            (~df_edges["protege"]) & (df_edges["nom_rue"].isin(top3_noms))
        ]
        rang_map = {nom: i for i, nom in enumerate(rues_candidates.head(3)["nom_rue"])}
        couleurs_rang = ["#7D0000", "#A93226", "#C0392B"]

        for _, row in candidats_edges.iterrows():
            geom = row["geometry"]
            if geom is None:
                continue
            coords = [(lat, lon) for lon, lat in geom.coords]
            rang   = rang_map.get(row["nom_rue"], 2)
            folium.PolyLine(
                coords,
                color=couleurs_rang[min(rang, 2)],
                weight=7, opacity=0.85,
                tooltip=f"⭐ Candidate #{rang+1} : {row['nom_rue']}",
            ).add_to(fg_top)

    fg_prot.add_to(m)
    fg_nprot.add_to(m)
    fg_top.add_to(m)
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    legende_html = """
    <div style="position:fixed;bottom:28px;left:28px;min-width:230px;
    background:rgba(255,255,255,0.97);border-radius:8px;
    box-shadow:0 2px 16px rgba(0,0,0,0.14);font-family:sans-serif;z-index:9999;padding:14px 18px;">
      <div style="font-size:12px;font-weight:600;text-transform:uppercase;
                  letter-spacing:0.08em;color:#566573;margin-bottom:10px;">Statut des tronçons</div>
      <div style="display:flex;align-items:center;margin:6px 0;">
        <div style="width:28px;height:4px;background:#1E8449;border-radius:2px;margin-right:10px;"></div>
        <span style="font-size:12px;color:#2C3E50;">Sur infrastructure protégée</span>
      </div>
      <div style="display:flex;align-items:center;margin:6px 0;">
        <div style="width:28px;height:4px;background:#C0392B;border-radius:2px;margin-right:10px;"></div>
        <span style="font-size:12px;color:#2C3E50;">Hors infrastructure (risque)</span>
      </div>
      <div style="display:flex;align-items:center;margin:6px 0;">
        <div style="width:28px;height:7px;background:#7D0000;border-radius:2px;margin-right:10px;"></div>
        <span style="font-size:12px;color:#2C3E50;">Top 3 rues candidates (⭐ priorité)</span>
      </div>
      <div style="font-size:10px;color:#AAB7B8;margin-top:10px;">Épaisseur ∝ volume Bixi</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legende_html))
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# RENDU PRINCIPAL DE LA PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_page3():
    inject_css()
    import os

    # PAGE 3 FIX: titre sans sous-titre non pertinent
    st.markdown("""
    <div class="page-header">
      <h1>Déplacements Bixi — Analyse d'infrastructure</h1>
    </div>
    """, unsafe_allow_html=True)

    # PAGE 3 FIX: suppression du badge "données pré-calculées chargées depuis data/"
    # Chargement silencieux

    with st.spinner("Chargement du réseau cyclable officiel..."):
        gdf_reseau = load_reseau()

    # ── Chemin pré-calculé ──────────────────────────────────────────────────
    if (
        os.path.exists("data/trajets_routes.parquet")
        and os.path.exists("data/edges_routes.parquet")
    ):
        df_trajets = pd.read_parquet("data/trajets_routes.parquet")
        df_edges   = pd.read_parquet("data/edges_routes.parquet")

        df_trajets = df_trajets.rename(columns={
            "Depart":           "Départ",
            "Arrivee":          "Arrivée",
            "Dist. reseau (m)": "Dist. réseau (m)",
            "Ratio detour":     "Ratio détour",
        })

        from shapely.geometry import LineString
        import ast

        def parse_geom(s):
            try:
                coords = ast.literal_eval(s)
                return LineString(coords) if len(coords) >= 2 else None
            except Exception:
                return None

        if "coords_json" in df_edges.columns:
            df_edges["geometry"] = df_edges["coords_json"].apply(parse_geom)

        if os.path.exists("data/rues_candidates.parquet"):
            rues = pd.read_parquet("data/rues_candidates.parquet")
        else:
            rues = analyse_rues_candidates(df_edges)

        if os.path.exists("data/top_od_pairs.parquet"):
            od_df = pd.read_parquet("data/top_od_pairs.parquet")
        else:
            df_bixi = load_bixi()
            od_df   = compute_top_od(df_bixi)

    # ── Calcul en direct ────────────────────────────────────────────────────
    else:
        df_bixi = load_bixi()
        od_df   = compute_top_od(df_bixi, n=TOP_OD_PAIRS)

        with st.spinner("Chargement du graphe OSMnx..."):
            G = load_graph()
            nodes_gdf, edges_gdf = get_edges_gdf(G)

        protected_set = build_protected_set(gdf_reseau, edges_gdf, buffer_m=BUFFER_M)

        df_edges, df_trajets = route_top_od(G, od_df, protected_set)
        rues = analyse_rues_candidates(df_edges)

    # PAGE 3 FIX: "Paires Origine-Destination analysées" au lieu de "Paires O-D"
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi-card bleu">
        <div class="kpi-value">{len(od_df)}</div>
        <div class="kpi-label">Paires Origine-Destination analysées</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if df_edges.empty or df_trajets.empty:
        st.error("Impossible de charger les données de routing.")
        return

    # PAGE 3 FIX: "Résultats du routing" renommé, moy. → moyenne au complet, réordonné
    st.markdown(
        '<div class="section-title">Résultats — Statistiques globales</div>',
        unsafe_allow_html=True,
    )

    col_piste = "% sur piste" if "% sur piste" in df_trajets.columns else next(
        (c for c in df_trajets.columns if "piste" in c.lower()), None
    )
    col_dist = next(
        (c for c in df_trajets.columns if "réseau" in c.lower() or "reseau" in c.lower()), None
    )

    pct_moy  = df_trajets[col_piste].mean()  if col_piste else 0
    pct_med  = df_trajets[col_piste].median() if col_piste else 0
    dist_moy = df_trajets[col_dist].mean()   if col_dist  else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        # PAGE 3 FIX: "Moyenne sur piste" (de l'avant, au complet)
        couleur = "vert" if pct_moy >= 60 else ("jaune" if pct_moy >= 40 else "rouge")
        st.markdown(
            f'<div class="kpi-card {couleur}"><div class="kpi-value">{pct_moy:.1f}'
            f'<span class="kpi-unit">%</span></div>'
            f'<div class="kpi-label">Moyenne sur piste</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        # PAGE 3 FIX: "Médiane sur piste" (de l'avant)
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-value">{pct_med:.1f}'
            f'<span class="kpi-unit">%</span></div>'
            f'<div class="kpi-label">Médiane sur piste</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        # PAGE 3 FIX: "Distance moyenne réseau" (moy. → moyenne au complet)
        st.markdown(
            f'<div class="kpi-card bleu"><div class="kpi-value">{dist_moy:.0f}'
            f'<span class="kpi-unit">m</span></div>'
            f'<div class="kpi-label">Distance moyenne réseau</div></div>',
            unsafe_allow_html=True,
        )

    # ── Tableau des trajets ─────────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Détail par trajet</div>',
        unsafe_allow_html=True,
    )
    cols_display = [c for c in ["Départ", "Arrivée", "Occurrences", "Dist. réseau (m)", "% sur piste"]
                    if c in df_trajets.columns]

    # PAGE 3 FIX: index commence à 1 au lieu de 0
    df_trajets_display = df_trajets[cols_display].copy().reset_index(drop=True)
    df_trajets_display.index = range(1, len(df_trajets_display) + 1)
    st.dataframe(
        df_trajets_display,
        use_container_width=True,
        column_config={
            "Départ": st.column_config.TextColumn(
                "Départ",
                help="Nom de la station Bixi de départ du trajet"
            ),
            "Arrivée": st.column_config.TextColumn(
                "Arrivée",
                help="Nom de la station Bixi d'arrivée du trajet"
            ),
            "Occurrences": st.column_config.NumberColumn(
                "Occurrences",
                help="Nombre de fois que ce trajet Origine-Destination a été effectué dans les données Bixi"
            ),
            "Dist. réseau (m)": st.column_config.NumberColumn(
                "Dist. réseau (m)",
                help="Distance totale du trajet calculée sur le graphe cyclable OSMnx (en mètres)"
            ),
            "% sur piste": st.column_config.NumberColumn(
                "% sur piste",
                help="Pourcentage de la distance du trajet effectuée sur une infrastructure cyclable protégée (piste ou bande)"
            ),
        }
    )

    # ── Carte principale ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="section-title">Carte — Trajets Bixi sur/hors infrastructure cyclable</div>',
        unsafe_allow_html=True,
    )
    st.markdown("""
    <p style="font-size:13px;color:#7F8C8D;margin-bottom:12px;">
      <b>Vert</b> = segment protégé · <b>Rouge</b> = hors infrastructure ·
      <b>Rouge épais</b> = top 3 rues candidates prioritaires ·
      Épaisseur proportionnelle au volume de passages Bixi.
    </p>
    """, unsafe_allow_html=True)

    m = build_map_trajets(
        df_edges,
        gdf_reseau,
        rues if not rues.empty else pd.DataFrame(),
    )
    st_folium(m, width="100%", height=600, returned_objects=[])

    # ── Export CSV ───────────────────────────────────────────────────────────
    if not df_trajets.empty:
        df_trajets.to_csv("page3_resultats_trajets.csv", index=False)
    if not rues.empty:
        rues.to_csv("page3_rues_candidates.csv", index=False)

    # ── Note méthodologique ──────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:24px;background:#F4F6F7;border-radius:6px;
    padding:14px 18px;font-size:12px;color:#566573;line-height:1.8;border:1px solid #E5E8EC;">
      <b>Note méthodologique :</b>
      Top {TOP_OD_PAIRS} paires Origine-Destination par fréquence absolue (CSV déjà agrégé, tri direct).
      Graphe vélo OSMnx : <code>network_type="bike"</code> sur la boîte de Montréal.
      Routing : plus court chemin pondéré par <code>length</code> (Dijkstra).
      Classification protégé : jointure spatiale (buffer {BUFFER_M} m) avec le GeoJSON officiel
      de la Ville de Montréal (<code>PROTEGE_4S="Oui"</code> ou <code>TYPE_VOIE_DESC</code> contient
      "Piste cyclable") + tags OSM <code>highway=cycleway</code> / <code>cycleway=track|lane|protected_lane…</code>.
      Seuil longueur minimum rue candidate : {MIN_RUE_M} m · passages minimum : {MIN_PASSAGES}.
      Score rue = 60 % passages Bixi normalisés + 40 % longueur normalisée.
      Tableau : top 10 rues candidates · Carte : top 3 seulement.
    </div>
    """, unsafe_allow_html=True)


# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_page_3 = render_page3
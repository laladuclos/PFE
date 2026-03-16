"""
preprocess.py — Script de pré-traitement
Auteurs : Laurie-Anne Duclos, Mathieu Couturier, Alexis Desjardins

USAGE : python preprocess.py

Roule ce script UNE SEULE FOIS dans ton terminal.
Il génère tous les fichiers lourds dans le dossier data/ :
  - data/reseau_cyclable.geojson
  - data/graph_montreal_bike.graphml
  - data/accidents_classes.parquet
  - data/compteurs_agg.parquet
  - data/zones_rouges.parquet
  - data/top3_zones.parquet
  - data/top_od_pairs.parquet
  - data/trajets_routes.parquet
  - data/edges_routes.parquet
  - data/rues_candidates.parquet

Après ça, l'app Streamlit charge tout en ~2-3 secondes.
"""

import os
import pandas as pd
import geopandas as gpd
import numpy as np
import osmnx as ox
import networkx as nx
import requests
from shapely.geometry import LineString
import warnings
warnings.filterwarnings("ignore")

os.makedirs("data", exist_ok=True)

SEUIL_M      = 15       # Distance (m) pour classification accident sur/hors piste
BUFFER_M     = 15       # Buffer (m) pour jointure spatiale réseau officiel ↔ OSMnx
TOP_OD_PAIRS = 100      # Mettre 5 pour tester rapidement
MIN_RUE_M    = 800      # Longueur minimale (m) — rues assez longues pour valoir une construction
MIN_PASSAGES = 5

# Tags OSM élargis (fallback si jointure spatiale ne couvre pas l'edge)
PROTECTED_VALUES_OSM = {
    "track", "opposite_track", "buffered_lane", "protected_lane",
    "segregated", "crossing", "lane", "shared_lane", "opposite_lane",
}

URL_RESEAU = (
    "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536"
    "/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"
)

def log(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def ok(msg):
    print(f"  OK  {msg}")


# ════════════════════════════════════════════════════════
# ETAPE 1 — Réseau cyclable
# ════════════════════════════════════════════════════════
log("ETAPE 1/8 — Reseau cyclable de Montreal")

OUT = "data/reseau_cyclable.geojson"
if os.path.exists(OUT):
    ok(f"Deja present : {OUT} — skip")
    gdf_reseau = gpd.read_file(OUT)
else:
    print("  Telechargement depuis donnees.montreal.ca...")
    gdf_reseau = gpd.read_file(URL_RESEAU)
    gdf_reseau.to_file(OUT, driver="GeoJSON")
    ok(f"Sauvegarde : {OUT}  ({len(gdf_reseau)} troncons)")

# Afficher les types de voie disponibles (utile pour debug)
if "TYPE_VOIE_DESC" in gdf_reseau.columns:
    print("  Types de voie dans le réseau officiel :")
    for t in sorted(gdf_reseau["TYPE_VOIE_DESC"].dropna().unique()):
        print(f"    - {t}")


# ════════════════════════════════════════════════════════
# ETAPE 2 — Classification des accidents
# ════════════════════════════════════════════════════════
log("ETAPE 2/8 — Classification accidents velo 2021")

OUT = "data/accidents_classes.parquet"
if os.path.exists(OUT):
    ok(f"Deja present : {OUT} — skip")
else:
    print("  Chargement collisions_routieres (1).csv...")
    df_coll = pd.read_csv("collisions_routieres (1).csv", low_memory=False)
    df_2021 = df_coll[
        (df_coll["AN"] == 2021) &
        (df_coll["nb_bicyclette"] > 0) &
        df_coll["LOC_LAT"].notna() &
        df_coll["LOC_LONG"].notna()
    ].copy()

    gdf_acc = gpd.GeoDataFrame(
        df_2021,
        geometry=gpd.points_from_xy(df_2021["LOC_LONG"], df_2021["LOC_LAT"]),
        crs="EPSG:4326"
    )
    gdf_acc_m    = gdf_acc.to_crs("EPSG:32618")
    gdf_reseau_m = gdf_reseau.to_crs("EPSG:32618")

    print(f"  Jointure spatiale sur {len(gdf_acc_m)} accidents...")
    gdf_joined = gpd.sjoin_nearest(
        gdf_acc_m,
        gdf_reseau_m[["geometry", "TYPE_VOIE_DESC", "NOM_ARR_VILLE_DESC"]],
        how="left", distance_col="dist_piste_m"
    )
    gdf_joined["classification"] = gdf_joined["dist_piste_m"].apply(
        lambda d: "Sur piste" if d <= SEUIL_M else "Hors piste"
    )
    gdf_wgs = gdf_joined.to_crs("EPSG:4326")
    gdf_wgs["lon"] = gdf_wgs.geometry.x
    gdf_wgs["lat"] = gdf_wgs.geometry.y

    cols = ["AN", "LOC_LAT", "LOC_LONG", "lat", "lon", "GRAVITE",
            "nb_bicyclette", "nb_automobile_camion_leger",
            "classification", "dist_piste_m", "TYPE_VOIE_DESC", "NOM_ARR_VILLE_DESC"]
    if "nb_pieton" in gdf_wgs.columns:
        cols.append("nb_pieton")
    cols = [c for c in cols if c in gdf_wgs.columns]
    gdf_wgs[cols].to_parquet(OUT, index=False)
    ok(f"Sauvegarde : {OUT}  ({len(gdf_wgs)} accidents)")


# ════════════════════════════════════════════════════════
# ETAPE 3 — Compteurs cyclistes
# ════════════════════════════════════════════════════════
log("ETAPE 3/8 — Agregation des compteurs cyclistes")

OUT = "data/compteurs_agg.parquet"
if os.path.exists(OUT):
    ok(f"Deja present : {OUT} — skip")
else:
    df_cpt = pd.read_csv("Compteurs cyclistes permanents.csv", low_memory=False)
    df_cpt = df_cpt.dropna(subset=["latitude", "longitude", "vitesseMoyenne"])
    df_cpt = df_cpt[
        df_cpt["latitude"].between(45.4, 45.7) &
        df_cpt["longitude"].between(-74.0, -73.4) &
        (df_cpt["vitesseMoyenne"] > 0)
    ].copy()
    agg = {"vitesseMoyenne": "mean"}
    if "volume" in df_cpt.columns:
        agg["volume"] = "mean"
    df_agg = df_cpt.groupby(["latitude", "longitude"]).agg(agg).reset_index()
    df_agg.to_parquet(OUT, index=False)
    ok(f"Sauvegarde : {OUT}  ({len(df_agg)} compteurs)")


# ════════════════════════════════════════════════════════
# ETAPE 4 — Zones rouges + Top 3
# ════════════════════════════════════════════════════════
log("ETAPE 4/8 — Calcul des zones rouges")

OUT_ZONES = "data/zones_rouges.parquet"
OUT_TOP3  = "data/top3_zones.parquet"

if os.path.exists(OUT_ZONES) and os.path.exists(OUT_TOP3):
    ok("Deja presents — skip")
else:
    df_acc = pd.read_parquet("data/accidents_classes.parquet")
    acc_hors = df_acc[df_acc["classification"] == "Hors piste"].copy()
    acc_hors["lat_grid"] = (acc_hors["lat"] * 50).round() / 50
    acc_hors["lon_grid"] = (acc_hors["lon"] * 50).round() / 50
    zones = acc_hors.groupby(["lat_grid", "lon_grid"]).agg(
        nb_accidents=("GRAVITE", "count"),
        nb_graves=("GRAVITE", lambda x: x.isin(["Mortel", "Blessé grave"]).sum())
    ).reset_index()
    zones = zones[zones["nb_accidents"] >= 2].sort_values("nb_accidents", ascending=False)
    zones.to_parquet(OUT_ZONES, index=False)
    ok(f"Sauvegarde : {OUT_ZONES}  ({len(zones)} zones)")

    try:
        r1 = requests.get("https://gbfs.velobixi.com/gbfs/2-2/fr/station_information.json", timeout=10).json()
        r2 = requests.get("https://gbfs.velobixi.com/gbfs/2-2/fr/station_status.json",      timeout=10).json()
        stations = pd.DataFrame(r1["data"]["stations"])
        status   = pd.DataFrame(r2["data"]["stations"])
        bixi = stations.merge(status, on="station_id")
        bixi = bixi.rename(columns={"name": "station", "num_bikes_available": "velos_disponibles"})
        bixi = bixi[bixi["lat"].between(45.4, 45.7) & bixi["lon"].between(-74.0, -73.4)]
        bixi = bixi[["station", "lat", "lon", "velos_disponibles"]].dropna()
        ok("Donnees Bixi live recuperees")
    except Exception:
        bixi = pd.DataFrame(columns=["station", "lat", "lon", "velos_disponibles"])
        print("  Avertissement : API Bixi indisponible")

    if len(bixi) > 0:
        bixi_gdf  = gpd.GeoDataFrame(bixi, geometry=gpd.points_from_xy(bixi["lon"], bixi["lat"]), crs="EPSG:4326").to_crs("EPSG:32618")
        zones_gdf = gpd.GeoDataFrame(zones, geometry=gpd.points_from_xy(zones["lon_grid"], zones["lat_grid"]), crs="EPSG:4326").to_crs("EPSG:32618")
        bixi_gdf["passages"] = bixi_gdf["velos_disponibles"]
        merged = gpd.sjoin_nearest(zones_gdf, bixi_gdf[["geometry", "passages", "station"]], how="left", distance_col="dist_bixi_m")
        merged["passages"] = merged["passages"].fillna(0)
    else:
        merged = zones.copy()
        merged["passages"] = 0
        merged["station"]  = "—"

    max_p = max(merged["passages"].max(), 1)
    merged["score"] = (merged["nb_accidents"] * 2 + merged["nb_graves"] * 5 + (merged["passages"] / max_p * 3)).round(2)
    top3 = merged.sort_values("score", ascending=False).head(3).reset_index(drop=True)
    top3[["lat_grid", "lon_grid", "nb_accidents", "nb_graves", "passages", "score", "station"]].to_parquet(OUT_TOP3, index=False)
    ok(f"Sauvegarde : {OUT_TOP3}")


# ════════════════════════════════════════════════════════
# ETAPE 5 — Graphe OSMnx
# ════════════════════════════════════════════════════════
log("ETAPE 5/8 — Graphe OSMnx zone Bixi (reduite)")

# Zone centrée sur les stations Bixi — couvre ~98% des trajets
# Beaucoup plus léger : ~30MB au lieu de ~178MB pour toute l'île
BBOX_NORTH =  45.565
BBOX_SOUTH =  45.455
BBOX_EAST  = -73.510
BBOX_WEST  = -73.650

OUT = "data/graph_montreal_bike.graphml"

# Supprimer l'ancien graphe s'il est trop gros (>50MB = toute l'île)
if os.path.exists(OUT):
    size_mb = os.path.getsize(OUT) / (1024 * 1024)
    if size_mb > 50:
        print(f"  Ancien graphe trop grand ({size_mb:.0f} MB) — suppression et recréation...")
        os.remove(OUT)
    else:
        ok(f"Deja present : {OUT} ({size_mb:.0f} MB) — skip")
        G = ox.load_graphml(OUT)

if not os.path.exists(OUT):
    print(f"  Telechargement zone reduite...")
    ox_ver = tuple(int(x) for x in ox.__version__.split(".")[:2])
    try:
        if ox_ver >= (2, 0):
            G = ox.graph_from_bbox(
                bbox=(BBOX_WEST, BBOX_SOUTH, BBOX_EAST, BBOX_NORTH),
                network_type="bike", retain_all=False, simplify=True)
        else:
            G = ox.graph_from_bbox(
                north=BBOX_NORTH, south=BBOX_SOUTH,
                east=BBOX_EAST,   west=BBOX_WEST,
                network_type="bike", retain_all=False, simplify=True)
    except Exception as e:
        print(f"  bbox echoue ({e}), fallback...")
        G = ox.graph_from_place("Plateau-Mont-Royal, Montreal, Quebec, Canada",
                                network_type="bike", retain_all=False, simplify=True)
    ox.save_graphml(G, OUT)
    size_mb = os.path.getsize(OUT) / (1024 * 1024)
    ok(f"Sauvegarde : {OUT}  ({len(G.nodes)} noeuds, {len(G.edges)} edges, {size_mb:.0f} MB)")



# ════════════════════════════════════════════════════════
# ETAPE 6 — Top N paires O-D Bixi
# ════════════════════════════════════════════════════════
log(f"ETAPE 6/8 — Top {TOP_OD_PAIRS} paires O-D Bixi")

OUT = "data/top_od_pairs.parquet"
if os.path.exists(OUT):
    ok(f"Deja present : {OUT} — skip")
    od_df = pd.read_parquet(OUT)
else:
    df_bixi = pd.read_csv("bixi.csv")
    cols = df_bixi.columns.tolist()

    # Renommer les deux premières colonnes (départ / arrivée) si nécessaire
    rename = {}
    if cols[0] != "STARTSTATIONNAME":
        rename[cols[0]] = "STARTSTATIONNAME"
    if cols[1] != "ENDSTATIONNAME":
        rename[cols[1]] = "ENDSTATIONNAME"
    if rename:
        df_bixi = df_bixi.rename(columns=rename)
        print(f"  Colonnes renommées : {rename}")

    needed = [
        "STARTSTATIONNAME", "ENDSTATIONNAME",
        "STARTSTATIONLATITUDE", "STARTSTATIONLONGITUDE",
        "ENDSTATIONLATITUDE", "ENDSTATIONLONGITUDE",
        "occurrences",
    ]

    # Vérification des colonnes requises
    missing = [c for c in needed if c not in df_bixi.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans bixi.csv : {missing}\nColonnes disponibles : {df_bixi.columns.tolist()}")

    # Le CSV est déjà agrégé — tri direct sur occurrences
    df_bixi = df_bixi.dropna(subset=needed)
    df_bixi = df_bixi[df_bixi["STARTSTATIONNAME"] != df_bixi["ENDSTATIONNAME"]]
    od_df = (
        df_bixi
        .sort_values("occurrences", ascending=False)
        .head(TOP_OD_PAIRS)
        .reset_index(drop=True)
    )
    od_df.to_parquet(OUT, index=False)
    ok(f"Sauvegarde : {OUT}  ({len(od_df)} paires O-D)")
    print(f"  Top 3 paires : ")
    for _, r in od_df.head(3).iterrows():
        print(f"    {r['STARTSTATIONNAME'][:30]} → {r['ENDSTATIONNAME'][:30]} ({r['occurrences']} passages)")


# ════════════════════════════════════════════════════════
# ETAPE 7 — Routing OSMnx (version originale simple)
# ════════════════════════════════════════════════════════
log(f"ETAPE 7/8 — Routing OSMnx ({TOP_OD_PAIRS} trajets)")

OUT_TRAJETS = "data/trajets_routes.parquet"
OUT_EDGES   = "data/edges_routes.parquet"

if os.path.exists(OUT_TRAJETS) and os.path.exists(OUT_EDGES):
    ok("Deja presents — skip")
else:
    def is_protected(edge_data):
        hw = edge_data.get("highway", "")
        if isinstance(hw, list): hw = hw[0]
        if hw == "cycleway": return True
        for key in ["cycleway","cycleway:right","cycleway:left","cycleway:both"]:
            val = edge_data.get(key, "")
            if isinstance(val, list): val = val[0]
            if val in PROTECTED_VALUES_OSM: return True
        return False


    # Pénaliser les rues ordinaires pour forcer le routing sur les pistes
    # Une rue sans piste "compte" PENALTY fois plus longue pour Dijkstra
    PENALTY = 3.0
    print("  Application des poids de routing (pénalité rues ordinaires x3)...")
    for u, v, k, data in G.edges(data=True, keys=True):
        data["bike_length"] = data.get("length", 1) if is_protected(data) else data.get("length", 1) * PENALTY

    records_edges   = []
    records_trajets = []
    total  = len(od_df)
    errors = 0

    for idx, row in od_df.iterrows():
        print(f"  {idx+1}/{total} : {str(row['STARTSTATIONNAME'])[:28]} -> {str(row['ENDSTATIONNAME'])[:28]}   ", end="\r")
        try:
            orig = ox.distance.nearest_nodes(G, X=row["STARTSTATIONLONGITUDE"], Y=row["STARTSTATIONLATITUDE"])
            dest = ox.distance.nearest_nodes(G, X=row["ENDSTATIONLONGITUDE"],   Y=row["ENDSTATIONLATITUDE"])
            if orig == dest: continue

            path = nx.shortest_path(G, orig, dest, weight="bike_length")
            dist_total = dist_protegee = 0.0
            dist_total = dist_protegee = 0.0

            for u, v in zip(path[:-1], path[1:]):
                ed     = min(G[u][v].values(), key=lambda d: d.get("length", 9999))
                length = ed.get("length", 0)
                prot   = is_protected(ed)
                name = ed.get("name", None)
                if isinstance(name, list): name = name[0]
                if not name or str(name).strip() == "":
                    continue  # skip cet edge — pas de nom, on l'ignore
                name = str(name).strip()

                dist_total    += length
                dist_protegee += length if prot else 0

                if "geometry" in ed:
                    coords = list(ed["geometry"].coords)
                else:
                    nu = G.nodes[u]; nv = G.nodes[v]
                    coords = [(nu["x"], nu["y"]), (nv["x"], nv["y"])]

                records_edges.append({
                    "u": u, "v": v,
                    "nom_rue":     name,
                    "protege":     prot,
                    "length_m":    length,
                    "occurrences": row["occurrences"],
                    "depart":      row["STARTSTATIONNAME"],
                    "arrivee":     row["ENDSTATIONNAME"],
                    "coords_json": str(coords),
                })

            dist_eucl = ox.distance.great_circle(
                row["STARTSTATIONLATITUDE"], row["STARTSTATIONLONGITUDE"],
                row["ENDSTATIONLATITUDE"],   row["ENDSTATIONLONGITUDE"])
            pct = (dist_protegee / dist_total * 100) if dist_total > 0 else 0
            records_trajets.append({
                "Depart":                row["STARTSTATIONNAME"],
                "Arrivee":               row["ENDSTATIONNAME"],
                "Occurrences":           row["occurrences"],
                "Dist. reseau (m)":      round(dist_total),
                "Dist. euclidienne (m)": round(dist_eucl),
                "% sur piste":           round(pct, 1),
                "Ratio detour":          round(dist_total / max(dist_eucl, 1), 2),
            })
        except Exception:
            errors += 1
            continue

    print(f"\n  {len(records_trajets)} trajets routés, {errors} erreurs ignorées")

    # ── Reclassification spatiale sur les edges traversés seulement ──────────
    print("  Reclassification spatiale (GeoJSON officiel MTL)...")

    from shapely.geometry import LineString as SLS
    from shapely.strtree import STRtree
    from pyproj import Transformer
    import gc

    MAX_ANGLE_DEG = 35

    def get_bearing(geom):
        c = list(geom.coords)
        x0, y0 = c[0]; x1, y1 = c[-1]
        return np.degrees(np.arctan2(y1 - y0, x1 - x0)) % 180

    def angle_diff(a1, a2):
        d = abs(a1 - a2) % 180
        return min(d, 180 - d)

    tr = Transformer.from_crs("EPSG:4326", "EPSG:32188", always_xy=True)

    def proj_geom(geom):
        return SLS([tr.transform(x, y) for x, y in geom.coords])

    # Inclut les pistes protégées ET les bandes cyclables du réseau officiel MTL
    gdf_prot = gdf_reseau[
        (gdf_reseau["PROTEGE_4S"] == "Oui") |
        (gdf_reseau["TYPE_VOIE_DESC"].str.contains("Piste|Bande", case=False, na=False))
    ][["geometry"]].copy().reset_index(drop=True)

    def explode_to_lines(geom):
        if geom.geom_type == "LineString": return [geom]
        if geom.geom_type == "MultiLineString": return list(geom.geoms)
        return []

    simple_lines = []
    for g in gdf_prot.geometry:
        simple_lines.extend(explode_to_lines(g))

    prot_proj     = [proj_geom(g) for g in simple_lines]
    prot_bearings = [get_bearing(g) for g in prot_proj]
    prot_tree     = STRtree(prot_proj)

    spatial_cache = {}

    for rec in records_edges:
        key = (rec["u"], rec["v"])
        if key in spatial_cache:
            rec["protege"] = spatial_cache[key]
            continue

        if rec["protege"]:
            spatial_cache[key] = True
            continue

        raw_coords = rec["coords_json"]
        try:
            import ast
            coords = ast.literal_eval(raw_coords)
            edge_geom = proj_geom(SLS(coords))
        except Exception:
            spatial_cache[key] = False
            continue

        edge_bearing = get_bearing(edge_geom)
        nearby       = prot_tree.query(edge_geom.buffer(15))
        is_prot      = False

        for i in nearby:
            if edge_geom.distance(prot_proj[i]) <= 15 and \
               angle_diff(edge_bearing, prot_bearings[i]) <= MAX_ANGLE_DEG:
                is_prot = True
                break

        rec["protege"]       = is_prot
        spatial_cache[key]   = is_prot

    del prot_proj, prot_tree, spatial_cache, gdf_prot
    gc.collect()

    n_prot = sum(1 for r in records_edges if r["protege"])
    print(f"  Après reclassification : {n_prot}/{len(records_edges)} edges protégés")

    from collections import defaultdict
    stats = defaultdict(lambda: {"dt": 0.0, "dp": 0.0})
    for rec in records_edges:
        k = (rec["depart"], rec["arrivee"])
        stats[k]["dt"] += rec["length_m"]
        if rec["protege"]: stats[k]["dp"] += rec["length_m"]

    for t in records_trajets:
        k  = (t["Depart"], t["Arrivee"])
        dt = stats[k]["dt"]
        dp = stats[k]["dp"]
        t["% sur piste"] = round((dp / dt * 100) if dt > 0 else 0, 1)


    df_trajets = pd.DataFrame(records_trajets)
    df_edges   = pd.DataFrame(records_edges)

    df_trajets.to_parquet(OUT_TRAJETS, index=False)
    df_edges.to_parquet(OUT_EDGES, index=False)

    df_trajets.rename(columns={
        "Depart": "Départ", "Arrivee": "Arrivée",
        "Dist. reseau (m)": "Dist. réseau (m)",
        "Ratio detour": "Ratio détour",
    }).to_csv("page3_resultats_trajets.csv", index=False)

    ok(f"Sauvegarde : {OUT_TRAJETS}  ({len(df_trajets)} trajets)")
    ok(f"Sauvegarde : {OUT_EDGES}    ({len(df_edges)} edges)")

    if len(df_trajets) > 0:
        print(f"  % sur piste — moy: {df_trajets['% sur piste'].mean():.1f}%  med: {df_trajets['% sur piste'].median():.1f}%")

# ════════════════════════════════════════════════════════
# ETAPE 8 — Rues candidates
# ════════════════════════════════════════════════════════
log("ETAPE 8/8 — Analyse des rues candidates")

OUT = "data/rues_candidates.parquet"
if os.path.exists(OUT):
    ok(f"Deja present : {OUT} — skip")
else:
    df_edges = pd.read_parquet("data/edges_routes.parquet")
    hors = df_edges[
    ~df_edges["protege"] &
    df_edges["nom_rue"].notna() &
    (df_edges["nom_rue"] != "Rue inconnue")
].copy()
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
        (agg["longueur_totale_m"] >= 800) &
        (agg["passages_bixi"]     >= MIN_PASSAGES)
    ].copy()
    if len(agg) > 0:
        max_p = agg["passages_bixi"].max()
        max_l = agg["longueur_totale_m"].max()
        agg["score"] = (
            (agg["passages_bixi"]     / max_p * 0.6) +
            (agg["longueur_totale_m"] / max_l * 0.4)
        ).round(4) * 100
        # Garder top 10 dans le parquet (tableau page 3) — carte affichera top 3
        agg = agg.sort_values("score", ascending=False).head(10).reset_index(drop=True)
    agg.to_parquet(OUT, index=False)
    agg.to_csv("page3_rues_candidates.csv", index=False)
    ok(f"Sauvegarde : {OUT}  ({len(agg)} rues candidates)")
    if len(agg) > 0:
        print("  Top 3 rues candidates (carte) :")
        for _, r in agg.head(3).iterrows():
            print(f"    {r['nom_rue']:<35} score={r['score']:.1f}  passages={int(r['passages_bixi']):,}  longueur={r['longueur_totale_m']:.0f}m")


# ════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  PRE-TRAITEMENT TERMINE")
print("="*60)
print("\n  Fichiers generes dans data/ :\n")
for f in sorted(os.listdir("data")):
    size = os.path.getsize(f"data/{f}") / 1024
    print(f"    {f:<42} {size:>8.1f} KB")
print("\n  Lance maintenant :  streamlit run app.py\n")
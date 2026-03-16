import geopandas as gpd
import pandas as pd
import os

# --- CONFIGURATION ---
FICHIER_EXISTANT = "flux_bixi_estimes.geojson"
URL_RESEAU = "https://donnees.montreal.ca/dataset/5ea29f40-1b5b-4f34-85b3-7c67088ff536/resource/0dc6612a-be66-406b-b2d9-59c9e1c65ebf/download/reseau_cyclable.geojson"

# 🔧 CHANGE CETTE VALEUR POUR AJUSTER LE BLEU (En mètres)
# 2.0 = Très strict (Le bleu disparaît si pas pile dessus)
# 3.5 = Moyen (Recommandé)
# 6.0 = Large (Beaucoup de bleu)
NOUVEAU_BUFFER = 8 

print(f"🎨 Recalcul des couleurs avec une tolérance de {NOUVEAU_BUFFER} mètres...")

if not os.path.exists(FICHIER_EXISTANT):
    print("❌ Erreur : Tu dois avoir généré le fichier 'flux_bixi_estimes.geojson' au moins une fois (même moche) avec le gros script.")
    exit()

try:
    # 1. Chargement (C'est rapide, les trajets sont déjà là)
    print("   Chargement des trajets existants...")
    gdf_flux = gpd.read_file(FICHIER_EXISTANT)
    
    print("   Chargement du réseau officiel...")
    reseau_officiel = gpd.read_file(URL_RESEAU)

    # 2. Projection en mètres pour la précision
    flux_m = gdf_flux.to_crs(epsg=32188)
    reseau_m = reseau_officiel.to_crs(epsg=32188)

    # 3. Le recalcul magique (Rapide)
    print("   Application de la nouvelle précision...")
    buffer_piste = reseau_m.geometry.buffer(NOUVEAU_BUFFER).unary_union
    flux_m['sur_piste'] = flux_m.geometry.intersects(buffer_piste)

    # 4. Sauvegarde
    gdf_final = flux_m.to_crs(epsg=4326)
    gdf_final['couleur'] = gdf_final['sur_piste'].apply(lambda x: '#3498db' if x else '#FF0000')
    gdf_final['etat'] = gdf_final['sur_piste'].apply(lambda x: 'Sur Piste' if x else 'Hors Piste (Missing Link)')
    
    # On écrase l'ancien fichier
    gdf_final.to_file(FICHIER_EXISTANT, driver="GeoJSON")
    
    print("✅ TERMINÉ ! Relance ton site (streamlit run app.py) pour voir le changement.")

except Exception as e:
    print(f"❌ Erreur : {e}")
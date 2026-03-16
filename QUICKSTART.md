# 🚀 Guide de Démarrage Rapide - MobilityPro

## Installation Express (5 minutes)

### Option 1 : Avec vos données

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Placer vos fichiers de données dans le dossier
#    - bixi.csv
#    - comptage_velo_2025.csv
#    - collisions_routieres.csv
#    - flux_bixi_estimes.geojson (optionnel)

# 3. Lancer l'application
streamlit run dashboard_insane.py
```

### Option 2 : Mode Démonstration

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Générer des données de démonstration
python generer_donnees_demo.py

# 3. Lancer l'application
streamlit run dashboard_insane.py
```

## 🎯 Première Utilisation

1. **Ouvrir l'app** : `http://localhost:8501` s'ouvre automatiquement

2. **Explorer les pages** :
   - 🎯 Dashboard Exécutif → Vue d'ensemble
   - 🗺️ Réseau → Cartes interactives
   - 🚴 BIXI → Temps réel
   - 🤖 IA → Prédictions et recommandations
   - ⚠️ Sécurité → Analyse des accidents
   - 📈 Analytics → Statistiques avancées

3. **Activer le mode sombre** :
   - Sidebar → ☑️ Mode Sombre

4. **Filtrer les données** :
   - Sidebar → Sélectionner l'année

## 💡 Fonctionnalités Clés

### Dashboard Exécutif
- **KPIs en temps réel** : Vélos disponibles, accidents, réseau
- **Graphiques interactifs** : Évolution, tendances
- **Heatmap temporelle** : Accidents par jour/heure

### Réseau & Infrastructure
- **Carte du réseau** : Pistes, bandes, REV
- **Overlay accidents** : Visualisation des zones à risque
- **Filtres avancés** : Type d'infrastructure, gravité

### BIXI Temps Réel
- **Clustering K-Means** : Segmentation intelligente des stations
- **Taux d'occupation** : Monitoring en direct
- **Top/Bottom stations** : Identification des problèmes

### IA & Prédictions
- **Score de priorité** : Algorithme multi-critères
- **Matrice Impact/Faisabilité** : Aide à la décision
- **Recommandations** : Quick wins identifiés

### Analyse Sécurité
- **Sur/Hors piste** : Comparaison
- **Heatmap de densité** : Zones critiques
- **Analyse temporelle** : Patterns horaires/journaliers

### Analytics Avancés
- **Corrélations** : Matrices interactives
- **Séries temporelles** : Tendances avec MA
- **Statistiques** : Distributions, percentiles

## 🎨 Personnalisation

### Changer les couleurs
Éditer `config.json` :
```json
{
  "colors": {
    "primary": "#VOTRE_COULEUR"
  }
}
```

### Modifier les poids du scoring
Éditer `config.json` :
```json
{
  "ml": {
    "priority_score": {
      "volume_weight": 0.5,
      "length_weight": 0.3,
      "accidents_weight": 0.2
    }
  }
}
```

## 🐛 Résolution Problèmes

### "Module not found"
```bash
pip install --upgrade -r requirements.txt
```

### Les cartes ne s'affichent pas
- Vérifier connexion internet
- APIs externes requises

### Données manquantes
- Utiliser `python generer_donnees_demo.py`
- Ou placer vos fichiers CSV

### Performance lente
- Réduire `max_map_points` dans config.json
- Limiter la période analysée

## 📊 Structure des Données

### Format attendu

**bixi.csv**
```csv
STARTSTATIONNAME,ENDSTATIONNAME,STARTSTATIONLATITUDE,STARTSTATIONLONGITUDE,ENDSTATIONLATITUDE,ENDSTATIONLONGITUDE,occurrences
Métro Pie-IX,Desjardins,45.554,-73.551,45.551,-73.541,4660
```

**comptage_velo_2025.csv**
```csv
date,heure,id_compteur,nb_passages,longitude,latitude
2025-01-01,00:00:00,100054073,0,-73.591,45.561
```

**collisions_routieres.csv**
```csv
DT_ACCDN,LOC_LAT,LOC_LONG,NB_BICYCLETTE,GRAVITE
2024-01-15 14:30:00,45.52,-73.58,1,Léger
```

## 🚀 Prochaines Étapes

1. ✅ Explorer toutes les pages
2. ✅ Tester les filtres
3. ✅ Générer des insights
4. ✅ Exporter des visualisations (screenshots)
5. ✅ Personnaliser selon vos besoins

## 💬 Support

- 📖 Consulter README.md complet
- 🐛 Créer une issue sur GitHub
- 💡 Partager vos suggestions

---

**Bon Analytics ! 🚴📊**
# 🚴 MobilityPro Analytics - Dashboard INSANE

## 🚀 Fonctionnalités Principales

### 1️⃣ **Dashboard Exécutif**
- KPIs en temps réel avec design premium
- Graphiques interactifs Plotly
- Heatmap horaire des accidents
- Métriques de performance

### 2️⃣ **Réseau & Infrastructure**
- Carte interactive du réseau cyclable
- Overlay accidents et stations BIXI
- Statistiques par type d'infrastructure
- Filtres avancés

### 3️⃣ **BIXI Temps Réel**
- Données live des stations
- **Clustering intelligent avec K-Means**
- Analyse des taux d'occupation
- Top/Bottom stations

### 4️⃣ **IA & Prédictions**
- Scoring de priorité des segments
- **Matrice Impact vs Faisabilité**
- Recommandations intelligentes
- Identification des Quick Wins

### 5️⃣ **Analyse Sécurité**
- Accidents sur/hors piste
- Heatmap de densité
- Analyse temporelle (heure/jour/mois)
- Filtres de gravité

### 6️⃣ **Analytics Avancés**
- Statistiques descriptives
- Matrices de corrélation
- Séries temporelles avec moyenne mobile
- Analyses bivariées

## 🎨 Fonctionnalités Premium

- ✅ **Mode Sombre/Clair** - Switch dans la sidebar
- ✅ **CSS Ultra-Premium** - Design moderne et professionnel
- ✅ **Animations CSS** - Effets visuels fluides
- ✅ **Cards Interactives** - Hover effects
- ✅ **Gradient Backgrounds** - Interface élégante
- ✅ **Status Badges** - Indicateurs visuels
- ✅ **Responsive Design** - Adaptatif

## 📦 Installation

### Prérequis
```bash
python >= 3.8
```

### 1. Installer les dépendances

```bash
pip install streamlit pandas numpy geopandas folium plotly streamlit-folium scikit-learn requests
```

### 2. Structure des fichiers

```
projet/
│
├── dashboard_insane.py          # Dashboard principal
├── bixi.csv                     # Données trajets BIXI
├── comptage_velo_2025.csv       # Comptage vélo
├── collisions_routieres.csv     # Données accidents
├── flux_bixi_estimes.geojson    # Flux estimés (optionnel)
└── README.md                    # Ce fichier
```

### 3. Lancer l'application

```bash
streamlit run dashboard_insane.py
```

L'application s'ouvrira automatiquement dans votre navigateur à `http://localhost:8501`

## 📊 Sources de Données

### Requises
1. **Réseau Cyclable** - Chargé automatiquement depuis API Montréal
2. **BIXI Live** - Chargé automatiquement depuis API BIXI

### Optionnelles (améliore les fonctionnalités)
1. **bixi.csv** - Trajets historiques BIXI
2. **comptage_velo_2025.csv** - Données de comptage
3. **collisions_routieres.csv** - Accidents cyclistes
4. **flux_bixi_estimes.geojson** - Flux estimés pour priorisation

## 🎯 Guide d'Utilisation

### Navigation
Utilisez la **sidebar** pour naviguer entre les 6 pages principales :

1. **🎯 Dashboard Exécutif** - Vue d'ensemble stratégique
2. **🗺️ Réseau & Infrastructure** - Analyse du réseau
3. **🚴 BIXI Temps Réel** - Monitoring des stations
4. **🤖 IA & Prédictions** - Aide à la décision
5. **⚠️ Analyse Sécurité** - Accidents et zones à risque
6. **📈 Analytics Avancés** - Statistiques approfondies

### Filtres Globaux
- **Année** - Sélection de l'année d'analyse
- **Mode Sombre/Clair** - Toggle dans la sidebar

### Interactions
- **Hover** sur les graphiques pour voir les détails
- **Zoom/Pan** sur les cartes Folium
- **Clic** sur les markers pour les popups
- **Sliders** pour ajuster les paramètres

## 🔧 Personnalisation

### Modifier les Couleurs
Dans la fonction `inject_custom_css()`, changez :
```python
accent_color = "#005528"  # Vert de Montréal
```

### Ajouter des KPIs
Dans chaque page, utilisez le template :
```python
st.markdown("""
    <div class="metric-card">
        <div class="metric-label">📊 Label</div>
        <div class="metric-value">Valeur</div>
        <div class="metric-delta">Delta</div>
    </div>
""", unsafe_allow_html=True)
```

### Modifier le Clustering
Ajustez le nombre de clusters :
```python
n_clusters = st.slider("Nombre de clusters", 2, 10, 5)
```

## 📈 Algorithmes ML Utilisés

1. **K-Means Clustering** - Segmentation des stations BIXI
2. **StandardScaler** - Normalisation des features
3. **Score de Priorité** - Algorithme custom multi-critères

```python
SCORE_PRIORITE = VOLUME * 0.5 + (LONGUEUR/1000) * 0.3 + ACCIDENTS * 0.2
```

## 🐛 Troubleshooting

### Erreur: "Module not found"
```bash
pip install --upgrade [nom_module]
```

### Cartes ne s'affichent pas
Vérifiez votre connexion internet (API externe)

### Données manquantes
L'app fonctionne en mode dégradé si certains fichiers sont absents

### Performance lente
Réduisez le nombre de points sur les cartes avec le slider

## 🚀 Améliorations Futures

- [ ] Export PDF des rapports
- [ ] Prédictions ML avec LSTM
- [ ] API REST pour intégrations
- [ ] Dashboard temps réel avec WebSockets
- [ ] Analyse de sentiment Twitter
- [ ] Recommandations personnalisées par utilisateur

## 📝 Notes Techniques

- **Caching Streamlit** : Données mises en cache (TTL: 1h pour BIXI live)
- **Projections** : EPSG:4326 (WGS84) pour affichage, EPSG:32188 (MTM Zone 8) pour calculs
- **Performance** : Limite de 2000 points sur les cartes par défaut

## 💡 Cas d'Usage

1. **Urbanistes** - Planification d'infrastructures cyclables
2. **Décideurs** - Priorisation budgétaire
3. **Analystes** - Études de sécurité routière
4. **Chercheurs** - Analyse de mobilité urbaine

## 📞 Support

Pour questions ou suggestions : créez une issue sur GitHub

## 📜 Licence

MIT License - Libre d'utilisation et modification

---

**Développé avec ❤️ pour Montréal | 2026**
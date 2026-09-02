# ML Notes — Observations, Limites & Évolutions

> Document de travail data scientist. Conserve les décisions de modélisation,
> les biais identifiés et les pistes d'amélioration pour les itérations futures.

---

## 1. Contexte dataset — Olist Brazilian E-Commerce

| Propriété | Valeur |
|---|---|
| Type | Marketplace (non-contractuel) |
| Période | Oct 2016 – Août 2018 |
| Commandes | ~100k |
| Clients uniques | ~96k |
| Taux mono-acheteurs | ~90% |

**Implication centrale :** Olist est un marketplace, pas un service par abonnement.
L'absence de ré-achat est le comportement **normal**, pas une anomalie.
Tous les modèles comportementaux doivent intégrer cette réalité.

---

## 2. RFM

### 2.1 Implémentation actuelle

- Quantiles égaux (`pd.qcut`) sur chaque dimension R, F, M
- n_segments = 4 par défaut → scores [1..4] par dimension
- Segment final par seuil sur le score total + contrainte obligatoire sur r_score

```
Champions      → ratio ≥ 0.75 ET r_score ≥ n_segments - 1
Loyal Customer → ratio ≥ 0.55
At Risk        → ratio ≥ 0.35 OU r_score élevé (client récent mais faible valeur)
Lost           → reste
```

### 2.2 Problèmes identifiés

**Biais fréquence (F) :**
~90% des clients ont frequency=1. `pd.qcut` crée 4 bins d'effectifs égaux, mais
avec une distribution aussi dégénérée les 3 premiers bins correspondent tous à
frequency=1 avec des seuils artificiels. Le f_score ne discrimine pas bien.

**Champions à haute récence (corrigé) :**
Sans contrainte sur r_score, un client avec un seul achat élevé il y a 18 mois
pouvait atteindre le segment Champions. Corrigé en v1 en imposant r_score ≥ n-1.

**Pas de pondération des dimensions :**
R, F, M ont un poids égal. En pratique, selon le secteur, R est souvent
l'indicateur le plus prédictif de la valeur future.

### 2.3 Évolutions possibles

| Priorité | Évolution | Commentaire |
|---|---|---|
| Haute | Pondération R×F×M configurable | Ex: poids (0.4, 0.3, 0.3) selon contexte métier |
| Haute | Gestion distribution dégénérée de F | Binning log ou quantiles sur rank pour F |
| Moyenne | RFM pondéré par valeur produit | Tous les achats n'ont pas la même valeur relationnelle |
| Moyenne | Ajout dimension T (Tenure) → RFMT | Distinguer nouveaux clients vs clients historiques |
| Basse | Modèle probabiliste BG/NBD | Standard non-contractuel, prédit les achats futurs |

```python
# Évolution suggérée : pondération configurable
rfm["rfm_score"] = (
    weights["r"] * rfm["r_score"] +
    weights["f"] * rfm["f_score"] +
    weights["m"] * rfm["m_score"]
)
```

---

## 3. Churn

### 3.1 Implémentation actuelle

- Label engineered : `churned = 1` si `recency_days ≥ inactivity_threshold` (défaut 365j)
- Features : total_orders, total_revenue, avg_order_value, tenure_days, recency_days
- Modèle : RandomForest, `class_weight='balanced'`, train/test split 80/20
- Score : probabilité de la classe 1 (`predict_proba[:, 1]`)

### 3.2 Problèmes identifiés

**Labelling inadapté au marketplace (root cause) :**
Avec un seuil de 180j, ~71% des clients étaient labellisés "churned" — car sur un
marketplace, ne pas racheter dans les 6 mois est normal. Le modèle apprenait à
prédire "churn=1" pour presque tout le monde.
→ Corrigé : seuil passé à 365j.

**Overfitting train = test (corrigé) :**
Le modèle était entraîné et scoré sur le même jeu complet. Le RandomForest
mémorisait les exemples → tous les scores retournaient exactement 0.0 ou 1.0.
→ Corrigé : split 80/20 stratifié.

**Leakage potentiel :**
`recency_days` est directement corrélé au label (`churned = recency ≥ threshold`).
Le modèle apprend en partie une règle triviale déjà connue.
En production, recency_days ne devrait pas être une feature — ou le label doit
être défini indépendamment de la récence.

**Pas de validation temporelle :**
Le split actuel est aléatoire. Un split temporel (entraîner sur 2016-2017,
scorer sur 2018) serait plus réaliste et éviterait le data leakage temporel.

**Concept drift :**
Le modèle est ré-entraîné à chaque appel. En production, il faudrait un modèle
pré-entraîné sauvegardé et ré-entraîné périodiquement.

### 3.3 Évolutions possibles

| Priorité | Évolution | Commentaire |
|---|---|---|
| Haute | Split temporel (time-based CV) | `TimeSeriesSplit` ou coupure à date fixe |
| Haute | Supprimer recency_days des features | Évite le leakage label → feature |
| Haute | Modèle BG/NBD + Gamma-Gamma (CLV) | Standard académique pour churn non-contractuel |
| Moyenne | Persist du modèle entraîné (`.pkl`) | Évite le re-training à chaque requête (~10s) |
| Moyenne | SHAP values pour l'explicabilité | "Pourquoi ce client est-il à risque ?" |
| Basse | XGBoost ou LightGBM à la place de RF | Meilleures performances sur données tabulaires déséquilibrées |
| Basse | Score de propension à la rétention | Complémentaire au churn : qui peut-on sauver ? |

```python
# Évolution suggérée : split temporel
cutoff = customers["last_purchase"].quantile(0.8)
train_mask = customers["last_purchase"] <= cutoff
X_train = feature_df[train_mask]
y_train = labels[train_mask]
# scorer sur tout le dataset
clf.fit(X_train, y_train)
```

---

## 4. Segmentation KMeans

### 4.1 Implémentation actuelle

- Features : total_orders, total_revenue, avg_order_value
- StandardScaler avant fit
- n_clusters configurable [2..8], défaut 4
- Labels : "Segment 1..N" triés par revenue moyen décroissant

### 4.2 Problèmes identifiés

**Initialisation non déterministe :**
`n_init=10` et `random_state=42` assurent la reproductibilité, mais les labels
(Segment 1, 2, 3…) peuvent changer d'un run à l'autre si les données changent.

**Choix de K non automatique :**
L'utilisateur choisit n_clusters manuellement. Sans méthode Elbow ou Silhouette,
il peut choisir un K sous-optimal.

**Features limitées :**
Pas de dimension temporelle (tenure, recency). Deux clients avec le même revenue
mais des comportements temporels très différents se retrouvent dans le même cluster.

### 4.3 Évolutions possibles

| Priorité | Évolution | Commentaire |
|---|---|---|
| Haute | Auto-sélection K par score Silhouette | Tester K=2..8, retourner le K optimal |
| Moyenne | Ajouter recency_days et tenure_days aux features | Dimension temporelle manquante |
| Moyenne | UMAP + KMeans (si >50k clients) | Réduction dimensionnelle avant clustering |
| Basse | DBSCAN pour détecter les outliers | Identifier les clients "hors norme" |
| Basse | Nommer les clusters automatiquement via LLM | "High-value frequent buyers" plutôt que "Segment 1" |

---

## 5. CLV

### 5.1 Implémentation actuelle

Modèle historique simplifié :
```
CLV_12m = (total_orders / tenure_months) × avg_order_value × 12
```

### 5.2 Limites

- Ne prédit pas le futur — projette linéairement le passé
- Ignore la probabilité que le client achète encore (churn non intégré)
- Sur-estime les clients avec un seul achat récent (tenure_months = 1 → taux mensuel élevé)

### 5.3 Évolutions possibles

| Priorité | Évolution | Commentaire |
|---|---|---|
| Haute | CLV = P(alive) × valeur future | Intégrer le churn score : `clv = (1 - churn_score) × clv_historique` |
| Haute | Modèle Gamma-Gamma (lifetimes library) | Standard pour CLV non-contractuel |
| Moyenne | Segmentation CLV en déciles | "Top 10% de CLV = X% du revenue" |
| Basse | CLV par cohorte | Comparer les cohortes d'acquisition |

```python
# Évolution immédiate : pondérer par probabilité de survie
df["clv_adjusted"] = df["clv_estimated"] * (1 - df["churn_score"])
```

---

## 6. Architecture ML — Évolutions globales

### 6.1 Performance

Le modèle de churn est ré-entraîné à chaque appel agent (~10 secondes sur 96k clients).
En production :

```
Approche recommandée :
1. Pré-entraîner et sauvegarder models/churn_model.pkl au preprocessing
2. Le ChurnTool charge le pkl (< 100ms)
3. Ré-entraînement déclenché manuellement ou en cron
```

### 6.2 Validation

Aucune métrique de validation n'est actuellement exposée. Pour un portfolio sérieux,
ajouter dans le notebook `03_model_prototyping.ipynb` :

- Churn : AUC-ROC, precision/recall curve, matrice de confusion
- RFM : distribution des segments, stabilité sur sous-échantillons
- KMeans : courbe Elbow, score Silhouette par K
- CLV : MAE vs CLV réel sur holdout temporel

### 6.3 Drift monitoring (v3+)

Sur des données réelles en production :
- Monitorer la distribution des features (PSI — Population Stability Index)
- Alerter si le taux de churn prédit dérive de > 10% vs baseline
- Recalibrer le seuil d'inactivité si la fréquence d'achat du marché change

---

## 7. Décisions de conception documentées

| Décision | Choix retenu | Alternative écartée | Raison |
|---|---|---|---|
| Churn labelling | Règle seuil (recency ≥ 365j) | Survie (Kaplan-Meier) | Simplicité, pas de censure à gérer |
| Churn modèle | RandomForest | BG/NBD | RF plus rapide à implémenter, BG/NBD en v2 |
| RFM quantiles | `pd.qcut` égaux | Quantiles business-defined | Adaptatif aux données |
| CLV | Historique linéaire | Gamma-Gamma | Pas de dépendance externe, transparent |
| Train/test split | Aléatoire stratifié 80/20 | Temporel | Suffisant pour portfolio, temporel en v2 |
| Features churn | 5 features agrégées | Features par commande (séries temporelles) | Complexité maîtrisée, pas de LSTM nécessaire |

# Demo Script — 5 Reference Questions

These 5 questions are the minimum viable demo. Each should work correctly before the project is considered complete.

---

## Q1 — RFM Segmentation

**Input:** "Qui sont mes meilleurs clients ?"

**Expected tool call:** `compute_rfm`  
**Expected output:** Text summary with Champions/Loyal/At Risk/Lost counts + scatter chart.  
**Key assertion:** Champions segment identified, chart visible with 4 distinct colors.

---

## Q2 — Churn Risk

**Input:** "Quels clients risquent de partir dans les prochains mois ?"

**Expected tool call:** `predict_churn`  
**Expected output:** Count of high-risk customers + top 20 ranked list + horizontal bar chart.  
**Key assertion:** Churn scores between 0 and 1, chart renders.

---

## Q3 — Ad-hoc SQL

**Input:** "Montre-moi le revenu total par état brésilien, du plus grand au plus petit."

**Expected tool call:** `sql_query`  
**Expected SQL:** `SELECT customer_state, SUM(order_value) AS revenue FROM orders_enriched GROUP BY customer_state ORDER BY revenue DESC`  
**Expected output:** Table + bar chart with ~27 states.  
**Key assertion:** SP (São Paulo) should be the top state by revenue.

---

## Q4 — Multi-turn Memory

**Input (after Q1):** "Maintenant segmente ces clients par comportement, pas par RFM."

**Expected tool call:** `run_kmeans`  
**Expected output:** 4 behavioral clusters with revenue/order stats + scatter chart.  
**Key assertion:** Agent remembers context from Q1, uses KMeans (not RFM again).

---

## Q5 — Out-of-scope Graceful Degradation

**Input:** "Prédis le revenu du mois prochain."

**Expected tool call:** `list_capabilities`  
**Expected output:** Clear explanation that revenue forecasting is not available + suggestion of what the agent CAN do.  
**Key assertion:** No hallucinated numbers, no crash, polite redirection.

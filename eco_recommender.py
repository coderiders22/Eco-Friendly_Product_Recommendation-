"""EcoWise smart recommender.

Combines:
- Synonym / brand-to-category expansion (e.g. "macbook" -> "laptop notebook")
- Category-aware filtering (so a "macbook" search returns laptops, not cables)
- TF-IDF semantic similarity over product name + category + about_product
- Hybrid ranking using semantic score, eco_score, and user rating
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Maps user search terms to expanded category-relevant keywords.
# These help route brand / model queries to the correct product family.
QUERY_EXPANSIONS: dict[str, str] = {
    # Laptops
    "macbook": "laptop notebook computer apple",
    "mac": "laptop notebook computer apple",
    "thinkpad": "laptop notebook computer lenovo",
    "ideapad": "laptop notebook computer lenovo",
    "vivobook": "laptop notebook computer asus",
    "zenbook": "laptop notebook computer asus",
    "inspiron": "laptop notebook computer dell",
    "pavilion": "laptop notebook computer hp",
    "laptop": "laptop notebook computer",
    "notebook": "laptop notebook computer",
    # Phones
    "iphone": "smartphone mobile phone apple",
    "samsung phone": "smartphone mobile phone samsung galaxy",
    "galaxy": "smartphone mobile phone samsung",
    "redmi": "smartphone mobile phone xiaomi",
    "oneplus": "smartphone mobile phone oneplus",
    "pixel": "smartphone mobile phone google",
    "phone": "smartphone mobile phone",
    "mobile": "smartphone mobile phone",
    # Audio
    "airpods": "earbuds earphones headphones wireless apple",
    "earphones": "earphones earbuds in-ear headphones",
    "earbuds": "earbuds earphones in-ear headphones",
    "headphone": "headphones over-ear on-ear",
    "headphones": "headphones over-ear on-ear",
    "speaker": "speaker bluetooth audio sound",
    # TV
    "tv": "television smart tv smarttelevision",
    "television": "television smart tv smarttelevision",
    "smart tv": "television smart tv smarttelevision",
    # Watch
    "smartwatch": "smartwatch watch wearable",
    "watch": "smartwatch watch wearable",
    "applewatch": "smartwatch watch wearable apple",
    # Cables / chargers
    "charger": "charger adapter wallcharger",
    "adapter": "charger adapter wallcharger",
    "cable": "cable usb wire cord",
    "usb": "usb cable cord",
    "hdmi": "hdmi cable",
    # Kitchen
    "mixer": "mixer grinder mixergrinder",
    "grinder": "mixer grinder mixergrinder",
    "kettle": "electric kettle",
    "iron": "iron dryiron steamiron",
    "blender": "blender handblender",
    "purifier": "water purifier filter",
    "heater": "heater electricheater roomheater fanheater",
    # Computer accessories
    "mouse": "mouse mice computer",
    "keyboard": "keyboard computer",
    "monitor": "monitor display screen",
    "printer": "printer printing",
    "router": "router wifi network",
}


def _expand_query(query: str) -> str:
    """Expand the query with synonyms / category hints for better matching."""
    q = query.lower().strip()
    expanded_terms = [q]
    for key, expansion in QUERY_EXPANSIONS.items():
        if key in q:
            expanded_terms.append(expansion)
    return " ".join(expanded_terms)


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[\s/\-_,&|]+", text.lower()) if t]


class EcoRecommender:
    def __init__(self, data_path: str = "amazon_final_eco_scored.csv") -> None:
        df = pd.read_csv(data_path).drop_duplicates(subset=["product_id"]).reset_index(drop=True)

        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0)
        df["eco_score"] = pd.to_numeric(df["eco_score"], errors="coerce").fillna(0)

        df["product_name"] = df["product_name"].fillna("")
        df["category"] = df["category"].fillna("")
        df["about_product"] = df.get("about_product", "").fillna("")

        # Pre-compute helpers
        df["leaf_category"] = df["category"].apply(
            lambda c: c.split("|")[-1] if isinstance(c, str) and c else "General"
        )
        df["top_category"] = df["category"].apply(
            lambda c: c.split("|")[0] if isinstance(c, str) and c else "General"
        )
        df["category_words"] = df["category"].str.replace("|", " ", regex=False)

        # Rich TF-IDF text: name (weighted), category (weighted), about
        df["features"] = (
            (df["product_name"] + " ") * 3
            + (df["category_words"] + " ") * 2
            + df["about_product"]
        ).str.lower()

        self.df = df
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=20000,
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(df["features"])

        # Pre-compute lowercase columns to speed up filtering
        self._name_lower = df["product_name"].str.lower()
        self._cat_lower = df["category_words"].str.lower()
        self._about_lower = df["about_product"].str.lower()

    # ------------------------------------------------------------------
    # Search / Recommend
    # ------------------------------------------------------------------
    def recommend(
        self,
        query: str,
        top_n: int = 5,
        sort_by: str = "balanced",
        category: Optional[str] = None,
    ) -> pd.DataFrame | str:
        """Return the top_n most relevant + eco-friendly products for a query.

        sort_by:
            - "balanced": hybrid score (relevance + eco + rating)
            - "eco": eco_score first
            - "rating": rating first
        """
        if not query or not str(query).strip():
            return "Please enter a search term."

        original = str(query).strip().lower()
        expanded = _expand_query(original)
        tokens = _tokenize(expanded)

        # Vectorize the query and compute semantic similarity
        q_vec = self.vectorizer.transform([expanded])
        sim = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        # Token-overlap score (boosts exact keyword presence in name/category)
        token_score = np.zeros(len(self.df))
        for t in set(tokens):
            if len(t) < 2:
                continue
            in_name = self._name_lower.str.contains(t, na=False, regex=False).to_numpy()
            in_cat = self._cat_lower.str.contains(t, na=False, regex=False).to_numpy()
            in_about = self._about_lower.str.contains(t, na=False, regex=False).to_numpy()
            token_score += in_name.astype(float) * 1.2
            token_score += in_cat.astype(float) * 1.0
            token_score += in_about.astype(float) * 0.4

        # Normalize token_score 0..1
        if token_score.max() > 0:
            token_score = token_score / token_score.max()

        # Combined relevance: semantic + lexical
        relevance = 0.6 * sim + 0.4 * token_score

        # Keep only candidates with a meaningful relevance score
        candidate_mask = relevance > 0.05
        if not candidate_mask.any():
            return "No matching products found. Try a different keyword."

        results = self.df.loc[candidate_mask].copy()
        results["relevance"] = relevance[candidate_mask]

        # Category filter (optional, exact leaf or top-level match)
        if category and category != "All":
            mask = (results["leaf_category"] == category) | (results["top_category"] == category)
            if mask.any():
                results = results[mask]

        # Auto category routing: if the query semantically points to one
        # primary product family, restrict results to that family so a
        # search like "iphone" returns Smartphones, not phone accessories.
        if not category or category == "All":
            primary = self._infer_primary_category(original, expanded)
            if primary is not None:
                focused = results[results["leaf_category"] == primary]
                if len(focused) >= min(top_n, 3):
                    results = focused
            else:
                top_pool = results.sort_values("relevance", ascending=False).head(25)
                cat_counts = top_pool["leaf_category"].value_counts()
                if len(cat_counts) and cat_counts.iloc[0] >= max(3, int(0.4 * len(top_pool))):
                    dominant = cat_counts.index[0]
                    focused = results[results["leaf_category"] == dominant]
                    if len(focused) >= top_n:
                        results = focused

        # Hybrid scoring
        rating_norm = (results["rating"] / 5.0) * 100
        results["hybrid_score"] = (
            results["relevance"] * 100 * 0.45
            + results["eco_score"] * 0.35
            + rating_norm * 0.20
        )

        if sort_by == "eco":
            results = results.sort_values(by=["eco_score", "rating", "hybrid_score"], ascending=False)
        elif sort_by == "rating":
            results = results.sort_values(by=["rating", "eco_score", "hybrid_score"], ascending=False)
        else:
            results = results.sort_values(by=["hybrid_score", "eco_score"], ascending=False)

        cols = [
            "product_id",
            "product_name",
            "category",
            "leaf_category",
            "rating",
            "rating_count",
            "eco_score",
            "discounted_price",
            "actual_price",
            "discount_percentage",
            "img_link",
            "product_link",
            "hybrid_score",
            "relevance",
        ]
        cols = [c for c in cols if c in results.columns]
        return results[cols].head(top_n).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Primary category routing
    # ------------------------------------------------------------------
    # Maps query keywords to a target leaf category in the dataset.
    PRIMARY_CATEGORY_MAP: dict[str, str] = {
        "iphone": "Smartphones",
        "smartphone": "Smartphones",
        "mobile phone": "Smartphones",
        "android phone": "Smartphones",
        "samsung phone": "Smartphones",
        "redmi": "Smartphones",
        "oneplus": "Smartphones",
        "pixel": "Smartphones",
        "galaxy": "Smartphones",
        "macbook": "Lapdesks",
        "laptop stand": "NotebookComputerStands",
        "notebook": "Lapdesks",
        "smartwatch": "SmartWatches",
        "smart watch": "SmartWatches",
        "applewatch": "SmartWatches",
        "fitness band": "SmartWatches",
        "smart tv": "SmartTelevisions",
        "television": "SmartTelevisions",
        "tv": "SmartTelevisions",
        "earbud": "In-Ear",
        "earphone": "In-Ear",
        "airpod": "In-Ear",
        "kettle": "ElectricKettles",
        "mixer": "MixerGrinders",
        "grinder": "MixerGrinders",
        "iron": "DryIrons",
        "steam iron": "SteamIrons",
        "blender": "HandBlenders",
        "purifier": "WaterFilters&Purifiers",
        "fan heater": "FanHeaters",
        "room heater": "ElectricHeaters",
        "water heater": "InstantWaterHeaters",
        "lint shaver": "LintShavers",
        "remote": "RemoteControls",
        "wall charger": "WallChargers",
        "usb cable": "USBCables",
        "hdmi": "HDMICables",
        "mouse": "Mice",
        "keyboard": "Keyboards",
        "screen protector": "ScreenProtectors",
        "laundry basket": "LaundryBaskets",
    }

    def _infer_primary_category(self, original: str, expanded: str) -> Optional[str]:
        text = f"{original} {expanded}".lower()
        # Longest key first to prefer more specific matches.
        for key in sorted(self.PRIMARY_CATEGORY_MAP, key=len, reverse=True):
            if key in text:
                cat = self.PRIMARY_CATEGORY_MAP[key]
                if cat in self.df["leaf_category"].values:
                    return cat
        return None

    # ------------------------------------------------------------------
    # Similar products (used for "you might also like")
    # ------------------------------------------------------------------
    def get_similar_products(
        self,
        product_id: str,
        top_n: int = 5,
        weight_sim: float = 0.25,
        weight_eco: float = 0.55,
        weight_rating: float = 0.20,
    ) -> pd.DataFrame | str:
        if product_id not in self.df["product_id"].values:
            return "Product not found."

        idx = self.df.index[self.df["product_id"] == product_id].tolist()[0]
        target_category = self.df.iloc[idx]["category"]

        sim = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        similar = self.df.copy()
        similar["similarity"] = sim
        similar = similar[
            (similar["product_id"] != product_id) & (similar["category"] == target_category)
        ]
        similar = similar[similar["similarity"] > 0.1]
        if similar.empty:
            return "No similar products found."

        similar["rating_norm"] = (similar["rating"] / 5.0) * 100
        similar["hybrid_score"] = (
            (similar["similarity"] * 100) * weight_sim
            + similar["eco_score"] * weight_eco
            + similar["rating_norm"] * weight_rating
        )
        similar = similar.sort_values(by="hybrid_score", ascending=False)
        cols = [
            "product_id",
            "product_name",
            "leaf_category",
            "rating",
            "eco_score",
            "discounted_price",
            "img_link",
            "product_link",
            "hybrid_score",
        ]
        cols = [c for c in cols if c in similar.columns]
        return similar[cols].head(top_n).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Helpers for UI
    # ------------------------------------------------------------------
    def list_categories(self) -> list[str]:
        return ["All"] + sorted(self.df["leaf_category"].dropna().unique().tolist())

    def trending(self, top_n: int = 6) -> pd.DataFrame:
        """Return high eco-score + high rating products to feature on the homepage."""
        d = self.df.copy()
        d["score"] = d["eco_score"] * 0.6 + (d["rating"] / 5.0) * 100 * 0.4
        d = d.sort_values(["score", "rating"], ascending=False)
        cols = [
            "product_id",
            "product_name",
            "leaf_category",
            "rating",
            "eco_score",
            "discounted_price",
            "img_link",
            "product_link",
        ]
        cols = [c for c in cols if c in d.columns]
        return d[cols].head(top_n).reset_index(drop=True)


if __name__ == "__main__":
    r = EcoRecommender()
    for q in ["macbook", "iphone", "earbuds", "smart tv", "kettle"]:
        out = r.recommend(q, top_n=5)
        print("\n===", q, "===")
        if isinstance(out, str):
            print(out)
        else:
            for _, row in out.iterrows():
                print(f"- [{row['leaf_category']}] {row['product_name'][:80]} | eco={row['eco_score']} rating={row['rating']}")

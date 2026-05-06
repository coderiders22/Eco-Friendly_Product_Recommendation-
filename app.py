"""EcoWise Flask web app."""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from eco_recommender import EcoRecommender

app = Flask(__name__)
recommender = EcoRecommender()


def _format_category(category_value: str) -> str:
    if not isinstance(category_value, str) or not category_value:
        return "General"
    parts = [p.strip() for p in category_value.split("|") if p.strip()]
    return parts[-1] if parts else "General"


import re
from urllib.parse import quote_plus

_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "your", "you",
    "are", "all", "any", "use", "one", "two", "new", "set", "pack",
    "size", "color", "model", "series", "edition", "version", "type",
    "inch", "inches", "cm", "mm", "ml", "ltr", "litre", "kg", "watt", "w",
    "rs", "in", "of", "by", "to", "a", "an", "is", "it", "on", "or",
}


def _keywords_from_product(name: str, category: str, max_words: int = 4) -> str:
    """Extract a short, image-search-friendly keyword string from a product."""
    leaf = ""
    if isinstance(category, str) and category:
        leaf = category.split("|")[-1]
        leaf = re.sub(r"([a-z])([A-Z])", r"\1 \2", leaf)
    text = f"{leaf} {name}".lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = []
    seen = set()
    for w in text.split():
        if len(w) < 3 or w in _STOPWORDS or w.isdigit() or w in seen:
            continue
        seen.add(w)
        words.append(w)
        if len(words) >= max_words:
            break
    if not words:
        words = ["product"]
    return " ".join(words)


def _fallback_image(name: str, category: str) -> str:
    """Generate an online fallback image URL based on product keywords.

    Uses Unsplash's source endpoint which returns a relevant free image
    for any keyword query — no API key required.
    """
    keywords = _keywords_from_product(name, category)
    return f"https://source.unsplash.com/600x600/?{quote_plus(keywords)}"


def _eco_label(score: float) -> str:
    if score >= 70:
        return "A+"
    if score >= 50:
        return "A"
    if score >= 30:
        return "B"
    if score >= 15:
        return "C"
    return "D"


def _serialize(rows) -> list[dict]:
    items = []
    for row in rows.to_dict(orient="records"):
        eco = float(row.get("eco_score", 0) or 0)
        rating = float(row.get("rating", 0) or 0)
        name = row.get("product_name", "")
        category_raw = row.get("category", row.get("leaf_category", ""))
        img_link = row.get("img_link") or ""
        fallback = _fallback_image(name, category_raw)
        items.append(
            {
                "product_id": row.get("product_id"),
                "product_name": name,
                "category": _format_category(category_raw),
                "rating": round(rating, 1),
                "rating_count": row.get("rating_count", ""),
                "eco_score": round(eco, 1),
                "eco_label": _eco_label(eco),
                "discounted_price": row.get("discounted_price", "N/A"),
                "actual_price": row.get("actual_price", ""),
                "discount_percentage": row.get("discount_percentage", ""),
                "img_link": img_link or fallback,
                "fallback_img": fallback,
                "product_link": row.get("product_link") or "",
            }
        )
    return items


@app.route("/", methods=["GET"])
def home():
    trending = _serialize(recommender.trending(top_n=6))
    categories = recommender.list_categories()
    return render_template(
        "index.html",
        trending=trending,
        categories=categories,
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        sort_by = request.form.get("sort", "balanced")
        category = request.form.get("category", "All")
    else:
        query = request.args.get("q", "").strip()
        sort_by = request.args.get("sort", "balanced")
        category = request.args.get("category", "All")

    recommendations: list[dict] = []
    message: str | None = None

    if not query:
        message = "Enter a keyword to start searching."
    else:
        results = recommender.recommend(
            query=query, top_n=5, sort_by=sort_by, category=category
        )
        if isinstance(results, str):
            message = results
        else:
            recommendations = _serialize(results)
            if not recommendations:
                message = "No matching products found."

    categories = recommender.list_categories()
    return render_template(
        "search.html",
        query=query,
        sort_by=sort_by,
        category=category,
        categories=categories,
        recommendations=recommendations,
        message=message,
    )


@app.route("/product/<product_id>")
def product(product_id: str):
    df = recommender.df[recommender.df["product_id"] == product_id]
    if df.empty:
        return render_template("search.html", message="Product not found.", recommendations=[],
                               categories=recommender.list_categories(), query="", sort_by="balanced", category="All")

    row = df.iloc[0].to_dict()
    eco = float(row.get("eco_score", 0) or 0)
    name = row.get("product_name", "")
    category_raw = row.get("category", "")
    img_link = row.get("img_link") or ""
    fallback = _fallback_image(name, category_raw)
    product_data = {
        "product_id": row.get("product_id"),
        "product_name": name,
        "category": _format_category(category_raw),
        "rating": round(float(row.get("rating", 0) or 0), 1),
        "rating_count": row.get("rating_count", ""),
        "eco_score": round(eco, 1),
        "eco_label": _eco_label(eco),
        "discounted_price": row.get("discounted_price", "N/A"),
        "actual_price": row.get("actual_price", ""),
        "discount_percentage": row.get("discount_percentage", ""),
        "about_product": row.get("about_product", ""),
        "img_link": img_link or fallback,
        "fallback_img": fallback,
        "product_link": row.get("product_link") or "",
    }

    similar_raw = recommender.get_similar_products(product_id, top_n=5)
    similar = _serialize(similar_raw) if not isinstance(similar_raw, str) else []
    return render_template(
        "product.html",
        product=product_data,
        similar=similar,
        categories=recommender.list_categories(),
    )


@app.route("/api/suggest")
def api_suggest():
    """Lightweight autocomplete suggestions."""
    q = request.args.get("q", "").strip().lower()
    if not q or len(q) < 2:
        return jsonify([])
    df = recommender.df
    name_hits = df[df["product_name"].str.lower().str.contains(q, na=False, regex=False)]
    suggestions = (
        name_hits["product_name"].head(6).tolist()
        + sorted({c for c in df["leaf_category"].unique() if q in c.lower()})[:4]
    )
    return jsonify(suggestions[:8])


@app.context_processor
def inject_globals():
    return {"site_name": "EcoWise", "tagline": "Smarter shopping. Greener planet."}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5051)

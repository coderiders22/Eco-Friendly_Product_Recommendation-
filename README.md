# EcoWise: AI-Powered Eco-Friendly Product Recommendations

> Smarter shopping. Greener planet.
> Search any product (for example *macbook*, *phone*, *kettle*) and get the top 5 sustainable picks, ranked by a hybrid score that blends search relevance, eco-score, and real user ratings.

EcoWise is a full-stack web application built on a TF-IDF + synonym-aware NLP recommender, served by a polished, light-themed Flask UI with a first-time user guide, autocomplete, image fallbacks, and category-aware filtering.

---

## Highlights

- Smart NLP recommender: TF-IDF (1- and 2-grams) on product name + category + description, plus synonym/brand expansion (for example `iphone` goes to Smartphones).
- Intent routing: searches like *macbook* land on Lapdesks, *phone* on Smartphones, *kettle* on ElectricKettles.
- Hybrid scoring: `relevance x 0.45 + eco_score x 0.35 + rating x 0.20`.
- Light, eco-themed UI with green/teal palette, modern typography, fully responsive.
- First-time user guide: a 4-step modal that auto-opens on the first visit and can be reopened anytime via a floating help button.
- Autocomplete API with live suggestions as the user types.
- Multi-page platform: Home, Search, Product detail, Similar recommendations.
- Image fallback chain: dataset image, then online keyword image (Unsplash), then a branded SVG fallback.
- One-click deploy to Vercel.

---

## Project Structure

```
.
|-- app.py                          # Flask routes, serializers, image fallbacks, API
|-- eco_recommender.py              # Smart NLP recommender (TF-IDF + hybrid scoring)
|-- amazon_final_eco_scored.csv     # ~1,350 products with eco_score column
|-- requirements.txt                # Pinned Python dependencies
|-- vercel.json                     # Vercel serverless config
|-- .vercelignore                   # Files excluded from deployment bundle
|-- .gitignore
|
|-- templates/                      # Jinja2 templates
|   |-- base.html                   # Shared layout: navbar, guide modal, footer
|   |-- index.html                  # Landing page (hero, trending, how-it-works, about, developers)
|   |-- search.html                 # Search results with filters
|   |-- product.html                # Product detail + similar items
|   `-- _card.html                  # Reusable product card partial
|
`-- static/
    |-- style.css                   # Light eco theme, responsive grid, animations
    |-- app.js                      # Autocomplete + first-time guide controller
    `-- brand-fallback.svg          # Branded image used when all image sources fail
```

---

## How the Recommendation Engine Works

### 1. Data preparation (`EcoRecommender.__init__`)

- Loads `amazon_final_eco_scored.csv` and drops duplicate `product_id`s.
- Cleans `rating` and `eco_score` to numeric.
- Pre-computes:
  - `leaf_category`: last node of the `|`-separated category path (for example `Electronics|Mobiles|Smartphones` becomes `Smartphones`).
  - A `features` text column equal to `product_name x 3 + category_words x 2 + about_product`.
- Builds a TF-IDF matrix on `features` with:
  - `ngram_range=(1, 2)` for phrases.
  - `sublinear_tf=True` for length normalization.
  - English stopwords removed.

### 2. Query processing (`recommend(query)`)

```
user query: "macbook"
   |
   v
expand into "macbook laptop notebook computer apple"
   |
   v
TF-IDF cosine similarity   +   token-overlap score
   |                              (boosts exact word match in name/category)
   v
relevance = 0.6 x semantic + 0.4 x lexical
   |
   v
infer primary category    -->    "Lapdesks"
   |                              (hard map for known brands/keywords)
   v
filter to that category
   |
   v
hybrid score = 0.45 * relevance * 100 + 0.35 * eco_score + 0.20 * rating * 20
   |
   v
sort and return top 5
```

### 3. Synonym and brand expansion

`QUERY_EXPANSIONS` and `PRIMARY_CATEGORY_MAP` in `eco_recommender.py` route brand and model queries to the right product family:

| User search | Expanded keywords | Routed category |
|---|---|---|
| `macbook` | laptop notebook computer apple | Lapdesks |
| `iphone` / `phone` | smartphone mobile phone | Smartphones |
| `airpods` | earbuds earphones in-ear | In-Ear |
| `smart tv` | television smart tv | SmartTelevisions |
| `kettle` | electric kettle | ElectricKettles |

### 4. Sort modes

The user can choose:
- Balanced (default): hybrid score
- Most eco-friendly: eco_score first
- Top rated: rating first

### 5. Similar products (product detail page)

`get_similar_products(product_id)`:
- Cosine similarity restricted to the same category.
- Hybrid weighting: `0.25 x similarity + 0.55 x eco + 0.20 x rating`.

---

## Web Application Routes (`app.py`)

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Landing page with hero, trending picks, how-it-works, about, developers |
| `/search` | GET / POST | Search page with category and sort filters; renders top 5 results |
| `/product/<product_id>` | GET | Full product detail and similar products |
| `/api/suggest?q=...` | GET | Autocomplete suggestions used by the search bar |

### Helpers in `app.py`

- `_format_category`: turns `Electronics|Mobiles|Smartphones` into `Smartphones`.
- `_eco_label(score)`: converts an eco-score (0 to 100) into a letter grade A+, A, B, C, or D shown as a corner badge on every card.
- `_keywords_from_product`: extracts a short, relevant keyword string from a product (used for the online image fallback).
- `_fallback_image(name, category)`: builds an Unsplash URL for a relevant photo when the dataset image is missing.
- `_serialize(rows)`: uniform JSON-friendly product objects for templates.

### Image fallback chain

```
1. dataset img_link
        v (404 or load error)
2. Unsplash keyword image (built from category + name)
        v (also fails)
3. /static/brand-fallback.svg     (branded EcoWise leaf icon)
```

Implemented with a small `onerror` handler in `_card.html` and `product.html`.

---

## Frontend (Templates and Assets)

### Templates (`templates/`)

- `base.html`: Shared shell. Includes:
  - Sticky navbar with brand mark, nav, and CTA.
  - First-time user guide modal with 4 steps and dot indicator (auto-opens on first visit; persistent in `localStorage`).
  - Floating help button to reopen the guide anytime.
  - Footer with links and newsletter form.
- `index.html`: Hero with gradient headline, animated floating stat cards, popular search chips, trending grid, "How it works" cards, About section, Developers section.
- `search.html`: Search hero with category and sort dropdowns, result grid, friendly empty/error states.
- `product.html`: Large product hero, eco/rating/price metrics, store link, "About this product" excerpt, similar products grid.
- `_card.html`: Reusable card with eco-grade badge, image with fallback chain, metrics, action buttons.

### Styles and Scripts (`static/`)

- `style.css`: Light eco theme.
  - Color tokens: `--eco`, `--eco-2`, `--teal`, `--lime`, plus surface and border tokens.
  - Card hover lifts, gradient buttons, eco-badge color scale.
  - Fully responsive grids using `auto-fit minmax(240px, 1fr)`.
  - Dedicated rules for the guide modal and floating help button.
- `app.js`: Two self-contained modules.
  1. Autocomplete: debounced fetch to `/api/suggest`, keyboard navigation, click-to-fill.
  2. Guide controller: open/close, step navigation, dot indicators, ESC and arrow keys, `localStorage` flag (`ecowise_onboarded_v1`).
- `brand-fallback.svg`: A branded EcoWise leaf icon on a soft green background, used as the final image fallback.

---

## Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python3 app.py

# 3. Open in browser
http://127.0.0.1:5051
```

> Why port 5051? On macOS, port 5000 is taken by AirPlay Receiver. Change in `app.py` if you prefer.

### Test the recommender directly (no web server)

```bash
python3 eco_recommender.py
```

You will see top-5 recommendations printed for sample queries: `macbook`, `iphone`, `earbuds`, `smart tv`, `kettle`.

---

## Deploy to Vercel

The repo is preconfigured.

### Option A: Vercel dashboard (easiest)

1. Push this repo to GitHub.
2. Go to https://vercel.com/new
3. Import your GitHub repo.
4. Click Deploy (no environment variables needed).
5. You get a live URL like `https://eco-wise.vercel.app`.

### Option B: Vercel CLI

```bash
npm install -g vercel
vercel login
vercel             # preview deploy
vercel --prod      # production deploy
```

### `vercel.json`: what it does

```json
{
    "version": 2,
    "builds": [
        {
            "src": "app.py",
            "use": "@vercel/python",
            "config": { "maxLambdaSize": "50mb", "includeFiles": "**" }
        }
    ],
    "routes": [
        { "src": "/(.*)", "dest": "app.py" }
    ]
}
```

- `includeFiles: "**"` ensures `templates/`, `static/`, and the CSV are bundled with the serverless function (they are not Python imports, so Vercel would not include them by default).
- All requests, including `/static/*`, are routed to Flask, which serves them itself.

### Why CSS or static files might fail on Vercel

If you remove `includeFiles` or revert `vercel.json`, the static folder is not bundled and you will see an unstyled page. Keep `"includeFiles": "**"` in place.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Flask 3 |
| ML / NLP | scikit-learn (TF-IDF, cosine similarity), pandas, numpy |
| Frontend | Jinja2, vanilla CSS, vanilla JS |
| Fonts | Plus Jakarta Sans + Inter (Google Fonts) |
| Hosting | Vercel (serverless Python) |
| Dataset | Amazon India product listings, eco-scored offline |

---

## Customization Cheatsheet

| Want to change... | Edit |
|---|---|
| Colors / theme | `static/style.css` (`:root` block at the top) |
| Brand name / tagline | `app.py` -> `inject_globals()` |
| Guide steps | `templates/base.html` -> `.onboard-step` blocks |
| Sample search chips | `templates/index.html` -> `chips` loop |
| Synonyms / routing | `eco_recommender.py` -> `QUERY_EXPANSIONS`, `PRIMARY_CATEGORY_MAP` |
| Hybrid score weights | `eco_recommender.py` -> `recommend()` and `get_similar_products()` |
| Number of results | `recommend(top_n=N)` in `app.py` |
| Image fallback look | `static/brand-fallback.svg` |

---

## Dataset Schema

`amazon_final_eco_scored.csv` (~1,350 unique products) includes columns used by EcoWise:

| Column | Used for |
|---|---|
| `product_id` | Unique identifier (URLs, similar lookup) |
| `product_name` | Title + TF-IDF features + image keywords |
| `category` | Hierarchical path (`L1\|L2\|...\|leaf`); routing and filtering |
| `about_product` | Description text added to features |
| `rating`, `rating_count` | User rating signal |
| `eco_score` | Pre-computed sustainability score (0 to 100) |
| `discounted_price`, `actual_price`, `discount_percentage` | Price display |
| `img_link` | Product image (with fallback chain if missing) |
| `product_link` | "Buy" external link |

---

## Roadmap / Ideas

- Re-rank with embedding models (for example `sentence-transformers`) for even smarter intent matching.
- User accounts and a saved "green wishlist".
- Compare two products side-by-side.
- Real-time price and availability via an external API.
- Light/Dark theme toggle.

---

## Team and Credits

EcoWise was built collaboratively by:

| Member | Role | Contribution |
|---|---|---|
| Manav Rai | Platform Developer / Design | Designed and developed the full web platform: Flask backend, routing, recommender integration, UI/UX, light eco theme, first-time user guide, image fallback system, and Vercel deployment. |
| Uday Chugh | ML Engineer | Co-built the eco-scoring and recommendation ML model. |
| Samar Pratap Singh | ML Engineer | Co-built the eco-scoring and recommendation ML model. |

> The recommendation engine (TF-IDF + hybrid scoring + eco-score signals) is the result of the ML work by Uday and Samar; the platform that wraps and serves it was designed and developed by Manav.

---

## License

MIT. Feel free to fork, remix, and ship your own greener marketplace.

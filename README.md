# EcoWise — AI-Powered Eco-Friendly Product Recommendations

Search anything and get the top 5 eco-friendly product picks, ranked by a hybrid score (relevance + eco-score + user rating).

## Local Development

```bash
pip install -r requirements.txt
python3 app.py
# open http://127.0.0.1:5051
```

## Deploy to Vercel

### Option A — One-click via the Vercel website (no terminal needed)

1. Push this repo to GitHub (if not already).
2. Go to [vercel.com/new](https://vercel.com/new).
3. **Import** the GitHub repo `Eco-Friendly_Product_Recommendation`.
4. Vercel auto-detects Python via `vercel.json`. Just click **Deploy**.
5. After ~1–2 minutes you’ll get a live URL like `https://eco-wise.vercel.app`.

### Option B — Deploy from the terminal

```bash
npm install -g vercel
vercel login
vercel             # follow prompts; accept defaults
vercel --prod      # promote to production
```

## Project Structure

```
.
├── app.py                          # Flask app + routes
├── eco_recommender.py              # Smart NLP recommender (TF-IDF + hybrid score)
├── amazon_final_eco_scored.csv     # Product dataset
├── requirements.txt                # Python dependencies (pinned)
├── vercel.json                     # Vercel config
├── templates/                      # Jinja templates
│   ├── base.html
│   ├── index.html
│   ├── search.html
│   ├── product.html
│   └── _card.html
└── static/
    ├── style.css
    ├── app.js
    └── brand-fallback.svg
```

## Notes about Vercel

- Vercel’s serverless functions cold-start. The first request after idle may take 3–5 seconds while the recommender loads.
- The bundle includes `pandas` + `scikit-learn`. It fits in Vercel’s 250 MB unzipped limit but pushes against it; if a build ever fails for size, switch to **Render** (no size limit) using a `Procfile`:

  ```
  web: gunicorn app:app
  ```

  and add `gunicorn` to `requirements.txt`.

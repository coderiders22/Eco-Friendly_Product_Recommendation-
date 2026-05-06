import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class EcoRecommender:
    def __init__(self, data_path='amazon_final_eco_scored.csv'):
        # Load data and drop completely duplicated product_ids to ensure clean recommendations
        self.df = pd.read_csv(data_path).drop_duplicates(subset=['product_id']).reset_index(drop=True)
        
        # Ensure numeric types
        self.df['rating'] = pd.to_numeric(self.df['rating'], errors='coerce').fillna(0)
        self.df['eco_score'] = pd.to_numeric(self.df['eco_score'], errors='coerce').fillna(0)
        
        # Build TF-IDF matrix based on product name and category for semantic similarity
        self.df['features'] = self.df['product_name'].fillna('') + ' ' + self.df['category'].fillna('')
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df['features'])
    
    def recommend(self, query, top_n=5, sort_by='eco_score'):
        """
        Recommend products based on the query, prioritizing eco-friendly ones.
        """
        # Filter by query
        query_str = query.lower()
        mask = self.df['product_name'].str.lower().str.contains(query_str, na=False) | \
               self.df['category'].str.lower().str.contains(query_str, na=False)
        
        results = self.df[mask]
        
        if results.empty:
            return "No matching products found."
        
        # We can rank by combination of eco_score and rating
        if sort_by == 'eco_score':
            results = results.sort_values(by=['eco_score', 'rating'], ascending=[False, False])
        else:
            results = results.sort_values(by=['rating', 'eco_score'], ascending=[False, False])
        
        # Return top_n recommendations
        return results[['product_name', 'category', 'rating', 'eco_score']].head(top_n)

    def get_similar_products(self, product_id, top_n=5, weight_sim=0.25, weight_eco=0.55, weight_rating=0.20):
        """
        Recommend similar products to a specific product_id using NLP similarity,
        combined with the product's eco-score and real user rating.
        """
        if product_id not in self.df['product_id'].values:
            return "Product not found."
            
        # Get index of target product
        idx = self.df.index[self.df['product_id'] == product_id].tolist()[0]
        target_name = self.df.iloc[idx]['product_name']
        target_category = self.df.iloc[idx]['category']
        
        # Compute cosine similarity of the target product against all others
        cosine_sim = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        
        # Create a copy to store similarities safely
        similar = self.df.copy()
        similar['similarity'] = cosine_sim
        
        # Exclude the target product itself and enforce category matching to prevent wild recommendations
        similar = similar[(similar['product_id'] != product_id) & (similar['category'] == target_category)]
        
        # Filter for products that are at least somewhat similar (threshold > 0.1)
        similar = similar[similar['similarity'] > 0.1]
        
        if similar.empty:
            return target_name, target_category, "No similar products found."
            
        # Hybrid Scoring System: 
        # Normalize rating (0-5) to 0-100 scale to match eco_score (0-100) and similarity (0-1)
        similar['rating_norm'] = (similar['rating'] / 5.0) * 100
        
        similar['hybrid_score'] = (
            (similar['similarity'] * 100) * weight_sim +
            (similar['eco_score']) * weight_eco +
            (similar['rating_norm']) * weight_rating
        )
        
        # Sort by the new mixed score
        similar = similar.sort_values(by='hybrid_score', ascending=False)
        
        return target_name, target_category, similar[['product_id', 'product_name', 'similarity', 'eco_score', 'rating', 'hybrid_score']].head(top_n)

if __name__ == '__main__':
    recommender = EcoRecommender()
    print("--- ML-Powered Eco-Friendly Recommender System ---")
    
    # Pick 5 distinct products from different categories to test
    test_products = recommender.df.drop_duplicates(subset=['category']).head(5)['product_id'].tolist()
    
    for pid in test_products:
        target_name, target_cat, sim = recommender.get_similar_products(pid)
        
        print(f'\n======================================================')
        print(f'Target Product: {target_name[:80]}...') # Truncate for display
        print(f'Category: {target_cat.split("|")[-1]}') # Show only the main category node
        print('Top 5 Sustainable Alternatives:')
        
        if isinstance(sim, str):
            print(sim)
        else:
            # Format the numbers for cleaner printing and truncate name
            sim_display = sim.copy()
            sim_display['product_name'] = sim_display['product_name'].str[:75] + '...'
            sim_display['similarity'] = sim_display['similarity'].round(3)
            sim_display['hybrid_score'] = sim_display['hybrid_score'].round(2)
            print(sim_display.to_string(index=False))

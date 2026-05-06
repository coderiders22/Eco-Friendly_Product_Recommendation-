import pandas as pd

def calculate_eco_score(text):
    """
    Calculate an eco-score based on the presence of sustainability keywords.
    Each unique keyword found adds 20 points, up to a maximum of 100.
    """
    # Define our list of environmentally friendly keywords
    eco_keywords = [
        'eco-friendly', 'environment', 'sustainable', 'biodegradable', 
        'organic', 'recycled', 'bamboo', 'green', 'energy saving', 
        'solar', 'plastic-free', 'natural'
    ]
    
    if pd.isna(text):
        return 0
        
    text = str(text).lower()
    score = sum(1 for word in eco_keywords if word in text)
    
    # Cap the maximum score at 100
    return min(score * 20, 100)

def process_dataset():
    print("Loading original Amazon dataset...")
    # Load the raw dataset
    df = pd.read_csv('amazon.csv')

    print("Calculating eco-scores based on product names and descriptions...")
    # Apply the scoring function to the product name and description
    df['nlp_eco_score_name'] = df['product_name'].apply(calculate_eco_score)
    df['nlp_eco_score_desc'] = df['about_product'].apply(calculate_eco_score)

    # Take the highest score between the name and the description
    df['eco_score'] = df[['nlp_eco_score_name', 'nlp_eco_score_desc']].max(axis=1)

    # Drop the temporary calculation columns to keep the final dataset clean
    df = df.drop(columns=['nlp_eco_score_name', 'nlp_eco_score_desc'])

    output_filename = 'amazon_final_eco_scored.csv'
    print(f"Saving newly scored dataset to {output_filename}...")
    
    # Save the new dataset
    df.to_csv(output_filename, index=False)
    print("Done! Dataset is ready for the recommender system.")

if __name__ == "__main__":
    process_dataset()
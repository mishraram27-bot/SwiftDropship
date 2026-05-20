import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models import Product


class ProductRecommender:
    def __init__(self):
        self.vectorizer = CountVectorizer()
        self.similarity_matrix = None
        self.products_df = None

    def train(self):
        products = Product.query.all()
        if not products:
            return

        product_data = []
        for product in products:
            features = f"{product.category} {product.name} {product.description}".lower()
            product_data.append(
                {
                    "id": product.id,
                    "features": features,
                    "category": product.category,
                    "price": product.price,
                }
            )

        self.products_df = pd.DataFrame(product_data)
        feature_vectors = self.vectorizer.fit_transform(self.products_df["features"])
        self.similarity_matrix = cosine_similarity(feature_vectors)

    def get_recommendations(self, product_id, num_recommendations=4):
        if self.similarity_matrix is None or self.products_df is None:
            return []

        try:
            product_idx = self.products_df[self.products_df["id"] == product_id].index[0]
            similarity_scores = list(enumerate(self.similarity_matrix[product_idx]))
            similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

            recommended_indices = [i[0] for i in similarity_scores[1 : num_recommendations + 1]]
            recommended_ids = self.products_df.iloc[recommended_indices]["id"].tolist()

            return Product.query.filter(Product.id.in_(recommended_ids)).all()
        except Exception:
            return []

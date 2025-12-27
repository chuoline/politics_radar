from flask import Flask, render_template
from .queries import fetch_category_counts, fetch_matrix_counts

def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        cat_counts = fetch_category_counts()
        matrix, bins = fetch_matrix_counts()
        return render_template("index.html", cat_counts=cat_counts, matrix=matrix, bins=bins)

    return app
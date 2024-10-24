from app import *

if __name__ == "__main__":
    with app.app_context():
        models.seed()
    app.run(debug=True, port=5000, host='0.0.0.0')
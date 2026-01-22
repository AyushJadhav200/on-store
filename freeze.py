from flask_frozen import Freezer
from app import app

# Configuration for Frozen-Flask
# This will save the static files to a 'build' directory
app.config['FREEZER_DESTINATION'] = 'build'
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_REMOVE_EXTRA_FILES'] = False

freezer = Freezer(app)

if __name__ == '__main__':
    print("Freezing the Flask application...")
    freezer.freeze()
    print("Static site generated in the 'build' directory.")

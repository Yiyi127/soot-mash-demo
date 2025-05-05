from flask import Flask
from api.mash import mash_bp
from api.soot_connector import soot_bp

app = Flask(__name__)
app.register_blueprint(mash_bp, url_prefix='/mash')
app.register_blueprint(soot_bp, url_prefix='/soot')

if __name__ == '__main__':
    app.run(debug=True, port=5001)

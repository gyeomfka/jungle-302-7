from flask import Flask, render_template, jsonify
from db import get_db
app = Flask(__name__)

@app.route('/')
def home():
   return render_template('index.html')

@app.route('/test')
def test():
   db = get_db()
   user = list(db.user.find({}))
   print(user)
   return jsonify({"count": len(user)})



if __name__ == '__main__':  
   app.run('0.0.0.0',port=5001,debug=True)
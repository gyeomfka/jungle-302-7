from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response
import requests
import urllib.parse
from datetime import datetime, timezone
from db import get_db
from config import get_config
from utils.auth import token_required, get_user_info

app = Flask(__name__)
cfg = get_config()

@app.route('/')
def home():
   return render_template('index.html')

@app.route('/login')
def login_page():
   return render_template('login.html')


@app.route('/auth/kakao')
def kakao_login():
   kakao_auth_url = "https://kauth.kakao.com/oauth/authorize"
   params = {
       'client_id': cfg.KAKAO_CLIENT_ID,
       'redirect_uri': cfg.KAKAO_REDIRECT_URI,
       'response_type': 'code'
   }
   auth_url = f"{kakao_auth_url}?{urllib.parse.urlencode(params)}"
   return redirect(auth_url)

@app.route('/auth/kakao/callback')
def kakao_callback():
   code = request.args.get('code')

   if not code:
       return redirect(url_for('login_page'))
   
   token_url = "https://kauth.kakao.com/oauth/token"
   token_data = {
       'grant_type': 'authorization_code',
       'client_id': cfg.KAKAO_CLIENT_ID,
       'client_secret': cfg.KAKAO_CLIENT_SECRET,
       'redirect_uri': cfg.KAKAO_REDIRECT_URI,
       'code': code
   }
   
   token_response = requests.post(token_url, data=token_data)
   token_json = token_response.json()
   
   if 'access_token' not in token_json:
       return redirect(url_for('login_page'))
   
   access_token = token_json['access_token']
   expires_in = token_json['expires_in']
   refresh_token = token_json['refresh_token']
   refresh_token_expires_in = token_json['refresh_token_expires_in']
   
   user_info = get_user_info(access_token)
   
   kakao_id = str(user_info['id'])
   kakao_profile = user_info.get('kakao_account', {})
   email = kakao_profile.get('email', '')
   nickname = kakao_profile.get('profile', {}).get('nickname', f'사용자{kakao_id}')
   
   db = get_db()
   
   user = db.user.find_one({'id': kakao_id})
   
   if not user:
       user_data = {
           'id': kakao_id,
           'email': email,
           'name': nickname,
       }
       result = db.user.insert_one(user_data)
       user_id = result.inserted_id
       response = make_response(redirect(url_for('profile')))
   else:
       user_id = user['id']
       db.user.update_one(
           {'id': user_id},
           {'$set': {'updated_at': datetime.now(timezone.utc)}}
       )
       response = make_response(redirect(url_for('study')))

   response.set_cookie('access_token', access_token, 
                      max_age=expires_in,
                      httponly=True, secure=False)
   response.set_cookie('refresh_token', refresh_token,
                      max_age=refresh_token_expires_in,
                      httponly=True, secure=False)
   request.current_user_id = str(user_id)
   
   return response

@app.route('/study')
@token_required
def study():
   # 스터디 목록
   return jsonify({
       'message': '로그인 성공!',
       'user_id': request.current_user_id
   })

@app.route('/profile')
@token_required
def profile():
   return jsonify({
       'message': 'profile!',
       'user_id': request.current_user_id
   })

@app.route('/logout')
def logout():
   response = make_response(redirect(url_for('login_page')))
   response.set_cookie('access_token', '', expires=0)
   response.set_cookie('refresh_token', '', expires=0)
   request.current_user_id = None
   return response

@app.route('/test')
def test():
   db = get_db()
   user = list(db.user.find({}))
   print(user)
   return jsonify({"count": len(user)})

if __name__ == '__main__':  
   app.run('0.0.0.0',port=5001,debug=True)


# TODO: 회원가입 후 관심사 설정

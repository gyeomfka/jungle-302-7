from flask import Flask, render_template, jsonify, request, redirect, url_for
import urllib.parse
from db import get_db
from config import get_config
from utils.auth import token_required, handle_kakao_callback, handle_logout, update_user_profile

app = Flask(__name__)
cfg = get_config()

# TODO: 설정하지 않은 나머지 경로는 /study로 이동
@app.route('/')
def home():
   return redirect('/study')

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
   return handle_kakao_callback(code)

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
   return render_template('profile.html')

@app.route('/profile/update', methods=['POST'])
@token_required
def profile_update():
   interests = request.form.get('interests', '')
   description = request.form.get('description', '')
   
   success = update_user_profile(
      request.current_user_id,
      interests,
      description
   )
   
   if success:
      return redirect(url_for('study'))
   else:
      return render_template('profile.html', error="프로필 업데이트에 실패했습니다. 다시 시도해주세요.")
      
@app.route('/create_study', methods=['GET'])
def create_study_form():
   return render_template('create_study.html')

@app.route('/create_study', methods=['POST'])
def create_study():
   db = get_db()
   data = request.get_json()
   
   name = data.get("studyName")
   host_id = "test_user"
   description = data.get("studyIntro")
   category = data.get("category")
   max_participants = data.get("maxParticipants")
   candidate = [item['selectedDate'] for item in data['expectedDateList']]

   study = {
      "name": name,
      "host_id": host_id,
      "description": description,
      "category": category,
      "max_participants": max_participants,
      "candidate": candidate
   }

   db.study.insert_one(study)
   return jsonify({'result': 'success'})

@app.route('/logout')
def logout():
   return handle_logout()

@app.route('/test')
def test():
   db = get_db()
   user = list(db.user.find({}))
   print(user)
   return jsonify({"count": len(user)})

if __name__ == '__main__':  
   app.run('0.0.0.0',port=5001,debug=True)


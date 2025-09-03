from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    make_response,
)
import urllib.parse
from bson import ObjectId
from db import get_db
from config import get_config
from utils.auth import (
    token_required,
    handle_kakao_callback,
    handle_logout,
    update_user_profile,
)
from utils.study import (
    apply_to_study,
    get_study_participants,
    update_confirmed_candidates,
    get_user_profile,
    get_studies_by_tab,
    get_study_by_id
)

app = Flask(__name__)
cfg = get_config()


# TODO: 설정하지 않은 나머지 경로는 /study로 이동
@app.route("/")
def home():
    return redirect("/study")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/auth/kakao")
def kakao_login():
    kakao_auth_url = "https://kauth.kakao.com/oauth/authorize"
    params = {
        "client_id": cfg.KAKAO_CLIENT_ID,
        "redirect_uri": cfg.KAKAO_REDIRECT_URI,
        "response_type": "code",
    }
    auth_url = f"{kakao_auth_url}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


@app.route("/auth/kakao/callback")
def kakao_callback():
    code = request.args.get("code")
    return handle_kakao_callback(code)


@app.route("/study")
@token_required
def study():
    tab = request.args.get("tab", "all")  # 기본값: 전체 스터디

    # 유효한 탭인지 확인
    if tab not in ["all", "my", "applied"]:
        tab = "all"

    # 탭에 따라 스터디 데이터 조회
    studies = get_studies_by_tab(request.current_user_id, tab) 

    return render_template('study.html', studies=studies, tab=tab)


@app.route("/study/create", methods=['GET'])
@token_required
def study_create_page():
   if request.method == 'GET':
       return render_template("create_study.html")
   

@app.route("/study/create", methods=['POST'])
@token_required
def create_study():
    try:
        db = get_db()
        data = request.get_json()
        
        # 필수 필드 검증
        name = data.get("studyName")
        if not name or name.strip() == "":
            return jsonify({'result': 'error', 'message': '스터디 이름을 입력해주세요.'}), 400
        
        host_id = request.current_user_id
        if not host_id:
            return jsonify({'result': 'error', 'message': '로그인이 필요합니다.'}), 401
            
        subject = data.get("category")
        if not subject:
            return jsonify({'result': 'error', 'message': '카테고리를 선택해주세요.'}), 400
            
        expected_date_list = data.get("expectedDateList", [])
        if not expected_date_list:
            return jsonify({'result': 'error', 'message': '예상 모임 날짜를 하나 이상 선택해주세요.'}), 400
        
        # candidate 배열 생성 - {date: string, user_id: string} 형식
        candidate = []
        for item in expected_date_list:
            selected_date = item.get('selectedDate')
            if selected_date:
                candidate.append({
                    "date": selected_date,
                    "user_id": []  # 빈 배열로 초기화
                })
        
        if not candidate:
            return jsonify({'result': 'error', 'message': '유효한 모임 날짜를 선택해주세요.'}), 400
        
        # 스터디 데이터 생성 (MongoDB 스키마에 맞게)
        study = {
            "id": str(ObjectId()),  # 고유 ID 생성
            "host_id": host_id,
            "name": name.strip(),
            "description": data.get("studyIntro", "").strip(),
            "subject": subject,
            "candidate": candidate,
            "max_participants": int(data.get("maxParticipants", 5)),
            "confirmed_candidate": [],  # 빈 배열로 초기화
            "isClosed": False,   # 빈 배열로 초기화
            "study_date": ""           # 빈 문자열로 초기화
        }
        
        db.study.insert_one(study)
        return jsonify({'result': 'success'})
        
    except ValueError as e:
        return jsonify({'result': 'error', 'message': '잘못된 데이터 형식입니다.'}), 400
    except Exception as e:
        print(f"스터디 생성 오류: {e}")
        return jsonify({'result': 'error', 'message': '스터디 생성 중 오류가 발생했습니다.'}), 500


@app.route("/study/<string:study_id>")
@token_required
def study_detail(study_id):
    study = get_study_by_id(study_id)
    current_user_id = request.current_user_id
     
    # 스터디 호스트인 경우 참가자 정보도 함께 조회
    confirmed_participants = []
    pending_candidates = []
    
    if current_user_id == study.get("host_id"):
        confirmed_participants, pending_candidates = get_study_participants(study_id)
    
    # 쿼리스트링에서 탭 정보 가져오기

    tab = request.args.get('tab', 'all')
    html = render_template(
        "components/study/study_detail_fragment.html", 
        study=study,
        current_user_id=current_user_id,
        confirmed_participants=confirmed_participants,
        pending_candidates=pending_candidates,
        tab=tab
    )
    response = make_response(html, 200)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


@app.route("/study/<string:study_id>/apply", methods=["POST"])
@token_required
def study_apply(study_id):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        data = request.get_json()
        selected_dates = data.get("selected_dates", [])

        success, message = apply_to_study(
            study_id, request.current_user_id, selected_dates
        )

        if success:
            return make_response(message, 200)
        else:
            return make_response(message, 400)

    except Exception as e:
        print(f"스터디 신청 API 오류: {e}")
        return make_response("신청 처리 중 오류가 발생했습니다.", 500)


@app.route("/study/<string:study_id>/confirm-candidates", methods=["POST"])
@token_required
def confirm_candidates(study_id):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)
    
    try:
        data = request.get_json()
        confirmed_candidates = data.get("confirmed_candidates", [])
        
        success, message = update_confirmed_candidates(study_id, confirmed_candidates)
        
        if success:
            return make_response(message, 200)
        else:
            return make_response(message, 400)
            
    except Exception as e:
        print(f"참가자 확정 API 오류: {e}")
        return make_response("확정 처리 중 오류가 발생했습니다.", 500)


@app.route("/user/<string:user_id>/profile")
@token_required
def user_profile_api(user_id):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)
    
    try:
        user = get_user_profile(user_id)
        
        if not user:
            return make_response("사용자를 찾을 수 없습니다.", 404)
        
        # MongoDB ObjectId 제거
        if '_id' in user:
            del user['_id']
            
        return jsonify(user)
        
    except Exception as e:
        print(f"사용자 프로필 API 오류: {e}")
        return make_response("사용자 정보 조회 중 오류가 발생했습니다.", 500)


@app.route("/profile")
@token_required
def profile():
    return render_template("profile.html")


@app.route("/profile/update", methods=["POST"])
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
      

@app.route('/logout')
def logout():
    return handle_logout()


@app.route("/test")
def test():
    db = get_db()
    user = list(db.user.find({}))
    return jsonify({"count": len(user)})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)

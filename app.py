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
    delete_user_account,
    get_user_profile
)
from utils.study import (
    apply_to_study,
    get_study_participants,
    update_confirmed_candidates,
    get_studies_by_tab,
    get_study_by_id,
    withdraw_from_study,
    delete_study
)
from utils.notification import (
    get_user_notifications,
    get_unread_notification_count,
    mark_notification_as_read,
    mark_all_notifications_as_read
)
from utils.date_utils import to_datetime_str

from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit, send, disconnect
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
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
    search_keyword = request.args.get("searchKeyword", "")
    category = request.args.get("category")
    
    is_closed = request.args.get("is_closed")
    context={}
    if is_closed is not None:
        context["is_closed"] = is_closed

    # 유효한 탭인지 확인
    if tab not in ["all", "my", "applied"]:
        tab = "all"
        
    # 탭에 따라 스터디 데이터 조회
    studies = get_studies_by_tab(request.current_user_id, tab, search_keyword, category, is_closed) 

    return render_template('study.html', studies=studies, tab=tab, search_keyword=search_keyword, category=category, **context, to_datetime_str=to_datetime_str)



@app.route("/study/create", methods=['GET'])
@token_required
def study_create_page():
    if request.method == 'GET':
        return render_template("create_study.html", to_datetime_str=to_datetime_str)


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
            return jsonify({
                'result': 'error',
                'message': '예상 모임 날짜를 하나 이상 선택해주세요.'
            }), 400

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
            "is_closed": False,   # 빈 배열로 초기화
            "study_date": ""           # 빈 문자열로 초기화
        }

        db.study.insert_one(study)
        return jsonify({'result': 'success'})

    except ValueError:
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
        tab=tab, 
        to_datetime_str=to_datetime_str
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


@app.route("/study/<string:study_id>/withdraw", methods=["POST"])
@token_required
def study_withdraw(study_id):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        success, message = withdraw_from_study(study_id, request.current_user_id)

        if success:
            return make_response(message, 200)
        else:
            return make_response(message, 400)

    except Exception as e:
        print(f"스터디 철회 API 오류: {e}")
        return make_response("철회 처리 중 오류가 발생했습니다.", 500)


@app.route("/study/<string:study_id>/delete", methods=["DELETE"])
@token_required
def study_delete(study_id):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        success, message = delete_study(study_id, request.current_user_id)

        if success:
            return make_response(message, 200)
        else:
            return make_response(message, 400)

    except Exception as e:
        print(f"스터디 삭제 API 오류: {e}")
        return make_response("삭제 처리 중 오류가 발생했습니다.", 500)


@app.route("/study/<string:study_id>/confirm-candidates", methods=["POST"])
@token_required
def confirm_candidates(study_id):    
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        data = request.get_json()

        confirmed_candidates = data.get("confirmed_candidates", [])
        study_date = data.get("study_date")
        
        # 스터디 날짜가 필수인지 확인
        if not study_date:
            return make_response("스터디 진행 날짜를 선택해주세요.", 400)

        success, message = update_confirmed_candidates(
            study_id, confirmed_candidates, study_date
        )

        if success:
            return make_response(message, 200)
        else:
            return make_response(message, 400)
    except Exception as e:
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
    # 현재 사용자 프로필 정보 가져오기
    user_profile = get_user_profile(request.current_user_id)
    return render_template("profile.html", user_profile=user_profile, to_datetime_str=to_datetime_str)


@app.route("/profile/update", methods=["POST"])
@token_required
def profile_update():
    interests = request.form.get('interests', '')
    phone = request.form.get('phone', '')
    description = request.form.get('description', '')

    success = update_user_profile(
        request.current_user_id,
        interests,
        phone,
        description
    )

    if success:
        return redirect(url_for('study'))
    else:
        return render_template(
            'profile.html',
            error="프로필 업데이트에 실패했습니다. 다시 시도해주세요.", to_datetime_str=to_datetime_str
        )

@app.route('/logout')
def logout():
    return handle_logout()


@app.route("/user/delete-account", methods=["POST"])
@token_required
def delete_account():
    """회원탈퇴 - 사용자 데이터 및 관련 스터디 삭제"""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    success, message = delete_user_account(request.current_user_id)

    if success:
        return make_response(message, 200)
    else:
        return make_response(message, 500)


@app.route("/notifications")
@token_required
def notifications():
    """사용자 알림 목록을 반환합니다."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        user_id = request.current_user_id
        notifications = get_user_notifications(user_id)

        # MongoDB ObjectId를 문자열로 변환
        for notification in notifications:
            notification['_id'] = str(notification['_id'])
            if 'created_at' in notification:
                notification['created_at'] = notification['created_at'].isoformat()

        return jsonify({
            'success': True,
            'notifications': notifications
        })

    except Exception as e:
        print(f"알림 목록 조회 오류: {e}")
        return make_response("알림을 불러오는 중 오류가 발생했습니다.", 500)


@app.route("/notifications/unread-count")
@token_required
def unread_notification_count():
    """읽지 않은 알림 개수를 반환합니다."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        user_id = request.current_user_id
        count = get_unread_notification_count(user_id)

        return jsonify({
            'success': True,
            'count': count
        })

    except Exception as e:
        print(f"읽지 않은 알림 개수 조회 오류: {e}")
        return make_response("알림 개수를 불러오는 중 오류가 발생했습니다.", 500)


@app.route("/notifications/<string:notification_id>/read", methods=["POST"])
@token_required
def mark_notification_read(notification_id):
    """특정 알림을 읽음 상태로 변경합니다."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        user_id = request.current_user_id
        success = mark_notification_as_read(notification_id, user_id)

        if success:
            return jsonify({
                'success': True,
                'message': '알림이 읽음 처리되었습니다.'
            })
        else:
            return make_response("알림 처리에 실패했습니다.", 400)

    except Exception as e:
        print(f"알림 읽음 처리 오류: {e}")
        return make_response("알림 처리 중 오류가 발생했습니다.", 500)


@app.route("/notifications/mark-all-read", methods=["POST"])
@token_required
def mark_all_notifications_read():
    """모든 알림을 읽음 상태로 변경합니다."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return make_response("잘못된 요청입니다.", 400)

    try:
        user_id = request.current_user_id
        count = mark_all_notifications_as_read(user_id)

        return jsonify({
            'success': True,
            'message': f'{count}개의 알림이 읽음 처리되었습니다.',
            'count': count
        })

    except Exception as e:
        print(f"모든 알림 읽음 처리 오류: {e}")
        return make_response("알림 처리 중 오류가 발생했습니다.", 500)


@app.route("/test")
def test():
    db = get_db()
    user = list(db.user.find({}))
    return jsonify({"count": len(user)})

# 현재 생성된 방들
rooms = {}

@app.route('/error')
def error():
    return render_template("error.html", to_datetime_str=to_datetime_str)

@app.route('/room/<room_id>/<user_id>')
def room(room_id, user_id):
    db = get_db()
    # room_id가 db에 있는지 확인
    roomFound = db.video_chat.find_one({'id': room_id})
    if not roomFound:
        return redirect(url_for("error"))
    
    print('----------------------------')
    print(roomFound)
    # user_id가 db에 있는지 확인
    userFound = db.user.find_one({'id': user_id})
    if not userFound:
        return redirect(url_for("error"))
    
    print(userFound)
    # 방을 만들어도 되는 시간 인지 (start_date + 3시간)

    start_time = datetime.fromisoformat(roomFound["start_date"])
    # start_time = (roomFound["start_date"])
    expire_time = start_time + timedelta(hours=3)

    print(start_time)
    print(expire_time)
    print(datetime.now() > expire_time)
    print(datetime.now() < start_time - timedelta(minutes=10))
    print(datetime.now() > expire_time) or (datetime.now() < start_time - timedelta(minutes=10))
    if (datetime.now() > expire_time) or (datetime.now() < start_time - timedelta(minutes=10)):
        print('date error')
        return redirect(url_for("error"))
    
    session["room"] = room_id
    session["user"] = user_id
    
    # 입력한 room_id가 rooms에 없으면 새로운 방 생성
    if room_id not in rooms:
        rooms[room_id] = {"members" : 0, "userIDs":{}}
    print('==============render html===============')
    return render_template("room.html", room_id=room_id, username = userFound["name"], to_datetime_str=to_datetime_str)
    # return render_template("room.html", room_id=room_id, username = "userFound")



@socketio.on("join")
def handle_join(data):
    user_id = session.get("user")
    room_id = session.get("room")


    
    rooms[room_id]["userIDs"][user_id] = request.sid
    
    # 자바스크립트에서 전달된 데이터 가져오기 (룸 ID)
    room = data["room"]

    # 현재 세션 ID
    user_id = request.sid

    # 클라이언트 연결을 위해 소켓에서 방 참여 - 추후 아무도 없을때 방 삭제
    join_room(room)

    # 생성된 방의 인원 수 1명 증가
    rooms[room]["members"] += 1

    # 자바스크립트 " socketio.on("user-joined.."로 이동 // 현재 들어온 유저 제외 모든 사람한테 전달
    emit("user-joined", {"userId": user_id}, room=room, include_self=False)


# A 유저에서 B 유저한테 signal - offer / answer / ICE 전송
@socketio.on("signal")
def handle_signal(data):
    to_user = data["to"]
    emit("signal", {**data, "from": request.sid}, room=to_user)

@socketio.on("message")
def message(data):
    db = get_db()
    room = session.get("room")
    if room not in rooms:
        return
    user_doc = db.user.find_one({"id": session.get("user")})
    user_name = user_doc["name"] if user_doc else "Unknown"
    content = {
        "name": user_name,
        "message": data["data"]
    }
    send(content, to=room)

# 이게 있어야 disconnect 작동가능 - 소켓 서버 열결 코드는 "join"
@socketio.on("connect")
def connect():
    return

@socketio.on("disconnect")
def disconnect():
    print('asd')
    room = session.get('room')
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    user_id = request.sid
    emit("user-left", {"userId": user_id}, room=room)   


if __name__ == "__main__":
    socketio.run(app, "0.0.0.0", port=5001, debug=True)
    # app.run("0.0.0.0", port=5001, debug=True)

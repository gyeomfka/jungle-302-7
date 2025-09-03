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
from db import get_db
from config import get_config
from utils.auth import (
    token_required,
    handle_kakao_callback,
    handle_logout,
    update_user_profile,
)
# from utils.study import get_studies_by_tab, get_study_by_id, apply_to_study  # TODO
from utils.study import apply_to_study
from __mocks__.study import mock_studies

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
    # studies = get_studies_by_tab(request.current_user_id, tab)  # TODO

    return render_template("study.html", studies=mock_studies, tab=tab)
    # return render_template('study.html', studies=studies, tab=tab) # TODO


@app.route("/study/create")
@token_required
def study_create():
    return render_template("study_create.html")


@app.route("/study/<string:study_id>")
@token_required
def study_detail(study_id):
    # study = get_study_by_id(study_id)  # TODO
    html = render_template(
        "components/study/study_detail_fragment.html", study=mock_studies[0]
    )
    # html = render_template(  # TODO
    #     'components/study/study_detail_fragment.html', study=study
    # )
    response = make_response(html, 200)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


@app.route("/study/<string:study_id>/apply", methods=["POST"])
@token_required
def study_apply(study_id):  # TODO: 실제 데이터로 확인
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


@app.route("/profile")
@token_required
def profile():
    return render_template("profile.html")


@app.route("/profile/update", methods=["POST"])
@token_required
def profile_update():
    interests = request.form.get("interests", "")
    description = request.form.get("description", "")

    success = update_user_profile(request.current_user_id, interests, description)

    if success:
        return redirect(url_for("study"))
    else:
        return render_template(
            "profile.html", error="프로필 업데이트에 실패했습니다. 다시 시도해주세요."
        )


@app.route("/logout")
def logout():
    return handle_logout()


@app.route("/test")
def test():
    db = get_db()
    user = list(db.user.find({}))
    print(user)
    return jsonify({"count": len(user)})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5001, debug=True)

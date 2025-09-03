import requests
from datetime import datetime, timezone
from flask import request, redirect, url_for, make_response
from functools import wraps
from config import get_config
from db import get_db

cfg = get_config()


def get_token_from_request():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            token = auth_header.split(" ")[1]
            return token
        except IndexError:
            return None

    return [request.cookies.get("access_token"), request.cookies.get("refresh_token")]


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token, refresh_token = get_token_from_request()

        need_token_refresh = False

        if not access_token:
            # access_token이 없으면 refresh_token으로 갱신
            result = refresh_access_token(refresh_token)
            if isinstance(result, tuple):
                access_token, expires_in, refresh_token, refresh_token_expires_in = (
                    result
                )
                need_token_refresh = True
            else:
                # 갱신 실패시 로그인 페이지로 리다이렉트
                return result
        else:
            # access_token이 있으면 유효한지 확인
            token_response = requests.get(
                "https://kapi.kakao.com/v1/user/access_token_info",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if token_response.status_code != 200:
                # 토큰이 만료되었으면 refresh_token으로 갱신
                result = refresh_access_token(refresh_token)

                if isinstance(result, tuple):
                    (
                        access_token,
                        expires_in,
                        refresh_token,
                        refresh_token_expires_in,
                    ) = result
                    need_token_refresh = True
                else:
                    # 갱신 실패시 로그인 페이지로 리다이렉트
                    return result

        # 사용자 정보를 request에 저장 (카카오 API에서 사용자 정보 가져오기
        user_info = get_user_info(access_token)
        request.current_user_id = str(user_info["id"])

        # 원래 함수 실행
        result = f(*args, **kwargs)

        # 토큰 갱신이 필요하면 쿠키 설정
        if need_token_refresh:
            response = make_response(result)
            response.set_cookie(
                "access_token",
                access_token,
                max_age=expires_in,
                httponly=True,
                secure=False,
            )
            # refresh_token이 있고 expires_in이 있을 때만 쿠키 설정
            if refresh_token and refresh_token_expires_in:
                response.set_cookie(
                    "refresh_token",
                    refresh_token,
                    max_age=refresh_token_expires_in,
                    httponly=True,
                    secure=False,
                )
            return response

        return result

    return decorated


def refresh_access_token(refresh_token):
    """리프레시 토큰으로 액세스 토큰을 갱신합니다."""
    if not refresh_token:
        return redirect(url_for("login_page"))

    token_data = {
        "grant_type": "refresh_token",
        "client_id": cfg.KAKAO_CLIENT_ID,
        "client_secret": cfg.KAKAO_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    token_response = requests.post(
        "https://kauth.kakao.com/oauth/token", data=token_data
    )
    token_json = token_response.json()

    if "access_token" not in token_json:
        return redirect(url_for("login_page"))

    access_token = token_json["access_token"]
    expires_in = token_json["expires_in"]

    # 토큰 만료기한이 1개월 미만일 때 갱신
    if "refresh_token" in token_json:
        refresh_token = token_json["refresh_token"]
        refresh_token_expires_in = token_json["refresh_token_expires_in"]
        return access_token, expires_in, refresh_token, refresh_token_expires_in
    else:
        # refresh_token이 없으면 기존 refresh_token 유지
        return access_token, expires_in, refresh_token, None


def get_user_info(access_token):
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    user_response = requests.get(
        user_info_url, headers={"Authorization": f"Bearer {access_token}"}
    )

    user_info = user_response.json()

    if "id" not in user_info:
        return None

    return user_info


def get_kakao_tokens_from_code(code):
    """카카오 인증 코드를 사용해서 토큰을 가져옵니다."""
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": cfg.KAKAO_CLIENT_ID,
        "client_secret": cfg.KAKAO_CLIENT_SECRET,
        "redirect_uri": cfg.KAKAO_REDIRECT_URI,
        "code": code,
    }

    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()

    if "access_token" not in token_json:
        return None

    return {
        "access_token": token_json["access_token"],
        "expires_in": token_json["expires_in"],
        "refresh_token": token_json["refresh_token"],
        "refresh_token_expires_in": token_json["refresh_token_expires_in"],
    }


def create_or_update_user(user_info):
    """사용자 정보를 DB에 생성하거나 업데이트합니다."""
    kakao_id = str(user_info["id"])
    kakao_profile = user_info.get("kakao_account", {})
    email = kakao_profile.get("email", "")
    nickname = kakao_profile.get("profile", {}).get("nickname", f"사용자{kakao_id}")

    db = get_db()
    user = db.user.find_one({"id": kakao_id})

    if not user:
        # 새 사용자 생성
        user_data = {
            "id": kakao_id,
            "email": email,
            "name": nickname,
            "created_at": datetime.now(timezone.utc),
        }
        result = db.user.insert_one(user_data)
        return {"user_id": result.inserted_id, "is_new_user": True}
    else:
        # 기존 사용자 업데이트
        user_id = user["id"]
        db.user.update_one(
            {"id": user_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )
        return {"user_id": user_id, "is_new_user": False}


def handle_kakao_callback(code):
    """카카오 OAuth 콜백을 처리합니다."""
    if not code:
        return redirect(url_for("login_page"))

    # 1. 인증 코드로 토큰 가져오기
    tokens = get_kakao_tokens_from_code(code)
    if not tokens:
        return redirect(url_for("login_page"))

    # 2. 토큰으로 사용자 정보 가져오기
    user_info = get_user_info(tokens["access_token"])
    if not user_info:
        return redirect(url_for("login_page"))

    # 3. 사용자 생성/업데이트
    user_result = create_or_update_user(user_info)

    # 4. 리다이렉트 결정 (신규 사용자면 프로필, 기존 사용자면 스터디)
    redirect_url = "profile" if user_result["is_new_user"] else "study"
    response = make_response(redirect(url_for(redirect_url)))

    # 5. 쿠키에 토큰 설정
    response.set_cookie(
        "access_token",
        tokens["access_token"],
        max_age=tokens["expires_in"],
        httponly=True,
        secure=False,
    )
    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
        max_age=tokens["refresh_token_expires_in"],
        httponly=True,
        secure=False,
    )

    return response


def handle_logout():
    """로그아웃 처리 - 쿠키 삭제 후 로그인 페이지로 리다이렉트"""
    response = make_response(redirect(url_for("login_page")))
    response.set_cookie("access_token", "", expires=0)
    response.set_cookie("refresh_token", "", expires=0)
    request.current_user_id = None
    return response


def update_user_profile(user_id, interests, description):
    try:
        db = get_db()

        # 관심사를 리스트로 변환
        interest_list = [
            interest.strip() for interest in interests.split(",") if interest.strip()
        ]

        # 사용자 프로필 업데이트
        update_data = {
            "interest_of_subject": interest_list,
            "description": description,
        }

        result = db.user.update_one({"id": user_id}, {"$set": update_data})

        return result.modified_count > 0

    except Exception as e:
        print(f"프로필 업데이트 오류: {e}")
        return False

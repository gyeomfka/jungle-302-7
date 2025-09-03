import requests
from datetime import datetime, timezone, timedelta
from flask import request, redirect, url_for, make_response
from functools import wraps
from config import get_config

cfg = get_config()

def get_token_from_request():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(' ')[1]
            return token
        except IndexError:
            return None
    
    return [request.cookies.get('access_token'),request.cookies.get('refresh_token')]

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token, refresh_token = get_token_from_request()
        
        need_token_refresh = False
        
        if not access_token:
            # access_token이 없으면 refresh_token으로 갱신
            result = refresh_access_token(refresh_token)
            if isinstance(result, tuple):
                access_token, expires_in, refresh_token, refresh_token_expires_in = result
                need_token_refresh = True
            else:
                # 갱신 실패시 로그인 페이지로 리다이렉트
                return result
        else:
            # access_token이 있으면 유효한지 확인
            token_response = requests.get(
                'https://kapi.kakao.com/v1/user/access_token_info',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if token_response.status_code != 200:
                # 토큰이 만료되었으면 refresh_token으로 갱신
                result = refresh_access_token(refresh_token)
                print(result)
                if isinstance(result, tuple):
                    access_token, expires_in, refresh_token, refresh_token_expires_in = result
                    need_token_refresh = True
                else:
                    # 갱신 실패시 로그인 페이지로 리다이렉트
                    return result
        
        # 사용자 정보를 request에 저장 (카카오 API에서 사용자 정보 가져오기
        user_info = get_user_info(access_token)
        request.current_user_id = str(user_info['id'])
        
        # 원래 함수 실행
        result = f(*args, **kwargs)
        
        # 토큰 갱신이 필요하면 쿠키 설정
        if need_token_refresh:
            response = make_response(result)
            response.set_cookie('access_token', access_token, 
                                max_age=expires_in,
                                httponly=True, secure=False)
            # refresh_token이 있고 expires_in이 있을 때만 쿠키 설정
            if refresh_token and refresh_token_expires_in:
                response.set_cookie('refresh_token', refresh_token,
                                    max_age=refresh_token_expires_in,
                                    httponly=True, secure=False)
            return response
        
        return result
    
    return decorated

def refresh_access_token(refresh_token):
    if not refresh_token:
        return redirect(url_for('login_page'))
    
    body = {
        'grant_type': 'refresh_token',
        'client_id': cfg.KAKAO_CLIENT_ID,
        'client_secret': cfg.KAKAO_CLIENT_SECRET,
        'refresh_token': refresh_token
    }
    token_response = requests.post("https://kauth.kakao.com/oauth/token", data=body)
    token_json = token_response.json()

    if 'access_token' not in token_json:
        return redirect(url_for('login_page'))
    
   
    access_token = token_json['access_token']
    expires_in = token_json['expires_in']
    
    # 토큰 만료기한이 1개월 미만일 때 갱신
    if 'refresh_token' in token_json:
        refresh_token = token_json['refresh_token']
        refresh_token_expires_in = token_json['refresh_token_expires_in']
        return access_token, expires_in, refresh_token, refresh_token_expires_in
    else:
        # refresh_token이 없으면 기존 refresh_token 유지
        return access_token, expires_in, refresh_token, None

def get_user_info(access_token):
   user_info_url = "https://kapi.kakao.com/v2/user/me"
   user_response = requests.get(
       user_info_url,
       headers={'Authorization': f'Bearer {access_token}'}
   )

   user_info = user_response.json()   

   if 'id' not in user_info:
       return redirect(url_for('login_page'))
   
   return user_info
   
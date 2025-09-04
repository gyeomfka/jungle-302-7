from db import get_db
from utils.video_chat import create_study_confirmation_notification
from utils.notification import create_notification


def get_studies_by_tab(user_id, tab, search_keyword=None, category=None, is_closed=None):
    """탭에 따라 스터디 데이터를 조회합니다."""
    try:
        db = get_db()
        query = {}

        if tab == "all":
            # 전체 스터디
            query = {}
        elif tab == "my":
            # 나의 스터디 (host_id가 현재 사용자)
            query = {"host_id": user_id}
        elif tab == "applied":
            # 지원한 스터디
            # (confirmed_candidate, candidate의 user_id에 포함)
            query = {
                "$or": [
                    {"confirmed_candidate": user_id},
                    {"candidate.user_id": user_id},
                ]
            }

        if search_keyword:
            # 예: name, description 필드에서 검색
            query["$or"] = query.get("$or", []) + [
                {"name": {"$regex": search_keyword, "$options": "i"}},
                {"description": {"$regex": search_keyword, "$options": "i"}},
            ]
            
        if category:
            query["subject"] = category

        if is_closed:
            query["is_closed"] = str_to_bool(is_closed)

        studies = list(db.study.find(query).sort("_id", -1))

        # 각 스터디에 대한 지원 상태 정보 추가
        for study in studies:
            study['application_status'] = get_application_status(study, user_id)

        return studies

    except Exception as e:
        print(f"스터디 조회 오류: {e}")
        return []

def str_to_bool(value):
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)

def get_study_by_id(study_id):
    """스터디 ID로 특정 스터디를 조회합니다."""
    try:
        db = get_db()
        study = db.study.find_one({"id": study_id})
        return study

    except Exception as e:
        print(f"스터디 상세 조회 오류: {e}")
        return None


def apply_to_study(study_id, user_id, selected_dates):
    """스터디에 참여 신청합니다."""
    try:
        db = get_db()

        # 스터디 존재 확인
        study = db.study.find_one({"id": study_id})
        if not study:
            return False, "스터디를 찾을 수 없습니다."

        # 이미 신청했는지 확인
        already_applied = any(
            user_id in candidate.get("user_id", [])
            for candidate in study.get("candidate", [])
        )

        if already_applied:
            return False, "이미 신청한 스터디입니다."

        # 확정 참여자인지 확인
        if user_id in study.get("confirmed_candidate", []):
            return False, "이미 확정된 참여자입니다."

        # 마감된 스터디인지 확인
        if study.get('is_closed'):
            return False, "스터디가 이미 마감되었습니다."

        # 선택된 날짜들에 사용자 ID 추가
        for selected_date in selected_dates:
            db.study.update_one(
                {"id": study_id, "candidate.date": selected_date},
                {"$addToSet": {"candidate.$.user_id": user_id}},
            )

        return True, "스터디 참여 신청이 완료되었습니다."

    except Exception as e:
        print(f"스터디 신청 오류: {e}")
        return False, "신청 처리 중 오류가 발생했습니다."


def get_study_participants(study_id):
    """스터디 참가자 정보를 조회합니다."""
    try:
        db = get_db()

        study = db.study.find_one({"id": study_id})
        if not study:
            return None, None

        # 확정된 참가자 정보 조회
        confirmed_participants = []
        if study.get("confirmed_candidate"):
            confirmed_users = list(db.user.find(
                {"id": {"$in": study["confirmed_candidate"]}}
            ))
            confirmed_participants = confirmed_users

        # 대기 중인 지원자 정보 조회 (confirmed에 없는 사람들)
        pending_user_ids = set()
        for candidate in study.get("candidate", []):
            for user_id in candidate.get("user_id", []):
                if user_id not in study.get("confirmed_candidate", []):
                    pending_user_ids.add(user_id)

        pending_candidates = []
        if pending_user_ids:
            pending_users = list(db.user.find(
                {"id": {"$in": list(pending_user_ids)}}
            ))
            pending_candidates = pending_users

        return confirmed_participants, pending_candidates

    except Exception as e:
        print(f"참가자 정보 조회 오류: {e}")
        return [], []


def update_confirmed_candidates(study_id, confirmed_candidates, study_date=None):
    """스터디의 확정 참가자와 날짜를 업데이트합니다."""
    try:
        db = get_db()

        # 스터디 존재 확인
        study = db.study.find_one({"id": study_id})
        if not study:
            return False, "스터디를 찾을 수 없습니다."

        # 최대 참가자 수 확인
        if len(confirmed_candidates) > study.get("max_participants", 0):
            return False, "최대 참가자 수를 초과했습니다."

        # 업데이트할 데이터 준비
        update_data = {
            "confirmed_candidate": confirmed_candidates,
            "is_closed": True
        }

        # 스터디 날짜가 제공된 경우 추가
        if study_date:
            update_data["study_date"] = study_date

        # 확정 참가자 및 스터디 날짜 업데이트
        result = db.study.update_one(
            {"id": study_id},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            # 확정된 사용자들에게 알림 및 이메일 발송
            try:
                study_name = study.get("name", "스터디")
                final_date = study_date or study.get("study_date", "")

                if confirmed_candidates and final_date:
                    create_study_confirmation_notification(
                        confirmed_candidates,
                        study_name,
                        final_date
                    )
            except Exception as notification_error:
                print(f"알림 발송 오류 (스터디 확정은 완료됨): {notification_error}")

            return True, "참가자가 확정되었습니다."
        else:
            return False, "변경사항이 없습니다."

    except Exception as e:
        print(f"참가자 확정 오류: {e}")
        return False, "확정 처리 중 오류가 발생했습니다."



def withdraw_from_study(study_id, user_id):
    """스터디 지원을 철회합니다."""
    try:
        db = get_db()

        # 스터디 존재 확인
        study = db.study.find_one({"id": study_id})
        if not study:
            return False, "스터디를 찾을 수 없습니다."

        # 스터디가 이미 마감된 경우 철회 불가
        if study.get('is_closed'):
            return False, "이미 마감된 스터디에서는 철회할 수 없습니다."

        # confirmed_candidate에서 제거
        was_confirmed = user_id in study.get("confirmed_candidate", [])
        if was_confirmed:
            db.study.update_one(
                {"id": study_id},
                {"$pull": {"confirmed_candidate": user_id}}
            )

        # candidate에서 사용자 ID 제거
        withdrawn = False
        for candidate in study.get("candidate", []):
            if user_id in candidate.get("user_id", []):
                db.study.update_one(
                    {"id": study_id, "candidate.date": candidate["date"]},
                    {"$pull": {"candidate.$.user_id": user_id}}
                )
                withdrawn = True

        if not withdrawn and not was_confirmed:
            return False, "지원하지 않은 스터디입니다."

        # 호스트에게 알림 생성
        host_id = study.get("host_id")
        if host_id:
            # 사용자 정보 조회
            user = db.user.find_one({"id": user_id})
            user_name = user.get("name", "사용자") if user else "사용자"
            
            status_text = "확정 참가자" if was_confirmed else "지원자"
            message = f"{user_name}님이 '{study.get('name', '스터디')}'에서 {status_text} 철회했습니다."
            
            create_notification(host_id, message)

        return True, "지원이 철회되었습니다."

    except Exception as e:
        print(f"지원 철회 오류: {e}")
        return False, "철회 처리 중 오류가 발생했습니다."


def delete_study(study_id, user_id):
    """스터디를 삭제합니다. (호스트만 가능)"""
    try:
        db = get_db()

        # 스터디 존재 확인
        study = db.study.find_one({"id": study_id})
        if not study:
            return False, "스터디를 찾을 수 없습니다."

        # 호스트 권한 확인
        if study.get("host_id") != user_id:
            return False, "스터디를 삭제할 권한이 없습니다."

        # 이미 확정된 스터디는 삭제 불가
        if study.get('is_closed'):
            return False, "이미 확정된 스터디는 삭제할 수 없습니다."

        # 스터디 삭제
        result = db.study.delete_one({"id": study_id})
        
        if result.deleted_count > 0:
            return True, "스터디가 삭제되었습니다."
        else:
            return False, "스터디 삭제에 실패했습니다."

    except Exception as e:
        print(f"스터디 삭제 오류: {e}")
        return False, "삭제 처리 중 오류가 발생했습니다."


def get_application_status(study, user_id):
    """스터디에 대한 사용자의 지원 상태를 반환합니다."""
    # print(study)
    try:
        # 확정 참여자인 경우
        if user_id in study.get("confirmed_candidate", []):
            return "confirmed"  # 참여

        # 스터디가 마감된 경우
        if study.get("is_closed", False):
            return "closed"  # 다음 기회에

        # 지원했지만 아직 대기중인 경우
        for candidate in study.get("candidate", []):
            print(candidate.get("user_id", []))
            print(user_id)
            print(user_id in candidate.get("user_id", []))
            if user_id in candidate.get("user_id", []):
                return "pending"  # 대기중

        return "not_applied"  # 지원하지 않음

    except Exception as e:
        print(f"지원 상태 확인 오류: {e}")
        return "unknown"

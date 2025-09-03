from db import get_db


def get_studies_by_tab(user_id, tab):
    """탭에 따라 스터디 데이터를 조회합니다."""
    try:
        db = get_db()

        if tab == "all":
            # 전체 스터디
            studies = list(db.study.find({}))
        elif tab == "my":
            # 나의 스터디 (host_id가 현재 사용자)
            studies = list(db.study.find({"host_id": user_id}))
        elif tab == "applied":
            # 지원한 스터디 (confirmed_candidate, rejected_candidate, candidate의 user_id에 포함)
            studies = list(
                db.study.find(
                    {
                        "$or": [
                            {"confirmed_candidate": user_id},
                            {"rejected_candidate": user_id},
                            {
                                "candidate.user_id": user_id
                            },  # TODO: user_id가 리스트인데 잘 가지고 오는지 확인 필요
                        ]
                    }
                )
            )
        else:
            studies = []

        return studies

    except Exception as e:
        print(f"스터디 조회 오류: {e}")
        return []


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

        # 거절된 참여자인지 확인
        if user_id in study.get("rejected_candidate", []):
            return False, "참여가 거절된 스터디입니다."

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

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
                            {"candidate.user_id": user_id},
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

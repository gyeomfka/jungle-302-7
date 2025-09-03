from db import get_db
from bson import ObjectId
from datetime import datetime, timezone
from utils.send_mail import send_notification_email


def get_user_notifications(user_id):
    """사용자의 모든 알림을 가져옵니다."""
    try:
        db = get_db()
        notifications = list(db.notification.find(
            {"user_id": user_id}
        ).sort("_id", -1))  # 최신순으로 정렬

        return notifications

    except Exception as e:
        print(f"알림 조회 오류: {e}")
        return []


def get_unread_notification_count(user_id):
    """사용자의 읽지 않은 알림 개수를 반환합니다."""
    try:
        db = get_db()
        count = db.notification.count_documents({
            "user_id": user_id,
            "read": False
        })

        return count

    except Exception as e:
        print(f"읽지 않은 알림 개수 조회 오류: {e}")
        return 0


def mark_notification_as_read(notification_id, user_id):
    """특정 알림을 읽음 상태로 변경합니다."""
    try:
        db = get_db()

        # ObjectId 변환
        if isinstance(notification_id, str):
            notification_id = ObjectId(notification_id)

        result = db.notification.update_one(
            {
                "_id": notification_id,
                "user_id": user_id  # 보안: 해당 사용자의 알림만 수정 가능
            },
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.now(timezone.utc)
                }
            }
        )

        return result.modified_count > 0

    except Exception as e:
        print(f"알림 읽음 처리 오류: {e}")
        return False


def mark_all_notifications_as_read(user_id):
    """사용자의 모든 알림을 읽음 상태로 변경합니다."""
    try:
        db = get_db()

        result = db.notification.update_many(
            {
                "user_id": user_id,
                "read": False
            },
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.now(timezone.utc)
                }
            }
        )

        return result.modified_count

    except Exception as e:
        print(f"모든 알림 읽음 처리 오류: {e}")
        return 0



def create_notification(user_id, message, notification_type="general",
                        send_email=True):
    """새로운 알림을 생성합니다."""
    try:
        db = get_db()

        notification = {
            "id": str(ObjectId()),
            "user_id": user_id,
            "message": message,
            "type": notification_type,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        }

        # 알림을 데이터베이스에 저장
        result = db.notification.insert_one(notification)

        # 이메일 발송 (옵션)
        if send_email and result.inserted_id:
            try:
                # 사용자 정보 조회
                user = db.user.find_one({"id": user_id})
                if user and user.get("email"):
                    user_name = user.get("name", "사용자")
                    user_email = user.get("email")

                    # 이메일 발송
                    send_notification_email(user_email, user_name, message)

            except Exception as email_error:
                print(f"이메일 발송 오류 (알림은 정상 생성됨): {email_error}")

        return result.inserted_id is not None

    except Exception as e:
        print(f"알림 생성 오류: {e}")
        return False



def delete_notification(notification_id, user_id):
    """특정 알림을 삭제합니다."""
    try:
        db = get_db()

        # ObjectId 변환
        if isinstance(notification_id, str):
            notification_id = ObjectId(notification_id)

        result = db.notification.delete_one({
            "_id": notification_id,
            "user_id": user_id  # 보안: 해당 사용자의 알림만 삭제 가능
        })

        return result.deleted_count > 0

    except Exception as e:
        print(f"알림 삭제 오류: {e}")
        return False

from db import get_db
from bson import ObjectId
from datetime import datetime, timezone
from utils.send_mail import send_study_confirmation_email
import uuid

def create_study_confirmation_notification(confirmed_candidates, study_name, study_date, host_id=None):
    """스터디 확정 알림을 생성하고 확정 이메일을 발송합니다."""
    try:
        db = get_db()
        
        # 날짜 포맷팅
        if isinstance(study_date, str):
            try:
                date_obj = datetime.fromisoformat(study_date.replace('T', ' ').replace('Z', ''))
            except:
                date_obj = datetime.now()
        else:
            date_obj = study_date
            
        formatted_date = date_obj.strftime("%Y년 %m월 %d일 %H시 %M분")
        
        # 고유한 방 ID 생성
        room_id = str(uuid.uuid4())
        
        # 트랜잭션을 위한 성공/실패 추적
        successful_operations = []
        failed_operations = []
        
        try:
            # 1. video_chat 컬렉션에 방 정보 저장
            video_chat = {
                "id": room_id,
                "user_id": confirmed_candidates,
                "start_date": study_date,
            }
            
            video_chat_result = db.video_chat.insert_one(video_chat)
            if not video_chat_result.inserted_id:
                raise Exception("video_chat 생성 실패")
            
            successful_operations.append(('video_chat', video_chat_result.inserted_id))
            
            # 2. 각 확정된 사용자에게 알림 생성 및 이메일 발송
            for user_id in confirmed_candidates:
                try:
                    # 알림 메시지 생성
                    message = f"{study_name} 스터디 참여가 확정되었습니다. {formatted_date}에 화상 채팅으로 진행됩니다."
                    
                    # 알림 생성
                    notification = {
                        "id": str(ObjectId()),
                        "user_id": user_id,
                        "message": message,
                        "type": "study_confirmation",
                        "read": False,
                        "created_at": datetime.now(timezone.utc)
                    }
                    
                    notify_result = db.notification.insert_one(notification)
                    if not notify_result.inserted_id:
                        raise Exception(f"사용자 {user_id} 알림 생성 실패")
                    
                    successful_operations.append(('notification', notify_result.inserted_id))
                    
                    # 사용자 정보 조회
                    user = db.user.find_one({"id": user_id})
                    if user and user.get("email"):
                        user_name = user.get("name", "사용자")
                        user_email = user.get("email")
                        
                        # 미팅 링크 생성
                        meeting_link = f"/room/{room_id}/{user_id}"
                        
                        # 이메일 발송
                        email_sent = send_study_confirmation_email(
                            user_email, 
                            user_name, 
                            study_name, 
                            date_obj, 
                            meeting_link
                        )
                        
                        if not email_sent:
                            print(f"사용자 {user_id} ({user_email}) 이메일 발송 실패")
                            failed_operations.append(('email', user_id))
                        else:
                            successful_operations.append(('email', user_id))
                    else:
                        print(f"사용자 {user_id} 이메일 정보 없음")
                        failed_operations.append(('user_info', user_id))
                        
                except Exception as user_error:
                    print(f"사용자 {user_id} 처리 오류: {user_error}")
                    failed_operations.append(('user_process', user_id))
                    # 개별 사용자 실패시에도 다른 사용자들은 계속 처리
                    continue
            
            # 3. 호스트에게도 알림 생성 및 이메일 발송
            if host_id:
                try:
                    # 호스트용 알림 메시지 생성
                    host_message = f"{study_name} 스터디 참가자 확정이 완료되었습니다. {formatted_date}에 화상 채팅으로 진행됩니다."
                    
                    # 호스트 알림 생성
                    host_notification = {
                        "id": str(ObjectId()),
                        "user_id": host_id,
                        "message": host_message,
                        "type": "study_host_confirmation",
                        "read": False,
                        "created_at": datetime.now(timezone.utc)
                    }
                    
                    host_notify_result = db.notification.insert_one(host_notification)
                    if not host_notify_result.inserted_id:
                        raise Exception(f"호스트 {host_id} 알림 생성 실패")
                    
                    successful_operations.append(('host_notification', host_notify_result.inserted_id))
                    
                    # 호스트 정보 조회
                    host_user = db.user.find_one({"id": host_id})
                    if host_user and host_user.get("email"):
                        host_name = host_user.get("name", "호스트")
                        host_email = host_user.get("email")
                        
                        # 호스트용 미팅 링크 생성
                        host_meeting_link = f"/room/{room_id}/{host_id}"
                        
                        # 호스트에게 이메일 발송
                        host_email_sent = send_study_confirmation_email(
                            host_email, 
                            host_name, 
                            study_name, 
                            date_obj, 
                            host_meeting_link
                        )
                        
                        if not host_email_sent:
                            print(f"호스트 {host_id} ({host_email}) 이메일 발송 실패")
                            failed_operations.append(('host_email', host_id))
                        else:
                            successful_operations.append(('host_email', host_id))
                    else:
                        print(f"호스트 {host_id} 이메일 정보 없음")
                        failed_operations.append(('host_user_info', host_id))
                        
                except Exception as host_error:
                    print(f"호스트 {host_id} 처리 오류: {host_error}")
                    failed_operations.append(('host_process', host_id))
            
            # 결과 확인
            if failed_operations:
                print(f"일부 작업 실패: {failed_operations}")
                print(f"성공한 작업: {successful_operations}")
                
                # 중요한 작업(video_chat, notification, host_notification)이 실패한 경우 롤백 고려
                critical_failures = [op for op in failed_operations if op[0] in ['video_chat', 'notification', 'host_notification']]
                if critical_failures:
                    print(f"중요한 작업 실패 감지: {critical_failures}")
                    # 필요시 롤백 로직 추가 가능
                    return False
            
            print(f"스터디 확정 처리 완료 - 성공: {len(successful_operations)}, 실패: {len(failed_operations)}")
            return True
            
        except Exception as process_error:
            print(f"스터디 확정 처리 중 오류: {process_error}")
            
            # 롤백 - 생성된 데이터 삭제
            for operation_type, operation_id in successful_operations:
                try:
                    if operation_type == 'video_chat':
                        db.video_chat.delete_one({"_id": operation_id})
                    elif operation_type == 'notification':
                        db.notification.delete_one({"_id": operation_id})
                    elif operation_type == 'host_notification':
                        db.notification.delete_one({"_id": operation_id})
                except Exception as rollback_error:
                    print(f"롤백 오류 ({operation_type}, {operation_id}): {rollback_error}")
            
            return False
        
    except Exception as e:
        print(f"스터디 확정 알림 생성 오류: {e}")
        return False

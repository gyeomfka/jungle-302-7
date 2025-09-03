import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import get_config

cfg = get_config()


def send_study_confirmation_email(user_email, user_name, study_name,
                                  study_date, meeting_link):
    """스터디 참여 확정 이메일을 발송합니다."""
    user_email = 'quake7289@gmail.com'
    try:
        # Gmail SMTP 설정
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # 설정에서 Gmail 정보 가져오기
        sender_email = getattr(cfg, 'GMAIL_USER', None)
        sender_password = getattr(cfg, 'GMAIL_APP_PASSWORD', None)

        if not sender_email or not sender_password:
            print("Gmail 설정이 없습니다. GMAIL_USER와 "
                  "GMAIL_APP_PASSWORD를 설정해주세요.")
            return False

        # 날짜 포맷 변환
        if isinstance(study_date, str):
            try:
                date_obj = datetime.fromisoformat(
                    study_date.replace('T', ' ').replace('Z', '')
                )
            except ValueError:
                date_obj = datetime.now()
        else:
            date_obj = study_date

        formatted_date = date_obj.strftime("%Y년 %m월 %d일 %H시 %M분")

        # 이메일 내용 구성
        subject = f"[스터디 확정] {study_name} 참여가 확정되었습니다"

        body = f"""
안녕하세요 {user_name}님,

{study_name} 스터디 참여가 확정되었습니다.

📅 일정: {formatted_date}
🔗 화상 채팅 링크: {meeting_link}

위 일정에 맞춰 링크를 통해 화상 채팅 스터디에 참여해 주세요.

감사합니다.
        """

        # 이메일 메시지 생성
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = user_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain", "utf-8"))

        # SMTP 서버 연결 및 이메일 발송
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        text = message.as_string()
        server.sendmail(sender_email, user_email, text)
        server.quit()

        print(f"이메일 발송 성공: {user_email}")
        return True

    except Exception as e:
        print(f"이메일 발송 오류: {e}")
        return False


def send_notification_email(user_email, user_name, notification_message):
    """일반 알림 이메일을 발송합니다."""
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        sender_email = getattr(cfg, 'GMAIL_USER', None)
        sender_password = getattr(cfg, 'GMAIL_APP_PASSWORD', None)

        if not sender_email or not sender_password:
            print("Gmail 설정이 없습니다.")
            return False

        # 이메일 내용 구성
        subject = "[스터디 플랫폼] 새로운 알림이 있습니다"

        body = f"""
안녕하세요 {user_name}님,

새로운 알림이 도착했습니다:

{notification_message}

스터디 플랫폼에 로그인하여 자세한 내용을 확인해 주세요.

감사합니다.
        """

        # 이메일 메시지 생성
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = user_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain", "utf-8"))

        # SMTP 서버 연결 및 이메일 발송
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        text = message.as_string()
        server.sendmail(sender_email, user_email, text)
        server.quit()

        print(f"알림 이메일 발송 성공: {user_email}")
        return True

    except Exception as e:
        print(f"알림 이메일 발송 오류: {e}")
        return False

from datetime import datetime
from typing import Union

def to_datetime_str(dt_like: Union[str, datetime]) -> str:
    """
    '2025-09-19T01:08' → '2025-09-19 오전 01:08'
    '2025-09-19 13:08' → '2025-09-19 오후 01:08'
    '2025-09-19T01:08:30Z' / '+09:00' 등도 처리
    datetime 객체도 입력 가능
    """
    # 1) datetime이면 그대로 사용
    if isinstance(dt_like, datetime):
        dt = dt_like
    else:
        s = dt_like.strip()
        # 'Z'는 fromisoformat이 못 읽으므로 +00:00으로 교체
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"

        # 2) ISO 시도
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            # 3) 일반 포맷들 재시도
            tried = False
            for fmt in (
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(s, fmt)
                    tried = True
                    break
                except ValueError:
                    continue
            if not tried:
                raise ValueError(f"지원하지 않는 날짜 형식: {dt_like!r}")

    # 한국식 오전/오후 + 12시간제
    hour24 = dt.hour
    period = "오전" if hour24 < 12 else "오후"
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12

    date_part = dt.date().isoformat()  # YYYY-MM-DD
    time_part = f"{hour12:02d}:{dt.minute:02d}"

    return f"{date_part} {period} {time_part}"

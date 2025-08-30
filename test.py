from datetime import datetime, time
from dateutil.relativedelta import relativedelta

def get_last_month_range(ref: datetime = None):
    """
    傳回 (上個月第一天 00:00:00, 上個月最後一天 23:59:59)
    :param ref: 參考時間 (預設為現在)
    """
    if ref is None:
        ref = datetime.now()

    # 上個月第一天 00:00:00
    first_day_last_month = (ref.replace(day=1) - relativedelta(months=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # 上個月最後一天 23:59:59
    last_day_last_month = (ref.replace(day=1) - relativedelta(days=1)).replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    return first_day_last_month, last_day_last_month


# 範例
start, end = get_last_month_range()
print("上個月第一天:", start)
print("上個月最後一天:", end)

import datetime
import pytz

KYIV_TZ = pytz.timezone("Europe/Kyiv")
now_tz = datetime.datetime.now(KYIV_TZ)
now_naive = datetime.datetime.now()
now_utc = datetime.datetime.now(datetime.timezone.utc)

print(f"System Naive: {now_naive}")
print(f"UTC:          {now_utc}")
print(f"Kyiv TZ:      {now_tz}")

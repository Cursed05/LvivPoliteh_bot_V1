import requests
from bs4 import BeautifulSoup

url = "https://student.lpnu.ua/students_schedule"
params = {"studygroup_abbrname": "КБ-407", "semestr": "2", "semestrduration": "1"}
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, params=params, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "html.parser")

# Шукаємо блоки з чисельником/знаменником і їх класи
for el in soup.select(".stud_schedule"):
    blocks = el.select(".week_color")
    if len(blocks) >= 2:
        for b in blocks:
            print("ID:", b.get("id"), "| CLASS:", b.get("class"), "| STYLE:", b.get("style"))
            print("TEXT:", b.get_text(" ", strip=True)[:80])
            print("---")
        break

# Також шукаємо будь-який елемент з "chys" або "znam" в id/class
print("\n=== Пошук chys/znam ===")
for el in soup.find_all(True):
    cls = " ".join(el.get("class", []))
    eid = el.get("id", "")
    if "chys" in cls.lower() or "znam" in cls.lower() or "chys" in eid.lower() or "znam" in eid.lower():
        print(f"TAG:{el.name} ID:{eid} CLASS:{cls}")
        print("TEXT:", el.get_text(" ", strip=True)[:80])
        print("---")

import requests
from bs4 import BeautifulSoup

url = "https://student.lpnu.ua/students_schedule"
params = {"studygroup_abbrname": "КБ-401", "semestr": "2", "semestrduration": "1"}
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, params=params, headers=headers, timeout=10)
soup = BeautifulSoup(r.text, "html.parser")

# Знаходимо четвер
in_thursday = False
for element in soup.select(".view-content > *"):
    if element.name == "span" and "view-grouping-header" in element.get("class", []):
        day = element.text.strip()
        in_thursday = (day == "Чт")
        if in_thursday:
            print(f"=== ДЕНЬ: {day} ===")

    if in_thursday:
        if element.name == "h3":
            print(f"\n--- ПАРА: {element.text.strip()} ---")
        elif element.name == "div" and "stud_schedule" in element.get("class", []):
            print("HTML блоку:")
            print(str(element)[:1500])
            print()

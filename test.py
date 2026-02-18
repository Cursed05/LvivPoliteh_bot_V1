import requests
from bs4 import BeautifulSoup

url = "https://student.lpnu.ua/students_schedule"
params = {
    "studygroup_abbrname": "КБ-407",
    "semestr": "2",
    "semestrduration": "1"
}

headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, params=params, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

schedule = {}
current_day = None
pair_number = None

for element in soup.select(".view-content > *"):

    # День тижня
    if element.name == "span" and "view-grouping-header" in element.get("class", []):
        current_day = element.text.strip()
        schedule[current_day] = []

    # Номер пари
    elif element.name == "h3":
        pair_number = element.text.strip()

    # Блок заняття
    elif element.name == "div" and "stud_schedule" in element.get("class", []):

        subject_block = element.select_one(".group_content")

        if subject_block and current_day and pair_number:

            # Робимо копію блоку
            block_copy = BeautifulSoup(str(subject_block), "html.parser")

            # Видаляємо URL із тексту
            url_span = block_copy.select_one(".schedule_url_link")
            if url_span:
                url_span.extract()

            # Чистий текст
            text = block_copy.get_text("\n", strip=True)

            # Окремо беремо посилання
            link_tag = subject_block.select_one(".schedule_url_link a")
            lesson_url = None

            if link_tag and "href" in link_tag.attrs:
                lesson_url = link_tag["href"].strip()
                if "http" in lesson_url:
                    lesson_url = lesson_url[lesson_url.find("http"):]

            schedule[current_day].append({
                "pair": pair_number,
                "info": text,
                "url": lesson_url
            })

# Вивід
for day, lessons in schedule.items():
    print(f"\n=== {day} ===")
    for lesson in lessons:
        print(f"{lesson['pair']} пара")
        print(lesson["info"])
        if lesson["url"]:
            print("🔗", lesson["url"])
        print()

import asyncio
import time
import requests
from bs4 import BeautifulSoup
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import SCHEDULE_URL

_cache: dict = {}
CACHE_TTL = 3600


def _parse_schedule(group: str, semestr: int) -> dict:
    """Парсинг розкладу студентської групи."""
    params = {
        "studygroup_abbrname": group,
        "semestr": str(semestr),
        "semestrduration": "1",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(SCHEDULE_URL, params=params, headers=headers, timeout=10)
    return _parse_html(response.text)


def _parse_teacher_schedule(teacher_name: str, semestr: int) -> dict:
    """Парсинг розкладу викладача з staff.lpnu.ua."""
    teacher_url = "https://staff.lpnu.ua/lecturer_schedule"
    params = {
        "teachername": teacher_name,
        "semestr": str(semestr),
        "semestrduration": "1",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(teacher_url, params=params, headers=headers, timeout=10)
    return _parse_html(response.text)


def _parse_html(html: str) -> dict:
    """Спільний парсер HTML розкладу."""
    soup = BeautifulSoup(html, "html.parser")
    schedule = {}
    current_day = None
    pair_number = None

    for element in soup.select(".view-content > *"):
        if element.name == "span" and "view-grouping-header" in element.get("class", []):
            current_day = element.text.strip()
            schedule[current_day] = []

        elif element.name == "h3":
            pair_number = element.text.strip()

        elif element.name == "div" and "stud_schedule" in element.get("class", []):
            if not current_day or not pair_number:
                continue

            try:
                pair_num = int(pair_number.split()[0])
            except (ValueError, IndexError):
                pair_num = None

            def extract_lesson(block):
                if not block:
                    return None
                block_copy = BeautifulSoup(str(block), "html.parser")
                url_span = block_copy.select_one(".schedule_url_link")
                lesson_url = None
                if url_span:
                    link_tag = block.select_one(".schedule_url_link a")
                    if link_tag and "href" in link_tag.attrs:
                        raw = link_tag["href"].strip()
                        if "http" in raw:
                            lesson_url = raw[raw.find("http"):]
                    url_span.extract()
                text = block_copy.get_text("\n", strip=True)
                return {"info": text, "url": lesson_url}

            # Визначаємо тип блоку за id обгортки
            chys_wrapper = element.select_one("#group_chys")
            znam_wrapper = element.select_one("#group_znam")
            sub1_wrapper = element.select_one("#sub_1_full")
            sub2_wrapper = element.select_one("#sub_2_full")
            full_wrapper = element.select_one("#group_full")

            if chys_wrapper and znam_wrapper:
                # Чисельник / знаменник (вся група)
                chys_active = "week_color" in chys_wrapper.get("class", [])
                znam_active = "week_color" in znam_wrapper.get("class", [])
                num_data = extract_lesson(chys_wrapper.select_one(".group_content"))
                den_data = extract_lesson(znam_wrapper.select_one(".group_content"))
                if num_data:
                    num_data["is_active"] = chys_active
                if den_data:
                    den_data["is_active"] = znam_active
                if num_data or den_data:
                    schedule[current_day].append({
                        "pair": pair_number,
                        "pair_num": pair_num,
                        "type": "num_den",
                        "numerator": num_data,
                        "denominator": den_data,
                        "subgroup1": None,
                        "subgroup2": None,
                        "info": None,
                        "url": None,
                    })

            elif sub1_wrapper or sub2_wrapper:
                # Пари розбиті на підгрупи
                sub1_data = extract_lesson(sub1_wrapper.select_one(".group_content")) if sub1_wrapper else None
                sub2_data = extract_lesson(sub2_wrapper.select_one(".group_content")) if sub2_wrapper else None
                if sub1_data or sub2_data:
                    schedule[current_day].append({
                        "pair": pair_number,
                        "pair_num": pair_num,
                        "type": "subgroups",
                        "numerator": None,
                        "denominator": None,
                        "subgroup1": sub1_data,
                        "subgroup2": sub2_data,
                        "info": None,
                        "url": None,
                    })

            else:
                # Звичайна пара для всієї групи
                block = full_wrapper.select_one(".group_content") if full_wrapper else element.select_one(".group_content")
                data = extract_lesson(block)
                if data:
                    schedule[current_day].append({
                        "pair": pair_number,
                        "pair_num": pair_num,
                        "type": "full",
                        "numerator": None,
                        "denominator": None,
                        "subgroup1": None,
                        "subgroup2": None,
                        "info": data["info"],
                        "url": data["url"],
                    })

    return schedule


async def fetch_schedule(group: str, semestr: int) -> dict:
    key = ("student", group.strip().upper(), semestr)
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < CACHE_TTL:
            return data
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _parse_schedule, group, semestr)
    _cache[key] = (now, data)
    return data


async def fetch_teacher_schedule(teacher_name: str, semestr: int) -> dict:
    key = ("teacher", teacher_name.strip(), semestr)
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < CACHE_TTL:
            return data
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _parse_teacher_schedule, teacher_name, semestr)
    _cache[key] = (now, data)
    return data


def invalidate_cache(group: str = None, semestr: int = None):
    if group and semestr:
        for prefix in ("student", "teacher"):
            key = (prefix, group.strip().upper(), semestr)
            _cache.pop(key, None)
    else:
        _cache.clear()


def _parse_exam_schedule(group: str) -> list:
    """Парсинг розкладу екзаменів. Повертає список {date, pair, pair_num, info}."""
    url = "https://student.lpnu.ua/students_exam"
    params = {"studygroup_abbrname": group}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    exams = []
    current_date = None
    pair_number = None

    for element in soup.select(".view-content > *"):
        if element.name == "span" and "view-grouping-header" in element.get("class", []):
            current_date = element.text.strip()

        elif element.name == "h3":
            pair_number = element.text.strip()

        elif element.name == "div" and "stud_schedule" in element.get("class", []):
            if not current_date or not pair_number:
                continue
            block = element.select_one(".group_content")
            if not block:
                continue
            text = block.get_text("\n", strip=True)
            try:
                pair_num = int(pair_number.split()[0])
            except (ValueError, IndexError):
                pair_num = None
            exams.append({
                "date": current_date,
                "pair": pair_number,
                "pair_num": pair_num,
                "info": text,
            })

    return exams


async def fetch_exam_schedule(group: str) -> list:
    key = ("exam", group.strip().upper())
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < CACHE_TTL:
            return data
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _parse_exam_schedule, group)
    _cache[key] = (now, data)
    return data


def _parse_teacher_exam_schedule(teacher_name: str) -> list:
    """Парсинг розкладу екзаменів викладача з staff.lpnu.ua/lecturer_exam."""
    url = "https://staff.lpnu.ua/lecturer_exam"
    params = {"teachername": teacher_name}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    exams = []
    current_date = None
    pair_number = None

    for element in soup.select(".view-content > *"):
        if element.name == "span" and "view-grouping-header" in element.get("class", []):
            text = element.text.strip()
            if text:  # пропускаємо порожні <span>
                current_date = text

        elif element.name == "h3":
            pair_number = element.text.strip()

        elif element.name == "div" and "stud_schedule" in element.get("class", []):
            if not current_date or not pair_number:
                continue
            block = element.select_one(".group_content")
            if not block:
                continue
            text = block.get_text("\n", strip=True)
            try:
                pair_num = int(pair_number.split()[0])
            except (ValueError, IndexError):
                pair_num = None
            exams.append({
                "date": current_date,
                "pair": pair_number,
                "pair_num": pair_num,
                "info": text,
            })

    # Сортуємо за датою
    exams.sort(key=lambda x: x["date"])
    return exams


async def fetch_teacher_exam_schedule(teacher_name: str) -> list:
    key = ("teacher_exam", teacher_name.strip())
    now = time.time()
    if key in _cache:
        ts, data = _cache[key]
        if now - ts < CACHE_TTL:
            return data
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _parse_teacher_exam_schedule, teacher_name)
    _cache[key] = (now, data)
    return data

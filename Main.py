from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import tempfile
import time
import re

driver = None
trafficRanks = {"Low Traffic": [1, 25], "Moderate Traffic": [26, 75], "Heavy Traffic": [76, 150]}


def scrapeWaze(start: str, destination: str) -> list:
    global driver

    while True:
        if driver:
            driver.quit()

        options = Options()
        options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")

        driver = webdriver.Chrome(options=options)
        driver.get("https://www.waze.com/live-map")

        ok1 = select_suggestion_waze(start, "Choose starting point")
        ok2 = select_suggestion_waze(destination, "Choose destination")

        if ok1 != 0 and ok2 != 0:
            break

    remove_tooltips()
    bestRoute = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".wm-routes-item-desktop.is-active"))
    ).get_attribute("textContent").split(" ")[0] + " minArrive"

    distance = float(WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".wm-routes-item-desktop__footer"))
    ).get_attribute("textContent").split()[0])

    return [bestRoute, distance]


def scrapeOCTranspo(start: str, destination: str) -> int:
    driver.get("https://plan.octranspo.com/plan")

    select_suggestion_oc(start, "gh-StartLocationInput")
    select_suggestion_oc(destination, "gh-EndLocationInput")

    driver.find_element(By.ID, "ServiceModeTrainBtn").click()
    driver.find_element(By.CSS_SELECTOR, ".gh-RequestButton.gh-TravelPlansRequestButton").click()

    WebDriverWait(driver, 20).until(
        lambda d: (
            el := d.find_elements(By.CSS_SELECTOR, ".TravelPlanDuration")
        ) and el[0].get_attribute("textContent").strip() != " "
    )

    totalTime = int(re.findall(
        r"\d+", driver.find_element(By.CSS_SELECTOR, ".TravelPlanDuration").get_attribute("textContent")
    )[0])

    walkingTime = int(re.findall(
        r"\d+", driver.find_element(By.CSS_SELECTOR, ".TravelPlanWalkingDuration").get_attribute("textContent")
    )[0])

    return totalTime - walkingTime


def select_suggestion_waze(query: str, txtPlaceholder: str):
    loc_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{txtPlaceholder}']"))
    )

    remove_tooltips()

    loc_input.clear()
    loc_input.send_keys(query)

    time.sleep(1)

    suggestions = driver.find_elements(By.CSS_SELECTOR, ".wm-search-item")

    retries = 0
    while retries < 3:
        if any("Sign in to see your saved places" in s.get_attribute("textContent") for s in suggestions):
            time.sleep(0.5)
            suggestions = driver.find_elements(By.CSS_SELECTOR, ".wm-search-item")
            retries += 1
            continue
        break

    if len(suggestions) < 2:
        return 0

    try:
        time.sleep(0.5) 

        suggestions = driver.find_elements(By.CSS_SELECTOR, ".wm-search-item")
        el = suggestions[1]

        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        time.sleep(0.2)

        driver.execute_script("arguments[0].click();", el) 

    except:
        return 0

    old = {
        m.get_attribute("textContent") for m in driver.find_elements(By.CSS_SELECTOR, ".wm-marker-label__text")
        if m.get_attribute("textContent").strip()
    }

    try:
        new_marker_texts = WebDriverWait(driver, 10).until(
            lambda d: [
                m.get_attribute("textContent") for m in d.find_elements(By.CSS_SELECTOR, ".wm-marker-label__text")
                if m.get_attribute("textContent").strip() and m.get_attribute("textContent") not in old
            ] or False
        )

        if not any(query.lower() in t.lower() for t in new_marker_texts):
            return 0

    except:
        return 0

    return 1


def remove_tooltips():
    time.sleep(1)
    for button in driver.find_elements(By.CSS_SELECTOR, "[class*='waze-tooltip'] button"):
        try:
            button.click()
        except:
            pass


def select_suggestion_oc(query: str, inputID: str):
    loc_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, f"#{inputID} input"))
    )

    loc_input.clear()
    loc_input.send_keys(query)

    time.sleep(1)

    suggestions = WebDriverWait(driver, 10).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, ".ui-menu-item.gh-Suggestion")
    )

    if not suggestions:
        return

    suggestions = driver.find_elements(By.CSS_SELECTOR, ".ui-menu-item.gh-Suggestion")

    driver.execute_script("arguments[0].scrollIntoView(true);", suggestions[0])
    time.sleep(0.2)

    driver.execute_script("arguments[0].click();", suggestions[0])
    time.sleep(1)

    reconfirm = driver.find_elements(By.CSS_SELECTOR, ".DidYouMeanSuggestion")

    if reconfirm:
        driver.execute_script("arguments[0].click();", reconfirm[0])



def planTrip(start: str, destination: str) -> dict:
    trafficInfo = scrapeWaze(start, destination)
    transitTime = scrapeOCTranspo(start, destination)

    carTime = int(re.findall(r"\d+", trafficInfo[0])[0])
    percentage = 0 if carTime == 0 else round(((transitTime - carTime) / carTime) * 100, 2)

    trafficStatus = "Severe Traffic"
    for rank in trafficRanks:
        if trafficRanks[rank][0] <= percentage <= trafficRanks[rank][1]:
            trafficStatus = rank
            break

    return {
        "Best Route Info": trafficInfo[0],
        "Best Route Distance (km)": round(trafficInfo[1], 2),
        "OC Transpo Time": transitTime,
        "Traffic Status": trafficStatus
    }


print(planTrip("", "")) # Enter your from and to locations here respectively  
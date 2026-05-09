from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import re

"""
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-position=-2400,-2400")
"""

driver = webdriver.Chrome()
trafficRanks = {"Low Traffic": [1, 25], "Moderate Traffic": [26, 75], "Heavy Traffic": [76, 150]}

def scrapeWaze(start: str, destination: str) -> list:
    driver.get("https://www.waze.com/live-map")

    while select_suggestion_waze(start, "Choose starting point") == 0 or select_suggestion_waze(destination, "Choose destination") == 0:
        driver.get("https://www.waze.com/live-map")

    bestRoute = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wm-routes-item-desktop.is-active'))).text.split("\n")[1]
    distance = float(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wm-routes-item-desktop__footer'))).text.split()[0])
        
    return [bestRoute, distance]

def scrapeOCTranspo(start: str, destination: str) -> int:
    driver.get("https://plan.octranspo.com/plan")
    select_suggestion_oc(start, "gh-StartLocationInput")
    select_suggestion_oc(destination, "gh-EndLocationInput")

    disableButton = driver.find_element(By.ID, "ServiceModeTrainBtn")
    disableButton.click()

    submitButton = driver.find_element(By.CSS_SELECTOR, ".gh-RequestButton.gh-TravelPlansRequestButton")
    submitButton.click()

    totalTimeElement = WebDriverWait(driver, 10).until(lambda d: d.find_element(By.CSS_SELECTOR, ".TravelPlanDuration"))
    WebDriverWait(driver, 10).until(lambda d: totalTimeElement.text.strip() != "")
    totalTime = int(re.findall(r'\d+', totalTimeElement.text)[0])

    walkingTimeElement = WebDriverWait(driver, 10).until(lambda d: d.find_element(By.CSS_SELECTOR, ".TravelPlanWalkingDuration"))
    WebDriverWait(driver, 10).until(lambda d: walkingTimeElement.text.strip() != "")
    walkingTime = int(re.findall(r'\d+', walkingTimeElement.text)[0])

    drivingTime = totalTime - walkingTime

    return drivingTime

def select_suggestion_waze(query: str, txtPlaceholder: str):
    loc_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{txtPlaceholder}']")))

    remove_tooltips()
    loc_input.send_keys(query)

    suggestions = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".wm-search-item")))

    retries = 0
    while retries < 5:
        suggestions = driver.find_elements(By.CSS_SELECTOR, ".wm-search-item")
        if any(item.text == "Sign in to see your saved places" for item in suggestions):
            retries += 1
            time.sleep(2)
            continue

        break

    if len(suggestions) <= 1:
        return 0

    driver.execute_script("arguments[0].click();", suggestions[1])

    old = {m.text for m in driver.find_elements(By.CSS_SELECTOR, ".wm-marker-label__text") if m.text.strip()}
    try:
        new_marker_texts = WebDriverWait(driver, 100).until(lambda d: [m.text for m in d.find_elements(By.CSS_SELECTOR, ".wm-marker-label__text") if m.text.strip() and m.text not in old] or False)
        if not any(query in t for t in new_marker_texts):
            return 0
    except TimeoutException:
        return 0

    return 1

def remove_tooltips():
    time.sleep(3)
    tooltip_buttons = driver.find_elements(By.CSS_SELECTOR, "[class*='waze-tooltip'] button")
    for button in tooltip_buttons:
        button.click();

def select_suggestion_oc(query: str, inputID: str):
    loc_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{inputID} input")))
    loc_input.send_keys(query)

    loc_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, inputID)))

    suggestion = WebDriverWait(loc_input, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-menu-item.gh-Suggestion")))
    suggestion.click()

def planTrip(start: str, destination: str) -> dict:
    trafficInfo = scrapeWaze(start, destination)
    transitTime = scrapeOCTranspo(start, destination)

    idealTime = round(trafficInfo[1] / (50/60), 2)
    percentage = round(((transitTime - idealTime) / idealTime) * 10, 2)
    trafficStatus = "Severe Traffic"
    for rank in trafficRanks:
        if trafficRanks[rank][0] <= percentage <= trafficRanks[rank][1]:
            trafficStatus = rank
            break
    
    newDictionary = {"Best Route Info": trafficInfo[0], "Best Route Distance": trafficInfo[1] * 1.609, "OC Transpo Time": transitTime, "Traffic Status": trafficStatus}
    return newDictionary

print(planTrip("Parliament", "Billings Bridge"))
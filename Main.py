from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

"""
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-position=-2400,-2400")
"""

driver = webdriver.Chrome()

def scrapeWaze(start: str, destination: str) -> list:
    driver.get("https://www.waze.com/live-map?utm_source=waze_website&utm_campaign=waze_website&utm_medium=website_menu")

    select_suggestion_waze(start, "Choose starting point")
    select_suggestion_waze(destination, "Choose destination")

    element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wm-routes.multiple-routes')))
    descendants = element.find_elements(By.XPATH, ".//*")
    bestRoute = ""
    for descendant in descendants:
        if descendant.get_attribute("class") == "wm-routes-item-desktop is-active":
            bestRoute = descendant.text.split("\n")[1]
            break

    distanceText = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.wm-routes-item-desktop__footer'))).text
    distance = float(distanceText.split()[0])
        
    return [bestRoute, distance]

def scrapeOCTranspo(start: str, destination: str) -> int:
    driver.get("https://plan.octranspo.com/plan")
    select_suggestion_oc(start, "gh-StartLocationInput")
    select_suggestion_oc(destination, "gh-EndLocationInput")

    disableButton = driver.find_element(By.ID, "ServiceModeTrainBtn")
    disableButton.click()

    submitButton = driver.find_element(By.CSS_SELECTOR, ".gh-RequestButton.gh-TravelPlansRequestButton")
    submitButton.click()

    time.sleep(5)

    timeText = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".TravelPlanHeader"))).text
    timeInfo = timeText.split("\n")
    
    while True:
        timeText = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".TravelPlanHeader"))).text
        timeInfo = timeText.split("\n")
        if len(timeInfo) > 1:
            break

    totalTime = int(timeInfo[1].split()[0])
    walkingTime = int(timeInfo[2].split()[1])
    drivingTime = totalTime - walkingTime

    return drivingTime


def select_suggestion_waze(query: str, txtPlaceholder: str):
    loc_input = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.XPATH, f"//input[@placeholder='{txtPlaceholder}']")))
    loc_input.send_keys(query)

    time.sleep(5)

    suggestions_element = driver.find_elements(By.CSS_SELECTOR, "#search-suggestions > div")
    suggestions = []

    for suggestion in suggestions_element:
        suggestions = suggestion.text.split("\n")

    flag = True
    while flag:
        flag = False
        for suggestion in suggestions:
            if suggestion == "Sign in to see your saved places":
                flag = True
                suggestions_element = driver.find_elements(By.CSS_SELECTOR, "#search-suggestions > div")
                for suggestion in suggestions_element:
                    suggestions = suggestion.text.split("\n")
                time.sleep(1)

    for suggestion in suggestions_element:
        descendants = suggestion.find_elements(By.XPATH, ".//*")
        for descendant in descendants:
            if descendant.get_attribute("class") == "wm-search-item":
                descendant.click()
                break

def select_suggestion_oc(query: str, inputID: str):
    loc_input = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{inputID} input")))
    loc_input.send_keys(query)

    time.sleep(1)

    loc_input = driver.find_element(By.ID, inputID)
    elements = loc_input.find_elements(By.XPATH, ".//*")
    for element in elements:
        if element.get_attribute("class") == "ui-menu-item gh-Suggestion":
            element.click()
            break

trafficRanks = {"Low Traffic": [1, 25], "Moderate Traffic": [26, 75], "Heavy Traffic": [76, 150]}

def planTrip(start: str, destination: str) -> dict:
    trafficInfo = scrapeWaze(start, destination)
    transitTime = scrapeOCTranspo(start, destination)

    idealTime = round(trafficInfo[1] / (50/60), 2)
    percentage = round(((transitTime - idealTime) / idealTime) * 100, 2)
    trafficStatus = "Severe Traffic"
    for rank in trafficRanks:
        if trafficRanks[rank][0] <= percentage <= trafficRanks[rank][1]:
            trafficStatus = rank
            break
    
    newDictionary = {"Best Route Info": trafficInfo[0], "Best Route Distance": trafficInfo[1] * 1.609, "OC Transpo Time": transitTime, "Traffic Status": trafficStatus}
    return newDictionary

print(planTrip("Parliament", "Billings Bridge"))
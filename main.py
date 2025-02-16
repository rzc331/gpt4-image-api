import json
import os
import time

import undetected_chromedriver as uc
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

options = uc.ChromeOptions()
options.headless = False
driver = uc.Chrome(options=options)
app = FastAPI()

ANSWER_FORMAT = "Answer ONLY by JSON following this format: " '{"answer": your answer in one paragraph}'
PORT_NUMBER = 8000
WAIT_TIME = 1


class Payload(BaseModel):
    prompt: str
    image_path: str = "None"
    new_chat: bool = True
    answer_format: str = ANSWER_FORMAT


@app.get("/start")
async def start_session():
    driver.get("https://chat.openai.com/")
    # time.sleep(WAIT_TIME)

    login_button = driver.find_element(By.XPATH, '//div[text()="Log in"]')
    login_button.click()
    time.sleep(WAIT_TIME)

    google = driver.find_element(By.XPATH, '//button[@data-provider="google"]')
    google.click()
    time.sleep(WAIT_TIME)

    # find email field
    email = driver.find_element(By.XPATH, '//input[@type="email"]')
    email.send_keys(os.getenv("GOOGLE_EMAIL"))
    # Find next button
    next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
    next_button.click()
    time.sleep(WAIT_TIME*2)

    # Find password field
    password = driver.find_element(By.XPATH, '//input[@type="password"]')
    password.send_keys(os.getenv("GOOGLE_PASSWORD"))
    # Find next button
    next_button = driver.find_element(By.XPATH, '//span[text()="Next"]')
    next_button.click()
    time.sleep(WAIT_TIME*2)

    # Wait for user to validate login
    input("Press Enter to continue...")

    # Find the Okay, let’s go button
    okay_button = driver.find_element(By.XPATH, '//div[text()="Okay, let’s go"]')
    okay_button.click()
    # Setup OK
    return {"status": "Selenium session started!"}


@app.post("/action/")
async def perform_action(payload: Payload):
    try:
        # Use the local path directly
        image_filename = payload.image_path

        # open new chat
        if payload.new_chat:
            driver.get("https://chat.openai.com/?model=gpt-4")
            time.sleep(WAIT_TIME * 2)

        # Make the input file element visible
        driver.execute_script(
            'document.querySelector(\'input[type="file"]\').style.display = "block";'
        )
        # Send the local path of the downloaded image to the file input element
        upload = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')

        # upload image
        if image_filename != "None":
            upload.send_keys(os.path.abspath(image_filename))
        
        # else, remove the previously uploaded image from the next input
        else:
            driver.execute_script("arguments[0].value = '';", upload)

        # Find prompt text area
        prompt = driver.find_element(By.XPATH, '//textarea[@id="prompt-textarea"]')
        prompt.send_keys(payload.prompt + '\n' + payload.answer_format)

        # Find the submit button data-testid="send-button
        submit_button = driver.find_element(
            By.XPATH, '//button[@data-testid="send-button"]'
        )
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(submit_button))
        prompt.send_keys(Keys.ENTER)
        time.sleep(WAIT_TIME*2)

        # Wait the result
        regen_btn = (By.XPATH, "//div[contains(text(), 'Regenerate')]")
        WebDriverWait(driver, 120).until(EC.presence_of_element_located(regen_btn))

        # Get response
        code_elements = driver.find_elements(By.TAG_NAME, "code")

        answer = code_elements[-1].text.strip() if code_elements else None
        if not answer:
            answer_elements = driver.find_elements(
                By.CSS_SELECTOR, ".markdown.prose.w-full.break-words"
            )
            answer = answer_elements[-1].text.strip()

        final_resp = {"status": "Success", "result": {}}
        if answer:
            final_resp["result"] = json.loads(answer)

        return final_resp

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stop")
async def stop_session():
    driver.quit()
    return {"status": "Selenium session closed!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT_NUMBER)

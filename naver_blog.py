import time
import pyperclip
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import NAVER_ID, NAVER_PW, BLOG_ID, CHROME_PROFILE_DIR


class NaverBlogPoster:
    def __init__(self):
        self.driver = None

    def _create_driver(self):
        options = Options()
        options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        # headless 모드 (서버 배포 시)
        # options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        return driver

    def login(self):
        """네이버 로그인 (pyperclip 붙여넣기 방식으로 캡챠 우회)"""
        self.driver = self._create_driver()
        self.driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)

        # 이미 로그인 상태인지 확인
        if "nid.naver.com" not in self.driver.current_url:
            return True

        try:
            id_input = self.driver.find_element(By.ID, "id")
            id_input.click()
            pyperclip.copy(NAVER_ID)
            id_input.send_keys(Keys.COMMAND, "v")  # macOS
            time.sleep(0.5)

            pw_input = self.driver.find_element(By.ID, "pw")
            pw_input.click()
            pyperclip.copy(NAVER_PW)
            pw_input.send_keys(Keys.COMMAND, "v")  # macOS
            time.sleep(0.5)

            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            time.sleep(3)

            # 로그인 성공 여부 확인
            if "nid.naver.com" in self.driver.current_url:
                raise Exception("로그인 실패 - 캡챠 또는 2단계 인증 확인 필요")

            return True
        except Exception as e:
            raise Exception(f"로그인 실패: {e}")

    def get_categories(self) -> list[dict]:
        """블로그 카테고리 목록 조회"""
        self.driver.get(f"https://blog.naver.com/{BLOG_ID}/postwrite")
        time.sleep(3)

        # iframe 전환
        self.driver.switch_to.frame("mainFrame")
        time.sleep(1)

        categories = []
        try:
            # 카테고리 select 요소 찾기
            cat_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".blog2_category"))
            )
            cat_btn.click()
            time.sleep(1)

            cat_items = self.driver.find_elements(By.CSS_SELECTOR, ".blog2_category .item")
            for item in cat_items:
                categories.append({
                    "name": item.text.strip(),
                    "value": item.get_attribute("data-categoryno") or item.text.strip(),
                })
            cat_btn.click()  # 닫기
        except Exception:
            pass

        self.driver.switch_to.default_content()
        return categories

    def post(self, title: str, content: str, category: str = "",
             tags: list[str] = None, image_paths: list[str] = None) -> bool:
        """네이버 블로그에 글 발행"""
        try:
            # 글쓰기 페이지 이동
            self.driver.get(f"https://blog.naver.com/{BLOG_ID}/postwrite")
            time.sleep(3)

            # mainFrame iframe 전환
            self.driver.switch_to.frame("mainFrame")
            time.sleep(2)

            # 1. 카테고리 선택
            if category:
                self._select_category(category)

            # 2. 제목 입력
            self._input_title(title)

            # 3. 사진 첨부
            if image_paths:
                self._upload_images(image_paths)

            # 4. 본문 입력
            self._input_content(content)

            # 5. 태그 입력
            if tags:
                self._input_tags(tags)

            # 6. 발행
            self._publish()

            self.driver.switch_to.default_content()
            return True

        except Exception as e:
            self.driver.switch_to.default_content()
            raise Exception(f"포스팅 실패: {e}")

    def _select_category(self, category_name: str):
        try:
            cat_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".blog2_category"))
            )
            cat_btn.click()
            time.sleep(1)

            cat_items = self.driver.find_elements(By.CSS_SELECTOR, ".blog2_category .item")
            for item in cat_items:
                if category_name in item.text:
                    item.click()
                    break
            time.sleep(0.5)
        except Exception:
            pass  # 카테고리 선택 실패 시 기본 카테고리로 진행

    def _input_title(self, title: str):
        title_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-title-text .se-text-paragraph"))
        )
        title_area.click()
        time.sleep(0.3)
        pyperclip.copy(title)
        title_area.send_keys(Keys.COMMAND, "v")
        time.sleep(0.5)

    def _input_content(self, content: str):
        # 본문 영역 클릭
        content_area = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".se-component-content .se-text-paragraph"))
        )
        content_area.click()
        time.sleep(0.3)

        # 줄바꿈 처리하여 붙여넣기
        pyperclip.copy(content)
        content_area.send_keys(Keys.COMMAND, "v")
        time.sleep(0.5)

    def _upload_images(self, image_paths: list[str]):
        """이미지 업로드"""
        try:
            # 사진 버튼 클릭
            photo_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".se-toolbar-item-image"))
            )
            photo_btn.click()
            time.sleep(1)

            # 파일 input에 파일 경로 전달
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_paths_str = "\n".join(
                str(Path(p).resolve()) for p in image_paths if Path(p).exists()
            )
            if file_paths_str:
                file_input.send_keys(file_paths_str)
                time.sleep(3)  # 업로드 대기
        except Exception:
            pass  # 이미지 업로드 실패 시 텍스트만 발행

    def _input_tags(self, tags: list[str]):
        try:
            tag_input = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".tag input, #post-tag"))
            )
            for tag in tags:
                tag_input.send_keys(tag)
                tag_input.send_keys(Keys.ENTER)
                time.sleep(0.3)
        except Exception:
            pass

    def _publish(self):
        """발행 버튼 클릭"""
        publish_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".publish_btn__Y5mLP, #publish-btn"))
        )
        publish_btn.click()
        time.sleep(2)

        # 확인 버튼이 있으면 클릭
        try:
            confirm_btn = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".confirm_btn, .btn_ok"))
            )
            confirm_btn.click()
            time.sleep(2)
        except Exception:
            pass

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

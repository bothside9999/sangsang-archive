import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import math
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import gspread
import io
from pathlib import Path
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_agraph import agraph, Node, Edge, Config

# -----------------------------------------------------------------------------
# 1. Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="업무 아카이빙 시스템",
    page_icon="📂",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Custom CSS (Google Gemini Style - Minimal & High Contrast)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

    /* Global Settings */
    :root {
        --font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
        --primary-color: #1A73E8; /* Google Blue */
        --bg-color-light: #FFFFFF;
        --text-color-light: #333333;
        --subtext-color-light: #5F6368;
        --border-color-light: #E0E0E0;
        --input-bg-light: #F1F3F4;
        
        --bg-color-dark: #0E1117;
        --text-color-dark: #E8EAED;
        --subtext-color-dark: #9AA0A6;
        --border-color-dark: #3C4043;
        --input-bg-dark: #202124;
    }

    html, body, [class*="css"] {
        font-family: var(--font-family) !important;
        line-height: 1.6;
    }

    /* Light Mode (Default) */
    .stApp {
        background-color: var(--bg-color-light);
        color: var(--text-color-light);
    }
    
    /* Dark Mode Override */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background-color: var(--bg-color-dark);
            color: var(--text-color-dark);
        }
    }

    /* Typography */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        margin-bottom: 1rem;
    }
    h1 { font-size: 2.2rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }

    /* Inputs (Flat & Minimal) */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background-color: var(--input-bg-light);
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 10px 12px;
        color: var(--text-color-light);
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus, 
    .stTextArea > div > div > textarea:focus {
        background-color: #FFFFFF;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
    }
    
    @media (prefers-color-scheme: dark) {
        .stTextInput > div > div > input, 
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div {
            background-color: var(--input-bg-dark);
            color: var(--text-color-dark);
        }
        .stTextInput > div > div > input:focus, 
        .stTextArea > div > div > textarea:focus {
            background-color: #171717;
        }
    }

    /* Buttons (Pill Shape) */
    .stButton > button {
        border-radius: 9999px !important; /* Pill shape */
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: none !important;
        transition: transform 0.1s, background-color 0.2s;
    }
    /* Primary Button */
    .stButton > button[kind="primary"] {
        background-color: var(--text-color-light) !important;
        color: #FFFFFF !important;
    }
    @media (prefers-color-scheme: dark) {
        .stButton > button[kind="primary"] {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
    }
    /* Secondary Button */
    .stButton > button[kind="secondary"] {
        background-color: var(--input-bg-light) !important;
        color: var(--text-color-light) !important;
    }
    @media (prefers-color-scheme: dark) {
        .stButton > button[kind="secondary"] {
            background-color: var(--input-bg-dark) !important;
            color: var(--text-color-dark) !important;
        }
    }

    /* Cards (Gemini Style) */
    .post-card {
        background-color: var(--bg-color-light);
        border: 1px solid var(--border-color-light);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: box-shadow 0.2s ease;
    }
    .post-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        border-color: transparent;
    }
    
    @media (prefers-color-scheme: dark) {
        .post-card {
            background-color: var(--bg-color-dark);
            border: 1px solid var(--border-color-dark);
        }
        .post-card:hover {
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            border-color: var(--subtext-color-dark);
        }
    }

    /* Tags */
    .meta-tag {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 8px;
        background-color: var(--input-bg-light);
        color: var(--text-color-light);
    }
    @media (prefers-color-scheme: dark) {
        .meta-tag {
            background-color: var(--input-bg-dark);
            color: var(--text-color-dark);
        }
    }
</style>
""", unsafe_allow_html=True)

# 캐시 강제 초기화 (설정 변경 적용을 위해)
# st.cache_resource.clear() # 속도 향상을 위해 주석 처리
# st.cache_data.clear() # 속도 향상을 위해 주석 처리

# 구글 시트 및 드라이브 설정
# 구글 시트 및 드라이브 설정
# 1. Load Secrets securely
if "general" in st.secrets and "target_sheet_id" in st.secrets["general"]:
    TARGET_SHEET_ID = st.secrets["general"]["target_sheet_id"]
    SHEET_URL = f"https://docs.google.com/spreadsheets/d/{TARGET_SHEET_ID}"
    DRIVE_FOLDER_ID = st.secrets["general"].get("drive_folder_id", "")
else:
    st.error("🚨 필수 설정(Sheet ID 등)이 .streamlit/secrets.toml 파일에 없습니다.")
    st.stop()


# 1. app.py 파일이 위치한 폴더 경로 구하기 (pathlib 사용)
BASE_DIR = Path(__file__).parent.absolute()

# 2. secrets.json 경로 설정
SECRETS_PATH = BASE_DIR / "secrets.json"
IMAGE_DIR = BASE_DIR / "images"

# 디버깅: 경로 정보 출력 (문제가 해결되면 삭제 가능)


if not IMAGE_DIR.exists():
    IMAGE_DIR.mkdir(exist_ok=True)
    
# 문자열로 변환 (라이브러리 호환성 위해)
SECRETS_PATH = str(SECRETS_PATH)
IMAGE_DIR = str(IMAGE_DIR)

import extra_streamlit_components as stx
import time

# -----------------------------------------------------------------------------
# Authentication Logic
# -----------------------------------------------------------------------------

def get_manager():
    # 쿠키 매니저 초기화 (새로운 키 사용으로 캐시 충돌 방지)
    return stx.CookieManager(key="auth_manager")

def load_auth_config():
    """
    Load authentication configuration from st.secrets.
    """
    # 기본값 설정 (Secrets 로드 실패 시 대비, 그러나 실제론 Secrets가 우선)
    config = {
        "users": [],
        "password": None
    }

    try:
        if "general" in st.secrets:
            # Load password
            if "app_password" in st.secrets["general"]:
                config["password"] = st.secrets["general"]["app_password"]
            
            # Load allowed users
            if "allowed_users" in st.secrets["general"]:
                config["users"] = st.secrets["general"]["allowed_users"]
            
    except (FileNotFoundError, KeyError, AttributeError):
        pass
        
    return config

# Load configuration
auth_config = load_auth_config()
ALLOWED_USERS = auth_config["users"]
APP_PASSWORD = auth_config["password"]

def check_login(username, password):
    # 비밀번호 설정이 안 되어 있으면 로그인 차단
    if not APP_PASSWORD:
        st.error("🚨 시스템 설정 오류: 보안 설정(Secrets)이 로드되지 않았습니다.")
        return False
        
    if username in ALLOWED_USERS and password == APP_PASSWORD:
        return True
    return False



def login_page(cookie_manager):
    # 이미 로그인 상태라면 패스 (main에서 처리했으므로 여기선 이중 체크 불필요)
    if st.session_state.logged_in:
        return

    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🔒 상상이룸 업무 아카이브 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>지역명(ID)을 선택하고 비밀번호를 입력해주세요.</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            # Change text_input to selectbox for User ID
            username = st.selectbox("아이디 (지역명)", options=ALLOWED_USERS)
            password = st.text_input("비밀번호", type="password")
            submit = st.form_submit_button("로그인", use_container_width=True)
            
            if submit:
                if check_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    
                    # 쿠키 저장 (7일 유지, UTC 기준)
                    cookie_manager.set("sangsang_user", username, expires_at=datetime.utcnow() + timedelta(days=7))
                    
                    st.success(f"환영합니다, {username}님!")
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")

# 세션 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'list'
if 'selected_post_id' not in st.session_state:
    st.session_state.selected_post_id = None
if 'username' not in st.session_state:
    st.session_state.username = "Guest"

# -----------------------------------------------------------------------------
# 2. Helper Functions (Google API & Utils)
# -----------------------------------------------------------------------------

@st.cache_resource
def connect_to_sheets():
    """
    Google Sheets 인증: st.secrets 우선 확인 후 secrets.json 파일 확인
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    
    # 1. Streamlit Secrets (배포 환경) 확인
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            return gspread.authorize(creds)
    except (FileNotFoundError, KeyError, AttributeError):
        pass # 로컬 환경이므로 무시하고 진행

    # 2. 로컬 파일 (개발 환경) 확인
    try:
        if os.path.exists(SECRETS_PATH):
            creds = Credentials.from_service_account_file(SECRETS_PATH, scopes=scope)
            return gspread.authorize(creds)
            
        st.error("🚨 인증 정보를 찾을 수 없습니다. (secrets.json 또는 st.secrets)")
        return None
    except Exception as e:
        st.error(f"구글 시트 연결 오류: {e}")
        return None

@st.cache_resource
def connect_to_drive():
    """
    Google Drive 인증: st.secrets 우선 확인 후 secrets.json 파일 확인
    """
    scope = ["https://www.googleapis.com/auth/drive"]
    
    # 1. Streamlit Secrets (배포 환경) 확인
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            return build('drive', 'v3', credentials=creds)
    except (FileNotFoundError, KeyError, AttributeError):
        pass # 로컬 환경이므로 무시하고 진행

    # 2. 로컬 파일 (개발 환경) 확인
    try:
        if os.path.exists(SECRETS_PATH):
            creds = Credentials.from_service_account_file(SECRETS_PATH, scopes=scope)
            return build('drive', 'v3', credentials=creds)
            
        return None
    except Exception as e:
        st.error(f"Drive API 연결 오류: {e}")
        return None

def sanitize_filename(name):
    return "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()

def upload_secure_file(file_obj):
    """
    보안 파일 업로드: 권한 변경 없이 파일 ID와 이름만 반환
    """
    service = connect_to_drive()
    if not service: return None
    
    try:
        safe_name = sanitize_filename(file_obj.name)
        file_metadata = {'name': safe_name, 'parents': [DRIVE_FOLDER_ID]}
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        
        # supportsAllDrives=True: 공유 드라이브 지원
        file = service.files().create(body=file_metadata, media_body=media, fields='id, name', supportsAllDrives=True).execute()
        
        return {"id": file.get('id'), "name": file.get('name')}
    except Exception as e:
        st.error(f"파일 업로드 실패: {e}")
        return None

def download_file_from_drive(file_id):
    """
    파일 다운로드: Drive API를 통해 바이너리 데이터 가져오기
    """
    service = connect_to_drive()
    if not service: return None
    
    try:
        return service.files().get_media(fileId=file_id).execute()
    except Exception as e:
        st.error(f"파일 다운로드 실패: {e}")
        return None

def delete_file_from_drive(file_id):
    """
    구글 드라이브에서 파일 삭제 (권한 문제를 피하기 위해 휴지통으로 이동)
    """
    service = connect_to_drive()
    if not service: return False
    
    try:
        # 영구 삭제 대신 휴지통으로 보냄 (공유 드라이브 권한 문제 해결)
        service.files().update(
            fileId=file_id, 
            body={'trashed': True}, 
            supportsAllDrives=True
        ).execute()
        return True
    except Exception as e:
        st.error(f"드라이브 파일 삭제 실패: {e}")
        return False

# -----------------------------------------------------------------------------
# 3. Data Handling (CRUD)
# -----------------------------------------------------------------------------

# 컬럼 정의 (순서 중요)
# 1. 작성일, 2. 작성자, 3. 제목, 4. 내용, 5. 파일링크, 6. 연관글ID, 7. 이미지경로, 8. 학년도, 9. 업무시기, 10. 태그
EXPECTED_COLS = ['작성일', '작성자', '제목', '내용', '파일링크', '연관글ID', '이미지경로', '학년도', '업무시기', '태그']

@st.cache_data(ttl=600)
def fetch_sheet_data():
    # 기본 빈 프레임
    empty_df = pd.DataFrame(columns=EXPECTED_COLS)
    
    client = connect_to_sheets()
    if not client: return empty_df
    
    # ID 공백 제거 (안전장치)
    clean_sheet_id = TARGET_SHEET_ID.strip()
    
    if not clean_sheet_id:
        st.warning("⚠️ app.py 파일 상단의 `TARGET_SHEET_ID` 변수를 확인해주세요.")
        return empty_df

    try:
        # 1차 시도: ID로 열기 + get_worksheet(0) 사용
        try:
            doc = client.open_by_key(clean_sheet_id)
            sheet = doc.get_worksheet(0) # 첫 번째 시트 명시적 호출
        except Exception:
            # 2차 시도: URL로 열기 (Fallback)
            doc = client.open_by_url(SHEET_URL)
            sheet = doc.get_worksheet(0)
            
        all_values = sheet.get_all_values()
        
        # 1. 데이터가 아예 없는 경우 (헤더 복구)
        if not all_values:
            sheet.append_row(EXPECTED_COLS)
            return empty_df

        # 2. 첫 번째 줄이 헤더가 아닌 경우 (데이터가 1행부터 시작하는 경우)
        # 간단한 검증: 첫 번째 컬럼이 '작성일'인지 확인
        first_row = all_values[0]
        is_header_valid = False
        if len(first_row) >= len(EXPECTED_COLS):
             # 컬럼명이 대략 맞는지 확인
             if str(first_row[0]).strip() == "작성일":
                 is_header_valid = True
        
        if not is_header_valid:
            # 헤더 강제 삽입 (1행에)
            sheet.insert_row(EXPECTED_COLS, index=1)
            # 데이터 다시 로드
            all_values = sheet.get_all_values()
            
        # 3. 헤더만 있고 데이터는 없는 경우
        if len(all_values) < 2:
             return empty_df

        headers = all_values[0]
        data = all_values[1:]
        
        # 시트 데이터로 DataFrame 생성
        df_sheet = pd.DataFrame(data, columns=headers)
        
        # 최종 DataFrame (순서 및 컬럼 강제)
        df_final = pd.DataFrame(columns=EXPECTED_COLS)
        
        # 데이터 매핑 (앱 내부적으로만 처리, 시트 원본은 건드리지 않음)
        for col in EXPECTED_COLS:
            if col in df_sheet.columns:
                df_final[col] = df_sheet[col]
            else:
                # 시트에 없는 컬럼은 빈 값으로 채워서 에러 방지
                df_final[col] = ""
                
        return df_final
    except Exception as e:
        st.error(f"데이터 불러오기 실패: {e}")
        return empty_df

def append_data(row_data):
    client = connect_to_sheets()
    if not client or not SHEET_URL: return False

    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        sheet.append_row(row_data)
        fetch_sheet_data.clear()
        return True
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")
        return False

def delete_post(title):
    client = connect_to_sheets()
    if not client or not SHEET_URL: return False

    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        cell = sheet.find(str(title))
        
        # 헤더(1행) 삭제 방지
        if cell.row <= 1:
            st.error("삭제할 수 없는 항목입니다.")
            return False

        # 삭제 전 첨부파일 정보 확인 및 삭제
        row_values = sheet.row_values(cell.row)
        # 파일링크는 5번째 컬럼 (인덱스 4)
        if len(row_values) > 4:
            file_link_json = row_values[4]
            if file_link_json and file_link_json.startswith('['):
                try:
                    file_list = json.loads(file_link_json)
                    for file_info in file_list:
                        f_id = file_info.get('id')
                        if f_id:
                            delete_file_from_drive(f_id)
                except:
                    pass

        sheet.delete_rows(cell.row)
        fetch_sheet_data.clear()
        return True
    except Exception as e:
        st.error(f"데이터 삭제 실패: {e}")
        return False

def update_post(original_title, new_data):
    client = connect_to_sheets()
    if not client or not SHEET_URL: return False

    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        cell = sheet.find(str(original_title))
        # A부터 J열까지 업데이트 (10개 컬럼)
        col_letter = chr(64 + len(EXPECTED_COLS)) # J
        sheet.update(range_name=f"A{cell.row}:{col_letter}{cell.row}", values=[new_data])
        fetch_sheet_data.clear()
        return True
    except Exception as e:
        st.error(f"데이터 수정 실패: {e}")
        return False

def delete_tags_from_all_posts(tags_to_delete):
    """
    모든 게시글에서 특정 태그들을 일괄 삭제
    """
    client = connect_to_sheets()
    if not client or not SHEET_URL: return False
    
    try:
        sheet = client.open_by_url(SHEET_URL).sheet1
        all_values = sheet.get_all_values()
        if len(all_values) < 2: return True
        
        headers = all_values[0]
        data = all_values[1:]
        
        tag_col_idx = EXPECTED_COLS.index('태그')
        
        updated_tags_column = []
        updates_needed = False
        
        for row in data:
            if len(row) > tag_col_idx:
                current_tags_str = row[tag_col_idx]
                if current_tags_str:
                    # 해시태그 기반 분리
                    current_tags = [t.strip() for t in current_tags_str.split(' ') if t.strip()]
                    new_tags = [t for t in current_tags if t not in tags_to_delete]
                    
                    if len(current_tags) != len(new_tags):
                        updates_needed = True
                    
                    updated_tags_column.append([" ".join(new_tags)])
                else:
                    updated_tags_column.append([""])
            else:
                updated_tags_column.append([""])
        
        if updates_needed:
            col_letter = chr(65 + tag_col_idx) 
            range_name = f"{col_letter}2:{col_letter}{len(data) + 1}"
            sheet.update(range_name=range_name, values=updated_tags_column)
            fetch_sheet_data.clear()
            return True
        return True
            
    except Exception as e:
        st.error(f"태그 삭제 실패: {e}")
        return False

# -----------------------------------------------------------------------------
# 4. UI Components & Logic
# -----------------------------------------------------------------------------

def process_tags_input(tag_input):
    """
    태그 입력 문자열을 처리하여 해시태그 리스트로 반환
    예: "안전 예산" -> "#안전 #예산"
    """
    if not tag_input: return ""
    
    tags = []
    # 쉼표나 공백으로 분리
    tokens = tag_input.replace(',', ' ').split()
    for token in tokens:
        token = token.strip()
        if not token: continue
        if not token.startswith('#'):
            token = '#' + token
        tags.append(token)
    
    return " ".join(tags)

def get_all_unique_tags(df):
    """
    모든 글의 태그를 수집하여 유니크 리스트 반환
    """
    if df.empty or '태그' not in df.columns:
        return []
    
    all_tags = set()
    for t_str in df['태그']:
        if t_str:
            # 해시태그 단위로 분리 (#태그1 #태그2)
            tags = t_str.split()
            for t in tags:
                t = t.strip()
                if t: all_tags.add(t)
    
    return sorted(list(all_tags))

def render_sidebar_header(cookie_manager):
    with st.sidebar:
        st.title("메뉴")
        if st.button("🏠 홈으로", use_container_width=True):
            navigate_to('list')
            
        st.write(f"**로그인 정보**: {st.session_state.username}")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            # 쿠키 삭제
            cookie_manager.delete("sangsang_user")
            st.rerun()
            
        st.divider()

def view_list(df, cookie_manager):
    st.title("📂 업무 지식 목록")
    
    # ---------------------------
    # 사이드바 필터
    # ---------------------------
    with st.sidebar:
        st.header("🔍 상세 필터")
        
        # 데이터가 정상적으로 로드되었는지 확인
        if '학년도' in df.columns:
            # 1. 학년도 필터
            all_years = set()
            for y_str in df['학년도']:
                if y_str:
                    for y in str(y_str).split(','):
                        if y.strip(): all_years.add(y.strip())
            selected_years = st.multiselect("📅 학년도", sorted(list(all_years)), placeholder="학년도 선택")
        else:
            selected_years = []
            st.error("데이터 구조 오류: '학년도' 컬럼 없음")
        
        if '업무시기' in df.columns:
            # 2. 업무 시기 필터
            all_months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
            selected_months = st.multiselect("📆 업무 시기", all_months, placeholder="월 선택")
        else:
            selected_months = []
        
        # 3. 태그 관리 (관리자용)
        st.divider()
        with st.expander("🗑️ 태그 관리 (관리자용)"):
            if '태그' in df.columns:
                all_tags = set()
                for t_str in df['태그']:
                    if t_str:
                        for t in str(t_str).split(): # 공백으로 구분된 해시태그
                            if t.strip(): all_tags.add(t.strip())
                
                tags_to_remove = st.multiselect("삭제할 태그", sorted(list(all_tags)))
                if tags_to_remove:
                    if st.button("선택 태그 일괄 삭제", type="primary"):
                        if delete_tags_from_all_posts(tags_to_remove):
                            st.success("삭제 완료!")
                            st.rerun()

    # ---------------------------
    # 메인 검색 및 리스트
    # ---------------------------
    # ---------------------------
    # 메인 검색 및 리스트
    # ---------------------------
    col1, col2, col3 = st.columns([6, 2, 2])
    with col1:
        if st.button("⬅️ 뒤로가기"):
            go_back()
    with col2:
        if st.button("🕸️ 지식 그래프"):
            navigate_to('graph')
    with col3:
        if st.button("➕ 새 글 작성"):
            navigate_to('write')

    if df.empty:
        st.info("등록된 글이 없습니다.")
        return

    # 검색바
    search_query = st.text_input("🔍 검색 (제목, 내용, 태그)", placeholder="검색어를 입력하세요 (예: 안전, #예산)")
    
    # 필터링 로직
    filtered_df = df.copy()
    
    # 1. 학년도 필터링
    if selected_years:
        filtered_df = filtered_df[filtered_df['학년도'].apply(lambda x: any(y in [v.strip() for v in str(x).split(',')] for y in selected_years) if x else False)]
    
    # 2. 업무 시기 필터링
    if selected_months:
        filtered_df = filtered_df[filtered_df['업무시기'].apply(lambda x: any(m in [v.strip() for v in str(x).split(',')] for m in selected_months) if x else False)]
        
    # 3. 검색어 필터링
    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['제목'].str.lower().str.contains(query) | 
            filtered_df['내용'].str.lower().str.contains(query) |
            filtered_df['태그'].str.lower().str.contains(query)
        ]

    st.divider()
    
    # 리스트 출력
    # 페이지네이션 설정
    items_per_page = 10
    total_items = len(filtered_df)
    total_pages = max(1, math.ceil(total_items / items_per_page))
    
    if st.session_state.page > total_pages: st.session_state.page = total_pages
    if st.session_state.page < 1: st.session_state.page = 1
        
    start_idx = (st.session_state.page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_df = filtered_df.iloc[start_idx:end_idx]

    for index, row in page_df.iterrows():
        with st.container():
            # 카드 스타일 컨테이너 시작
            st.markdown('<div class="post-card">', unsafe_allow_html=True)
            
            # 파일 아이콘
            has_file = '파일링크' in row and isinstance(row['파일링크'], str) and row['파일링크'].strip()
            try:
                if has_file and row['파일링크'].startswith('['):
                    files = json.loads(row['파일링크'])
                    if not files: has_file = False
            except: pass
            file_icon = "📎" if has_file else ""

            # 제목 (크게, 클릭 가능하게 버튼으로 구현하되 스타일링 적용)
            col_title, col_meta = st.columns([7, 3])
            with col_title:
                # 제목을 버튼으로 만들어서 클릭 시 이동하게 함 (스타일은 CSS로 제어)
                if st.button(f"{row['제목']} {file_icon}", key=f"title_btn_{index}", help="클릭하여 상세 내용 보기"):
                    navigate_to('detail', row['제목'])
            
            with col_meta:
                st.caption(f"✍️ {row['작성자']} (수정: {row['작성일'][:10]})")

            # 태그 및 메타데이터
            tags = row['태그'].split() if row['태그'] else []
            tag_html = "".join([f"<span class='tag-badge'>{t}</span>" for t in tags])
            
            meta_html = ""
            if row['학년도']:
                meta_html += f"<span style='margin-right:8px; font-size:0.9rem;'>📅 {row['학년도']}</span>"
            if row['업무시기']:
                meta_html += f"<span style='font-size:0.9rem;'>📆 {row['업무시기']}</span>"
            
            st.markdown(f"<div style='margin-top:8px;'>{meta_html}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:8px;'>{tag_html}</div>", unsafe_allow_html=True)
            
            # 내용 미리보기
            content_preview = str(row['내용'])
            preview_text = content_preview[:120] + "..." if len(content_preview) > 120 else content_preview
            st.markdown(f"<div style='margin-top:10px; color:gray; font-size:0.95rem;'>{preview_text}</div>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True) # 카드 닫기

    # 페이지네이션 컨트롤 (복구됨)
    if total_pages > 1:
        st.markdown("---")
        c1, c2, c3 = st.columns([1, 8, 1])
        with c2:
            # 페이지 번호 버튼들을 가로로 나열
            page_cols = st.columns(min(total_pages, 10))
            for i in range(min(total_pages, 10)):
                p_num = i + 1
                with page_cols[i]:
                    # 현재 페이지는 Primary 스타일, 나머지는 Secondary
                    btn_type = "primary" if p_num == st.session_state.page else "secondary"
                    if st.button(str(p_num), key=f"p_{p_num}", type=btn_type, use_container_width=True):
                        st.session_state.page = p_num
                        st.rerun()

def view_write(df):
    st.title("📝 새 업무 기록 작성")
    
    if st.button("⬅️ 뒤로가기"):
        go_back()

    with st.form("write_form"):
        title = st.text_input("제목")
        
        # 메타데이터 입력 (학년도, 시기)
        c1, c2 = st.columns(2)
        with c1:
            # 학년도 범위 확장 (2018 ~ 2035)
            years_options = [str(y) for y in range(2018, 2036)]
            selected_years = st.multiselect("학년도 (다중 선택)", years_options, placeholder="학년도를 선택하거나 입력하세요")
        with c2:
            months_options = [f"{i}월" for i in range(1, 13)]
            selected_months = st.multiselect("업무 시기 (다중 선택)", months_options)

        # 태그 입력 (기존 태그 선택 + 직접 입력)
        st.markdown("##### 🏷️ 태그 입력")
        t1, t2 = st.columns([1, 1])
        with t1:
            all_existing_tags = get_all_unique_tags(df)
            selected_existing_tags = st.multiselect("기존 태그 선택 (검색 가능)", all_existing_tags, placeholder="태그를 검색하세요")
        with t2:
            new_tag_input = st.text_input("직접 입력 (새로운 태그)", placeholder="#태그 (자동으로 #이 붙습니다)")
        
        st.info("ℹ️ '내용' 입력란에는 텍스트만 입력 가능합니다.")
        content = st.text_area("내용", height=300)

        # 파일 첨부
        st.markdown("##### 📎 파일 첨부")
        uploaded_files = st.file_uploader("문서나 파일을 여기에 드래그하세요", accept_multiple_files=True)
        
        # 연관 업무
        existing_titles = df['제목'].tolist() if not df.empty else []
        related_posts = st.multiselect("연관된 업무 (다중 선택)", existing_titles)
        
        submit = st.form_submit_button("저장하기")
        
        if submit:
            if not title:
                st.error("제목을 입력해주세요.")
            elif title in existing_titles:
                st.error("이미 존재하는 제목입니다.")
            else:
                # 파일 업로드
                file_info_list = []
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        result = upload_secure_file(uploaded_file)
                        if result: file_info_list.append(result)
                
                file_info_json = json.dumps(file_info_list, ensure_ascii=False) if file_info_list else ""
                
                # 데이터 가공
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                related_ids_str = ",".join(related_posts)
                years_str = ", ".join(selected_years)
                months_str = ", ".join(selected_months)
                
                # 태그 합치기 (선택된 태그 + 직접 입력 태그)
                manual_tags_str = process_tags_input(new_tag_input)
                final_tags_list = list(set(selected_existing_tags + manual_tags_str.split()))
                tags_str = " ".join(final_tags_list)
                
                # 순서: 작성일, 작성자, 제목, 내용, 파일링크, 연관글ID, 이미지경로, 학년도, 업무시기, 태그
                row_data = [timestamp, st.session_state.username, title, content, file_info_json, related_ids_str, "", years_str, months_str, tags_str]
                
                if append_data(row_data):
                    st.success("저장되었습니다!")
                    navigate_to('detail', title)

def view_edit(df):
    st.title("✏️ 업무 기록 수정")
    
    if st.session_state.selected_post_id is None:
        navigate_to('list')
        return

    filtered_posts = df[df['제목'] == st.session_state.selected_post_id]
    if filtered_posts.empty:
        st.error("글을 찾을 수 없습니다.")
        navigate_to('list')
        return

    current_post = filtered_posts.iloc[0]
    
    if st.button("⬅️ 뒤로가기"):
        go_back()

    with st.form("edit_form"):
        new_title = st.text_input("제목", value=current_post['제목'])
        
        # 기존 값 파싱
        cur_years = [y.strip() for y in str(current_post['학년도']).split(',') if y.strip()]
        cur_months = [m.strip() for m in str(current_post['업무시기']).split(',') if m.strip()]
        
        c1, c2 = st.columns(2)
        with c1:
             # 학년도 범위 확장 (2018 ~ 2035)
            years_options = [str(y) for y in range(2018, 2036)]
            new_years = st.multiselect("학년도", years_options, default=cur_years, placeholder="학년도를 선택하거나 입력하세요")
        with c2:
            months_options = [f"{i}월" for i in range(1, 13)]
            new_months = st.multiselect("업무 시기", months_options, default=cur_months)

        # 태그 수정 (기존 태그 선택 + 직접 입력)
        st.markdown("##### 🏷️ 태그 수정")
        
        # 현재 태그를 리스트로 변환
        current_tags_list = current_post['태그'].split() if current_post['태그'] else []
        all_existing_tags = get_all_unique_tags(df)
        
        # 현재 태그가 전체 목록에 없으면 추가 (옵션에 있어야 default로 설정 가능)
        for t in current_tags_list:
            if t not in all_existing_tags:
                all_existing_tags.append(t)
        
        t1, t2 = st.columns([1, 1])
        with t1:
            selected_existing_tags = st.multiselect("태그 선택/삭제", sorted(list(set(all_existing_tags))), default=current_tags_list)
        with t2:
            new_tag_input = st.text_input("새로운 태그 추가 (직접 입력)", placeholder="#태그")
        
        st.info("ℹ️ '내용' 입력란에는 텍스트만 입력 가능합니다.")
        new_content = st.text_area("내용", value=current_post['내용'], height=300)
        
        # 기존 파일 로드
        existing_files = []
        try:
            if current_post['파일링크'] and current_post['파일링크'].startswith('['):
                existing_files = json.loads(current_post['파일링크'])
        except:
            pass

        # 기존 파일 삭제 UI (Form 내부로 이동)
        st.markdown("##### 📂 기존 파일 관리")
        files_to_delete_names = []
        if existing_files:
            file_map = {f['name']: f for f in existing_files}
            files_to_delete_names = st.multiselect("🗑️ 삭제할 파일을 선택하세요", list(file_map.keys()))
        else:
            st.caption("첨부된 파일이 없습니다.")

        # 파일 첨부 (Form 내부로 이동)
        st.markdown("##### 📎 새 파일 추가")
        new_uploaded_files = st.file_uploader("새 파일 추가", accept_multiple_files=True)
        
        # 연관 업무
        existing_titles = df['제목'].tolist() if not df.empty else []
        if current_post['제목'] in existing_titles: existing_titles.remove(current_post['제목'])
        
        cur_related = [x.strip() for x in str(current_post['연관글ID']).split(',') if x.strip()]
        default_related = [x for x in cur_related if x in existing_titles]
        new_related_posts = st.multiselect("연관된 업무", existing_titles, default=default_related)
        
        submit = st.form_submit_button("수정 완료")
        
        if submit:
            if not new_title:
                st.error("제목을 입력해주세요.")
            else:
                # 1. 파일 처리 (삭제 + 추가)
                current_file_list = []
                
                # 삭제할 파일 찾기
                files_to_delete = []
                if existing_files and files_to_delete_names:
                    file_map = {f['name']: f for f in existing_files}
                    files_to_delete = [file_map[name] for name in files_to_delete_names if name in file_map]

                # 기존 파일 중 삭제되지 않은 것만 유지
                if existing_files:
                    for f in existing_files:
                        is_deleted = False
                        for del_f in files_to_delete:
                            if f['id'] == del_f['id']:
                                is_deleted = True
                                # 드라이브에서 실제 삭제 시도
                                delete_result = delete_file_from_drive(f['id'])
                                if not delete_result:
                                    st.warning(f"파일 '{f['name']}' 삭제 실패 (이미 삭제되었을 수 있음)")
                                break
                        if not is_deleted:
                            current_file_list.append(f)
                
                # 새 파일 추가
                if new_uploaded_files:
                    for uploaded_file in new_uploaded_files:
                        result = upload_secure_file(uploaded_file)
                        if result: current_file_list.append(result)
                
                final_file_json = json.dumps(current_file_list, ensure_ascii=False) if current_file_list else ""

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                related_ids_str = ",".join(new_related_posts)
                years_str = ", ".join(new_years)
                months_str = ", ".join(new_months)
                
                # 태그 합치기
                manual_tags_str = process_tags_input(new_tag_input)
                final_tags_list = list(set(selected_existing_tags + manual_tags_str.split()))
                tags_str = " ".join(final_tags_list)
                
                # 순서: 작성일, 작성자, 제목, 내용, 파일링크, 연관글ID, 이미지경로, 학년도, 업무시기, 태그
                row_data = [timestamp, st.session_state.username, new_title, new_content, final_file_json, related_ids_str, "", years_str, months_str, tags_str]
                
                if update_post(current_post['제목'], row_data):
                    st.success("수정되었습니다!")
                    navigate_to('detail', new_title)

def view_detail(df):
    if st.session_state.selected_post_id is None:
        navigate_to('list')
        return

    filtered_posts = df[df['제목'] == st.session_state.selected_post_id]
    if filtered_posts.empty:
        st.error("글을 찾을 수 없습니다.")
        navigate_to('list')
        return

    current_post = filtered_posts.iloc[0]
    
    if st.button("⬅️ 뒤로가기"):
        go_back()

    # 화면 비율 조절 슬라이더
    c_guide1, c_slider, c_guide2 = st.columns([2, 6, 2])
    with c_guide1:
        st.markdown("<div style='text-align: right; font-weight: bold; font-size: 16px; padding-top: 10px;'>🕸️ 그래프 확대 ⬅️</div>", unsafe_allow_html=True)
    with c_slider:
        split_ratio = st.slider("화면 비율 조절", 0.1, 0.9, 0.6, 0.05, label_visibility="collapsed")
    with c_guide2:
        st.markdown("<div style='text-align: left; font-weight: bold; font-size: 16px; padding-top: 10px;'>➡️ 게시글 확대 📄</div>", unsafe_allow_html=True)
    
    col_text, col_graph = st.columns([split_ratio, 1 - split_ratio])
    
    with col_text:
        # 메타데이터 표시
        st.markdown(f"### {current_post['제목']}")
        st.caption(f"마지막 작성자: {current_post['작성자']} | 수정일: {current_post['작성일']}")
        
        m1, m2 = st.columns(2)
        with m1:
            if current_post['학년도']:
                st.markdown(f"**📅 학년도:** {current_post['학년도']}")
        with m2:
            if current_post['업무시기']:
                st.markdown(f"**📆 업무 시기:** {current_post['업무시기']}")
        
        if current_post['태그']:
            tags = current_post['태그'].split()
            tag_html = "".join([f"<span style='color:#0068c9; background-color:#e8f0fe; padding:4px 10px; border-radius:16px; margin-right:6px; font-size:14px; font-weight:bold;'>{t}</span>" for t in tags])
            st.markdown(tag_html, unsafe_allow_html=True)
            
        st.divider()
        st.markdown(current_post['내용'])
        
        # 첨부파일
        if current_post['파일링크']:
            st.divider()
            st.markdown("**📎 첨부파일**")
            try:
                file_list = json.loads(current_post['파일링크'])
                if isinstance(file_list, list):
                    for file_info in file_list:
                        f_id = file_info.get('id')
                        f_name = file_info.get('name')
                        
                        c_f1, c_f2 = st.columns([8, 2])
                        with c_f1: st.text(f"📄 {f_name}")
                        with c_f2:
                            file_data = download_file_from_drive(f_id)
                            if file_data:
                                st.download_button("💾 다운로드", data=file_data, file_name=f_name, key=f"down_{f_id}")
                            else:
                                st.error("로드 실패")
            except:
                st.markdown(f"[링크]({current_post['파일링크']})")

        # 수정/삭제 버튼
        st.divider()
        b1, b2 = st.columns(2)
        with b1:
            if st.button("✏️ 수정하기", use_container_width=True):
                navigate_to('edit', current_post['제목'])
        with b2:
            if st.button("🗑️ 삭제하기", type="primary", use_container_width=True):
                if delete_post(current_post['제목']):
                    st.success("삭제되었습니다.")
                    navigate_to('list')

    with col_graph:
        st.markdown("#### 🕸️ 지식 그래프")
        # 그래프 생성 로직 (간소화)
        from streamlit_agraph import agraph, Node, Edge, Config
        
        nodes = []
        edges = []
        existing_titles = df['제목'].tolist()
        
        # 현재 글 노드 (빨간색)
        nodes.append(Node(id=current_post['제목'], label=current_post['제목'], size=25, color="#FF4B4B"))
        
        # 연관 글 노드 및 엣지
        related_ids = [x.strip() for x in str(current_post['연관글ID']).split(',') if x.strip()]
        for r_id in related_ids:
            if r_id in existing_titles:
                nodes.append(Node(id=r_id, label=r_id, size=15, color="#0068C9"))
                edges.append(Edge(source=current_post['제목'], target=r_id))
        
        config = Config(width="100%", height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
        return_value = agraph(nodes=nodes, edges=edges, config=config)
        
        if return_value:
            navigate_to('detail', return_value)

def view_graph(df):
    st.title("🕸️ 업무 지식 그래프")
    
    if st.button("⬅️ 목록으로"):
        navigate_to('list')

    if df.empty:
        st.info("데이터가 없습니다.")
        return

    nodes = []
    edges = []
    added_nodes = set()

    # 1. 게시글 노드 생성
    for index, row in df.iterrows():
        post_id = row['제목']
        if post_id not in added_nodes:
            nodes.append(Node(id=post_id, label=post_id, size=20, color="#4A90E2")) # 파란색
            added_nodes.add(post_id)
        
        # 2. 연관글 엣지 생성
        related_ids = str(row['연관글ID']).split(',')
        for related_id in related_ids:
            related_id = related_id.strip()
            if related_id and related_id in df['제목'].values:
                edges.append(Edge(source=post_id, target=related_id, color="#BDC3C7"))
                
        # 3. 태그 노드 및 엣지 생성
        tags = str(row['태그']).split()
        for tag in tags:
            tag = tag.strip()
            if not tag: continue
            
            if tag not in added_nodes:
                nodes.append(Node(id=tag, label=tag, size=15, color="#50E3C2", shape="diamond")) # 초록색
                added_nodes.add(tag)
            
            edges.append(Edge(source=post_id, target=tag, color="#EAEDED"))

    config = Config(width="100%", height=600, directed=False, physics=True, hierarchy=False)
    
    return_value = agraph(nodes=nodes, edges=edges, config=config)
    
    if return_value:
        # 노드 클릭 시 해당 글로 이동 (태그는 제외)
        if not return_value.startswith('#'):
             navigate_to('detail', return_value)

# -----------------------------------------------------------------------------
# 5. Main Navigation
# -----------------------------------------------------------------------------

def navigate_to(view, post_id=None):
    st.session_state.current_view = view
    st.session_state.selected_post_id = post_id
    st.session_state.page = 1 # 페이지 초기화
    st.rerun()

def go_back():
    if st.session_state.current_view == 'detail':
        navigate_to('list')
    elif st.session_state.current_view in ['write', 'edit']:
        navigate_to('list')
    else:
        navigate_to('list')
        
def view_graph(df):
    st.title("🕸️ 업무 지식 그래프")
    
    if st.button("⬅️ 목록으로"):
        navigate_to('list')

    if df.empty:
        st.info("데이터가 없습니다.")
        return

    nodes = []
    edges = []
    added_nodes = set()

    # 1. 게시글 노드 생성
    for index, row in df.iterrows():
        post_id = row['제목']
        if post_id not in added_nodes:
            nodes.append(Node(id=post_id, label=post_id, size=20, color="#4A90E2")) # 파란색
            added_nodes.add(post_id)
        
        # 2. 연관글 엣지 생성
        related_ids = str(row['연관글ID']).split(',')
        for related_id in related_ids:
            related_id = related_id.strip()
            if related_id and related_id in df['제목'].values:
                edges.append(Edge(source=post_id, target=related_id, color="#BDC3C7"))
                
        # 3. 태그 노드 및 엣지 생성
        tags = str(row['태그']).split()
        for tag in tags:
            tag = tag.strip()
            if not tag: continue
            
            if tag not in added_nodes:
                nodes.append(Node(id=tag, label=tag, size=15, color="#50E3C2", shape="diamond")) # 초록색
                added_nodes.add(tag)
            
            edges.append(Edge(source=post_id, target=tag, color="#EAEDED"))

    # 화면 높이 조절 (기기별 대응)
    with st.expander("🔧 그래프 높이 조절 (모바일/태블릿/PC)", expanded=False):
        graph_height = st.slider("화면 높이 (픽셀)", min_value=400, max_value=2000, value=1000, step=50, help="기기 화면 크기에 맞춰 그래프의 세로 길이를 조절하세요.")

    # 그래프 설정
    config = Config(width="100%", height=graph_height, directed=False, physics=True, hierarchy=False)
    
    return_value = agraph(nodes=nodes, edges=edges, config=config)
    
    if return_value:
        # 노드 클릭 시 해당 글로 이동 (태그는 제외)
        if not return_value.startswith('#'):
             navigate_to('detail', return_value)

def main():
    # 0. 쿠키 매니저 초기화 (모든 페이지 로드 시 필수)
    cookie_manager = get_manager()
    
    # 1. 자동 로그인 체크 (로그인 상태가 아닐 때만)
    # 1. 자동 로그인 체크 (로그인 상태가 아닐 때만)
    # 1. 자동 로그인 체크 (로그인 상태가 아닐 때만)
    if not st.session_state.logged_in:
        try:
            # 브라우저 쿠키 로딩 대기
            if "cookie_checked" not in st.session_state:
                with st.spinner("사용자 정보 확인 중... (잠시만 기다려주세요)"):
                    time.sleep(1.0) # 충분한 대기 시간 확보
                    st.session_state.cookie_checked = True
            
            # 특정 쿠키 명시적 확인
            cookie_user = cookie_manager.get("sangsang_user")
            
            if cookie_user and cookie_user in ALLOWED_USERS:
                st.session_state.logged_in = True
                st.session_state.username = cookie_user
                st.rerun()
        except:
             pass

    # 2. 로그인 화면 표시
    if not st.session_state.logged_in:
        login_page(cookie_manager)
        return

    # 공통 사이드바 (홈, 로그아웃 등)
    render_sidebar_header(cookie_manager)

    # 데이터 로드
    df = fetch_sheet_data()
    
    if st.session_state.current_view == 'list':
        view_list(df, cookie_manager)
    elif st.session_state.current_view == 'write':
        view_write(df)
    elif st.session_state.current_view == 'detail':
        view_detail(df)
    elif st.session_state.current_view == 'edit':
        view_edit(df)
    elif st.session_state.current_view == 'graph':
        view_graph(df)

if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile

# --- 기본 설정 ---
WIDTH = 1920
HEIGHT = 1080
PAUSE = 0.6                 # 단어 읽은 후 대기 시간 (초)
TITLE_DURATION = 2.5        # 표지 화면이 온전히 보여지는 시간 (초)
TRANSITION_DURATION = 0.5   # 화면이 쓱 밀고 내려오는 애니메이션 시간 (초)

MAX_TEXT_WIDTH = WIDTH * 0.85
LINE_SPACING_RATIO = 1.2

# --- 폰트 고정 로드 ---
font_en_large = ImageFont.truetype("font/static/Lexend-Bold.ttf", 120)
font_ko_large = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 120)
font_en_small = ImageFont.truetype("font/static/Lexend-Bold.ttf", 90)
font_ko_small = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 90)

# --- 배경 이미지 고정 로드 ---
@st.cache_resource
def load_base_image():
    img = Image.open("background.png").convert("RGB")
    return img.resize((WIDTH, HEIGHT))

base_bg_image = load_base_image()

# --- 텍스트 줄바꿈 헬퍼 함수 ---
def draw_wrapped_text(draw, text, font, max_width, fill="black"):
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word]) if current_line else word
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
        
    bbox_h = font.getbbox("Ay가") 
    single_line_height = (bbox_h[3] - bbox_h[1]) * LINE_SPACING_RATIO
    total_block_height = len(lines) * single_line_height
    start_y = (HEIGHT / 2) - (total_block_height / 2)
    
    current_y = start_y
    for line in lines:
        draw.text((WIDTH/2, current_y), line, font=font, fill=fill, anchor="ma")
        current_y += single_line_height

# --- 슬라이드 이미지 생성 함수 ---
def make_title_slide(topic):
    img = base_bg_image.copy()
    draw = ImageDraw.Draw(img)
    text = "Flash cards"
    if topic:
        text += f"\n- {topic} -"
    draw.multiline_text((WIDTH/2, HEIGHT/2), text, font=font_ko_large, fill="#4c9cff", anchor="mm", align="center", spacing=60)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

def make_slide(text, font, is_long_text=False):
    img = base_bg_image.copy()
    draw = ImageDraw.Draw(img)
    text_str = str(text).strip() if pd.notna(text) else ""
    if text_str:
        if is_long_text:
            draw_wrapped_text(draw, text_str, font, MAX_TEXT_WIDTH)
        else:
            draw.text((WIDTH/2, HEIGHT/2), text_str, font=font, fill="black", anchor="mm")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# --- 오디오 생성 함수 ---
def make_audio(text):
    text_str = str(text).strip() if pd.notna(text) else ""
    if not text_str: text_str = "."
    tts = gTTS(text=text_str, lang="en")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# --- 애니메이션(위에서 아래로 밀어내기) 위치 계산 함수 ---
def make_slide_in_effect(duration):
    def effect(t):
        if t < duration:
            # y축을 -HEIGHT(화면 밖 위쪽)에서 0(화면 중앙)으로 이동시킵니다.
            return ('center', -HEIGHT * (1.0 - (t / duration)))
        return ('center', 0)
    return effect

# --- Streamlit UI ---
st.title("Vocabulary Video Generator")

# 템플릿 다운로드
try:
    with open("words.csv", "rb") as f:
        st.download_button("📥 CSV 템플릿 다운로드", data=f, file_name="words.csv", mime="text/csv")
except FileNotFoundError:
    csv_template = "word,ko_meaning,en_meaning,example,example_ko\napple,사과,A round fruit,I ate an apple.,나는 사과를 먹었다.\n"
    st.download_button("📥 CSV 템플릿 다운로드", data=csv_template, file_name="words.csv", mime="text/csv")

topic_input = st.text_input("주제를 영문으로 입력하세요")
uploaded = st.file_uploader("Upload CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    if st.button("Generate Video"):
        with st.spinner("애니메이션 효과를 적용하여 비디오를 생성 중입니다. 시간이 조금 걸릴 수 있습니다..."):
            clips = []
            
            # 1. 제목 화면 세팅
            title_img_path = make_title_slide(topic_input)
            title_duration = TITLE_DURATION + TRANSITION_DURATION
            
            # 제목 화면 오디오 (무음 처리용 꼼수: 아주 짧은 오디오를 전체 길이만큼 늘림)
            title_audio_file = AudioFileClip(make_audio("."))
            title_audio = CompositeAudioClip([title_audio_file.set_start(0)]).set_duration(title_duration)
            
            title_clip = ImageClip(title_img_path).set_duration(title_duration).set_audio(title_audio)
            clips.append(title_clip)

            # 2. 본문 화면 생성
            for i, row in df.iterrows():
                slides = [
                    (row["word"], row["word"], font_en_large, False),
                    (row["ko_meaning"], row["word"], font_ko_large, False),
                    (row["en_meaning"], row["en_meaning"], font_en_large, False),
                    (row["example"], row["example"], font_en_small, True),
                    (row["example_ko"], row["example"], font_ko_small, True)
                ]
                
                for screen_text, voice_text, font, is_long in slides:
                    if pd.isna(screen_text) and pd.isna(voice_text): continue

                    img_path = make_slide(screen_text, font, is_long_text=is_long)
                    audio_path = make_audio(voice_text)
                    audio_file = AudioFileClip(audio_path)
                    
                    # 클립 하나당 총 길이 = 음성 길이 + 무음 대기 시간 + 애니메이션 진행 시간
                    clip_duration = audio_file.duration + PAUSE + TRANSITION_DURATION
                    
                    # 해당 클립 길이에 맞춰 오디오를 합성 (끝부분은 자동으로 무음 처리됨)
                    clip_audio = CompositeAudioClip([audio_file.set_start(0)]).set_duration(clip_duration)
                    
                    video_clip = ImageClip(img_path).set_duration(clip_duration).set_audio(clip_audio)
                    clips.append(video_clip)
            
            # 3. 화면 전환 효과(Slide Down) 일괄 적용
            # 표지(첫 번째 클립)를 제외한 모든 클립에 내려오는 효과 부여
            for j in range(1, len(clips)):
                clips[j] = clips[j].set_pos(make_slide_in_effect(TRANSITION_DURATION))

            # 4. 영상 합성 (padding을 음수로 주어 애니메이션 시간만큼 겹치게 만듭니다)
            if clips:
                video = concatenate_videoclips(
                    clips, 
                    padding=-TRANSITION_DURATION, 
                    method="compose" # 화면이 겹치면서 그려지도록 compose 모드 활성화
                )
                
                output_filename = "vocab_video.mp4"
                video.write_videofile(
                    output_filename,
                    fps=24, 
                    codec="libx264",
                    audio_codec="aac"
                )
                st.success("비디오 생성이 완료되었습니다!")
                st.video(output_filename)

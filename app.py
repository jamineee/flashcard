import streamlit as st
import pandas as pd
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile

# --- 기본 설정 ---
WIDTH = 1920
HEIGHT = 1080
PAUSE = 0.6
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

# --- 1. 제목 슬라이드 생성 함수 (새로 추가) ---
def make_title_slide(topic):
    img = base_bg_image.copy()
    draw = ImageDraw.Draw(img)
    
    text = "Flash cards"
    if topic:
        text += f"\n- {topic} -"
        
    # 한글 주제 입력이 가능하므로 ko_large 폰트 사용, 글자색은 요청하신 #4c9cff 적용
    draw.multiline_text(
        (WIDTH/2, HEIGHT/2), 
        text, 
        font=font_ko_large, 
        fill="#4c9cff", 
        anchor="mm", 
        align="center",
        spacing=60  # 줄 간격 여백
    )
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# --- 본문 슬라이드 생성 함수 ---
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


# --- Streamlit UI ---
st.title("Vocabulary Video Generator")

# 2. 템플릿 다운로드 버튼
try:
    with open("words.csv", "rb") as f:
        st.download_button(
            label="📥 CSV 템플릿 다운로드",
            data=f,
            file_name="words.csv",
            mime="text/csv"
        )
except FileNotFoundError:
    # 혹시 로컬에 파일이 없을 때 앱 에러를 막기 위한 비상용 텍스트 템플릿
    csv_template = "word,ko_meaning,en_meaning,example,example_ko\napple,사과,A round fruit,I ate an apple.,나는 사과를 먹었다.\n"
    st.download_button(
        label="📥 CSV 템플릿 다운로드",
        data=csv_template,
        file_name="words.csv",
        mime="text/csv"
    )

# 3. 주제 입력 칸 추가
topic_input = st.text_input("주제를 입력하세요 (예: Day 1. 필수 영단어)")

uploaded = st.file_uploader("Upload CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    if st.button("Generate Video"):
        with st.spinner("비디오 생성 중... 잠시만 기다려주세요."):
            clips = []
            audios = []
            
            # --- 4. 영상 시작 전 인트로(제목) 슬라이드 삽입 ---
            title_img_path = make_title_slide(topic_input)
            
            # 오디오도 "Flash cards." 뒤에 주제를 자연스럽게 읽어주도록 세팅
            title_audio_text = f"Flash cards. {topic_input}" if topic_input else "Flash cards."
            title_audio_path = make_audio(title_audio_text)
            
            title_audio_clip = AudioFileClip(title_audio_path)
            title_duration = title_audio_clip.duration + PAUSE
            title_video_clip = ImageClip(title_img_path).set_duration(title_duration)
            
            clips.append(title_video_clip)
            audios.append(title_audio_clip)
            audios.append(AudioClip(lambda t: 0, duration=PAUSE))

            # --- 단어 본문 생성 루프 ---
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
                    
                    audio_clip = AudioFileClip(audio_path)
                    duration = audio_clip.duration + PAUSE
                    
                    video_clip = ImageClip(img_path).set_duration(duration)
                    
                    clips.append(video_clip)
                    audios.append(audio_clip)
                    audios.append(AudioClip(lambda t: 0, duration=PAUSE))
            
            # --- 영상 합성 ---
            if clips:
                video = concatenate_videoclips(clips)
                final_audio = concatenate_audioclips(audios)
                
                final_audio = final_audio.set_duration(video.duration)
                video = video.set_audio(final_audio)
                
                output_filename = "vocab_video.mp4"
                video.write_videofile(
                    output_filename,
                    fps=24, 
                    codec="libx264",
                    audio_codec="aac"
                )
                st.success("비디오 생성이 완료되었습니다!")
                st.video(output_filename)

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

# --- 폰트 고정 로드 (확인 없이 바로) ---
font_en_large = ImageFont.truetype("font/static/Lexend-Bold.ttf", 120)
font_ko_large = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 120)
font_en_small = ImageFont.truetype("font/static/Lexend-Bold.ttf", 90)
font_ko_small = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 90)

# --- 배경 이미지 고정 로드 (확인 없이 바로) ---
@st.cache_resource
def load_base_image():
    # background.png 파일을 무조건 불러와서 크기 맞춤
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

# --- 슬라이드 생성 함수 ---
def make_slide(text, font, is_long_text=False):
    img = base_bg_image.copy() # 고정된 배경 이미지 바로 복사
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

uploaded = st.file_uploader("Upload CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    if st.button("Generate Video"):
        with st.spinner("비디오 생성 중... 잠시만 기다려주세요."):
            clips = []
            audios = []
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

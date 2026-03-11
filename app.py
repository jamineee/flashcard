import streamlit as st
import pandas as pd
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile

WIDTH = 1920
HEIGHT = 1080
PAUSE = 0.6

# 폰트 경로가 실제 환경에 맞게 존재하는지 확인해주세요
font_en = ImageFont.truetype("font/static/Lexend-Bold.ttf", 120)
font_ko = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 120)

# 수정 1: 매개변수로 text와 font를 함께 받도록 변경
def make_slide(text, font):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    
    # 텍스트가 float(NaN) 등일 경우를 대비해 str()로 변환
    draw.text((WIDTH/2, HEIGHT/2), str(text), font=font, fill="black", anchor="mm")
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

def make_audio(text):
    # 텍스트가 비어있거나 NaN일 경우 에러 방지
    text = str(text) if pd.notna(text) else ""
    tts = gTTS(text=text, lang="en")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

st.title("Vocabulary Video Generator")
uploaded = st.file_uploader("Upload CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    if st.button("Generate Video"):
        clips = []
        audios = []
        for i, row in df.iterrows():
            # 수정 2: 슬라이드 정보에 어떤 폰트를 사용할지 추가
            slides = [
                (row["word"], row["word"], font_en),
                (row["ko_meaning"], row["word"], font_ko),
                (row["en_meaning"], row["en_meaning"], font_en),
                (row["example"], row["example"], font_en),
                (row["example_ko"], row["example"], font_ko)
            ]
            
            # 수정 3: 폰트 매개변수(font)도 같이 받아서 make_slide에 전달
            for screen_text, voice_text, font in slides:
                # 결측치(NaN) 건너뛰기 로직이 필요하다면 여기에 추가할 수 있습니다.
                img_path = make_slide(screen_text, font)
                audio_path = make_audio(voice_text)
                audio = AudioFileClip(audio_path)
                
                duration = audio.duration + PAUSE
                clip = ImageClip(img_path).set_duration(duration)
                
                clips.append(clip)
                audios.append(audio)
                audios.append(AudioClip(lambda t: 0, duration=PAUSE))
                
        video = concatenate_videoclips(clips)
        final_audio = concatenate_audioclips(audios)
        video = video.set_audio(final_audio)
        
        video.write_videofile(
            "vocab_video.mp4",
            fps=30,
            audio_codec="aac"
        )
        st.video("vocab_video.mp4")

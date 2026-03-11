import streamlit as st
import pandas as pd
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile

# --- 기본 설정 ---
WIDTH = 1920
HEIGHT = 1080
PAUSE = 1.5                 
TITLE_DURATION = 3.0        
TRANSITION_DURATION = 0.5   
FADEIN_DURATION = 1.0       # 맨 처음 표지가 서서히 나타나는 시간 (1초)

MAX_TEXT_WIDTH = WIDTH * 0.85
LINE_SPACING_RATIO = 1.2

# --- 폰트 고정 로드 ---
try:
    font_en_large = ImageFont.truetype("font/static/Lexend-Bold.ttf", 120)
    font_ko_large = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 120)
    font_en_small = ImageFont.truetype("font/static/Lexend-Bold.ttf", 90)
    font_ko_small = ImageFont.truetype("font/static/NotoSansKR-Bold.ttf", 90)
except OSError:
    st.error("폰트 파일을 찾을 수 없습니다. font/static/ 경로를 확인해주세요.")
    st.stop()

# --- 배경 이미지 3종 로드 (경로 수정 및 캐시 에러 완벽 해결) ---
@st.cache_resource
def load_backgrounds():
    def load_and_resize(path):
        try:
            img = Image.open(path).convert("RGB")
            return img.resize((WIDTH, HEIGHT))
        except FileNotFoundError:
            st.error(f"필수 배경 이미지 파일이 없습니다: '{path}'\n해당 폴더에 파일을 넣어주세요.")
            st.stop() 
            
    # 이미지를 딕셔너리 형태로 반환합니다. (background 폴더 경로 반영)
    return {
        "title": load_and_resize("background/bg_title.png"),
        "content": load_and_resize("background/bg_content.png"),
        "ending": load_and_resize("background/bg_ending.png")
    }

# 캐시된 함수를 호출하여 변수에 각각 저장합니다. (재실행 시에도 값 유지됨)
backgrounds = load_backgrounds()
bg_title = backgrounds["title"]
bg_content = backgrounds["content"]
bg_ending = backgrounds["ending"]

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

# --- 1. [표지] 슬라이드 생성 함수 ---
def make_title_slide(topic):
    img = bg_title.copy()
    draw = ImageDraw.Draw(img)
    text = "Flash cards"
    if topic:
        text += f"\n- {topic} -"
    
    draw.multiline_text((WIDTH/2, HEIGHT/2), text, font=font_ko_large, fill="#4c9cff", anchor="mm", align="center", spacing=60)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# --- 2. [본문] 슬라이드 생성 함수 ---
def make_slide(text, font, is_long_text=False):
    img = bg_content.copy()
    draw = ImageDraw.Draw(img)
    text_str = str(text).strip() if pd.notna(text) else ""
    text_color = "black" 

    if text_str:
        if is_long_text:
            draw_wrapped_text(draw, text_str, font, MAX_TEXT_WIDTH, fill=text_color)
        else:
            draw.text((WIDTH/2, HEIGHT/2), text_str, font=font, fill=text_color, anchor="mm")
            
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# --- 3. [엔딩] 슬라이드 생성 함수 ---
def make_ending_slide():
    img = bg_ending.copy()
    draw = ImageDraw.Draw(img)
    text = "Great Job!\nCompleted."
    
    draw.multiline_text((WIDTH/2, HEIGHT/2), text, font=font_en_large, fill="white", anchor="mm", align="center", spacing=40)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name

# --- 오디오 생성 함수 ---
def make_audio(text):
    text_str = str(text).strip() if pd.notna(text) else ""
    if not text_str: 
        text_str = "blank" 
    tts = gTTS(text=text_str, lang="en")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

# --- 애니메이션 좌표 계산 함수 ---
def make_slide_in_effect(duration):
    def effect(t):
        if t >= duration:
            return (0, 0)
        y_pos = -HEIGHT + (HEIGHT * (t / duration))
        return (0, int(y_pos))
    return effect

# --- Streamlit UI ---
st.title("Vocabulary Video Generator")

try:
    with open("words.csv", "rb") as f:
        st.download_button("📥 CSV 템플릿 다운로드", data=f, file_name="words.csv", mime="text/csv")
except FileNotFoundError:
    csv_template = "word,ko_meaning,en_meaning,example,example_ko\napple,사과,A round fruit,I ate an apple.,나는 사과를 먹었다.\n"
    st.download_button("📥 CSV 템플릿 다운로드", data=csv_template, file_name="words.csv", mime="text/csv")

topic_input = st.text_input("주제를 입력하세요 (예: Day 1. 필수 영단어)")
uploaded = st.file_uploader("Upload CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    if st.button("Generate Video"):
        with st.spinner("프레임 단위로 애니메이션을 합성 중입니다. (시간이 조금 걸립니다)..."):
            clips = []
            
            # --- 1. 표지 화면 추가 ---
            title_img_path = make_title_slide(topic_input)
            title_total_duration = TITLE_DURATION + TRANSITION_DURATION 
            title_audio = AudioClip(lambda t: 0, duration=title_total_duration)
            title_clip = ImageClip(title_img_path).set_duration(title_total_duration).set_audio(title_audio)
            clips.append(title_clip)

            # --- 2. 본문 화면 루프 ---
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
                    
                    clip_duration = audio_file.duration + PAUSE + TRANSITION_DURATION
                    clip_audio = CompositeAudioClip([audio_file.set_start(0)]).set_duration(clip_duration)
                    
                    video_clip = ImageClip(img_path).set_duration(clip_duration).set_audio(clip_audio)
                    clips.append(video_clip)

            # --- 3. 엔딩 화면 추가 ---
            ending_img_path = make_ending_slide()
            ending_total_duration = TITLE_DURATION + TRANSITION_DURATION
            ending_audio = AudioClip(lambda t: 0, duration=ending_total_duration)
            ending_clip = ImageClip(ending_img_path).set_duration(ending_total_duration).set_audio(ending_audio)
            clips.append(ending_clip)
            
            # --- 4. 애니메이션 좌표 계산 및 타임라인 배치 ---
            start_time = 0
            final_clips = []
            
            for idx, clip in enumerate(clips):
                if idx == 0:
                    # ✅ 첫 번째(표지) 화면에 페이드 인(Fade-in) 효과 추가
                    fadein_clip = clip.fadein(FADEIN_DURATION).set_start(start_time)
                    final_clips.append(fadein_clip)
                    start_time += clip.duration
                else:
                    start_time -= TRANSITION_DURATION 
                    animated_clip = clip.set_pos(make_slide_in_effect(TRANSITION_DURATION)).set_start(start_time)
                    final_clips.append(animated_clip)
                    start_time += clip.duration

            # --- 5. 최종 합성 (CompositeVideoClip) ---
            if final_clips:
                # 배경색을 검정으로 설정하여 검은 화면에서 서서히 밝아지도록 연출
                video = CompositeVideoClip(final_clips, size=(WIDTH, HEIGHT), bg_color=(0,0,0))
                
                output_filename = "vocab_video.mp4"
                video.write_videofile(
                    output_filename,
                    fps=24, 
                    codec="libx264",
                    audio_codec="aac"
                )
                st.success("🎉 비디오 생성이 완료되었습니다!")
                st.video(output_filename)

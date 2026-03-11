import streamlit as st
import pandas as pd
from gtts import gTTS
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import tempfile

WIDTH = 1920
HEIGHT = 1080
PAUSE = 0.6

font_en = ImageFont.truetype("font/static/Lexend-Bold.ttf",120)
font_ko = ImageFont.truetype("font/NotoSansKR-Bold.otf",120)

def make_slide(text):

    img = Image.new("RGB",(WIDTH,HEIGHT),"white")
    draw = ImageDraw.Draw(img)

    draw.text((WIDTH/2,HEIGHT/2), word, font=font_en, fill="black",anchor="mm")
    draw.text((WIDTH/2,HEIGHT/2), ko_meaning, font=font_ko, fill="black",anchor="mm")
    draw.text(((WIDTH/2,HEIGHT/2), en_meaning, font=font_en, fill="black",anchor="mm")
    draw.text((WIDTH/2,HEIGHT/2), example, font=font_en, fill="black",anchor="mm")
    draw.text((WIDTH/2,HEIGHT/2), example_ko, font=font_ko, fill="black",anchor="mm")

    tmp = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
    img.save(tmp.name)

    return tmp.name


def make_audio(text):

    tts = gTTS(text=text,lang="en")

    tmp = tempfile.NamedTemporaryFile(delete=False,suffix=".mp3")
    tts.save(tmp.name)

    return tmp.name


st.title("Vocabulary Video Generator")

uploaded = st.file_uploader("Upload CSV",type="csv")

if uploaded:

    df = pd.read_csv(uploaded)

    if st.button("Generate Video"):

        clips=[]
        audios=[]

        for i,row in df.iterrows():

            slides = [
                (row["word"], row["word"]),
                (row["ko_meaning"], row["word"]),
                (row["en_meaning"], row["en_meaning"]),
                (row["example"], row["example"]),
                (row["example_ko"], row["example"])
            ]

            for screen_text,voice_text in slides:

                img_path = make_slide(screen_text)
                audio_path = make_audio(voice_text)

                audio = AudioFileClip(audio_path)

                duration = audio.duration + PAUSE

                clip = ImageClip(img_path).set_duration(duration)

                clips.append(clip)

                audios.append(audio)
                audios.append(AudioClip(lambda t:0,duration=PAUSE))

        video = concatenate_videoclips(clips)

        final_audio = concatenate_audioclips(audios)

        video = video.set_audio(final_audio)

        video.write_videofile(
            "vocab_video.mp4",
            fps=30,
            audio_codec="aac"
        )

        st.video("vocab_video.mp4")

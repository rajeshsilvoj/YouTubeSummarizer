# Import necessary libraries
import streamlit as st
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from gensim.summarization.summarizer import summarize
import requests
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
import uuid
from moviepy.editor import *
from time import sleep



# Set page configs
st.set_page_config(page_title="Summarizer", page_icon="▶️")

st.title("Yt Summarizer 🎥🎞️")

# Text to text translation
def text_to_text_translation(sentence,target_language):
	subscription_key = "b2f0fecf617e4336b3c7ec887f2e3339"
	# Replace the above with your key
	endpoint = "https://api.cognitive.microsofttranslator.com"

	location = "eastus2"

	path = '/translate'
	constructed_url = endpoint + path

	params = {
	    'api-version': '3.0',
	    'to': [target_language]
	}
	
	constructed_url = endpoint + path

	headers = {
	    'Ocp-Apim-Subscription-Key': subscription_key,
	    'Ocp-Apim-Subscription-Region': location,
	    'Content-type': 'application/json',
	    'X-ClientTraceId': str(uuid.uuid4())
	}

	body = [{'text': sentence}]
	request = requests.post(constructed_url, params=params, headers=headers, json=body)
	response = request.json()
	#st.json(response)
	source_language = response[0]['detectedLanguage']['language']
	result = response[0]['translations'][0]['text']
	return source_language, result

# Form for user inputs
form = st.form(key='inputs')
url = form.text_input("Enter Youtube Video URL","https://www.youtube.com/watch?v=xTUZY0d9Fdk")
lang = form.selectbox('Select Target Language',['English','French','Japanese'])
summ_ratio = form.slider("Select Summarization Ratio:",0.05,1.0,0.5)
submit_button = form.form_submit_button('Summarize')



if submit_button:
	language = lang[:2].lower()
	
	try: 
		# https://www.youtube.com/watch?v=xTUZY0d9Fdk 
		yt = YouTube(url)

	except:
		st.error("Enter correct URL")	

	else:
		with st.spinner("Fetching Video Details..."):
			video_id = yt.video_id
			video_title = yt.title
			video_thumbnail = yt.thumbnail_url

			mp4files = yt.streams.filter(file_extension='mp4', progressive=True)

			video = mp4files[-1]
			video.download(skip_existing=True)	

			st.info("Video fetched successfully")

			transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
			for t in transcript_list:
				captions = t.translate('en').fetch()
				break
		
		#st.json(captions)	

		with st.spinner("Captions..."):
			full_text_list = []
			for x in captions:
				full_text_list.append(x['text'])
			full_text = " ".join(full_text_list).capitalize()
			#st.info("Full Text")
			#st.markdown(full_text)

			# Punctuate
			try:
				r = requests.post("http://bark.phon.ioc.ee/punctuator", data={"text":full_text})
				
				punctuated_expander = st.expander("Full Captions:",expanded=False)
				punctuated_captions = r.text
			except:
				punctuated_captions = full_text	

			display_text = []
			temp = punctuated_captions.split(".")
			i = 0
			for x in temp:
				if i%3 == 0:
					display_text.append(x+".\n\n")
				else:
					display_text.append(x+".")	
				i += 1
			display_text = "".join(display_text)
			punctuated_expander.caption(f"Text Length: {len(display_text)}")
			punctuated_expander.markdown(display_text)

		with st.spinner("Generating summary..."):
			summary_expander = st.expander("Summary:",expanded=True)
			
			summary = summarize(punctuated_captions, ratio = summ_ratio)
			
			summary_expander.caption(f"Text Length: {len(summary)}")
			summary_list = summary.split(".")

			# line = summary_expander.number_input("Enter line no. to be read: ",1,len(summary_list)-1)
			# line = int(line) - 1

			
			# Audio Output
			tts_button = Button(label="Speak", width=100)
			#speak = "hi hello"

			tts_button.js_on_event("button_click", CustomJS(code=f"""
			    var u = new SpeechSynthesisUtterance();
			    u.text = "{summary_list[0]}";
			    u.lang = 'en-US';

			    speechSynthesis.speak(u);
			    """))

			summary_expander.subheader("Audio Summary")
			summary_expander.bokeh_chart(tts_button)

			summary_expander.caption("All sentences are clickable 🌐🔗") 
			summary_expander.subheader(video_title)
			summary_expander.image(video_thumbnail,width=300)
			#summary_expander.markdown(summary)

			display_text = []
			temp = summary.split(".")
			i = 1
			j = 0
			every_three = []
			my_string = ""
			
			for x in temp:
				if i%3 == 0:
					if j < len(captions):
						pic_time = captions[j]["start"] + captions[j]["duration"]
						frame_image = VideoFileClip(f"{video_title}.mp4")
						frame_image.save_frame("frame.png",t=pic_time)
						summary_expander.image("frame.png",width=300)
						#summary_expander.markdown("\n\n")
						display_text.append("\n\n")
						every_three.append(my_string)
						my_string = ""
				

				my_string += x
				summary_expander.markdown(f'<a target="_blank" style="text-decoration:none;color:black" href="https://www.google.com/search?tbm=isch&q={x}">{x}.</a>',unsafe_allow_html=True)
				display_text.append(f'<a target="_blank" style="text-decoration:none;color:black" href="https://www.google.com/search?tbm=isch&q={x}">{x}.</a>')
				i += 1
				j += 1
			
			final_text = "".join(temp).lower()
			summary_text = "".join(temp).lower()

			# translate text
			if language != "en":
				_, final_text = text_to_text_translation(final_text,language)
				converted_expander = st.expander("Translated Summary:")
				converted_expander.markdown(final_text,unsafe_allow_html=True)

			#st.markdown(every_three)


		# Generate Video Summary
		with st.spinner("Generating Video Summary..."):
			st.title("Video Summary")
			if url != "https://www.youtube.com/watch?v=xTUZY0d9Fdk":
				video = VideoFileClip(f"{video_title}.mp4")
				#st.markdown(final_text)
				total_length = 0

				clips = []
				final_video = []

				captions_length = len(captions)
				q = 0
				while q < captions_length-1:
					element = captions[q]
					next_element = captions[q+1]
					next_element_text = len(next_element["text"])
					length = len(element["text"])
					total_length += length

					if element["text"] in summary_text[total_length:total_length+next_element_text+10] and len(clips)!=2:
						clips.append(element["start"])

					if element["text"] not in summary_text[total_length:total_length+next_element_text+10]:
						clips.append(next_element["start"])						

					if len(clips) == 2:	
						clip_object = video.subclip(clips[0], clips[1])
						final_video.append(clip_object)
						clips = []

					q = q + 1	

		with st.spinner("Loading Final Video..."):
			if url == "https://www.youtube.com/watch?v=xTUZY0d9Fdk":
				st.video("summary.mp4")
			else:	
				summ_vid = concatenate_videoclips(final_video)
				summ_vid.write_videofile("summary1.mp4")
				sleep(0.2)
				st.video("summary1.mp4")	

		

		with st.spinner("Generating questions..."):
			try:
				API_URL = "https://api-inference.huggingface.co/models/iarfmoose/t5-base-question-generator"
				API_URL2 = "https://api-inference.huggingface.co/models/deepset/roberta-base-squad2"
				headers = {"Authorization": "Bearer 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"}

				def query(url,payload):
					response = requests.post(url, headers=headers, json=payload)
					return response.json()

				st.title("Questions 🤔⁉️")	
				st.caption("Use the following questions to test your new knowledge.")
				no_of_questions = min(5,len(every_three))
				answers = []
				qno = 1

				for z in range(no_of_questions):
					question = query(API_URL,{"inputs": f"{every_three[z]}"})
					st.markdown(f"{qno}. {question[0]['generated_text'].capitalize()}")
					output = query(API_URL2,{
				    "inputs": {
						"question": f"{question}",
						"context": f"{every_three[z]}",
									},
								})
					answers.append(output["answer"].capitalize())
					qno += 1

				answers_expander = st.expander("Answers 👀",expanded=False)

				ano = 1
				for a in answers:
					answers_expander.markdown(f"{ano}. {a}")	
					ano += 1
			except:
				st.info("No questions available currently.")




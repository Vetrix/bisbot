import errno
import os
import sys
import tempfile
import random
from gtts import gTTS
from imdb import IMDb
from argparse import ArgumentParser
from urllib.parse import quote
from kbbi import KBBI
from urbandictionary_top import udtop
from googletrans import Translator
import requests
import wikipedia
import json

from flask import Flask, request, abort

from linebot import (
	LineBotApi, WebhookHandler
)
from linebot.exceptions import (
	InvalidSignatureError, LineBotApiError
)
from linebot.models import *

translator = Translator()
wiki_settings = {}
save_file = {}

ytlist = ["https://youtu.be/nBteO-bU78Y", "https://youtu.be/Xrcvig0f92U","https://youtu.be/M276QojLU-s",
			"https://youtu.be/I1qo9ZxoF04", "https://youtu.be/KF322xXDffg", "https://youtu.be/a1vNFJMpIUo"]

app = Flask(__name__)

line_bot_api = LineBotApi('CzSF4tZw1pR4X9i8Y6s580+0p7ebCpqq9MpoA98z8zsAl1ObHL+/Bmsk0t6BRk2+W9bxrNQMsUDsiEFcwr3nF7lVx644o8HwAXfr7mMfVhyXPC88CoNZKZxETv+WLa0L/gZoHA3YMc9KFINKeeoP+gdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('f69e514026a91f8ba1e5e3c7934eca35')


static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# function for create tmp dir for download content
def make_static_tmp_dir():
	try:
		os.makedirs(static_tmp_path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
			pass
		else:
			raise

@app.route("/callback", methods=['POST'])
def callback():
	# get X-Line-Signature header value
	signature = request.headers['X-Line-Signature']

	# get request body as text
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)

	# handle webhook body
	try:
		handler.handle(body, signature)
	except InvalidSignatureError:
		abort(400)

	return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

	text=event.message.text
	
	if isinstance(event.source, SourceGroup):
		subject = line_bot_api.get_group_member_profile(event.source.group_id,
														event.source.user_id)
		set_id = event.source.group_id
	elif isinstance(event.source, SourceRoom):
		subject = line_bot_api.get_room_member_profile(event.source.room_id,
                                                   event.source.user_id)
		set_id = event.source.room_id
	else:
		subject = line_bot_api.get_profile(event.source.user_id)
		set_id = event.source.user_id
		
	def split(text):
		return text.split(' ', 1)[-1]		
	
	def force_safe(text):
		return text.replace('http','https',1)
			
	def wolframs(query):
		wolfram_appid = ('83L4JP-TWUV8VV7J7')

		url = 'https://api.wolframalpha.com/v2/simple?i={}&appid={}'
		return url.format(quote(query), wolfram_appid)
	
	def wolfram(query):
		wolfram_appid = ('83L4JP-KWW62H4Y96')

		url = 'https://api.wolframalpha.com/v2/result?i={}&appid={}'
		return requests.get(url.format(quote(query), wolfram_appid)).text
	
	def trans(word):
		sc = 'id'
		to = 'en'
		
		if word[0:].lower().strip().startswith('sc='):
			sc = word.split(', ', 1)[0]
			sc = sc.split('sc=', 1)[-1]
			word = word.split(', ', 1)[1]
	
		if word[0:].lower().strip().startswith('to='):
			to = word.split(', ', 1)[0]
			to = to.split('to=', 1)[-1]
			word = word.split(', ', 1)[1]
			
		if word[0:].lower().strip().startswith('sc='):
			sc = word.split(', ', 1)[0]
			sc = sc.split('sc=', 1)[-1]
			word = word.split(', ', 1)[1]
			
		return translator.translate(word, src=sc, dest=to).text
		
	def wiki_get(keyword, set_id, trim=True):
    
		try:
			wikipedia.set_lang(wiki_settings[set_id])
		except KeyError:
			wikipedia.set_lang('en')

		try:
			result = wikipedia.summary(keyword)

		except wikipedia.exceptions.DisambiguationError:
			articles = wikipedia.search(keyword)
			result = "{} disambiguation:".format(keyword)
			for item in articles:
				result += "\n{}".format(item)
		except wikipedia.exceptions.PageError:
			result = "{} not found!".format(keyword)

		else:
			if trim:
				result = result[:2000]
				if not result.endswith('.'):
					result = result[:result.rfind('.')+1]
		return result
		
	def wiki_lang(lang, set_id):
    
		langs_dict = wikipedia.languages()
		if lang in langs_dict.keys():
			wiki_settings[set_id] = lang
			return ("Language has been changed to {} successfully."
					.format(langs_dict[lang]))

		return ("{} not available!\n"
				"See meta.wikimedia.org/wiki/List_of_Wikipedias for "
				"a list of available languages, and use the prefix "
				"in the Wiki column to set the language."
				.format(lang))	
	
	def find_kbbi(keyword, ex=False):

		try:
			entry = KBBI(keyword)
		except KBBI.TidakDitemukan as e:
			result = str(e)
		else:
			result = "Definisi {}:\n".format(keyword)
			if ex:
				result += '\n'.join(entry.arti_contoh)
			else:
				result += str(entry)
		return result
		
	def urban(keyword, ex=True):
		
		try:
			entry = udtop(keyword)
		except (TypeError, AttributeError, udtop.TermNotFound) :
			result = "{} definition not found in urbandictionary.".format(keyword)
		else:
			result = "{} definition:\n".format(keyword)
			if ex:
				result += str(entry)
			else:
				result += entry.definition
		return result
		
	def fdetect(url) :
		http_url = 'https://api-us.faceplusplus.com/facepp/v3/detect'
		key = "lM4feUDrJJYyKm8s4WvmxgWlVpZE0iNw"
		secret = "Y5L_l2a87UAtKeFzL-FD8K3C5OwtAbfA"
		attributes="age,gender,ethnicity,beauty"
		
		#add emotion later in atributes
		
		resp = requests.post(http_url,
			data = { 
					'api_key': key,
					'api_secret': secret,
					'image_url': url,
					'return_attributes': attributes}
		)

		r = resp.json()
	
		if (len(r) == 3 ) :
			return ("Face not detected")
			
		dict1 = r['faces']
		if ((len(dict1) > 1) or (len(dict1) < 1)):
			return ("Please send picture with one face only")
		else:
			dict2 = dict1[0]['attributes']['gender']['value']
			dict3 = dict1[0]['attributes']['age']['value']
			dict4 = dict1[0]['attributes']['beauty']
			
			if (dict2 == 'Male') :
				dict4 = dict4['male_score']
			else:
				dict4 = dict4['female_score']
			
			dict5 = dict1[0]['attributes']['ethnicity']['value']
			
			#dict6 = dict1[0]['attributes']['emotion'] add emotion later
			
			return("Gender		: " + str(dict2) + "\n" +
					"Age				: " + str(dict3) + "\n" +
					"Beauty		: " + str(round(dict4, 2)) + "\n" +
					"Ethnicity	: " + str(dict5))
	
	def pt(city) :
		url = "https://time.siswadi.com/pray/?address={}"
		r = requests.get(url.format(city))

		data = r.json()
		dict1 = data['data']
		dict2 = data['location']
		dict3 = data['time']
		
		return (str(dict2['address']) + " prayer time " + str(dict3['date']) + "\n"
				"Fajr				: " + str(dict1['Fajr']) + "\n"
				"Sunrise	: " + str(dict1['Sunrise']) + "\n"
				"Dhuhr		: " + str(dict1['Dhuhr']) + "\n"
				"Asr				: " + str(dict1['Asr']) + "\n"
				"Maghrib	: " + str(dict1['Maghrib']) + "\n"
				"Isha				: " + str(dict1['Isha']))
	
	def ig(username) :
		url = "https://www.instagram.com/{}"
		r = requests.get(url.format(username))
		if r.status_code == 404:
			return ("Unavailable")
			
		html = r.text
		jsondata = html.split("window._sharedData = ")[1].split(";</script>")[0]

		data = json.loads(jsondata)
		dict1 = data['entry_data']['ProfilePage'][0]['graphql']['user']

		return ("User : @"+ dict1['username'] + "\n" + "Name : " + dict1['full_name'] + "\n" + 
				"Following : " + str(dict1['edge_follow']['count']) + "\n" +
				"Followers : " + str(dict1['edge_followed_by']['count']) + "\n" +
				"Bio : " + dict1['biography'])
		
	def igs(username) :
		url = "https://www.instagram.com/{}"
		r = requests.get(url.format(username))
		html = r.text
		jsondata = html.split("window._sharedData = ")[1].split(";</script>")[0]

		data = json.loads(jsondata)
		dict1 = data['entry_data']['ProfilePage'][0]['graphql']['user']

		return (dict1['profile_pic_url_hd'])
		
	def picg(uri) :
		url = uri
		r = requests.get(url)
		if r.status_code == 404:
			return ("Unavailable")
		
		html = r.text
		jsondata = html.split("""<script type="application/ld+json">""")[1].split("</script>")[0]

		data = json.loads(jsondata)
		dict1 = data['caption']
		
		dict1 = dict1[:1900]
		
		data2 = html.split("""og:title" content=\"""")[1].split(":")[0]
		return(data2 + " : \n" + dict1 + "\n...")
		
	def picgs(uri) :
		url = uri
		r = requests.get(url)
		html = r.text

		data = html.split("""og:image" content=\"""")[1].split("\"")[0]
		return (data)
	
	def vigs(uri) :
		url = uri
		r = requests.get(url)
		html = r.text

		data = html.split("""og:video" content=\"""")[1].split("\"")[0]
		return (data)	
	
	def tts(word):
		la ='en'
		ext = 'mp3'
		
		if word[0:].lower().strip().startswith('la='):
			la = word.split(', ', 1)[0]
			la = la.split('la=', 1)[-1]
			word = word.split(', ', 1)[1]
			
		speech = gTTS(text=word, lang=la)
		with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix='mp3-', delete=False) as tf:
			speech.write_to_fp(tf)
		tempfile_path = tf.name
		
		dist_path = tempfile_path + '.' + ext
		dist_name = os.path.basename(dist_path)
		os.rename(tempfile_path, dist_path)
		
		url = request.host_url + os.path.join('static', 'tmp', dist_name)
		return force_safe(url)

	def mreview(movie) :	
		ia = IMDb()
		movies = ia.search_movie(movie)
		
		ID = movies[0].movieID
		data = ia.get_movie(ID)
		
		#data.infoset2keys (get all info)
		
		cast = ''
		i = 0
		while (i != 4) :
			cast = cast + "\n" + str(data['cast'][i]) + " as " +  str(data['cast'][i].notes)
			i += 1
		
		duration = str(data['runtimes']).split("'")[1]
		
		year = str(data['year'])
		
		plot = str(data['plot'][0].split("::")[0])
		
		rate = str(data['rating'])
		
		return ("Title						: " + str(movies[0]) + "\n"
				"Rating				: " + rate + "\n"
				"Duration			: " + duration + " minutes\n"
				"Year						: " + year + "\n"
				"Main Casts 	: " + cast + "\n"
				"Plot : \n" + str(plot))
				
	def imdbpic(movie) :
		ia = IMDb()
		movies = ia.search_movie(movie)
		
		ID = movies[0].movieID
		data = ia.get_movie(ID)
		
		return (str(data['cover url']))
	
	def ox(keyword):
		oxdict_appid = ('7dff6c56')
		oxdict_key = ('41b55bba54078e9fb9f587f1b978121f')
		
		word = quote(keyword)
		url = ('https://od-api.oxforddictionaries.com:443/api/v1/entries/en/{}'.format(word))
		req = requests.get(url, headers={'app_id': oxdict_appid, 'app_key': oxdict_key})
		if "No entry available" in req.text:
			return 'No entry available for "{}".'.format(word)

		req = req.json()
		result = ''
		i = 0
		for each_result in req['results']:
			for each_lexEntry in each_result['lexicalEntries']:
				for each_entry in each_lexEntry['entries']:
					for each_sense in each_entry['senses']:
						if 'crossReferenceMarkers' in each_sense:
							search = 'crossReferenceMarkers'
						else:
							search = 'definitions'
						for each_def in each_sense[search]:
							i += 1
							result += '\n{}. {}'.format(i, each_def)

		if i == 1:
			result = 'Definition of {}:\n'.format(keyword) + result[4:]
		else:
			result = 'Definitions of {}:'.format(keyword) + result
		return result
	
	if text == '/help':
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage("Full command bisbot pwrlvl9k : \n"
							"/leave, /kbbi, /wolfram, /wolframs,\n"
							"/trans, /wiki, /wikilang, /urban,\n"
							"/on, /off, /tts, /stalkig, /photoig,\n"
							"/videoig, /imdb, /pt, /fdetect, /ox"))
	
	elif text == '/on':
		save_file[set_id] = True
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("Save file on"))
				
	elif text == '/off':
		save_file[set_id] = False
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("Save file off"))
	
	elif text == '/music':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage(random.choice(ytlist)))
	
	elif text == '/kbbi':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get meaning of a word from https://kbbi.kemdikbud.go.id/ \n"
								"command /kbbi {word}"))
	
	elif text == '/urban':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get meaning of a word from https://www.urbandictionary.com/ \n"
								"command /urban {word}"))
	
	elif text == '/ox':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get meaning of a word from https://www.oxforddictionaries.com/ \n"
								"command /ox {word}"))
								
	elif text == '/imdb':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get movie review from https://www.imdb.com/ \n"
								"command /imdb {movie}"))
								
	elif text == '/fdetect':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get face detection of photo url \n"
								"command /fdetect {url}"))
	
	elif text == '/wolfram':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("use https://www.wolframalpha.com/ features, and give the result "
								"in simple text \n"
								"command /wolfram {input}"))
				
	elif text == '/wolframs':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("use https://www.wolframalpha.com/ features, and give the result "
								"in image \n"
								"command /wolframs {input}"))
				
	elif text == '/stalkig':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get simple description of instagram account and profile picture \n"
								"command /stalkig {username}"))
				
	elif text == '/photoig':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get photo and description of instagram post \n"
								"command /photoig {post link}"))
				
	elif text == '/videoig':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get video and description of instagram post \n"
								"command /videoig {post link}"))
				
	elif text == '/trans':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get translation from https://translate.google.com/ \n"
								"command /trans sc={language code}, to={language code}, {text}"))
				
	elif text == '/tts':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get audio file about how a word pronounced in a language \n"
								"command /tts la={language code}, {text}"))
	
	elif text == '/wiki':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get https://www.wikipedia.org/ description of something \n"
								"command /wiki {text}"))
				
	elif text == '/wikilang':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("change the language of wikipedia description \n"
								"command /wikilang {language code}"))
								
	elif text == '/pt':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage("get prayer time of your city \n"
								"command /pt {city}"))
	
	elif text == 'Stalk':
		if isinstance(event.source, SourceGroup):
			try:
				profile = line_bot_api.get_group_member_profile(event.source.group_id, event.source.user_id)
				line_bot_api.reply_message(
					event.reply_token,
					TextSendMessage("Display name: " + profile.display_name + "\n" +
									"Profile picture: " + profile.picture_url + "\n" +
									"User_ID: " + profile.user_id))
			except LineBotApiError:
				pass
		
		elif isinstance(event.source, SourceRoom):
			try:
				profile = line_bot_api.get_room_member_profile(event.source.room_id, event.source.user_id)
				line_bot_api.reply_message(
					event.reply_token,
					TextSendMessage("Display name: " + profile.display_name + "\n" +
									"Profile picture: " + profile.picture_url + "\n" +
									"User_ID: " + profile.user_id))
			except LineBotApiError:
				pass
				
		else:
			try:
				profile = line_bot_api.get_profile(event.source.user_id)
				line_bot_api.reply_message(
					event.reply_token,
					TextSendMessage("Display name: " + profile.display_name + "\n" +
									"Profile picture: " + profile.picture_url + "\n" +
									"User_ID: " + profile.user_id))
			except LineBotApiError:
				pass
			
	elif text == '/leave':
		if isinstance(event.source, SourceGroup):
			line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage('Bye.'))
			line_bot_api.leave_group(event.source.group_id)
		
		elif isinstance(event.source, SourceRoom):
			line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage('Bye.'))
			line_bot_api.leave_room(event.source.room_id)
			
		else:
			line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage('Gabisa dodol.'))

	elif text=='/wolfram':
		line_bot_api.reply_message(
				event.reply_token,
				TextSendMessage('command /wolfram {input}'))
	
	elif text[0:].lower().strip().startswith('/ox '):
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(ox(split(text))))
			
	elif text[0:].lower().strip().startswith('/pt ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(pt(split(text))))
			
	elif text[0:].lower().strip().startswith('/fdetect ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(fdetect(split(text))))
			
	elif text[0:].lower().strip().startswith('/tts ') :
		line_bot_api.reply_message(
				event.reply_token, [
				TextSendMessage(tts(split(text))),
				AudioSendMessage(original_content_url=tts(split(text)), duration=60000)
				])
	
	elif text[0:].lower().strip().startswith('/videoig '):
		line_bot_api.reply_message(
			event.reply_token, [
			TextSendMessage(picg(split(text))),
			VideoSendMessage(original_content_url= vigs(split(text)),
							preview_image_url= picgs(split(text)))
			])
	
	elif text[0:].lower().strip().startswith('/photoig '):
		line_bot_api.reply_message(
			event.reply_token, [
			TextSendMessage(picg(split(text))),
			ImageSendMessage(original_content_url= picgs(split(text)),
							preview_image_url= picgs(split(text)))
			])
	
	elif text[0:].lower().strip().startswith('/stalkig '):
		line_bot_api.reply_message(
			event.reply_token, [
			TextSendMessage(ig(split(text))),
			ImageSendMessage(original_content_url= igs(split(text)),
							preview_image_url= igs(split(text)))
			])
			
	elif text[0:].lower().strip().startswith('/imdb '):
		line_bot_api.reply_message(
			event.reply_token, [
			TextSendMessage(mreview(split(text))),
			ImageSendMessage(original_content_url= imdbpic(split(text)),
							preview_image_url= imdbpic(split(text)))
			])
				
	elif text[0:].lower().strip().startswith('/wolfram '):
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(wolfram(split(text))))
			
	elif text[0:].lower().strip().startswith('/kbbi '):
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(find_kbbi(split(text))))
			
	elif text[0:].lower().strip().startswith('/wolframs '):
		line_bot_api.reply_message(
			event.reply_token,
			ImageSendMessage(original_content_url= wolframs(split(text)),
								preview_image_url= wolframs(split(text))))
								
	elif text[0:].lower().strip().startswith('/echo ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(split(text)))
			
	elif text[0:].lower().strip().startswith('/trans ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(trans(split(text))))
			
	elif text[0:].lower().strip().startswith('/urban '):
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(urban(split(text))))
	
	elif text[0:].lower().strip().startswith('/wiki ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(wiki_get(split(text), set_id=set_id)))
			
	elif text[0:].lower().strip().startswith('/wikilang ') :
		line_bot_api.reply_message(
			event.reply_token,
			TextSendMessage(wiki_lang(split(text), set_id=set_id)))
	
			
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
	line_bot_api.reply_message(
		event.reply_token,
		StickerSendMessage(
			package_id=event.message.package_id,
			sticker_id=event.message.sticker_id)
	)

# Other Message Type
@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
	if isinstance(event.source, SourceGroup):
		subject = line_bot_api.get_group_member_profile(event.source.group_id,
														event.source.user_id)
		set_id = event.source.group_id
	elif isinstance(event.source, SourceRoom):
		subject = line_bot_api.get_room_member_profile(event.source.room_id,
                                                   event.source.user_id)
		set_id = event.source.room_id
	else:
		subject = line_bot_api.get_profile(event.source.user_id)
		set_id = event.source.user_id
		
	try :
		if save_file[set_id] :
			if isinstance(event.message, ImageMessage):
				ext = 'jpg'
			elif isinstance(event.message, VideoMessage):
				ext = 'mp4'
			elif isinstance(event.message, AudioMessage):
				ext = 'm4a'
			else:
				return

			message_content = line_bot_api.get_message_content(event.message.id)
			with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
				for chunk in message_content.iter_content():
					tf.write(chunk)
				tempfile_path = tf.name

			dist_path = tempfile_path + '.' + ext
			dist_name = os.path.basename(dist_path)
			os.rename(tempfile_path, dist_path)

			line_bot_api.reply_message(
				event.reply_token, [
					TextSendMessage(text='Save content.'),
					TextSendMessage(text=request.host_url + os.path.join('static', 'tmp', dist_name))
				])
	except KeyError:
		save_file[set_id] = False
	
@handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
	if isinstance(event.source, SourceGroup):
		subject = line_bot_api.get_group_member_profile(event.source.group_id,
														event.source.user_id)
		set_id = event.source.group_id
	elif isinstance(event.source, SourceRoom):
		subject = line_bot_api.get_room_member_profile(event.source.room_id,
                                                   event.source.user_id)
		set_id = event.source.room_id
	else:
		subject = line_bot_api.get_profile(event.source.user_id)
		set_id = event.source.user_id
	
	try :
		if save_file[set_id] :
			message_content = line_bot_api.get_message_content(event.message.id)
			with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix='file-', delete=False) as tf:
				for chunk in message_content.iter_content():
					tf.write(chunk)
				tempfile_path = tf.name
			
			dist_path = tempfile_path + '-' + event.message.file_name
			dist_name = os.path.basename(dist_path)
			os.rename(tempfile_path, dist_path)
			
			line_bot_api.reply_message(
				event.reply_token, [
					TextSendMessage(text='Save file.'),
					TextSendMessage(text=request.host_url + os.path.join('static', 'tmp', dist_name))
				])
	except KeyError:
		save_file[set_id] = False

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
	line_bot_api.reply_message(
		event.reply_token,
		LocationSendMessage(
			title=event.message.title, address=event.message.address,
			latitude=event.message.latitude, longitude=event.message.longitude
		)
	)

@handler.add(JoinEvent)
def handle_join(event):
	line_bot_api.reply_message(
		event.reply_token,
		TextSendMessage(text='Barista is here... ' + event.source.type + ' apa ini?'))

if __name__ == "__main__":
	port = int(os.environ.get('PORT', 5000))
	make_static_tmp_dir()
app.run(host='0.0.0.0', port=port)

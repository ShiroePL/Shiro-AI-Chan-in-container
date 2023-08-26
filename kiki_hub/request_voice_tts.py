#For more samples please visit https://github.com/Azure-Samples/cognitive-services-speech-sdk 
import os
import azure.cognitiveservices.speech as speechsdk

def request_voice_fn(text, lang=False):
    """text: text to be converted to speech, lang: english(default) or polish"""
        #speech config
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
    
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    ssml = """<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US">
        <voice name="en-US-AshleyNeural"><prosody rate="3%" pitch="21%">""" + text + """</prosody></voice></speak>"""
   
    ssml_pl = """<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="pl-PL">
    <voice name="pl-PL-ZofiaNeural"><prosody rate="+9.00%" volume="-60.00%" pitch="+7.00%">""" + text + """</prosody></voice></speak>"""


    #result = synthesizer.speak_ssml_async(ssml).get() if lang else synthesizer.speak_ssml_async(ssml_pl).get()
    if lang ==True:
        result = synthesizer.speak_ssml_async(ssml_pl).get()
    else:  
        result = synthesizer.speak_ssml_async(ssml).get()
    stream = speechsdk.AudioDataStream(result)
    stream.save_to_wav_file("./kiki_hub/response.wav")
    

if __name__ == "__main__":
    #request_voice_fn("I am good, and you?")
    pass
    
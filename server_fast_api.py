from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
import logging
from better_profanity import profanity
import chatgpt_api
import kiki_hub.request_voice_tts as request_voice
import string
import anilist.anilist_api_requests as anilist_api_requests
import re
from shiro_agent import CustomToolsAgent
from langchain_database.test_wszystkiego import add_event_from_shiro, retrieve_plans_for_days
import requests
from typing import Optional
import connect_to_phpmyadmin
from home_assistant import ha_api_requests
from datetime import datetime


content_type_mode =""
app = FastAPI()
anilist_mode = False

#logging.basicConfig(filename=/app/logs/shiro_fastapi_vps.log', filemode='a', format='%(asctime)s - %(message)s', level=logging.INFO)
class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors."""

    BLUE = "\033[34m"
    RESET = "\033[0m"

    FORMATS = {
        logging.INFO: BLUE + "%(asctime)s - %(filename)s - %(message)s" + RESET,
        'DEFAULT': "%(asctime)s - %(filename)s - %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS['DEFAULT'])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    


# Get a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a FileHandler
file_handler = logging.FileHandler('/app/logs/shiro_fastapi_vps.log')

file_handler.setLevel(logging.INFO)

# Set the formatter for the handler
file_handler.setFormatter(CustomFormatter())

# Add the handler to the logger
logger.addHandler(file_handler)

# class QuestionWithUser(BaseModel):
#     question: str
#     username: str
#     checkbox_agentmode: bool
#     checkbox_voice: bool
#     checkbox_update: bool
#     checkbox_polish: bool
class QuestionWithUser(BaseModel):
    question: str
    username: str
    checkbox_agentmode: Optional[bool] = None
    checkbox_voice: Optional[bool] = None
    checkbox_update: Optional[bool] = None
    checkbox_polish: Optional[bool] = None

    class Config:
        alias_generator = lambda s: s  # disable automatic snake_case conversion
        allow_population_by_field_name = True  # allow populating by field name

class Question_to_chromabd(BaseModel):
    question: str

class ChatMessage(BaseModel):
    role: str
    content: str

def agent_shiro(query):
    agent = CustomToolsAgent()
    final_answer = agent.run(query)
    return final_answer

def exit_anilist_mode():
    global anilist_mode
    anilist_mode = False
    print("--------------------")
    print("exited anilist mode")
    print("--------------------")

def chroma_db_search(question: str):
    # Prepare the payload to send to the PC server
    payload = {"question": question}

    try:
        response = requests.get("http://10.147.17.21:8055/health", timeout=0.3)
        response.raise_for_status()

        # If no exception was raised, the PC server is running and we can forward the request
        response = requests.post("http://10.147.17.21:8055/question", json=payload)

        # Extract the answer from the response
        answer = response.json()["answer"]
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        # PC server is not available, so do something else
        answer = "Default answer because PC server is not available."

    return answer


# Test endpoint to see what data is being sent
@app.post("/test")
async def test(payload: dict):
    print(payload)
    
    return {"payload": payload}

@app.post("/do_work")
async def do_work(payload: Question_to_chromabd):
    # First check if the PC server is running
    try:
        response = requests.get("http://10.147.17.21:8055/health", timeout=0.3)  # 1 second timeout
        response.raise_for_status()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        raise HTTPException(status_code=503, detail="PC server is not available")
    
    # If no exception was raised, the PC server is running and we can forward the request
    response = requests.post("http://10.147.17.21:8055/question", json=payload.dict())
    
    # Forward the PC server's response to the client
    return response.json()



@app.get("/health")
def health_check():
    logger.info("Health check working :D")
    # Replace with the IP address and port number of your machine running FastAPI
    url = "http://10.147.17.21:8055/health"
    response = requests.get(url)
    # print out the response
    print(f'Response Status Code: {response.status_code}')
    print(f'Response Content: {response.json()}')
    return {"status": "Healthy, and here is response from pc: " + str(response.json())}

@app.get("/health_mobile")
def health_check1():
    return {"status": "ShiroAi-chan is healthy and ready to work!"}

@app.get("/chat_history/{name}")
async def get_chat_history(name: str):
    messages = connect_to_phpmyadmin.retrieve_chat_history_from_database("normal")
    logger.info("current short-term history:" + str(messages))
    return {"messages": messages}


@app.get("/audio/{audio_file_name}")
async def get_audio(audio_file_name: str):
    return FileResponse(f"./kiki_hub/{audio_file_name}")

@app.post("/question")
async def question(payload: dict):
    """
    A FastAPI endpoint to answer a question
    """
    question_text = payload["question"]
    username = payload["username"]
    # checkboxes from watch UI
    checkbox_agentmode = payload["checkBox_agentmode"]
    checkbox_voice= payload["checkBox_voice"]
    checkbox_update= payload["checkBox_update"]
    checkbox_polish= payload["checkBox_polish"]


    #answer = shiro_on_android.voice_control(question_text, username, checkbox) #need to change this
    answer = main_function(question_text, checkbox_agentmode, username, checkbox_update, checkbox_polish)


    # Process the question, username and checkbox as needed
    done_answer = f" {answer}"
    logger.info(f"Question: {question_text} | Answer: {done_answer}")
    return {"answer": done_answer}


def main_function(question, checkbox_agentmode, name, checkbox_update, checkbox_polish):

    name="normal"
    agent_mode_variable = checkbox_agentmode
    agent_reply = ''
    connect_to_phpmyadmin.check_user_in_database(name)
    messages = connect_to_phpmyadmin.retrieve_chat_history_from_database(name)
    global anilist_mode
    
    global content_type_mode
    global content_type_mode
    
    # Get all punctuation but leave colon ':'
    punctuation_without_colon = "".join([ch for ch in string.punctuation if ch != ":"])
    cleaned_question = question.translate(str.maketrans("", "", punctuation_without_colon)).strip().lower()


    if agent_mode_variable == True or cleaned_question.startswith("agent mode"):
        print("wejscie w if od agenta ")
        logger.info("wejscie w if od agenta ")
        cleaned_question = cleaned_question.replace("agent:", "").strip()
        agent_reply = agent_shiro(cleaned_question)
        
        print("Agent: " + agent_reply)
        logger.info("Agent: " + agent_reply)


    if cleaned_question in ("stop:"):
        exit_anilist_mode()
        print("exited anilist mode")
        logger.info("exited anilist mode")
        answer = "exited anilist mode"
        return answer
        

    elif cleaned_question.lower().startswith("plan:") or "add_event_to_calendar" in agent_reply:
        query = cleaned_question.replace("plan:", "").strip()

        messages.append({"role": "user", "content": query})
            # use chain to add event to calendar
        answer, prompt_tokens, completion_tokens, total_tokens, formatted_query_to_calendar = add_event_from_shiro(query)


        
        print("I added event with this info: \n" + formatted_query_to_calendar)
        logger.info("I added event with this info: \n" + formatted_query_to_calendar)
        answer = "I added event with this info: \n" + formatted_query_to_calendar

        request_voice.request_voice_fn(answer)
        connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to Azure DB to user table    
        connect_to_phpmyadmin.add_pair_to_general_table(name, answer) #to general table with all  questions and answers
        connect_to_phpmyadmin.send_chatgpt_usage_to_database(prompt_tokens, completion_tokens, total_tokens) #to A DB with usage stats
        print("-----addded tokens to db--------")
        logger.info("-----addded tokens to db--------")

        return answer

    elif cleaned_question.lower().startswith("schedule:") or "retrieve_event_from_calendar" in agent_reply:
        query = cleaned_question.replace("schedule:", "").strip()
        query = "Madrus: " + query
        messages.append({"role": "user", "content": query})

        # use function chain to add event to calendar
        answer, prompt_tokens, completion_tokens, total_tokens = retrieve_plans_for_days(query)

        

            # sending schedule to shiro to add personality to raw schedule
        question = f"""can you summarize my plans ? what i have for that days. tell me like assistant tells plans for her boss when he has little time to listen. In 'your words', not just plain date's. and please order it by dates. here are my plans: '{answer}"""
        
        messages.append({"role": "user", "content": question})
                
        print("messages: " + str(messages))
        logger.info("messages: " + str(messages))
        personalized_answer, prompt_tokens2, completion_tokens2, total_tokens2 = chatgpt_api.send_to_openai(messages)

        prompt_tokens += prompt_tokens2
        completion_tokens += completion_tokens2
        total_tokens += total_tokens2

        
        print("answer: " + answer)
        logger.info("answer: " + answer)
        tts_answer = "these are your plans:"
        request_voice.request_voice_fn(tts_answer)
        connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to Azure DB to user table    
        connect_to_phpmyadmin.add_pair_to_general_table(name, answer) #to general table with all  questions and answers
        connect_to_phpmyadmin.send_chatgpt_usage_to_database(prompt_tokens, completion_tokens, total_tokens) #to A DB with usage stats
        print("-----addded tokens to db--------")
        logger.info("-----addded tokens to db--------")
        return personalized_answer
          
    elif cleaned_question.lower().startswith("ha:") or "home_assistant" in agent_reply:
        query = cleaned_question.replace("ha:", "").strip()
        # use function chain to add event to calendar
        answer_from_ha = ha_api_requests.room_temp()
        print("answer from api: " + answer_from_ha)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
        query2 = f"[current time: {current_time}] Madrus: {query}. shiro: Retriving informations from her sensors... Done! Info from sensors:{answer_from_ha}°C. Weather outside: 25°C.| (please say °C in your answer) | Shiro:"        
        messages.append({"role": "user", "content": query2})
                
        print("messages: " + str(messages))
        logger.info("messages: " + str(messages))
        personalized_answer, prompt_tokens, completion_tokens, total_tokens = chatgpt_api.send_to_openai(messages)

        print("answer: " + personalized_answer)
        logger.info("answer: " + personalized_answer)
        request_voice.request_voice_fn(personalized_answer)
        connect_to_phpmyadmin.insert_message_to_database(name, question, personalized_answer, messages) #insert to Azure DB to user table    
        connect_to_phpmyadmin.add_pair_to_general_table(name, personalized_answer) #to general table with all  questions and answers
        connect_to_phpmyadmin.send_chatgpt_usage_to_database(prompt_tokens, completion_tokens, total_tokens) #to A DB with usage stats
        print("-----addded tokens to db--------")
        logger.info("-----addded tokens to db--------")
        return personalized_answer      

    elif cleaned_question.lower().startswith("db:") or "database_search" in agent_reply:
        query = cleaned_question.replace("db:", "").strip()
        messages.append({"role": "user", "content": query})
        #answer = search_chroma_db(query)
        ##########################################################################
            # here si request to PC to run chroma db search, and if no response, get this info
        
        answer = chroma_db_search(question)
        
        return answer

        # request_voice.request_voice_fn(answer)
        # print("got answer from db" + answer)
        
        # connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to Azure DB to user table    
        # connect_to_phpmyadmin.add_pair_to_general_table(name, answer) #to general table with all  questions and answers


    elif "show_anime_list" in agent_reply or "show_manga_list" in agent_reply:
            
        content_type = "anime" if "anime" in agent_reply else "manga" 
        
        list_content, _ = anilist_api_requests.get_10_newest_entries("ANIME") if content_type == "anime" else anilist_api_requests.get_10_newest_entries("MANGA")  # assuming this method exists        
            
        question = f"Madrus: I will give you list of my 10 most recent watched/read {content_type} from site AniList. Here is this list:{list_content}. I want you to remember this because in next question I will ask you to update episodes/chapters of one of them."
        #print("question from user:" + question)
        messages.append({"role": "user", "content": question})

        # send to open ai for answer !!!!!!!! I WONT SEND IT BECOUSE I ALREADY GOT IT FROM reformatting
        answer = "Okay, I will remember it, Madrus. I'm waiting for your next question. Give it to me nyaa."
        answer_to_app = f"Here is your list of most recent anime/manga.{list_content}" # this goes 

        logging.info("requested list: \n" + answer_to_app)
        print("requested list: \n" + answer_to_app)
        logger.info("requested list: \n" + answer_to_app)
        request_voice.request_voice_fn("Here is your list. *smile*") #request Azure TTS to for answer
           
        
        connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to Azure DB to user table    
        print("------end of list function--------")
        logging.info("-----end of list function------")
        content_type_mode = content_type
        
        return answer_to_app
        

        
    elif checkbox_update: # she is in animelist mode, so she rebebmers list i gave her 
        
       
        
        # make shiro find me id of anime/manga
          
        content_type = content_type_mode   
        chapters_or_episodes = "episodes" if content_type == "anime" else "chapters"

        end_question = "I would like you to answer me giving me ONLY THIS: ' title:<title>,id:<id>,"
        extra = " episodes:<episodes>'. Nothing more." if content_type == "anime" else " chapters:<chapters>'. Nothing more."
        question = f"Madrus: {question}. {end_question}{extra}"

        #print("question from user:" + question)
        messages.append({"role": "user", "content": question})
        
        # send to open ai for answer
        
        answer, prompt_tokens, completion_tokens, total_tokens = chatgpt_api.send_to_openai(messages) 
        print("answer from OpenAI: " + answer)
        logger.info("answer from OpenAI: " + answer)
            # START find ID and episodes number of updated anime
        # The regex pattern             
        pattern = r"id:\s*(\d+),\s*episodes:\s*(\d+)" if content_type == "anime" else r"id:\s*(\d+),\s*chapters:\s*(\d+)"

        # Use re.search to find the pattern in the text
        match = re.search(pattern, answer)
        

        if match:
            # match.group(1) contains the id, match.group(2) contains the episodes number
            updated_id = match.group(1)
            
            updated_info = match.group(2)
            print(f"reformatted request: id:{updated_id}, type:{content_type}: ep/chap{updated_info}")
            logger.info(f"reformatted request: id:{updated_id}, type:{content_type}: ep/chap{updated_info}")

            anilist_api_requests.change_progress(updated_id, updated_info,content_type)

            request_voice.request_voice_fn(f"Done, updated it to {updated_info} {chapters_or_episodes}")

                # Save to database 
            connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to Azure DB to user table    
            connect_to_phpmyadmin.send_chatgpt_usage_to_database(prompt_tokens, completion_tokens, total_tokens) #to Azure DB with usage stats
            print("---------saved to db-------------")
            logger.info("---------saved to db-------------")
            answer_to_app = f"Done, updated it to {updated_info} {chapters_or_episodes}"
        else:
            print("No match found")
            logger.info("No match found")
            request_voice.request_voice_fn("Sorry, I couldn't understand your request.")
            answer_to_app = "Sorry, I couldn't understand your request."
        # END find ID and episodes number of updated anime/manga

        
        
        
        print("exited animelist mode")
        logger.info("----updated anime/manga----")
        return answer_to_app

    else: # normal question and answer mode
        # to database
        question = f"Madrus: {question}. Odpowiedz po polsku." if checkbox_polish == True else f"Madrus: {question}."
        
        logger.info("------normal q/a mode------")
        logger.info("question from user:" + question)
        print("------normal q/a mode------")

        print("question from user:" + question)
        messages.append({"role": "user", "content": question})
        
            # send to open ai for answer
        logger.info("messages: " + str(messages))
        print("messages: " + str(messages))
        answer, prompt_tokens, completion_tokens, total_tokens = chatgpt_api.send_to_openai(messages) 
        logger.info("answer from OpenAI: " + answer)
        print("ShiroAi-chan: " + answer)
         
        request_voice.request_voice_fn(answer, checkbox_polish) #request Azure TTS to for answer
        
        if profanity.contains_profanity(answer) == True:
            answer = profanity.censor(answer)     

        connect_to_phpmyadmin.insert_message_to_database(name, question, answer, messages) #insert to DB to user table    
        connect_to_phpmyadmin.add_pair_to_general_table(name, answer) #to general table with all  questions and answers
        connect_to_phpmyadmin.send_chatgpt_usage_to_database(prompt_tokens, completion_tokens, total_tokens) #to A DB with usage stats
        logger.info("------saved to db => end of q/a mode------")
        print("------saved to db => end of q/a mode------")
        
        return answer

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="10.147.17.98", port=8057)

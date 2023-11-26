from llmonitor import monitor, users, agent, tool
import openai
import os, time
# from dotenv import load_dotenv

openai.api_key = os.environ.get('OPENAI_API_KEY')

monitor(openai)

@agent("Monitored Chat App", user_id="wangjsty", tags=["test", "test2"])
def monitored_chat1_app(a, b, c, test, test2):

    print("DEBUG: monitored_chat1_app started ...")
    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "What is GitOps?"}],
        user_id="wangjsty",
    )
    return "Agent output"

def monitored_chat2_app(a, b, c, test, test2):

    print("DEBUG: monitored_chat2_app started ...")
    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "What is AIOps?"}],
        user_id="wangjsty",
    )
    return "Agent output"

monitored_chat1_app(1, 2, 3, test="sdkj", test2="sdkj")
monitored_chat2_app(4, 5, 6, test="sdkj", test2="sdkj")

print("DEBUG: wait for 15 seconds ~~~")
time.sleep(5)

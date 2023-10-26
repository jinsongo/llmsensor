from llmsensor import monitor, users, agent, tool
import openai
import os
# from dotenv import load_dotenv

openai.api_key = os.environ.get('OPENAI_API_KEY')

monitor(openai)

with users.identify('user1', user_props={"email": "wangjsty@cn.ibm.com"}):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hello world"}]
    )
    print("DEBUG: Output from with users.identify:")
    print(completion.choices[0].message.content)
    print("DEBUG: Output from with done !!!")


@agent("Monitored Chat App", user_id="wangjsty", tags=["test", "test2"])
def monitored_chat_app(a, b, c, test, test2):
    tool1("hello")
    print("DEBUG: Call OpenAI ChatCompletion.create ...")
    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "What is the OpenAI website URL?"}],
        user_id="wangjsty",
    )
    print(output)
    print(output.choices[0].message.content)
    tool2()
    return "Agent output"

@tool(name="tool 1", user_id="wangjsty")
def tool1(a):
    return "Output 1"

@tool()
def tool2():
    return "Output 2"

monitored_chat_app(1, 2, 3, test="sdkj", test2="sdkj")
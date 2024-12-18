import streamlit as st
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
from io import StringIO

import streamlit.components.v1 as components
# Set your OpenAI API key
# openai.api_key = 'YOUR_OPENAI_API_KEY'

if 'message' not in st.session_state:
    st.session_state.message = []

if 'plot_instruction' not in st.session_state:
    st.session_state.plot_instruction = []

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
st.title("📊CSV Analysis with GPT")


st.write("Upload a CSV file to analyze and interact with GPT for plotting.")


uploaded_file = st.file_uploader("Upload a CSV file", type="csv")


with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"

    st.markdown(
    "## 如何使用？\n\n"

    "1. **输入您的 OpenAI API 密钥**\n\n"

    "2. **上传从FluoXpert Vision 获取的阳性分析CSV**  \n\n"

    "3. **输入提示词**  （可以给用户提供提示词模板/教学）\n\n"

    "4. **等待图片生成** 对结果不满意可以调整提示词  \n\n"

    )

if uploaded_file is not None:
    # Read the uploaded CSV file into a Pandas DataFrame
    df = pd.read_csv(uploaded_file)
    st.write("Data Preview:")
    st.write(df.head(n=10))
    # only pass first 100 rows to api if dataframe is too large
    if len(df) > 101:
        txt = df.iloc[:101].to_string()
    else:
        txt = df.to_string()
    
    # Function to generate plot based on user instructions
    def generate_plot(plot_instruction):
        client = OpenAI(api_key=openai_api_key)
        
        prompt=f"""Given the following DataFrame:\n{txt}\n, which is the first 100 rows of a big dataframe. Generate a Python 
                    code to create a plot for the big DataFrame based user's instruction,only give the code in the answer, 
                    without any explaination or comment, so the user can direct run the code with python exec() function. 
                    assuming that my dataframe is provide and called 'df' so you do not need to read csv. name the figure as 'fig'. set figsize to (5,4). 
                    make sure texts in the plot are clear, visible. and also make the plots publication quality. 
                    User's instruction are given as following """
        #  and fontsize as 12
       
       
        # system_prompt = """ You are an expert in writing python code for plotting. 
        # You should never include codes that are harmful or risky for the system in you answer """
        system_msg = [{"role": "system", "content": "You are an expert in writing python code for plotting in scientific publication. You should never include codes that are harmful or risky for the system in you answer"},
                {"role": "system", "content": f'{prompt}'}]
        user_msg =  [{"role": "user", "content": message} for message in plot_instruction]
        print(system_msg)
        print(user_msg)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages= system_msg + user_msg
                # + [{"role": m["role"], "content": m["content"]} for m in plot_instruction]
            
        )
        

        response = completion.choices[0].message.content

        code = response.strip('` \n')
        if code.startswith('python'):
            code = code[6:]
        print("Generated Code:", code)
        st.session_state.message.append({"role": "assistant", "content": code})
        # Execute the code within a local environment
        try:
            # fig = plt.figure()
            local_vars = {}
            # global variable, local variable
            exec(code, {'plt': plt, 'pd': pd, 'df': df}, local_vars)
            with st.chat_message("assistant"):
                # st.write("Here's your plot:")
                st.pyplot(local_vars['fig'],use_container_width=False)
            # fig_html = mpld3.fig_to_html(local_vars['fig'])
            # components.html(fig_html, height=600)
            st.session_state.chat_history.append({"role": "assistant", "content": local_vars['fig']})
        except Exception as e:
            print(f"Error in executing the generated code: {e}")
            st.write(f"Error in executing the generated code: {e}")
            st.markdown('## Something went wrong, try again!')
    response_container = st.container(border = False)
    input_container = st.container(border = False)
    # Chat interface for user to input plot instructions
    with  response_container:
        for msg in  st.session_state.chat_history:
# write chat message in response container,
            if msg["role"] == 'assistant':
                with st.chat_message("assistant"):
                    st.write("Here's your plot:")
                    st.pyplot(msg['content'],use_container_width=False)
                    st.write('Let me know if you need further analysis or adjustments!')
            if msg["role"] == 'user':
                with st.chat_message("user"):
                    st.write(msg["content"])
        
    with input_container:
        user_input = st.chat_input("Enter your plot instructions")
        if user_input:
            st.session_state.message.append({"role": "user", "content": user_input}) # to 
            st.session_state.plot_instruction.append(user_input) # 
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            if not openai_api_key:
                st.info("Please add your OpenAI API key to continue.")
                st.stop()
            # st.write(f'Your instruction: {user_input}')
            # st.chat_message("user").write(user_input)
            generate_plot(st.session_state.plot_instruction)
            st.rerun()
            # with st.spinner('Wait for it...'):
            #     time.sleep(5)
else:
    st.write("Please upload a CSV file to continue.")

if st.button('Clear Session'):
    st.session_state.message = []
    st.session_state.plot_instruction = []
    st.session_state.chat_history = []
    st.rerun()



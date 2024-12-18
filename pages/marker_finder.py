import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
import pandas as pd
from streamlit_pdf_viewer import pdf_viewer
from serpapi.google_search import GoogleSearch
import json
from bs4 import BeautifulSoup
import time
import re
import ast
import PyPDF2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
OPENAI_API_KEY = 'sk-None-Yhc6UEcabs1bx1kdOIZsT3BlbkFJXUmsfJBaqilS3OurTa0Y'


SERP_API_KEY = '6c6ea99dc81db64f4d0a2fc1c19b6edadf1a1aca0188095c821826e8ef8a5bf9' # serpApi key

SEMANTIC_API_KEY = "LXL6qzpUGr547fhuIzV0J4npYJbR6fQEatEpI2SP"

# 谷歌搜索api
# 返回JSON
# 默认10条结果
def search_web(query):
    """
    
    
    """
    params = {
        "q": query,
        "api_key": SERP_API_KEY
    }
    response = requests.get("https://serpapi.com/search", params=params)
    results = response.json()
    return results



# 
def summarize_results(results):
    # Extract relevant snippets or URLs from the search results
    top_results = []
    for result in results.get("organic_results", []):
        print(result)
        top_results.append(result["snippet"])
    return "\n".join(top_results)




# 将谷歌搜索的结果发给GPT，由GPT判断每一条结果属于科研文献还是网站
# 如果是文献就下载pdf
# 如果是网站就用selenium爬取信息
def gpt_query_with_search(query):
    """
    
    
    
    """
    # Search the web
    search_results = search_web(query)
    # print(search_results)

    prompt = f"""Here are some search results for '{query}':\n{search_results}\n\n
                extract the reference as website from each result and decide if the result is from a publication 
                or from a website 
                with the following JSON format:
                Marker:
                Website:
                Publication or Website:
                only return the result in JSON format without any other explanation
            """
    # Ask GPT to generate a response
    client = OpenAI(api_key=openai_api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # with st.spinner('Extracting...'):
        #     time.sleep(5)
        response = completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Failed to analyze text with GPT-4: {e}")
        return None
    
# 从文献网站提取文章标题信息 
def get_paper_title(url):
    headers = {
                "authority": "www.google.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # add more headers as needed
        }
    # Send a GET request to the website
    time.sleep(0.01)
    response = requests.get(url,headers=headers)
    
    # If the request was successful
    if response.status_code == 200:
        # Parse the content of the page with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to extract the title from <title> tag (common in most cases)
        title = soup.title.string if soup.title else None
        
        # If <title> tag is not available, try to get title from <meta> tags
        if not title:
            title_tag = soup.find('meta', {'name': 'citation_title'})
            if title_tag:
                title = title_tag.get('content')
        
        return title
    else:
        return f"Error: Unable to fetch the page (status code {response.status_code})"
# 
# 用GPT从文章标题信息中提取出文章标题
def extract_title_with_gpt (text):
    prompt = f"""extract title of each paper from the following {text}
                only give the result as a list without any other explanation
        """
    client = OpenAI(api_key=openai_api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # with st.spinner('Extracting...'):
        #     time.sleep(5)
        response = completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Failed to analyze text with GPT-4: {e}")
        return None
    

# 根据文章标题，在scihub上找文章 
def search_scihub(title):
    """
    find doi of publication based on its title and then
    search in scihub based on its doi

    Param: title of publication
    -------#系统prompt

    Return: download url from Sci-Hub
    -------
    
    """
    url = 'https://sci-hub.se/'
    headers = {
                    "authority": "www.google.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        # add more headers as needed
            }
    # Get HTML content
    data = {'sci-hub-plugin-check': '', 'request': title}
    try :
        time.sleep(0.01)
        response = requests.post(url, data=data, headers=headers)
        html_content = response.text
        
        # Extract PDF URL
        pattern = "location.href='(.*?pdf)"
        pdf_path = re.findall(pattern, html_content)
        scihub_url = f'https:{pdf_path[0]}' if pdf_path else None
        print(scihub_url)
        
        
        return scihub_url

    except Exception as e:
        print(f"Failed to download : {e}")

        return None  

# 下载文章pdf，有可能会失败，重复3次  
no_of_retries = 3
def download_pdf(pdf_url:str, title:str):

    """
    download pdf with given URL,save it as 'title.pdf'
    Params:
    Return: 

    
    
    """
    for i in range(0,no_of_retries):
        time.sleep(3)
        try:
            headers = {
                    "authority": "www.google.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        # add more headers as needed
            }
            response = requests.get(pdf_url,headers=headers)
            response.raise_for_status()  # Ensure the request was successful

            # Use title as filename
            filename = f"{title}.pdf"

            # Write the PDF content to a file
            with open(filename, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {filename}")
            # st.write('✅Downloaded')
            
            if 'error' not in response:
                return filename
            else: continue
        except Exception as e:
            
            print(f"Failed to download {pdf_url}: {e}")
            # provide the link if failed to download 
            continue

    # return filename

# pdf转为text 
def extract_text_from_pdf(pdf_file):
    """
    convert pdf file to text.

    Param:
    Return:

    """

    try:
        with open(pdf_file, 'rb') as f:
            reader = PyPDF2.PdfReader(f,strict=False)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_file}: {e}")
        return None
    

# 用GPT从文本中（pdf或网站文本）提取 marker信息 
def analyze_pdf_with_gpt(text,celltype,tissue):
    """
    Send query to GPT api
    
    Param:
    -----------
    Return:
    -----------
    
    """
    prompt = f"""Extract information about all the protein markers used to identify {celltype} in {tissue} from the following text:\n\n{text},
    using the following JSON format:
    "Marker": " ",
    "Description": " "
    only write the marker name abbriviation in the "Marker"
    and only based on the information from the document. 
    only return the result in JSON format without any other explanation"""
    client = OpenAI(api_key=openai_api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in biochemistry who is good at reading and extracting information from text."},
                {"role": "user", "content": prompt}
            ]
        )
       
        response = completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Failed to analyze text with GPT-4: {e}")
        return None        

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"


# st.session_state 用来储存信息/状态
#  
if "result" not in st.session_state:
    st.session_state.result = None

if "txt_list_down" not in st.session_state:
    st.session_state.txt_list_down = []

if "df" not in st.session_state:
    st.session_state.df = {}

if "search" not in st.session_state:
    st.session_state.search = False

if "webtext" not in st.session_state:
    st.session_state.webtext = []


st.title("Protein Markers for Cell Type Identification")

# 组织类型
tissue_types = ['Eyes','Brain','Esophagus','Lung','Breast','Heart','Stomach','Kidney',
                'Adipose tissue','Liver','Pancreas','Blood','Spleen','Instestine','Embryo',
                'Bone Marrow','Ovary','Testis','Skin','Prostate']

# tissue_types_mouse = ['Eyes','Brain','Esophagus','Lung','Breast','Heart','Stomach','Kidney'
#                 'Adipose tissue','Liver','Pancreas','Blood','Spleen','Instestine','Embryo',
#                 'Bone Marrow','Ovary','Testis','Skin','Prostate']

#  物种类型
selected_species = st.selectbox('Species',['Human','Mouse'])

selected_tissue = st.selectbox('Tissue Type',tissue_types)
# if selected_species == 'Mouse':
#     selected_tissue = st.selectbox('Tissue Type',tissue_types_mouse)
# 用户输入细胞类型
input_celltype = st.text_input('Cell Type')

# 谷歌搜索所用的关键词
query = f"What are the protein markers generally used to identify {input_celltype} in {selected_species} {selected_tissue} "
if st.button('Search'):
    st.session_state.search = True
    
    if st.session_state.search == True:
        # GPT判断每条结果是来自科研文献还是网站
        # 结果返回为一个表格  
        json_data = gpt_query_with_search(query)
        # print(json_data)
        json_data = json_data.strip('` \n') #Remove "```" in the GPT response

        if json_data.startswith('json'):
            json_data = json_data[4:]  # Remove the first 4 characters 'json'

        # json text to json
        data = json.loads(json_data)
        # json to dataframe
        st.session_state.result = pd.DataFrame(data)
        
        # 结果分为 文献 和 网站, 分别处理
        pub_list = []
        web_list = []
        for i,row in st.session_state.result.iterrows():
            if row["Publication or Website"] == "Publication":
                pub_list.append(row["Website"])
            else:
                web_list.append(row["Website"])
        print(pub_list)
        print(web_list)


        # Extract information from publication
        

        title_list = []

        #  get title of the paper from the search result
        for p in pub_list:
            title_list.append(get_paper_title(p))
        # print(title_list)
        # st.write(title_list)
        
        #  extract title using gpt
        extracted_list = extract_title_with_gpt(str(title_list))
        # st.write(extracted_list)
        extracted_list = ast.literal_eval(extracted_list)

        # st.write(extracted_list)
        print(extracted_list)
        #  download papers by searching on scihub
        for t in extracted_list:
            # st.write(t)
            url = search_scihub(t)
            if url:
                pdf = download_pdf(url,t)
                if pdf: 
                    st.session_state.txt_list_down.append(extract_text_from_pdf(pdf))
                

        #  extract marker information from downloaded papers
        for i,text in enumerate(st.session_state.txt_list_down):
            try:
                json_data = analyze_pdf_with_gpt(text,input_celltype,selected_tissue)

                json_data = json_data.strip('` \n') #Remove "```" in the GPT response

                if json_data.startswith('json'):
                    json_data = json_data[4:]  # Remove the first 4 characters 'json'

                # json text to json
                data = json.loads(json_data)
                # st.write(json_data)
                # json to dataframe
                df = pd.DataFrame(data)
                
                st.write(f"df{i}")       
                st.dataframe(df)
                st.write(f"Reference: {pub_list[i]}") # provide the website url as reference
                st.write("--------------------------------------")
                print(f"add pub_{i} ")
                # store in df dictionary
                st.session_state.df.update({f'pub_{i}':df})

            except Exception as e:
                print(f"Failed to extract{e}")

        # Extract information from website with selenium
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 无头模式，不打开浏览器窗口
            options.add_argument('--disable-gpu')
            # options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36')
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            # service = Service()
            # driver = webdriver.Chrome(service=service, options=options)
            
            st.session_state.webtext = [] #用来储存爬取的网站文本信息
            try:
            # Open the website
                for i, w in enumerate(web_list):
                    driver.get(w)

                    # Wait for the page to load completely 
                    time.sleep(2+ i%3) # 添加随机等待时间，模拟人类行为

                    # Extract text from the body of the page 
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    st.session_state.webtext.append(page_text)
                    # Print the extracted text
                    print(f"result{i}:{page_text[:100]}")
                    print("---------------------------------------------")
            finally:
            # Close the browser window
                driver.quit()
        
        except Exception as e:
            print(e)

        #  extract information from website text
        for i,text in enumerate(st.session_state.webtext):

            try:
                json_data = analyze_pdf_with_gpt(text,input_celltype,selected_tissue)

                json_data = json_data.strip('` \n') #Remove "```" in the GPT response

                if json_data.startswith('json'):
                    json_data = json_data[4:]  # Remove the first 4 characters 'json'
                
                data = json.loads(json_data)
                # json to dataframe
                df = pd.DataFrame(data)
                
                st.dataframe(df)
                st.write(f"Reference: {web_list[i]}") # provide the website url as reference
                st.write("--------------------------------------")
                print(f"add web_{i} ")
                # store in dictionary: st.session_state.df
                st.session_state.df.update({f'web_{i}':df})

            except Exception as e:
                print(f"Failed to extract{e}")                

        # combine dataframes
        dfs = [df for n,df in st.session_state.df.items()]
        combined_df = pd.concat(dfs, ignore_index=True)

        # Group by 'marker'
        # 统计不同marker出现的频率
        summary1 = combined_df.groupby('Marker').size().reset_index(name='frequency')
        st.dataframe(summary1)




# 清除储存的信息
if st.button('clear'):
    st.session_state.search = False
    st.session_state.result = None
    st.session_state.df = {}
    st.session_state.txt_list_down = []
    st.session_state.webtext = []
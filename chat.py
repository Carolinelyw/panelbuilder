import streamlit as st
from openai import OpenAI
import requests
import pandas as pd
from io import StringIO
from PyPDF2 import PdfReader
import PyPDF2
from streamlit import session_state as ss
from streamlit_pdf_viewer import pdf_viewer
from serpapi.google_search import GoogleSearch
# import pandas as pd
import json
import time
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import streamlit.components.v1 as components
import base64
import re
from habanero import counts
from habanero import Crossref
from streamlit_extras.stylable_container import stylable_container
import datetime
import os



SERP_API_KEY = '6c6ea99dc81db64f4d0a2fc1c19b6edadf1a1aca0188095c821826e8ef8a5bf9' # serpApi key
SEMANTIC_API_KEY = "LXL6qzpUGr547fhuIzV0J4npYJbR6fQEatEpI2SP"
user_id = 'user01' 

#  uploaded paper as text
if "txt_list_up" not in st.session_state:
    st.session_state.txt_list_up = []
#  
if "pdf_to_view" not in st.session_state:
    st.session_state.pdf_to_view = None
#  downloaded paper as text
if "txt_list_down" not in st.session_state:
    st.session_state.txt_list_down = []
#  downloaded paper information({title:[doi,cite counts]})
if "downloaded_papers" not in st.session_state:
    st.session_state.downloaded_papers = []
#  download status information
if "download_info" not in st.session_state:
    st.session_state.download_info = []
#  title of all the papers
if "title_info" not in st.session_state:
    st.session_state.title_info = []
#  dataframe of extracted panel information
if "df" not in st.session_state:
    st.session_state.df = {}
#  search state
if "search" not in st.session_state:
    st.session_state.search = False
#  use to clear file uploader
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0
#  dfs to download  
if "df_csv" not in st.session_state:
    st.session_state.df_csv = None


# page config
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
)
# st.markdown("""
#     <style>
#     div[data-testid="stButton",type="secondary"] > button {
#         float: right;
#     }
#     </style>
#     """, unsafe_allow_html=True)
# 

# add chat history to json file
# 储存对话记录
def add_session_history(file_name, session_name, session_msg):
    """
    add session history to user's history file. if file doesn't exist, create a new one 
    based on input file name, file name is usually user's id
    
    Param:
    -----------
    Return:
    -----------
    
    """
    # Check if the file already exists
    if os.path.exists(file_name):
        # If the file exists, load the existing data
        with open(file_name, 'r',encoding="utf-8") as file:
            data = json.load(file)
    else:
        # If the file doesn't exist, start with an empty dictionary
        data = {}
    

    # Add the new session to the data
    data[session_name] = session_msg

    # Save the updated data back to the file
    with open(file_name, 'w',encoding="utf-8") as file:
        json.dump(data, file, indent=2,ensure_ascii = False)
    st.write('Saved!')

# 加载历史记录
def load_chat_histories():
    """
    load the chat history file based on user's id
    
    Param:
    -----------
    Return:
    -----------
    
    """
    if os.path.exists(f"{user_id}"):
        with open(f"{user_id}", "r") as file:
            return json.load(file)
    else:
        return {}

# 根据doi获取期刊名
def get_journal_name(doi):
    """
    Use Crossref API to get name of the journal based on doi of a publication
    
    Param: doi as string
    -----------
    Return: Journal name
    -----------
    
    """
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'message' in data and 'container-title' in data['message']:
            journal_name = data['message']['container-title'][0]
            return journal_name
        else:
            return "Journal name not found"
    else:
        return f"Error: {response.status_code}"

# 根据doi获取引用数
def get_cite_count_from_doi(doi):
    """
    Use Crossref API to get number of citaions based on doi of a publication
    
    Param:
    -----------
    Return:
    -----------
    
    """
    try:
        return counts.citation_count(doi)

    except Exception as e:
        print(f'error by get cite counts from doi:{e}')
        return f'unknown'

# 根据文章名获取doi
def get_doi_from_title(title):
    """
    Use Crossref API to get doi based on title of a publication
    
    Param: title of publication as string
    -----------
    Return: doi as string
    -----------
    
    """
    
    
    time.sleep(0.1)
    # Construct the CrossRef API search URL
    url = f"https://api.crossref.org/works?query.title={title}&rows=1"  # Limit to 1 result

    # Send GET request to the API
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if any items are returned
            if 'message' in data and 'items' in data['message'] and len(data['message']['items']) > 0:
                # Get the DOI from the first result
                doi = data['message']['items'][0].get('DOI', 'DOI not found')
                return doi
            else:
                return 'No results found'
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        print(f'error by get doi from title: {e}')


# 
def download_button(object_to_download, download_filename):
    """
    generates an HTML page with an embedded download link for the specified object. 
    The object is encoded as a Base64 string and used to create a downloadable 
    link that triggers an automatic download when the page is rendered. 
    
    Params:
    ------
    object_to_download:  The object to be downloaded.
    download_filename (str): filename and extension of file. e.g. mydata.csv,
    Returns:
    -------
    (str): the anchor tag to download object_to_download
    """


    try:
        b64 = base64.b64encode(object_to_download.encode()).decode()

    except AttributeError as e:
        b64 = base64.b64encode(object_to_download).decode()

    dl_link = f"""
    <html>
    <head>
    <title>Start Auto Download file</title>
    <script src="http://code.jquery.com/jquery-3.2.1.min.js"></script>
    <script>
    $('<a href="data:text/csv;base64,{b64}" download="{download_filename}">')[0].click()
    </script>
    </head>
    </html>
    """
    return dl_link

# 
def download_df(object_to_download, download_filename):
    """
    Params:
    Return:
    
    """
    # df = pd.DataFrame(st.session_state.col_values, columns=[st.session_state.col_name])
    components.html(
        download_button(object_to_download, download_filename),
        height=0,
    )


# 在谷歌学术上搜索文章  
def search_google_scholar(query):
    """
    search with google scholar and download publications based on query.
    if not available in google scholar, try to search and download in Sci-Hub.
    
    Param:
    ------------------
    Return:
    ------------------
    """
    st.session_state.txt_list_down =[]
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": NUM,
        "as_ylo": YEAR_O,
        "as_yli": YEAR_I,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    all_dataframe = []  # List to hold data for all papers
    scihub_url = None
    # Get the results
    # google scholar api response
    for i,result in enumerate(results.get("organic_results", [])):
        print(f"Title: {result['title']}")
        st.write(f"[{i+1}/{NUM}] Title: {result['title']}")
        doi_tmp = get_doi_from_title(result['title'])
        st.session_state.downloaded_papers.append(f"""[{i+1}/{NUM}] Title: {result['title']} \n\n DOI: {doi_tmp} 
                                                  \n\n Cited counts: {get_cite_count_from_doi(doi_tmp)} 
                                                  \n\n Journal: {get_journal_name(doi_tmp)}""")
        
        # st.session_state.download_info.append(f"Title: {result['title']}")
        st.session_state.title_info.append(result['title'])
        print(f"Link: {result['link']}")
        print(f"Snippet: {result.get('snippet', 'No snippet available')}")
        resources = result.get('resources', [])
        pdf_found = False
        
        for resource in resources:
            if resource.get('file_format', '').lower() == 'pdf':
                pdf_found = True
                print(f"PDF Link: {resource.get('link')}")
                # download pdf
                pdf_file = download_pdf(resource.get('link'), result['title'])
                if pdf_file:
                    
                    st.session_state.download_info.append('✅ Downloaded')
                    
                    st.session_state.txt_list_down.append(extract_text_from_pdf(pdf_file))
                else:   
                    # doi =  get_doi_from_title(result['title'])   
                    # st.write(doi)   
                    scihub_url = search_scihub(doi_tmp)
                
                    if scihub_url:
                        pdf_file = download_pdf(scihub_url,result['title'])
                        if pdf_file:
                            
                            st.session_state.download_info.append('✅ Downloaded')
                            st.session_state.txt_list_down.append(extract_text_from_pdf(pdf_file))
                        else:
                            st.session_state.download_info.append(f"❌ Failed to download. You can download it manually here: \n\n {resource.get('link')}")
                    else:
                        st.session_state.download_info.append(f"❌ PDF not available. You can download it manually here: \n\n {resource.get('link')}")

                    

        if not pdf_found:

            scihub_url = search_scihub(doi_tmp)
            if scihub_url:
                pdf_file = download_pdf(scihub_url,result['title'])
                if pdf_file:
                    # st.write('✅ Downloaded')
                    
                    st.session_state.txt_list_down.append(extract_text_from_pdf(pdf_file))
                    st.session_state.download_info.append('✅ Downloaded')
                else:
                    st.session_state.download_info.append(f"❌ PDF not available. You can download it manually here: \n\n {result['link']}")
            else:
                st.session_state.download_info.append(f"❌ PDF not available. You can download it manually here: \n\n {result['link']}")
            
# 
#
# 根据文章名在scihub上找文章
def search_scihub(title):
    """
    find doi of publication based on its title and then
    search in scihub based on its doi

    Param: title of publication
    -------

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
    # Step 1: Get HTML content
    data = {'sci-hub-plugin-check': '', 'request': title}
    try :
        time.sleep(0.01)
        response = requests.post(url, data=data, headers=headers)
        html_content = response.text
        
        # Step 2: Extract PDF URL
        pattern = "location.href='(.*?pdf)"
        pdf_path = re.findall(pattern, html_content)
        scihub_url = f'https:{pdf_path[0]}' if pdf_path else None
        print(scihub_url)
        
        
        return scihub_url

    except Exception as e:
        print(f"Failed to download : {e}")
        # provide the link if failed to download 
        # st.session_state.download_info.append(f'❌ Failed to download. You can download it manually here: \n\n {pdf_url}')
        return None   
#  



#  alternative for google scholar
def search_semantic_schloar(query):
    """
    search with semantic scholar and download publications based on query.
    if not available, try to search and download in Sci-Hub.
    
    Param:
    ------------------
    Return:
    ------------------
    """
    http = Session()
    http.mount('https://', HTTPAdapter(max_retries=Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"HEAD", "GET", "OPTIONS"}
    )))

    # Define the search query and filters
    query = query
    fields = "paperId,title,year,authors,fieldsOfStudy,openAccessPdf,citationCount" # information to return
    limit = NUM  # number of papers to search in one request
    publication_types = "JournalArticle,Review"  # Filter by publication types
    fields_of_study = ""  # Filter by fields of study
    year = f"{YEAR_I}-{YEAR_O}"  # Papers published between YEAR_I and YEAR_O

    response = http.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers={'x-api-key': SEMANTIC_API_KEY},
        params={
            'query': query,
            'fields': fields,
            'limit': limit,
            'publicationTypes': publication_types,
            'fieldsOfStudy': fields_of_study,
            'year': year,
            'openAccessPdf':'',
            
        }
    )

    response.raise_for_status()  # Ensures we stop if there's an error
    data = response.json()

    # Output the fetched data
    print(f"Total estimated matches: {data.get('total')}")
    for i,paper in enumerate(data.get('data', [])):
        print(f"Paper ID: {paper.get('paperId')}")
        print(f"Title: {paper.get('title')}")
        st.write(f"[{i+1}/{NUM}] Title: {paper.get('title')}")
        doi_tmp = get_doi_from_title(paper.get('title'))
        # st.session_state.downloaded_papers.append(f"""Title: {paper.get('title')} \n\n DOI: {doi_tmp} 
        #                                           \n\n Cited counts: {get_cite_count_from_doi(doi_tmp)}
        #                                              \n\n Journal: {get_journal_name(doi_tmp)}""")
        st.session_state.downloaded_papers.append(f"""[{i+1}/{NUM}] Title: {paper.get('title')} \n\n DOI: {doi_tmp} 
                                            \n\n Cited counts: {get_cite_count_from_doi(doi_tmp)}
                                                """)
        st.session_state.title_info.append(paper.get('title'))
        print(f"Year: {paper.get('year')}")
        print(f"cite counts:{paper.get('citationCount')}")
        print(f"URL: {paper['openAccessPdf']['url']}")
        print("---")
        pdf_file = download_pdf(paper['openAccessPdf']['url'], paper.get('title'))
        
        if pdf_file: # if pdf is downloaded 
            
            st.session_state.download_info.append('✅ Downloaded')
            
            st.session_state.txt_list_down.append(extract_text_from_pdf(pdf_file))
        
        else:  # pdf not downloaded
            # doi =  get_doi_from_title(result['title'])   
            # st.write(doi)   
            scihub_url = search_scihub(doi_tmp) # search in Sci-hub
        
            if scihub_url: # found in Sci-hub
                pdf_file = download_pdf(scihub_url,paper.get('title'))
                if pdf_file:
                    
                    st.session_state.download_info.append('✅ Downloaded')
                    st.session_state.txt_list_down.append(extract_text_from_pdf(pdf_file))
                else:
                    st.session_state.download_info.append(f"❌ Failed to download. You can download it manually here: \n\n {paper['openAccessPdf']['url']}")
            else:
                st.session_state.download_info.append(f"❌ PDF not available. You can download it manually here: \n\n {paper['openAccessPdf']['url']}")




# 根据url下载pdf
def download_pdf(pdf_url:str, title:str):
    """
    download pdf with given URL,save it as 'title.pdf'
    Params:
    Return: 

    
    
    """
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

        # Clean title to use it as a filename
        filename = f"{title}.pdf"

        # Write the PDF content to a file
        with open(filename, 'wb') as f:
            f.write(response.content)

        print(f"Downloaded: {filename}")
        # st.write('✅Downloaded')
        
        return filename
    except Exception as e:
        print(f"Failed to download {pdf_url}: {e}")
        # provide the link if failed to download 
        
        return None


# pdf转化为text
def extract_text_from_pdf(pdf_file):
    """
    convert pdf file to text.

    Param:
    Return:

    """

    try:
        with open(pdf_file, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_file}: {e}")
        return None

#  extract information from text 
#  用GPT 提取文章信息
def analyze_pdf_text_with_gpt4(text):
    """
    Send query to GPT api
    
    Param:
    -----------
    Return:
    -----------
    
    """
    prompt = f"""Extract information about all the protein markers used by immunofluorescence from the following document:\n\n{text},
    using the following JSON format:
    marker: 
    name: 
    description: 
    primary_antibody_clone:
    antibody_source:
    catalog_number:
    fluorophore: 
    dilution: 
    staining_method:
    target_location:
    associated_function: 
    clinical_relevance: 
    and only based on the information from the document. if there is no information about something, simply write unknown
    only return the result in JSON format without any other explanation"""
    client = OpenAI(api_key=openai_api_key)
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in biochemistry and immunofluorescence who is good at reading and extracting information from literatures."},
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
    
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password",help=" API key")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"

    # st.markdown(
    # "## How to use?\n\n"
    # "1. Enter your Openai API key \n\n"
    # "2. Chat with FluoXpert Chatbot about your research project. You may ask FluoXpert Chatbot to suggest you search keywords \n\n"
    # "3. Find out your favourite search keyword, type in to search and download publications.\n\n"
    # "4. Download publications by yourself and Upload to the server \n\n"
    # "5. Press the 'Extract Panel Information' button to extract protein marker panel information and download.\n\n"
    # "6. Press the 'Clear Chat'/'Clear result' button to start a new chat/search session.\n\n"
    # )
    if st.toggle('使用说明'):
        st.markdown(
        "## 如何使用？\n\n"

        "1. **输入您的 OpenAI API 密钥**\n\n"

        "2. **与 FluoXpert Chatbot探讨您的研究项目:**  您还可以让 FluoXpert Chatbot为您建议搜索关键词。\n\n"

        "3. **搜索和下载文献:**  找到合适的搜索关键词后，输入进行搜索并下载相关文献。\n\n"

        "4. **上传文献:**  您也可以手动下载并上传相关文献。\n\n"

        "5. **提取信息:**  点击“提取信息”按钮，即可提取文献中蛋白标记物组合信息并下载。\n\n"

        "6. **开始新的会话:**  点击“清空聊天”或“清空结果”按钮，以开始新的聊天或搜索会话。\n\n"

        )   



st.title("🧑‍🔬🧬 FluoXpert Chat",help="FluoXpert Chat 是一款智能对话工具，专为多重免疫荧光实验和分析而设计，\n\nFluoXpert Chat 能够根据用户输入提供实验设计建议、进行数据分析。\n\n.........\n\n........")
st.caption(datetime.date.today())
#  system prompt for GPT
# 系统prompt
system_msg = "you are an expert in biochemistry and immunofluorescence, you will guide the user to find out protein markers panel for their research. after answering a question, you may ask user a question to help them clarify their needs. when the user ask you to summarize keyword for searching literature, always include 'immunofluorescence' in the each keyword that you give."

#  user instruction msg
# 用户指引
greating_msg = """您好，我是FluoXpert聊天机器人，专注于帮助您设计和优化多重免疫荧光实验中的蛋白标记物组合。我可以根据您的研究需求，为您推荐抗体标记物组合。

您可以通过以下几种方式与我互动：

\n\n 描述您的研究需求： 您可以详细说明研究的主题（如肿瘤微环境、免疫逃逸机制、特定信号通路等），目标（如检测细胞类型、信号通路活性或空间分布等）和组织类型。
\n\n 关键词提取与文献支持： 根据您的需求，我可以总结搜索关键词并为您下载相关文献，帮助您了解领域中的标记物组合趋势。
\n\n 上传现有文献： 如果您已有相关文献，您可以上传给我，我会提取其中关于多重免疫荧光标记物组合的具体信息。
\n\n 定制化推荐： 基于您的研究和文献数据，我会为您提供个性化的标记物组合建议，支持您的实验设计。
\n\n 无论您处于哪个研究阶段，我都可以为您的实验提供有效的支持。
请告诉我，您目前的研究方向是什么，我会为您提供针对性的帮助！"""

# 您好，我是FluoXpert聊天机器人，可以帮助您根据您的研究主题选择多重免疫荧光实验的蛋白标记物组合。您可以与我聊天，来阐明您的研究需求并让我总结搜索关键词。
# 我可以根据您的搜索关键词下载相关文献。您也可以上传文献，我会从中提取相关的组合信息。我能如何帮助您？

#  layout main page: 3 columns
col1, col, col2 = st.columns([1.1,0.01,1.2])
with col2:
    ######################
    ##  chat module     ##
    ######################
    #  containers to display response and user input
    response_container = st.container(height = 750,border = False)
    input_container = st.container(border = False)

    with response_container:
        # all queries and response are stored in "messages" to achieve memory of GPT
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": f"Hi, I am FluoXpert chatbot. I can help you with selecting protein marker panels for your multiplexed immunofluorescence experiments based on your research topic. You may chat with me to clarify your research need. I can also download publications based on your search keywords. You may also upload publications and I will extract the panel information from them. How can I help you? \n\n {greating_msg}" }]
            st.session_state.messages.append({"role":"system","content":system_msg})
        for msg in st.session_state.messages:
            # write chat message in response container,
            if msg["role"] == 'assistant':
                st.chat_message(msg["role"]).write(msg["content"])
            if msg["role"] == 'user':
                st.chat_message(msg["role"]).write(msg["content"])

    with input_container:
        # when user input a message 
        if prompt := st.chat_input():
            if not openai_api_key:
                st.info("Please add your OpenAI API key to continue.")
                st.stop()
            client = OpenAI(api_key=openai_api_key)
            # save chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with response_container:
                st.chat_message("user").write(prompt)  
            # request an API call
            stream = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                        stream=True,
                    )
            with response_container:
                # write response
                response = st.chat_message("assistant").write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    
    col21, col22  = st.columns(2)
    with col21:
            # save chat history of one session as json
            # one json file for each user
            #  Example:
            #   "session_name": 
            # {
            #   "user_id": "user_001",
            #   "date": "2024-11-01",
            #   "messages": [
            #     {
            #       "role": "user",
            #       "content": "Question"
            #     },
            #     {
            #       "role": "assistant",
            #       "content": " Answer"
            #     }
            #   ]
            # }
            # # 
        # TODO 
        # if st.button('Save Chat History'):
            with st.popover("Save Chat History"):
                session_name = st.text_input("Save As")
                if st.button('Confirm'):
                    if session_name :
                        # save chat history, except the first two(system msg)
                        add_session_history(user_id, session_name, st.session_state.messages[2:])
    with col22:
        with stylable_container(
            key="chat_with_df",
            css_styles="""
            button{
                float: right;
            }
            """
        ):

            if st.button('Reset Chat'):
                del st.session_state['messages']
                st.rerun()
    # clear conversation with gpt


with col1:
    st.markdown('')
    with st.container(height = 500,border = False):
    ######################
    ##  search module   ##
    ######################
        
        keyword = st.text_input("Search Keyword", "", help = "搜索和下载文献: \n\n找到合适的搜索关键词后，\n\n输入进行搜索并下载相关文献。\n\n 您可以选择搜索文章的数量以及限定年份")
        col11, col12, col13 = st.columns([1,1,1])
        with col11:
            # number of papers to search
            NUM = st.number_input('Number of papers, default = 10',min_value=1,max_value=20,value=10)
        with col12:
            # start from year....
            YEAR_I = st.number_input('From year... , default = 2000',min_value=1950,max_value=datetime.date.today().year,value=2000)
        with col13:
            # until year ....
            YEAR_O = st.number_input('Until year..., default = 2024',min_value=1951,max_value=datetime.date.today().year,value=2024)
        # pick search engine
        engine = st.radio(label='Pick a search engine',    options=[
                            "Google Scholar",
                            "Semantic Scholar",
                        ],)
        #  if search button is clicked
        if st.button('Search & Download'):
            st.session_state.search = True
            if engine == "Google Scholar":
                search_google_scholar(keyword)
            if engine ==  "Semantic Scholar":
                search_semantic_schloar(keyword)
        #  search result
        if st.session_state.search == True:    

            st.write('-----------------------------------------------------\n\n')
            
            for i, t in enumerate(st.session_state.download_info):
                # 
                # print information about downloaded papers
                
                st.write(st.session_state.downloaded_papers[i])
                   
                
                st.write(t)
                # check box to view pdf
                if st.checkbox('View PDF',key=f'pdf{i}'):
                    with response_container:
                        try:
                            # st.session_state.downloaded_papers[i]: Title: xxxxxxDOI: xxxxx ..... 
                            pdf_viewer(f'{st.session_state.downloaded_papers[i].split("DOI")[0].split("Title: ")[1].strip()}.pdf')
                        except Exception as e:
                            st.write('PDF Not Downloaded')

                st.write('-----------------------------------------------------------------\n\n')

                        
    with st.container(height =500,border = False):
 
    ######################
    ##  upload module   ##
    ######################


        # File uploader. Access the uploaded ref via a key.
        uploaded_files = st.file_uploader("Upload PDF file", type=('pdf'),  key=st.session_state["file_uploader_key"],accept_multiple_files=True
                                          ,help= "上传文献: \n\n您也可以手动下载并上传相关文献，进行分析。")

        if uploaded_files:

            st.session_state.txt_list_up = []
            for pdf_file in uploaded_files:
                
                # convert pdf to text and store in list
                reader = PyPDF2.PdfReader(pdf_file)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ""
                # Display the filename and store the extracted text
                st.write(f"✅ Filename: {pdf_file.name}")
                # store text of pdf 
                st.session_state.txt_list_up.append(text)
                # store title of paper
                st.session_state.title_info.append(pdf_file.name)


    ######################
    ##  extract module  ##
    ######################
        #  click extract panel button
        if st.button('Extract Panel Information',key = 'extract1'):
            list_tmp = []
            # list of downloaded paper + uploaded paper
            list_tmp = st.session_state.txt_list_down + st.session_state.txt_list_up
            st.write(len(list_tmp))
            # non-empty 
            if len(list_tmp) > 0:
                for i,t in enumerate(list_tmp):
                    try:
                        #  analyze each text with GPT
                        json_data = analyze_pdf_text_with_gpt4(t)

                        json_data = json_data.strip('` \n') #Remove "```" in the GPT response

                        if json_data.startswith('json'):
                            json_data = json_data[4:]  # Remove the first 4 characters 'json'

                        # json text to json
                        data = json.loads(json_data)
                        # json to dataframe
                        df = pd.DataFrame(data)
                        # store in df dictionary
                        st.session_state.df.update({i:df})

                    except Exception as e:
                        print(f"Failed to extract{e}")


                                
            else:
                placeholder = st.empty()
                placeholder.text('No file available.')
                time.sleep(1)  # Wait for 1 seconds
                placeholder.empty() 



        # download selected df, use st.form 
        # A form is a container that visually groups other elements and widgets together, 
        # and contains a Submit button. When the form's Submit button is pressed,
        # all widget values inside the form will be sent to Streamlit in a batch.
        with st.form('download'): 
            # dataframe to store selected rows
            selected_dfs = []     
            for n,df in st.session_state.df.items():
                
                selected = st.checkbox(f'Paper {n+1}')# TODO add paper title

                event = st.dataframe(df,on_select="rerun",selection_mode=["multi-row"],key=f'df{n}')
                
                if selected and event.selection.rows:
                    selected_dfs.append((n, df.iloc[event.selection.rows]))
               
            submit = st.form_submit_button("Download dataframe")
            
            if submit:
                if selected_dfs:
                    # Create an in-memory string buffer
                    f = StringIO()
                    # Write each dataframe's title and content to buffer
                    for n, df in selected_dfs:
                        f.write(f"Title: {st.session_state.title_info[n]}")
                        f.write('\n')
                        df.to_csv(f, index=False)
                        f.write('\n')  # Add new lines between CSVs
                    
                    # Get CSV data from buffer
                    df_csv = f.getvalue()
                    st.session_state.df_csv = df_csv

                    download_df(st.session_state.df_csv,'panel_info')
        
        c11, c12= st.columns(2)

        with c11:
            #      
            # summarize frequency of markers, antibody company used in downloaded papers 
        
                if st.button('Antibody Information'):
                    try:
                        dfs = [df for n,df in st.session_state.df.items()]
                        combined_df = pd.concat(dfs, ignore_index=True)

                        # Group by 'marker' and 'antibody_source' to get frequency of each pair
                        summary1 = combined_df.groupby('marker').size().reset_index(name='frequency')
                        summary2 = combined_df.groupby(['marker', 'antibody_source']).size().reset_index(name='frequency')

                        # Display the summary
                        st.dataframe(summary1)      
                        st.dataframe(summary2)        
                    except Exception as e:
                        st.write('no file available')

        with c12:
            #  stylable container to make button right-aligned 
            with stylable_container(
                key="chat_with_df",
                css_styles="""
                button{
                    float: right;
                }
                """
            ):

            #  chat with dataframe using gpt
                if st.button('Chat With Dataframe'):
                    try:
                        
                        st.session_state['messages'] = [] # clear previous chat history with gpt 
                        dfs = [df for n,df in st.session_state.df.items()]
                        combined_df = pd.concat(dfs, ignore_index=True)
                        df_txt = combined_df.to_string() # convert df to string
                        
                        if not openai_api_key:
                            st.info("Please add your OpenAI API key to continue.")
                            st.stop()
                        client = OpenAI(api_key=openai_api_key)
                        # use text of the dataframe as prompt
                        # add it to chat messages
                        st.session_state.messages.append({"role": "system", "content": f'You are an expert at extracting information from dataframes. You are given the following dataframe{df_txt}, The user will ask questions about this dataframe. Please give answers only based on the content of the dataframe.'})
                        
                        with response_container:
                            st.chat_message("user").write(combined_df )  
                        # request an API call
                        stream = client.chat.completions.create(
                                    model="gpt-4o-mini", 
                                    messages=[
                                        {"role": m["role"], "content": m["content"]}
                                        for m in st.session_state.messages
                                    ],
                                    stream=True,
                                )
                        with response_container:
                            # write response
                            response = st.chat_message("assistant").write_stream(stream)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    except Exception as e:
                        st.write('no file available')

        # clear session_state
    if st.button('Clear Results'):
        
        st.session_state["file_uploader_key"] += 1   # clear file_uploader by replacing it with a new file_uploader
        st.session_state.txt_list_up = []
        st.session_state.txt_list_down = []
        st.session_state.downloaded_papers = []
        st.session_state.download_info = []
        st.session_state.df = {}
        st.session_state.title_info = []
        st.session_state.search = False
        #  rerun the script to make changes
        st.rerun()




######################
##      sidebar     ##
######################
# save/load chat history 


with st.sidebar:
    chat_histories = load_chat_histories()

    # Sidebar for selecting a previous chat session
    session_names = list(chat_histories.keys())
    if st.toggle('Load session history',help ="打开后选择历史记录查看，并可以继续对话。结束后点击对话框右下角'Reset Chat'重置聊天"):
        st.session_state['messages'] = []
        selected_session = st.sidebar.selectbox("Select a previous session", session_names, placeholder="Select session history...",index=None)
        if selected_session:
            
            chat_history = chat_histories[selected_session]
            
            with response_container:
                st.chat_message("assistant").write(f'已加载历史记录{selected_session}')
                for message in chat_history:
                    st.session_state['messages'].append(message)
                    
                    if message["role"] == 'assistant':
                        st.chat_message("assistant").write(message["content"])
                    elif message["role"] == 'user':
                        st.chat_message("user").write(message["content"])
        
            
            st.write(f"已加载: {selected_session}")
   
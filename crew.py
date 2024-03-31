import os
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from tools.elastic_tool import EventSearchTool
from tools.cve_avd_tool import CVESearchTool
from langchain_community.llms import HuggingFaceHub, HuggingFaceEndpoint, Ollama
from dotenv import load_dotenv

load_dotenv()

sys_prompt_wrn = '''You are a cybersecurity expert. You have been asked to explain a complex cybersecurity concept in technical terms. You need to provide a detailed and technical explanation of the concept in a way that is easy to understand for a non-technical audience. You should include relevant details and examples to help illustrate the concept. You should also provide any necessary background information to help the audience understand the context of the concept. Your explanation should be clear, concise, and engaging. Your goal is to provide a clear and informative explanation that helps the audience understand the concept and its importance in the field of cybersecurity.
And most importantly, you should not provide any disclaimers or additional information. You should focus on providing a clear and concise explanation of the concept in simple terms. And don't write code nor execute it, just provide the information. Also, don't use any tools from your end, just use the information provided to you.
AGAIN DON'T USE TOOLS NO MATTER WHAT, JUST USE THE INFORMATION PROVIDED TO YOU.
'''

llm = Ollama(model="openhermes", base_url="https://7625-41-87-148-33.ngrok-free.app", temperature=0.1, num_predict=-1)
wrn = Ollama(model="wrn", base_url="https://7625-41-87-148-33.ngrok-free.app", temperature=0.1, system=sys_prompt_wrn)

# print("## Test llm : ")
# print(llm.invoke("Hello, /how are you?"))

# print("## Test wrn : ")
# print(wrn.invoke("Hello, how are you?"))



ioc_search_tool = EventSearchTool().search
event_id_search_tool = EventSearchTool().get_event_by_id
cve_search_tool = CVESearchTool().cvesearch

# Define your agents with roles and goals
class HunterCrew:
  def __init__(self, query):
    self.query = query

  def run(self):
    searcher = Agent(
      role='Searcher of events',
      goal='Ask the user for a query, then use the EventSearchTool to then search the keyword (can be an IP address/ hash/ registry key/ domain...) or an event ID, then use the search results to answer the user query in a technical way. while providing any necessary background information to help the audience understand the context of the concept. ',
      backstory="""You work at a big events archive.
      Your expertise is taking user's question and getting the search results from the search tool.
      You should then use search results to provide and thourough explanation to user.
      Don't provide any disclaimers nor additional information, just provide the information.
      If the search results is empty or not found, just tell it to the user.
      Also, while answering the question, provide event_id and any links of external analysis if available.
      """,
      verbose=True,
      allow_delegation=True,
      tools=[ioc_search_tool, event_id_search_tool],  
      llm=llm
    )
    cve_searcher = Agent(
      role='CVE Searcher',
      goal='Prompt the user for a CVE ID/keyword, then utilize the CVE Search Tool to search for information related to that CVE ID/keyword, and provide the search results to the explainer agent for further explanation.',
      backstory="""You are an expert in CVE (Common Vulnerabilities and Exposures) research and analysis. Your role involves retrieving detailed information about CVEs based on user queries.
      DON'T summarize the information, pass it as it is to the explainer agent.""",
      verbose=True,
      allow_delegation=True,
      function_calling_llm=None,
      tools=[cve_search_tool],
      llm=llm
    )
    explainer = Agent(
      role='Security events Explainer and Analyser',
      goal=f'Provide detailed and technical explainations to user question based on search results. Here is the query from the user that you need to explain: {self.query} DO NOT USE ANY TOOLS OR DELEGATE TO OTHER AGENTS.',
      backstory="""You are a renowned Cybersecurity analytics expert, known for your insightful explainations.
      You transform complex data into compelling reports. Don't tell any disclaimers, just provide the information.
      Don't look for supplementary information and don't use any tools nor create them, just use the information provided to you.
      Answer: """,
      verbose=True,
      allow_delegation=False,
      llm=wrn,
    )

    general_agent = Agent(
      role='Provide assistance to the user!',
      goal='You are a helpful assistant, your goal is to assist the user',
      backstory="""You are a helpful assistant, your goal is to assist the user. You can answer general questions like : how are you? and who are you?""",
      verbose=True,
      allow_delegation=True,
      llm=llm
    )

    entry_task = Task(
    description=f"""Identify the intent of the user query and delegate it to the appropriate agent for further processing.
    If the query is related to CVE (Common Vulnerabilities and Exposures), delegate to the CVE Searcher agent. 
    If the query is related to an event (contains an ip or a hash or an indicator in general), delegate it to the Searcher of events agent. Otherwise, just answer it yourself.
    Here is the query from the user that you need to process: {self.query}""",
    agent=general_agent  # Default to general agent
    )


    # Create tasks for your agents
    task3 = Task(
        description=f"""Take a user query that contains a CVE ID, search for information related to that CVE ID, and then pass the search results to the explainer agent.
        Don't summarize the information nor modify it, pass it as it is to the explainer agent.
        If the user query doesn't contain a CVE ID, delegate it to the general agent.
        AGAIN DON'T summarize the information, pass it as it is to the explainer agent
        Also, pass ALL the information to the explainer agent, don't skip anything.

        Here is the query from the user that you need to search for: {self.query}""",
        agent=cve_searcher,
        expected_output=dedent("""
      Explain the following CVE-XXXX-XXXXX in simple terms:

      - CVE ID: CVE-XXXX-XXXXX
      - Status: 
      - Description: 
      - CVSS Score: 
      - Affected Configurations: 
      - References: [put links here (github, reports, virus total, etc)]
                               
      - CVE ID: CVE-XXXX-XXXXX
      - Status: 
      - Description: 
      - CVSS Score: 
      - Affected Configurations: 
      - References: [put links here (github, reports, virus total, etc)]                               
    """)
    )

    task1 = Task(
      description=f"""Take a user query that contain and indicator of compromise, 
      search for the keyword using ioc_search_tool and then explain the search results in a technical way to the user while answering the following query {self.query}
      You MUST use the tool provided to you to search for the keyword.
      This is how to use the tool: `Use Tool: Event search Tool(keyword: str)`.
      
      here is the query from the user that you need to search for: {self.query}""",
      agent=searcher
    )


    task2 = Task(
      description=f"""Using the search results provided by the searcher agent, develop a bit detailed and compelling/interesting technical explanation of the 
      text provided to you about Cybersecurity answering to the following query {self.query}""",
      agent=explainer
    )

    # task3 = Task(
    #   description=f"""Answer the user's message in a human way {self.query}, no need to use any tools or delegate to other agents""",
    #   agent=general_agent
    # )

    # Instantiate your crew with a sequential process
    HunterCrew = Crew(
      agents=[explainer, searcher],
      tasks=[task1],
      verbose=2, # You can set it to 1 or 2 to different logging levels
      manager_llm=llm
    )

    # print(llm._default_params)
    # print(wrn._default_params)
    return HunterCrew.kickoff()
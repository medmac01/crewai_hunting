import os
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from tools.elastic_tool import EventSearchTool
from tools.cve_avd_tool import CVESearchTool
from langchain_community.llms import HuggingFaceHub, Ollama
from dotenv import load_dotenv

load_dotenv()

# llm = HuggingFaceHub(
#     # repo_id="mistralai/Mistral-7B-Instruct-v0.2",
#     repo_id="HuggingFaceH4/zephyr-7b-beta",
#     task="text-generation",
#     model_kwargs={
#         "max_new_tokens": 512,
#         "temperature": 0.1,
#         "return_full_text":False
#     },
# )
llm = Ollama(model="openhermes", base_url="https://ed3f-41-87-148-33.ngrok-free.app")
wrn = Ollama(model="wrn", base_url="https://ed3f-41-87-148-33.ngrok-free.app")

# print("## Test llm : ")
# print(llm.invoke("Hello, /how are you?"))

# print("## Test wrn : ")
# print(wrn.invoke("Hello, how are you?"))



ioc_search_tool = EventSearchTool().search
cve_search_tool = CVESearchTool().cvesearch

# Define your agents with roles and goals
class HunterCrew:
  def __init__(self, query):
    self.query = query

  def run(self):
    searcher = Agent(
      role='Searcher of events',
      goal='Ask the user for a query, then use the EventSearchTool to then search the keyword (can be an IP address/ hash/ registry key/ domain...), and provide the search results to the explainer agent so it can then be explained',
      backstory="""You work at a big events archive.
      Your expertise is taking user's question and getting the search results""",
      verbose=True,
      allow_delegation=True,
      tools=[ioc_search_tool],
      llm=llm
    )
    cve_searcher = Agent(
      role='CVE Searcher',
      goal='Prompt the user for a CVE ID/keyword, then utilize the CVE Search Tool to search for information related to that CVE ID/keyword, and provide the search results to the explainer agent for further explanation.',
      backstory="""You are an expert in CVE (Common Vulnerabilities and Exposures) research and analysis. Your role involves retrieving detailed information about CVEs based on user queries.
      DON'T summarize the information, pass it as it is to the explainer agent.""",
      verbose=True,
      allow_delegation=True,
      tools=[cve_search_tool],
      llm=llm
    )
    explainer = Agent(
      role='Security events Explainer and Analyser',
      goal=f'Provide detailed and technical explainations to user question based on search results. Here is the query from the user that you need to explain: {self.query}',
      backstory="""You are a renowned Cybersecurity analytics expert, known for your insightful explainations.
      You transform complex data into compelling reports. Don't tell any disclaimers, just provide the information.
      Don't look for supplementary information and don't use any tools nor create them, just use the information provided to you.""",
      verbose=True,
      allow_delegation=False,
      llm=wrn
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

        Here is the query from the user that you need to search for: {self.query}""",
        agent=cve_searcher
    )

    task1 = Task(
      description=f"""Take a user query that contain and indicator of compromise, search for the keyword and then pass the search results to the explainer agent
      If the user query doesn't contain any indicator just delegate it to the general agent
      
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
      agents=[explainer, cve_searcher],
      tasks=[task3, task2],
      verbose=2, # You can set it to 1 or 2 to different logging levels
      manager_llm=llm
    )

    HunterCrew.kickoff()

if __name__ == "__main__":
  # print("## Welcome to Newsletter Writer")
  print('-------------------------------')
  urls = input(
    dedent("""
      How can I help?
    """))
  
  hunt_crew = HunterCrew(urls)
  result = hunt_crew.run()
  # print("\n\n########################")
  # print("## Here is the Result")
  # print("########################\n")
  # print(result)
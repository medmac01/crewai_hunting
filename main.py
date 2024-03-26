import os
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from tools.elastic_tool import EventSearchTool
from langchain_community.llms import HuggingFaceHub
from dotenv import load_dotenv

load_dotenv()

llm = HuggingFaceHub(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    task="text-generation",
    model_kwargs={
        "max_new_tokens": 512,
        "temperature": 0.1,
        "return_full_text":False
    },
)

print(llm.invoke("Hello!!"))

ioc_search_tool = EventSearchTool().search

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
    explainer = Agent(
      role='Security events Explainer and Analyser',
      goal='Provide detailed and technical explainations to user question based on search results.',
      backstory="""You are a renowned Cybersecurity analytics expert, known for your insightful explainations.
      You transform complex data into compelling reports.""",
      verbose=True,
      allow_delegation=False,
      llm=llm
    )
    general_agent = Agent(
      role='Provide assistance to the user!',
      goal='You are a helpful assistant, your goal is to assist the user',
      backstory="""You are a helpful assistant, your goal is to assist the user. You can answer general questions like : how are you? and who are you?""",
      verbose=True,
      allow_delegation=False,
      llm=llm
    )

    # Create tasks for your agents
    task1 = Task(
      description=f"""Take a user query that contain and indicator of compromise, search for the keyword and then pass the search results to the explainer agent
      If the user query doesn't contain any indicator just delegate it to the general agent
      
      here is the query from the user that you need to search for: {self.query}""",
      agent=searcher
    )

    task2 = Task(
      description=f"""Using the search results provided by the searcher agent, develop a short and compelling/interesting short-form explanation of the 
      text provided to you about Cybersecurity answering to the following query {self.query}""",
      agent=explainer
    )

    # task3 = Task(
    #   description=f"""Answer the user's message in a human way {self.query}, no need to use any tools or delegate to other agents""",
    #   agent=general_agent
    # )

    # Instantiate your crew with a sequential process
    HunterCrew = Crew(
      agents=[searcher, explainer],
      tasks=[task1, task2],
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
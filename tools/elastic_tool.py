import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from langchain.tools import tool

class EventSearchTool():
  @tool("Event search Tool")
  def search(keyword: str):
    "Useful tool to search for an indicator of compromise or an security event"
    es = Elasticsearch(
      "https://localhost:9200",
      basic_auth=("elastic","dVJI85*y60R3ZVbECj1w"),
      ca_certs="/Volumes/macOS/Projects/PFE UM6P/elasticsearch-8.12.1/config/certs/http_ca.crt"
    )

    if not es.ping():
       raise "ElasticNotReachable"
    
    query = {
        "match": {"value": {
            "query": keyword
        }}
    }

    # Execute the search query
    res = es.search(size=5, index="all_events_full", query=query, knn=None, _source=["event_id", "event_title", "event_date", "category", "attribute_tags", "type", "value"])
    hits = res["hits"]["hits"]

    return [x['_source'] for x in hits]
    

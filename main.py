import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver

from tools_tavily import tavily_function
from tool_avitaion import aviation_funtion

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

llm = ChatGroq(model="openai/gpt-oss-120b")


class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    final_response: str
    llm_calls: int


def flight_agent(state: TravelState):
    result = aviation_funtion(state["user_query"])
    return {
        "flight_results": str(result),
        "messages": [AIMessage(content="flight result fetched")],
    }


def hotel_agent(state: TravelState):
    result = tavily_function(state["user_query"])
    return {
        "hotel_results": str(result),
        "messages": [AIMessage(content="hotel information fetched")],
    }


def itinerary_agent(state: TravelState):
    prompt = f"""
    Create a travel itinerary.

    User query: {state["user_query"]}
    Flight results: {state["flight_results"]}
    Hotel results: {state["hotel_results"]}
    """

    response = llm.invoke([
        SystemMessage(content="You are a helpful AI assistant."),
        HumanMessage(content=prompt),
    ])

    return {
        "itinerary": response.content,
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def final_agent(state: TravelState):
    final_prompt = f"""
    Generate a final travel response.

    Flight: {state["flight_results"]}
    Hotel: {state["hotel_results"]}
    Itinerary: {state["itinerary"]}
    """

    response = llm.invoke([HumanMessage(content=final_prompt)])

    return {
        "final_response": response.content,
        "messages": [AIMessage(content=response.content)],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)

pg = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
checkpointer = PostgresSaver(pg)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "user_abhishek"}}

    user_input = input("Enter travel request: ")

    result = app.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "final_response": "",
            "llm_calls": 0,
        },
        config=config,
    )

    print("\nFINAL RESPONSE:\n")
    print(result["final_response"])
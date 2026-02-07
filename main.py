from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from groq import Groq

from agents import ResearchAgent, PlannerAgent
from utils import load_state, save_state

load_dotenv()

app = FastAPI()

# Allow React to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

research_agent = ResearchAgent()
planner_agent = PlannerAgent(client)


class IdeaRequest(BaseModel):
    idea: str


@app.post("/generate-plan")
def generate_plan(req: IdeaRequest):
    state = load_state()

    idea = req.idea
    state["idea"] = idea
    save_state(state)

    # Step 1: Research
    research = research_agent.research_topic(idea)

    # Step 2: Paraphrase
    refined = planner_agent.paraphrase_idea(idea, research)

    # Step 3: Generate Plan
    plan = planner_agent.generate_plan(refined)

    if not plan:
        return {"error": "LLM failed to generate valid plan"}

    state["plan"] = plan
    state["current_phase"] = 1
    save_state(state)

    return {
        "refined_idea": refined,
        "plan": plan
    }


@app.get("/state")
def get_state():
    return load_state()

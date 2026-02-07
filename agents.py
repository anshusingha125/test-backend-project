import requests
from github import Github, GithubException
import random
import json
from utils import parse_llm_output

class ResearchAgent:
    """Performs light research using Wikipedia API."""
    def research_topic(self, topic):
        print(f"\n[ResearchAgent] Searching Wikipedia for: {topic}...")
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": topic,
                "srlimit": 1
            }
            response = requests.get(url, params=params)
            data = response.json()
            if data["query"]["search"]:
                title = data["query"]["search"][0]["title"]
                # Get summary
                params_prop = {
                    "action": "query",
                    "format": "json",
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True,
                    "titles": title
                }
                res_prop = requests.get(url, params=params_prop)
                pages = res_prop.json()["query"]["pages"]
                page_id = next(iter(pages))
                summary = pages[page_id].get("extract", "No summary found.")
                print(f"[ResearchAgent] Found info on '{title}'.")
                return summary[:500] + "..." # Limit length
            else:
                return "No Wikipedia articles found."
        except Exception as e:
            return f"Research failed: {str(e)}"

class PlannerAgent:
    """Uses Groq LLM to paraphrase ideas and generate execution plans."""
    def __init__(self, client):
        self.client = client
        self.model = "llama-3.3-70b-versatile"  # Updated to supported model

    def paraphrase_idea(self, idea, research_summary):
        prompt = f"""
        I have an idea: "{idea}".
        Here is some background context: "{research_summary}".
        
        Please rewrite my idea to be clear, actionable, and suitable for a phased execution plan. 
        Output ONLY the paraphrased idea as a single paragraph.
        """
        
        print("\n[PlannerAgent] Paraphrasing idea...")
        return self._generate(prompt)

    def generate_plan(self, refined_idea, current_plan=None):
        prompt = f"""
        Goal: "{refined_idea}".
        Create a phased execution plan (3-6 phases).
        For each phase, provide:
        1. Phase number
        2. 3-5 concrete tasks
        3. One exact suggested commit message.
        
        Output MUST be valid JSON format like this:
        {{
            "total_phases": 3,
            "phases": [
                {{
                    "phase": 1,
                    "tasks": ["task 1", "task 2"],
                    "commit_message": "feat: complete phase 1"
                }}
            ]
        }}
        """
        
        print("\n[PlannerAgent] Generating execution plan...")
        output = self._generate(prompt)
        # Verify if output is wrapped in code block
        return parse_llm_output(output)

    def generate_clarifying_questions(self, idea):
        prompt = f"""
        User Idea: "{idea}"
        
        To create a solid execution plan, I need more details. 
        Generate exactly 3 specific, clarifying questions for the user to help refine the scope and technical details.
        Output ONLY the 3 questions as a numbered list.
        """
        print("\n[PlannerAgent] Generating clarifying questions...")
        return self._generate(prompt)

    def update_plan(self, current_plan, feedback, current_phase):
        prompt = f"""
        Current Project Plan: {json.dumps(current_plan)}
        Current Phase: {current_phase}
        User Feedback/Changes: "{feedback}"
        
        Update the REMAINING phases (starting from phase {current_phase + 1}) based on this feedback.
        Keep the phases that are already completed or in progress (up to {current_phase}) exactly as they are.
        Modify, add, or remove future phases as needed.
        
        Output MUST be the full valid JSON plan (including past phases):
        {{
            "total_phases": N,
            "phases": [...]
        }}
        """
        print("\n[PlannerAgent] Updating plan based on feedback...")
        output = self._generate(prompt)
        return parse_llm_output(output)

    def _generate(self, prompt):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=2048,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error generating text with Groq: {e}")
            return ""

class VerifierAgent:
    """Verifies progress via GitHub."""
    def verify_phase(self, repo_url, phase_data):
        print(f"\n[VerifierAgent] Verifying Phase {phase_data['phase']}...")
        
        # Extract owner/repo from URL
        clean_url = repo_url.rstrip(".git")
        parts = clean_url.split("/")
        if len(parts) < 2:
            print("Invalid GitHub URL.")
            return False
            
        repo_name = f"{parts[-2]}/{parts[-1]}"
        
        try:
            g = Github() # Anonymous access for public repos
            repo = g.get_repo(repo_name)
            
            # Check latest commit
            commits = repo.get_commits()
            if commits.totalCount == 0:
                print("Repo is empty.")
                return False
                
            latest_commit = commits[0]
            msg = latest_commit.commit.message.strip()
            expected = phase_data['commit_message'].strip()
            
            print(f"[VerifierAgent] Latest commit: '{msg}'")
            print(f"[VerifierAgent] Expected match: '{expected}'")
            
            if expected.lower() in msg.lower():
                print("[VerifierAgent] Commit message matched!")
                return True
            else:
                print("[VerifierAgent] Commit message did NOT match.")
                return False
                
        except GithubException as e:
            print(f"[VerifierAgent] GitHub Error: {e}")
            return False
        except Exception as e:
            print(f"[VerifierAgent] Error: {e}")
            return False

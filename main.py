import logging
import os

import requests
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

GITLAB_API_TOKEN = os.environ.get("GITLAB_API_TOKEN")
GITLAB_API_BASE_URL = os.environ.get("GITLAB_API_BASE_URL")
RAG_API_TOKEN = os.environ.get("RAG_API_TOKEN")
RAG_URL = os.environ.get("RAG_URL", "http://localhost:9000/backstage-ai/api/query")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI

app = FastAPI()


@app.post("/issues/webhook")
async def gitlab_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("object_kind") == "issue" and payload.get("event_type") == "issue":

        action = payload.get("object_attributes", {}).get("action")

        if action not in ["open", "update"]:
            logger.info(f"Ignoring event with action: {action}")
            return {
                "message": "Event not processed. Only 'open' and 'update' actions are handled."
            }

        project_id = payload.get("project", {}).get("id")
        issue_iid = payload.get("object_attributes", {}).get("iid")
        issue_title = payload.get("object_attributes", {}).get("title")
        description = payload.get("object_attributes", {}).get("description", "")


        logger.info(
            f"Processing issue: {issue_title} (IID: {issue_iid}) in project ID: {project_id}"
        )

        if not (project_id and issue_iid):
            logger.error("Missing project_id or issue_iid in payload")
            raise HTTPException(
                status_code=400, detail="Missing project_id or issue_iid in payload"
            )

        headers = {"Private-Token": GITLAB_API_TOKEN}
        labels_url = f"{GITLAB_API_BASE_URL}/projects/{project_id}/labels"
        logger.info(f"Fetching labels from: {labels_url}")
        labels_response = requests.get(labels_url, headers=headers)
        if labels_response.status_code != 200:
            raise HTTPException(
                status_code=labels_response.status_code, detail="Failed to fetch labels"
            )

        labels = [label["name"] for label in labels_response.json()]

        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': RAG_API_TOKEN  # Usamos la variable RAG_API_TOKEN
        }

        query = f"""
            Based on the following issue description and list of labels:
            Description: {description}
            Labels: {', '.join(labels)}

            Provide a helpful comment for the task. If you think it is relevant, include a GitLab label command with the labels you believe should be associated with this issue.
            """

        data = {
            "query": query,
            "system_prompt": "You are an AI assistant trying to help as much as possible.",
            "temperature": 0,
            "context": []
        }

        response = requests.post(RAG_URL, headers=headers, json=data)

        if response.status_code == 200:
            response_data = response.json()
            answer = response_data.get("answer")
            sources = response_data.get("sources", [])
            sources_info = "\n".join([f"Source name: {source['name']}, URL: {source['url']}" for source in sources])
            comment_body = f"""
                Hi!
                {answer}

                Sources:
                {sources_info}
            """

            comment_url = f"{GITLAB_API_BASE_URL}/projects/{project_id}/issues/{issue_iid}/notes"
            comment_data = {
                "body": comment_body
            }
            comment_response = requests.post(
                comment_url, headers=headers, json=comment_data
            )
            if comment_response.status_code != 201:
                raise HTTPException(
                    status_code=comment_response.status_code,
                    detail="Failed to create comment",
                )
        else:
            print(f"Error: {response.status_code}, {response.text}")

        return {"message": "Webhook processed and comment created successfully"}

    raise HTTPException(status_code=400, detail="Event not handled")

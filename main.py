import logging
import os
import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

GITLAB_API_TOKEN = os.environ.get("GITLAB_API_TOKEN")
GITLAB_API_BASE_URL = os.environ.get("GITLAB_API_BASE_URL")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
            return {"message": "Event not processed. Only 'open' and 'update' actions are handled."}

        project_id = payload.get("project", {}).get("id")
        issue_iid = payload.get("object_attributes", {}).get("iid")
        issue_title = payload.get("object_attributes", {}).get("title")
        project_url = payload.get("project", {}).get("web_url")

        logger.info(f"Processing issue: {issue_title} (IID: {issue_iid}) in project ID: {project_id}")


        if not (project_url and issue_iid):
            logger.error("Missing project_url or issue_iid in payload")
            raise HTTPException(status_code=400, detail="Missing project_url or issue_iid in payload")

        headers = {"Private-Token": GITLAB_API_TOKEN}
        labels_url = f"{project_url}/-/labels"
        logger.info(f"Fetching labels from: {labels_url}")
        labels_response = requests.get(labels_url, headers=headers)
        if labels_response.status_code != 200:
            raise HTTPException(status_code=labels_response.status_code, detail="Failed to fetch labels")

        labels = [label["name"] for label in labels_response.json()]


        comment_url = f"{project_url}/-/issues/{issue_iid}/notes"
        comment_data = {
            "body": f"Hello! Here are the labels available in this project: {', '.join(labels)}"
        }
        comment_response = requests.post(comment_url, headers=headers, json=comment_data)
        if comment_response.status_code != 201:
            raise HTTPException(status_code=comment_response.status_code, detail="Failed to create comment")

        return {"message": "Webhook processed and comment created successfully"}

    raise HTTPException(status_code=400, detail="Event not handled")
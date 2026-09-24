from fastapi import APIRouter

# Intentionally endpoint-free for now: the CRUD handlers land in the next stage.
router = APIRouter(prefix="/tasks", tags=["tasks"])

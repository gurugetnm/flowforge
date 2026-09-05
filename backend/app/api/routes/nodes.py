"""The node catalog that drives the editor's palette and forms."""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.nodes import all_executors
from app.schemas.node import NodeTypeSchema

router = APIRouter(prefix="/node-types", tags=["nodes"])


@router.get("", response_model=list[NodeTypeSchema])
def list_node_types(current_user: CurrentUser) -> list[NodeTypeSchema]:
    """Describe every installed node type.

    The editor renders its palette and every configuration form from this
    response, so adding a node type on the server requires no client change.
    """
    return [NodeTypeSchema.from_executor(executor) for executor in all_executors()]

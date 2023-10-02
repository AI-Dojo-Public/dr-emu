from fastapi import APIRouter
from testbed_app.controllers.infrastructure import InfrastructureController

router = APIRouter(
    prefix="/infrastructures",
    tags=["infrastructures"],
    responses={404: {"description": "Not found"}},
)


@router.get("/delete/{infrastructure_id}")
async def destroy_infra(infrastructure_id: int):
    """
    responses:
      200:
        description: Destroys docker infrastructure
    """
    infrastructure = await InfrastructureController.get_infra(infrastructure_id)
    await InfrastructureController.stop_infra(infrastructure)
    await InfrastructureController.delete_infra(infrastructure)

    return {"message": f"Infrastructure {infrastructure_id} has been destroyed"}


@router.get("/")
async def list_infrastructures():
    """
    responses:
      200:
        description: List infrastructures id:name key values
    """
    return {"infrastructures": await InfrastructureController.list_infrastructures()}


@router.get("/get/{infrastructure_id}")
async def get_infra(infrastructure_id: int):
    return {"message": await InfrastructureController.get_infra(infrastructure_id)}

from fastapi import APIRouter, Response, status
from sqlalchemy.exc import NoResultFound

from dr_emu.api.dependencies.core import DBSession
from dr_emu.api.helpers import nonexistent_object_msg
from dr_emu.controllers.infrastructure import InfrastructureController
from dr_emu.schemas.infrastructure import InfrastructureInfo, NetworkSchema, ApplianceSchema, InfrastructureSchema

router = APIRouter(
    prefix="/infrastructures",
    tags=["infrastructures"],
    responses={
        404: {"description": "Infrastructure with specified ID Not found"},
    },
)


@router.delete(
    "/delete/{infrastructure_id}/",
    responses={204: {"description": "Object successfully deleted"}},
    status_code=status.HTTP_204_NO_CONTENT,
)
async def destroy_infra(infrastructure_id: int, session: DBSession):
    try:
        infrastructure = await InfrastructureController.get_infra(infrastructure_id, session)
    except NoResultFound:
        return {"message": f"Infrastructure with id: {infrastructure_id} doesn't exist"}

    await InfrastructureController.stop_infra(infrastructure)
    await InfrastructureController.delete_infra(infrastructure, session)


@router.get("/", response_model=list[InfrastructureSchema])
async def list_infrastructures(session: DBSession):
    infras = await InfrastructureController.list_infrastructures(session)
    response = [InfrastructureSchema(id=infra.id, name=infra.name) for infra in infras]
    return response


@router.get("/get/{infrastructure_id}/", response_model=InfrastructureInfo)
async def get_infra(infrastructure_id: int, session: DBSession, response: Response):
    try:
        infrastructure = await InfrastructureController.get_infra_info(infrastructure_id, session)

        infra_info = InfrastructureInfo(id=infrastructure_id, name=infrastructure.name)
        for network in infrastructure.networks:
            network_info = NetworkSchema(name=network.name, ip=str(network.ipaddress))
            infra_info.networks.append(network_info)
            for interface in network.interfaces:
                network_info.appliances.append(
                    ApplianceSchema(name=interface.appliance.name, ip=str(interface.ipaddress))
                )

        return infra_info

    except NoResultFound:
        response.status_code = status.HTTP_404_NOT_FOUND
        return nonexistent_object_msg("Infrastructure", infrastructure_id)

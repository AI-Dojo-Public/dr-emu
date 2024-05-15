from fastapi import APIRouter, status, HTTPException
from sqlalchemy.exc import NoResultFound

from dr_emu.models import Attacker, ServiceAttacker
from shared import constants
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=nonexistent_object_msg(constants.INFRASTRUCTURE, infrastructure_id),
        )

    await InfrastructureController.stop_infra(infrastructure)
    await InfrastructureController.delete_infra(infrastructure, session)


@router.get("/", response_model=list[InfrastructureSchema])
async def list_infrastructures(session: DBSession):
    infras = await InfrastructureController.list_infrastructures(session)
    response = [InfrastructureSchema(id=infra.id, name=infra.name, run_id=infra.instance.run_id) for infra in infras]
    return response


@router.get("/get/{infrastructure_id}/", response_model=InfrastructureInfo)
async def get_infra(infrastructure_id: int, session: DBSession):
    try:
        infrastructure = await InfrastructureController.get_infra_info(infrastructure_id, session)

        networks_info = []

        for network in infrastructure.networks:
            appliances_info = []
            for interface in network.interfaces:
                appliances_info.append(
                    ApplianceSchema(
                        name=interface.appliance.name,
                        ip=str(interface.ipaddress),
                        original_ip=str(interface.original_ip),
                    )
                )
            network_info = NetworkSchema(name=network.name, ip=str(network.ipaddress), appliances=appliances_info)
            networks_info.append(network_info)

        attackers = {}
        for node in infrastructure.nodes:
            if type(node) is Attacker:
                for service in node.services:
                    if type(service) is ServiceAttacker:
                        attackers[node.name] = service.environment["CRYTON_WORKER_NAME"]

        infra_info = InfrastructureInfo(
            id=infrastructure_id,
            name=infrastructure.name,
            run_id=infrastructure.instance.run_id,
            networks=networks_info,
            attackers=attackers
        )

        return infra_info

    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=nonexistent_object_msg(constants.INFRASTRUCTURE, infrastructure_id),
        )

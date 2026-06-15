"""Reference-resolution validation for the shared system architecture."""

from __future__ import annotations

from collections.abc import Iterable

from melos.core.project.model import Project

from .model import ValidationIssue


def validate_references(project: Project) -> list[ValidationIssue]:
    """Validate that entity references resolve to existing project IDs."""

    issues: list[ValidationIssue] = []

    asset_ids = {asset.id for asset in project.assets.items}
    system_ids = {system.id for system in project.systems}
    translation_map_ids = {tm.id for tm in project.translation_maps}

    link_ids_by_system = {system.id: {link.id for link in system.links} for system in project.systems}
    site_ids_by_system = {system.id: {site.id for site in system.sites} for system in project.systems}
    joint_ids_by_system = {system.id: {joint.id for joint in system.joints} for system in project.systems}
    geometry_ids_by_system = {
        system.id: {geometry.id for geometry in system.geometries} for system in project.systems
    }
    coordinate_ids_by_system = {
        system.id: {
            coordinate.id
            for joint in system.joints
            for coordinate in joint.coordinates
        }
        for system in project.systems
    }
    all_link_ids = set().union(*link_ids_by_system.values()) if link_ids_by_system else set()
    all_coordinate_ids = (
        set().union(*coordinate_ids_by_system.values()) if coordinate_ids_by_system else set()
    )

    def require_exists(value: str | None, existing: set[str], *, location: str, label: str) -> None:
        if value is None:
            return
        if value not in existing:
            issues.append(
                ValidationIssue(
                    code="ref.missing",
                    message=f"{label} {value!r} does not exist.",
                    location=location,
                )
            )

    def require_all_exist(values: Iterable[str], existing: set[str], *, location: str, label: str) -> None:
        for value in values:
            require_exists(value, existing, location=location, label=label)

    for system in project.systems:
        link_ids = link_ids_by_system[system.id]
        site_ids = site_ids_by_system[system.id]
        joint_ids = joint_ids_by_system[system.id]
        geometry_ids = geometry_ids_by_system[system.id]
        coordinate_ids = coordinate_ids_by_system[system.id]

        require_exists(
            system.root_link_id,
            link_ids,
            location=f"systems[{system.id}].root_link_id",
            label="System root link",
        )
        require_all_exist(
            system.asset_ids,
            asset_ids,
            location=f"systems[{system.id}].asset_ids",
            label="System asset",
        )

        for link in system.links:
            require_all_exist(
                link.asset_ids,
                asset_ids,
                location=f"systems[{system.id}].links[{link.id}].asset_ids",
                label="Link asset",
            )

        for site in system.sites:
            require_exists(
                site.link_id,
                link_ids,
                location=f"systems[{system.id}].sites[{site.id}].link_id",
                label="Site link",
            )
            require_exists(
                site.parent_site_id,
                site_ids,
                location=f"systems[{system.id}].sites[{site.id}].parent_site_id",
                label="Parent site",
            )

        for joint in system.joints:
            require_exists(
                joint.parent_link_id,
                link_ids,
                location=f"systems[{system.id}].joints[{joint.id}].parent_link_id",
                label="Joint parent link",
            )
            require_exists(
                joint.child_link_id,
                link_ids,
                location=f"systems[{system.id}].joints[{joint.id}].child_link_id",
                label="Joint child link",
            )
            require_exists(
                joint.parent_site_id,
                site_ids,
                location=f"systems[{system.id}].joints[{joint.id}].parent_site_id",
                label="Joint parent site",
            )
            require_exists(
                joint.child_site_id,
                site_ids,
                location=f"systems[{system.id}].joints[{joint.id}].child_site_id",
                label="Joint child site",
            )

        for geometry in system.geometries:
            require_exists(
                geometry.link_id,
                link_ids,
                location=f"systems[{system.id}].geometries[{geometry.id}].link_id",
                label="Geometry link",
            )
            require_exists(
                geometry.site_id,
                site_ids,
                location=f"systems[{system.id}].geometries[{geometry.id}].site_id",
                label="Geometry site",
            )
            require_exists(
                geometry.asset_id,
                asset_ids,
                location=f"systems[{system.id}].geometries[{geometry.id}].asset_id",
                label="Geometry asset",
            )

        for actuator in system.actuators:
            require_exists(
                actuator.joint_id,
                joint_ids,
                location=f"systems[{system.id}].actuators[{actuator.id}].joint_id",
                label="Actuator joint",
            )
            require_exists(
                actuator.coordinate_id,
                coordinate_ids,
                location=f"systems[{system.id}].actuators[{actuator.id}].coordinate_id",
                label="Actuator coordinate",
            )
            require_all_exist(
                actuator.link_ids,
                link_ids,
                location=f"systems[{system.id}].actuators[{actuator.id}].link_ids",
                label="Actuator link",
            )
            require_all_exist(
                actuator.site_ids,
                site_ids,
                location=f"systems[{system.id}].actuators[{actuator.id}].site_ids",
                label="Actuator site",
            )
            actuator_location = f"systems[{system.id}].actuators[{actuator.id}]"
            for index, node in enumerate(actuator.route):
                require_exists(
                    node.site_id,
                    site_ids,
                    location=f"{actuator_location}.route[{index}].site_id",
                    label="Route site",
                )
                require_exists(
                    node.geometry_id,
                    geometry_ids,
                    location=f"{actuator_location}.route[{index}].geometry_id",
                    label="Route wrap geometry",
                )
                require_exists(
                    node.side_site_id,
                    site_ids,
                    location=f"{actuator_location}.route[{index}].side_site_id",
                    label="Route side site",
                )

        for sensor in system.sensors:
            require_exists(
                sensor.link_id,
                link_ids,
                location=f"systems[{system.id}].sensors[{sensor.id}].link_id",
                label="Sensor link",
            )
            require_exists(
                sensor.site_id,
                site_ids,
                location=f"systems[{system.id}].sensors[{sensor.id}].site_id",
                label="Sensor site",
            )


    def require_endpoint_refs(endpoint: object, *, location: str, label: str) -> None:
        endpoint_system_id = getattr(endpoint, "system_id", None)
        require_exists(
            endpoint_system_id,
            system_ids,
            location=f"{location}.system_id",
            label=f"{label} system",
        )
        if endpoint_system_id not in link_ids_by_system:
            return
        endpoint_link_ids = link_ids_by_system[endpoint_system_id]
        endpoint_site_ids = site_ids_by_system.get(endpoint_system_id, set())
        endpoint_geometry_ids = geometry_ids_by_system.get(endpoint_system_id, set())
        require_exists(
            getattr(endpoint, "anchor_link_id", None),
            endpoint_link_ids,
            location=f"{location}.anchor_link_id",
            label=f"{label} anchor link",
        )
        require_all_exist(
            getattr(endpoint, "reference_link_ids", ()),
            endpoint_link_ids,
            location=f"{location}.reference_link_ids",
            label=f"{label} reference link",
        )
        require_all_exist(
            getattr(endpoint, "reference_site_ids", ()),
            endpoint_site_ids,
            location=f"{location}.reference_site_ids",
            label=f"{label} reference site",
        )
        require_all_exist(
            getattr(endpoint, "reference_geometry_ids", ()),
            endpoint_geometry_ids,
            location=f"{location}.reference_geometry_ids",
            label=f"{label} reference geometry",
        )

    for assembly in project.assemblies:
        for connection in assembly.connections:
            require_endpoint_refs(
                connection.endpoint_a,
                location=f"assemblies[{assembly.id}].connections[{connection.id}].endpoint_a",
                label="Connection endpoint_a",
            )
            if connection.endpoint_b is not None:
                require_endpoint_refs(
                    connection.endpoint_b,
                    location=f"assemblies[{assembly.id}].connections[{connection.id}].endpoint_b",
                    label="Connection endpoint_b",
                )

        for coupling in assembly.couplings:
            require_exists(
                coupling.source_coordinate_id,
                all_coordinate_ids,
                location=f"assemblies[{assembly.id}].couplings[{coupling.id}].source_coordinate_id",
                label="Coupling source coordinate",
            )
            require_exists(
                coupling.target_coordinate_id,
                all_coordinate_ids,
                location=f"assemblies[{assembly.id}].couplings[{coupling.id}].target_coordinate_id",
                label="Coupling target coordinate",
            )

    for signal in project.control.observations:
        if not signal.source_ref:
            issues.append(
                ValidationIssue(
                    code="ref.empty",
                    message="Observation source_ref must not be empty.",
                    location=f"control.observations[{signal.id}].source_ref",
                )
            )

    for signal in project.control.commands:
        if not signal.target_ref:
            issues.append(
                ValidationIssue(
                    code="ref.empty",
                    message="Command target_ref must not be empty.",
                    location=f"control.commands[{signal.id}].target_ref",
                )
            )

    visual_asset_ids = {asset.id for asset in project.assets.items if asset.role == "visual"}
    fitting_asset_ids = {asset.id for asset in project.assets.items if asset.role == "fitting"}

    for attachment in project.skin_attachments:
        if attachment.mesh_asset_id not in visual_asset_ids:
            issues.append(
                ValidationIssue(
                    code="ref.missing",
                    message=f"mesh_asset_id {attachment.mesh_asset_id!r} does not resolve to a 'visual' asset.",
                    location=f"skin_attachments[{attachment.id}].mesh_asset_id",
                )
            )
        if attachment.binding_asset_id not in fitting_asset_ids:
            issues.append(
                ValidationIssue(
                    code="ref.missing",
                    message=f"binding_asset_id {attachment.binding_asset_id!r} does not resolve to a 'fitting' asset.",
                    location=f"skin_attachments[{attachment.id}].binding_asset_id",
                )
            )
        require_exists(
            attachment.target_system_id,
            system_ids,
            location=f"skin_attachments[{attachment.id}].target_system_id",
            label="Skin attachment target system",
        )
        require_exists(
            attachment.translation_map_id,
            translation_map_ids,
            location=f"skin_attachments[{attachment.id}].translation_map_id",
            label="Translation map",
        )
        target_link_ids = link_ids_by_system.get(attachment.target_system_id, set())
        target_site_ids = site_ids_by_system.get(attachment.target_system_id, set())
        target_geometry_ids = geometry_ids_by_system.get(attachment.target_system_id, set())
        require_exists(
            attachment.fit.anchor_link_id,
            target_link_ids,
            location=f"skin_attachments[{attachment.id}].fit.anchor_link_id",
            label="Skin attachment anchor link",
        )
        require_all_exist(
            attachment.fit.reference_link_ids,
            target_link_ids,
            location=f"skin_attachments[{attachment.id}].fit.reference_link_ids",
            label="Skin attachment reference link",
        )
        require_all_exist(
            attachment.fit.reference_site_ids,
            target_site_ids,
            location=f"skin_attachments[{attachment.id}].fit.reference_site_ids",
            label="Skin attachment reference site",
        )
        require_all_exist(
            attachment.fit.reference_geometry_ids,
            target_geometry_ids,
            location=f"skin_attachments[{attachment.id}].fit.reference_geometry_ids",
            label="Skin attachment reference geometry",
        )

    return issues

from dataclasses import dataclass, field, is_dataclass
from typing import Any, Optional, get_args, get_origin, get_type_hints
from docassemble.base.util import DAStaticFile  # type: ignore


@dataclass(slots=True)
class ContactNumber:
    label: str
    number: str
    help: Optional[str] = None
    icon: Optional[str] = None


# @dataclass(slots=True)
# class ServiceAddress:
#     address: str
#     suburb: str
#     postCode: str


@dataclass(slots=True)
class Branch:
    """ 
        The purpose of a Branch is to allow for multiple addresses or services per organisation.
        A branch could correspond to an office, unit, or division of an organisation.

        However, if an organisation offers only a single service, that service must not be listed as a separate branch. Instead, it should appear as though it is the root organisation, without specifying any branches. The name of the organisation will then be the name of the service.
    """
    ID: str
    name: str
    address: str
    # if phoneNumber is a list, the first item in the list is considered the primary number
    number: str | list[ContactNumber]
    # if no url was provided the url of the parent organisation will be used
    url: Optional[str] = None
    logo: Optional[str] = None


@dataclass(slots=True)
class Organisation:
    # a unique id for this organisation or service
    ID: str
    # the name of the organisation or service
    name: str
    url: str
    # address is optional ONLY if there is at least one branch
    address: Optional[str] = None
    # if phoneNumber is a list, the first item in the list is considered the primary number
    # phoneNumber is optional ONLY if there is at least one branch
    number: Optional[str] | Optional[list[ContactNumber]] = None
    logo: Optional[str] = None
    branches: Optional[list[Branch]] | Optional[dict[str, Branch]] = None


def convertServiceListToDataclassDict(cls, data):
    if type(data) is str:
        return data
    if isinstance(data, (tuple, list)):
        if is_dataclass(cls):
            fieldtype = cls
        else:
            fieldtype = [arg for arg in get_args(
                cls) if get_origin(arg) is list][0].__args__[0]
        if isinstance(data[0], dict) and data[0].get("ID", None) is not None:
            return {i["ID"]: convertServiceListToDataclassDict(fieldtype, i) for i in data}
        return [convertServiceListToDataclassDict(fieldtype, i) for i in data]
    if isinstance(data, dict):
        if is_dataclass(cls):
            fieldtypes = get_type_hints(cls)
            return cls(**{k: convertServiceListToDataclassDict(fieldtypes[k], data[k]) for k in data})
    return data


@dataclass(slots=True)
class StoreManager:
    _services: dict[str, Organisation] = field(default_factory=dict)

    def setStoreFromJsonFile(self, filename: str = 'serviceData.json'):
        _tempServiceStore: dict[str, Organisation] = {}
        # convert JSON to Python dict
        import json

        # raise SystemError(
        #     'we got ' + json.dumps(json.loads(jsonFilePath)))

        # parsedServiceList: list[Any] = json.loads(jsonText)

        # for serviceItem in parsedServiceList:
        #     _serviceID = str(serviceItem["ID"])
        #     _tempServiceStore[_serviceID] = Organisation(**serviceItem)
        # raise SystemError(
        #     'we got ' + repr(_tempServiceStore))

        _jsonFile = DAStaticFile('servicelistfile', filename=filename)
        _jsonText: str = _jsonFile.slurp()

        parsedServiceList: list[Any] = json.loads(_jsonText)
        _tempServiceStore = convertServiceListToDataclassDict(  # type: ignore
            Organisation, parsedServiceList)
        self._services = _tempServiceStore

    def setStoreFromList(self, serviceList: list[Any]):
        _tempServiceStore = {}

        for serviceItem in serviceList:
            _tempServiceStore[serviceItem["ID"]] = Organisation(**serviceItem)

        self._services = _tempServiceStore

    def get(self, organisationID: str, branchID: Optional[str] = None) -> None | Organisation | Branch:
        _org: Organisation | None = self._services.get(organisationID, None)
        if branchID is not None and _org is not None:
            if _org.branches is not None and len(_org.branches) > 0 and isinstance(_org.branches, dict):
                # we want to get the branch, we don't care about the organisation
                _branch: Branch | None = _org.branches.get(branchID, None)
                return _branch
            # no branch was found, maybe invalid ID
            return None
        # we only want the organisation, or None if org was not found
        return _org

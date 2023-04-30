from dataclasses import asdict, dataclass, field, is_dataclass
from collections.abc import Callable
from typing import Any, Optional, cast, get_args, get_origin, get_type_hints
from . import storeManagement
from docassemble.base.util import DAList, DADict, DAStaticFile  # type: ignore

# from docassemble.base.error import DAError


@dataclass(slots=True)
class Filter:
    name: str
    # value should
    value: str | list[str]
    hurdle: bool = False


@dataclass(slots=True)
class Filters:
    local_dict: dict[str, Filter] = field(default_factory=dict)

    def add(self, filter: Filter):
        # convert DAList to normal list
        if isinstance(filter.value, DAList):
            filter.value = list(filter.value)
        # convert a DADict to a normal list with only the true values
        if isinstance(filter.value, DADict):
            filter.value = list(cast(DADict, filter.value).true_values())
        self.local_dict[filter.name] = filter

    def getValue(self, filterName):
        return self.local_dict[filterName].value

    def isHurdle(self, filterName):
        return self.local_dict[filterName].hurdle


@dataclass(slots=True)
class ServiceCondition:
    # the name of the filter
    TheSelected: str
    Is: str = ''
    IsNot: str = ''
    IsEither: list[str] = field(default_factory=list)
    IsBoth: list[str] = field(default_factory=list)
    IsNeither: list[str] = field(default_factory=list)
    IsNotBoth: list[str] = field(default_factory=list)
    # whether the condition should be exclusive
    strictly: bool = False


@dataclass(slots=True)
class __ServiceContractBase:
    """ 
        Filtration is carried out in two stages. The first stage filters the organisations. The second stage filters the branches.

        If an organisation is excluded, the filtration process will conclude for that org and its branches will not be considered.  
    """
    # pass a list of conditions that will determine whether to exclude this item or not
    # or pass a boolean to always show (true) or never show (false). You must not True if no branch is provided. False can only be used for testing.
    showIf: list[ServiceCondition] | bool


@dataclass(slots=True)
class ServiceContractBranch(__ServiceContractBase):
    #  the id of the branch, not the name
    branchID: str
    # branches is a versatile concept to group units, divisions, offices, and the like under one parent, where can share some data. When the list of matches is generated, however, branches are spread into their own separate element, and will appear on the screen as individual boxes. This is not always ideal, especially when dealing with location, where you might want all branhces to remain contained within a single component. To get that behaviour set fold to True, and the branch will be nested withing the parent organisation box.
    fold: bool = False


@dataclass(slots=True)
class ServiceContract(__ServiceContractBase):
    #  the id of the organisation or service, not the name
    organisationID: str
    # no branches by default
    branches: list[ServiceContractBranch] = field(default_factory=list)


@dataclass(slots=True)
class MatchMetaData:
    # false denotes a `close match`
    exactMatch: Optional[bool] = None
    # a percentage of how many conditions were satisfied (returned true) after testing against the filters out of the total number of specified CONDITIONS for a specific service. This gives precise detail when the service is a close match.
    conditionSatisfaction: Optional[int] = None
    # a percentage of how many conditions were satisfied out of the total number of FILTERS. This compliments satisfaction, to provide a clearer image of how a specific service relates to the user original query (the filters)
    querySatisfaction: Optional[int] = None


@dataclass(slots=True, kw_only=True)
class FilteredServiceContractBranch(ServiceContractBranch):
    metaData: MatchMetaData


@dataclass(slots=True, kw_only=True)
class FilteredServiceContract(ServiceContract):
    metaData: MatchMetaData
    # no branches by default
    branches: list[FilteredServiceContractBranch] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class MatchedServiceVariant(MatchMetaData):
    branchID: str


@dataclass(slots=True, kw_only=True)
class MatchedService(MatchMetaData):
    organisationID: str  # type: ignore
    branchID: Optional[str] = None
    # when a branch is folded, it is appended to this list, so it could be displayed nested within the root org
    variants: list[MatchedServiceVariant] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class MatchedServiceFullVariant(MatchMetaData):
    branchID: str
    name: str
    address: str
    number: str
    url: Optional[str] = None
    logo: Optional[str] = None


@dataclass(slots=True, kw_only=True)
class MatchedServiceFull(MatchedService):
    name: str
    address: str
    url: str | None = None
    # TODO: implement ContactNumber class and its support
    number: Optional[str] = None
    logo: Optional[str] = None
    variants: list[MatchedServiceFullVariant] = field(default_factory=list)


def convertContractListToDataclassList(cls, data):
    if type(data) is str:
        return data
    if isinstance(data, (tuple, list)):
        if is_dataclass(cls):
            fieldtype = cls
        else:
            fieldtype = [arg for arg in get_args(
                cls) if get_origin(arg) is list]
            fieldtype = fieldtype[0].__args__[
                0] if len(fieldtype) > 0 else list
        if isinstance(data[0], dict) and data[0].get("ID", None) is not None:
            return {i["ID"]: convertContractListToDataclassList(fieldtype, i) for i in data}
        return [convertContractListToDataclassList(fieldtype, i) for i in data]
    if isinstance(data, dict):
        if is_dataclass(cls):
            fieldtypes = get_type_hints(cls)
            return cls(**{k: convertContractListToDataclassList(fieldtypes[k], data[k]) for k in data})
    return data


@dataclass(slots=True)
class ContractsManager:

    # originalContracts contains a list of serviceContracts which determine if the service should be listed or filtered out.
    originalContracts: list[ServiceContract] = field(
        default_factory=list)

    _filteredContracts: list[FilteredServiceContract] = field(
        default_factory=list)

    _specificServices: list[str] = field(
        default_factory=list)

    _fallbackContracts: list[FilteredServiceContract] = field(
        default_factory=list)

    # contains a unique list of filters that we need to ask
    _lookAheadFilters: set[str] = field(default_factory=set)
    _useLookAhead: bool = True

    def getLookAheadList(self) -> set[str]:
        # the look ahead list triggers new questions. If we have only one match, we don't ask further questions to avoid showing nothing to user
        if len(self._filteredContracts) > 1:
            return self._lookAheadFilters
        return set()

    def add(self, contract: ServiceContract):
        self.originalContracts.append(contract)

    def initContractList(self, filename: str = 'serviceContracts.json'):
        _tempContractList: list[ServiceContract] = []
        # convert JSON to Python list
        import json

        _jsonFile = DAStaticFile('servicelistfile', filename=filename)
        _jsonText: str = _jsonFile.slurp()

        _parsedContractList: list[Any] = json.loads(_jsonText)
        _convertToDict = convertContractListToDataclassList(
            ServiceContract, _parsedContractList)
        _tempContractList = _convertToDict if isinstance(
            _convertToDict, list) else []
        self.originalContracts = _tempContractList

    def _initSpecificServiceList(self):
        # initialise the list if empty and only regenerate if new contract had been added after last initialisation
        if len(self._specificServices) == 0 or len(self._specificServices) != len(self.originalContracts):
            _tempList = []
            for contract in self.originalContracts:
                _tempList.append(contract.organisationID)
            self._specificServices = _tempList

    def testConditionList(self, conditionList: list[ServiceCondition], filtersDict: dict[str, Filter], hasBranches: bool = False, inheritedConditionList: list[ServiceCondition] = [], exactMatchOnly: bool = False, setMetaDataFn: Optional[Callable[..., None]] = None) -> bool:
        """Checks if the provided condition list matches any of the provided filters.

        Args:
            conditionList (list[ServiceCondition]): list of condition, usually the value of `showIf`
            filtersDict (dict[str, Filter]): the filters dictionary
            hasBranches (bool, optional): whether the organisation has branches. Defaults to False.
            inheritedConditionList (list[ServiceCondition], optional): a list of parent conditions. Defaults to [].
            exactMatchOnly (bool, optional): whether to return true only if exact match. Defaults to False.

        Returns:
            bool: whether the list of conditions matches the filters, influenced by exactMatchOnly
        """
        # when there is not an inherited list of conditions, treat service as the root org
        _isRootOrg = len(inheritedConditionList) == 0

        if not _isRootOrg:
            # this service inherits conditions from parent. Reconstruct the condition list in a none desctructive way (if branch condition conflicts with a parent condition we preserve the branch condition).
            _flattenedConditionsInherited = [
                condition.TheSelected for condition in inheritedConditionList]
            _flattenedConditionsBranch = [
                condition.TheSelected for condition in conditionList]
            # get any conflicting conditions
            _conflictingConditions = set(
                _flattenedConditionsInherited).intersection(_flattenedConditionsBranch)
            # resolve any conflicts by removing from the inherited list
            inheritedConditionList = [
                condition for condition in inheritedConditionList if condition.TheSelected not in _conflictingConditions]
            # merge inherited conditions with self conditions
            conditionList = [*inheritedConditionList, *conditionList]

        # check if any of the filters provided is a hurdle
        _hurdleFilters = [
            f for f in filtersDict if filtersDict[f].hurdle]
        _thereIsHurdleFilter = len(_hurdleFilters) > 0
        _thereIsNoConditionCorrespondingToHurdle = _thereIsHurdleFilter
        _conditionsCorrespondingToHurdles = 0
        # presume service passed all hurdles. we don't presume the contrary because some service might be fallbacks and we don't want to automatically treat them as `unrelated`. So, technicall passing a hurdling and not even testing is considered the same, albeit the later will classify the service as `fallback`. However, failing to pass a hurdle (returing False) immediately disqualifies the service as a potential match.
        _serviceDidNotPassSomeHurdles = False

        # a service could either be a close match or an exact match. By default this function returns the value of _closeMatch. Set exactMatchOnly to True to only return True if the service is an exact match
        _closeMatch = False
        _exactMatch = False
        # we keep track of the match result (true or false) of each condition that has been tested
        _testResults = []

        for condition in conditionList:
            _conditionName = condition.TheSelected
            # some condition are exclusive and applied strictly so that the service is excluded if it did not match a strict condition
            _conditionIsExclusive = condition.strictly
            # the testConditionList function in invoked as long as the filters dictionary contains at least one valid value, so it is possible that the filters dictionary may not have items corresponding to every condition specified (especially when using predictive filtering).
            _hasCorrespondingFilter = filtersDict.get(
                _conditionName, None) is not None

            if not _hasCorrespondingFilter:
                # if we are using look ahead strategy add missing filter to the list of needed filters
                if self._useLookAhead:
                    # note we only add to the look ahead list filters that have not been defined yet
                    self._lookAheadFilters.add(_conditionName)
                # we could not test this condittion
                _testResults.append(False)
                # current condition can't be checked. move to the next one.
                continue

            # condition has a corresponding filter against which we could test. Get the value and whether it is a hurdle
            _currentFilterValue = filtersDict[_conditionName].value
            _currentFilterIsHurdle = filtersDict[_conditionName].hurdle

            # stores whether the current condition matches the corresponding filter
            _conditionMatched = False
            # the `Is` field could be empty
            if (condition.Is.strip() not in (None, '')):
                # the `Is` field could only be a string but the value of the filter could be either string or list
                if isinstance(_currentFilterValue, list):
                    _conditionMatched = condition.Is in _currentFilterValue
                else:
                    _conditionMatched = _currentFilterValue == condition.Is

            # the `IsNot` field could be empty
            if (condition.IsNot.strip() not in (None, '')):
                # the `IsNot` field could only be a string but the value of the filter could be either string or list
                if isinstance(_currentFilterValue, list):
                    # we must not override _conditionMatched if it is already True
                    _conditionMatched = _conditionMatched or condition.IsNot not in _currentFilterValue

                else:
                    _conditionMatched = _conditionMatched or _currentFilterValue != condition.IsNot

            # the `IsEither` field is a list and it could be empty
            if (len(condition.IsEither) > 0):
                # the value of the filter could be either string or list
                if isinstance(_currentFilterValue, list):
                    # we must not override _matched if it is already True
                    _conditionMatched = _conditionMatched or not set(
                        _currentFilterValue).isdisjoint(condition.IsEither)

                else:
                    _conditionMatched = _conditionMatched or _currentFilterValue in condition.IsEither

            # the `IsNeither` field is a list and it could be empty
            if (len(condition.IsNeither) > 0):
                # the value of the filter could be either string or list
                if isinstance(_currentFilterValue, list):
                    # we must not override _matched if it is already True
                    _conditionMatched = _conditionMatched or set(
                        _currentFilterValue).isdisjoint(condition.IsNeither)
                else:
                    _conditionMatched = _conditionMatched or _currentFilterValue not in condition.IsNeither

            # `IsBoth` and `IsNotBoth` are only valid if the filter value is a list
            if isinstance(_currentFilterValue, list):
                if (len(condition.IsBoth) > 0):
                    _conditionMatched = _conditionMatched or set(
                        _currentFilterValue) == set(condition.IsBoth)
                if (len(condition.IsNotBoth) > 0):
                    _conditionMatched = _conditionMatched or set(
                        _currentFilterValue) != set(condition.IsNotBoth)

            if _thereIsHurdleFilter and _currentFilterIsHurdle and not _conditionMatched:
                # this service does not match a hurdle filter, so it is unrelated, regardless of whether it matched other conditions
                _serviceDidNotPassSomeHurdles = True
                _testResults = [False]
                # stop testing other conditions, it is sufficient that one hurdle filter failed
                break

            if _conditionIsExclusive and not _conditionMatched:
                # this condition is strict and because we could not satisfy it, the service must be filtered out
                _testResults = [False]
                # stop testing other conditions, it is sufficient that one strict condition failed
                break

            # we know there is a hurdle filter, check if any of the conditions corresponds with the hurdle filter. If none of the conditions correspond then this service will be treated as a fallback (relative) as per the Service Classification System
            if _thereIsHurdleFilter and _currentFilterIsHurdle:
                # when there is a hurdle filter we presume that there is no corresponding condition, then we check each condition individual. If we found a corresponding condition, we update the variable to indicate that the presumption was false and that there is a corresponding condition
                _thereIsNoConditionCorrespondingToHurdle = False
                # we also keep count of how many hurdles have a corresponding conditions, as there could be more than one hurdle and we need to either pass them all, or specify none.
                # if we pass them all, it is a match
                # if we don't pass some despite having a corresponding filter or not, it is an unrelated service
                # if we don't specify corresponding conditions to any, then it is a fallback.
                # it is also a fallback if we specify only some filters and pass them - in other words, a service is unrelated the moment it fails to pass even one hurdle, but it is a fallback if it does not fail nor pass (it does not have a corresponding filter)
                _conditionsCorrespondingToHurdles += 1

            # add the return value of current condition to the total test results.
            _testResults.append(_conditionMatched)

        # reaching here means one of three possibilites
        #   1. there is no hurdle filter - continue normally (we matched)
        #   2. there are hurdle filters and service passed them all - continue normally (we matched)
        #   3. there are hurdle filters but service was not tested against them all (it did not have a corresponding condition for some but it did pass those with corresponding conditions) - we did not match precisely (service is a fallback)
        if _thereIsHurdleFilter and _conditionsCorrespondingToHurdles != len(_hurdleFilters):
            # we matched but only because we ignored hurdles, so service is not a good match. we instead treat it as a fallback option, not a close or exact match.
            # TODO: setFallbackServiceFn()
            _testResults = [False]

        # it is a close match if there is at least one True value (one condition matches)
        _closeMatch = True in _testResults
        # get only true conditions for _testResults
        _truthyConditions = [
            truthyCondition for truthyCondition in _testResults if truthyCondition]
        # it is an exact match only if all filters were matched {no condition returned False and the number of truthy conditions matches the filters}
        _exactMatch = False not in _testResults and (
            len(_truthyConditions) == len(filtersDict))

        # we only save meta data about the service (match) if it was a close or exact match, but not `fallback` or `unrelated`
        if setMetaDataFn is not None and not _serviceDidNotPassSomeHurdles and (_exactMatch or _closeMatch):
            _passedConditionCount = len(_truthyConditions)
            # the strength of the match in relation to the specified conditions - by calculating the percentage of satisfied conditions out of total conditions
            _conditionSatisfaction = int((
                _passedConditionCount / len(conditionList)) * 100)
            # the strength of the match in relation to the filters - by calculating the percentage of satisfied conditions out of total filters
            _querySatisfaction = int(
                (_passedConditionCount /
                 len(filtersDict.keys())) * 100)
            setMetaDataFn(exactMatch=_exactMatch, conditionSatisfaction=_conditionSatisfaction,
                          querySatisfaction=_querySatisfaction)

        return _closeMatch if not exactMatchOnly else _exactMatch

    def filter(self, filters: dict[str, Filter]) -> list[FilteredServiceContract]:
        """
        Filters the list of contracts based on the provided filters.

        Args: 
            filters (dict[str, Filter]): a dictionary containing the filters stored by name as key.

        Returns: 
            list[ServiceContract]: optionally a filtered list of ServiceContract
        """

        if (len(filters.keys()) == 0):
            # nothing to match as no filters were provided
            return []

        _hasInvalidValue = False

        for fltr in filters.values():
            # each filter value could either be a plain string or a list of strings.
            # we need to check that the value is not empty and is valid

            # check for valid string
            if type(fltr.value) is not list and type(fltr.value) is not str:
                _hasInvalidValue = True
            # check there is at least one item in the list
            if type(fltr.value) is list and len(fltr.value) == 0:
                _hasInvalidValue = True

            if _hasInvalidValue:
                break

        if _hasInvalidValue:
            # some values are invalid, don't filter
            return []

        # generate the list of specific service from which we are going to compute the generic service list later. Only do this once
        self._initSpecificServiceList()

        # every time we filter we recreate the look ahead list, so that we don't ask questions filtered out
        self._lookAheadFilters = set()

        _tempFilteredContracts: list[FilteredServiceContract] = []

        _tempOriginalContracts = self.originalContracts.copy()
        for contract in _tempOriginalContracts:
            # for testing purposed a service can be hidden by setting showIf to false, in which case we skip that service.
            if type(contract.showIf) is bool and contract.showIf == False:
                continue

            # some organisations offer more than one service or perhaps at different locations - collectively called Branch. For this type of organisations we need to filter and match the branches as well, as the root organisation is just a collection rather than a service in itself.
            __hasBranches = len(contract.branches) > 0

            # setting showIf to True without having any branch is dissallowed
            if not __hasBranches and type(contract.showIf) is bool:
                continue

            # keep useful information about the match ie `exactMatch`, `conditionSatisfaction`, and `querySatisfaction`.
            _metadataOrg = MatchMetaData()

            def _setMetaData(dictionary: MatchMetaData):
                """Sets the metadata received from testConditionList to the provided dictionary
                """
                def _innerSetMetaData(exactMatch: bool, conditionSatisfaction: int, querySatisfaction: int):
                    dictionary.exactMatch = exactMatch
                    dictionary.conditionSatisfaction = conditionSatisfaction
                    dictionary.querySatisfaction = querySatisfaction

                return _innerSetMetaData

            def _addServiceToFiltered():
                _metaOrg = FilteredServiceContract(
                    organisationID=contract.organisationID, showIf=contract.showIf, branches=cast(list[FilteredServiceContractBranch], contract.branches), metaData=_metadataOrg)
                _tempFilteredContracts.append(
                    _metaOrg)

            _rootOrgSatisfiesSomeFilters = False
            # when we have at least one branch we can bypass the filtration for the parent organisation, and immediately proceed to filtering the branches
            if type(contract.showIf) is bool:
                # if showIf is boolean it can only be True, because of the condition at the top where we skip if false
                _rootOrgSatisfiesSomeFilters = True
            else:
                _rootOrgSatisfiesSomeFilters = self.testConditionList(
                    conditionList=contract.showIf, filtersDict=filters, hasBranches=__hasBranches, setMetaDataFn=_setMetaData(_metadataOrg))

            if not _rootOrgSatisfiesSomeFilters:
                # none of the specified conditions were satisfied, move to the next service and skip this
                continue

            if not __hasBranches:
                # no branches were provided, and this service has matched some of the filters, so add it to the list of filtered services.
                _addServiceToFiltered()
                continue

            # reaching here means we have branches and the root org matches filters. We must check that at least one branch matches the filters, before append an empty service. If no branch matches the query, the root org will be filtered out.

            _tempFilteredBranches = []

            for branch in contract.branches:
                _metadataBranch = MatchMetaData()
                # A branch can set showIf to a boolean, indicating that it should never be filtered out (True), or should always be hidden (False)
                if (type(branch.showIf) is bool and not branch.showIf) or (type(branch.showIf) is bool and type(contract.showIf) is bool):
                    # we hide when False, but when True, we apply the conditions of the parent only if the parent has a condition list and not boolean
                    _branchSatisfiesSomeFilters = branch.showIf
                else:
                    if type(branch.showIf) is bool and type(contract.showIf) is not bool:
                        # use the conditions of the parent if True, if parent has conditions, so that we get the metaData.
                        _branchConditionList = contract.showIf
                        _inheritance: list[ServiceCondition] = []
                    elif type(branch.showIf) is not bool and type(contract.showIf) is bool:
                        _branchConditionList: list[ServiceCondition] = branch.showIf
                        _inheritance: list[ServiceCondition] = []
                    else:
                        _branchConditionList: list[ServiceCondition] = cast(
                            list[ServiceCondition], branch.showIf)
                        # Note: branches inherit the conditions of the parent organisation. Brnaches can make inherited conditions more specific, or add more conditions, but they should not make an inherited condition falsy. For example, the root org could specify `location:[north, south]` and a branch could specify `location:north` but it should not specify `location:east` as this would conflict with  the inherited condition. When setting branch conditions it should be assumed that you only reach the branch if the conditions of the parent root are truthy. In the above example, `location:east` is not truthy against `location:[north, south]`. However, note that technically the root org only needs to be a close match for the filtration process to proceed onto the branches. So, its possible for `location:east` (which is not a hurdle fiter) to match a branch but not its parent which specifies `location:[north, south]`.
                        _inheritance: list[ServiceCondition] = cast(
                            list[ServiceCondition], contract.showIf)

                    # Test against the filters

                    _branchSatisfiesSomeFilters = self.testConditionList(
                        conditionList=_branchConditionList, filtersDict=filters, inheritedConditionList=_inheritance, setMetaDataFn=_setMetaData(_metadataBranch))

                if not _branchSatisfiesSomeFilters:
                    # skip branch it does not match the filters
                    continue

                # reaching here means the branch matches the query, so keep it.
                _metaBranch = FilteredServiceContractBranch(
                    branchID=branch.branchID, showIf=branch.showIf, metaData=_metadataBranch, fold=branch.fold)
                _tempFilteredBranches.append(_metaBranch)

            if len(_tempFilteredBranches) == 0:
                # none of the branches matches the filters, so no need for this org. Move to the next one.
                continue

            # reaching here means some branches satisfies the query. Replace the original branches with the filtered one and append the root org to the filtered service list.
            contract.branches = _tempFilteredBranches
            _addServiceToFiltered()

        # update the filteredContracts list
        self._filteredContracts = _tempFilteredContracts
        return _tempFilteredContracts

    def getMatches(self) -> list[MatchedService]:
        """ Generates a list of filtered services with useful metadata about the matches (i.e. type, strength, etc)

        It simply flattens the filtered ServiceContract list, by removing organisations that have branches and move those branches to the top level list, except when that branch is a variant, then it remains folded
        """

        _tempMatchedServices: list[MatchedService] = []
        for contract in self._filteredContracts:
            __hasBranches = len(contract.branches) > 0
            if not __hasBranches:
                # no branches. Add this org as a service
                _tempMatchedServices.append(MatchedService(
                    organisationID=contract.organisationID, exactMatch=contract.metaData.exactMatch, querySatisfaction=contract.metaData.querySatisfaction, conditionSatisfaction=contract.metaData.conditionSatisfaction))
                continue
            _multiLocationsService = MatchedService(
                organisationID=contract.organisationID, exactMatch=contract.metaData.exactMatch, querySatisfaction=contract.metaData.querySatisfaction, conditionSatisfaction=contract.metaData.conditionSatisfaction)
            for branch in contract.branches:
                if branch.fold:
                    # branch should remain nested
                    _multiLocationsService.variants.append(MatchedServiceVariant(
                        branchID=branch.branchID,
                        exactMatch=branch.metaData.exactMatch,
                        querySatisfaction=branch.metaData.querySatisfaction,
                        conditionSatisfaction=branch.metaData.conditionSatisfaction
                    ))
                    continue

                # Org has branches. Branch should be spread. Ignore the root org and only add the branches as services.
                _tempMatchedServices.append(MatchedService(
                    organisationID=contract.organisationID, branchID=branch.branchID, exactMatch=branch.metaData.exactMatch, querySatisfaction=branch.metaData.querySatisfaction, conditionSatisfaction=branch.metaData.conditionSatisfaction))
            if len(_multiLocationsService.variants) > 0:
                # add the multi location service
                _tempMatchedServices.append(_multiLocationsService)
        # sorting logic, first by query satisfaction, then condition satisfaction
        _sortedMatchList = sorted(_tempMatchedServices, key=lambda s: (
            s.querySatisfaction, s.conditionSatisfaction), reverse=True)
        return _sortedMatchList

    def getFallbacks(self, serviceStore) -> None:
        # TODO: get relative fallbacks
        # TODO: get alien fallbacks (general services)
        pass

    def getFallbacksRelative(self) -> None:
        pass

    def _getGenericServices(self, serviceStore) -> None:
        # TODO: get the items that are in the serviceStore but not in the self._specificServices - in other words, generic services refer to those services without a corresponding serviceContract
        pass


@dataclass(slots=True)
class ServiceDirectoryManager:

    contractsDossier: ContractsManager
    filters: Filters
    store: storeManagement.StoreManager

    def filter(self) -> list[FilteredServiceContract]:
        return self.contractsDossier.filter(self.filters.local_dict)

    def getMatches(self) -> list[MatchedService]:
        """ retrieves a list of match metadata - not the service itself. You should use this with store.get(orgID, branchID). Or, use `getMatchedServices()` which does this automatically for you.

        Returns:
            list[MatchedService]: _description_
        """
        return self.contractsDossier.getMatches()

    def getMatchedServices(self) -> list[MatchedServiceFull]:
        _matchesMetaData = self.getMatches()
        _matchesFull: list[MatchedServiceFull] = []
        for match in _matchesMetaData:
            # get the actual data for this match
            _service = self.store.get(match.organisationID, match.branchID)

            # skip if we got nothing. The issue is like invalid id or the store was not updated to the latest version. Otherwise, we sould get something, as serviceContract list is supposed to be constructed in reliance on the data in the store.
            if _service is None:
                continue

            _matchConcat = MatchedServiceFull(
                exactMatch=match.exactMatch,
                conditionSatisfaction=match.conditionSatisfaction,
                querySatisfaction=match.querySatisfaction,
                organisationID=match.organisationID,
                branchID=match.branchID,
                name=_service.name,
                address=_service.address or "Not Available",
                url=_service.url,
                # TODO: number could be contractNumber but not used yet
                number=cast(str, _service.number),
                logo=_service.logo
            )
            if len(match.variants) > 0:
                # we have variants, get their data
                for variant in match.variants:
                    _orgVariant = self.store.get(
                        match.organisationID, variant.branchID)
                    # sometimes when the id is wrong we don't get any data from the store, so skip it
                    if _orgVariant is None:
                        continue

                    _variantConcat = MatchedServiceFullVariant(
                        exactMatch=variant.exactMatch,
                        conditionSatisfaction=variant.conditionSatisfaction,
                        querySatisfaction=variant.querySatisfaction,
                        branchID=variant.branchID,
                        # if None inherit from root org
                        name=_orgVariant.name or _service.name,
                        url=_orgVariant.url or _service.url,
                        address=_orgVariant.address or _service.address or 'Not Available',
                        # TODO: number could be contractNumber but not used yet
                        number=cast(
                            str, _orgVariant.number or _service.number),
                        logo=_orgVariant.logo or _service.logo
                    )
                    # add to the root org
                    _matchConcat.variants.append(_variantConcat)
            # add each service to the list of matches
            _matchesFull.append(_matchConcat)

        return _matchesFull

    def getFallbacks(self, serviceStore) -> None:
        return self.contractsDossier.getFallbacks(serviceStore=serviceStore)

    def getFallbacksRelative(self) -> None:
        return self.contractsDossier.getFallbacksRelative()

    def getFallbacksAlien(self, serviceStore) -> None:
        return self.contractsDossier._getGenericServices(serviceStore=serviceStore)

    def getLookAheadList(self):
        return self.contractsDossier.getLookAheadList()
